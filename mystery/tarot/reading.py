"""
塔罗第 1 层（抽牌）+ 第 2 层（结构分析）—— 全程零 LLM。

抽牌由程序决定，LLM 只解释既定牌面。默认使用系统安全随机；显式 seed 保留
旧版结果。完整洗牌快照支持跨进程回放，鼠标参与摘要可作为可选混合输入。

第 2 层把抽出的牌做确定性的结构判断（大牌占比、元素分布、正逆位比、宫廷牌、
重复数字等），整理成「关键看点」，供第 3 层 LLM 据以定主线。
"""
import secrets
from copy import deepcopy

from ..randomness import DrawRandom, digest, validate_random_evidence

from .data import (get_deck, get_spread, SUITS, COURT_CN,
                                  DECK_SYSTEM)


def new_seed():
    """兼容调用者的 seed 工具；默认抽牌不再经过 seed/普通 PRNG。"""
    return secrets.randbits(256)


def prepare_shuffle(*, seed=None, interaction=None, deck=DECK_SYSTEM, reversals=True):
    """Prepare one private shuffle, reusable across selection requests.

    Keep this object server-side until selection is complete: it contains the
    whole hidden deck. An interaction digest is evidence of supplied input,
    not proof of a human or a verifiable no-reroll protocol.
    """
    if type(reversals) is not bool:
        raise ValueError("reversals must be boolean")
    seed = int(seed) if seed is not None else None
    rng = DrawRandom("tarot", seed=seed, interaction=interaction)
    pool = list(get_deck(deck))
    rng.shuffle(pool)
    orient = [rng.reversed() for _ in pool] if reversals else [False] * len(pool)
    return {"schema": "tarot-shuffle-v1", "deck": deck,
            "deck_sha256": digest(get_deck(deck)), "seed": seed,
            "card_ids": [card["id"] for card in pool], "orientations": orient,
            "reversals": reversals, "random": deepcopy(rng.evidence)}


def _validate_shuffle(shuffle, deck):
    if not isinstance(shuffle, dict) or shuffle.get("schema") != "tarot-shuffle-v1":
        raise ValueError("unknown shuffle version")
    cards = get_deck(deck)
    ids = shuffle.get("card_ids")
    orientations = shuffle.get("orientations")
    if (shuffle.get("deck") != deck or shuffle.get("deck_sha256") != digest(cards)
            or not isinstance(ids, list) or len(ids) != len(cards)
            or any(not isinstance(card_id, str) for card_id in ids)
            or set(ids) != {card["id"] for card in cards}
            or not isinstance(orientations, list) or len(orientations) != len(cards)
            or any(type(value) is not bool for value in orientations)
            or type(shuffle.get("reversals")) is not bool
            or (not shuffle["reversals"] and any(orientations))
            or "seed" not in shuffle
            or (shuffle["seed"] is not None and type(shuffle["seed"]) is not int)
            or not isinstance(shuffle.get("random"), dict)):
        raise ValueError("invalid shuffle or changed deck")
    evidence = validate_random_evidence(shuffle["random"], "tarot")
    if (evidence["source"] == "explicit-seed") != (shuffle["seed"] is not None):
        raise ValueError("shuffle seed and random source disagree")


def _validate_picks(spread, picks, pool_size):
    count = spread["count"]
    if picks is None:
        picks = list(range(count))
    if not isinstance(picks, (list, tuple)):
        raise ValueError("选牌位置必须是整数列表")
    picks = list(picks)
    if any(type(p) is not int for p in picks):
        raise ValueError("选牌位置必须是整数")
    if len(picks) != count:
        raise ValueError(f"该牌阵需选 {count} 张，收到 {len(picks)} 张")
    if len(set(picks)) != count:
        raise ValueError("选牌不能重复")
    if any(p < 0 or p >= pool_size for p in picks):
        raise ValueError("选牌位置越界")
    return picks


def _draw_cards(spread, shuffle, picks, deck):
    lookup = {card["id"]: card for card in get_deck(deck)}
    pool = [lookup[card_id] for card_id in shuffle["card_ids"]]
    orient = shuffle["orientations"]

    out = []
    for pos, slot in zip(spread["positions"], picks):
        card = pool[slot]
        reversed_ = orient[slot]
        out.append({
            "position": deepcopy(pos),
            "card": deepcopy(card),
            "reversed": reversed_,
            "meaning": card["rev"] if reversed_ else card["up"],
        })
    return out


def _analyze(cards):
    """第 2 层：对抽出的牌做确定性结构分析，产出统计 + 关键看点(compositions)"""
    n = len(cards)
    major_count = sum(1 for c in cards if c["card"]["arcana"] == "major")
    minor_count = n - major_count
    reversed_count = sum(1 for c in cards if c["reversed"])
    court_count = sum(1 for c in cards
                      if c["card"]["arcana"] == "minor" and c["card"]["num"] >= 11)

    # 小牌元素分布
    element = {"火": 0, "水": 0, "风": 0, "土": 0}
    for c in cards:
        suit = c["card"]["suit"]
        if suit:
            element[SUITS[suit]["element"]] += 1
    minor_elems = {k: v for k, v in element.items() if v > 0}
    dom_element = max(minor_elems, key=minor_elems.get) if minor_elems else None
    # 「缺」只在小牌足够多时才有意义
    lack_element = None
    if minor_count >= 3:
        zero = [k for k, v in element.items() if v == 0]
        lack_element = "、".join(zero) if zero else None

    # 重复数字（含大小牌的 num；宫廷牌按阶位算同号）
    num_count = {}
    for c in cards:
        num_count.setdefault(c["card"]["num"], []).append(c["card"]["cn"])
    repeats = {k: v for k, v in num_count.items() if len(v) >= 2}

    # ── 关键看点：与八字/星盘同构，weight 越大越优先 ──
    comps = []
    if n >= 3:
        ratio = major_count / n
        if ratio >= 0.5:
            comps.append({"name": "大牌主导", "weight": 3,
                          "note": f"{n}张里有{major_count}张大阿尔卡那，事件处在人生重大、命运层面的节点，"
                                  f"非日常琐事，外力与大势的分量重，个人可掌控的余地相对小。"})
        elif major_count == 0:
            comps.append({"name": "全为小牌", "weight": 1,
                          "note": "全是小阿尔卡那，议题集中在日常、具体、可操作的层面，更多取决于自己当下的选择与行动。"})

    if dom_element and minor_count >= 3 and minor_elems[dom_element] >= max(2, minor_count // 2 + 1):
        themes = {"火": "行动力、激情与事业推进", "水": "情感、关系与内心感受",
                  "风": "思虑、沟通与决断", "土": "现实、金钱与务实层面"}
        comps.append({"name": f"{dom_element}元素偏重", "weight": 2,
                      "note": f"小牌以{_suit_cn_by_element(dom_element)}（{dom_element}）为主，议题重心落在"
                              f"{themes[dom_element]}上。"})
    if lack_element:
        comps.append({"name": f"缺{lack_element}", "weight": 1,
                      "note": f"牌面缺少{lack_element}元素，对应层面的能量在此事中较弱或被忽略，可留意是否需要补足。"})

    if n >= 3 and reversed_count >= max(2, (n + 1) // 2):
        comps.append({"name": "逆位偏多", "weight": 2,
                      "note": f"{n}张里有{reversed_count}张逆位，多处能量受阻、延迟或指向尚未察觉的内在/潜意识面，"
                              f"提示当前更需要向内看、处理卡点，而非急于向外推进。"})
    elif n >= 3 and reversed_count == 0:
        comps.append({"name": "全为正位", "weight": 1,
                      "note": "全部正位，能量流动相对顺畅、外显，事情大体按其本义直接展开。"})

    if court_count >= 2:
        comps.append({"name": "多张宫廷牌", "weight": 2,
                      "note": f"出现{court_count}张宫廷牌，暗示此事高度牵涉具体的人（他人或你扮演的角色），"
                              f"人际互动是关键变量。"})

    for num, names in repeats.items():
        if num in COURT_CN:
            label = COURT_CN[num]
        else:
            label = f"数字{num}"
        comps.append({"name": f"{label}×{len(names)}", "weight": 2,
                      "note": f"重复出现{label}（{'、'.join(names)}），该数字/阶位的主题在此事中被反复强调，是贯穿主线。"})

    comps.sort(key=lambda x: x["weight"], reverse=True)

    return {
        "card_total": n,
        "major_count": major_count, "minor_count": minor_count,
        "element": element, "dom_element": dom_element, "lack_element": lack_element,
        "reversed_count": reversed_count,
        "reversed_ratio": round(reversed_count / n, 2) if n else 0,
        "court_count": court_count,
        "structures": {"compositions": comps},
    }


def _suit_cn_by_element(elem):
    """元素 → 该元素花色中文名（用于看点文案）"""
    for suit, info in SUITS.items():
        if info["element"] == elem:
            return info["cn"]
    return elem


def fan_size(deck=DECK_SYSTEM):
    """洗牌后摊开供用户点选的牌堆张数（整副）"""
    return len(get_deck(deck))


def draw(spread_key, question="", seed=None, picks=None, deck=DECK_SYSTEM, *,
         interaction=None, shuffle=None, reversals=None):
    """
    抽一副牌并附结构分析。入口函数。
    默认系统安全随机；seed 是旧版复现模式，不能与 interaction/shuffle 混用。
    shuffle 是 prepare_shuffle() 的私有快照；不提供时创建一次洗牌。
    picks 为用户点选的槽位顺序；为空则按洗牌顺序取前 count 张。
    """
    spread = get_spread(spread_key)
    if spread is None:
        raise ValueError(f"未知牌阵：{spread_key}")
    picks = _validate_picks(spread, picks, len(get_deck(deck)))
    if reversals is not None and type(reversals) is not bool:
        raise ValueError("reversals must be boolean")
    if shuffle is not None and (seed is not None or interaction is not None):
        raise ValueError("shuffle cannot be combined with seed or interaction")
    if shuffle is None:
        shuffle = prepare_shuffle(seed=seed, interaction=interaction, deck=deck,
                                  reversals=True if reversals is None else reversals)
    _validate_shuffle(shuffle, deck)
    if reversals is not None and (type(reversals) is not bool
                                  or reversals != shuffle["reversals"]):
        raise ValueError("reversals differs from the saved shuffle")
    cards = _draw_cards(spread, shuffle, picks, deck)
    return {
        "deck": deck,
        "spread": {"key": spread["key"], "cn": spread["cn"],
                   "desc": spread["desc"], "count": spread["count"]},
        "question": (question or "").strip(),
        "seed": shuffle["seed"],
        "picks": picks,
        "cards": cards,
        "analysis": _analyze(cards),
        "random": deepcopy(shuffle["random"]),
        "replay": {"schema": "tarot-reading-v2", "spread_key": spread_key,
                   "spread_sha256": digest(spread),
                   "picks": picks[:], "shuffle": deepcopy(shuffle)},
    }


def replay(snapshot, question=""):
    """Replay a completed reading without drawing fresh random values."""
    if (not isinstance(snapshot, dict)
            or snapshot.get("schema") not in ("tarot-reading-v1", "tarot-reading-v2")
            or not isinstance(snapshot.get("spread_key"), str)
            or not isinstance(snapshot.get("picks"), list)):
        raise ValueError("unknown tarot replay version")
    shuffle = snapshot.get("shuffle")
    if not isinstance(shuffle, dict):
        raise ValueError("invalid tarot replay")
    spread = get_spread(snapshot["spread_key"])
    if (snapshot["schema"] == "tarot-reading-v2"
            and (spread is None or snapshot.get("spread_sha256") != digest(spread))):
        raise ValueError("changed or missing spread definition")
    result = draw(snapshot["spread_key"], question=question,
                  picks=snapshot["picks"], deck=shuffle.get("deck"), shuffle=shuffle)
    if snapshot["schema"] == "tarot-reading-v1":
        # Keep an older record explicitly older; do not invent a historical checksum.
        result["replay"] = deepcopy(snapshot)
    return result


def card_label(entry):
    """单张牌的展示标签，如「权杖三（逆位）」"""
    return entry["card"]["cn"] + ("（逆位）" if entry["reversed"] else "（正位）")
