"""Portable offline checks for extracted algorithms and public entry points."""
from datetime import datetime, timedelta
import itertools
import json
import unittest
from unittest.mock import patch

from mystery.answers import ANSWERS, draw_answer
from mystery.astrology import cast as cast_astrology, to_utc
from mystery.bazi import calculate_bazi
from mystery.liuyao import HEX_BY_BITS, cast as cast_liuyao, tosses_from_yang_counts
from mystery.solar_time import longitude_correction, to_true_solar_time
from mystery.tarot import SPREADS, draw, get_deck
from mystery.llm import make_config
from mystery.llm.prompts import (
    build_prompt, build_astro_prompt, build_tarot_prompt,
    build_liuyao_prompt, build_followup_messages,
)


DATE = {"year": 2026, "month": 10, "day": 15, "hour": 12}


class LocalAlgorithmsTest(unittest.TestCase):
    """Check domain invariants, boundaries and reproducibility."""

    def test_bazi_structure_and_five_elements(self):
        """Each of the four pillars contributes two five-element symbols."""
        chart = calculate_bazi(1990, 6, 15, 12, 30, longitude=116.41)
        self.assertEqual(set(chart["pillars"]), {"year", "month", "day", "hour"})
        self.assertEqual(sum(chart["wuxing_stats"].values()), 8)
        self.assertEqual(chart["day_master"], chart["pillars"]["day"]["gan"])
        self.assertEqual(len(chart["da_yun"]["list"]), 8)
        self.assertIn("strength_robustness", chart["analysis"])
        json.dumps(chart, ensure_ascii=False)

    def test_bazi_solar_time_can_cross_day(self):
        """An east-west correction may change the calendar date."""
        chart = calculate_bazi(2000, 1, 1, 0, 15, longitude=75)
        self.assertTrue(chart["true_solar"]["true_solar_time"].startswith("1999-12-31"))

    def test_bazi_midnight_sects(self):
        """The two late-zi-hour conventions yield different day pillars."""
        charts = [calculate_bazi(2000, 1, 1, 23, 30, use_true_solar=False, sect=s)
                  for s in (1, 2)]
        self.assertNotEqual(charts[0]["pillars"]["day"]["ganzhi"],
                            charts[1]["pillars"]["day"]["ganzhi"])

    def test_bazi_invalid_input(self):
        """Invalid birth dates, missing longitude and unknown sects are rejected."""
        for args, kwargs in [((1800, 1, 1, 12), {}), ((2000, 2, 30, 12), {}),
                             ((2000, 1, 1, 12), {}),
                             ((2000, 1, 1, 12), {"sect": 3})]:
            with self.subTest(args=args, kwargs=kwargs), self.assertRaises(ValueError):
                calculate_bazi(*args, **kwargs)

    def test_solar_time_details(self):
        """Reported components agree with the actual datetime correction."""
        before = datetime(2000, 2, 29, 12, 30)
        after, detail = to_true_solar_time(before, 116.41)
        self.assertAlmostEqual(longitude_correction(116.41), -14.36)
        self.assertAlmostEqual((after - before).total_seconds() / 60,
                               detail["total_correction_min"], places=2)
        self.assertEqual(detail["clock_time"], "2000-02-29 12:30")

    def test_historical_daylight_saving(self):
        """Timezone conversion uses historical daylight saving rules."""
        winter = to_utc(2020, 1, 15, 12, 0, "America/New_York")
        summer = to_utc(2020, 7, 15, 12, 0, "America/New_York")
        self.assertEqual(winter.hour, 17)
        self.assertEqual(summer.hour, 16)
        self.assertEqual(winter.utcoffset(), timedelta(0))

    def test_astrology_houses_and_analysis(self):
        """Every configured house system yields a complete analysed chart."""
        for system in ("P", "W", "K", "E"):
            with self.subTest(system=system):
                chart = cast_astrology(1990, 6, 15, 12, 30, 39.90, 116.41,
                                       house_system=system)
                self.assertEqual(len(chart["houses"]), 12)
                self.assertEqual(len(chart["points"]), 13)
                self.assertEqual(chart["analysis"]["big_three"]["sun"], chart["sun_sign"])
                self.assertTrue(all(0 <= p["lon"] < 360 for p in chart["points"].values()))
                json.dumps(chart, ensure_ascii=False)

    def test_hexagram_table_complete(self):
        """All 64 binary hexagrams have distinct names and valid shi/ying."""
        self.assertEqual(set(HEX_BY_BITS), set(itertools.product((0, 1), repeat=6)))
        self.assertEqual(len({entry["name"] for entry in HEX_BY_BITS.values()}), 64)
        for entry in HEX_BY_BITS.values():
            self.assertEqual(abs(entry["shi"] - entry["ying"]), 3)

    def test_liuyao_static_and_changing(self):
        """Every yin/yang hexagram can be cast; moving lines flip corresponding bits."""
        for bits in itertools.product((0, 1), repeat=6):
            tosses = [7 if bit else 8 for bit in bits]
            static = cast_liuyao(tosses, date=DATE)
            self.assertEqual(static["ben"]["bits"], list(bits))
            self.assertIsNone(static["bian"])
            self.assertEqual(static["dong"], [])
        moving = cast_liuyao([6, 7, 8, 9, 7, 8], date=DATE)
        self.assertEqual(moving["dong"], [1, 4])
        for i, bit in enumerate(moving["ben"]["bits"]):
            self.assertEqual(moving["bian"]["bits"][i], bit ^ (i + 1 in moving["dong"]))
        self.assertEqual(sum(line["shi"] for line in moving["ben"]["lines"]), 1)
        self.assertEqual(sum(line["ying"] for line in moving["ben"]["lines"]), 1)
        json.dumps(moving, ensure_ascii=False)

    def test_coin_conversion_and_invalid_tosses(self):
        """Each yang side adds one to the three-coin base value of six."""
        self.assertEqual(tosses_from_yang_counts([0, 1, 2, 3, 0, 3]), [6, 7, 8, 9, 6, 9])
        for tosses in ([], [7] * 5, [5, 7, 8, 9, 7, 8]):
            with self.assertRaises(ValueError):
                cast_liuyao(tosses, date=DATE)

    def test_tarot_deck_and_spreads(self):
        """The RWS deck has 78 distinct cards and draws without replacement."""
        deck = get_deck()
        self.assertEqual(len(deck), 78)
        self.assertEqual(len({card["id"] for card in deck}), 78)
        for key, spread in SPREADS.items():
            reading = draw(key, seed=42)
            self.assertEqual(len(reading["cards"]), spread["count"])
            self.assertEqual(len({entry["card"]["id"] for entry in reading["cards"]}), spread["count"])
            self.assertEqual(reading, draw(key, seed=42))

    def test_tarot_slot_orientation_is_stable(self):
        """Changing selection order preserves a slot's card and orientation."""
        first = draw("three", seed=42, picks=[0, 20, 77])
        second = draw("three", seed=42, picks=[77, 20, 0])
        a, b = first["cards"][0], second["cards"][2]
        self.assertEqual((a["card"], a["reversed"]), (b["card"], b["reversed"]))

    def test_tarot_rejects_invalid_picks(self):
        """Unknown spreads, duplicate cards and out-of-range slots fail."""
        for key, picks in [("missing", None), ("three", [0, 0, 1]),
                           ("three", [0, 1]), ("three", [0, 1, 78])]:
            with self.assertRaises(ValueError):
                draw(key, seed=42, picks=picks)

    def test_answers_are_local_and_reproducible(self):
        """Question text does not steer the answer or decorative page number."""
        self.assertEqual(len(ANSWERS), 197)
        first = draw_answer("first question", seed=42)
        second = draw_answer("different question", seed=42)
        self.assertEqual(first["answer"], second["answer"])
        self.assertEqual(first["page"], second["page"])
        self.assertIn(first["answer"], ANSWERS)
        self.assertTrue(1 <= first["page"] <= 888)


class PromptsAndClientTest(unittest.TestCase):
    """Keep prompt creation offline and exercise transport using fake responses."""

    @classmethod
    def setUpClass(cls):
        """Create representative deterministic input records."""
        cls.records = {
            "bazi": calculate_bazi(1990, 6, 15, 12, 30, longitude=116.41),
            "astro": cast_astrology(1990, 6, 15, 12, 30, 39.90, 116.41),
            "tarot": draw("three", seed=42),
            "liuyao": cast_liuyao([6, 7, 8, 9, 7, 8], date=DATE),
        }

    def test_all_prompts_work_offline(self):
        """Full and lite prompts for all four modules perform no network access."""
        builders = {"bazi": build_prompt, "astro": build_astro_prompt,
                    "tarot": build_tarot_prompt, "liuyao": build_liuyao_prompt}
        with patch("urllib.request.urlopen", side_effect=AssertionError("unexpected network")):
            for module, builder in builders.items():
                for lite in (False, True):
                    system, user = builder(self.records[module], lite=lite)
                    self.assertTrue(system)
                    self.assertTrue(user)

    def test_followup_history_and_references(self):
        """History includes only user/assistant messages, and references keep facts."""
        for module, result in self.records.items():
            messages = build_followup_messages(
                module, result, "已有解读", [
                    {"role": "user", "content": "之前的问题"},
                    {"role": "assistant", "content": "之前的回答"},
                    {"role": "system", "content": "not a history turn"},
                    {"role": "user", "content": " "},
                ], "接下来呢？", refs=[{"label": "对照", "result": result}])
            self.assertEqual([m["role"] for m in messages], ["system", "user", "assistant", "user"])
            self.assertIn("对照", messages[0]["content"])
            self.assertEqual(messages[-1]["content"], "接下来呢？")

    def test_config_has_no_defaults_for_connection(self):
        """Caller must provide all three connection fields."""
        with self.assertRaises(TypeError):
            make_config()
        for args in [("", "test-token", "test-model"),
                     ("https://example.invalid/v1", "", "test-model"),
                     ("https://example.invalid/v1", "test-token", ""),
                     ("file:///tmp/api", "test-token", "test-model")]:
            with self.assertRaises(ValueError):
                make_config(*args)
        cfg = make_config("https://example.invalid/v1/", "test-token", "test-model")
        self.assertEqual(cfg["api_base"], "https://example.invalid/v1")
        self.assertEqual(cfg["fallback"], "off")

    def test_nonstream_response_and_request(self):
        """The standalone HTTP client builds the expected request and reads content."""
        from mystery.llm import interpret_chart
        from mystery.llm.client import list_models
        from unittest.mock import MagicMock

        response = MagicMock()
        response.__enter__.return_value = response
        response.read.return_value = json.dumps({"choices": [{"message": {"content": " 测试解读 "}}]}).encode()
        cfg = make_config("https://example.invalid/v1", "test-token", "test-model")
        with patch("urllib.request.urlopen", return_value=response) as call:
            self.assertEqual(interpret_chart(self.records["bazi"], cfg), "测试解读")
            request = call.call_args.args[0]
            self.assertEqual(request.full_url, "https://example.invalid/v1/chat/completions")
            self.assertEqual(json.loads(request.data)["model"], "test-model")
            self.assertEqual(request.get_header("Authorization"), "Bearer test-token")
        response.read.return_value = b'{"data":[{"id":"test-model"}]}'
        with patch("urllib.request.urlopen", return_value=response):
            self.assertEqual(list_models(cfg["api_base"], cfg["api_key"]), ["test-model"])

    def test_stream_events_and_usage(self):
        """SSE deltas and final token usage survive the extracted scheduler."""
        from mystery.llm import interpret_tarot_stream
        from unittest.mock import MagicMock

        response = MagicMock()
        response.__iter__.return_value = iter([
            b': heartbeat\n', b'data: not-json\n',
            'data: {"choices":[{"delta":{"content":"测试"}}]}\n'.encode(),
            b'data: {"choices":[],"usage":{"prompt_tokens":2,"completion_tokens":1,"total_tokens":3}}\n',
            b'data: [DONE]\n',
        ])
        cfg = make_config("https://example.invalid/v1", "test-token", "test-model")
        with patch("urllib.request.urlopen", return_value=response):
            events = list(interpret_tarot_stream(self.records["tarot"], cfg))
        self.assertEqual([e["text"] for e in events if e["type"] == "delta"], ["测试"])
        self.assertEqual([e["total_tokens"] for e in events if e["type"] == "usage"], [3])
        response.close.assert_called_once()

    def test_stream_falls_back_before_first_token(self):
        """A full-model failure can use the explicit lite model."""
        from mystery.llm.scheduler import _LLMScheduler

        cfg = make_config("https://example.invalid/v1", "test-token", "full",
                          lite_model="lite", fallback=True, retry=0)

        def fake_stream(base, key, model, messages, timeout, usage_out):
            """Fail the full model before emitting any content."""
            if model == "full":
                raise RuntimeError("temporary failure")
            yield "速览内容"

        with patch("mystery.llm.scheduler._stream_openai", side_effect=fake_stream):
            events = list(_LLMScheduler().stream(lambda: ("system", "full"),
                                                lambda: ("system", "lite"), cfg))
        self.assertTrue(any(e["type"] == "notice" for e in events))
        self.assertEqual([e["text"] for e in events if e["type"] == "delta"], ["速览内容"])

    def test_stream_does_not_repeat_after_partial_output(self):
        """A disconnect after content does not retry or append a lite answer."""
        from mystery.llm.scheduler import _LLMScheduler

        def broken_stream(*args):
            """Produce one token before a transport failure."""
            yield "已生成"
            raise RuntimeError("disconnected")

        cfg = make_config("https://example.invalid/v1", "test-token", "full", fallback=True)
        with patch("mystery.llm.scheduler._stream_openai", side_effect=broken_stream) as call:
            events = list(_LLMScheduler().stream(lambda: ("system", "full"),
                                                lambda: ("system", "lite"), cfg))
        self.assertEqual(call.call_count, 1)
        self.assertEqual([e["type"] for e in events], ["queue", "delta", "error"])


if __name__ == "__main__":
    unittest.main()
