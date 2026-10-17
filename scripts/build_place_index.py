"""Build offline province/pinyin search data; pypinyin is build-time only."""
import hashlib
import json
from pathlib import Path
import re
import sys
import urllib.request
import zipfile

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / '.cache/place-data-tools'))
from pypinyin import lazy_pinyin
from opencc import OpenCC

LABELS = dict(zip('01 02 03 04 05 06 07 08 09 10 11 12 13 14 15 16 18 19 20 21 22 23 24 25 26 28 29 30 31 32 33'.split(),
                 '安徽省 浙江省 江西省 江苏省 吉林省 青海省 福建省 黑龙江省 河南省 河北省 湖南省 湖北省 新疆维吾尔自治区 西藏自治区 甘肃省 广西壮族自治区 贵州省 辽宁省 内蒙古自治区 宁夏回族自治区 北京市 上海市 山西省 山东省 陕西省 天津市 云南省 广东省 海南省 四川省 重庆市'.split()))


def main():
    target = ROOT / 'desktop/web/assets/geography'
    raw = ROOT / '.cache/geonames-CN.zip'
    if not raw.exists():
        urllib.request.urlretrieve('https://download.geonames.org/export/dump/CN.zip', raw)
    with zipfile.ZipFile(raw) as archive:
        provinces = []
        for line in archive.read('CN.txt').decode('utf-8').splitlines():
            r = line.split('\t')
            if r[7] != 'ADM1' or r[10] not in LABELS:
                continue
            label = LABELS[r[10]]
            short = re.sub(r'(维吾尔自治区|壮族自治区|回族自治区|自治区|省|市)$', '', label)
            provinces.append(dict(id='region-' + r[0], name=r[1], display_name=label,
                                  aliases=list(dict.fromkeys([label, short, r[1], r[2], *r[3].split(',')])),
                                  latitude=float(r[4]), longitude=float(r[5]), country='CN', region=r[10],
                                  region_name=label, tz_name='Asia/Shanghai', population=int(r[14] or 0),
                                  kind='province', precision='region', approximate=True))
    assert len(provinces) == 31
    cities = json.loads((target / 'cities.json').read_text(encoding='utf-8'))
    keys, primary, display_names = {}, {}, {}
    converter = OpenCC('t2s')
    for place in [*cities, *provinces]:
        aliases = list(dict.fromkeys(converter.convert(a) for a in place['aliases']
                                    if re.search('[\u4e00-\u9fff]', a) and not re.search('[\u3040-\u30ff\uac00-\ud7af]', a)))
        if aliases:
            # Prefer the Chinese alias whose pinyin matches the primary romanized city name.
            roman = re.sub('[^a-z]', '', place['name'].lower())
            preferred = [a for a in aliases if ''.join(lazy_pinyin(a)) == roman]
            canonical = place.get('display_name') or (min(preferred, key=len) if preferred else aliases[0])
            display_names[place['id']] = canonical
            py = lazy_pinyin(canonical)
            primary[place['id']] = [canonical, ''.join(py), ''.join(s[0] for s in py if s)]
            if place.get('kind') == 'province' and canonical.endswith(('省', '自治区')):
                short = re.sub(r'(维吾尔自治区|壮族自治区|回族自治区|自治区|省)$', '', canonical)
                py = lazy_pinyin(short)
                primary[place['id']].extend([short, ''.join(py), ''.join(s[0] for s in py if s)])
        terms = set()
        for name in aliases:
            syllables = lazy_pinyin(name)
            terms.add(''.join(syllables))
            terms.add(''.join(s[0] for s in syllables if s))
        if place['country'] == 'CN':
            region = LABELS.get(place['region'], '')
            short = re.sub(r'(维吾尔自治区|壮族自治区|回族自治区|自治区|省|市)$', '', region)
            for name in aliases:
                for prefix in [region, short]:
                    if not prefix or name.startswith(prefix): continue
                    terms.add(prefix + name)
                    py = lazy_pinyin(prefix + name)
                    terms.add(''.join(py))
                    terms.add(''.join(s[0] for s in py if s))
        if terms: keys[place['id']] = sorted(terms)
    payload = {'schema': 'place-search-v1', 'region_names': LABELS, 'provinces': provinces, 'keys': keys,
               'primary': primary, 'display_names': display_names}
    output = target / 'place-search.json'
    output.write_text(json.dumps(payload, ensure_ascii=False, separators=(',', ':')), encoding='utf-8')
    metadata = {'sources': ['https://download.geonames.org/export/dump/CN.zip', 'https://pypi.org/project/pypinyin/0.55.0/'],
                'geonames_archive_sha256': hashlib.sha256(raw.read_bytes()).hexdigest(),
                'output_sha256': hashlib.sha256(output.read_bytes()).hexdigest(), 'provinces': len(provinces),
                'indexed_places': len(keys), 'pypinyin': '0.55.0', 'opencc-python-reimplemented': '0.1.7', 'runtime_dependency': False,
                'precision': 'Province coordinates are GeoNames ADM1 reference points, not a precise birthplace.'}
    (target / 'place-search-manifest.json').write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(metadata, ensure_ascii=False))


if __name__ == '__main__': main()
