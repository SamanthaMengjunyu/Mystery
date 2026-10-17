"""通过显式参数建立 LLM 配置；不读取或保存任何本机凭据。"""
from urllib.parse import urlsplit


def make_config(api_base, api_key, model, *, lite_model=None, timeout=120,
                cloud_concurrency=3, lite_concurrency=3, retry=2, fallback=False):
    """构造独立配置字典；地址、Key、模型必填，默认关闭速览兜底。"""
    values = {"api_base": api_base, "api_key": api_key, "model": model}
    for name, value in values.items():
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{name} 不能为空")
    base = api_base.strip().rstrip("/")
    parsed = urlsplit(base)
    if (parsed.scheme not in ("http", "https") or not parsed.netloc
            or parsed.username or parsed.password or parsed.query or parsed.fragment):
        raise ValueError("api_base 须为 http/https API 根地址，不能包含凭据、查询或片段")
    if timeout <= 0 or cloud_concurrency < 1 or lite_concurrency < 1 or retry < 0:
        raise ValueError("超时和并发须为正数，重试次数不能为负数")
    if any(isinstance(n, bool) or not isinstance(n, int)
           for n in (cloud_concurrency, lite_concurrency, retry)):
        raise ValueError("并发和重试次数须为整数")
    if lite_model is not None and (not isinstance(lite_model, str) or not lite_model.strip()):
        raise ValueError("lite_model 须为非空字符串或 None")
    if not isinstance(fallback, bool):
        raise ValueError("fallback 须为布尔值")
    return {"backend": "cloud", "api_base": base, "api_key": api_key.strip(),
            "model": model.strip(), "lite_api_base": base,
            "lite_api_key": api_key.strip(),
            "lite_model": lite_model.strip() if lite_model else model.strip(),
            "timeout": timeout, "cloud_concurrency": cloud_concurrency,
            "lite_concurrency": lite_concurrency, "retry": retry,
            "fallback": "on" if fallback else "off"}
