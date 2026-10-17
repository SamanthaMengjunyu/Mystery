"""Canonical Petit Lenormand identities, with project-authored Chinese prompts.

Keywords and selected ordered-pair hints are a small declared reading profile,
not a reproduction of a commercial deck guide or an exhaustive combination book.
"""
from copy import deepcopy

_ROWS = (
    ("骑士", "Rider", ("到来", "消息"), "movement"),
    ("四叶草", "Clover", ("小机会", "短暂幸运"), "opportunity"),
    ("船", "Ship", ("远行", "拓展"), "movement"),
    ("房屋", "House", ("家庭", "根基"), "stability"),
    ("树", "Tree", ("成长", "长期积累"), "growth"),
    ("云", "Clouds", ("疑虑", "信息不清"), "uncertainty"),
    ("蛇", "Snake", ("迂回", "复杂关系"), "complexity"),
    ("棺材", "Coffin", ("结束", "暂停"), "closure"),
    ("花束", "Bouquet", ("馈赠", "欣赏"), "opportunity"),
    ("镰刀", "Scythe", ("切断", "突然决定"), "change"),
    ("鞭子", "Whip", ("反复", "争论"), "friction"),
    ("鸟", "Birds", ("交谈", "纷杂声音"), "communication"),
    ("孩子", "Child", ("新起点", "小规模"), "growth"),
    ("狐狸", "Fox", ("策略", "核实动机"), "complexity"),
    ("熊", "Bear", ("力量", "资源掌控"), "resources"),
    ("星星", "Stars", ("方向", "愿景"), "orientation"),
    ("鹳", "Stork", ("迁移", "阶段变化"), "change"),
    ("狗", "Dog", ("信任", "伙伴"), "relationship"),
    ("塔", "Tower", ("机构", "界限"), "structure"),
    ("花园", "Garden", ("社交", "公开场合"), "community"),
    ("山", "Mountain", ("阻隔", "缓慢推进"), "obstacle"),
    ("岔路", "Crossroads", ("选择", "分支"), "decision"),
    ("老鼠", "Mice", ("损耗", "细小漏洞"), "erosion"),
    ("心", "Heart", ("感情", "喜爱"), "relationship"),
    ("戒指", "Ring", ("约定", "持续联系"), "commitment"),
    ("书", "Book", ("知识", "尚未公开"), "information"),
    ("信", "Letter", ("文字消息", "文件"), "communication"),
    ("男士", "Man", ("人物", "可选男性指示牌"), "person"),
    ("女士", "Woman", ("人物", "可选女性指示牌"), "person"),
    ("百合", "Lilies", ("成熟", "安宁"), "maturity"),
    ("太阳", "Sun", ("明朗", "活力"), "clarity"),
    ("月亮", "Moon", ("感受", "认可"), "recognition"),
    ("钥匙", "Key", ("突破口", "关键条件"), "solution"),
    ("鱼", "Fish", ("流动资源", "交易"), "resources"),
    ("锚", "Anchor", ("稳定", "长期投入"), "stability"),
    ("十字架", "Cross", ("负担", "责任"), "burden"),
)
_DECK = [{"id": index, "cn": cn, "en": en, "keywords": list(words), "theme": theme}
         for index, (cn, en, words, theme) in enumerate(_ROWS, 1)]

SPREADS = {
    "three": {"key": "three", "count": 3, "cn": "三张线性牌阵",
              "positions": ["左侧背景", "中心焦点", "右侧背景"],
              "reading": "按左至右串联，以中牌为焦点；两端可作镜像对照，不默认等于过去未来。"},
    "five": {"key": "five", "count": 5, "cn": "五张线性牌阵",
             "positions": ["左侧外缘", "左侧近因", "中心焦点", "右侧近因", "右侧外缘"],
             "reading": "按左至右串联，三号为焦点；一五、二四作镜像对照，不直接换算日期。"},
}

# Selected directional associations authored for this project. Others stay unset.
PAIR_HINTS = {
    (27, 25): "文件涉及约定：可关注条款是否写明。",
    (25, 27): "已有约定需要沟通或文字确认。",
    (24, 25): "感情议题连向承诺：可讨论双方期待。",
    (25, 24): "持续联系中的情感需求值得被看见。",
    (6, 31): "疑虑遇到明朗线索：可寻找澄清信息。",
    (31, 6): "已有把握中仍有疑点：可核对未明之处。",
    (34, 35): "流动资源与长期稳定相连：可审视持续性。",
    (35, 34): "稳定基础牵涉资源流动：可梳理投入与周转。",
    (18, 35): "伙伴关系与长期支持相连：可确认彼此能承担的角色。",
    (35, 18): "稳定安排有赖信任与协作。",
    (26, 27): "尚未公开的信息可能需要文字整理。",
    (27, 26): "文字材料中仍有未了解的部分。",
    (1, 27): "消息抵达并落实为文字：可关注具体内容。",
    (27, 1): "一份文字消息带来新的动向。",
    (22, 21): "选择面前存在阻隔：可分别检查各条路径。",
    (21, 22): "阻碍促使重新比较方案。",
    (23, 34): "细小损耗牵涉资源：可逐项核对流失。",
    (34, 23): "资源流动中可能有漏洞：可检查消耗环节。",
    (33, 26): "突破口与知识或尚待发现的信息有关。",
    (26, 33): "理解信息有助于找到关键条件。",
}


def get_deck():
    """Return an isolated copy of the 36 canonical card records."""
    return deepcopy(_DECK)


def get_spread(key):
    if not isinstance(key, str) or key not in SPREADS:
        raise ValueError("雷诺曼牌阵须为 three/five")
    return deepcopy(SPREADS[key])
