import math
from pathlib import Path
import tempfile
import unittest

from desktop.places import search, resolve, nearby, search_data, get_place
from desktop.backend import Backend


class PlaceTest(unittest.TestCase):
    def test_provinces_pinyin_initials_context_and_typo_search(self):
        self.assertEqual(len(search_data()['provinces']), 31)
        for query, name in [('湖南', '湖南省'), ('hunan', '湖南省'), ('sichuan', '四川省'),
                            ('changsha', '长沙'), ('cs', '长沙'), ('hunan changsha', '长沙'),
                            ('shanghia', '上海'), ('niuyue', '纽约'), ('chongqing', '重庆')]:
            self.assertEqual(search(query)[0]['display_name'], name, query)
        province = search('湖南省')[0]
        self.assertEqual(province['kind'], 'province')
        self.assertEqual(province['precision'], 'region')
        self.assertTrue(province['approximate'])
        self.assertEqual(get_place(province['id'])['tz_name'], 'Asia/Shanghai')
        self.assertEqual(search('hunan changsha')[0]['region_name'], '湖南省')
        self.assertEqual(search('湖南省已经改名的旧镇')[0]['display_name'], '湖南省')
        self.assertEqual(search('ThisPlaceDoesNotExistAtAll'), [])
        self.assertEqual(search('乌鲁木齐')[0]['display_name'], '乌鲁木齐')
        self.assertEqual(search('乌鲁木齐')[0]['tz_name'], 'Asia/Shanghai')
        self.assertEqual(search('Hohhot')[0]['display_name'], '呼和浩特')

    def test_selected_place_controls_coordinates_zone_and_snapshot(self):
        with tempfile.TemporaryDirectory() as folder:
            b = Backend(Path(folder))
            ny = search('New York')[0]
            p = b.save_birthday({'name': '自动时区', 'datetime': '2000-06-15T12:30',
                                 'birth_place_id': ny['id'], 'tz_name': 'UTC', 'longitude': 0, 'latitude': 0})
            self.assertEqual(p['tz_name'], 'America/New_York')
            self.assertEqual(p['longitude'], ny['longitude'])
            record = b.calculate({**p, 'module': 'astro', 'tz_name': 'UTC'})
            self.assertEqual(record['inputs']['tz_name'], 'America/New_York')
            changed = b.save_birthday({**p, 'birth_place_id': search('湖南省')[0]['id']})
            self.assertEqual(changed['birth_place_kind'], 'province')
            self.assertEqual(changed['tz_name'], 'Asia/Shanghai')
            self.assertEqual(b.get(record['id']), record)
            with self.assertRaises(ValueError):
                b.save_birthday({**p, 'birth_place_id': 'not-a-place'})
            with self.assertRaises(ValueError):
                b.save_birthday({**p, 'datetime': '2024-03-10T02:30'})
            with self.assertRaises(ValueError):
                b.save_birthday({**p, 'datetime': '2024-11-03T01:30'})
            p = b.save_birthday({**p, 'datetime': '2024-11-03T01:30', 'fold': '1'})
            self.assertEqual(p['fold'], '1')

    def test_map_click_offers_nearby_named_cities_and_handles_dateline(self):
        for lon,lat,zone in [(121.4581,31.2222,'Asia/Shanghai'),(-74.006,40.7143,'America/New_York')]:
            choices=nearby(lon,lat)
            self.assertEqual(choices[0]['tz_name'],zone)
            self.assertLess(choices[0]['distance_km'],1)
            self.assertTrue(all(c['display_name'] and c['distance_km']<=500 for c in choices))
            self.assertEqual([c['distance_km'] for c in choices],sorted(c['distance_km'] for c in choices))
        self.assertEqual(nearby(-140,0),[])
        self.assertTrue(all(c['distance_km']<=500 for c in nearby(179.9,-16)))
        for lon,lat in [(181,0),(0,math.nan),(True,0)]:
            with self.assertRaises(ValueError):nearby(lon,lat)

    def test_person_color_is_validated_persisted_and_preserved_by_older_clients(self):
        with tempfile.TemporaryDirectory() as folder:
            b=Backend(Path(folder))
            p=b.save_birthday({'name':'代表色测试','datetime':'2000-08-16T04:00','color':'#8EDBCB'})
            self.assertEqual(Backend(Path(folder)).birthday(p['id'])['color'],'#8edbcb')
            older={k:v for k,v in p.items() if k!='color'}
            self.assertEqual(b.save_birthday(older)['color'],'#8edbcb')
            p=b.save_birthday({**p,'color':'#bba1ef'})
            self.assertEqual(p['color'],'#bba1ef')
            for bad in ['red','#abc','#12345600','var(--x)',123]:
                with self.assertRaises(ValueError):b.save_birthday({**p,'color':bad})
            self.assertEqual(b.birthday(p['id'])['color'],'#bba1ef')

    def test_city_search_english_chinese_and_duplicates(self):
        for name, zone in [('上海', 'Asia/Shanghai'), ('纽约', 'America/New_York'), ('London', 'Europe/London'), ('Tokyo', 'Asia/Tokyo'), ('Sydney', 'Australia/Sydney')]:
            self.assertEqual(search(name)[0]['tz_name'], zone, name)
        self.assertEqual(search(''), [])
        self.assertLessEqual(len(search('San')), 12)
        self.assertTrue(all('country' in p and 'region' in p for p in search('London')))

    def test_polygon_timezone_and_overlap_manual_choice(self):
        for lon, lat, zone in [(116.41, 39.9, 'Asia/Shanghai'), (-74.006, 40.713, 'America/New_York'), (139.69, 35.69, 'Asia/Tokyo'), (151.21, -33.87, 'Australia/Sydney')]:
            self.assertEqual(resolve(lon, lat)['tz_name'], zone)
        xinjiang = resolve(87.6, 43.8)
        self.assertEqual(xinjiang['tz_name'], 'Asia/Shanghai')
        self.assertIn('Asia/Urumqi', xinjiang['choices'])

    def test_invalid_coordinates_and_search(self):
        for lon, lat in [(181, 0), (0, 91), (math.nan, 0), (0, math.inf), (True, 0)]:
            with self.assertRaises(ValueError):
                resolve(lon, lat)
        with self.assertRaises(ValueError):
            search('x' * 121)

    def test_current_residence_does_not_change_birth_timezone_or_old_records(self):
        with tempfile.TemporaryDirectory() as folder:
            b = Backend(Path(folder))
            p = b.save_birthday({'name': '测试朋友', 'datetime': '2000-08-16T04:00', 'tz_name': 'Asia/Shanghai',
                                 'birth_place': '上海', 'longitude': 121.4581, 'latitude': 31.2222,
                                 'current_place': 'New York City', 'current_longitude': -74.006, 'current_latitude': 40.7143})
            self.assertEqual(p['tz_name'], 'Asia/Shanghai')
            self.assertEqual(b.birthdays('New York'), [p])
            self.assertEqual(Backend(Path(folder)).birthday(p['id']), p)
            p = b.save_birthday({**p, 'current_place': '', 'current_latitude': '', 'current_longitude': ''})
            self.assertIsNone(p['current_longitude'])
            self.assertEqual(p['longitude'], 121.4581)
            with self.assertRaises(ValueError):
                b.save_birthday({**p, 'current_latitude': 30})
            with self.assertRaises(ValueError):
                b.save_birthday({**p, 'current_latitude': 95, 'current_longitude': 100})

    def test_dst_checks_remain_for_automatic_city_timezone(self):
        with tempfile.TemporaryDirectory() as folder:
            b = Backend(Path(folder))
            base = {'name': 'DST 测试', 'tz_name': search('New York')[0]['tz_name'], 'longitude': -74.006, 'latitude': 40.713}
            with self.assertRaises(ValueError):
                b.save_birthday({**base, 'datetime': '2024-03-10T02:30'})
            with self.assertRaises(ValueError):
                b.save_birthday({**base, 'datetime': '2024-11-03T01:30'})
            p = b.save_birthday({**base, 'datetime': '2024-11-03T01:30', 'fold': '1'})
            self.assertEqual(p['fold'], '1')
