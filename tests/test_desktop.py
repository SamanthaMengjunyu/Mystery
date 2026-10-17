"""Desktop integration: real engines, private shuffle boundary, persistence and local HTTP auth."""
import copy
import http.cookiejar
import json
from pathlib import Path
import tempfile
import threading
import time
import unittest
from unittest.mock import patch
import urllib.error
import urllib.request

from desktop.backend import Backend, MODULES
from desktop.app import create_server


class DesktopTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.backend = Backend(Path(self.tmp.name))

    def tearDown(self):
        self.tmp.cleanup()

    def p(self, module, **kwargs):
        return {"module": module, "datetime": "2000-08-16T04:00", "first": 34, "second": 43, "third": 1, **kwargs}

    def test_all_modules_and_offline_prompts(self):
        for module in MODULES:
            with self.subTest(module=module):
                p = self.p(module)
                if module in ("tarot", "lenormand"):
                    p.update(self.backend.shuffle(p))
                record = self.backend.calculate(p)
                self.assertEqual(self.backend.get(record["id"]), record)
                if module in ("tarot", "lenormand", "liuyao", "meihua", "answers"):
                    self.assertTrue(self.backend.replay(record["id"])["verified"])
                if module not in ("answers", "solar"):
                    self.assertGreater(len(self.backend.prompt({"id": record["id"]})["user"]), 50)
        self.assertEqual(len(Backend(Path(self.tmp.name)).records()), 10)

    def test_private_deck_session_and_retry(self):
        p = self.p("tarot")
        info = self.backend.shuffle(p)
        self.assertEqual(set(info), {"session", "count"})
        p.update(info)
        p["picks"] = [1, 1, 2]
        with self.assertRaises(ValueError): self.backend.calculate(p)
        p["picks"] = [1, 20, 77]
        record = self.backend.calculate(p)
        self.assertEqual(len(record["result"]["cards"]), 3)
        with self.assertRaises(ValueError): self.backend.calculate(p)
        self.assertNotIn("session", record["inputs"])
        self.assertNotIn("interaction", record["inputs"])

    def test_simulation_and_preferences_do_not_store_credentials(self):
        for module in ("liuyao", "answers", "tarot", "lenormand"):
            p = self.p(module, seed="12345", interaction=[{"x": .2, "y": .3, "t_ms": 0}])
            if module in ("tarot", "lenormand"):
                p.update(self.backend.shuffle(p))
            result = self.backend.calculate(p)["result"]
            self.assertEqual(result["random"]["source"], "explicit-seed")
        self.backend.preferences({"api_key": "must-not-save", "quality": "low", "pinned": True})
        self.assertEqual(Backend(Path(self.tmp.name)).preferences(), {"quality": "low", "pinned": True})
        self.assertNotIn("must-not-save", (Path(self.tmp.name) / "preferences.json").read_text())

    def test_manual_methods_and_time_validation(self):
        for method, fields in (("numbers", {"third": "", "hour_number": 4}),
                               ("time", {}), ("lunar", {"year_branch": 1, "lunar_month": 2, "lunar_day": 3, "hour_branch": 4}),
                               ("direct", {"upper": 1, "lower": 8, "moving_line": 2})):
            self.assertTrue(self.backend.replay(self.backend.calculate(self.p("meihua", method=method, **fields))["id"])["verified"])
        self.backend.calculate(self.p("lenormand", method="manual", card_ids=[27, 25, 24]))
        self.backend.calculate(self.p("liuyao", method="manual", tosses=[6, 7, 8, 9, 7, 8]))
        with self.assertRaises(ValueError):
            self.backend.calculate(self.p("astro", datetime="2024-03-10T02:30", tz_name="America/New_York"))
        with self.assertRaises(ValueError):
            self.backend.calculate(self.p("bazi", datetime="2024-11-03T01:30", tz_name="America/New_York"))
        self.backend.calculate(self.p("bazi", datetime="2024-11-03T01:30", tz_name="America/New_York", fold="1"))

    def test_import_preserves_conversation_and_rejects_changed_snapshot(self):
        record = self.backend.calculate(self.p("answers"))
        record["interpretation"] = "一段说明"
        record["history"] = [{"role": "user", "content": "继续"}, {"role": "assistant", "content": "回应"}]
        imported = self.backend.import_record({"record": record})
        self.assertEqual(imported["result"], record["result"])
        self.assertEqual(imported["history"], record["history"])
        self.assertEqual(imported["interpretation"], record["interpretation"])
        changed = copy.deepcopy(record)
        changed["result"]["replay"]["page"] = 0
        with self.assertRaises(ValueError): self.backend.import_record({"record": changed})

    def test_ai_stream_followup_and_same_module_refs(self):
        record = self.backend.calculate(self.p("bazi"))
        ref = self.backend.calculate(self.p("bazi"))
        p = {"id": record["id"], "api_base": "https://example.test/v1", "api_key": "test-only", "model": "test-model"}
        def drain(job):
            for _ in range(100):
                poll = self.backend.poll({"job": job})
                if poll["done"]: return poll
                time.sleep(.01)
            self.fail("AI worker did not finish")
        with patch("mystery.llm.interpret_chart_stream", return_value=iter([{"type":"delta", "text":"模拟解读"}])):
            drain(self.backend.start_ai(p)["job"])
        self.assertEqual(self.backend.get(record["id"])["interpretation"], "模拟解读")
        with patch("mystery.llm.interpret_followup_stream", return_value=iter([{"type":"delta", "text":"模拟追问"}])) as fn:
            drain(self.backend.start_ai({**p, "question": "比较差异", "refs": [ref["id"]]})["job"])
            self.assertEqual(len(fn.call_args.kwargs["refs"]), 1)
        self.assertEqual(len(self.backend.get(record["id"])["history"]), 2)
        other = self.backend.calculate(self.p("answers"))
        with self.assertRaises(ValueError): self.backend.start_ai({**p, "question": "比较", "refs": [other["id"]]})

    def test_http_auth_origin_and_local_assets(self):
        server, _, url = create_server(Path(self.tmp.name) / "http")
        threading.Thread(target=server.serve_forever, daemon=True).start()
        try:
            origin = url.split('/?')[0]
            with self.assertRaises(urllib.error.HTTPError): urllib.request.urlopen(origin)
            entry = urllib.request.urlopen(url)
            cookie = entry.headers['Set-Cookie'].split(';')[0]
            token = url.split('session=')[1]
            self.assertIn(token.encode(), entry.read())
            for path in ('/country-layer.js','/country-geometry.js','/assets/geography/countries-110m.json'):
                request=urllib.request.Request(origin+path,headers={'Cookie':cookie})
                self.assertEqual(urllib.request.urlopen(request).status,200)
            for path in ("/app.js", "/scene.js", "/preferences.js", "/central-star.js", "/controls.js", "/controls.css", "/rituals.js", "/ritual-models.js", "/candles.js", "/answer-book.js", "/world-map.js", "/geo-models.js", "/birthday-atlas.js", "/place-picker.js", "/atlas.css", "/assets/geography/land-110m.json", "/tarot-art.js", "/location-context.js", "/location-panel.js", "/assets/tarot-rws/m00.jpg", "/assets/tarot-rws/p14.jpg", "/rituals.css", "/transitions.js", "/sparks.js", "/star-trails.js", "/node-layout.js", "/planets.css", "/birthdays.css", "/interactions.css", "/assets/nebula-dust-v1.png", "/vendor/three.module.js", "/vendor/three.core.js", "/vendor/OrbitControls.js"):
                request = urllib.request.Request(origin + path, headers={"Cookie": cookie})
                self.assertEqual(urllib.request.urlopen(request).status, 200)
            payload = b'{}'
            with self.assertRaises(urllib.error.HTTPError):
                urllib.request.urlopen(urllib.request.Request(origin + '/api/catalog', payload, headers={"Cookie": cookie}))
            headers = {"Cookie": cookie, "X-Mystery-Token": token, "Origin": origin}
            response = urllib.request.urlopen(urllib.request.Request(origin + '/api/catalog', payload, headers=headers))
            self.assertTrue(json.load(response)["ok"])
            def call(action, values):
                request = urllib.request.Request(origin + '/api/' + action, json.dumps(values).encode(), headers=headers)
                return json.load(urllib.request.urlopen(request))["data"]
            self.assertEqual(call('search-places', {'query': '上海'})[0]['tz_name'], 'Asia/Shanghai')
            self.assertEqual(call('place-at', {'longitude': -74.006, 'latitude': 40.713})['tz_name'], 'America/New_York')
            self.assertEqual(call('nearby-places', {'longitude': -74.006, 'latitude': 40.7143})[0]['tz_name'], 'America/New_York')
            person = call('save-birthday', {"name": "HTTP 测试", "datetime": "2000-08-16T04:00"})
            self.assertEqual(call('birthday', {"id": person["id"]}), person)
            self.assertEqual(len(call('birthdays', {"query": "HTTP"})), 1)
            self.assertTrue(call('delete-birthday', {"id": person["id"]})["deleted"])
            self.assertEqual(call('birthdays', {}), [])
            with self.assertRaises(urllib.error.HTTPError):
                urllib.request.urlopen(urllib.request.Request(origin + '/api/catalog', payload, headers={**headers, "Origin": "https://example.test"}))
        finally:
            server.shutdown()
            server.server_close()

    def person(self, **values):
        return {"name": "测试朋友", "datetime": "2000-08-16T04:00", "tz_name": "Asia/Shanghai",
                "longitude": 116.41, "latitude": 39.90, "gender": "女", "birth_place": "北京", **values}

    def test_effects_migration_marker_and_later_explicit_choices_persist(self):
        self.backend.preferences({"effects_default": "full-1", "quality": "high", "reduced": False})
        self.backend.preferences({**self.backend.preferences(), "quality": "low", "reduced": True})
        self.assertEqual(Backend(self.backend.data_dir).preferences(),
                         {"effects_default": "full-1", "quality": "low", "reduced": True})

    def test_six_throws_reveal_only_current_lines_and_save_once(self):
        info = self.backend.start_ritual(self.p('liuyao', seed='42'))
        self.assertEqual(set(info), {'session', 'total'})
        self.assertEqual(self.backend.records(), [])
        with self.assertRaises(ValueError): self.backend.finish_ritual(info)
        with self.assertRaises(ValueError): self.backend.ritual_step({**info, 'step': 2})
        for step in range(1, 7):
            value = self.backend.ritual_step({**info, 'step': step})
            self.assertEqual(len(value['tosses']), step)
            self.assertEqual(value, self.backend.ritual_step({**info, 'step': step}))
            self.assertEqual(self.backend.records(), [])
        record = self.backend.finish_ritual(info)
        self.assertEqual(record['result']['replay']['tosses'], value['tosses'])
        self.assertEqual(record['result']['random']['source'], 'explicit-seed')
        self.assertTrue(self.backend.replay(record['id'])['verified'])
        self.assertEqual(self.backend.finish_ritual(info)['id'], record['id'])
        self.assertEqual(len(self.backend.records()), 1)

    def test_physical_cut_rotates_private_deck_and_orientation_together(self):
        for module in ('tarot', 'lenormand'):
            info = self.backend.shuffle(self.p(module, seed='82'))
            before = copy.deepcopy(self.backend.sessions[info['session']][1])
            response = self.backend.cut_deck({**info, 'at': 11})
            self.assertEqual(set(response), {'cut', 'count'})
            self.backend.cut_deck({**info, 'at': 11})
            after = self.backend.sessions[info['session']][1]
            for key in ('card_ids', 'orientations'):
                if key in before: self.assertEqual(after[key], before[key][11:] + before[key][:11])
            with self.assertRaises(ValueError): self.backend.cut_deck({**info, 'at': 12})
            record = self.backend.calculate({**self.p(module), **info, 'picks': [0, 1, 2], 'cut_at': 11})
            self.assertTrue(self.backend.replay(record['id'])['verified'])

    def test_book_and_meihua_ritual_preserve_results_and_cancel(self):
        for module, total in [('answers', 1), ('meihua', 3)]:
            values = self.p(module, seed='16')
            expected = self.backend.calculate(values.copy(), persist=False)
            info = self.backend.start_ritual(values)
            for step in range(1, total + 1):
                partial = self.backend.ritual_step({**info, 'step': step})
                if module == 'meihua' and step == 1:
                    self.assertNotIn('ben', partial)
                    self.assertNotIn('bian', partial)
                if module == 'meihua' and step == 3:
                    self.assertEqual(partial['moving'], expected['moving_line'])
            record = self.backend.finish_ritual(info)
            self.assertEqual(record['result'], expected)
        info = self.backend.start_ritual(self.p('answers'))
        self.backend.cancel_ritual(info)
        with self.assertRaises(ValueError): self.backend.ritual_step({**info, 'step': 1})
        self.assertEqual(len(self.backend.records()), 2)

    def test_ritual_expiration_and_manual_coins(self):
        p = self.p('liuyao', method='manual', tosses=[6, 7, 8, 9, 8, 7])
        info = self.backend.start_ritual(p)
        for step in range(1, 7): self.backend.ritual_step({**info, 'step': step})
        record = self.backend.finish_ritual(info)
        self.assertEqual(record['result']['random']['source'], 'manual')
        self.assertEqual(record['result']['replay']['tosses'], p['tosses'])
        info = self.backend.start_ritual(self.p('answers'))
        self.backend.rituals[info['session']]['at'] -= 1801
        with self.assertRaises(ValueError): self.backend.ritual_step({**info, 'step': 1})
        with self.assertRaises(ValueError): self.backend.start_ritual(self.p('tarot'))

    def test_parallel_local_windows_keep_independent_sessions(self):
        servers = [create_server(Path(self.tmp.name) / name) for name in ("window-a", "window-b")]
        browser = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
        try:
            for server, _, url in servers:
                threading.Thread(target=server.serve_forever, daemon=True).start()
                browser.open(url).close()
            for server, _, url in servers:
                origin = url.split('/?')[0]
                token = url.split('session=')[1]
                request = urllib.request.Request(origin + '/api/save-birthday', json.dumps(self.person()).encode(),
                                                  headers={"X-Mystery-Token": token, "Origin": origin})
                self.assertTrue(json.load(browser.open(request))["ok"])
        finally:
            for server, _, _ in servers:
                server.shutdown()
                server.server_close()

    def test_birthday_crud_search_and_persistence(self):
        first = self.backend.save_birthday(self.person(notes="家人"))
        second = self.backend.save_birthday(self.person(datetime="1998-05-20T12:30", notes="Friend"))
        self.assertNotEqual(first["id"], second["id"])
        self.assertEqual(len(Backend(self.backend.data_dir).birthdays()), 2)
        self.assertEqual(self.backend.birthdays("friend"), [second])
        self.assertEqual(self.backend.birthdays("家人"), [first])
        changed = self.backend.save_birthday({**first, "name": "改后的称呼", "birth_place": "上海"})
        self.assertEqual(changed["id"], first["id"])
        self.assertEqual(changed["created"], first["created"])
        self.assertEqual(Backend(self.backend.data_dir).birthday(first["id"]), changed)
        self.assertEqual(self.backend.birthdays("上海"), [changed])
        self.backend.delete_birthday(second["id"])
        self.assertEqual(len(Backend(self.backend.data_dir).birthdays()), 1)

    def test_birthday_rejects_invalid_values_without_saving(self):
        for invalid in ({"name": " "}, {"name": "字" * 81}, {"datetime": "2000-02-30T12:00"},
                        {"datetime": "1899-12-31T12:00"}, {"datetime": "2000-08-16T04:00+08:00"},
                        {"tz_name": "not-a-zone"}, {"longitude": 181}, {"latitude": float('nan')},
                        {"gender": "未知"}, {"fold": 3}, {"notes": "a" * 1001}, {"use_true_solar": "false"}):
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                self.backend.save_birthday(self.person(**invalid))
        self.assertEqual(self.backend.birthdays(), [])

    def test_birthday_dst_disambiguation(self):
        p = self.person(datetime="2024-11-03T01:30", tz_name="America/New_York")
        with self.assertRaises(ValueError): self.backend.save_birthday(p)
        saved = self.backend.save_birthday({**p, "fold": "1"})
        self.assertEqual(saved["fold"], "1")
        with self.assertRaises(ValueError):
            self.backend.save_birthday(self.person(datetime="2024-03-10T02:30", tz_name="America/New_York"))

    def test_birthday_delete_preserves_chart_snapshot_and_clears_active(self):
        person = self.backend.save_birthday(self.person())
        self.backend.preferences({"active_birth_id": person["id"], "birth_onboarding_done": True, "pinned": True})
        record = self.backend.calculate({**self.p("bazi"), **{k: person[k] for k in ("datetime", "gender", "tz_name", "longitude")},
                                         "birthday_id": person["id"], "label": person["name"]})
        self.backend.save_birthday({**person, "datetime": "2001-08-16T04:00"})
        self.assertEqual(self.backend.get(record["id"]), record)
        self.backend.delete_birthday(person["id"])
        self.assertEqual(self.backend.get(record["id"]), record)
        self.assertEqual(self.backend.preferences(), {"active_birth_id": "", "birth_onboarding_done": True, "pinned": True})

    def test_birthday_unknown_ids_and_field_allowlist(self):
        with self.assertRaises(ValueError): self.backend.save_birthday(self.person(id="missing"))
        with self.assertRaises(ValueError): self.backend.birthday("missing")
        with self.assertRaises(ValueError): self.backend.delete_birthday("missing")
        person = self.backend.save_birthday(self.person(api_key="must-not-save", result={"wrong": True}))
        self.assertNotIn("api_key", person)
        self.assertNotIn("result", person)
        self.assertNotIn("must-not-save", json.dumps(self.backend.birthdays()))


if __name__ == "__main__": unittest.main()
