"""Offline city search and geographic IANA zone suggestions; no network calls."""
from functools import lru_cache
import json
import math
from pathlib import Path
import unicodedata
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


def normalize(value):
    return ''.join(c for c in unicodedata.normalize('NFKD', value.casefold()) if not unicodedata.combining(c)).strip()


@lru_cache(maxsize=1)
def cities():
    return json.loads((Path(__file__).parent / 'web/assets/geography/cities.json').read_text(encoding='utf-8'))


@lru_cache(maxsize=1)
def search_data():
    return json.loads((Path(__file__).parent / 'web/assets/geography/place-search.json').read_text(encoding='utf-8'))


def compact(value):
    return ''.join(c for c in normalize(value).replace('ü', 'v') if c.isalnum())


@lru_cache(maxsize=1)
def place_lookup():
    return {p['id']: p for p in [*cities(), *search_data()['provinces']]}


def get_place(identity):
    try: return result_view(place_lookup()[identity])
    except (KeyError, TypeError): raise ValueError('地点候选已失效，请重新搜索并选择') from None


def result_view(c, query=''):
    names = [a for a in c['aliases'] if len(a) > 1 and any('\u4e00' <= ch <= '\u9fff' for ch in a)]
    preferred = [a for a in names if query and query in compact(a)]
    display = c.get('display_name') or search_data()['display_names'].get(c['id']) or min(preferred or names, key=len, default=c['name'])
    region = search_data()['region_names'].get(c['region'], c['region']) if c['country'] == 'CN' else c['region']
    return {**{k: c[k] for k in ('id', 'name', 'latitude', 'longitude', 'country', 'region', 'tz_name')},
            'tz_name': 'Asia/Shanghai' if c['country'] == 'CN' else c['tz_name'],
            'display_name': display, 'region_name': region, 'kind': c.get('kind', 'city'),
            'precision': c.get('precision', 'city'), 'approximate': c.get('approximate', False)}


@lru_cache(maxsize=1)
def search_index():
    extra = search_data()['keys']
    return [(c, list({compact(n) for n in [*c['aliases'], *extra.get(c['id'], [])] if n}), [compact(n) for n in [c['name'], *search_data()['primary'].get(c['id'], [])]])
            for c in [*cities(), *search_data()['provinces']]]


def near_spelling(a, b):
    """Bounded Damerau distance: accept one typo, or two for long names."""
    limit = 2 if len(a) >= 8 else 1
    if abs(len(a) - len(b)) > limit or not b or a[0] != b[0]: return False
    previous = list(range(len(b) + 1)); older = None
    for i, x in enumerate(a, 1):
        row = [i]
        for j, y in enumerate(b, 1):
            v = min(row[-1] + 1, previous[j] + 1, previous[j-1] + (x != y))
            if older is not None and j > 1 and x == b[j-2] and a[i-2] == y: v = min(v, older[j-2] + 1)
            row.append(v)
        if min(row) > limit: return False
        older, previous = previous, row
    return previous[-1] <= limit


def search(query):
    if not isinstance(query, str) or len(query) > 120:
        raise ValueError('地名查询最长 120 字')
    query = compact(query)
    if not query:
        return []
    matches = []
    for c, names, primary in search_index():
        rank = 0 if query in primary else 1 if query in names else 2 if any(n.startswith(query) for n in primary) else 3 if any(n.startswith(query) for n in names) else 4 if any(query in n for n in names) else 5
        if rank < 5:
            matches.append((rank, -c['population'], c))
    if not matches and query.isascii() and 4 <= len(query) <= 32:
        for c, names, primary in search_index():
            if any(n.isascii() and near_spelling(query, n) for n in names): matches.append((5, -c['population'], c))
    if not matches:
        # An obsolete town after a recognizable province still offers an explicit coarse candidate.
        for c, names, primary in search_index():
            if c.get('kind') == 'province' and any(len(n) >= 2 and query.startswith(n) for n in primary):
                matches.append((6, -c['population'], c))
    matches.sort(key=lambda item: item[:2])
    return [result_view(c, query) for _, _, c in matches[:12]]



def resolve(longitude, latitude):
    if (isinstance(longitude, bool) or isinstance(latitude, bool)):
        raise ValueError('请提供有效经纬度')
    lon, lat = float(longitude), float(latitude)
    if not math.isfinite(lon) or not math.isfinite(lat) or abs(lon) > 180 or abs(lat) > 90:
        raise ValueError('经纬度超出范围')
    from tzfpy import get_tzs
    choices = []
    for name in get_tzs(lon, lat):
        try:
            ZoneInfo(name)
            choices.append(name)
        except ZoneInfoNotFoundError:
            pass
    # A suggestion is not silently coerced to the nearest city's zone or UTC.
    return {'longitude': round(lon, 4), 'latitude': round(lat, 4),
            'tz_name': 'Asia/Shanghai' if 'Asia/Shanghai' in choices else choices[0] if choices else None,
            'choices': choices, 'approximate': True}


def nearby(longitude, latitude):
    """Offer named cities for a map click; never silently select a distant city."""
    if isinstance(longitude, bool) or isinstance(latitude, bool):
        raise ValueError('请选择有效地图位置')
    lon, lat = float(longitude), float(latitude)
    if not math.isfinite(lon) or not math.isfinite(lat) or abs(lon) > 180 or abs(lat) > 90:
        raise ValueError('地图位置超出范围')
    def distance(c):
        a, b = math.radians(lat), math.radians(c['latitude'])
        h = math.sin((b-a)/2)**2 + math.cos(a)*math.cos(b)*math.sin(math.radians(c['longitude']-lon)/2)**2
        return 6371*2*math.asin(math.sqrt(min(1, h)))
    matches = sorted(((distance(c), c) for c in cities()), key=lambda item:item[0])[:6]
    result = []
    for km, c in matches:
        if km > 500:
            continue
        result.append({**result_view(c), 'distance_km': round(km, 1)})
    return result
