"""OS-backed sampling, optional interaction evidence, and legacy seed compatibility.

Interaction digests bind supplied input to a draw; they do not authenticate a
human, estimate entropy, or prove that an application did not reroll a result.
No device information is collected by this module.
"""
import hashlib
import hmac
import json
import math
import secrets
from copy import deepcopy
from random import Random


def digest(value):
    """SHA-256 over canonical, finite JSON; also used to version static pools."""
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True,
                         separators=(",", ":"), allow_nan=False).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def interaction_evidence(events=(), *, device_time=None, app_version=None, location=None):
    """Summarize up to 4096 pointer samples without retaining the raw trail.

    Samples: {x: 0..1, y: 0..1, t_ms: nonnegative relative time}; time must
    not decrease or exceed 24 hours. Coordinates are relative to the interaction area's size.
    A touch/keyboard user may supply no samples. Optional context is caller
    supplied, untrusted and never counted as entropy. IP/OS identifiers are
    deliberately not part of this interface. Optional location is a browser-side
    salted commitment, never coordinates. Its secret nonce is not retained.
    """
    if not isinstance(events, (list, tuple)) or len(events) > 4096:
        raise ValueError("events must be a list/tuple of at most 4096 samples")
    samples = []
    previous = 0
    for event in events:
        if not isinstance(event, dict) or set(event) != {"x", "y", "t_ms"}:
            raise ValueError("each pointer sample requires only x, y, t_ms")
        values = [event[key] for key in ("x", "y", "t_ms")]
        if any(isinstance(v, bool) or not isinstance(v, (int, float))
               or (isinstance(v, float) and not math.isfinite(v)) for v in values):
            raise ValueError("pointer values must be finite numbers")
        x, y, time = values
        if not (0 <= x <= 1 and 0 <= y <= 1 and previous <= time <= 86_400_000):
            raise ValueError("coordinates must be in 0..1; times must increase within 24 hours")
        samples.append([round(x, 6), round(y, 6), round(time, 3)])
        previous = time
    context = {}
    for name, value in (("device_time", device_time), ("app_version", app_version)):
        if value is not None:
            if not isinstance(value, str) or len(value) > 128:
                raise ValueError(f"{name} must be a string of at most 128 characters")
            context[name] = value
    if location is not None:
        if (not isinstance(location, dict) or set(location) != {"schema", "source", "commitment"}
                or location["schema"] != "location-input-v1" or location["source"] not in ("device", "manual")
                or not isinstance(location["commitment"], str) or len(location["commitment"]) != 64
                or any(c not in "0123456789abcdef" for c in location["commitment"])):
            raise ValueError("location requires a salted commitment; raw coordinates are not accepted")
        context["location"] = dict(location)
    return {"schema": "interaction-v2" if location is not None else "interaction-v1",
            "event_count": len(samples), "events_sha256": digest(samples), "context_sha256": digest(context),
            **({"location_source": location["source"]} if location is not None else {})}


def _validate_evidence(evidence):
    expected = {"schema", "event_count", "events_sha256", "context_sha256"}
    if isinstance(evidence, dict) and evidence.get("schema") == "interaction-v2":
        expected.add("location_source")
        if evidence.get("location_source") not in ("device", "manual"):
            raise ValueError("invalid location source")
    if not isinstance(evidence, dict) or set(evidence) != expected:
        raise ValueError("use interaction_evidence() to create interaction input")
    count = evidence["event_count"]
    if (evidence["schema"] not in ("interaction-v1", "interaction-v2") or type(count) is not int
            or not 0 <= count <= 4096):
        raise ValueError("invalid interaction evidence")
    for name in ("events_sha256", "context_sha256"):
        value = evidence[name]
        if (not isinstance(value, str) or len(value) != 64
                or any(c not in "0123456789abcdef" for c in value)):
            raise ValueError("invalid interaction digest")
    return dict(evidence)


def validate_random_evidence(evidence, purpose, *, allow_manual=False):
    """Validate saved source labels and structure, not their authenticity."""
    expected = {"schema", "purpose", "source", "algorithm", "interaction"}
    if (not isinstance(evidence, dict) or set(evidence) != expected
            or evidence["schema"] != "random-v1" or evidence["purpose"] != purpose):
        raise ValueError("invalid random evidence")
    source, algorithm, interaction = (evidence[key] for key in
                                      ("source", "algorithm", "interaction"))
    if source == "os-csprng":
        if algorithm == "os-hmac-sha256-rejection-v1":
            _validate_evidence(interaction)
        elif algorithm != "secrets-randbelow-v1" or interaction is not None:
            raise ValueError("invalid OS random evidence")
    elif source == "explicit-seed":
        if algorithm != "python-random-legacy-v1" or interaction is not None:
            raise ValueError("invalid legacy random evidence")
    elif allow_manual and source == "manual":
        if algorithm != "external-tosses" or interaction is not None:
            raise ValueError("invalid manual random evidence")
    else:
        raise ValueError("unknown random source")
    return deepcopy(evidence)


class DrawRandom:
    """Fresh OS randomness for every candidate; unbiased rejection sampling.

    With interaction input, HMAC-SHA256 mixes each fresh 256-bit OS key with
    its digest, purpose and counter. This is not a seeded PRNG or a claim of
    NIST validation. Without interaction, secrets.randbelow is used directly.
    An explicit seed selects the old Python PRNG, exclusively for compatibility.
    """

    def __init__(self, purpose, *, seed=None, interaction=None):
        if not isinstance(purpose, str) or not 1 <= len(purpose) <= 64:
            raise ValueError("purpose must be a nonempty string of at most 64 characters")
        if seed is not None and interaction is not None:
            raise ValueError("legacy seed and interaction cannot be combined")
        self._legacy = Random(seed) if seed is not None else None
        self._interaction = (_validate_evidence(interaction)
                             if interaction is not None else None)
        self._purpose = purpose
        self._counter = 0
        self._evidence = {
            "schema": "random-v1", "purpose": purpose,
            "source": "explicit-seed" if seed is not None else "os-csprng",
            "algorithm": ("python-random-legacy-v1" if seed is not None else
                          "os-hmac-sha256-rejection-v1" if interaction is not None else
                          "secrets-randbelow-v1"),
            "interaction": self._interaction,
        }

    @property
    def evidence(self):
        """An isolated record; callers cannot alter the sampler via metadata."""
        return deepcopy(self._evidence)

    def randbelow(self, upper):
        if type(upper) is not int or not 0 < upper <= 2 ** 256:
            raise ValueError("upper must be an integer in 1..2**256")
        if self._legacy is not None:
            return self._legacy.randrange(upper)
        if self._interaction is None:
            return secrets.randbelow(upper)
        limit = 2 ** 256 - (2 ** 256 % upper)
        while True:
            message = {"domain": "mystery-draw-v1", "purpose": self._purpose,
                       "interaction": self._interaction, "counter": self._counter}
            self._counter += 1
            value = int.from_bytes(hmac.new(secrets.token_bytes(32),
                                           bytes.fromhex(digest(message)),
                                           hashlib.sha256).digest(), "big")
            if value < limit:
                return value % upper

    def shuffle(self, values):
        if self._legacy is not None:
            self._legacy.shuffle(values)
            return
        for index in range(len(values) - 1, 0, -1):
            other = self.randbelow(index + 1)
            values[index], values[other] = values[other], values[index]

    def reversed(self):
        # Preserve the original seeded tarot stream exactly.
        if self._legacy is not None:
            return self._legacy.random() < 0.5
        return bool(self.randbelow(2))
