"""liuyao 提示词构造：只整理既定结果，不发起网络请求。"""

def _liuyao_facts_block(r, lite=False):
    """把六爻起卦+装卦+分析整理成事实清单（卦象为 ground truth）。

    lite=True（速览版）跳过末尾的「干支历参考」长表——速览不断精确应期，省去这段
    可显著缩短本地 CPU 的 prompt 处理耗时。
    """
    d = r["date"]
    ben = r["ben"]
    lines = [
        f"占问类别：{r['category_label']}（用神：{r['analysis']['yong_shen']['note']}）",
        f"问题：{r['question'] or '（未具体提问，做综合论断）'}",
        f"起卦时间：{d['year']}-{d['month']:02d}-{d['day']:02d}；月建{d['month_zhi']}、"
        f"日辰{d['day_ganzhi']}、旬空{''.join(d['xunkong'])}",
        f"本卦：{ben['name']}（{ben['palace']}宫·{ben['palace_wx']}·{ben['pos_name']}），"
        f"世在{ben['shi']}爻、应在{ben['ying']}爻"
        f"{'，为六冲卦' if ben['is_liuchong'] else ''}",
    ]
    if ben.get("gua_ci"):
        lines.append(f"本卦卦辞：{ben['gua_ci']}")
    if r["bian"]:
        lines.append(f"变卦：{r['bian']['name']}（{r['bian']['palace']}宫）"
                     f"{'，变卦六冲' if r['bian']['is_liuchong'] else ''}"
                     + (f"；变卦卦辞：{r['bian']['gua_ci']}" if r['bian'].get('gua_ci') else ""))
    else:
        lines.append("变卦：无（六爻安静）")
    lines.append("装卦（上爻→初爻）：")
    for ln in reversed(ben["lines"]):
        tag = "（世）" if ln["shi"] else ("（应）" if ln["ying"] else "")
        dong = ""
        if ln["moving"]:
            dong = f"〔{ln['line_name']}发动→变{ln.get('bian_zhi','')}{ln.get('bian_zhi_wx','')}" \
                   f"{('·'+ln['huitou']) if ln.get('huitou') else ''}〕"
        kong = "·旬空" if ln["kong"] else ""
        lines.append(f"  {ln['pos']}爻{tag} {ln['liushen']} {ln['gan']}{ln['zhi']}"
                     f"{ln['zhi_wx']} {ln['liuqin']}{kong} {dong}")
    yd = r["analysis"]["yong_shen"]["detail"]
    if yd:
        lines.append("用神旺衰：" + "；".join(
            f"{x['liuqin']}({x['pos']}爻{x['zhi']}{x['zhi_wx']})逢月建日辰为「{x['verdict']}」"
            f"{('·'+'·'.join(x['flags'])) if x['flags'] else ''}" for x in yd))
    cal = r.get("calendar")
    if cal and not lite:
        lines.append("【干支历参考（断应期、把地支换算成公历年月/生肖时只能据此，不得自行推算）】")
        lines.append("流年：" + "；".join(
            f"{y['year']}年={y['ganzhi']}（{y['sx']}年）" for y in cal["years"]))
        lines.append("流月：" + "；".join(
            f"{m['label']}={m['ganzhi']}" for m in cal["months"]))
    return "\n".join(lines)


def _liuyao_insights_block(r):
    comps = r["analysis"].get("structures", {}).get("compositions", [])
    if not comps:
        return ""
    out = ["【本卦关键看点（已按重要度排序，断卦须紧扣这些主线）】"]
    for i, c in enumerate(comps, 1):
        out.append(f"{i}. {c['name']}：{c['note']}")
    return "\n".join(out)


def build_liuyao_prompt(r, lite=False):
    """构造六爻解读的 system + user 提示。lite=True 为云端繁忙时的简短速览版。"""
    if lite:
        system = (
            "你是一名资深六爻预测师，精通京房纳甲筮法。给你的起卦、装卦、月建日辰与用神旺衰，"
            "都是程序按六爻规则精确算定的事实，你不得改动或重排任何卦象、爻、干支、六亲、世应。"
            "**当前云端繁忙，这是一份速览版**：围绕用神，只用简洁中文给出——"
            "（1）卦象速断：用神的六亲、旺衰（月建日辰生克）、是否旬空/发动，并据动爻对用神的生克与世应，"
            "3-4 句给出此事的吉凶倾向（要落到本卦具体爻位，不空谈）；"
            "（2）建议：2-3 条。**速览版不必推断精确应期**，全文不超过 280 字。"
            "结尾加一句『以上为速览，详细断卦版可稍后点重新解读获取，仅供参考娱乐，事在人为』。"
        )
        sections = "\n".join(["### 卦象速断", "### 建议"])
    else:
        system = (
            "你是一名资深六爻预测师，精通京房纳甲筮法。给你的起卦、装卦（纳甲、世应、六亲、六神、旬空）、"
            "月建日辰与用神旺衰，都是程序按六爻规则**精确算定的事实**，你不得改动或重排任何卦象、爻、干支、六亲、世应。"
            "请围绕**用神**写一份具体、不空泛的断卦，要求：\n"
            "1) 以『用神』为核心：先看用神的六亲归属、旺衰（月建日辰生克）、是否旬空/月破/发动，定事体根基的强弱；\n"
            "2) 再看**动爻**对用神的生克（生扶为吉、克制为凶）、回头生克、以及世应关系（世为求测者、应为对方/事体）；\n"
            "3) 必须用到本卦**特有**的爻位与组合（如『某爻官鬼发动克世』『用神妻财旬空待填实』），让结论只贴合这一卦；\n"
            "4) 有动爻则结合**变卦**讲事情走向（现状→结果）；可引用本卦/变卦的卦辞或动爻爻辞作经典印证（兜底）；\n"
            "5) 给出**具体、可落地的判断与建议**（含大致应期方向，如逢某地支之月日填实/冲动），不下绝对铁口；\n"
            "6) 适度使用『倾向/多主/宜/恐』等措辞；结尾加一句『以上为基于卦象符号的推演，仅供参考娱乐，事在人为』。\n"
            "※ 关键约束：凡把地支/干支换算成**公历年月或生肖**（如某年是何生肖、某月干支为何），"
            "**只能查阅事实里的『干支历参考』表**，严禁凭记忆或自行推算；表中未列出的年月，"
            "一律用干支或地支表述（如『逢寅卯之年月』『至申酉之期』），绝不臆造公历年份或生肖。"
        )
        sections = "\n".join(["### 卦象总断", "### 用神与动爻", "### 走向与建议"])
    insights = _liuyao_insights_block(r)
    user = ((insights + "\n\n" if insights else "")
            + f"【卦象事实】\n{_liuyao_facts_block(r, lite=lite)}\n\n"
            + f"请据上，按如下小节断卦（用 Markdown 小标题，紧扣关键看点与所问之事）：\n{sections}\n")
    return system, user
