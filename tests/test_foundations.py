"""Sampling contracts, replay compatibility and civil-time edge cases."""
from collections import Counter
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import itertools
import json
import unittest
from unittest.mock import patch
from zoneinfo import ZoneInfo

from mystery.answers import ANSWERS, draw_answer, replay as replay_answer
from mystery.astrology import cast as cast_astrology, to_utc
from mystery.bazi import calculate_bazi
from mystery.liuyao import cast, draw as draw_liuyao, replay as replay_liuyao
from mystery.randomness import DrawRandom, interaction_evidence
from mystery.solar_time import to_true_solar_time
from mystery.tarot import draw, prepare_shuffle, replay as replay_tarot
from mystery.timebase import resolve_local

DATE = {"year": 2026, "month": 10, "day": 15, "hour": 12}
EVENTS = [{"x": 0.25, "y": 0.75, "t_ms": 0},
          {"x": 0.75, "y": 0.25, "t_ms": 12.5}]


class RandomFoundationTest(unittest.TestCase):
    def test_interaction_has_no_raw_trajectory_or_device_context(self):
        evidence = interaction_evidence(EVENTS, device_time="2026-10-15T12:00:00+08:00",
                                        app_version="0.2.0")
        self.assertEqual(evidence["event_count"], 2)
        self.assertEqual(set(evidence), {"schema", "event_count", "events_sha256", "context_sha256"})
        other = interaction_evidence(EVENTS, app_version="0.2.1")
        self.assertEqual(evidence["events_sha256"], other["events_sha256"])
        self.assertNotEqual(evidence["context_sha256"], other["context_sha256"])
        json.dumps(evidence, allow_nan=False)

    def test_interaction_rejects_invalid_or_unbounded_samples(self):
        bad = [[{"x": 0, "y": 0, "t_ms": -1}],
               [{"x": 2, "y": 0, "t_ms": 0}],
               [{"x": float("nan"), "y": 0, "t_ms": 0}],
               [{"x": True, "y": 0, "t_ms": 0}],
               [EVENTS[1], EVENTS[0]], [EVENTS[0]] * 4097,
               [{**EVENTS[0], "ip": "192.168.1.2"}]]
        for events in bad:
            with self.subTest(events=str(events[:2])), self.assertRaises(ValueError):
                interaction_evidence(events)
        with self.assertRaises(ValueError):
            DrawRandom("test", interaction={"event_count": 1})

    def test_context_and_purpose_participate_with_fresh_os_input(self):
        first = interaction_evidence(EVENTS)
        second = interaction_evidence([EVENTS[0]])
        with patch("mystery.randomness.secrets.token_bytes", return_value=b"\x19" * 32) as source:
            values = [DrawRandom(purpose, interaction=context).randbelow(2 ** 256)
                      for purpose, context in (("tarot", first), ("tarot", second), ("liuyao", first))]
        self.assertEqual(source.call_count, 3)
        self.assertEqual(len(set(values)), 3)
        with patch("mystery.randomness.secrets.token_bytes", side_effect=OSError("unavailable")):
            with self.assertRaises(OSError):
                DrawRandom("test", interaction=first).randbelow(2)
        with self.assertRaises(ValueError):
            DrawRandom("test", seed=42, interaction=first)

    def test_rejection_sampling_discards_biased_tail(self):
        class Block:
            def __init__(self, value):
                self.value = value

            def digest(self):
                return self.value

        with patch("mystery.randomness.hmac.new", side_effect=[Block(b"\xff" * 32), Block(b"\x00" * 32)]), \
                patch("mystery.randomness.secrets.token_bytes", return_value=b"\x00" * 32) as source:
            self.assertEqual(DrawRandom("test", interaction=interaction_evidence()).randbelow(3), 0)
            self.assertEqual(source.call_count, 2)

    def test_fisher_yates_can_reach_each_small_permutation_once(self):
        outcomes = Counter()
        for choices in itertools.product(range(3), range(2)):
            rng = DrawRandom("test")
            values = [0, 1, 2]
            with patch.object(rng, "randbelow", side_effect=choices):
                rng.shuffle(values)
            outcomes[tuple(values)] += 1
        self.assertEqual(set(outcomes), set(itertools.permutations(range(3))))
        self.assertEqual(set(outcomes.values()), {1})

    def test_default_draws_do_not_use_legacy_random(self):
        with patch("mystery.randomness.Random", side_effect=AssertionError("legacy RNG used")):
            readings = [draw("three"), draw_answer(), draw_liuyao(date=DATE)]
        for reading in readings:
            self.assertEqual(reading["random"]["source"], "os-csprng")

    def test_old_seed_results_are_preserved(self):
        tarot = draw("three", seed=42, picks=[0, 20, 77])
        self.assertEqual([(c["card"]["id"], c["reversed"]) for c in tarot["cards"]],
                         [("cups_12", False), ("cups_01", True), ("major_14", False)])
        answer = draw_answer(seed=42)
        self.assertEqual((answer["page"], answer["answer"]), (655, ANSWERS[28]))
        self.assertEqual(answer["random"]["source"], "explicit-seed")

    def test_secure_tarot_shuffle_is_stable_across_picks_and_replay(self):
        shuffle = prepare_shuffle(interaction=interaction_evidence(EVENTS))
        first = draw("three", picks=[0, 20, 77], shuffle=shuffle)
        second = draw("three", picks=[77, 20, 0], shuffle=shuffle)
        self.assertEqual(first["cards"][0]["card"], second["cards"][2]["card"])
        self.assertEqual(first["cards"][0]["reversed"], second["cards"][2]["reversed"])
        self.assertEqual(len({c["card"]["id"] for c in first["cards"]}), 3)
        restored = json.loads(json.dumps(first["replay"]))
        with patch("mystery.randomness.secrets.randbelow", side_effect=AssertionError("fresh draw")), \
                patch("mystery.randomness.secrets.token_bytes", side_effect=AssertionError("fresh draw")):
            self.assertEqual(first, replay_tarot(restored))
        self.assertTrue(all(not c["reversed"] for c in draw("celtic", reversals=False)["cards"]))

    def test_replay_rejects_changed_decks_and_incomplete_records(self):
        reading = draw("three")
        bad = deepcopy(reading["replay"])
        bad["shuffle"]["card_ids"][0] = bad["shuffle"]["card_ids"][1]
        with self.assertRaises(ValueError):
            replay_tarot(bad)
        bad = deepcopy(reading["replay"])
        bad["shuffle"]["deck_sha256"] = "changed"
        with self.assertRaises(ValueError):
            replay_tarot(bad)
        for snapshot in ({"schema": "tarot-reading-v1"}, {"schema": "future-version"}):
            with self.assertRaises(ValueError):
                replay_tarot(snapshot)
        for picks in ([0.2, 1, 2], [False, 1, 2]):
            with self.assertRaises(ValueError):
                draw("three", picks=picks)

    def test_fixed_book_pages_and_replay(self):
        for index in range(len(ANSWERS)):
            with patch("mystery.randomness.secrets.randbelow", return_value=index):
                reading = draw_answer()
            self.assertEqual((reading["page"], reading["answer"]), (index + 1, ANSWERS[index]))
            self.assertEqual(reading, replay_answer(json.loads(json.dumps(reading["replay"]))))
        bad = deepcopy(reading["replay"])
        bad["answer_index"] = 0
        with self.assertRaises(ValueError):
            replay_answer(bad)

    def test_coin_method_exhaustive_probability_and_replay(self):
        counts = Counter()
        for coins in itertools.product((0, 1), repeat=3):
            with patch("mystery.randomness.DrawRandom.randbelow", side_effect=coins * 6):
                reading = draw_liuyao(date=DATE)
            counts[reading["tosses"][0]] += 1
            self.assertEqual(reading["tosses"], [6 + sum(coins)] * 6)
            self.assertEqual(reading, replay_liuyao(json.loads(json.dumps(reading["replay"]))))
        self.assertEqual(counts, {6: 1, 7: 3, 8: 3, 9: 1})


class CivilTimeTest(unittest.TestCase):
    def test_dst_gaps_and_overlaps_need_explicit_resolution(self):
        for fold in (None, 0, 1):
            with self.assertRaises(ValueError):
                resolve_local(datetime(2024, 3, 10, 2, 30), "America/New_York", fold=fold)
        with self.assertRaises(ValueError):
            to_utc(2024, 11, 3, 1, 30, "America/New_York")
        first = to_utc(2024, 11, 3, 1, 30, "America/New_York", fold=0)
        second = to_utc(2024, 11, 3, 1, 30, "America/New_York", fold=1)
        self.assertEqual(second - first, timedelta(hours=1))

    def test_same_instant_across_local_zones_has_same_chart(self):
        # New York 00:30 and Shanghai 13:30 are the same winter instant.
        a = calculate_bazi(2024, 1, 15, 0, 30, longitude=116.41, tz_name="America/New_York")
        b = calculate_bazi(2024, 1, 15, 13, 30, longitude=116.41)
        self.assertEqual(a["pillars"], b["pillars"])
        self.assertEqual(a["time"]["utc"], b["time"]["utc"])
        a = cast_astrology(2024, 1, 15, 0, 30, 39.9, 116.41, "America/New_York")
        b = cast_astrology(2024, 1, 15, 13, 30, 39.9, 116.41)
        self.assertEqual(a["points"], b["points"])
        tosses = [6, 7, 8, 9, 7, 8]
        a = cast(tosses, date={"year": 2024, "month": 1, "day": 15, "hour": 0, "minute": 30},
                 tz_name="America/New_York")
        b = cast(tosses, date={"year": 2024, "month": 1, "day": 15, "hour": 13, "minute": 30})
        self.assertEqual(a["ben"], b["ben"])
        self.assertEqual(a["date"], b["date"])
        self.assertEqual(a, replay_liuyao(a["replay"]))

    def test_chinese_historical_dst_removed_before_solar_correction(self):
        summer = datetime(1990, 6, 15, 12, 30)
        actual, detail = to_true_solar_time(summer, 116.41, tz_name="Asia/Shanghai")
        expected, _ = to_true_solar_time(datetime(1990, 6, 15, 11, 30), 116.41)
        self.assertEqual(actual, expected)
        self.assertEqual(detail["clock_time"], "1990-06-15 11:30")
        aware = summer.replace(tzinfo=ZoneInfo("Asia/Shanghai"))
        self.assertEqual(to_true_solar_time(aware, 116.41)[0], expected)
        a = calculate_bazi(1990, 6, 15, 12, 30, longitude=116.41)
        b = calculate_bazi(1990, 6, 15, 11, 30, longitude=116.41, tz_name="Etc/GMT-8")
        self.assertEqual(a["pillars"], b["pillars"])

    def test_default_cast_clock_is_explicit_and_saved(self):
        now = datetime(2026, 10, 15, 12, 34, 56, tzinfo=ZoneInfo("Asia/Shanghai"))
        with patch("mystery.liuyao.casting.datetime", wraps=datetime) as clock:
            clock.now.return_value = now
            reading = cast([7] * 6)
            clock.now.assert_called_once_with(ZoneInfo("Asia/Shanghai"))
        self.assertEqual(reading["date"]["minute"], 34)
        self.assertEqual(reading["time"]["utc"], "2026-10-15T04:34:56+00:00")
        self.assertEqual(reading, replay_liuyao(reading["replay"]))
        with self.assertRaises(ValueError):
            cast([7] * 6, date={"month": 1})
        date_only = cast([7] * 6, date={"year": 2026, "month": 10, "day": 15})
        self.assertEqual(date_only["date"]["hour"], 0)

    def test_aware_and_naive_solar_inputs_do_not_double_convert(self):
        actual, _ = to_true_solar_time(datetime(2024, 1, 1, 0, tzinfo=timezone.utc), 120)
        expected, _ = to_true_solar_time(datetime(2024, 1, 1, 8), 120)
        self.assertEqual(actual, expected)
        with self.assertRaises(ValueError):
            to_true_solar_time(datetime(2024, 1, 1, tzinfo=timezone.utc), 120, tz_name="UTC")


if __name__ == "__main__":
    unittest.main()
