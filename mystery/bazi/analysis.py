"""
八字分析层（第 2 层：结构化判断，纯规则，零 LLM）

本模块把排盘得到的符号（四柱干支/藏干/十神）按古籍规则做确定性推断：
  - 旺衰量化与喜用神（扶抑派加权计分 + 调候参考）
  - 格局（月令透干定格）
  - 刑冲合害（天干五合冲、地支六合/三合/三会/六冲/三刑/六害）
  - 神煞（贵人/文昌/桃花/驿马/华盖/将星/羊刃/禄神 等查表）
  - 大运吉凶（大运五行与喜忌的生克）

设计说明：
  * 旺衰/喜用神属「扶抑派」一种量化实现，权重可调；命理流派不唯一，
    此处给出透明、可复算的结论，而非唯一真理。
  * 十神分类直接复用排盘层（lunar EightChar）已算出的十神字符串，保证一致。
  * 入参为 mystery.bazi.calculate_bazi() 返回的 chart 字典。
"""

# ── 基础常量 ────────────────────────────────────────────────────────────
TIAN_GAN = ["甲", "乙", "丙", "丁", "戊", "己", "庚", "辛", "壬", "癸"]
DI_ZHI = ["子", "丑", "寅", "卯", "辰", "巳", "午", "未", "申", "酉", "戌", "亥"]

GAN_WUXING = {
    "甲": "木", "乙": "木", "丙": "火", "丁": "火", "戊": "土",
    "己": "土", "庚": "金", "辛": "金", "壬": "水", "癸": "水",
}
GAN_YINYANG = {  # 阳=True
    "甲": True, "乙": False, "丙": True, "丁": False, "戊": True,
    "己": False, "庚": True, "辛": False, "壬": True, "癸": False,
}
ZHI_WUXING = {
    "子": "水", "丑": "土", "寅": "木", "卯": "木", "辰": "土", "巳": "火",
    "午": "火", "未": "土", "申": "金", "酉": "金", "戌": "土", "亥": "水",
}

# 五行生克
SHENG = {"木": "火", "火": "土", "土": "金", "金": "水", "水": "木"}  # X 生 SHENG[X]
KE = {"木": "土", "土": "水", "水": "火", "火": "金", "金": "木"}      # X 克 KE[X]

# 十神 → 五大类
SHISHEN_CATEGORY = {
    "比肩": "比劫", "劫财": "比劫",
    "正印": "印", "偏印": "印",
    "食神": "食伤", "伤官": "食伤",
    "正财": "财", "偏财": "财",
    "正官": "官杀", "七杀": "官杀",
    "日主": "日主",
}

PILLAR_LABELS = {"year": "年", "month": "月", "day": "日", "hour": "时"}

# ── 天干关系 ────────────────────────────────────────────────────────────
GAN_WUHE = {  # 天干五合 → 合化五行
    frozenset(["甲", "己"]): "土", frozenset(["乙", "庚"]): "金",
    frozenset(["丙", "辛"]): "水", frozenset(["丁", "壬"]): "木",
    frozenset(["戊", "癸"]): "火",
}
GAN_CHONG = [  # 天干相冲
    frozenset(["甲", "庚"]), frozenset(["乙", "辛"]),
    frozenset(["丙", "壬"]), frozenset(["丁", "癸"]),
]

# ── 地支关系 ────────────────────────────────────────────────────────────
ZHI_LIUHE = {  # 地支六合 → 合化五行
    frozenset(["子", "丑"]): "土", frozenset(["寅", "亥"]): "木",
    frozenset(["卯", "戌"]): "火", frozenset(["辰", "酉"]): "金",
    frozenset(["巳", "申"]): "水", frozenset(["午", "未"]): "土",
}
ZHI_SANHE = {  # 三合局
    frozenset(["申", "子", "辰"]): "水", frozenset(["亥", "卯", "未"]): "木",
    frozenset(["寅", "午", "戌"]): "火", frozenset(["巳", "酉", "丑"]): "金",
}
ZHI_SANHUI = {  # 三会方
    frozenset(["寅", "卯", "辰"]): "木", frozenset(["巳", "午", "未"]): "火",
    frozenset(["申", "酉", "戌"]): "金", frozenset(["亥", "子", "丑"]): "水",
}
ZHI_LIUCHONG = [  # 六冲
    frozenset(["子", "午"]), frozenset(["丑", "未"]), frozenset(["寅", "申"]),
    frozenset(["卯", "酉"]), frozenset(["辰", "戌"]), frozenset(["巳", "亥"]),
]
ZHI_LIUHAI = [  # 六害
    frozenset(["子", "未"]), frozenset(["丑", "午"]), frozenset(["寅", "巳"]),
    frozenset(["卯", "辰"]), frozenset(["申", "亥"]), frozenset(["酉", "戌"]),
]
# 三刑（无恩之刑 寅巳申、持势之刑 丑戌未）、相刑（子卯无礼）、自刑（辰午酉亥）
ZHI_SANXING = [["寅", "巳", "申"], ["丑", "戌", "未"]]
ZHI_XIANGXING = [frozenset(["子", "卯"])]
ZHI_ZIXING = ["辰", "午", "酉", "亥"]

# ── 神煞表 ──────────────────────────────────────────────────────────────
# 天乙贵人（按日干）：甲戊庚牛羊，乙己鼠猴乡，丙丁猪鸡位，壬癸兔蛇藏，六辛逢马虎
TIANYI_GUIREN = {
    "甲": ["丑", "未"], "戊": ["丑", "未"], "庚": ["丑", "未"],
    "乙": ["子", "申"], "己": ["子", "申"],
    "丙": ["亥", "酉"], "丁": ["亥", "酉"],
    "壬": ["卯", "巳"], "癸": ["卯", "巳"],
    "辛": ["午", "寅"],
}
# 文昌贵人（按日干）
WENCHANG = {
    "甲": "巳", "乙": "午", "丙": "申", "丁": "酉", "戊": "申",
    "己": "酉", "庚": "亥", "辛": "子", "壬": "寅", "癸": "卯",
}
# 禄神（按日干）
LUSHEN = {
    "甲": "寅", "乙": "卯", "丙": "巳", "丁": "午", "戊": "巳",
    "己": "午", "庚": "申", "辛": "酉", "壬": "亥", "癸": "子",
}
# 羊刃（按日干，阳干临官前一位/帝旺）
YANGREN = {"甲": "卯", "丙": "午", "戊": "午", "庚": "酉", "壬": "子"}
# 桃花/驿马/华盖/将星（按年支或日支所属三合局）
_SANHE_GROUP = {
    "申": "申子辰", "子": "申子辰", "辰": "申子辰",
    "寅": "寅午戌", "午": "寅午戌", "戌": "寅午戌",
    "巳": "巳酉丑", "酉": "巳酉丑", "丑": "巳酉丑",
    "亥": "亥卯未", "卯": "亥卯未", "未": "亥卯未",
}
TAOHUA = {"申子辰": "酉", "寅午戌": "卯", "巳酉丑": "午", "亥卯未": "子"}
YIMA = {"申子辰": "寅", "寅午戌": "申", "巳酉丑": "亥", "亥卯未": "巳"}
HUAGAI = {"申子辰": "辰", "寅午戌": "戌", "巳酉丑": "丑", "亥卯未": "未"}
JIANGXING = {"申子辰": "子", "寅午戌": "午", "巳酉丑": "酉", "亥卯未": "卯"}

# ── 长生十二宫（日主在各地支的状态，用于通根强度）────────────────────────
_CHANG_SHENG_STATES = ["长生", "沐浴", "冠带", "临官", "帝旺",
                       "衰", "病", "死", "墓", "绝", "胎", "养"]
_CHANG_SHENG_START = {  # 各天干长生所在地支；阳干顺行、阴干逆行
    "甲": ("亥", 1), "丙": ("寅", 1), "戊": ("寅", 1), "庚": ("巳", 1), "壬": ("申", 1),
    "乙": ("午", -1), "丁": ("酉", -1), "己": ("酉", -1), "辛": ("子", -1), "癸": ("卯", -1),
}
# 各长生状态的通根强度权重（临官帝旺长生为强根）
_STATE_WEIGHT = {
    "长生": 1.0, "沐浴": 0.3, "冠带": 0.6, "临官": 1.1, "帝旺": 1.2,
    "衰": 0.4, "病": 0.3, "死": 0.2, "墓": 0.5, "绝": 0.1, "胎": 0.3, "养": 0.5,
}


def _chang_sheng_state(gan, zhi):
    """日主天干在某地支的长生十二宫状态"""
    start_zhi, direction = _CHANG_SHENG_START[gan]
    base = DI_ZHI.index(start_zhi)
    offset = (DI_ZHI.index(zhi) - base) * direction % 12
    return _CHANG_SHENG_STATES[offset]


# ── 调候用神（穷通宝鉴主用神参考，按日主 × 月支）────────────────────────
# 仅取广为引用的「主调候用神」，作为参考，与扶抑结论并列展示。
TIAO_HOU = {
    "甲": {"寅": "丙癸", "卯": "庚丙", "辰": "庚丁壬", "巳": "癸丁", "午": "癸丁",
           "未": "癸丁庚", "申": "庚丁壬", "酉": "庚丁丙", "戌": "庚甲丁壬", "亥": "庚丁丙",
           "子": "丁庚丙", "丑": "丁庚丙"},
    "乙": {"寅": "丙癸", "卯": "丙癸", "辰": "癸丙戊", "巳": "癸", "午": "癸丙",
           "未": "癸丙", "申": "丙癸己", "酉": "癸丙丁", "戌": "癸辛", "亥": "丙戊",
           "子": "丙", "丑": "丙"},
    "丙": {"寅": "壬庚", "卯": "壬己", "辰": "壬甲", "巳": "壬庚癸", "午": "壬庚",
           "未": "壬庚", "申": "壬戊", "酉": "壬癸", "戌": "甲壬", "亥": "甲戊庚壬",
           "子": "壬戊己", "丑": "壬甲"},
    "丁": {"寅": "甲庚", "卯": "庚甲", "辰": "甲庚", "巳": "甲庚", "午": "壬庚癸",
           "未": "甲壬庚", "申": "甲庚丙戊", "酉": "甲庚丙戊", "戌": "甲庚戊", "亥": "甲庚",
           "子": "甲庚", "丑": "甲庚"},
    "戊": {"寅": "丙甲癸", "卯": "丙甲癸", "辰": "甲丙癸", "巳": "甲丙癸", "午": "壬甲丙",
           "未": "癸丙甲", "申": "丙癸甲", "酉": "丙癸", "戌": "甲丙癸", "亥": "甲丙",
           "子": "丙甲", "丑": "丙甲"},
    "己": {"寅": "丙庚甲", "卯": "甲癸丙", "辰": "丙癸甲", "巳": "癸丙", "午": "癸丙",
           "未": "癸丙", "申": "丙癸", "酉": "丙癸", "戌": "甲丙癸", "亥": "丙甲戊",
           "子": "丙甲戊", "丑": "丙甲戊"},
    "庚": {"寅": "丙甲戊", "卯": "丁甲丙", "辰": "甲丁壬癸", "巳": "壬戊丙", "午": "壬癸",
           "未": "丁甲", "申": "丁甲", "酉": "丁甲丙", "戌": "甲壬", "亥": "丁丙",
           "子": "丁丙甲", "丑": "丙丁甲"},
    "辛": {"寅": "己壬庚", "卯": "壬甲", "辰": "壬甲", "巳": "壬甲癸", "午": "壬己癸",
           "未": "壬庚甲", "申": "壬甲戊", "酉": "壬甲", "戌": "壬甲", "亥": "壬丙",
           "子": "丙戊壬", "丑": "丙壬戊"},
    "壬": {"寅": "庚丙戊", "卯": "戊辛庚", "辰": "甲庚", "巳": "壬辛庚癸", "午": "癸庚辛",
           "未": "辛甲", "申": "戊丁", "酉": "甲庚", "戌": "甲丙", "亥": "戊庚丙",
           "子": "戊丙", "丑": "丙丁甲"},
    "癸": {"寅": "辛丙", "卯": "庚辛", "辰": "丙辛甲", "巳": "辛", "午": "庚壬癸辛",
           "未": "庚辛壬癸", "申": "丁", "酉": "辛丙", "戌": "辛甲壬癸", "亥": "庚辛戊丁",
           "子": "丙辛", "丑": "丙丁"},
}


# ── 引擎：旺衰量化 + 喜用神 ──────────────────────────────────────────────
# 各柱地支基础权重（月令当权最重，日支坐下次之）
_BRANCH_WEIGHT = {"year": 1.0, "month": 2.0, "day": 1.5, "hour": 1.0}
# 藏干按 本气/中气/余气 递减
_HIDE_WEIGHT = [1.0, 0.5, 0.3]

# 旺衰可信度检测：用三套代表不同流派的权重预设各算一次，看结论是否一致
STRENGTH_PRESETS = [
    {"name": "重月令派", "desc": "月令当权、得令即旺（子平传统）",
     "weight": {"year": 1.0, "month": 3.0, "day": 1.5, "hour": 1.0}},
    {"name": "均衡派", "desc": "月令偏重但兼顾各柱（折中，系统默认）",
     "weight": {"year": 1.0, "month": 2.0, "day": 1.5, "hour": 1.0}},
    {"name": "通盘派", "desc": "弱化月令、重通盘通根",
     "weight": {"year": 1.2, "month": 1.5, "day": 1.3, "hour": 1.2}},
]


def _element_relation(dm_wx, other_wx):
    """other_wx 相对日主五行的归类：同/印/食伤/财/官杀"""
    if other_wx == dm_wx:
        return "比劫"
    if SHENG[other_wx] == dm_wx:
        return "印"
    if SHENG[dm_wx] == other_wx:
        return "食伤"
    if KE[dm_wx] == other_wx:
        return "财"
    if KE[other_wx] == dm_wx:
        return "官杀"
    return "?"


def _strength(chart, branch_weight=None):
    """日主旺衰加权量化，返回结论字典。branch_weight 可传入流派权重预设。"""
    branch_weight = branch_weight or _BRANCH_WEIGHT
    pillars = chart["pillars"]
    dm = chart["day_master"]
    dm_wx = GAN_WUXING[dm]

    friend = 0.0  # 同党：比劫 + 印
    foe = 0.0     # 异党：食伤 + 财 + 官杀
    detail = {"比劫": 0.0, "印": 0.0, "食伤": 0.0, "财": 0.0, "官杀": 0.0}

    # 天干（日主本身不计入帮扶力量）
    for key in ("year", "month", "day", "hour"):
        if key == "day":
            continue
        gan = pillars[key]["gan"]
        rel = _element_relation(dm_wx, GAN_WUXING[gan])
        if rel in detail:
            detail[rel] += 1.0

    # 地支藏干（按通根强度 × 柱权重）
    for key in ("year", "month", "day", "hour"):
        base = branch_weight[key]
        for i, hg in enumerate(pillars[key]["hide_gan"]):
            w = base * _HIDE_WEIGHT[i] if i < len(_HIDE_WEIGHT) else base * 0.3
            rel = _element_relation(dm_wx, GAN_WUXING[hg])
            if rel in detail:
                detail[rel] += w

    friend = detail["比劫"] + detail["印"]
    foe = detail["食伤"] + detail["财"] + detail["官杀"]
    total = friend + foe
    ratio = friend / total if total else 0.5

    if ratio >= 0.62:
        label = "身强" if ratio < 0.75 else "身旺（太强）"
    elif ratio <= 0.38:
        label = "身弱" if ratio > 0.25 else "身衰（太弱）"
    else:
        label = "中和"

    # 月令是否得令（月支本气相对日主）
    month_main = pillars["month"]["hide_gan"][0]
    de_ling = _element_relation(dm_wx, GAN_WUXING[month_main]) in ("比劫", "印")

    return {
        "day_master": dm, "day_master_wx": dm_wx,
        "friend_score": round(friend, 2), "foe_score": round(foe, 2),
        "ratio": round(ratio, 3), "label": label,
        "de_ling": de_ling,
        "month_state": _chang_sheng_state(dm, pillars["month"]["zhi"]),  # 日主坐月令长生状态
        "day_state": _chang_sheng_state(dm, pillars["day"]["zhi"]),      # 日主坐日支状态
        "detail": {k: round(v, 2) for k, v in detail.items()},
    }


def _xi_ji(dm, strong):
    """按强弱取喜忌五行（纯函数，供旺衰与可信度检测复用）"""
    dm_wx = GAN_WUXING[dm]
    same = dm_wx
    yin = next(k for k, v in SHENG.items() if v == dm_wx)   # 生我者
    shi = SHENG[dm_wx]                                       # 我生者
    cai = KE[dm_wx]                                          # 我克者
    guan = next(k for k, v in KE.items() if v == dm_wx)     # 克我者
    if strong:
        return [shi, cai, guan], [same, yin], "身强宜抑——喜 食伤/财/官杀，忌 比劫/印"
    return [yin, same], [shi, cai, guan], "身弱宜扶——喜 印/比劫，忌 食伤/财/官杀"


def _yong_shen(chart, strength):
    """喜用神：扶抑取用 + 调候参考"""
    dm = chart["day_master"]
    strong = strength["ratio"] >= 0.5
    xi, ji, method = _xi_ji(dm, strong)

    month_zhi = chart["pillars"]["month"]["zhi"]
    tiao_hou = TIAO_HOU.get(dm, {}).get(month_zhi, "")

    return {
        "strong": strong, "method": method,
        "xi_wuxing": xi, "ji_wuxing": ji,
        "tiao_hou": tiao_hou,
        "tiao_hou_note": f"{dm}日生{month_zhi}月，穷通宝鉴主调候用神「{tiao_hou}」" if tiao_hou else "",
    }


# 旺衰临界带：默认强弱比落在此区间，视为喜忌天然两可
_BORDERLINE_BAND = (0.44, 0.56)


def _strength_robustness(chart):
    """
    旺衰可信度检测（用户无需理解权重，看结论即可）：
      - 用三套代表不同流派的权重各算一次；
      - 任一流派给出相反喜忌（跨过 0.5），或默认强弱比贴近中点 → 判「临界」；
      - 否则「稳健」。临界时同时给出身强/身弱两套读法。
    """
    dm = chart["day_master"]
    runs = []
    for preset in STRENGTH_PRESETS:
        s = _strength(chart, preset["weight"])
        strong = s["ratio"] >= 0.5
        xi, ji, _ = _xi_ji(dm, strong)
        runs.append({
            "name": preset["name"], "desc": preset["desc"],
            "label": s["label"], "ratio": s["ratio"], "strong": strong,
            "xi_wuxing": xi, "ji_wuxing": ji,
        })

    default_ratio = runs[1]["ratio"]                      # 均衡派为默认代表
    diverge = len({r["strong"] for r in runs}) > 1        # 流派间喜忌反转
    near_mid = _BORDERLINE_BAND[0] <= default_ratio <= _BORDERLINE_BAND[1]

    xs, js, _ = _xi_ji(dm, True)
    xw, jw, _ = _xi_ji(dm, False)
    readings = {"strong": {"xi": xs, "ji": js}, "weak": {"xi": xw, "ji": jw}}

    if diverge or near_mid:
        verdict = "临界"
        if diverge:
            cause = "不同流派权重下结论反转"
        else:
            cause = f"强弱比 {default_ratio} 贴近中点 0.5"
        note = (f"此盘旺衰处于临界（{cause}）：按身强取用则喜「{'、'.join(xs)}」，"
                f"按身弱取用则喜「{'、'.join(xw)}」，两说喜忌相反。"
                f"宜两说并参，不宜把旺衰当唯一定论。")
    else:
        verdict = "稳健"
        side = "身强一侧" if runs[1]["strong"] else "身弱一侧"
        note = f"重月令 / 均衡 / 通盘三套算法均判为「{side}」，喜忌一致，结论可信度高。"

    return {"verdict": verdict, "note": note, "runs": runs, "readings": readings}


# ── 引擎：格局（含可信度检测）────────────────────────────────────────────
_QI_TIER = ["本气", "中气", "余气"]


def _ge_name(ss):
    """由十神名得格名（比劫归建禄/月劫）"""
    cat = SHISHEN_CATEGORY.get(ss, "")
    if cat == "比劫":
        return "建禄格" if ss == "比肩" else "月劫格"
    return f"{ss}格" if ss else "未定格"


def _pattern(chart):
    """
    月令透干定格，并自动检测格局可信度（明确 / 可议）。

    争议来源（与旺衰可信度同思路，用户无需懂细节，看结论 + 候选即可）：
      - 月令多个藏干透出 → 多个候选格（主格取本气/最得力，余为兼格）
      - 月令本气未透、由中/余气透出 → 子平派取透出之神为格，传统派仍以本气论，两说并存
      - 月令为比劫（建禄/月劫）→ 特殊格，取用须另议
      - 月令藏干全不透 → 格局不显，力量虚
    """
    month = chart["pillars"]["month"]
    gans = [chart["pillars"][k]["gan"] for k in ("year", "month", "day", "hour")]
    hide = month["hide_gan"]
    shishen_zhi = month["shishen_zhi"]
    ben_qi = hide[0] if hide else ""
    ben_ss = shishen_zhi[0] if shishen_zhi else ""

    # 月令藏干透出情况
    transparent = []  # [(tier_name, hidden_gan, 十神, 格名)]
    for i, hg in enumerate(hide):
        if hg in gans:
            ss = shishen_zhi[i] if i < len(shishen_zhi) else ""
            transparent.append((_QI_TIER[i] if i < len(_QI_TIER) else "余气", hg, ss, _ge_name(ss)))

    candidates = []   # 候选格读法
    ben_is_bijie = SHISHEN_CATEGORY.get(ben_ss, "") == "比劫"
    # 可议仅保留「格名本身有分歧」的真争议；兼格/特殊/格虚均归明确并以提示说明
    non_bijie_trans = [(t, hg, ss, g) for (t, hg, ss, g) in transparent
                       if SHISHEN_CATEGORY.get(ss, "") != "比劫"]

    if ben_is_bijie:
        # 月令逢日主禄/劫（建禄/月劫）
        name = _ge_name(ben_ss)
        by = f"月令本气{ben_qi}为日主{('禄' if ben_ss == '比肩' else '劫')}"
        candidates.append({"name": name, "basis": by})
        if non_bijie_trans:
            # 与透出之财官并存 → 真争议（建禄月劫格 vs 以透出神论格）
            verdict = "可议"
            for t, hg, ss, g in non_bijie_trans:
                candidates.append({"name": g, "basis": f"另有{t}{hg}透出（{ss}），一说以此论{g}"})
            note = "月令逢禄/劫：一说作建禄/月劫特殊格、取用另议；一说以透出之财官等论格，两说并存。"
        else:
            verdict = "明确"
            note = "月令为日主禄/劫，建禄/月劫格；比劫不另立财官格，取用须看调候与全局。"

    elif transparent:
        tier, hg, ss, gname = transparent[0]   # 主格取最先透出者（本气优先）
        name = gname
        by = f"月令{tier}{hg}透出（{ss}）"
        candidates.append({"name": name, "basis": by})
        if tier != "本气":
            # 本气未透、由中/余气定格 → 子平派 vs 传统派格名分歧，真争议
            verdict = "可议"
            candidates.append({"name": _ge_name(ben_ss),
                               "basis": f"传统派：月令本气{ben_qi}（{ben_ss}）虽未透，仍以本气论格"})
            note = f"月令本气{ben_qi}未透、由{tier}{hg}透出定格（子平派）；传统派仍以本气『{_ge_name(ben_ss)}』论，两说并存。"
        else:
            # 本气透出，主格清晰；多透则附兼格（不算争议）
            verdict = "明确"
            if len(transparent) > 1:
                for t2, hg2, ss2, g2 in transparent[1:]:
                    candidates.append({"name": g2, "basis": f"另有{t2}{hg2}透出（{ss2}），可作兼格并参"})
                note = "月令本气透出为主格，格局清晰；另有透出之神可作兼格参看。"
            else:
                note = "月令本气独透，格局清晰。"

    else:
        # 全不透 → 格虚，但以本气论格读法无分歧
        name = _ge_name(ben_ss)
        by = f"月令本气{ben_qi}（{ben_ss}）未透，以本气论"
        verdict = "明确"
        candidates.append({"name": name, "basis": by})
        note = "月令藏干均未透干，格局不显、力量较虚（仍以本气论），宜结合调候与全局判断。"

    return {
        "name": name, "by": by,
        "transparent": bool(transparent),
        "verdict": verdict,
        "candidates": candidates,
        "note": note,
    }


# ── 引擎：刑冲合害 ──────────────────────────────────────────────────────
def _branch_relations(chart):
    """地支之间的六合/三合/三会/六冲/三刑/六害；天干五合/冲"""
    keys = ["year", "month", "day", "hour"]
    zhis = {k: chart["pillars"][k]["zhi"] for k in keys}
    gans = {k: chart["pillars"][k]["gan"] for k in keys}
    zset = set(zhis.values())
    hits = []

    def pos(zhi_or_gan, src):
        return "".join(PILLAR_LABELS[k] for k in keys if src[k] == zhi_or_gan)

    # 天干五合 / 相冲
    for i in range(len(keys)):
        for j in range(i + 1, len(keys)):
            pair = frozenset([gans[keys[i]], gans[keys[j]]])
            if len(pair) == 2 and pair in GAN_WUHE:
                hits.append({"type": "天干五合", "items": list(pair),
                             "extra": f"合化{GAN_WUHE[pair]}",
                             "where": PILLAR_LABELS[keys[i]] + PILLAR_LABELS[keys[j]]})
            if pair in GAN_CHONG:
                hits.append({"type": "天干相冲", "items": list(pair), "extra": "",
                             "where": PILLAR_LABELS[keys[i]] + PILLAR_LABELS[keys[j]]})

    # 地支三会 / 三合（整局）
    for combo, wx in ZHI_SANHUI.items():
        if combo <= zset:
            hits.append({"type": "三会局", "items": list(combo), "extra": f"会{wx}局",
                         "where": "".join(pos(z, zhis) for z in combo)})
    for combo, wx in ZHI_SANHE.items():
        if combo <= zset:
            hits.append({"type": "三合局", "items": list(combo), "extra": f"合{wx}局",
                         "where": "".join(pos(z, zhis) for z in combo)})

    # 两两关系：六合/六冲/六害
    for i in range(len(keys)):
        for j in range(i + 1, len(keys)):
            a, b = zhis[keys[i]], zhis[keys[j]]
            pair = frozenset([a, b])
            w = PILLAR_LABELS[keys[i]] + PILLAR_LABELS[keys[j]]
            if len(pair) == 2 and pair in ZHI_LIUHE:
                hits.append({"type": "六合", "items": [a, b], "extra": f"合化{ZHI_LIUHE[pair]}", "where": w})
            if pair in ZHI_LIUCHONG:
                hits.append({"type": "六冲", "items": [a, b], "extra": "", "where": w})
            if pair in ZHI_LIUHAI:
                hits.append({"type": "六害", "items": [a, b], "extra": "", "where": w})
            if pair in ZHI_XIANGXING:
                hits.append({"type": "相刑", "items": [a, b], "extra": "子卯无礼之刑", "where": w})

    # 三刑（需三支俱全）与自刑
    for group in ZHI_SANXING:
        if set(group) <= zset:
            hits.append({"type": "三刑", "items": group, "extra": "",
                         "where": "".join(pos(z, zhis) for z in group)})
    for z in ZHI_ZIXING:
        where = [k for k in keys if zhis[k] == z]
        if len(where) >= 2:
            hits.append({"type": "自刑", "items": [z, z], "extra": "",
                         "where": "".join(PILLAR_LABELS[k] for k in where)})

    return hits


# ── 引擎：神煞 ──────────────────────────────────────────────────────────
def _shensha(chart):
    """以日干 / 年支 / 日支为主查常用神煞，标注落在哪些柱"""
    keys = ["year", "month", "day", "hour"]
    zhis = {k: chart["pillars"][k]["zhi"] for k in keys}
    day_gan = chart["day_master"]
    year_zhi = chart["pillars"]["year"]["zhi"]
    day_zhi = chart["pillars"]["day"]["zhi"]
    results = []

    def find(targets):
        if isinstance(targets, str):
            targets = [targets]
        return [PILLAR_LABELS[k] for k in keys if zhis[k] in targets]

    def add(name, targets, basis):
        where = find(targets)
        if where:
            results.append({"name": name, "where": "".join(where),
                            "zhi": targets if isinstance(targets, list) else [targets],
                            "basis": basis})

    add("天乙贵人", TIANYI_GUIREN.get(day_gan, []), "按日干")
    add("文昌贵人", WENCHANG.get(day_gan), "按日干")
    add("禄神", LUSHEN.get(day_gan), "按日干")
    if day_gan in YANGREN:
        add("羊刃", YANGREN[day_gan], "按日干")

    # 以年支与日支两套三合局各查一次（取并集去重）
    for base_zhi, basis in ((year_zhi, "按年支"), (day_zhi, "按日支")):
        grp = _SANHE_GROUP[base_zhi]
        add("桃花", TAOHUA[grp], basis)
        add("驿马", YIMA[grp], basis)
        add("华盖", HUAGAI[grp], basis)
        add("将星", JIANGXING[grp], basis)

    # 去重（同名同位置）
    seen, dedup = set(), []
    for r in results:
        sig = (r["name"], r["where"])
        if sig not in seen:
            seen.add(sig)
            dedup.append(r)
    return dedup


# ── 引擎：大运吉凶 ──────────────────────────────────────────────────────
def _da_yun_luck(chart, yong):
    """逐步大运：干支五行与喜忌的吻合度评吉凶"""
    xi = set(yong["xi_wuxing"])
    ji = set(yong["ji_wuxing"])
    out = []
    for d in chart["da_yun"]["list"]:
        gz = d["ganzhi"]
        if len(gz) < 2:
            continue
        gan_wx = GAN_WUXING.get(gz[0], "")
        zhi_wx = ZHI_WUXING.get(gz[1], "")
        score = 0
        for wx in (gan_wx, zhi_wx):
            if wx in xi:
                score += 1
            elif wx in ji:
                score -= 1
        verdict = "吉" if score > 0 else ("凶" if score < 0 else "平")
        out.append({**d, "gan_wx": gan_wx, "zhi_wx": zhi_wx, "verdict": verdict})
    return out


# ── 引擎：调候 / 扶抑 一致性 ─────────────────────────────────────────────
def _yong_shen_consistency(yong):
    """
    调候用神 与 扶抑喜忌 是否同向。
    扶抑看强弱、调候看寒暖燥湿，二者有时相左（如冬生身强喜泄，调候却急需火暖），
    此时不可单执一法。给出 一致/中性/冲突 提示，用户看结论即可。
    """
    tiao = yong.get("tiao_hou", "")
    if not tiao:
        return {"verdict": "不适用", "note": "暂无调候用神数据，仅以扶抑取用。"}
    xi, ji = set(yong["xi_wuxing"]), set(yong["ji_wuxing"])
    items = []
    for g in tiao:
        wx = GAN_WUXING.get(g)
        if wx:
            side = "喜" if wx in xi else ("忌" if wx in ji else "中")
            items.append({"gan": g, "wx": wx, "side": side})
    if not items:
        return {"verdict": "不适用", "note": "调候用神无法解析。"}

    primary = items[0]
    if primary["side"] == "喜":
        verdict = "一致"
        note = f"主调候用神{primary['gan']}（{primary['wx']}）正属扶抑喜用，两法同向，取用明确。"
    elif primary["side"] == "忌":
        verdict = "冲突"
        note = (f"主调候用神{primary['gan']}（{primary['wx']}）恰落扶抑忌神：寒暖调候与强弱取用相左。"
                f"此类盘多以调候为急、或两法并参，不宜单执扶抑喜忌。")
    else:
        verdict = "中性"
        note = f"主调候用神{primary['gan']}（{primary['wx']}）与扶抑喜忌无直接冲突，可并参。"
    return {"verdict": verdict, "primary": f"{primary['gan']}（{primary['wx']}）",
            "items": items, "note": note}


# ── 引擎：组合结构识别（成象）+ 关键看点加权 ─────────────────────────────
def _god_category_of_element(dm_wx, target_wx):
    """某五行相对日主的十神大类"""
    return _element_relation(dm_wx, target_wx)


def _parse_dt(s):
    """'YYYY-MM-DD HH:MM' → (date_str, hour_int)；失败返回 (None, None)"""
    try:
        d, t = s.split(" ")
        return d, int(t.split(":")[0])
    except (ValueError, AttributeError):
        return None, None


def _shi_chen_index(hour):
    """小时 → 时辰地支序（子=0）"""
    return ((hour + 1) // 2) % 12


def _structures(chart, strength, yong, pattern, relations, robustness, consistency):
    """
    识别组合结构（成象）并按重要度加权，给出「关键看点」。
    这是把零散符号连成象的一层——LLM 据此知道这盘该先读什么、怎么连。
    """
    dm = chart["day_master"]
    dm_wx = GAN_WUXING[dm]
    pillars = chart["pillars"]
    keys = ("year", "month", "day", "hour")

    # 透干十神（日柱天干为日主，不计）与全局十神大类
    trans_gods = []      # 透出的具体十神
    trans_cats = set()   # 透出的十神大类
    for k in keys:
        if k == "day":
            continue
        ss = pillars[k]["shishen_gan"]
        trans_gods.append(ss)
        if ss in SHISHEN_CATEGORY:
            trans_cats.add(SHISHEN_CATEGORY[ss])
    branch_gods = set()  # 地支藏干十神大类
    branch_specific = set()
    for k in keys:
        for ss in pillars[k]["shishen_zhi"]:
            branch_specific.add(ss)
            if ss in SHISHEN_CATEGORY:
                branch_gods.add(SHISHEN_CATEGORY[ss])
    all_cats = trans_cats | branch_gods
    trans_set = set(trans_gods)

    comps = []   # {name, note, weight}

    def add(name, note, weight):
        comps.append({"name": name, "note": note, "weight": weight})

    # 1) 真太阳时跨界（最该向命主交代的不稳点）
    ts = chart.get("true_solar")
    if ts:
        cd, ch = _parse_dt(ts["clock_time"])
        td, th = _parse_dt(ts["true_solar_time"])
        if cd and td:
            if cd != td:
                add("真太阳时跨日", f"经度/均时差校正 {ts['total_correction_min']} 分钟，"
                    f"使排盘时刻由钟表 {ts['clock_time']} 退到真太阳时 {ts['true_solar_time']}，"
                    f"跨过日界——日柱/时柱因此改变，是本盘最敏感处。", 3)
            elif _shi_chen_index(ch) != _shi_chen_index(th):
                add("真太阳时跨时辰", f"校正 {ts['total_correction_min']} 分钟使时辰改变"
                    f"（{ts['clock_time']}→{ts['true_solar_time']}），时柱临界。", 3)

    # 2) 三合 / 三会 / 六合成局 → 化出五行的十神属性
    for h in relations:
        if h["type"] in ("三合局", "三会局") or (h["type"] == "六合" and h.get("extra")):
            wx = h["extra"].replace("合", "").replace("会", "").replace("化", "").replace("局", "")
            if wx in SHENG:
                cat = _god_category_of_element(dm_wx, wx)
                cat_name = {"比劫": "比劫(帮身)", "印": "印(生身)", "食伤": "食伤(吐秀)",
                            "财": "财", "官杀": "官杀"}.get(cat, cat)
                add(f"{h['type']}化{wx}·{cat_name}",
                    f"{'/'.join(h['items'])} {h['type']}化{wx}（{h['where']}），"
                    f"对日主为{cat_name}，此{wx}成势远超单字之力。", 3 if h["type"] != "六合" else 1)

    # 3) 财多身弱 / 身强财弱
    weak = strength["ratio"] < 0.5
    has_sanhe_cai = any(c["name"].startswith(("三合局化", "三会局化")) and "财" in c["name"] for c in comps)
    cai_force = strength["detail"]["财"]
    bijie_force = strength["detail"]["比劫"]
    if weak and ("财" in all_cats) and (has_sanhe_cai or cai_force >= bijie_force * 0.8):
        add("财多身弱", "财星旺而日主偏弱，担财吃力——求财易耗身劳神，喜比劫帮身分担，忌再行财运。", 3)
    elif (not weak) and ("财" in all_cats) and cai_force < bijie_force * 0.5 and "比劫" in trans_cats:
        add("身强财弱·比劫夺财", "日主旺、比劫透而财弱，易因人破财或竞争夺利，喜食伤通关、官杀制劫。", 2)

    # 4) 杀印相生 / 官印相生
    if ("官杀" in trans_cats and "印" in trans_cats):
        sha = "七杀" if "七杀" in trans_set else "正官"
        add("杀印相生" if sha == "七杀" else "官印相生",
            f"{sha}与印同透，官杀生印、印化官杀而生身——压力/竞争可转为助力与名位，化煞为权。", 2)

    # 5) 食神制杀 / 伤官驾杀
    if ("食伤" in trans_cats) and ("七杀" in trans_set or "七杀" in branch_specific):
        shi = "食神" if "食神" in trans_set else "伤官"
        add(f"{shi}制杀", f"{shi}透而克制七杀，化煞为用——主有魄力、能压制压力，宜从事竞争/专业领域。", 2)

    # 6) 伤官见官（至少一方透）
    if ("伤官" in trans_set and "正官" in (trans_set | branch_specific)) or \
       ("正官" in trans_set and "伤官" in (trans_set | branch_specific)):
        add("伤官见官", "伤官与正官并见，主易生是非口舌、变动或与权威/规则冲突，需印或财通关化解。", 2)

    # 7) 食伤生财（才华变现）
    if ("食伤" in trans_cats) and ("财" in all_cats):
        add("食伤生财", "食伤透而生财，主以才华/技艺/表达变现，财源较活。", 1)

    # 8) 旺衰临界 / 调候冲突 / 格局可议（来自既有检测，纳入看点）
    if robustness["verdict"] == "临界":
        add("旺衰临界", robustness["note"], 3)
    if consistency.get("verdict") == "冲突":
        add("调候与扶抑相左", consistency["note"], 2)
    if pattern.get("verdict") == "可议":
        add("格局可议", pattern["note"], 1)

    comps.sort(key=lambda c: -c["weight"])
    highlights = [c["name"] for c in comps if c["weight"] >= 2][:6]
    return {"compositions": comps, "highlights": highlights}


# ── 总入口 ──────────────────────────────────────────────────────────────
def analyze_chart(chart):
    """对排盘结果做结构化分析，返回分析字典（纯规则，零 LLM）"""
    strength = _strength(chart)
    robustness = _strength_robustness(chart)
    yong = _yong_shen(chart, strength)
    consistency = _yong_shen_consistency(yong)
    pattern = _pattern(chart)
    relations = _branch_relations(chart)
    structures = _structures(chart, strength, yong, pattern, relations, robustness, consistency)
    return {
        "strength": strength,
        "strength_robustness": robustness,
        "yong_shen": yong,
        "yong_shen_consistency": consistency,
        "pattern": pattern,
        "relations": relations,
        "shensha": _shensha(chart),
        "da_yun_luck": _da_yun_luck(chart, yong),
        "structures": structures,
        "disclaimer": "旺衰/喜用属扶抑派量化实现，流派不一；结论为确定性复算结果，供参考。",
    }
