"""Lenormand sampling and deterministic line structures, without tarot reversals."""
from collections import Counter
from copy import deepcopy

from ..randomness import DrawRandom, digest, validate_random_evidence
from .data import PAIR_HINTS, SPREADS, get_deck, get_spread


def _question(value):
    if value is None:
        return ""
    if not isinstance(value, str):
        raise ValueError("question 须为字符串")
    return value.strip()


def _rules():
    return {"schema": "lenormand-rules-v1", "deck": "petit-lenormand-36",
            "reversals": False, "profile": "project-linear-v1",
            "pair_order": "left-to-right", "focus": "middle-card",
            "mirrors": "outer-to-inner", "pair_dictionary": "selected-20-v1"}


def _fingerprint():
    return digest({"rules": _rules(), "deck": get_deck(), "spreads": SPREADS,
                   "pairs": [[list(pair), text] for pair, text in sorted(PAIR_HINTS.items())]})


def _picks(picks, count):
    if picks is None:
        return list(range(count))
    if (not isinstance(picks, (list, tuple)) or len(picks) != count
            or any(type(value) is not int or not 0 <= value < 36 for value in picks)
            or len(set(picks)) != count):
        raise ValueError(f"须选择 {count} 个不重复的0～35槽位")
    return list(picks)


def prepare_shuffle(*, seed=None, interaction=None):
    """Private deck snapshot: keep server-side until selection is complete."""
    if seed is not None and type(seed) is not int:
        raise ValueError("seed 须为整数；仅用于可复现模拟")
    rng = DrawRandom("lenormand", seed=seed, interaction=interaction)
    ids = [card["id"] for card in get_deck()]
    rng.shuffle(ids)
    return {"schema": "lenormand-shuffle-v1", "deck_sha256": digest(get_deck()),
            "card_ids": ids, "seed": seed, "random": rng.evidence}


def _validate_shuffle(shuffle):
    if (not isinstance(shuffle, dict) or shuffle.get("schema") != "lenormand-shuffle-v1"
            or shuffle.get("deck_sha256") != digest(get_deck())):
        raise ValueError("雷诺曼洗牌版本或牌库不匹配")
    ids = shuffle.get("card_ids")
    if (not isinstance(ids, list) or len(ids) != 36
            or any(type(value) is not int for value in ids) or set(ids) != set(range(1, 37))
            or "seed" not in shuffle or (shuffle["seed"] is not None and type(shuffle["seed"]) is not int)):
        raise ValueError("无效雷诺曼洗牌记录")
    evidence = validate_random_evidence(shuffle.get("random"), "lenormand")
    if (evidence["source"] == "explicit-seed") != (shuffle["seed"] is not None):
        raise ValueError("seed 与随机来源不一致")


def _pair(cards, left, right):
    first, second = cards[left]["card"], cards[right]["card"]
    hint = PAIR_HINTS.get((first["id"], second["id"]))
    return {"positions": [left + 1, right + 1], "card_ids": [first["id"], second["id"]],
            "label": f"{first['cn']} → {second['cn']}",
            "keywords": [first["keywords"][:], second["keywords"][:]],
            "has_selected_rule": hint is not None, "reading_hint": hint}


def _build(ids, spread_key, question, method, shuffle=None, picks=None):
    spread = get_spread(spread_key)
    if (not isinstance(ids, (list, tuple)) or len(ids) != spread["count"]
            or any(type(value) is not int or not 1 <= value <= 36 for value in ids)
            or len(set(ids)) != len(ids)):
        raise ValueError("录入牌须为1～36之间的不重复编号，张数匹配牌阵")
    deck = {card["id"]: card for card in get_deck()}
    cards = [{"position": index + 1, "position_name": spread["positions"][index],
              "card": deck[value]} for index, value in enumerate(ids)]
    middle = len(cards) // 2
    analysis = {"focus": deepcopy(cards[middle]),
                "adjacent_pairs": [_pair(cards, index, index + 1) for index in range(len(cards) - 1)],
                "mirror_pairs": [_pair(cards, index, len(cards) - index - 1) for index in range(middle)],
                "theme_counts": dict(Counter(card["card"]["theme"] for card in cards))}
    snapshot = {"schema": "lenormand-reading-v1", "method": method, "spread_key": spread_key,
                "question": question, "rules_sha256": _fingerprint(),
                "card_ids": list(ids), "shuffle": deepcopy(shuffle),
                "picks": list(picks) if picks is not None else None}
    return {"module": "lenormand", "question": question, "spread": spread,
            "source": {"method": method}, "random": deepcopy(shuffle["random"]) if shuffle else None,
            "rules": _rules(), "cards": cards, "analysis": analysis,
            "summary": " · ".join(card["card"]["cn"] for card in cards), "replay": snapshot}


def cast(card_ids, question="", *, spread_key=None):
    """Read physical/manually supplied cards; no RNG is consulted."""
    question = _question(question)
    if spread_key is None:
        if not isinstance(card_ids, (list, tuple)) or len(card_ids) not in (3, 5):
            raise ValueError("手动录入须为三张或五张牌")
        spread_key = "three" if len(card_ids) == 3 else "five"
    return _build(card_ids, spread_key, question, "manual")


def draw(spread_key="three", question="", seed=None, picks=None, *, interaction=None, shuffle=None):
    """OS-backed sampling without replacement; optional interaction or private shuffle."""
    question = _question(question)
    spread = get_spread(spread_key)
    picks = _picks(picks, spread["count"])
    if shuffle is not None and (seed is not None or interaction is not None):
        raise ValueError("shuffle 不能与 seed/interaction 混用")
    if shuffle is None:
        shuffle = prepare_shuffle(seed=seed, interaction=interaction)
    _validate_shuffle(shuffle)
    ids = [shuffle["card_ids"][slot] for slot in picks]
    return _build(ids, spread_key, question, "draw", shuffle, picks)


def replay(snapshot, question=None):
    """Replay trusted stored records; hashes detect changes, not authenticity."""
    if (not isinstance(snapshot, dict) or snapshot.get("schema") != "lenormand-reading-v1"
            or snapshot.get("method") not in ("manual", "draw")
            or snapshot.get("rules_sha256") != _fingerprint()
            or not isinstance(snapshot.get("card_ids"), list)
            or not isinstance(snapshot.get("spread_key"), str)):
        raise ValueError("雷诺曼回放无效，或牌库／牌阵／组合规则已变化")
    question = snapshot.get("question") if question is None else question
    if snapshot["method"] == "manual":
        if snapshot.get("shuffle") is not None or snapshot.get("picks") is not None:
            raise ValueError("手动录牌回放不能包含洗牌或槽位")
        result = cast(snapshot["card_ids"], question, spread_key=snapshot["spread_key"])
    else:
        if not isinstance(snapshot.get("shuffle"), dict) or not isinstance(snapshot.get("picks"), list):
            raise ValueError("抽牌回放缺少洗牌或槽位")
        result = draw(snapshot["spread_key"], question, picks=snapshot["picks"], shuffle=snapshot["shuffle"])
        if snapshot["card_ids"] != result["replay"]["card_ids"]:
            raise ValueError("牌序与所存槽位不匹配")
    return result
