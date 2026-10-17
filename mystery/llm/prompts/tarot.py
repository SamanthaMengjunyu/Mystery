"""tarot 提示词构造：只整理既定结果，不发起网络请求。"""

def _tarot_facts_block(reading):
    """把抽牌结果 + 结构分析整理成喂给 LLM 的事实清单（牌面为 ground truth）"""
    a = reading["analysis"]
    lines = [
        f"牌阵：{reading['spread']['cn']}（{reading['spread']['count']}张）——{reading['spread']['desc']}",
        f"用户的问题：{reading['question'] or '（未具体提问，做综合指引）'}",
        "抽到的牌（位置 → 牌名·正逆位 → 该位置牌义）：",
    ]
    for c in reading["cards"]:
        pos = c["position"]
        orient = "逆位" if c["reversed"] else "正位"
        lines.append(f"  [{pos['name']}：{pos['desc']}] → {c['card']['cn']}（{c['card']['en']}）·{orient}"
                     f" → {c['meaning']}")
    stat = [f"大牌{a['major_count']}/小牌{a['minor_count']}", f"逆位{a['reversed_count']}张"]
    if a["dom_element"]:
        stat.append(f"主导元素{a['dom_element']}")
    if a["lack_element"]:
        stat.append(f"缺{a['lack_element']}")
    if a["court_count"]:
        stat.append(f"宫廷牌{a['court_count']}张")
    lines.append("整体结构：" + "，".join(stat))
    return "\n".join(lines)


def _tarot_insights_block(reading):
    """把第 2 层识别的关键看点按重要度排成主线，放在 prompt 最前"""
    comps = reading["analysis"].get("structures", {}).get("compositions", [])
    if not comps:
        return ""
    out = ["【本次牌面关键看点（已按重要度排序，解读须紧扣这些主线，不可泛泛而谈）】"]
    for i, c in enumerate(comps, 1):
        out.append(f"{i}. {c['name']}：{c['note']}")
    return "\n".join(out)


def build_tarot_prompt(reading, lite=False):
    """构造塔罗解读的 system + user 提示。lite=True 为云端繁忙时的简短速览版。"""
    if lite:
        system = (
            "你是一名资深塔罗解读师。给你的牌阵、抽到的每张牌及其正逆位，都是程序已经确定的事实，"
            "你绝不可改牌、换牌或改动任何牌的正逆位与既定牌义。"
            "**当前云端繁忙，这是一份速览版**：围绕用户的问题，只用简洁中文给出——"
            "（1）综合指引：紧扣最重要的 1-2 个关键看点与牌面整体，3-4 句点出这次牌面对所问之事的核心信息（要落到具体牌，不空谈）；"
            "（2）给你的建议：2-3 条具体、可落地的提醒。不必逐张展开，全文不超过 280 字。"
            "语气温和、给人力量；结尾加一句『以上为速览，逐张细读版可稍后点重新解读获取，路怎么走还是你说了算』。"
        )
        sections = "\n".join(["### 综合指引", "### 给你的建议"])
    else:
        system = (
            "你是一名资深塔罗解读师。给你的牌阵、抽到的每张牌及其正逆位，都是程序"
            "**已经确定的事实**，你绝不可改牌、不可换牌、不可改动任何一张牌的正逆位或既定牌义。"
            "你的任务是**围绕用户的问题**，把这几张牌读成一个连贯、具体、对当事人有用的故事，要求：\n"
            "1) 先抓住『关键看点』里靠前的主线（如大牌主导、某元素偏重、逆位偏多、多张宫廷牌、重复数字等）来定调；\n"
            "2) **逐个位置**解读：把每张牌的牌义结合它所在位置的含义和用户的问题来讲，"
            "不要脱离位置只背牌义，也不要脱离问题空谈；\n"
            "3) 把牌与牌**连起来**讲故事（如『过去的高塔崩塌，正是现在隐者愿意独处沉淀的原因』），"
            "点出牌面之间的因果与张力，而不是逐张孤立罗列；\n"
            "4) 逆位牌要读出『受阻/延迟/转向内在/尚未察觉』的意味，而非简单当成反义词；\n"
            "5) 给出**具体、可落地的行动建议或心态提醒**，让结论只贴合这次牌面与这个问题；\n"
            "6) 语气温和、给人力量，使用『牌面显示/倾向/或许/不妨』等措辞，"
            "明确传达塔罗是反思与启发的工具、不预言宿命、最终选择权在用户手中；\n"
            "7) 结尾加一句『以上为基于牌面符号的推演，仅供参考娱乐，路怎么走还是你说了算』。"
        )
        sections = "\n".join(["### 逐张牌解读", "### 综合指引", "### 给你的建议"])
    insights = _tarot_insights_block(reading)
    user = ((insights + "\n\n" if insights else "")
            + f"【牌面事实】\n{_tarot_facts_block(reading)}\n\n"
            + f"请据上，按如下小节解读（用 Markdown 小标题，紧扣关键看点与用户问题）：\n{sections}\n")
    return system, user
