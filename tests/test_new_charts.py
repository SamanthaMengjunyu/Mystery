"""New natal entrances: independent fixtures, boundaries and LLM integration."""
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from datetime import datetime
import json
from pathlib import Path
import shutil
import unittest
from unittest.mock import patch

from mystery.astrology import cast as western
from mystery.jyotish import cast as jyotish, nakshatra, navamsa_position, vimshottari
from mystery.ziwei import cast as ziwei
from mystery.llm import interpret_jyotish_stream, interpret_ziwei_stream
from mystery.llm.prompts import build_jyotish_prompt, build_ziwei_prompt, build_followup_messages

_FIXTURE = Path(__file__).with_name("fixtures") / "ziwei_reference.json"


@unittest.skipUnless(shutil.which("node"), "Ziwei engine requires local Node.js")
class ZiweiChartTest(unittest.TestCase):
    def test_independent_commonjs_reference_cases(self):
        reference = json.loads(_FIXTURE.read_text(encoding="utf-8"))
        for item in reference["cases"]:
            y, m, d = map(int, item["date"].split("-"))
            hour = 23 if item["time_index"] == 12 else max(0, item["time_index"] * 2)
            with self.subTest(case=item["label"]):
                chart = ziwei(y, m, d, hour, gender=item["gender"], fix_leap=item["fix_leap"],
                              day_divide=item["day_divide"], target_year=2026)
                natal = {**chart["birth"], "palaces": chart["palaces"]}
                self.assertEqual(natal, item["expected"]["natal"])
                self.assertEqual(chart["decadals"], item["expected"]["decadals"])
                self.assertEqual(chart["annual"], item["expected"]["annual"])

    def test_palaces_stars_and_mutagens(self):
        chart = ziwei(2000, 8, 16, 4, gender="女", target_year=2026)
        self.assertEqual(chart["summary"], "午命/戌身 · 木三局")
        self.assertEqual(len(chart["palaces"]), 12)
        self.assertEqual(sum(p["isBodyPalace"] for p in chart["palaces"]), 1)
        self.assertEqual(len({p["earthlyBranch"] for p in chart["palaces"]}), 12)
        self.assertEqual(sum(len(p["majorStars"]) for p in chart["palaces"]), 14)
        self.assertEqual({m["mutagen"] for m in chart["analysis"]["natal_mutagens"]}, set("禄权科忌"))
        self.assertEqual(chart["analysis"]["soul_palace"]["name"], "命宫")
        self.assertEqual(len(chart["analysis"]["soul_surrounding_palaces"]), 4)
        self.assertTrue(all(b["yearRange"][1] - b["yearRange"][0] == 9 for b in chart["decadals"]))
        json.dumps(chart, allow_nan=False, ensure_ascii=False)

    def test_explicit_time_and_no_implicit_annual(self):
        first = ziwei(2024, 1, 15, 0, 30, tz_name="America/New_York")
        second = ziwei(2024, 1, 15, 13, 30)
        self.assertEqual(first["palaces"], second["palaces"])
        self.assertEqual(first["time"]["utc"], second["time"]["utc"])
        self.assertIsNone(first["annual"])
        self.assertIsNone(first["rules"]["annual_reference"])

    def test_true_solar_can_change_the_birth_date(self):
        chart = ziwei(2000, 1, 1, 0, 15, longitude=75, use_true_solar=True)
        self.assertTrue(chart["calculation_time"]["clock"].startswith("1999-12-31"))
        self.assertIsNotNone(chart["true_solar"])


class NewChartValidationTest(unittest.TestCase):
    def test_ziwei_reports_missing_runtime(self):
        with patch("mystery.ziwei.engine.shutil.which", return_value=None):
            with self.assertRaisesRegex(RuntimeError, "Node.js"):
                ziwei(2000, 8, 16, 4)

    def test_invalid_ziwei_rules_fail_before_node(self):
        with patch("mystery.ziwei.engine._run_engine", side_effect=AssertionError("engine invoked")):
            for options in ({"fix_leap": "true"}, {"gender": "unknown"},
                            {"use_true_solar": True}, {"day_divide": "unknown"},
                            {"target_year": 1999}, {"target_year": True}):
                with self.subTest(options=options), self.assertRaises(ValueError):
                    ziwei(2000, 8, 16, 4, **options)

    def test_shared_dst_validation_and_jyotish_options(self):
        for function, args in ((ziwei, (2024, 3, 10, 2, 30)),
                               (jyotish, (2024, 3, 10, 2, 30, 40, -74))):
            with self.assertRaises(ValueError):
                function(*args, tz_name="America/New_York")
        for options in ({"node_mode": "other"}, {"dasha_year": "other"}, {"lat": 90}, {"lat": float("nan")}):
            args = {"year": 2000, "month": 1, "day": 1, "hour": 12, "minute": 0,
                    "lat": 13.08, "lon": 80.27, **options}
            with self.subTest(options=options), self.assertRaises(ValueError):
                jyotish(**args)


class JyotishChartTest(unittest.TestCase):
    def test_textbook_moon_and_ascendant_examples(self):
        # PVR Narasimha Rao, Vedic Astrology: An Integrated Approach,
        # https://vedicastrologer.org/articles/vedic_astro_textbook.pdf
        # Example 50, printed p211: 2000-04-28 05:50 UTC-04, Moon 2°23' Aquarius.
        chart = jyotish(2000, 4, 28, 5, 50, 40.7, -74, "America/New_York")
        moon = chart["grahas"]["Moon"]
        self.assertAlmostEqual(moon["longitude"], 300 + 2 + 23 / 60, delta=1 / 60)
        self.assertEqual((moon["nakshatra"]["name"], moon["nakshatra"]["pada"]), ("Dhanishtha", 3))
        # Example 130, printed p428: 1966-11-30 10:36 IST, 77E47 11N19,
        # published Lagna 13°16' Capricorn. Compare within a rounded arcminute.
        chart = jyotish(1966, 11, 30, 10, 36, 11 + 19 / 60, 77 + 47 / 60)
        self.assertAlmostEqual(chart["d1"]["lagna"]["longitude"], 270 + 13 + 16 / 60, delta=1 / 60)

    def test_textbook_d9_and_dasha_balance(self):
        # Textbook Example 16, printed p55; input/output signs from the worked example.
        self.assertEqual(navamsa_position(60 + 11)["sign"], "摩羯")
        self.assertEqual(navamsa_position(210 + 19)["sign"], "射手")
        # Example 50 uses rounded Moon 2°23' Aquarius: Mars balance 2.24875 years.
        periods = vimshottari(2451662.9, 300 + 2 + 23 / 60, year="savana")
        self.assertEqual(periods["at_birth"]["mahadasha"], "Mars")
        self.assertAlmostEqual(periods["birth_balance_years"], 2.24875, places=10)

    def test_all_navamsa_and_nakshatra_boundaries(self):
        # Independent sign-based construction: movable/same, fixed/ninth, dual/fifth.
        for sign in range(12):
            start = (sign + (0, 8, 4)[sign % 3]) % 12
            for part in range(9):
                longitude = sign * 30 + (part + 0.5) * (30 / 9)
                self.assertEqual(navamsa_position(longitude)["sign_idx"], (start + part) % 12)
        self.assertEqual(navamsa_position(10 / 3 - 1e-9)["sign_idx"], 0)
        self.assertEqual(navamsa_position(10 / 3)["sign_idx"], 1)
        for index in range(27):
            for pada in range(4):
                middle = (index + (pada + 0.5) / 4) * (360 / 27)
                self.assertEqual((nakshatra(middle)["index"], nakshatra(middle)["pada"]), (index + 1, pada + 1))

    def test_nine_grahas_whole_sign_houses_and_opposite_nodes(self):
        chart = jyotish(1990, 6, 15, 12, 30, 13.08, 80.27)
        self.assertEqual(len(chart["grahas"]), 9)
        self.assertAlmostEqual((chart["grahas"]["Ketu"]["longitude"] - chart["grahas"]["Rahu"]["longitude"]) % 360, 180)
        for varga in (chart["d1"], chart["d9"]):
            self.assertEqual(len(varga["houses"]), 12)
            for point in varga["points"].values():
                self.assertTrue(1 <= point["house"] <= 12)
                self.assertEqual(varga["houses"][point["house"] - 1]["sign_idx"], point["sign_idx"])
        json.dumps(chart, allow_nan=False)

    def test_dasha_periods_are_contiguous_and_cover_birth(self):
        for year_days in ("sidereal", "julian", "savana"):
            periods = vimshottari(2451545, 6.0, year=year_days)
            majors = periods["mahadashas"]
            self.assertEqual(len(majors), 9)
            self.assertEqual(sum(p["years"] for p in majors), 120)
            self.assertAlmostEqual(majors[-1]["end_jd"] - majors[0]["start_jd"],
                                   120 * periods["year_days"], places=7)
            for index, major in enumerate(majors):
                if index:
                    self.assertEqual(majors[index - 1]["end_jd"], major["start_jd"])
                children = major["antardashas"]
                self.assertEqual(children[0]["start_jd"], major["start_jd"])
                self.assertEqual(children[-1]["end_jd"], major["end_jd"])
                self.assertAlmostEqual(sum(p["years"] for p in children), major["years"])
                for previous, current in zip(children, children[1:]):
                    self.assertEqual(previous["end_jd"], current["start_jd"])

    def test_cross_zone_same_instant_and_supported_endpoints(self):
        a = jyotish(2024, 1, 15, 0, 30, 13, 80, "America/New_York")
        b = jyotish(2024, 1, 15, 11, 0, 13, 80, "Asia/Kolkata")
        self.assertEqual(a["grahas"], b["grahas"])
        for y, m, d, zone in ((1900, 1, 1, "Etc/GMT-14"), (2100, 12, 31, "Etc/GMT+12")):
            chart = jyotish(y, m, d, 12, 0, 13, 80, zone)
            self.assertIsNotNone(chart["vimshottari"]["at_birth"])

    def test_sidereal_settings_do_not_change_western_results(self):
        args = (2000, 1, 1, 12, 0, 13, 80)
        reference = western(*args)
        sidereal = jyotish(*args)
        self.assertGreater(abs(reference["points"]["太阳"]["lon"] - sidereal["grahas"]["Sun"]["longitude"]), 20)
        with ThreadPoolExecutor(max_workers=4) as pool:
            futures = [pool.submit(western if index % 2 else jyotish, *args) for index in range(8)]
            values = [future.result() for future in futures]
        for index, value in enumerate(values):
            self.assertEqual(value["points"] if index % 2 else value["grahas"],
                             reference["points"] if index % 2 else sidereal["grahas"])


@unittest.skipUnless(shutil.which("node"), "new prompt integration uses a real Ziwei chart")
class NewChartInterpretationTest(unittest.TestCase):
    def test_offline_prompts_followups_and_stream_routing(self):
        charts = [("ziwei", ziwei(2000, 8, 16, 4), build_ziwei_prompt, interpret_ziwei_stream),
                  ("jyotish", jyotish(2000, 1, 1, 12, 0, 13, 80), build_jyotish_prompt, interpret_jyotish_stream)]
        for module, chart, builder, service in charts:
            original = deepcopy(chart)
            for lite in (False, True):
                system, user = builder(chart, lite=lite)
                self.assertTrue(system and user)
                self.assertIn("不可", system)
            messages = build_followup_messages(module, chart, "已有解读", [], "事业如何？")
            self.assertEqual(messages[-1]["content"], "事业如何？")
            with patch("mystery.llm.service._run_stream") as run:
                run.return_value = iter([{"type": "delta", "text": "test"}])
                self.assertEqual(list(service(chart, {}))[0]["text"], "test")
                full, lite, cfg = run.call_args.args
                self.assertEqual(full(), builder(chart, lite=False))
                self.assertEqual(lite(), builder(chart, lite=True))
            self.assertEqual(chart, original)


if __name__ == "__main__":
    unittest.main()
