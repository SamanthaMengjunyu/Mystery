"""python -m examples.question_methods — new question methods, no AI requests."""
import json

from mystery.meihua import cast_numbers, cast_time, replay as replay_meihua
from mystery.lenormand import draw, replay as replay_lenormand
from mystery.llm.prompts import build_meihua_prompt, build_lenormand_prompt


def main():
    meihua = cast_numbers(34, 43, 1, question="下一轮合作需要关注什么？")
    timed = cast_time(2026, 10, 15, 12, question="当前沟通应如何推进？")
    cards = draw("five", question="合作中的沟通与约定需要关注什么？")
    assert replay_meihua(meihua["replay"]) == meihua
    assert replay_lenormand(cards["replay"]) == cards
    print(json.dumps({
        "梅花报数": {"概览": meihua["summary"], "体用": meihua["analysis"]},
        "梅花时间": {"概览": timed["summary"], "历法": timed["trace"]["calendar"]},
        "雷诺曼": {"概览": cards["summary"], "中心": cards["analysis"]["focus"]["card"]["cn"],
                   "相邻组合": cards["analysis"]["adjacent_pairs"]},
        "离线提示词字数": {"梅花": sum(map(len, build_meihua_prompt(meihua))),
                           "雷诺曼": sum(map(len, build_lenormand_prompt(cards)))},
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
