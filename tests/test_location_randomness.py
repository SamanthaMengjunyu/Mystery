"""Optional location binds locally without storing coordinates or replacing OS entropy."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from desktop.backend import Backend
from mystery.randomness import DrawRandom, interaction_evidence, validate_random_evidence


CONTEXT = {"schema": "location-input-v1", "source": "device", "commitment": "8" * 64}
EVENTS = [{"x": .25, "y": .75, "t_ms": 0}]


class LocationRandomTest(unittest.TestCase):
    def test_location_changes_mixed_randomness_with_same_os_bytes(self):
        first = interaction_evidence(EVENTS, location=CONTEXT)
        other = interaction_evidence(EVENTS, location={**CONTEXT, "commitment": "9" * 64})
        self.assertEqual(first["events_sha256"], other["events_sha256"])
        self.assertNotEqual(first["context_sha256"], other["context_sha256"])
        self.assertNotIn(CONTEXT["commitment"], json.dumps(first))
        self.assertEqual(first["location_source"], "device")
        with patch("mystery.randomness.secrets.token_bytes", return_value=b'\x19' * 32) as os_random:
            values = [DrawRandom('test', interaction=e).randbelow(2**256) for e in (first, other)]
            self.assertEqual(os_random.call_count, 2)
            self.assertNotEqual(*values)
        sampler = DrawRandom('test', interaction=first)
        self.assertEqual(validate_random_evidence(sampler.evidence, 'test'), sampler.evidence)

    def test_location_rejects_raw_coordinates_and_invalid_commitments(self):
        for value in ({"latitude": 31.23, "longitude": 121.47},
                      {**CONTEXT, "latitude": 31.23}, {**CONTEXT, "source": "ip"},
                      {**CONTEXT, "commitment": 'g' * 64}, {**CONTEXT, "commitment": 'a'},
                      {**CONTEXT, "schema": 'unknown'}, 'a' * 64):
            with self.subTest(value=value), self.assertRaises(ValueError):
                interaction_evidence(EVENTS, location=value)
        bad = interaction_evidence(location=CONTEXT)
        bad['location_source'] = 'ip'
        with self.assertRaises(ValueError):
            DrawRandom('test', interaction=bad)

    def test_all_random_modules_keep_replay_and_export_without_location_input(self):
        with tempfile.TemporaryDirectory() as folder:
            backend = Backend(Path(folder))
            for module in ('tarot', 'lenormand', 'liuyao', 'answers'):
                with self.subTest(module=module):
                    p = {'module': module, 'datetime': '2026-10-15T12:00', 'interaction': EVENTS,
                         'random_location': dict(CONTEXT)}
                    if module in ('tarot', 'lenormand'):
                        p.update(backend.shuffle(p))
                    record = backend.calculate(p)
                    self.assertEqual(record['result']['random']['interaction']['location_source'], 'device')
                    self.assertTrue(backend.replay(record['id'])['verified'])
                    self.assertNotIn('random_location', record['inputs'])
                    self.assertNotIn('interaction', record['inputs'])
                    self.assertNotIn(CONTEXT['commitment'], json.dumps(record))
                    self.assertEqual(backend.import_record({'record': record})['result'], record['result'])
                    if module != 'answers':
                        prompt = backend.prompt({'id': record['id']})
                        self.assertNotIn(CONTEXT['commitment'], json.dumps(prompt))
            self.assertNotIn(CONTEXT['commitment'].encode(), backend.db_path.read_bytes())

    def test_seed_simulation_ignores_location_and_no_pointer_is_supported(self):
        self.assertIsNone(Backend.evidence({}))
        options = Backend.random_options({'seed': '42', 'random_location': CONTEXT, 'interaction': EVENTS})
        self.assertEqual(options, {'seed': 42})
        evidence = Backend.evidence({'random_location': CONTEXT})
        self.assertEqual(evidence['event_count'], 0)
        self.assertEqual(evidence['schema'], 'interaction-v2')
        self.assertEqual(DrawRandom('test', interaction=evidence).evidence['source'], 'os-csprng')

    def test_prepared_deck_location_is_frozen_and_raw_input_cannot_be_saved(self):
        with tempfile.TemporaryDirectory() as folder:
            backend = Backend(Path(folder))
            p = {'module': 'tarot', 'random_location': dict(CONTEXT)}
            p.update(backend.shuffle(p))
            p['random_location'] = {**CONTEXT, 'source': 'manual', 'commitment': '9' * 64}
            record = backend.calculate(p)
            self.assertEqual(record['result']['random']['interaction']['location_source'], 'device')
            with self.assertRaises(ValueError):
                backend.shuffle({'module': 'tarot', 'random_location': {'latitude': 31.23, 'longitude': 121.47}})
            self.assertEqual(len(backend.records()), 1)
