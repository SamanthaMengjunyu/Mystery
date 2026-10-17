"""astrology 提示词构造：只整理既定结果，不发起网络请求。"""

ASTRO_DOMAINS = {
    "self": "性格与自我",
    "relationship": "情感与关系",
    "career": "事业与天赋",
    "growth": "人生课题与成长",
}


def _astro_facts_block(chart):
    """把星盘排盘 + 结构整理成事实清单"""
    a = chart["analysis"]
    pts = chart["points"]
    inp = chart.get("input") or {}
    if inp:
        # 关键：喂「当地出生时间」（用户所填）作主时间。chart['utc'] 是送瑞士星历做天文
        # 计算用的协调世界时（本地 −时区偏移），**不是出生时刻**——若把它当出生时间给 LLM，
        # 模型会拿 UTC 的时/日（如本地 00:29 被折成前一天 16:29）当真去断盘，造成困惑。
        birth_local = (f"{inp['year']}-{inp['month']:02d}-{inp['day']:02d} "
                       f"{inp['hour']:02d}:{inp['minute']:02d}")
        lines = [
            f"出生时间（当地，用户所填，断盘一律以此为准）：{birth_local}（时区 {inp.get('tz', 'Asia/Shanghai')}）",
            f"（内部折算的 UTC 为 {chart['utc']}，仅供天文排盘，**不是出生时刻**，"
            f"回答中凡提到出生时间一律用上面的当地时间 {birth_local}，切勿引用 UTC 的时/分/日）",
            f"宫制：{chart['house_system']}",
            f"太阳{chart['sun_sign']}、月亮{chart['moon_sign']}、上升{chart['asc_sign']}、中天{chart['mc_sign']}",
            "行星落点：",
        ]
    else:
        lines = [
            f"出生(UTC)：{chart['utc']}；宫制：{chart['house_system']}",
            f"太阳{chart['sun_sign']}、月亮{chart['moon_sign']}、上升{chart['asc_sign']}、中天{chart['mc_sign']}",
            "行星落点：",
        ]
    order = ["太阳", "月亮", "水星", "金星", "火星", "木星", "土星",
             "天王星", "海王星", "冥王星", "北交点", "上升", "中天"]
    for n in order:
        p = pts.get(n)
        if p:
            lines.append(f"  {n}：{p['sign']}{p['deg']:.1f}°·第{p['house']}宫"
                         f"{'·逆行' if p['retro'] else ''}（{p['element']}/{p['modality']}）")
    b = a["balance"]
    lines.append("元素：" + "，".join(f"{k}{v}" for k, v in b["element"].items())
                 + f"（主导{b['dom_element']}、缺{b['lack_element']}）")
    lines.append("三态：" + "，".join(f"{k}{v}" for k, v in b["modality"].items())
                 + f"（主导{b['dom_modality']}）")
    cr = a["chart_ruler"]
    lines.append(f"命主星：{cr['planet']}（{cr['placement']}）")
    if a["patterns"]:
        lines.append("相位格局：" + "；".join(f"{p['name']}({'/'.join(p.get('members', []))})"
                                          for p in a["patterns"]))
    if a["tight_aspects"]:
        lines.append("到日月升的紧密相位：" + "，".join(
            f"{t['p1']}{t['type']}{t['p2']}(差{t['orb']}°)" for t in a["tight_aspects"]))
    # 其余较紧相位（取前若干）
    others = [x for x in chart["aspects"] if x["orb"] < 3][:8]
    if others:
        lines.append("其他主要相位：" + "，".join(
            f"{x['p1']}{x['type']}{x['p2']}(差{x['orb']}°)" for x in others))
    if a["hemisphere"]["notes"]:
        lines.append("半球侧重：" + "；".join(a["hemisphere"]["notes"]))
    return "\n".join(lines)


def _astro_insights_block(chart):
    comps = chart["analysis"].get("structures", {}).get("compositions", [])
    if not comps:
        return ""
    out = ["【本盘关键看点（已按重要度排序，解读须紧扣这些主线）】"]
    for i, c in enumerate(comps, 1):
        out.append(f"{i}. {c['name']}：{c['note']}")
    return "\n".join(out)


def build_astro_prompt(chart, domains=None, lite=False):
    domains = domains or list(ASTRO_DOMAINS.keys())
    titles = [ASTRO_DOMAINS[d] for d in domains if d in ASTRO_DOMAINS]
    if lite:
        system = (
            "你是一名资深占星师。下面的『星盘数据』与『关键看点』已由瑞士星历精确排盘并做几何分析，"
            "是确定的事实，你不得改动或重算任何行星位置、星座、宫位、相位。"
            "**当前云端繁忙，这是一份速览版**：只用简洁中文给出——"
            "（1）综合结论：紧扣最重要的 1-2 个关键看点，3-4 句点出此盘核心特质（须用到本盘特有的落点/相位，不写套话）；"
            "（2）实用建议：2-3 条。全文不超过 280 字。"
            "结尾加一句『以上为速览，完整详细版可稍后点重新解读获取，仅供参考娱乐』。"
        )
        sections = "\n".join(["### 综合结论", "### 实用建议"])
    else:
        system = (
            "你是一名资深占星师。给你的『星盘数据』与『关键看点』已由瑞士星历精确排盘、并由程序做几何分析，"
            "是确定的事实，你不得改动或重新计算任何行星位置、星座、宫位、相位。"
            "请写出一份**具体、不空泛**的解读，要求：\n"
            "1) 先抓住『关键看点』靠前的主线（星群、相位格局、元素失衡、到日月升的紧密相位、大三件等）展开，不要逐条复述；\n"
            "2) 必须用到本盘**特有**的落点与相位（如『月亮在双子11宫刑火星』『命主星落某宫』），让结论只适用于这张盘；\n"
            "3) 把相互作用的因素连起来讲（如『太阳天秤逢土星刑，使自我表达受责任感压制』），点出因果，不罗列标签；\n"
            "4) 宫位与上升高度依赖精确出生时间——若数据含『出生时间敏感』看点，须提示时间不准时宫位结论需打折；\n"
            "5) 适度使用『偏向/可能/容易』等措辞，不下绝对断语；每个领域 3-5 句，言之有物；\n"
            "6) 结尾加一句『以上为基于星盘符号的推演，仅供参考娱乐』。"
        )
        sections = "\n".join(f"### {t}" for t in titles)
    insights = _astro_insights_block(chart)
    user = ((insights + "\n\n" if insights else "")
            + f"【星盘数据】\n{_astro_facts_block(chart)}\n\n"
            + f"请据上，按如下小节分别解读（用 Markdown 小标题，紧扣关键看点）：\n{sections}\n")
    return system, user
