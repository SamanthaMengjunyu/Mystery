"""
塔罗牌静态数据（第 1 层 ground truth）—— 韦特体系 (Rider-Waite-Smith, RWS)

设计原则（与八字/星盘一致）：本层是**确定性事实**，牌库与牌义在此写死，
抽牌与解读都以此为准，LLM 不得改动牌义。

多体系预留：每张牌带 `deck` 字段（当前恒为 "rws"）；未来加托特/马赛或主题牌组时，
可在 DECKS 注册新牌库并按 deck 切换，上层抽牌/解读逻辑无需改动。

字段说明：
- id      牌唯一标识（major_00 / wands_01 / cups_11 …）
- num     序号（大牌 0-21；小牌 1-10，宫廷 11=侍从/12=骑士/13=王后/14=国王）
- arcana  "major"（大阿尔卡那）/ "minor"（小阿尔卡那）
- suit    花色 key（大牌为 None；小牌 wands/cups/swords/pentacles）
- cn/en   中英文牌名
- up      正位关键词（牌义 ground truth）
- rev     逆位关键词
- deck    所属牌组体系（多体系预留）
"""

DECK_SYSTEM = "rws"

# 四花色 → 中文名 / 元素 / 主题（小牌元素由花色决定；大牌不参与元素统计）
SUITS = {
    "wands": {"cn": "权杖", "element": "火", "theme": "行动·激情·事业动力"},
    "cups": {"cn": "圣杯", "element": "水", "theme": "情感·关系·直觉"},
    "swords": {"cn": "宝剑", "element": "风", "theme": "思想·冲突·决断"},
    "pentacles": {"cn": "钱币", "element": "土", "theme": "物质·金钱·现实"},
}

# 宫廷牌序号 → 中文（小牌 11-14）
COURT_CN = {11: "侍从", 12: "骑士", 13: "王后", 14: "国王"}

# 牌面图：公有领域韦特(RWS)原版扫描，存于 static/cards/。
# 命名：大牌 m00-m21；小牌花色前缀(c圣杯/w权杖/s宝剑/p钱币)+序号01-14。
# 来源 metabismuth/tarot-json（取自 data.totl.net，RWS 公有领域，350×600）。
_SUIT_IMG_PREFIX = {"wands": "w", "cups": "c", "swords": "s", "pentacles": "p"}


def _major(num, cn, en, up, rev):
    return {"id": f"major_{num:02d}", "num": num, "arcana": "major", "suit": None,
            "cn": cn, "en": en, "up": up, "rev": rev, "deck": DECK_SYSTEM,
            "img": f"m{num:02d}.jpg"}


def _minor(suit, num, cn, en, up, rev):
    return {"id": f"{suit}_{num:02d}", "num": num, "arcana": "minor", "suit": suit,
            "cn": cn, "en": en, "up": up, "rev": rev, "deck": DECK_SYSTEM,
            "img": f"{_SUIT_IMG_PREFIX[suit]}{num:02d}.jpg"}


# ── 大阿尔卡那 22 张 ───────────────────────────────────────────────
MAJOR = [
    _major(0, "愚者", "The Fool", "新的开始、冒险、纯真、自由、无限可能", "鲁莽、轻率、缺乏计划、逃避、犹豫不前"),
    _major(1, "魔术师", "The Magician", "行动力、创造、专注、资源齐备、心想事成", "操纵、欺骗、才华未用、意志涣散"),
    _major(2, "女祭司", "The High Priestess", "直觉、潜意识、神秘、内在智慧、静观", "压抑直觉、隐情、表里不一、迷失自我"),
    _major(3, "皇后", "The Empress", "丰盛、孕育、母性、感官、自然滋养", "依赖、创造受阻、过度照顾、内在空虚"),
    _major(4, "皇帝", "The Emperor", "权威、秩序、掌控、稳定、父性结构", "专制、僵化、控制欲、权力旁落"),
    _major(5, "教皇", "The Hierophant", "传统、信仰、教导、体制、规范", "反叛、打破常规、教条、形式主义"),
    _major(6, "恋人", "The Lovers", "爱、结合、关系、抉择、价值一致", "失衡、分歧、错误选择、诱惑"),
    _major(7, "战车", "The Chariot", "意志、胜利、前进、掌控方向、决心", "失控、方向迷失、受阻、逞强蛮干"),
    _major(8, "力量", "Strength", "内在力量、勇气、耐心、温柔的掌控、自信", "自我怀疑、软弱、急躁、情绪失控"),
    _major(9, "隐者", "The Hermit", "内省、独处、寻求真理、指引、智慧", "孤立、逃避、自我封闭、迷失方向"),
    _major(10, "命运之轮", "Wheel of Fortune", "转机、循环、命运、机遇、转折点", "厄运、失控、抗拒变化、坏运循环"),
    _major(11, "正义", "Justice", "公正、因果、责任、真相、平衡", "不公、逃避责任、偏颇、失衡"),
    _major(12, "倒吊人", "The Hanged Man", "暂停、牺牲、换位思考、放下、顺其自然", "拖延、无谓牺牲、僵局、固执抗拒"),
    _major(13, "死神", "Death", "结束、转变、重生、放下、蜕变", "抗拒改变、停滞、拖延、恐惧结束"),
    _major(14, "节制", "Temperance", "平衡、调和、耐心、中庸、疗愈", "失衡、极端、急躁、不协调"),
    _major(15, "恶魔", "The Devil", "束缚、欲望、执着、物质、上瘾", "挣脱束缚、觉醒、解脱、直面阴影"),
    _major(16, "高塔", "The Tower", "突变、崩塌、觉醒、旧结构瓦解、解放", "避免灾难、拖延崩塌、内在动荡、恐惧改变"),
    _major(17, "星星", "The Star", "希望、疗愈、灵感、信心、平静", "失望、信心动摇、迷茫、灵感枯竭"),
    _major(18, "月亮", "The Moon", "幻象、潜意识、不安、直觉、迷雾", "释放恐惧、真相浮现、走出困惑、压抑松动"),
    _major(19, "太阳", "The Sun", "喜悦、成功、活力、光明、温暖", "暂时阴霾、过度乐观、延迟的成功、失落"),
    _major(20, "审判", "Judgement", "觉醒、重生、召唤、总结、宽恕", "自我批判、逃避、悔恨、犹豫不决"),
    _major(21, "世界", "The World", "圆满、完成、整合、成就、新循环", "未完成、拖延、缺口、停滞不前"),
]

# ── 小阿尔卡那 56 张 ───────────────────────────────────────────────
# 权杖（火）
WANDS = [
    _minor("wands", 1, "权杖一", "Ace of Wands", "灵感、新机会、创造火花、潜能、动力", "动力不足、延迟、灵感枯竭、方向不明"),
    _minor("wands", 2, "权杖二", "Two of Wands", "规划、远见、抉择、掌控未来、扩张", "犹豫、计划受阻、恐惧未知、目光短浅"),
    _minor("wands", 3, "权杖三", "Three of Wands", "远见实现、扩展、等待回报、前瞻、合作", "延迟、计划受挫、短视、进展受阻"),
    _minor("wands", 4, "权杖四", "Four of Wands", "庆祝、和谐、稳定、归属、里程碑", "不稳定、过渡期、缺乏归属、延迟的庆祝"),
    _minor("wands", 5, "权杖五", "Five of Wands", "竞争、冲突、分歧、挑战、磨合", "避免冲突、内耗、化解分歧、紧张缓和"),
    _minor("wands", 6, "权杖六", "Six of Wands", "胜利、认可、成功、凯旋、自信", "失利、缺乏认可、自负、延迟的成功"),
    _minor("wands", 7, "权杖七", "Seven of Wands", "坚守、防御、捍卫立场、勇气、挑战", "退缩、不堪重负、放弃、招架不住"),
    _minor("wands", 8, "权杖八", "Eight of Wands", "迅速、进展、消息、行动、顺势而为", "延迟、受阻、混乱、操之过急"),
    _minor("wands", 9, "权杖九", "Nine of Wands", "坚韧、防备、最后考验、韧性、戒备", "力竭、偏执、固执、防御过度"),
    _minor("wands", 10, "权杖十", "Ten of Wands", "重担、责任、压力、坚持到底、超负荷", "卸下重担、放手、不堪重负、学会委派"),
    _minor("wands", 11, "权杖侍从", "Page of Wands", "热情、探索、新点子、好奇、跃跃欲试", "三分钟热度、方向不明、拖延、不成熟"),
    _minor("wands", 12, "权杖骑士", "Knight of Wands", "行动、冒险、热情、冲劲、魅力", "鲁莽、急躁、虎头蛇尾、受挫"),
    _minor("wands", 13, "权杖王后", "Queen of Wands", "自信、热情、魅力、独立、活力", "善妒、急躁、缺乏自信、控制欲"),
    _minor("wands", 14, "权杖国王", "King of Wands", "领导、远见、魄力、魅力、掌控", "专横、冲动、独断、暴躁"),
]
# 圣杯（水）
CUPS = [
    _minor("cups", 1, "圣杯一", "Ace of Cups", "新感情、爱、直觉涌现、喜悦、灵性", "情感封闭、空虚、压抑、单恋"),
    _minor("cups", 2, "圣杯二", "Two of Cups", "结合、爱情、伙伴、互惠、吸引", "失衡、分手、不和、关系紧张"),
    _minor("cups", 3, "圣杯三", "Three of Cups", "友谊、欢聚、庆祝、社群、支持", "过度放纵、八卦、疏离、三角关系"),
    _minor("cups", 4, "圣杯四", "Four of Cups", "冷漠、不满、沉思、错失、倦怠", "重新振作、接受、觉察机会、走出低潮"),
    _minor("cups", 5, "圣杯五", "Five of Cups", "失落、遗憾、悲伤、聚焦失去、哀悼", "接受、疗愈、放下、看见尚存的"),
    _minor("cups", 6, "圣杯六", "Six of Cups", "怀旧、纯真、童年、重逢、善意", "沉溺过去、无法放下、幼稚、该向前看"),
    _minor("cups", 7, "圣杯七", "Seven of Cups", "幻想、选择繁多、白日梦、诱惑、迷惑", "清醒、抉择、务实、看清现实"),
    _minor("cups", 8, "圣杯八", "Eight of Cups", "离开、放下、追寻更高意义、转身、觉醒", "害怕离开、停滞、逃避、犹豫不决"),
    _minor("cups", 9, "圣杯九", "Nine of Cups", "满足、愿望成真、幸福、享受、感恩", "表面满足、贪求、内在空虚、物欲"),
    _minor("cups", 10, "圣杯十", "Ten of Cups", "圆满、家庭幸福、和谐、情感丰盈、归属", "关系失和、价值错位、和谐破裂"),
    _minor("cups", 11, "圣杯侍从", "Page of Cups", "灵感讯息、浪漫、直觉、创意、温柔", "情绪化、不成熟、逃避、不切实际的幻想"),
    _minor("cups", 12, "圣杯骑士", "Knight of Cups", "浪漫、追求、理想主义、魅力、邀约", "善变、不切实际、失望、情绪用事"),
    _minor("cups", 13, "圣杯王后", "Queen of Cups", "共情、温柔、直觉、包容、疗愈", "情绪失衡、过度敏感、依赖、自我牺牲"),
    _minor("cups", 14, "圣杯国王", "King of Cups", "情感成熟、包容、平和、智慧、外柔内刚", "情绪压抑、操控、喜怒无常、冷漠"),
]
# 宝剑（风）
SWORDS = [
    _minor("swords", 1, "宝剑一", "Ace of Swords", "突破、清晰、真相、新想法、决断", "混乱、误判、思绪不清、滥用力量"),
    _minor("swords", 2, "宝剑二", "Two of Swords", "抉择两难、僵局、权衡、回避、暂时平衡", "优柔寡断、僵局打破、信息明朗、逃避"),
    _minor("swords", 3, "宝剑三", "Three of Swords", "心碎、痛苦、背叛、悲伤、分离", "疗愈、释怀、走出痛苦、宽恕"),
    _minor("swords", 4, "宝剑四", "Four of Swords", "休息、恢复、沉淀、暂停、疗养", "倦怠、被迫停滞、重新出发、内心不安"),
    _minor("swords", 5, "宝剑五", "Five of Swords", "冲突、失利、自私、争胜、代价", "和解、放下争执、悔悟、化干戈"),
    _minor("swords", 6, "宝剑六", "Six of Swords", "过渡、远行、离开困境、前行、疗愈之旅", "滞留、无法放下、受阻、重蹈覆辙"),
    _minor("swords", 7, "宝剑七", "Seven of Swords", "策略、欺瞒、独行、投机、隐瞒", "坦白、被揭穿、良心发现、改变策略"),
    _minor("swords", 8, "宝剑八", "Eight of Swords", "受困、自我设限、无力、束缚、恐惧", "解脱、突破限制、觉醒、重获自由"),
    _minor("swords", 9, "宝剑九", "Nine of Swords", "焦虑、失眠、恐惧、担忧、精神压力", "走出焦虑、希望、释放恐惧、寻求帮助"),
    _minor("swords", 10, "宝剑十", "Ten of Swords", "谷底、终结、背叛、惨败、痛苦的结束", "触底反弹、复原、最坏已过、重生"),
    _minor("swords", 11, "宝剑侍从", "Page of Swords", "好奇、警觉、求知、言辞、机敏", "多疑、尖刻、搬弄是非、草率"),
    _minor("swords", 12, "宝剑骑士", "Knight of Swords", "果断、行动迅速、雄辩、直率、冲劲", "鲁莽、咄咄逼人、急躁、思虑不周"),
    _minor("swords", 13, "宝剑王后", "Queen of Swords", "理性、独立、洞察、坦率、明辨是非", "冷漠、苛刻、尖刻、情感封闭"),
    _minor("swords", 14, "宝剑国王", "King of Swords", "理智、权威、公正、决断、思想清晰", "专断、冷酷、滥用权威、操纵"),
]
# 钱币（土）
PENTACLES = [
    _minor("pentacles", 1, "钱币一", "Ace of Pentacles", "新机遇、财富、物质契机、丰盛、务实开端", "错失机会、财务不稳、贪婪、计划落空"),
    _minor("pentacles", 2, "钱币二", "Two of Pentacles", "平衡、灵活、多任务、适应、调度", "失衡、手忙脚乱、财务吃紧、顾此失彼"),
    _minor("pentacles", 3, "钱币三", "Three of Pentacles", "合作、技艺、团队、学习、打磨", "缺乏配合、品质不佳、各自为政、敷衍"),
    _minor("pentacles", 4, "钱币四", "Four of Pentacles", "稳固、掌控、储蓄、安全感、保守", "吝啬、执着、财务松动、掌控过度"),
    _minor("pentacles", 5, "钱币五", "Five of Pentacles", "匮乏、困顿、失援、不安、逆境", "走出困境、援助到来、复原、重拾信心"),
    _minor("pentacles", 6, "钱币六", "Six of Pentacles", "给予、慷慨、互助、公平、分享", "施舍不均、债务、依赖、有条件的给予"),
    _minor("pentacles", 7, "钱币七", "Seven of Pentacles", "耐心、投入、评估、长期回报、等待", "急功近利、付出无果、失去耐心、投资失利"),
    _minor("pentacles", 8, "钱币八", "Eight of Pentacles", "钻研、勤勉、精进、专注、工匠精神", "敷衍、完美主义、缺乏专注、低质重复"),
    _minor("pentacles", 9, "钱币九", "Nine of Pentacles", "富足、独立、自给、优雅、享受成果", "过度依赖、虚荣、财务不稳、孤独"),
    _minor("pentacles", 10, "钱币十", "Ten of Pentacles", "财富、家族、传承、长久稳定、根基", "财务纠纷、家庭问题、短视、传承断裂"),
    _minor("pentacles", 11, "钱币侍从", "Page of Pentacles", "学习、机会、务实、目标、脚踏实地", "拖延、眼高手低、分心、计划落空"),
    _minor("pentacles", 12, "钱币骑士", "Knight of Pentacles", "勤勉、可靠、耐心、务实、坚持", "固执、停滞、无趣、墨守成规"),
    _minor("pentacles", 13, "钱币王后", "Queen of Pentacles", "务实、滋养、丰盛、顾家、可靠", "操劳、物质至上、失衡、忽视自我"),
    _minor("pentacles", 14, "钱币国王", "King of Pentacles", "富足、稳健、事业有成、可靠、掌控", "固执、贪婪、物质主义、铺张"),
]

# 完整 78 张牌库（顺序：大牌 0-21 → 权杖 → 圣杯 → 宝剑 → 钱币）
DECK = MAJOR + WANDS + CUPS + SWORDS + PENTACLES

# 多体系注册表（当前仅韦特；扩展时在此加入新牌库）
DECKS = {DECK_SYSTEM: DECK}

# id → 牌 的索引，便于按 id 取牌
CARD_BY_ID = {c["id"]: c for c in DECK}


# ── 牌阵定义 ───────────────────────────────────────────────────────
# 每个牌阵：key / 名称 / 说明 / 位置列表（位置含 key / 名称 / 含义）
SPREADS = {
    "single": {
        "key": "single", "cn": "单张指引", "count": 1,
        "desc": "抽一张，看当下最该被你看见的能量。适合每日一抽或简单是非题。",
        "positions": [
            {"key": "core", "name": "核心指引", "desc": "此刻问题的核心能量与提醒"},
        ],
    },
    "three": {
        "key": "three", "cn": "三张牌（时间流）", "count": 3,
        "desc": "经典的过去-现在-未来三张牌，看一件事的来龙去脉与走向。",
        "positions": [
            {"key": "past", "name": "过去", "desc": "造成当下局面的根源与已发生的影响"},
            {"key": "present", "name": "现在", "desc": "当下的处境、心态与核心议题"},
            {"key": "future", "name": "未来", "desc": "若延续当前方向，事情的可能走向"},
        ],
    },
    "celtic": {
        "key": "celtic", "cn": "凯尔特十字", "count": 10,
        "desc": "最经典的 10 张深度牌阵，层层剖析现状、阻碍、内外因与最终结果。",
        "positions": [
            {"key": "present", "name": "现状", "desc": "问题的核心、当下处境"},
            {"key": "challenge", "name": "阻碍/助力", "desc": "横在面前的挑战，或正在帮你的力量"},
            {"key": "foundation", "name": "根基", "desc": "事情的远因、潜意识根源"},
            {"key": "past", "name": "近因", "desc": "刚过去、正在淡出的影响"},
            {"key": "goal", "name": "目标/显意识", "desc": "你意识层面的目标与期待"},
            {"key": "future", "name": "近期未来", "desc": "接下来即将到来的发展"},
            {"key": "self", "name": "自我态度", "desc": "你自己在此事中的态度与立场"},
            {"key": "environment", "name": "外部环境", "desc": "他人与环境对你的影响"},
            {"key": "hopes_fears", "name": "希望与恐惧", "desc": "你内心的期待，也是你的隐忧"},
            {"key": "outcome", "name": "最终结果", "desc": "综合各因素后的可能结局"},
        ],
    },
}


def get_deck(deck=DECK_SYSTEM):
    """按体系取牌库；拼错的体系名不能静默回退到另一副牌。"""
    if not isinstance(deck, str) or deck not in DECKS:
        raise ValueError("未知牌组体系")
    return DECKS[deck]


def get_spread(key):
    """按 key 取牌阵定义，未知则返回 None"""
    if not isinstance(key, str):
        raise ValueError("牌阵键必须是字符串")
    return SPREADS.get(key)
