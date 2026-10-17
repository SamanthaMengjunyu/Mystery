"""Deterministic Plum Blossom casting, independent of Najia interpretation.

The shared hexagram table supplies only names/bits; no six-relative, palace,
shi/ying or six-spirit rules are imported into Plum Blossom analysis.
"""
from copy import deepcopy
from importlib.metadata import version

from lunar_python import Solar
from ..liuyao.data import TRIGRAMS, BITS_TO_TRIGRAM, HEX_BY_BITS, WX_SHENG, WX_KE, ZHI
from ..randomness import digest
from ..timebase import beijing_clock, resolve_local, time_record, wall_datetime

ORDER = ("乾", "兑", "离", "震", "巽", "坎", "艮", "坤")


def _integer(value, low, high, label):
    if type(value) is not int or not low <= value <= high:
        raise ValueError(f"{label}须为 {low}~{high} 之间的整数")
    return value


def _question(value):
    if value is None:
        return ""
    if not isinstance(value, str):
        raise ValueError("question 须为字符串")
    return value.strip()


def _remainder(value, modulus):
    return (value - 1) % modulus + 1


def _hexagram(bits):
    return {"name": HEX_BY_BITS[tuple(bits)]["name"], "bits": list(bits),
            "upper": BITS_TO_TRIGRAM[tuple(bits[3:])],
            "lower": BITS_TO_TRIGRAM[tuple(bits[:3])]}


def _trigram(name, position):
    return {"name": name, "position": position, "element": TRIGRAMS[name]["wx"]}


def _relation(body, other, label):
    if body == other:
        key, text = "same", f"{label}与体比和"
    elif WX_SHENG[other] == body:
        key, text = "supports_body", f"{label}生体"
    elif WX_SHENG[body] == other:
        key, text = "drains_body", f"体生{label}"
    elif WX_KE[other] == body:
        key, text = "controls_body", f"{label}克体"
    else:
        key, text = "body_controls", f"体克{label}"
    return {"kind": key, "label": text, "body_element": body, "other_element": other}


def _rules(method, nuclear):
    if nuclear not in ("classic", "standard"):
        raise ValueError("nuclear 须为 classic/standard")
    rules = {"schema": "meihua-rules-v1", "method": method, "trigram_order": list(ORDER),
             "line_order": "bottom-to-top", "zero_remainder": "8-for-trigram/6-for-line",
             "body": "nonmoving-trigram", "nuclear": nuclear,
             "nuclear_lines": "lower-234/upper-345",
             "pure_qian_kun": "nuclear-of-changed" if nuclear == "classic" else "nuclear-of-original"}
    if method in ("lunar", "time"):
        rules.update(year_boundary="lunar-new-year", leap_month="repeat-month-number")
    if method == "time":
        rules.update(calendar_version=version("lunar-python"), clock="utc+08-standard",
                     day_boundary="00:00", hour_branch="23:00-and-00:00-zi")
    return rules


def _fingerprint(rules):
    return digest({"rules": rules, "trigrams": {name: {"bits": TRIGRAMS[name]["bits"],
                   "element": TRIGRAMS[name]["wx"]} for name in ORDER},
                   "hexagrams": [[list(bits), info["name"]] for bits, info in sorted(HEX_BY_BITS.items())],
                   "sheng": WX_SHENG, "ke": WX_KE})


def _build(upper, lower, moving_line, *, method, inputs, question, nuclear, trace,
           recorded_time=None):
    rules = _rules(method, nuclear)
    if method == "numbers":
        rules["number_profile"] = trace["profile"]
    bits = list(TRIGRAMS[ORDER[lower - 1]]["bits"] + TRIGRAMS[ORDER[upper - 1]]["bits"])
    changed = bits[:]
    changed[moving_line - 1] ^= 1
    nuclear_source = "bian" if nuclear == "classic" and len(set(bits)) == 1 else "ben"
    source = changed if nuclear_source == "bian" else bits
    mutual = source[1:4] + source[2:5]
    ben, hu, bian = _hexagram(bits), _hexagram(mutual), _hexagram(changed)
    body_position, use_position = ("upper", "lower") if moving_line <= 3 else ("lower", "upper")
    body = _trigram(ben[body_position], body_position)
    use = _trigram(ben[use_position], use_position)
    changed_use = _trigram(bian[use_position], use_position)
    analysis = {"body": body, "use": use, "changed_use": changed_use,
                "ben_relation": _relation(body["element"], use["element"], "用"),
                "bian_relation": _relation(body["element"], changed_use["element"], "变用"),
                "hu_relations": [_relation(body["element"], TRIGRAMS[hu[p]]["wx"], label)
                                 for p, label in (("lower", "下互"), ("upper", "上互"))]}
    question = _question(question)
    snapshot = {"schema": "meihua-reading-v1", "method": method, "input": deepcopy(inputs),
                "nuclear": nuclear, "question": question, "time": deepcopy(recorded_time),
                "rules_sha256": _fingerprint(rules)}
    return {"module": "meihua", "question": question, "input": deepcopy(inputs),
            "source": {"method": method, "deterministic": True}, "random": None,
            "time": recorded_time, "rules": rules, "trace": trace,
            "ben": ben, "hu": {**hu, "source": nuclear_source}, "bian": bian,
            "moving_line": moving_line, "analysis": analysis,
            "summary": f"{ben['name']} · {moving_line}爻动 → {bian['name']}", "replay": snapshot}


def cast(upper, lower, moving_line, question="", *, nuclear="classic"):
    """显式先天卦数1～8与动爻1～6；不做随机抽取。"""
    _integer(upper, 1, 8, "上卦数")
    _integer(lower, 1, 8, "下卦数")
    _integer(moving_line, 1, 6, "动爻")
    inputs = {"upper": upper, "lower": lower, "moving_line": moving_line}
    return _build(upper, lower, moving_line, method="explicit", inputs=inputs,
                  question=question, nuclear=nuclear, trace=deepcopy(inputs))


def cast_numbers(first, second, third=None, question="", *, hour_number=None, nuclear="classic"):
    """报数：前两数取上下卦；第三数独立取爻，或两数之和取爻。

    Optional hour_number=1..12 adds the hour to a two-number line total.
    These profiles are explicit choices; they do not silently add current time.
    """
    for name, value in (("first", first), ("second", second)):
        _integer(value, 0, 2 ** 31 - 1, name)
    if third is not None:
        _integer(third, 0, 2 ** 31 - 1, "third")
    if hour_number is not None:
        _integer(hour_number, 1, 12, "hour_number")
        if third is not None:
            raise ValueError("third 与 hour_number 不能混用")
    total = third if third is not None else first + second + (hour_number or 0)
    upper, lower, line = _remainder(first, 8), _remainder(second, 8), _remainder(total, 6)
    inputs = {"first": first, "second": second, "third": third, "hour_number": hour_number}
    profile = "independent-third" if third is not None else "sum-plus-hour" if hour_number else "sum"
    return _build(upper, lower, line, method="numbers", inputs=inputs, question=question,
                  nuclear=nuclear, trace={"profile": profile, "upper_total": first,
                  "lower_total": second, "line_total": total})


def _lunar_totals(year_branch, month, day, hour_branch):
    if not isinstance(year_branch, str) or year_branch not in ZHI:
        raise ValueError("year_branch 须为子至亥的地支")
    if not isinstance(hour_branch, str) or hour_branch not in ZHI:
        raise ValueError("hour_branch 须为子至亥的地支")
    _integer(month, 1, 12, "农历月")
    _integer(day, 1, 30, "农历日")
    year_number, hour_number = ZHI.index(year_branch) + 1, ZHI.index(hour_branch) + 1
    upper_total = year_number + month + day
    total = upper_total + hour_number
    return {"year_number": year_number, "hour_number": hour_number,
            "upper_total": upper_total, "lower_total": total, "line_total": total}


def cast_lunar(year_branch, month, day, hour_branch, question="", *, leap_month=False,
               nuclear="classic"):
    """传统年月日时数；无完整年份时仅校验数值范围，不验证具体农历日期。"""
    if type(leap_month) is not bool:
        raise ValueError("leap_month 须为布尔值")
    trace = _lunar_totals(year_branch, month, day, hour_branch)
    inputs = {"year_branch": year_branch, "month": month, "day": day,
              "hour_branch": hour_branch, "leap_month": leap_month}
    return _build(_remainder(trace["upper_total"], 8), _remainder(trace["lower_total"], 8),
                  _remainder(trace["line_total"], 6), method="lunar", inputs=inputs,
                  question=question, nuclear=nuclear, trace=trace)


def cast_time(year, month, day, hour, minute=0, question="", *, second=0,
              tz_name="Asia/Shanghai", fold=None, nuclear="classic"):
    """显式当地时间→UTC+08标准时→农历起卦，春节换年、午夜换日。"""
    civil = wall_datetime(year, month, day, hour, minute, second)
    if not 1900 <= year <= 2100:
        raise ValueError("年份须在 1900~2100 之间")
    local = resolve_local(civil, tz_name, fold=fold)
    clock = beijing_clock(local)
    lunar = Solar.fromYmdHms(clock.year, clock.month, clock.day, clock.hour,
                            clock.minute, clock.second).getLunar()
    branch = ZHI[((clock.hour + 1) // 2) % 12]
    trace = _lunar_totals(lunar.getYearZhi(), abs(lunar.getMonth()), lunar.getDay(), branch)
    trace["calendar"] = {"clock": clock.isoformat(), "year_branch": lunar.getYearZhi(),
                         "lunar_year": lunar.getYear(), "month": abs(lunar.getMonth()),
                         "day": lunar.getDay(), "hour_branch": branch, "leap_month": lunar.getMonth() < 0}
    inputs = {"year": year, "month": month, "day": day, "hour": hour, "minute": minute,
              "second": second, "tz_name": tz_name, "fold": local.fold}
    return _build(_remainder(trace["upper_total"], 8), _remainder(trace["lower_total"], 8),
                  _remainder(trace["line_total"], 6), method="time", inputs=inputs,
                  question=question, nuclear=nuclear, trace=trace,
                  recorded_time=time_record(local, basis="utc+08-standard"))


def replay(snapshot, question=None):
    """Recompute from declared input; detect changed rules or time interpretation."""
    functions = {"explicit": cast, "numbers": cast_numbers, "lunar": cast_lunar, "time": cast_time}
    if (not isinstance(snapshot, dict) or snapshot.get("schema") != "meihua-reading-v1"
            or not isinstance(snapshot.get("method"), str) or snapshot["method"] not in functions
            or not isinstance(snapshot.get("input"), dict)):
        raise ValueError("无效梅花回放记录")
    inputs = snapshot["input"]
    if set(inputs) & {"question", "nuclear"}:
        raise ValueError("回放输入含重复控制字段")
    try:
        result = functions[snapshot["method"]](**inputs, nuclear=snapshot.get("nuclear"),
                 question=snapshot.get("question") if question is None else question)
    except TypeError as error:
        raise ValueError("回放输入不完整或含未知字段") from error
    if (snapshot.get("rules_sha256") != result["replay"]["rules_sha256"]
            or "time" not in snapshot or snapshot["time"] != result["time"]):
        raise ValueError("梅花规则、历法版本或时间解释已变化")
    return result
