"""可选 AI 解读入口；显式调用才会联网，不参与排盘与规则判断。"""
from .client import _chat_openai
from .messages import _mk_messages
from .prompts import (build_prompt, build_astro_prompt, build_tarot_prompt,
                      build_liuyao_prompt, build_ziwei_prompt, build_jyotish_prompt,
                      build_meihua_prompt, build_lenormand_prompt,
                      build_followup_messages)
from .scheduler import _LLMScheduler

_SCHED = _LLMScheduler()

def interpret_chart(chart, cfg, domains=None):
    """生成自然语言解读，返回完整文本（非流式，云端 OpenAI 兼容）。"""
    system, user = build_prompt(chart, domains)
    return _chat_openai(cfg["api_base"], cfg["api_key"], cfg["model"],
                        _mk_messages(system, user), cfg.get("timeout", 120))


def _run_stream(build_full, build_lite, cfg):
    """统一调度：各模块共用。build_full/build_lite 为惰性构造 (system,user) 的无参函数。"""
    yield from _SCHED.stream(build_full, build_lite, cfg)


def interpret_chart_stream(chart, cfg, domains=None):
    """流式生成八字解读，yield 事件 dict（queue/notice/delta）。"""
    yield from _run_stream(lambda: build_prompt(chart, domains, lite=False),
                           lambda: build_prompt(chart, domains, lite=True), cfg)


def interpret_astro_stream(chart, cfg, domains=None):
    """流式生成星盘解读，yield 事件 dict（queue/notice/delta）。"""
    yield from _run_stream(lambda: build_astro_prompt(chart, domains, lite=False),
                           lambda: build_astro_prompt(chart, domains, lite=True), cfg)


def interpret_tarot_stream(reading, cfg):
    """流式生成塔罗解读，yield 事件 dict（queue/notice/delta）。"""
    yield from _run_stream(lambda: build_tarot_prompt(reading, lite=False),
                           lambda: build_tarot_prompt(reading, lite=True), cfg)


def interpret_liuyao_stream(reading, cfg):
    """流式生成六爻解读，yield 事件 dict（queue/notice/delta）。"""
    yield from _run_stream(lambda: build_liuyao_prompt(reading, lite=False),
                           lambda: build_liuyao_prompt(reading, lite=True), cfg)


def interpret_ziwei_stream(chart, cfg):
    """流式解读紫微既定命盘，仅显式调用时联网。"""
    yield from _run_stream(lambda: build_ziwei_prompt(chart, lite=False),
                           lambda: build_ziwei_prompt(chart, lite=True), cfg)


def interpret_jyotish_stream(chart, cfg):
    """流式解读印度占星既定命盘，仅显式调用时联网。"""
    yield from _run_stream(lambda: build_jyotish_prompt(chart, lite=False),
                           lambda: build_jyotish_prompt(chart, lite=True), cfg)


def interpret_meihua_stream(reading, cfg):
    """流式解读梅花问事，显式调用才联网。"""
    yield from _run_stream(lambda: build_meihua_prompt(reading, lite=False),
                           lambda: build_meihua_prompt(reading, lite=True), cfg)


def interpret_lenormand_stream(reading, cfg):
    """流式解读雷诺曼问事，显式调用才联网。"""
    yield from _run_stream(lambda: build_lenormand_prompt(reading, lite=False),
                           lambda: build_lenormand_prompt(reading, lite=True), cfg)


def interpret_followup_stream(module, result, interpretation, history, question,
                              cfg, refs=None):
    """流式生成追问回答，yield 事件 dict（queue/notice/delta），复用统一调度与速览兜底。"""
    yield from _run_stream(
        lambda: build_followup_messages(module, result, interpretation, history,
                                        question, refs=refs, lite=False),
        lambda: build_followup_messages(module, result, interpretation, history,
                                        question, refs=refs, lite=True),
        cfg)
