"""Deterministic Lahiri Jyotish with explicit traditional rule choices.

Uses existing pyswisseph; no PyJHora code or dependency is included.
D1/D9 use whole-sign houses; Parashari D9 uses the ninth harmonic.
"""
from datetime import datetime, timedelta, timezone
import swisseph as swe

from ..ephemeris import serialized
from ..timebase import resolve_local, time_record, wall_datetime

SIGNS = ("白羊", "金牛", "双子", "巨蟹", "狮子", "处女", "天秤", "天蝎", "射手", "摩羯", "水瓶", "双鱼")
SIGN_RULERS = ("Mars", "Venus", "Mercury", "Moon", "Sun", "Mercury",
               "Venus", "Mars", "Jupiter", "Saturn", "Saturn", "Jupiter")
GRAHAS = (("Sun", "太阳", swe.SUN), ("Moon", "月亮", swe.MOON),
          ("Mars", "火星", swe.MARS), ("Mercury", "水星", swe.MERCURY),
          ("Jupiter", "木星", swe.JUPITER), ("Venus", "金星", swe.VENUS),
          ("Saturn", "土星", swe.SATURN))
NAKSHATRAS = ("Ashwini", "Bharani", "Krittika", "Rohini", "Mrigashira", "Ardra",
              "Punarvasu", "Pushya", "Ashlesha", "Magha", "Purva Phalguni", "Uttara Phalguni",
              "Hasta", "Chitra", "Swati", "Vishakha", "Anuradha", "Jyeshtha", "Mula",
              "Purva Ashadha", "Uttara Ashadha", "Shravana", "Dhanishtha", "Shatabhisha",
              "Purva Bhadrapada", "Uttara Bhadrapada", "Revati")
DASHA_LORDS = ("Ketu", "Venus", "Sun", "Moon", "Mars", "Rahu", "Jupiter", "Saturn", "Mercury")
DASHA_YEARS = dict(zip(DASHA_LORDS, (7, 20, 6, 10, 7, 18, 16, 19, 17)))
YEAR_DAYS = {"sidereal": 365.25636, "julian": 365.25, "savana": 360.0}
_EPOCH = datetime(2000, 1, 1, 12, tzinfo=timezone.utc)


def _longitude(value):
    if (isinstance(value, bool) or not isinstance(value, (int, float))
            or not 0 <= value < 360):
        raise ValueError("longitude must be a finite number in [0, 360)")
    return value


def _position(longitude):
    index = int(longitude // 30)
    # Keep full precision for divisional and nakshatra boundaries.
    return {"longitude": longitude, "sign_idx": index, "sign": SIGNS[index],
            "degree": longitude - index * 30, "sign_lord": SIGN_RULERS[index]}


def nakshatra(longitude):
    """27 equal lunar mansions and four padas, from sidereal Aries 0°."""
    longitude = _longitude(longitude)
    span = 360 / 27
    index = min(26, int(longitude / span))
    fraction = (longitude - index * span) / span
    return {"index": index + 1, "name": NAKSHATRAS[index],
            "pada": min(4, int(fraction * 4) + 1), "lord": DASHA_LORDS[index % 9],
            "fraction_elapsed": fraction}


def navamsa_position(longitude):
    """Classical Parashari D9. Boundary classification precedes display formatting."""
    return _position((_longitude(longitude) * 9) % 360)


def _iso(jd):
    return (_EPOCH + timedelta(days=jd - 2451545.0)).isoformat()


def _period(lord, start, end, years):
    return {"lord": lord, "years": years, "start_jd": start, "end_jd": end,
            "start_utc": _iso(start), "end_utc": _iso(end)}


def vimshottari(birth_jd, moon_longitude, *, year="sidereal"):
    """One 120-year cycle from the natal mahadasha start, including pre-birth part.

    Nine mahadashas each contain nine antardashas. Periods are [start, end).
    Year length is a declared convention, not inferred from a calendar year.
    """
    if (isinstance(birth_jd, bool) or not isinstance(birth_jd, (int, float))
            or not 2415018 <= birth_jd <= 2488437):
        raise ValueError("birth_jd must be within the supported 1900..2100 era")
    if not isinstance(year, str) or year not in YEAR_DAYS:
        raise ValueError("year must be sidereal/julian/savana")
    mansion = nakshatra(moon_longitude)
    first = DASHA_LORDS.index(mansion["lord"])
    first_years = DASHA_YEARS[mansion["lord"]]
    year_days = YEAR_DAYS[year]
    cursor = birth_jd - mansion["fraction_elapsed"] * first_years * year_days
    major_periods = []
    running = None
    for offset in range(9):
        lord_index = (first + offset) % 9
        lord = DASHA_LORDS[lord_index]
        duration = DASHA_YEARS[lord]
        end = cursor + duration * year_days
        major = _period(lord, cursor, end, duration)
        subcursor = cursor
        children = []
        for step in range(9):
            sublord = DASHA_LORDS[(lord_index + step) % 9]
            years = duration * DASHA_YEARS[sublord] / 120
            subend = end if step == 8 else subcursor + years * year_days
            children.append(_period(sublord, subcursor, subend, years))
            if cursor <= birth_jd < end and subcursor <= birth_jd < subend:
                running = {"mahadasha": lord, "antardasha": sublord}
            subcursor = subend
        major["antardashas"] = children
        major_periods.append(major)
        cursor = end
    return {"system": "Vimshottari", "year": year, "year_days": year_days,
            "interval": "start-inclusive/end-exclusive", "at_birth": running,
            "birth_balance_years": first_years * (1 - mansion["fraction_elapsed"]),
            "mahadashas": major_periods}


def _varga(positions, lagna):
    asc = _position(lagna)
    points = {}
    for name, longitude in positions.items():
        point = _position(longitude)
        point["house"] = (point["sign_idx"] - asc["sign_idx"]) % 12 + 1
        points[name] = point
    houses = [{"house": number + 1, "sign_idx": (asc["sign_idx"] + number) % 12,
               "sign": SIGNS[(asc["sign_idx"] + number) % 12],
               "lord": SIGN_RULERS[(asc["sign_idx"] + number) % 12]}
              for number in range(12)]
    return {"lagna": asc, "points": points, "houses": houses}


def analyze_chart(chart):
    """Deterministic placements only; no imported western-aspect interpretation."""
    d1, d9 = chart["d1"], chart["d9"]
    lord = d1["lagna"]["sign_lord"]
    return {"lagna_lord": {"planet": lord, **d1["points"][lord]},
            "moon_nakshatra": chart["grahas"]["Moon"]["nakshatra"],
            "vargottama": [name for name in d1["points"]
                           if d1["points"][name]["sign_idx"] == d9["points"][name]["sign_idx"]]}


@serialized
def cast(year, month, day, hour, minute, lat, lon, tz_name="Asia/Kolkata", *,
         fold=None, node_mode="mean", dasha_year="sidereal"):
    """Lahiri geocentric nine-graha chart; civil local birth time → astronomical UTC.

    No true-solar correction is applied to the birth instant. D1 and D9 use
    whole-sign houses; Rahu/Ketu default to mean nodes. No present-time defaults.
    """
    civil = wall_datetime(year, month, day, hour, minute)
    if not 1900 <= year <= 2100:
        raise ValueError("年份须在 1900~2100 之间")
    for value, limit, label in ((lat, 90, "纬度"), (lon, 180, "经度")):
        if (isinstance(value, bool) or not isinstance(value, (int, float))
                or not -limit <= value <= limit or (label == "纬度" and abs(value) == 90)):
            raise ValueError(f"{label}超出有效范围")
    if node_mode not in ("mean", "true"):
        raise ValueError("node_mode 须为 mean/true")
    if not isinstance(dasha_year, str) or dasha_year not in YEAR_DAYS:
        raise ValueError("dasha_year 须为 sidereal/julian/savana")
    local = resolve_local(civil, tz_name, fold=fold)
    utc = local.astimezone(timezone.utc)
    jd = swe.julday(utc.year, utc.month, utc.day, utc.hour + utc.minute / 60 + utc.second / 3600)
    swe.set_sid_mode(swe.SIDM_LAHIRI)
    flags = swe.FLG_MOSEPH | swe.FLG_SPEED | swe.FLG_SIDEREAL
    _, ayanamsa = swe.get_ayanamsa_ex_ut(jd, swe.FLG_MOSEPH)
    _, angles = swe.houses_ex(jd, lat, lon, b"W", swe.FLG_SIDEREAL)
    lagna = angles[0] % 360
    grahas = {}
    planets = GRAHAS + (("Rahu", "罗睺", swe.MEAN_NODE if node_mode == "mean" else swe.TRUE_NODE),)
    for name, label, planet in planets:
        values, returned_flags = swe.calc_ut(jd, planet, flags)
        if not returned_flags & swe.FLG_SIDEREAL:
            raise RuntimeError("Swiss Ephemeris did not return sidereal positions")
        longitude = values[0] % 360
        grahas[name] = {"name": label, **_position(longitude), "speed": values[3],
                        "retrograde": values[3] < 0, "nakshatra": nakshatra(longitude)}
    ketu = (grahas["Rahu"]["longitude"] + 180) % 360
    grahas["Ketu"] = {"name": "计都", **_position(ketu), "speed": grahas["Rahu"]["speed"],
                      "retrograde": grahas["Rahu"]["retrograde"], "nakshatra": nakshatra(ketu)}
    positions = {name: point["longitude"] for name, point in grahas.items()}
    d1 = _varga(positions, lagna)
    d9 = _varga({name: navamsa_position(value)["longitude"] for name, value in positions.items()},
                navamsa_position(lagna)["longitude"])
    chart = {"module": "jyotish",
             "input": {"year": year, "month": month, "day": day, "hour": hour, "minute": minute,
                       "lat": lat, "lon": lon, "tz_name": tz_name, "fold": local.fold,
                       "node_mode": node_mode, "dasha_year": dasha_year},
             "time": time_record(local, basis="utc"), "julian_day_ut": jd,
             "rules": {"schema": "jyotish-rules-v1", "ephemeris": "moshier",
                       "swiss_ephemeris_version": swe.version, "zodiac": "sidereal",
                       "ayanamsa": "Lahiri", "ayanamsa_id": swe.SIDM_LAHIRI,
                       "ayanamsa_degrees": ayanamsa, "node_mode": node_mode,
                       "house_system": "whole-sign", "d9": "parashari-ninth-harmonic",
                       "dasha_year": dasha_year, "dasha_year_days": YEAR_DAYS[dasha_year]},
             "grahas": grahas, "d1": d1, "d9": d9,
             "vimshottari": vimshottari(jd, positions["Moon"], year=dasha_year),
             "summary": f"{d1['lagna']['sign']}上升 · 月亮{d1['points']['Moon']['sign']} · {grahas['Moon']['nakshatra']['name']}"}
    chart["analysis"] = analyze_chart(chart)
    return chart
