"""python -m examples.new_charts — two new local chart entrances, no AI requests."""
import json

from mystery.ziwei import cast as cast_ziwei
from mystery.jyotish import cast as cast_jyotish
from mystery.llm.prompts import build_ziwei_prompt, build_jyotish_prompt


def main():
    ziwei = cast_ziwei(2000, 8, 16, 4, 0, "女", target_year=2026)
    jyotish = cast_jyotish(2000, 4, 28, 5, 50, 40.7, -74, "America/New_York")
    print(json.dumps({
        "紫微": {"概览": ziwei["summary"], "本命四化": ziwei["analysis"]["natal_mutagens"],
                 "宫数": len(ziwei["palaces"]), "大限数": len(ziwei["decadals"]),
                 "流年干支": ziwei["annual"]["heavenlyStem"] + ziwei["annual"]["earthlyBranch"]},
        "印占": {"概览": jyotish["summary"], "月宿": jyotish["analysis"]["moon_nakshatra"],
                 "出生时大运": jyotish["vimshottari"]["at_birth"],
                 "出生大运余额年": jyotish["vimshottari"]["birth_balance_years"]},
        "离线提示词字数": {"紫微": sum(map(len, build_ziwei_prompt(ziwei))),
                           "印占": sum(map(len, build_jyotish_prompt(jyotish)))},
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
