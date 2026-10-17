"""
六爻第 1 层（起卦+装卦）+ 第 2 层（用神旺衰/动爻分析）—— 全程零 LLM。

起卦：三枚铜钱一掷得一爻（阳面=3、阴面=2，三钱之和 6/7/8/9）。
  6 老阴(✗动)、7 少阳、8 少阴、9 老阳(○动)。投六次自下而上成卦；
  动爻翻面 → 变卦。cast 接收实体/外部投掷结果；draw 使用系统安全随机模拟三钱。
装卦：八卦纳甲配干支五行、八宫定世应、卦宫五行定六亲、日干起六神、日支定旬空（京房纳甲）。
分析：按问事类别取用神，用月建(月支)/日辰(日支)判旺衰、旬空、动爻生克 → 关键看点。
"""
from datetime import datetime
from copy import deepcopy
from importlib.metadata import version
from lunar_python import Solar
from ..randomness import DrawRandom, digest, validate_random_evidence
from ..timebase import resolve_local, beijing_clock, time_record, load_zone

from .data import (
    TRIGRAMS, BITS_TO_TRIGRAM, HEX_BY_BITS, ZHI_WUXING, ZHI_SX,
    WX_SHENG, WX_KE, relation, liushen_for_lines, xunkong, GUA_CI,
)

# 三钱之和 → 爻象（本爻阴阳、是否动爻、爻名）
LINE_DECODE = {
    6: {"yang": 0, "moving": True, "name": "老阴", "mark": "✗"},
    7: {"yang": 1, "moving": False, "name": "少阳", "mark": ""},
    8: {"yang": 0, "moving": False, "name": "少阴", "mark": ""},
    9: {"yang": 1, "moving": True, "name": "老阳", "mark": "○"},
}

# 地支六冲
ZHI_CHONG = {"子": "午", "午": "子", "丑": "未", "未": "丑", "寅": "申", "申": "寅",
             "卯": "酉", "酉": "卯", "辰": "戌", "戌": "辰", "巳": "亥", "亥": "巳"}

# 六冲卦（八纯卦 + 天雷无妄 + 雷天大壮）
LIUCHONG_GUA = {"乾为天", "坎为水", "艮为山", "震为雷", "巽为风", "离为火",
                "坤为地", "兑为泽", "天雷无妄", "雷天大壮"}

# 问事类别 → 用神（六亲名，或 世/应）
CATEGORIES = {
    "zonghe": {"label": "综合/问己", "yong": "世", "note": "以世爻为用神，综合论断"},
    "career": {"label": "事业·功名·官非", "yong": "官鬼", "note": "以官鬼为用神（功名、职位、官非）"},
    "wealth": {"label": "求财·财运", "yong": "妻财", "note": "以妻财为用神"},
    "love": {"label": "婚恋·感情", "yong": "应", "note": "以应爻(对方)为用神，兼看妻财/官鬼"},
    "health": {"label": "健康·疾病", "yong": "世", "note": "以世爻(求测者)为用神，子孙为药、官鬼为病"},
    "study": {"label": "学业·考试·文书", "yong": "父母", "note": "以父母为用神（文书、考试）"},
    "children": {"label": "子女·晚辈", "yong": "子孙", "note": "以子孙为用神"},
    "travel": {"label": "出行·行人", "yong": "世", "note": "以世爻为用神"},
}


def _date_ganzhi(year, month, day, hour, minute=0, second=0):
    """取占问当天的月建(月支)/日干支/旬空（复用 lunar-python 干支历，节气换月）"""
    ec = Solar.fromYmdHms(year, month, day, hour, minute, second).getLunar().getEightChar()
    ec.setSect(2)
    day_gan, day_zhi = ec.getDayGan(), ec.getDayZhi()
    return {
        "year": year, "month": month, "day": day, "hour": hour,
        "minute": minute, "second": second,
        "month_zhi": ec.getMonthZhi(),
        "day_gan": day_gan, "day_zhi": day_zhi,
        "day_ganzhi": day_gan + day_zhi,
        "month_ganzhi": ec.getMonthGan() + ec.getMonthZhi(),
        "xunkong": list(xunkong(day_gan, day_zhi)),
    }


def _calendar_window(year, month, day, years_ahead=8, months_ahead=15):
    """干支历参考窗口：未来若干年的流年(干支+生肖) + 未来若干月的流月干支。
    供 L3 断应期时据此把地支换算成具体年月，避免 LLM 自行推算年份生肖出错。
    流年以立春换岁（取 6 月 1 日，确保在立春之后）。"""
    years = []
    for y in range(year, year + years_ahead):
        gz = Solar.fromYmdHms(y, 6, 1, 12, 0, 0).getLunar().getEightChar().getYear()
        years.append({"year": y, "ganzhi": gz, "sx": ZHI_SX.get(gz[1], "")})
    months = []
    yy, mm = year, month
    for _ in range(months_ahead):
        ec = Solar.fromYmdHms(yy, mm, 15, 12, 0, 0).getLunar().getEightChar()
        months.append({"label": f"{yy}年{mm}月", "ganzhi": ec.getMonthGan() + ec.getMonthZhi()})
        mm += 1
        if mm > 12:
            mm = 1
            yy += 1
    return {"years": years, "months": months}


def _trigram_najia(tri_key, outer):
    """取某八卦在内卦(outer=False)或外卦(outer=True)时的天干与三爻地支"""
    t = TRIGRAMS[tri_key]
    if outer:
        return t["gan_out"], t["zhi_out"]
    return t["gan_in"], t["zhi_in"]


def _dress_lines(bits, palace_wx, day_gan, kong):
    """装卦：对六爻(自下而上) 配干支/五行/六亲/六神/旬空"""
    inner_key = BITS_TO_TRIGRAM[tuple(bits[0:3])]
    outer_key = BITS_TO_TRIGRAM[tuple(bits[3:6])]
    liushen = liushen_for_lines(day_gan)
    lines = []
    for i in range(6):
        if i < 3:
            gan, zhis = _trigram_najia(inner_key, outer=False)
            zhi = zhis[i]
        else:
            gan, zhis = _trigram_najia(outer_key, outer=True)
            zhi = zhis[i - 3]
        wx = ZHI_WUXING[zhi]
        lines.append({
            "pos": i + 1,
            "yang": bits[i],
            "gan": gan, "zhi": zhi, "zhi_wx": wx, "shengxiao": ZHI_SX[zhi],
            "liuqin": relation(palace_wx, wx),
            "liushen": liushen[i],
            "kong": zhi in kong,
        })
    return lines, inner_key, outer_key


def _wang_shuai(wx, month_zhi, day_zhi):
    """用神五行相对月建/日辰的旺衰（简化扶抑评分）"""
    score = 0.0
    notes = []
    for label, ref_zhi in (("月建", month_zhi), ("日辰", day_zhi)):
        ref = ZHI_WUXING[ref_zhi]
        if ref == wx:
            score += 1; notes.append(f"{label}{ref_zhi}与用神比和（旺）")
        elif WX_SHENG[ref] == wx:
            score += 1; notes.append(f"{label}{ref_zhi}生用神（相）")
        elif WX_KE[ref] == wx:
            score -= 1; notes.append(f"{label}{ref_zhi}克用神（受制）")
        elif WX_SHENG[wx] == ref:
            score -= 0.5; notes.append(f"{label}{ref_zhi}泄用神之气")
        else:
            score -= 0.5; notes.append(f"用神克{label}{ref_zhi}（耗力）")
    if score >= 1.5:
        verdict = "旺"
    elif score >= 0.5:
        verdict = "偏旺"
    elif score > -0.5:
        verdict = "中和"
    else:
        verdict = "衰弱"
    return verdict, score, notes


def _yong_lines(category, lines, shi_pos, ying_pos):
    """按类别定位用神爻（返回爻位列表与说明）"""
    cat = CATEGORIES.get(category, CATEGORIES["zonghe"])
    yong = cat["yong"]
    if yong == "世":
        return [shi_pos], cat
    if yong == "应":
        return [ying_pos], cat
    positions = [ln["pos"] for ln in lines if ln["liuqin"] == yong]
    return positions, cat


def _rules_sha256():
    """Include static tables and the exact calendar dependency in new replays."""
    return digest({"schema": "liuyao-najia-v1", "calendar": version("lunar-python"),
                   "sect": 2, "categories": CATEGORIES, "trigrams": TRIGRAMS,
                   "hexagrams": [[list(bits), info] for bits, info in sorted(HEX_BY_BITS.items())],
                   "gua_ci": GUA_CI, "zhi_wuxing": ZHI_WUXING, "zhi_sx": ZHI_SX,
                   "sheng": WX_SHENG, "ke": WX_KE, "chong": ZHI_CHONG,
                   "liuchong": sorted(LIUCHONG_GUA), "line_decode": LINE_DECODE})


def _validate_category(category):
    if not isinstance(category, str) or category not in CATEGORIES:
        raise ValueError("未知六爻问事分类")


def _local_fields(local):
    return {key: getattr(local, key) for key in
            ("year", "month", "day", "hour", "minute", "second")}


def _resolve_date(date, tz_name, fold):
    if date is None:
        if fold is not None:
            raise ValueError("fold requires an explicit date")
        return datetime.now(load_zone(tz_name)).replace(microsecond=0)
    if not isinstance(date, dict) or not {"year", "month", "day"} <= set(date):
        raise ValueError("date requires year, month and day")
    fields = ("year", "month", "day", "hour", "minute", "second")
    if set(date) - set(fields) or any(type(v) is not int for v in date.values()):
        raise ValueError("date must contain integer calendar fields only")
    values = [date.get(key, 0) for key in fields]
    return resolve_local(datetime(*values), tz_name, fold=fold)


def cast(tosses, question="", category="zonghe", date=None, *,
         tz_name="Asia/Shanghai", fold=None):
    """
    起卦 + 装卦 + 分析。入口函数。
    tosses：6 个整数(6/7/8/9)，自下而上（初爻→上爻）。
    date：{year,month,day,hour,minute,second}，显式日期须含年月日，时间默认零点。
    缺省取 tz_name 当前时间，不依赖服务器本地时区。历法采用 UTC+08 标准时。
    """
    if (not isinstance(tosses, (list, tuple)) or len(tosses) != 6
            or any(type(t) is not int or t not in LINE_DECODE for t in tosses)):
        raise ValueError("需要 6 次投掷，每次结果为 6/7/8/9")
    _validate_category(category)

    local = _resolve_date(date, tz_name, fold)
    clock = beijing_clock(local)
    dz = _date_ganzhi(clock.year, clock.month, clock.day, clock.hour, clock.minute, clock.second)
    kong = dz["xunkong"]

    ben_bits = [LINE_DECODE[t]["yang"] for t in tosses]
    moving = [LINE_DECODE[t]["moving"] for t in tosses]
    has_dong = any(moving)
    bian_bits = [b ^ 1 if mv else b for b, mv in zip(ben_bits, moving)]

    ben_info = HEX_BY_BITS[tuple(ben_bits)]
    palace_wx = ben_info["palace_wx"]
    ben_lines, ben_in, ben_out = _dress_lines(ben_bits, palace_wx, dz["day_gan"], kong)

    # 逐爻补：爻名/动否/变后地支与六亲（变爻六亲以本卦卦宫为准）
    bian_info = HEX_BY_BITS[tuple(bian_bits)] if has_dong else None
    bian_lines = None
    if has_dong:
        bian_lines, _, _ = _dress_lines(bian_bits, palace_wx, dz["day_gan"], kong)
    for i, ln in enumerate(ben_lines):
        dec = LINE_DECODE[tosses[i]]
        ln["value"] = tosses[i]
        ln["line_name"] = dec["name"]
        ln["moving"] = dec["moving"]
        ln["mark"] = dec["mark"]
        ln["shi"] = (ln["pos"] == ben_info["shi"])
        ln["ying"] = (ln["pos"] == ben_info["ying"])
        if dec["moving"] and bian_lines:
            bl = bian_lines[i]
            ln["bian_zhi"] = bl["zhi"]
            ln["bian_zhi_wx"] = bl["zhi_wx"]
            ln["bian_liuqin"] = bl["liuqin"]
            # 回头生/克/冲（变后地支对本爻地支）
            bw, ow = bl["zhi_wx"], ln["zhi_wx"]
            if ZHI_CHONG.get(bl["zhi"]) == ln["zhi"]:
                ln["huitou"] = "回头冲"
            elif WX_SHENG.get(bw) == ow:
                ln["huitou"] = "回头生"
            elif WX_KE.get(bw) == ow:
                ln["huitou"] = "回头克"
            else:
                ln["huitou"] = ""

    dong_pos = [i + 1 for i in range(6) if moving[i]]

    result = {
        "question": (question or "").strip(),
        "category": category,
        "category_label": CATEGORIES.get(category, CATEGORIES["zonghe"])["label"],
        "tosses": list(tosses),
        "date": dz,
        "time": time_record(local, basis="utc+08-standard"),
        "rules": {"schema": "liuyao-najia-v1", "sect": 2,
                  "year_boundary": "lichun", "month_boundary": "jie"},
        "ben": {
            "name": ben_info["name"], "palace": ben_info["palace"], "palace_wx": palace_wx,
            "pos_name": ben_info["pos_name"], "shi": ben_info["shi"], "ying": ben_info["ying"],
            "bits": ben_bits, "trigrams": [ben_out, ben_in],
            "gua_ci": GUA_CI.get(ben_info["name"], ""),
            "is_liuchong": ben_info["name"] in LIUCHONG_GUA,
            "lines": ben_lines,
        },
        "bian": None,
        "dong": dong_pos,
    }
    if has_dong:
        result["bian"] = {
            "name": bian_info["name"], "palace": bian_info["palace"],
            "pos_name": bian_info["pos_name"], "bits": bian_bits,
            "gua_ci": GUA_CI.get(bian_info["name"], ""),
            "is_liuchong": bian_info["name"] in LIUCHONG_GUA,
        }
    result["calendar"] = _calendar_window(dz["year"], dz["month"], dz["day"])
    result["analysis"] = _analyze(result)
    result["random"] = {"schema": "random-v1", "source": "manual", "purpose": "liuyao",
                        "algorithm": "external-tosses", "interaction": None}
    result["replay"] = {"schema": "liuyao-reading-v2", "tosses": list(tosses),
                        "category": category, "date": _local_fields(local),
                        "tz_name": tz_name, "fold": local.fold,
                        "time": deepcopy(result["time"]), "rules_sha256": _rules_sha256(),
                        "random": deepcopy(result["random"])}
    return result


def draw(question="", category="zonghe", date=None, *, tz_name="Asia/Shanghai",
         fold=None, seed=None, interaction=None):
    """Six throws of three independent fair coins, bottom line first.

    Yang=3 and yin=2 gives line probabilities 6/7/8/9 = 1/3/3/1 out of 8.
    An explicit seed is only a reproducible simulation mode.
    """
    _validate_category(category)
    local = _resolve_date(date, tz_name, fold)
    rng = DrawRandom("liuyao", seed=seed, interaction=interaction)
    tosses = [6 + sum(rng.randbelow(2) for _ in range(3)) for _ in range(6)]
    result = cast(tosses, question, category, _local_fields(local), tz_name=tz_name, fold=local.fold)
    result["random"] = deepcopy(rng.evidence)
    result["replay"]["random"] = deepcopy(rng.evidence)
    return result


def replay(snapshot, question=""):
    """Recompute a saved reading from original tosses, local time and rules."""
    if (not isinstance(snapshot, dict)
            or snapshot.get("schema") not in ("liuyao-reading-v1", "liuyao-reading-v2")
            or not isinstance(snapshot.get("random"), dict)
            or not isinstance(snapshot.get("date"), dict)
            or not {"year", "month", "day", "hour", "minute", "second"} <= set(snapshot["date"])
            or not isinstance(snapshot.get("tz_name"), str)
            or type(snapshot.get("fold")) is not int):
        raise ValueError("unknown or incomplete liuyao replay")
    validate_random_evidence(snapshot["random"], "liuyao", allow_manual=True)
    if snapshot["schema"] == "liuyao-reading-v2" and snapshot.get("rules_sha256") != _rules_sha256():
        raise ValueError("changed or missing liuyao rules/calendar version")
    result = cast(snapshot.get("tosses"), question, snapshot.get("category", "zonghe"),
                  snapshot["date"], tz_name=snapshot["tz_name"], fold=snapshot["fold"])
    if snapshot["schema"] == "liuyao-reading-v2" and snapshot.get("time") != result["time"]:
        raise ValueError("saved time differs from current timezone resolution")
    result["random"] = deepcopy(snapshot["random"])
    result["replay"] = deepcopy(snapshot)
    return result


def _analyze(result):
    """第 2 层：取用神、判旺衰/旬空、动爻生克 → 关键看点"""
    ben = result["ben"]
    lines = ben["lines"]
    dz = result["date"]
    yong_pos, cat = _yong_lines(result["category"], lines, ben["shi"], ben["ying"])
    yong_lines = [ln for ln in lines if ln["pos"] in yong_pos]

    comps = []
    yong_detail = []
    for ln in yong_lines:
        verdict, score, notes = _wang_shuai(ln["zhi_wx"], dz["month_zhi"], dz["day_zhi"])
        flags = []
        if ln["kong"]:
            flags.append("旬空")
        if ZHI_CHONG.get(ln["zhi"]) == dz["month_zhi"]:
            flags.append("月破")
        if ln["moving"]:
            flags.append("发动")
        if ln.get("huitou"):
            flags.append(ln["huitou"])
        yong_detail.append({
            "pos": ln["pos"], "liuqin": ln["liuqin"], "zhi": ln["zhi"], "zhi_wx": ln["zhi_wx"],
            "verdict": verdict, "score": score, "flags": flags, "notes": notes,
        })

    # 用神状态看点
    if yong_lines:
        for yd in yong_detail:
            w = 3 if (yd["verdict"] in ("旺", "偏旺") and "旬空" not in yd["flags"]) else 2
            extra = ("，" + "、".join(yd["flags"])) if yd["flags"] else ""
            comps.append({"name": f"用神{yd['liuqin']}·{yd['verdict']}", "weight": w,
                          "note": f"用神为{yd['liuqin']}（{yd['pos']}爻{yd['zhi']}{yd['zhi_wx']}），"
                                  f"逢月建{dz['month_zhi']}、日辰{dz['day_zhi']}论之{yd['verdict']}{extra}。"
                                  f"（{cat['note']}）"})
    else:
        comps.append({"name": "用神不上卦", "weight": 3,
                      "note": f"{cat['note']}，但该六亲未现于卦中（用神不上卦），"
                              f"需查伏神或视为事体无根、缘分未现。"})

    # 动爻对用神的生克
    yong_wx = yong_lines[0]["zhi_wx"] if yong_lines else None
    for ln in lines:
        if not ln["moving"]:
            continue
        rel = ""
        if yong_wx:
            if ln["zhi_wx"] == yong_wx:
                rel = "比助用神"
            elif WX_SHENG.get(ln["zhi_wx"]) == yong_wx:
                rel = "生扶用神（利）"
            elif WX_KE.get(ln["zhi_wx"]) == yong_wx:
                rel = "克制用神（不利）"
            elif WX_SHENG.get(yong_wx) == ln["zhi_wx"]:
                rel = "泄用神之气"
        w = 2 if "不利" in rel or "生扶" in rel else 1
        ht = ("，" + ln["huitou"]) if ln.get("huitou") else ""
        comps.append({"name": f"{ln['pos']}爻{ln['liuqin']}发动", "weight": w,
                      "note": f"{ln['pos']}爻{ln['liuqin']}（{ln['zhi']}{ln['zhi_wx']}）发动"
                              f"{('，'+rel) if rel else ''}{ht}"
                              f"{('，变出'+ln.get('bian_zhi','')+ln.get('bian_zhi_wx','')) if ln.get('bian_zhi') else ''}。"})

    # 世应、卦性看点
    shi_ln = next(ln for ln in lines if ln["shi"])
    ying_ln = next(ln for ln in lines if ln["ying"])
    comps.append({"name": "世应", "weight": 1,
                  "note": f"世爻在{shi_ln['pos']}爻（{shi_ln['liuqin']}{shi_ln['zhi']}"
                          f"{'·旬空' if shi_ln['kong'] else ''}），应爻在{ying_ln['pos']}爻"
                          f"（{ying_ln['liuqin']}{ying_ln['zhi']}{'·旬空' if ying_ln['kong'] else ''}）。"})
    if ben["is_liuchong"]:
        comps.append({"name": "六冲卦", "weight": 2,
                      "note": "本卦为六冲卦，主事来去快、易冲散反复；求稳定、长久之事多不利，急事速断可参。"})
    if not result["dong"]:
        comps.append({"name": "静卦", "weight": 1,
                      "note": "六爻安静无动爻，事态相对稳定，吉凶主要看用神旺衰与世应。"})
    if result.get("bian") and result["bian"]["is_liuchong"]:
        comps.append({"name": "变卦六冲", "weight": 1, "note": "变卦为六冲，结局易生变动反复。"})

    comps.sort(key=lambda x: x["weight"], reverse=True)
    return {
        "yong_shen": {"positions": yong_pos, "detail": yong_detail, "note": cat["note"]},
        "structures": {"compositions": comps},
    }


def tosses_from_yang_counts(counts):
    """把每掷阳面枚数(0-3)转为爻值 6-9（阳面=3、阴面=2、三钱之和）"""
    if (not isinstance(counts, (list, tuple)) or len(counts) != 6
            or any(type(value) is not int or not 0 <= value <= 3 for value in counts)):
        raise ValueError("需要 6 次三钱投掷的阳面数，每次为 0/1/2/3")
    return [6 + value for value in counts]
