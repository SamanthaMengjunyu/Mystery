"""OpenAI 兼容 messages 格式转换。"""

def _mk_messages(system, user):
    """把 (system, user) 文本对包成 OpenAI messages 数组。"""
    return [{"role": "system", "content": system},
            {"role": "user", "content": user}]


def _norm_messages(built):
    """统一 build_* 的产物：(system, user) 元组 → messages；已是 messages 列表则原样返回。"""
    if isinstance(built, tuple):
        return _mk_messages(built[0], built[1])
    return built
