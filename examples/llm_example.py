"""可选联网示例；运行前自行设置 LLM_API_BASE / LLM_API_KEY / LLM_MODEL。"""
import os

from mystery.llm import interpret_tarot_stream, make_config
from mystery.tarot import draw


def main():
    """使用调用者提供的连接信息解读塔罗；不会打印 Key。"""
    required = ("LLM_API_BASE", "LLM_API_KEY", "LLM_MODEL")
    missing = [name for name in required if not os.environ.get(name, "").strip()]
    if missing:
        raise SystemExit("请先设置环境变量：" + ", ".join(missing))
    cfg = make_config(*(os.environ[name] for name in required))
    reading = draw("three", question="当前应该关注什么？", seed=12345)
    for event in interpret_tarot_stream(reading, cfg):
        if event["type"] == "delta":
            print(event["text"], end="", flush=True)
        elif event["type"] == "error":
            raise SystemExit(event["error"])
    print()


if __name__ == "__main__":
    main()
