"""运行方式：在 Mystery 目录执行 python -m examples.quickstart。"""
from datetime import datetime
import json

from mystery.bazi import calculate_bazi
from mystery.astrology import cast as cast_astrology
from mystery.liuyao import cast as cast_liuyao
from mystery.liuyao import draw as draw_liuyao
from mystery.tarot import draw, replay as replay_tarot
from mystery.randomness import interaction_evidence
from mystery.solar_time import to_true_solar_time
from mystery.answers import draw_answer
from mystery.llm.prompts import build_prompt


def main():
    """演示全部本地算法及离线提示词构造，不调用 AI。"""
    bazi = calculate_bazi(1990, 6, 15, 12, 30, longitude=116.41)
    astro = cast_astrology(1990, 6, 15, 12, 30, 39.90, 116.41)
    liuyao = cast_liuyao([6, 7, 8, 9, 7, 8], question="近期工作如何？",
                        category="career", date={"year": 2026, "month": 10, "day": 15, "hour": 12})
    # 示例输入由调用者提供；本包不会主动采集鼠标、IP或设备信息。
    evidence = interaction_evidence([
        {"x": 0.2, "y": 0.8, "t_ms": 0},
        {"x": 0.7, "y": 0.3, "t_ms": 83.5},
    ], app_version="0.2.1")
    tarot = draw("three", question="当前应该关注什么？", interaction=evidence)
    assert replay_tarot(tarot["replay"], question=tarot["question"]) == tarot
    auto_liuyao = draw_liuyao(date={"year": 2026, "month": 10, "day": 15, "hour": 12},
                             interaction=evidence)
    _, correction = to_true_solar_time(datetime(1990, 6, 15, 12, 30), 116.41,
                                       tz_name="Asia/Shanghai")
    system, user = build_prompt(bazi)
    print(json.dumps({
        "八字": bazi["summary"], "八字分析字段": list(bazi["analysis"]),
        "星盘大三件": astro["analysis"]["big_three"],
        "六爻": liuyao["ben"]["name"],
        "六爻自动三钱": auto_liuyao["tosses"],
        "塔罗": [entry["card"]["cn"] for entry in tarot["cards"]],
        "随机来源": tarot["random"], "排盘时间": bazi["time"],
        "真太阳时": correction, "答案之书": draw_answer("试试？"),
        "离线提示词字数": len(system) + len(user),
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
