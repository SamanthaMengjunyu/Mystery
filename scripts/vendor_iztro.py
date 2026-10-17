"""Copy the pinned upstream standalone bundle and third-party notices.

Usage: python scripts/vendor_iztro.py EXTRACTED_PACKAGE REFERENCE_NODE_MODULES
The inputs must already exist; this script performs no downloads or installs.
"""
import hashlib
import json
from pathlib import Path
import shutil
import sys


def main():
    package, modules = (Path(value).resolve() for value in sys.argv[1:])
    target = Path(__file__).resolve().parents[1] / "mystery" / "ziwei" / "vendor"
    target.mkdir(parents=True, exist_ok=True)
    metadata = json.loads((package / "package.json").read_text(encoding="utf-8"))
    if metadata["version"] != "2.6.2":
        raise ValueError("expected iztro 2.6.2")
    bundle = package / "dist" / "iztro-v2.6.2.min.js"
    shutil.copyfile(bundle, target / "iztro-2.6.2.min.js")
    shutil.copyfile(package / "LICENSE", target / "iztro-LICENSE.txt")
    notices = []
    notice_sources = {}
    # These are the dependencies named by the upstream standalone package.
    for name in metadata["dependencies"]:
        module = modules / name
        info = json.loads((module / "package.json").read_text(encoding="utf-8"))
        licenses = [p for p in module.iterdir() if p.is_file() and p.name.lower().startswith("license")]
        if not licenses:
            raise ValueError(f"missing license for {name}")
        notices.append(f"=== {name} ({info['license']}) ===\n" + licenses[0].read_text(encoding="utf-8"))
        notice_sources[name] = info["version"]
    (target / "THIRD_PARTY_NOTICES.txt").write_text("\n\n".join(notices), encoding="utf-8")
    manifest = {"name": "iztro", "version": "2.6.2", "license": "MIT",
                "source": "https://registry.npmjs.org/iztro/-/iztro-2.6.2.tgz",
                "npm_integrity": "sha512-7gwdUlFcHbxrQaHMcdnEBiphI1LeA0YM7+z8C+unHxCMNIJDYdfYdLSDW8sA1rqyeB7lYyAOt9h/FwbXII6dVQ==",
                "bundle_sha256": hashlib.sha256(bundle.read_bytes()).hexdigest(),
                "notice_text_source_versions": notice_sources,
                "note": "Bundle is unmodified upstream distribution. Notice source versions describe the license text copies, not an inferred bundle dependency lock."}
    (target / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
