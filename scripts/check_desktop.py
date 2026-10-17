"""Run offline tests and record the actual counts for release packaging."""
import json
from pathlib import Path
from runpy import run_path
import sys
import unittest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
suite = unittest.defaultTestLoader.discover(str(ROOT / "tests"))
result = unittest.TextTestRunner(verbosity=1).run(suite)
failed = len(result.errors) + len(result.failures)
summary = {"version": run_path(str(ROOT / "desktop" / "__init__.py"))["VERSION"],
           "passed": result.testsRun - failed - len(result.skipped), "failed": failed, "skipped": len(result.skipped)}
path = ROOT / ".cache" / "unittest-final-summary.json"
path.parent.mkdir(parents=True, exist_ok=True)
path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
sys.exit(0 if result.wasSuccessful() else 1)
