"""OpenAI 兼容 HTTP 客户端；不预设地址、Key 或模型。"""
import http.client
import json
import urllib.request
import urllib.error

from .messages import _mk_messages

def _chat_openai(api_base, api_key, model, messages, timeout):
    """OpenAI 兼容 /chat/completions（LLM / DeepSeek），非流式。"""
    url = api_base.rstrip("/") + "/chat/completions"
    payload = {
        "model": model,
        "messages": messages,
        "temperature": 0.7, "stream": False,
    }
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers={
        "Content-Type": "application/json",
        "Authorization": "Bearer " + api_key,
    })
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = json.loads(resp.read().decode("utf-8"))
        return body["choices"][0]["message"]["content"].strip()
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"LLM 接口错误 HTTP {e.code}：{e.read().decode('utf-8', 'ignore')[:200]}")
    except urllib.error.URLError as e:
        raise RuntimeError(f"无法连接 LLM（{api_base}）：{e}")
    except (ValueError, KeyError, IndexError) as e:
        raise RuntimeError(f"LLM 返回解析失败：{e}")


def list_models(api_base, api_key, timeout=15):
    """拉取某厂商的可用模型 id 列表（OpenAI 兼容 /models）。供后台下拉框用。"""
    url = api_base.rstrip("/") + "/models"
    req = urllib.request.Request(url, headers={"Authorization": "Bearer " + api_key})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"接口错误 HTTP {e.code}：{e.read().decode('utf-8', 'ignore')[:200]}")
    except urllib.error.URLError as e:
        raise RuntimeError(f"无法连接 {api_base}：{e}")
    except (ValueError, KeyError) as e:
        raise RuntimeError(f"返回解析失败：{e}")
    return [m.get("id") for m in body.get("data", []) if m.get("id")]


def ping_model(api_base, api_key, model, timeout=30):
    """用极短 prompt 试调一次，验证厂商+模型可用。返回回包文本片段。"""
    return _chat_openai(api_base, api_key, model,
                        _mk_messages("你是测试助手。", "回复两个字：可用"), timeout)


def _stream_openai(api_base, api_key, model, messages, timeout, usage_out=None):
    """OpenAI 兼容流式（LLM / DeepSeek），逐块 yield 文本增量。

    messages 为完整的 OpenAI 消息数组（含 system / 多轮 user-assistant），
    既用于单轮解读，也用于追问对话的多轮上下文。

    传入可变字典 usage_out 时，开启 stream_options.include_usage，把服务端在末尾
    返回的真实 token 用量（prompt/completion/total）写回该字典，供上层记账。
    """
    url = api_base.rstrip("/") + "/chat/completions"
    payload = {
        "model": model,
        "messages": messages,
        "temperature": 0.7, "stream": True,
    }
    if usage_out is not None:
        # 末尾追加一个 choices 为空、仅含 usage 的块
        payload["stream_options"] = {"include_usage": True}
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers={
        "Content-Type": "application/json", "Authorization": "Bearer " + api_key})
    try:
        resp = urllib.request.urlopen(req, timeout=timeout)
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"LLM 接口错误 HTTP {e.code}：{e.read().decode('utf-8', 'ignore')[:200]}")
    except urllib.error.URLError as e:
        raise RuntimeError(f"无法连接 LLM（{api_base}）：{e}")
    # 连接建立后逐行读取。网络不稳时，读取过程中可能出现连接被重置、读超时、
    # 不完整分块等错误（socket.timeout/ConnectionResetError 属 OSError、
    # IncompleteRead 属 http.client.HTTPException），这些都不是 RuntimeError，
    # 若不在此捕获就会以原始异常掐断 SSE 流 → 前端直接报 network error。
    # 统一转成带可读信息的 RuntimeError，让上层（退避重试 / 干净的 error 事件）接管。
    try:
        for raw in resp:
            line = raw.decode("utf-8", "ignore").strip()
            if not line.startswith("data:"):
                continue
            chunk = line[5:].strip()
            if chunk == "[DONE]":
                break
            try:
                obj = json.loads(chunk)
            except ValueError:
                continue
            # include_usage 模式：末尾块 choices 为空、带 usage
            if usage_out is not None and obj.get("usage"):
                u = obj["usage"]
                usage_out["prompt_tokens"] = u.get("prompt_tokens", 0)
                usage_out["completion_tokens"] = u.get("completion_tokens", 0)
                usage_out["total_tokens"] = u.get("total_tokens", 0)
            try:
                delta = obj["choices"][0]["delta"].get("content")
            except (KeyError, IndexError):
                continue
            if delta:
                yield delta
    except (urllib.error.URLError, http.client.HTTPException, OSError) as e:
        raise RuntimeError(f"流式读取中断（网络不稳定）：{e}")
    finally:
        try:
            resp.close()
        except OSError:
            pass
