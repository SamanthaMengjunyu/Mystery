"""bazi 提示词构造：只整理既定结果，不发起网络请求。"""

DOMAINS = {
    "personality": "性格心性",
    "career": "事业财运",
    "relationship": "婚恋关系",
    "fortune": "大运流年走势",
}


def _facts_block(chart):
    """把第 1/2 层的确定性结论整理成喂给 LLM 的事实清单（纯数据）"""
    p = chart["pillars"]
    a = chart["analysis"]
    s = a["strength"]
    y = a["yong_shen"]

    def pillar_line(key, name):
        pi = p[key]
        return (f"{name}柱 {pi['gan']}{pi['zhi']}（{pi['gan_wx']}{pi['zhi_wx']}，"
                f"十神:{pi['shishen_gan']}，藏干:{''.join(pi['hide_gan'])}，"
                f"支藏十神:{'/'.join(pi['shishen_zhi'])}，纳音:{pi['nayin']}，星运:{pi['dishi']}）")

    lines = [
        f"性别：{chart['input']['gender']}",
        f"四柱：{chart['summary']}",
        pillar_line("year", "年"), pillar_line("month", "月"),
        pillar_line("day", "日"), pillar_line("hour", "时"),
        f"日主：{chart['day_master']}（{s['day_master_wx']}）",
        f"旺衰：{s['label']}（同党{s['friend_score']}/异党{s['foe_score']}，"
        f"{'得令' if s['de_ling'] else '失令'}，日主坐月令『{s['month_state']}』）",
        f"旺衰可信度：{a['strength_robustness']['verdict']}——{a['strength_robustness']['note']}",
        f"五行分布：" + "，".join(f"{k}{v}" for k, v in chart["wuxing_stats"].items()),
        f"喜用五行：{'、'.join(y['xi_wuxing'])}；忌神五行：{'、'.join(y['ji_wuxing'])}",
    ]
    if y.get("tiao_hou"):
        cons = a.get("yong_shen_consistency", {})
        lines.append(f"调候参考用神：{y['tiao_hou']}（与扶抑喜忌{cons.get('verdict', '')}：{cons.get('note', '')}）")
    pat = a["pattern"]
    ge_line = f"格局：{pat['name']}（{pat['by']}）；可信度：{pat.get('verdict', '')}"
    if pat.get("verdict") == "可议" and len(pat.get("candidates", [])) > 1:
        ge_line += "，候选格：" + " / ".join(c["name"] for c in pat["candidates"])
    lines.append(ge_line)

    if a["relations"]:
        rel = "；".join(f"{h['type']}{''.join(h['items'])}"
                        f"{'·'+h['extra'] if h['extra'] else ''}[{h['where']}]"
                        for h in a["relations"])
        lines.append(f"刑冲合害：{rel}")
    if a["shensha"]:
        ss = "；".join(f"{x['name']}[{x['where']}]" for x in a["shensha"])
        lines.append(f"神煞：{ss}")
    if a["da_yun_luck"]:
        dy = "，".join(f"{d['ganzhi']}({d['start_age']}岁起·{d['verdict']})"
                       for d in a["da_yun_luck"])
        lines.append(f"大运吉凶：{dy}")
    return "\n".join(lines)


def _key_insights_block(chart):
    """把第 2 层识别的成象/关键看点按重要度排成主线，放在 prompt 最前"""
    comps = chart["analysis"].get("structures", {}).get("compositions", [])
    if not comps:
        return ""
    out = ["【本盘关键看点（已按重要度排序，解读须紧扣这些主线，不可泛泛而谈）】"]
    for i, c in enumerate(comps, 1):
        out.append(f"{i}. {c['name']}：{c['note']}")
    return "\n".join(out)


def build_prompt(chart, domains=None, lite=False):
    """构造发给 LLM 的 system + user 提示。lite=True 为云端繁忙时的简短速览版。"""
    domains = domains or list(DOMAINS.keys())
    titles = [DOMAINS[d] for d in domains if d in DOMAINS]

    if lite:
        system = (
            "你是一名资深八字命理师。下面的『命盘数据』与『关键看点』已由程序精确排盘与分析，"
            "是确定的事实，你不得改动或重算任何干支、旺衰、喜用、格局。"
            "**当前云端繁忙，这是一份速览版**：只用简洁中文给出——"
            "（1）总体结论：紧扣最重要的 1-2 个关键看点，3-4 句点出此命主线与最突出的特点（须用到本盘特有的十神/组合，不写套话）；"
            "（2）实用建议：2-3 条具体、贴合本盘的建议。"
            "不要逐柱逐字段展开，全文不超过 280 字。"
            "结尾加一句『以上为速览，完整详细版可稍后点重新解读获取，仅供参考娱乐』。"
        )
        sections = "\n".join(["### 总体结论", "### 实用建议"])
    else:
        system = (
            "你是一名资深八字命理师。给你的『命盘数据』与『关键看点』已由程序按命理规则精确排盘与分析，"
            "是确定的事实，你不得改动或重新计算任何干支、旺衰、喜用、格局。"
            "你的任务是写出一份**具体、不空泛**的解读，要求：\n"
            "1) 先抓住『关键看点』里排在前面的主线（如真太阳时跨界、三合成局、财多身弱、杀印相生、调候冲突等），"
            "围绕它们展开，而不是逐条复述字段；\n"
            "2) 必须用到本盘**特有**的十神与组合结构（如食神制杀、杀印相生、某神煞临某柱），"
            "让结论只适用于这张盘、换一张盘就不成立；不要写放之四海皆准的套话；\n"
            "3) 把相互作用的符号连起来讲（如『七杀被食神制、又被偏印化』『三合财局使财远旺于日主』），点出因果，不要罗列标签；\n"
            "4) 旺衰可信度为『临界』或格局『可议』或调候与扶抑『冲突』时，必须如实点出该处有争议、两种取向都交代，不可只押一边；\n"
            "5) 适度使用『偏向/可能/宜』等措辞，不下绝对断语；每个领域 3-5 句，言之有物；\n"
            "6) 结尾加一句『以上为基于命理符号的推演，仅供参考娱乐』。"
        )
        sections = "\n".join(f"### {t}" for t in titles)
    insights = _key_insights_block(chart)
    user = (
        (insights + "\n\n" if insights else "")
        + f"【命盘数据】\n{_facts_block(chart)}\n\n"
        + f"请据上，按如下小节分别解读（用 Markdown 小标题，紧扣关键看点）：\n{sections}\n"
    )
    return system, user
