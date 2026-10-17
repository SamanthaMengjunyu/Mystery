"""Regression checks for invalid input, changed rules and casting-time capture."""
from copy import deepcopy
from datetime import datetime
import json
import unittest
from unittest.mock import patch
from zoneinfo import ZoneInfo

from mystery.answers import draw_answer, replay as replay_answer
from mystery.astrology import compute_chart
from mystery.bazi import calculate_bazi
from mystery.liuyao import CATEGORIES, draw as draw_liuyao, replay as replay_liuyao
from mystery.randomness import DrawRandom, interaction_evidence
from mystery.solar_time import to_true_solar_time
from mystery.tarot import SPREADS, draw, get_deck, replay as replay_tarot
from mystery.timebase import resolve_local, time_record

DATE = {"year": 2026, "month": 10, "day": 15, "hour": 12}


class FoundationBoundariesTest(unittest.TestCase):
    def test_unknown_deck_and_house_system_are_rejected(self):
        for action in (lambda: get_deck("typo"), lambda: draw("three", deck="typo"),
                       lambda: compute_chart(2000, 1, 1, 12, 0, 30, 120,
                                             "Asia/Shanghai", house_system="X")):
            with self.assertRaises(ValueError):
                action()

    def test_changed_spread_cannot_silently_reinterpret_replay(self):
        reading = draw("three")
        with patch.dict(SPREADS["three"], {"desc": "Changed spread interpretation"}):
            with self.assertRaises(ValueError):
                replay_tarot(reading["replay"])

    def test_changed_liuyao_rules_or_time_cannot_silently_replay(self):
        reading = draw_liuyao(date=DATE)
        with patch.dict(CATEGORIES["zonghe"], {"note": "Changed rule"}):
            with self.assertRaises(ValueError):
                replay_liuyao(reading["replay"])
        altered = deepcopy(reading["replay"])
        altered["time"]["utc"] = "2026-10-15T05:00:00+00:00"
        with self.assertRaises(ValueError):
            replay_liuyao(altered)

    def test_random_evidence_is_validated_on_replay(self):
        records = [(draw("three")["replay"], replay_tarot),
                   (draw_answer()["replay"], replay_answer),
                   (draw_liuyao(date=DATE)["replay"], replay_liuyao)]
        for snapshot, restore in records:
            altered = deepcopy(snapshot)
            location = altered["shuffle"] if "shuffle" in altered else altered
            location["random"] = {"source": "os-csprng"}
            with self.subTest(restore=restore.__module__), self.assertRaises(ValueError):
                restore(altered)

    def test_random_evidence_cannot_mutate_a_running_sampler(self):
        interaction = interaction_evidence()
        sampler = DrawRandom("test", interaction=interaction)
        sampler.evidence["interaction"]["event_count"] = 4000
        self.assertEqual(sampler.evidence["interaction"]["event_count"], 0)

    def test_invalid_requests_do_not_consume_randomness(self):
        requests = (lambda: draw("three", picks=[0, 0, 1]),
                    lambda: draw("three", deck="typo"),
                    lambda: draw_liuyao(date={"month": 1}),
                    lambda: draw_liuyao(date=DATE, category="typo"))
        with patch("mystery.randomness.secrets.randbelow", side_effect=AssertionError("draw started")):
            for request in requests:
                with self.assertRaises(ValueError):
                    request()

    def test_casting_time_is_captured_before_first_coin(self):
        now = datetime(2026, 10, 15, 12, 0, tzinfo=ZoneInfo("Asia/Shanghai"))
        with patch("mystery.liuyao.casting.datetime", wraps=datetime) as clock:
            clock.now.return_value = now

            def coin(upper):
                self.assertTrue(clock.now.called)
                return 0

            with patch("mystery.randomness.secrets.randbelow", side_effect=coin):
                reading = draw_liuyao()
            self.assertEqual(clock.now.call_count, 1)
        self.assertEqual(reading["time"]["local"], now.isoformat())

    def test_aware_gap_and_naive_time_records_are_rejected(self):
        nonexistent = datetime(2024, 3, 10, 2, 30, tzinfo=ZoneInfo("America/New_York"))
        with self.assertRaises(ValueError):
            to_true_solar_time(nonexistent, -74)
        with self.assertRaises(ValueError):
            time_record(datetime(2024, 1, 1), basis="utc")

    def test_invalid_timezones_and_bazi_options_are_clear_errors(self):
        for zone in ("Missing/Zone", "", None, []):
            with self.subTest(zone=zone), self.assertRaises(ValueError):
                resolve_local(datetime(2024, 1, 1), zone)
        for options in ({"gender": "unknown"}, {"use_true_solar": "false"}, {"sect": True}):
            with self.subTest(options=options), self.assertRaises(ValueError):
                calculate_bazi(2000, 1, 1, 12, longitude=120, **options)

    def test_extreme_pointer_input_is_rejected_cleanly(self):
        with self.assertRaises(ValueError):
            interaction_evidence([{"x": 0, "y": 0, "t_ms": 10 ** 1000}])

    def test_replay_versions_survive_json_roundtrip(self):
        for reading, restore in ((draw("three"), replay_tarot),
                                 (draw_liuyao(date=DATE), replay_liuyao)):
            self.assertEqual(reading, restore(json.loads(json.dumps(reading["replay"]))))

    def test_original_v1_replays_remain_explicitly_v1(self):
        tarot = draw("three", seed=42)
        old = deepcopy(tarot["replay"])
        old["schema"] = "tarot-reading-v1"
        old.pop("spread_sha256")
        restored = replay_tarot(old)
        self.assertEqual(restored["cards"], tarot["cards"])
        self.assertEqual(restored["replay"], old)
        liuyao = draw_liuyao(date=DATE, seed=42)
        old = deepcopy(liuyao["replay"])
        old["schema"] = "liuyao-reading-v1"
        old.pop("rules_sha256")
        old.pop("time")
        restored = replay_liuyao(old)
        self.assertEqual(restored["ben"], liuyao["ben"])
        self.assertEqual(restored["replay"], old)

    def test_ambiguous_time_record_preserves_the_selected_occurrence(self):
        readings = [draw_liuyao(date={"year": 2024, "month": 11, "day": 3,
                                     "hour": 1, "minute": 30},
                                tz_name="America/New_York", fold=fold, seed=42)
                    for fold in (0, 1)]
        self.assertNotEqual(readings[0]["time"]["utc"], readings[1]["time"]["utc"])
        for reading in readings:
            self.assertEqual(reading, replay_liuyao(reading["replay"]))


if __name__ == "__main__":
    unittest.main()
