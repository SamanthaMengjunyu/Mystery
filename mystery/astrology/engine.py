"""
星盘（西洋占星本命盘）核心服务

设计与八字三层架构对齐：
  L1 排盘：用瑞士星历(pyswisseph, Moshier 内置星历，零数据文件)算行星黄经、宫位、相位——真天文，零 LLM。
  L2 结构：元素/三态平衡、上升日月「大三件」、命主星、星群(Stellium)、
           相位格局(大三角/T三角/大十字/Yod)、半球侧重——确定性几何识别，零 LLM。
  L3 解读：复用 mystery/llm（DeepSeek 流式），只组织语言、不参与排盘。

出生时刻经 zoneinfo 历史时区换算为 UTC（含夏令时）后送星历。
"""
import itertools
from zoneinfo import ZoneInfo
from ..timebase import resolve_local, time_record, wall_datetime
from ..ephemeris import serialized
import swisseph as swe

# ── 基础常量 ────────────────────────────────────────────────────────────
SIGNS = ["白羊", "金牛", "双子", "巨蟹", "狮子", "处女",
         "天秤", "天蝎", "射手", "摩羯", "水瓶", "双鱼"]
SIGN_EN = ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
           "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"]
SIGN_ELEMENT = ["火", "土", "风", "水"] * 3          # 白羊火、金牛土、双子风、巨蟹水…循环
SIGN_MODALITY = ["本位", "固定", "变动"] * 4         # 白羊本位、金牛固定、双子变动…循环
# 传统守护星（用于命主星）
SIGN_RULER = ["火星", "金星", "水星", "月亮", "太阳", "水星",
              "金星", "火星", "木星", "土星", "土星", "木星"]

PLANETS = [
    ("太阳", swe.SUN), ("月亮", swe.MOON), ("水星", swe.MERCURY),
    ("金星", swe.VENUS), ("火星", swe.MARS), ("木星", swe.JUPITER),
    ("土星", swe.SATURN), ("天王星", swe.URANUS), ("海王星", swe.NEPTUNE),
    ("冥王星", swe.PLUTO), ("北交点", swe.MEAN_NODE),
]
# 元素/三态计权（个人行星与三轴权重高）
POINT_WEIGHT = {
    "太阳": 3, "月亮": 3, "上升": 3, "水星": 2, "金星": 2, "火星": 2,
    "木星": 1.5, "土星": 1.5, "天王星": 1, "海王星": 1, "冥王星": 1, "中天": 1, "北交点": 0.5,
}

# 主要相位：角度 → (名称, 容许度)
ASPECTS = {0: ("合相", 8), 60: ("六分", 6), 90: ("刑相", 7),
           120: ("拱相", 8), 180: ("冲相", 8)}
QUINCUNX = (150, 3)   # 梅花相，用于 Yod

HOUSE_SYSTEMS = {"P": "Placidus（普拉西德，主流）", "W": "Whole Sign（整宫，古典）",
                 "K": "Koch（科赫）", "E": "Equal（等宫）"}

# 城市地理：纬度、经度、时区名（占星需纬度与时区）
CITY_GEO = {
    "北京": (39.90, 116.41, "Asia/Shanghai"), "上海": (31.23, 121.47, "Asia/Shanghai"),
    "天津": (39.13, 117.20, "Asia/Shanghai"), "重庆": (29.56, 106.55, "Asia/Shanghai"),
    "广州": (23.13, 113.26, "Asia/Shanghai"), "深圳": (22.54, 114.06, "Asia/Shanghai"),
    "香港": (22.32, 114.17, "Asia/Hong_Kong"), "澳门": (22.19, 113.55, "Asia/Macau"),
    "杭州": (30.27, 120.16, "Asia/Shanghai"), "南京": (32.06, 118.78, "Asia/Shanghai"),
    "苏州": (31.30, 120.62, "Asia/Shanghai"), "武汉": (30.59, 114.30, "Asia/Shanghai"),
    "成都": (30.66, 104.07, "Asia/Shanghai"), "西安": (34.27, 108.95, "Asia/Shanghai"),
    "郑州": (34.75, 113.62, "Asia/Shanghai"), "济南": (36.65, 117.00, "Asia/Shanghai"),
    "长沙": (28.23, 112.94, "Asia/Shanghai"), "南昌": (28.68, 115.86, "Asia/Shanghai"),
    "合肥": (31.82, 117.23, "Asia/Shanghai"), "福州": (26.07, 119.30, "Asia/Shanghai"),
    "厦门": (24.48, 118.08, "Asia/Shanghai"), "昆明": (25.04, 102.83, "Asia/Shanghai"),
    "贵阳": (26.65, 106.71, "Asia/Shanghai"), "南宁": (22.82, 108.37, "Asia/Shanghai"),
    "海口": (20.04, 110.20, "Asia/Shanghai"), "石家庄": (38.04, 114.51, "Asia/Shanghai"),
    "太原": (37.87, 112.55, "Asia/Shanghai"), "沈阳": (41.81, 123.43, "Asia/Shanghai"),
    "长春": (43.82, 125.32, "Asia/Shanghai"), "哈尔滨": (45.80, 126.53, "Asia/Shanghai"),
    "呼和浩特": (40.84, 111.75, "Asia/Shanghai"), "兰州": (36.06, 103.83, "Asia/Shanghai"),
    "西宁": (36.62, 101.78, "Asia/Shanghai"), "银川": (38.49, 106.27, "Asia/Shanghai"),
    "乌鲁木齐": (43.83, 87.62, "Asia/Shanghai"), "拉萨": (29.65, 91.14, "Asia/Shanghai"),
    "台北": (25.03, 121.56, "Asia/Taipei"),
}


def _norm(deg):
    return deg % 360.0


def _sign_of(lon):
    """黄经 → (星座索引, 星座内度数)"""
    lon = _norm(lon)
    idx = int(lon // 30)
    return idx, lon % 30


def _angle(a, b):
    """两黄经最小夹角 0~180"""
    d = abs(_norm(a) - _norm(b)) % 360
    return min(d, 360 - d)


def _assign_house(lon, cusps):
    """黄经落在第几宫（cusps 为 1..12 宫起点黄经，列表长度 12）"""
    lon = _norm(lon)
    for i in range(12):
        a = cusps[i]
        b = cusps[(i + 1) % 12]
        if a <= b:
            if a <= lon < b:
                return i + 1
        else:                       # 跨 0°
            if lon >= a or lon < b:
                return i + 1
    return 1


def to_utc(year, month, day, hour, minute, tz_name, *, fold=None):
    """本地出生时刻 → UTC datetime（按历史时区，含夏令时）"""
    local = resolve_local(wall_datetime(year, month, day, hour, minute), tz_name, fold=fold)
    return local.astimezone(ZoneInfo("UTC"))


@serialized
def compute_chart(year, month, day, hour, minute, lat, lon, tz_name, house_system="P", *, fold=None):
    """L1 排盘：返回行星、上升中天、宫位、相位"""
    civil = wall_datetime(year, month, day, hour, minute)
    if not 1900 <= year <= 2100:
        raise ValueError("年份须在 1900~2100 之间")
    for value, limit, label in ((lat, 90, "纬度"), (lon, 180, "经度")):
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not -limit <= value <= limit:
            raise ValueError(f"{label}须为 -{limit}~{limit} 之间的数值")
    if not isinstance(house_system, str) or house_system not in HOUSE_SYSTEMS:
        raise ValueError("宫制须为 P/W/K/E")
    local = resolve_local(civil, tz_name, fold=fold)
    utc = local.astimezone(ZoneInfo("UTC"))
    jd = swe.julday(utc.year, utc.month, utc.day,
                    utc.hour + utc.minute / 60 + utc.second / 3600)
    flags = swe.FLG_MOSEPH | swe.FLG_SPEED

    hsys = house_system.encode() if isinstance(house_system, str) else house_system
    cusps_raw, ascmc = swe.houses(jd, lat, lon, hsys)
    cusps = list(cusps_raw[:12])

    points = {}   # name → {lon, sign, sign_idx, deg, house, retro}

    def put(name, lon_val, speed=None):
        idx, deg = _sign_of(lon_val)
        points[name] = {
            "lon": round(_norm(lon_val), 3), "sign": SIGNS[idx], "sign_idx": idx,
            "deg": round(deg, 2), "house": _assign_house(lon_val, cusps),
            "retro": (speed is not None and speed < 0),
            "element": SIGN_ELEMENT[idx], "modality": SIGN_MODALITY[idx],
        }

    for name, pid in PLANETS:
        xx, _ = swe.calc_ut(jd, pid, flags)
        put(name, xx[0], xx[3])
    put("上升", ascmc[0])
    put("中天", ascmc[1])

    houses = []
    for i, c in enumerate(cusps):
        idx, deg = _sign_of(c)
        houses.append({"house": i + 1, "lon": round(_norm(c), 3),
                       "sign": SIGNS[idx], "deg": round(deg, 2)})

    # 相位（行星 + 三轴；北交点纳入）
    aspect_pts = [n for n, _ in PLANETS] + ["上升", "中天"]
    aspects = []
    for a, b in itertools.combinations(aspect_pts, 2):
        ang = _angle(points[a]["lon"], points[b]["lon"])
        for base, (nm, orb) in ASPECTS.items():
            if abs(ang - base) <= orb:
                aspects.append({"p1": a, "p2": b, "type": nm, "angle": base,
                                "orb": round(abs(ang - base), 2)})
                break
    aspects.sort(key=lambda x: x["orb"])

    return {
        "utc": utc.strftime("%Y-%m-%d %H:%M UTC"),
        "time": time_record(local, basis="utc"),
        "rules": {"schema": "astrology-rules-v1", "zodiac": "tropical",
                  "ephemeris": "moshier", "house_system": house_system},
        "house_system": HOUSE_SYSTEMS.get(house_system, house_system),
        "points": points, "houses": houses, "aspects": aspects,
        "asc_sign": points["上升"]["sign"], "mc_sign": points["中天"]["sign"],
        "sun_sign": points["太阳"]["sign"], "moon_sign": points["月亮"]["sign"],
    }


# ── L2 结构识别 ─────────────────────────────────────────────────────────
def _balance(points):
    """元素与三态加权平衡"""
    elem = {"火": 0.0, "土": 0.0, "风": 0.0, "水": 0.0}
    modal = {"本位": 0.0, "固定": 0.0, "变动": 0.0}
    for name, w in POINT_WEIGHT.items():
        p = points.get(name)
        if not p:
            continue
        elem[p["element"]] += w
        modal[p["modality"]] += w
    elem = {k: round(v, 1) for k, v in elem.items()}
    modal = {k: round(v, 1) for k, v in modal.items()}
    dom_elem = max(elem, key=elem.get)
    lack_elem = min(elem, key=elem.get)
    dom_modal = max(modal, key=modal.get)
    return {"element": elem, "modality": modal, "dom_element": dom_elem,
            "lack_element": lack_elem, "dom_modality": dom_modal}


def _aspect_patterns(points, aspects):
    """相位格局：星群/大三角/T三角/大十字/Yod"""
    pats = []
    planets = [n for n, _ in PLANETS if n != "北交点"]

    # 星群 Stellium：同星座 ≥3 颗（含日月不含交点）
    by_sign = {}
    for n in planets:
        by_sign.setdefault(points[n]["sign"], []).append(n)
    for sign, members in by_sign.items():
        if len(members) >= 3:
            pats.append({"name": f"{sign}星群", "type": "Stellium",
                         "members": members,
                         "note": f"{'、'.join(members)}集中于{sign}，该领域能量高度聚焦、是命盘重心。"})

    def has(a, b, base, orb):
        return _angle(points[a]["lon"], points[b]["lon"]) <= base + orb and \
               _angle(points[a]["lon"], points[b]["lon"]) >= base - orb

    trine = lambda a, b: abs(_angle(points[a]["lon"], points[b]["lon"]) - 120) <= 7
    sextile = lambda a, b: abs(_angle(points[a]["lon"], points[b]["lon"]) - 60) <= 5
    square = lambda a, b: abs(_angle(points[a]["lon"], points[b]["lon"]) - 90) <= 6
    oppo = lambda a, b: abs(_angle(points[a]["lon"], points[b]["lon"]) - 180) <= 7
    quin = lambda a, b: abs(_angle(points[a]["lon"], points[b]["lon"]) - 150) <= 3

    for a, b, c in itertools.combinations(planets, 3):
        if trine(a, b) and trine(b, c) and trine(a, c):
            pats.append({"name": "大三角", "type": "Grand Trine", "members": [a, b, c],
                         "note": f"{a}-{b}-{c}互成拱相(120°)，天赋顺畅、易成自洽循环，但也可能因太顺而惰性。"})
        # T 三角：一对冲相，第三点同刑两端
        for apex, (x, y) in [(a, (b, c)), (b, (a, c)), (c, (a, b))]:
            if oppo(x, y) and square(apex, x) and square(apex, y):
                pats.append({"name": "T三角", "type": "T-Square",
                             "members": [x, y, apex], "apex": apex,
                             "note": f"{x}冲{y}、{apex}为支点双刑——张力集中于{apex}，是动力与困境的焦点。"})
                break
        # Yod：一对六分，第三点同梅花两端
        for apex, (x, y) in [(a, (b, c)), (b, (a, c)), (c, (a, b))]:
            if sextile(x, y) and quin(apex, x) and quin(apex, y):
                pats.append({"name": "Yod(上帝之指)", "type": "Yod",
                             "members": [x, y, apex], "apex": apex,
                             "note": f"{x}与{y}六分、共同梅花相指向{apex}——{apex}是需反复调整的命运焦点。"})
                break

    # 大十字：两组互不相干的对冲，且四点交叉互刑（严格）
    done = False
    for combo in itertools.combinations(planets, 4):
        ps = list(combo)
        opps = [(i, j) for i, j in itertools.combinations(ps, 2) if oppo(i, j)]
        for o1, o2 in itertools.combinations(opps, 2):
            if set(o1) & set(o2):
                continue                      # 必须是 4 颗不同星
            a, c = o1
            b, d = o2
            if square(a, b) and square(a, d) and square(c, b) and square(c, d):
                pats.append({"name": "大十字", "type": "Grand Cross", "members": ps,
                             "note": f"{'、'.join(ps)}构成大十字，四方张力极强、动力充沛但易内耗。"})
                done = True
                break
        if done:
            break
    return pats


def _hemisphere(points):
    """半球侧重（个人 vs 社会、自我 vs 关系）"""
    south = sum(1 for n, _ in PLANETS if n != "北交点" and points[n]["house"] >= 7)  # 7-12 地平上
    north = sum(1 for n, _ in PLANETS if n != "北交点" and points[n]["house"] <= 6)
    east = sum(1 for n, _ in PLANETS if n != "北交点" and points[n]["house"] in (10, 11, 12, 1, 2, 3))
    west = sum(1 for n, _ in PLANETS if n != "北交点" and points[n]["house"] in (4, 5, 6, 7, 8, 9))
    notes = []
    if south >= north + 3:
        notes.append("行星多居地平之上(7-12宫)：偏外向、重社会舞台与他人。")
    elif north >= south + 3:
        notes.append("行星多居地平之下(1-6宫)：偏内向、重自我建构与私域。")
    if east >= west + 3:
        notes.append("行星偏东(自我半球)：自主性强、由己出发。")
    elif west >= east + 3:
        notes.append("行星偏西(关系半球)：易受他人与环境牵引、重关系。")
    return {"south": south, "north": north, "east": east, "west": west, "notes": notes}


def analyze_chart(chart):
    """L2 结构分析，返回分析字典 + 关键看点（按重要度）"""
    points = chart["points"]
    bal = _balance(points)
    patterns = _aspect_patterns(points, chart["aspects"])
    hemi = _hemisphere(points)

    # 命主星（上升星座守护星）及其落点
    asc_idx = points["上升"]["sign_idx"]
    ruler = SIGN_RULER[asc_idx]
    rp = points.get(ruler)
    chart_ruler = {"planet": ruler,
                   "placement": (f"{rp['sign']}{rp['deg']:.0f}°·第{rp['house']}宫" if rp else "")}

    big_three = {"sun": chart["sun_sign"], "moon": chart["moon_sign"], "asc": chart["asc_sign"]}

    # 紧密相位（容许度<2°，且涉及日月上升）到的，作为重点
    tight = [a for a in chart["aspects"] if a["orb"] < 2
             and (a["p1"] in ("太阳", "月亮", "上升") or a["p2"] in ("太阳", "月亮", "上升"))]

    # 关键看点加权
    comps = []
    for p in patterns:
        w = 3 if p["type"] in ("Stellium", "Grand Cross", "T-Square") else 2
        comps.append({"name": p["name"], "note": p["note"], "weight": w})
    # 元素显著失衡
    ev = bal["element"]
    if max(ev.values()) >= 2 * (min(ev.values()) + 0.1):
        comps.append({"name": f"{bal['dom_element']}相过重·缺{bal['lack_element']}",
                      "note": f"元素偏向{bal['dom_element']}、{bal['lack_element']}相薄弱，性格与行事明显偏色，需补足{bal['lack_element']}相之质。",
                      "weight": 2})
    comps.append({"name": f"大三件 日{big_three['sun']}·月{big_three['moon']}·升{big_three['asc']}",
                  "note": "太阳(自我核心)、月亮(情感本能)、上升(对外面貌)构成人格三轴。", "weight": 2})
    # 到日月升的紧密相位（最定义人格）
    _asp_mean = {"合相": "融合强化", "冲相": "对立张力", "刑相": "摩擦与动力",
                 "拱相": "顺畅天赋", "六分": "机会与协作"}
    for t in tight[:3]:
        comps.append({"name": f"{t['p1']}{t['type']}{t['p2']}",
                      "note": f"{t['p1']}与{t['p2']}成{t['type']}(差{t['orb']}°)，{_asp_mean.get(t['type'],'')}——紧密相位，影响显著。",
                      "weight": 2})
    if chart_ruler["placement"]:
        comps.append({"name": f"命主星{ruler}落{rp['sign']}{rp['house']}宫",
                      "note": f"上升{points['上升']['sign']}的守护星为{ruler}，落{chart_ruler['placement']}，主导命盘走向与人生重心。",
                      "weight": 1})
    for n in hemi["notes"]:
        comps.append({"name": "半球侧重", "note": n, "weight": 1})
    # 出生时间敏感性（始终提示）
    comps.append({"name": "出生时间敏感", "note": "上升点每4分钟移约1°，宫位与上升/中天高度依赖精确出生时间；时间存疑则宫位结论需打折，仅行星星座较稳。",
                  "weight": 2})

    comps.sort(key=lambda c: -c["weight"])
    highlights = [c["name"] for c in comps if c["weight"] >= 2][:7]

    return {
        "balance": bal, "big_three": big_three, "chart_ruler": chart_ruler,
        "patterns": patterns, "hemisphere": hemi, "tight_aspects": tight,
        "structures": {"compositions": comps, "highlights": highlights},
        "disclaimer": "星盘以瑞士星历(Moshier)精算，结构为确定性几何识别；宫位依出生时间与宫制流派，供参考。",
    }


def cast(year, month, day, hour, minute, lat, lon, tz_name="Asia/Shanghai",
         house_system="P", name="", *, fold=None):
    """主入口：排盘 + 结构分析"""
    chart = compute_chart(year, month, day, hour, minute, lat, lon, tz_name, house_system, fold=fold)
    chart["analysis"] = analyze_chart(chart)
    chart["input"] = {"year": year, "month": month, "day": day, "hour": hour,
                      "minute": minute, "lat": lat, "lon": lon, "tz": tz_name,
                      "house_system": house_system, "name": name, "fold": chart["time"]["fold"]}
    return chart
