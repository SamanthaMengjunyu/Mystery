"""Question methods: classical fixtures, exhaustive structures and private replay."""
from copy import deepcopy
import itertools
import json
import unittest
from unittest.mock import patch

from mystery.meihua import cast, cast_lunar, cast_numbers, cast_time, replay
from mystery.lenormand import cast as read_cards, draw, get_deck, prepare_shuffle
from mystery.lenormand import replay as replay_cards
from mystery.lenormand.data import PAIR_HINTS
from mystery.randomness import interaction_evidence
from mystery.llm import interpret_meihua_stream, interpret_lenormand_stream
from mystery.llm.prompts import build_meihua_prompt, build_lenormand_prompt, build_followup_messages


class MeihuaTest(unittest.TestCase):
    def test_classical_plum_and_peony_examples(self):
        # Primary text: 梅花易數卷一, 觀梅占 and 牡丹占.
        # https://zh.wikisource.org/wiki/梅花易數/卷一
        plum = cast_lunar("辰", 12, 17, "申")
        self.assertEqual((plum["ben"]["name"], plum["moving_line"], plum["bian"]["name"]),
                         ("泽火革", 1, "泽山咸"))
        self.assertEqual((plum["hu"]["upper"], plum["hu"]["lower"]), ("乾", "巽"))
        self.assertEqual(plum["analysis"]["body"]["name"], "兑")
        self.assertEqual(plum["analysis"]["ben_relation"]["label"], "用克体")
        self.assertEqual(plum["analysis"]["bian_relation"]["kind"], "supports_body")
        peony = cast_lunar("巳", 3, 16, "卯")
        self.assertEqual((peony["ben"]["name"], peony["moving_line"], peony["bian"]["name"]),
                         ("天风姤", 5, "火风鼎"))
        self.assertEqual((peony["hu"]["upper"], peony["hu"]["lower"]), ("乾", "乾"))
        self.assertEqual(peony["analysis"]["body"]["name"], "巽")

    def test_exhaustive_six_lines_and_body_positions(self):
        # Independent bottom-up trigram reference rather than the production table.
        bits_by_number = ((1, 1, 1), (1, 1, 0), (1, 0, 1), (1, 0, 0),
                          (0, 1, 1), (0, 1, 0), (0, 0, 1), (0, 0, 0))
        names = set()
        for upper, lower, moving in itertools.product(range(1, 9), range(1, 9), range(1, 7)):
            reading = cast(upper, lower, moving, nuclear="standard")
            names.add(reading["ben"]["name"])
            expected = list(bits_by_number[lower - 1] + bits_by_number[upper - 1])
            self.assertEqual(reading["ben"]["bits"], expected)
            expected[moving - 1] ^= 1
            self.assertEqual(reading["bian"]["bits"], expected)
            body = "upper" if moving <= 3 else "lower"
            self.assertEqual(reading["analysis"]["body"]["position"], body)
            self.assertEqual(reading["ben"][body], reading["bian"][body])
            original = reading["ben"]["bits"]
            self.assertEqual(reading["hu"]["bits"], original[1:4] + original[2:5])
        self.assertEqual(len(names), 64)

    def test_declared_pure_qian_kun_nuclear_rule(self):
        for number, expected in ((1, "天风姤"), (8, "地雷复")):
            classic = cast(number, number, 2)
            standard = cast(number, number, 2, nuclear="standard")
            self.assertEqual(classic["hu"]["source"], "bian")
            self.assertEqual(classic["hu"]["name"], expected)
            self.assertEqual(standard["hu"]["source"], "ben")
            self.assertEqual(standard["hu"]["bits"], standard["ben"]["bits"])

    def test_numeric_profiles_and_zero_remainders(self):
        for first, second in ((8, 16), (0, 0)):
            reading = cast_numbers(first, second)
            self.assertEqual((reading["ben"]["name"], reading["moving_line"]), ("坤为地", 6))
        third = cast_numbers(1, 2, 8)
        self.assertEqual(third["moving_line"], 2)
        self.assertEqual(third["rules"]["number_profile"], "independent-third")
        # 卷一 鄰夜扣門借物占: 1 and 5 sounds, 酉 hour=10, fourth line.
        knocking = cast_numbers(1, 5, hour_number=10)
        self.assertEqual((knocking["ben"]["name"], knocking["moving_line"], knocking["bian"]["name"]),
                         ("天风姤", 4, "巽为风"))
        self.assertEqual(knocking["trace"]["line_total"], 16)

    def test_time_uses_lunar_new_year_and_midnight(self):
        before = cast_time(2024, 2, 9, 23, 30)
        after = cast_time(2024, 2, 10, 0, 10)
        self.assertEqual(before["trace"]["calendar"]["year_branch"], "卯")
        self.assertEqual(after["trace"]["calendar"]["year_branch"], "辰")
        self.assertEqual(before["trace"]["calendar"]["hour_branch"], "子")
        self.assertEqual(after["trace"]["calendar"]["hour_branch"], "子")
        self.assertEqual(after["trace"]["calendar"]["month"], 1)
        self.assertEqual(after["trace"]["calendar"]["day"], 1)

    def test_leap_month_repeats_month_number(self):
        result = cast_time(2023, 4, 6, 12)
        calendar = result["trace"]["calendar"]
        self.assertTrue(calendar["leap_month"])
        self.assertEqual((calendar["month"], calendar["day"]), (2, 16))
        manual = cast_lunar(calendar["year_branch"], 2, 16, "午", leap_month=True)
        self.assertEqual(result["ben"], manual["ben"])
        self.assertEqual(result["moving_line"], manual["moving_line"])

    def test_time_zones_and_dst(self):
        ny = cast_time(2024, 1, 15, 0, 30, tz_name="America/New_York")
        china = cast_time(2024, 1, 15, 13, 30)
        self.assertEqual(ny["ben"], china["ben"])
        self.assertEqual(ny["trace"], china["trace"])
        self.assertEqual(ny["time"]["utc"], china["time"]["utc"])
        for y, m, d, h, minute in ((2024, 3, 10, 2, 30), (2024, 11, 3, 1, 30)):
            with self.assertRaises(ValueError):
                cast_time(y, m, d, h, minute, tz_name="America/New_York")
        late = cast_time(2024, 11, 3, 1, 30, tz_name="America/New_York", fold=1)
        self.assertEqual(late, replay(late["replay"]))

    def test_all_methods_replay_without_rng(self):
        readings = [cast(2, 3, 1, "合作如何？"), cast_numbers(34, 43, 1, "合作如何？"),
                    cast_lunar("辰", 12, 17, "申", "合作如何？"),
                    cast_time(2026, 10, 15, 12, question="合作如何？")]
        with patch("mystery.randomness.secrets.randbelow", side_effect=AssertionError("RNG used")), \
                patch("mystery.randomness.secrets.token_bytes", side_effect=AssertionError("RNG used")):
            for result in readings:
                self.assertIsNone(result["random"])
                self.assertEqual(result, replay(json.loads(json.dumps(result["replay"]))))
                self.assertEqual(replay(result["replay"], question="新问题")["question"], "新问题")
            self.assertEqual(cast_numbers(34, 43)["ben"]["upper"], "兑")

    def test_replay_detects_rules_and_time_changes(self):
        result = cast_time(2026, 10, 15, 12)
        changed = deepcopy(result["replay"])
        changed["time"]["utc"] = "changed"
        with self.assertRaises(ValueError):
            replay(changed)
        with patch("mystery.meihua.casting.version", return_value="different"):
            with self.assertRaises(ValueError):
                replay(result["replay"])
        bad = deepcopy(result["replay"])
        del bad["input"]["year"]
        with self.assertRaises(ValueError):
            replay(bad)

    def test_invalid_inputs(self):
        actions = (lambda: cast(0, 1, 1), lambda: cast(1, True, 1), lambda: cast(1, 2, 7),
                   lambda: cast_numbers(-1, 2), lambda: cast_numbers(1.5, 2),
                   lambda: cast_numbers(1, 2, 3, hour_number=1),
                   lambda: cast_lunar("龙", 12, 17, "申"), lambda: cast_lunar("辰", 13, 1, "申"),
                   lambda: cast_time(2024, 2, 30, 12), lambda: cast(1, 2, 3, nuclear="other"))
        for action in actions:
            with self.assertRaises(ValueError):
                action()


class LenormandTest(unittest.TestCase):
    def test_deck_identities_and_copy_isolation(self):
        deck = get_deck()
        self.assertEqual([card["id"] for card in deck], list(range(1, 37)))
        self.assertEqual((deck[0]["en"], deck[24]["en"], deck[35]["en"]), ("Rider", "Ring", "Cross"))
        deck[0]["keywords"].append("changed")
        self.assertNotIn("changed", get_deck()[0]["keywords"])
        self.assertFalse(any("reversed" in card for card in get_deck()))

    def test_default_rng_and_no_replacement(self):
        with patch("mystery.randomness.Random", side_effect=AssertionError("legacy RNG")):
            for spread, count in (("three", 3), ("five", 5)):
                result = draw(spread)
                self.assertEqual(len(result["cards"]), count)
                self.assertEqual(len({c["card"]["id"] for c in result["cards"]}), count)
                self.assertEqual(result["random"]["source"], "os-csprng")
                self.assertFalse(result["rules"]["reversals"])

    def test_seeded_reproducibility_and_interaction_evidence(self):
        self.assertEqual(draw("five", seed=42), draw("five", seed=42))
        evidence = interaction_evidence([{"x": 0.1, "y": 0.2, "t_ms": 0}])
        result = draw(interaction=evidence)
        self.assertEqual(result["random"]["interaction"], evidence)
        self.assertEqual(result["random"]["algorithm"], "os-hmac-sha256-rejection-v1")

    def test_same_shuffle_preserves_slots(self):
        shuffle = prepare_shuffle()
        first = draw(picks=[0, 20, 35], shuffle=shuffle)
        second = draw(picks=[35, 20, 0], shuffle=shuffle)
        self.assertEqual(first["cards"][0]["card"], second["cards"][2]["card"])
        self.assertEqual(first["cards"][1]["card"], second["cards"][1]["card"])

    def test_manual_cards_have_no_random_claim(self):
        with patch("mystery.randomness.secrets.randbelow", side_effect=AssertionError("RNG")):
            result = read_cards([27, 25, 24], "合作如何？")
        self.assertIsNone(result["random"])
        self.assertEqual(result["source"]["method"], "manual")

    def test_pair_order_focus_and_mirrors(self):
        result = read_cards([1, 27, 25, 24, 35])
        self.assertEqual(result["analysis"]["focus"]["card"]["id"], 25)
        self.assertEqual([p["positions"] for p in result["analysis"]["adjacent_pairs"]], [[1, 2], [2, 3], [3, 4], [4, 5]])
        self.assertEqual([p["positions"] for p in result["analysis"]["mirror_pairs"]], [[1, 5], [2, 4]])
        first = read_cards([27, 25, 24])["analysis"]["adjacent_pairs"][0]
        reverse = read_cards([25, 27, 24])["analysis"]["adjacent_pairs"][0]
        self.assertTrue(first["has_selected_rule"])
        self.assertNotEqual(first["reading_hint"], reverse["reading_hint"])
        unknown = read_cards([1, 2, 3])["analysis"]["adjacent_pairs"][0]
        self.assertFalse(unknown["has_selected_rule"])
        self.assertIsNone(unknown["reading_hint"])

    def test_roundtrip_uses_no_new_randomness(self):
        readings = [read_cards([27, 25, 24], "怎样沟通？"), draw("five", "如何推进？"), draw(seed=42)]
        with patch("mystery.randomness.secrets.randbelow", side_effect=AssertionError("RNG")), \
                patch("mystery.randomness.secrets.token_bytes", side_effect=AssertionError("RNG")):
            for result in readings:
                restored = replay_cards(json.loads(json.dumps(result["replay"], allow_nan=False)))
                self.assertEqual(restored, result)

    def test_replay_rejects_inconsistent_cards_and_changed_pair_rules(self):
        result = draw(seed=42)
        changed = deepcopy(result["replay"])
        changed["card_ids"] = list(reversed(changed["card_ids"]))
        with self.assertRaises(ValueError):
            replay_cards(changed)
        with patch.dict(PAIR_HINTS, {(27, 25): "Changed association"}):
            with self.assertRaises(ValueError):
                replay_cards(result["replay"])

    def test_invalid_requests_fail_before_randomness(self):
        with patch("mystery.randomness.secrets.randbelow", side_effect=AssertionError("RNG")):
            for action in (lambda: draw("other"), lambda: draw(picks=[0, 0, 1]),
                           lambda: draw(picks=[0, 1, 36]), lambda: draw(seed="42"),
                           lambda: read_cards([1, 1, 2]), lambda: read_cards([True, 2, 3]),
                           lambda: draw(question={})):
                with self.assertRaises(ValueError):
                    action()
        bad = prepare_shuffle(seed=42)
        bad["random"]["purpose"] = "tarot"
        with self.assertRaises(ValueError):
            draw(shuffle=bad)


class QuestionPromptTest(unittest.TestCase):
    def test_prompt_followup_and_stream_routes(self):
        cases = [("meihua", cast_lunar("辰", 12, 17, "申", "合作如何？"), build_meihua_prompt, interpret_meihua_stream),
                 ("lenormand", draw(question="沟通关注什么？", seed=42), build_lenormand_prompt, interpret_lenormand_stream)]
        for module, result, builder, service in cases:
            original = deepcopy(result)
            for lite in (False, True):
                system, user = builder(result, lite=lite)
                self.assertTrue(system and user)
                self.assertNotIn('"shuffle":', user)
                self.assertNotIn('"replay":', user)
            messages = build_followup_messages(module, result, "此前解释", [], "下一步呢？",
                        refs=[{"label": "对照", "result": result, "interpretation": "旧解释"}])
            self.assertEqual(messages[-1]["content"], "下一步呢？")
            with patch("mystery.llm.service._run_stream") as run:
                run.return_value = iter([{"type": "delta", "text": "test"}])
                self.assertEqual(list(service(result, {}))[0]["text"], "test")
                full, lite, _ = run.call_args.args
                self.assertEqual(full(), builder(result, lite=False))
                self.assertEqual(lite(), builder(result, lite=True))
            self.assertEqual(result, original)


if __name__ == "__main__":
    unittest.main()
