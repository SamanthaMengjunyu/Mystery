"""Versioned book pages; explicit seeds retain the old decorative-page behavior."""
from copy import deepcopy

from ..randomness import DrawRandom, digest, validate_random_evidence

from .data import ANSWERS


def draw_answer(question="", seed=None, *, interaction=None):
    """Default: 197 fixed pages. Explicit seed: old 888 decorative pages."""
    rng = DrawRandom("answers", seed=seed, interaction=interaction)
    if seed is None:
        page = rng.randbelow(len(ANSWERS)) + 1
        index = page - 1
        version = "answers-fixed-pages-v1"
    else:
        page = rng.randbelow(888) + 1
        index = rng.randbelow(len(ANSWERS))
        version = "answers-legacy-v1"
    snapshot = {"schema": version, "pool_sha256": digest(ANSWERS),
                "page": page, "answer_index": index, "random": deepcopy(rng.evidence)}
    return {"question": (question or "").strip(), "page": page,
            "answer": ANSWERS[index], "random": deepcopy(rng.evidence), "replay": snapshot}


def replay(snapshot, question=""):
    """Replay without randomness; detect incompatible answer pool versions."""
    if not isinstance(snapshot, dict):
        raise ValueError("invalid answer replay")
    version = snapshot.get("schema")
    page, index = snapshot.get("page"), snapshot.get("answer_index")
    limit = len(ANSWERS) if version == "answers-fixed-pages-v1" else 888
    if (version not in ("answers-fixed-pages-v1", "answers-legacy-v1")
            or snapshot.get("pool_sha256") != digest(ANSWERS)
            or type(page) is not int or not 1 <= page <= limit
            or type(index) is not int or not 0 <= index < len(ANSWERS)
            or (version == "answers-fixed-pages-v1" and index != page - 1)
            or not isinstance(snapshot.get("random"), dict)):
        raise ValueError("invalid answer replay or changed pool")
    evidence = validate_random_evidence(snapshot["random"], "answers")
    if ((version == "answers-legacy-v1") != (evidence["source"] == "explicit-seed")):
        raise ValueError("answer rules and random source disagree")
    return {"question": (question or "").strip(), "page": page, "answer": ANSWERS[index],
            "random": deepcopy(snapshot["random"]), "replay": deepcopy(snapshot)}
