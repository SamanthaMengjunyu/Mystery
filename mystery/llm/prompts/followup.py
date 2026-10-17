"""followup 提示词构造：只整理既定结果，不发起网络请求。"""

from .bazi import _facts_block, _key_insights_block
from .astrology import _astro_facts_block, _astro_insights_block
from .tarot import _tarot_facts_block, _tarot_insights_block
from .liuyao import _liuyao_facts_block, _liuyao_insights_block
from .ziwei import _ziwei_facts_block
from .jyotish import _jyotish_facts_block
from .meihua import _meihua_facts_block
from .lenormand import _lenormand_facts_block


_FOLLOWUP_META = {
    "meihua": {"role": "梅花易数解读师", "subject": "梅花问事卦",
               "immutable": "改动本互变卦、动爻或体用关系",
               "facts": _meihua_facts_block, "insights": lambda r: "",
               "extra": "不混用六爻纳甲；不把五行生克直接当必然吉凶，不编造外应和精确应期。"},
    "lenormand": {"role": "雷诺曼解读师", "subject": "雷诺曼牌阵",
                  "immutable": "更换牌、位置或顺序",
                  "facts": _lenormand_facts_block, "insights": lambda r: "",
                  "extra": "不使用塔罗正逆位；没有命中的组合规则须标为条件性解释，不冒充固定词典。"},
    "ziwei": {"role": "紫微斗数解读师", "subject": "紫微命盘",
              "immutable": "改动命身宫、星曜、四化或运限",
              "facts": _ziwei_facts_block, "insights": lambda r: "",
              "extra": "只用记录中的流派规则，未给出的流年流月不可编造；不混用其他术数。"},
    "jyotish": {"role": "印度占星Jyotish解读师", "subject": "印度占星命盘",
                "immutable": "改动恒星黄道位置、月宿、D1/D9或大运子运",
                "facts": _jyotish_facts_block, "insights": lambda r: "",
                "extra": "at_birth只表示出生时的大运，不是当前运势；不得混用热带西占或其他体系。"},
    "liuyao": {"role": "六爻预测师，精通京房纳甲筮法", "subject": "卦象",
               "immutable": "改卦、重排或更改任何卦象、爻、干支、六亲、世应、动变",
               "facts": lambda r: _liuyao_facts_block(r, lite=False),
               "insights": _liuyao_insights_block,
               "extra": ("※ 凡把地支/干支换算成公历年月或生肖（如断应期），只能查阅事实中的"
                         "『干支历参考』表，表中未列出的一律用干支/地支表述，绝不臆造公历年份或生肖。")},
    "tarot": {"role": "塔罗解读师", "subject": "牌面",
              "immutable": "改牌、换牌或更改任何一张牌的正逆位与既定牌义",
              "facts": _tarot_facts_block,
              "insights": _tarot_insights_block,
              "extra": ""},
    "bazi": {"role": "八字命理师", "subject": "命盘",
             "immutable": "改动或重排任何干支、旺衰、喜用、格局",
             "facts": _facts_block,
             "insights": _key_insights_block,
             "extra": ""},
    "astro": {"role": "占星师", "subject": "星盘",
              "immutable": "改动或重算任何行星位置、星座、宫位、相位",
              "facts": _astro_facts_block,
              "insights": _astro_insights_block,
              "extra": ("※ 宫位与上升高度依赖精确出生时间——若追问涉及宫位/上升相关结论，"
                        "时间不确定时须提示该结论需打折。")},
}


def _followup_ref_facts(module, result):
    """对照记录的事实块——比主记录精简（六爻略去干支历长表，仅作呼应对照而非断精确应期）。"""
    if module == "liuyao":
        return _liuyao_facts_block(result, lite=True)
    return _FOLLOWUP_META[module]["facts"](result)


def _followup_refs_block(module, refs):
    """把 @ 引用的同模块历史记录整理成『对照记录』块（事实 + 已有解读）。"""
    subject = _FOLLOWUP_META[module]["subject"]
    out = [f"【用户用 @ 选了以下历史{subject}记录，请把它们与本次结果**联合分析**"
           f"——指出异同、是否相互呼应/印证、走向是否一致；但不得更改其中任何已定结论】"]
    for i, ref in enumerate(refs, 1):
        out.append(f"〖对照记录{i}：{ref.get('label', '')}〗\n"
                   f"{_followup_ref_facts(module, ref['result'])}\n"
                   f"已有解读：{(ref.get('interpretation') or '（无）').strip()}")
    return "\n\n".join(out)


def build_followup_messages(module, result, interpretation, history, question,
                            refs=None, lite=False):
    """构造追问对话的 OpenAI messages：系统消息钉死本次事实+原解读，再接历史多轮与新问题。

    module: bazi/astro/ziwei/jyotish/liuyao/tarot/meihua/lenormand；result: 已确定的结果；
    interpretation: 已给出的解读全文；history: [{role, content}, ...] 既往对话；
    question: 本轮用户追问；refs: [{label, result, interpretation}, ...] @ 引用的同模块
    历史记录（联合分析对照组）。lite=True 仅令回答更简短（云端繁忙兜底），事实不缩水。
    """
    m = _FOLLOWUP_META[module]
    insights = m["insights"](result)
    facts = m["facts"](result)
    refs_block = _followup_refs_block(module, refs) if refs else ""
    system = (
        f"你是一名资深{m['role']}。下面是这次{m['subject']}的既定事实"
        f"与你此前给出的解读，全部是程序精确算定/已成文的事实，你不得{m['immutable']}。"
        f"用户会就这次结果继续追问，请**只依据**下面的{m['subject']}事实与已有解读来回答："
        f"紧扣本次具体的爻位/牌面，不另起新卦/新牌、不臆造未给出的信息；"
        f"措辞用『倾向/可能/宜/恐』等，不下绝对断语；回答简明、直接回应所问，必要时才展开。"
        + (("\n" + m["extra"]) if m["extra"] else "")
        + (("\n\n" + insights) if insights else "")
        + f"\n\n【本次{m['subject']}事实】\n{facts}"
        + f"\n\n【此前已给出的解读】\n{(interpretation or '（暂无完整解读，请据上面的事实作答）').strip()}"
        + (("\n\n" + refs_block) if refs_block else "")
        + ("\n\n（当前云端繁忙，请用尽量简短的话回答，控制在 200 字内。）" if lite else "")
    )
    messages = [{"role": "system", "content": system}]
    for turn in (history or []):
        role = turn.get("role")
        content = (turn.get("content") or "").strip()
        if role in ("user", "assistant") and content:
            messages.append({"role": role, "content": content})
    messages.append({"role": "user", "content": question})
    return messages
