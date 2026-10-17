"""原项目的进程内并发、排队、重试、速览兜底与 token 用量事件。"""
import threading
import time

from .client import _stream_openai
from .messages import _norm_messages

class _LLMScheduler:
    """限制云端并发、提供排队位次、退避重试，繁忙/失败时回退云端速览。"""

    def __init__(self):
        self._lock = threading.Lock()
        self._inflight = 0
        self._cloud_sema = None
        self._lite_sema = None

    def _ensure(self, cloud_n, local_n):
        """首次调用时按配置惰性建好信号量（之后固定）。"""
        with self._lock:
            if self._cloud_sema is None:
                self._cloud_sema = threading.BoundedSemaphore(max(1, cloud_n))
                self._lite_sema = threading.BoundedSemaphore(max(1, local_n))

    def _others(self):
        """当前正在生成的其它任务数（= 排在前面的人数）。"""
        with self._lock:
            return max(0, self._inflight - 1)

    def stream(self, build_full, build_lite, cfg):
        """统一调度入口，yield 事件 dict。"""
        self._ensure(cfg.get("cloud_concurrency", 3), cfg.get("lite_concurrency", 3))
        fallback_on = cfg.get("fallback", "on") != "off"
        with self._lock:
            self._inflight += 1
        try:
            got = self._cloud_sema.acquire(blocking=False)
            if got:
                yield {"type": "queue", "ahead": self._others(), "mode": "cloud"}
                state = {"emitted": False}
                try:
                    messages = _norm_messages(build_full())
                    yield from self._cloud_retry(messages, cfg, state)
                    return
                except RuntimeError as e:
                    # 已经吐出过内容后才断（网络中途掉线）：此时转 lite 会把两段
                    # 不同模型的答案拼在一起，反而更乱 → 干净报错，让前端「重试」按钮接管。
                    if state["emitted"]:
                        yield {"type": "error",
                               "error": f"生成过程中网络中断（{str(e)[:100]}）。上面已生成的内容已保留，可点「重试」继续。"}
                        return
                    if not fallback_on:
                        raise
                    yield {"type": "notice", "mode": "preview",
                           "text": f"完整模型生成失败，已转速览版（{str(e)[:80]}）"}
                finally:
                    self._cloud_sema.release()
                # 完整模型「在出首个 token 前」失败且允许兜底 → lite 速览
                yield from self._lite_stream(build_lite, cfg)
                return

            # 完整模型繁忙、拿不到槽位
            if not fallback_on:
                # 不兜底：排队等完整模型（发心跳显示位次）
                while not self._cloud_sema.acquire(timeout=2.0):
                    yield {"type": "queue", "ahead": self._others(), "mode": "cloud", "waiting": True}
                try:
                    messages = _norm_messages(build_full())
                    yield from self._cloud_retry(messages, cfg, {"emitted": False})
                finally:
                    self._cloud_sema.release()
                return
            # 兜底开启：不干等，转 lite 速览
            yield {"type": "queue", "ahead": self._others(), "mode": "preview"}
            yield {"type": "notice", "mode": "preview",
                   "text": "完整模型正在排队，先给你一份速览版（可收藏，稍后点『重新解读』获取完整报告）"}
            yield from self._lite_stream(build_lite, cfg)
        finally:
            with self._lock:
                self._inflight -= 1

    def _cloud_retry(self, messages, cfg, state):
        """云端流式 + 退避重试。仅在「未吐出任何 token 前」失败才重试，避免重复输出。

        state['emitted'] 置 True 表示已向前端吐出过至少一个 token——之后再断线
        就不能重试（会重复），也不该转 lite（会拼出两段答案），由调用方据此处理。
        """
        retries = cfg.get("retry", 2)
        timeout = cfg.get("timeout", 120)
        attempt = 0
        while True:
            usage_out = {}
            gen = _stream_openai(cfg["api_base"], cfg["api_key"], cfg["model"],
                                 messages, timeout, usage_out)
            try:
                first = next(gen)
            except StopIteration:
                return
            except RuntimeError:
                attempt += 1
                if attempt > retries:
                    raise
                time.sleep(1.5 * (2 ** (attempt - 1)))
                continue
            state["emitted"] = True
            yield {"type": "delta", "text": first}
            for delta in gen:    # 首 token 后再断线：转成 RuntimeError 向上抛，不重试
                yield {"type": "delta", "text": delta}
            if usage_out:
                # 内部记账事件（云端真实 token）；路由层的 track_stream 截获、不下发前端
                yield {"type": "usage", "mode": "cloud", **usage_out}
            return

    def _lite_stream(self, build_lite, cfg):
        """lite 便宜小模型速览：等 lite 槽位（期间发心跳），再云端流式输出。"""
        messages = _norm_messages(build_lite())
        api_base = cfg.get("lite_api_base") or cfg["api_base"]
        api_key = cfg.get("lite_api_key") or cfg["api_key"]
        model = cfg.get("lite_model") or cfg["model"]
        while not self._lite_sema.acquire(timeout=2.0):
            yield {"type": "queue", "ahead": self._others(), "mode": "preview", "waiting": True}
        try:
            usage_out = {}
            for delta in _stream_openai(api_base, api_key, model, messages,
                                        cfg.get("timeout", 120), usage_out):
                yield {"type": "delta", "text": delta}
            if usage_out:
                # 速览也记真实 token（便宜模型），标 mode=preview 供 track_stream 区分
                yield {"type": "usage", "mode": "preview", **usage_out}
        finally:
            self._lite_sema.release()
