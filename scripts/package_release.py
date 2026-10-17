"""Attach source, notices, usage notes and recorded validation to the built EXE."""
import hashlib
import json
from pathlib import Path
import shutil
import urllib.request
from runpy import run_path
from source_bundle import write_source_zip
import argparse

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "output" / "release"
VERSION = run_path(str(ROOT / "desktop" / "__init__.py"))["VERSION"]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-only', action='store_true', help='Prepare notices and sources without historical local validation reports')
    args = parser.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    shutil.copy2(ROOT / "DESKTOP.md", OUT / "使用说明.md")
    notices = OUT / "licenses"
    notices.mkdir(exist_ok=True)
    shutil.copytree(ROOT / "licenses", notices, dirs_exist_ok=True)
    if (ROOT / "LICENSE").exists():
        shutil.copy2(ROOT / "LICENSE", notices / "Mystery-LICENSE.txt")
    if (ROOT / "COPYRIGHT").exists():
        shutil.copy2(ROOT / "COPYRIGHT", notices / "Mystery-COPYRIGHT.txt")
    shutil.copy2(ROOT / "desktop" / "web" / "vendor" / "LICENSE", notices / "Three-LICENSE.txt")
    for name in ("iztro-LICENSE.txt", "THIRD_PARTY_NOTICES.txt"):
        shutil.copy2(ROOT / "mystery" / "ziwei" / "vendor" / name, notices / name)
    sources = OUT / "sources"
    sources.mkdir(exist_ok=True)
    # Include the exact Swiss Ephemeris source distribution and verify PyPI's hash.
    meta = json.load(urllib.request.urlopen("https://pypi.org/pypi/pyswisseph/2.10.3.2/json"))
    source = next(u for u in meta["urls"] if u["packagetype"] == "sdist")
    target = sources / source["filename"]
    if not target.exists(): target.write_bytes(urllib.request.urlopen(source["url"]).read())
    if hashlib.sha256(target.read_bytes()).hexdigest() != source["digests"]["sha256"]:
        raise RuntimeError("Swiss Ephemeris source hash does not match PyPI")
    (sources / "source-manifest.json").write_text(json.dumps({"pyswisseph": {
        "version": "2.10.3.2", "url": source["url"], "sha256": source["digests"]["sha256"]}}, indent=2), encoding="utf-8")
    source_zip = sources / f"Mystery-{VERSION}-source.zip"
    write_source_zip(ROOT, source_zip)
    if args.source_only:
        print(json.dumps({"sources": str(source_zip), "validation": "not performed by --source-only"}, indent=2))
        return
    algorithm = json.loads((ROOT / ".cache" / "exe-final-selftest.json").read_text(encoding="utf-8"))
    native = json.loads((ROOT / ".cache" / "exe-final-ui-test.json").read_text(encoding="utf-8"))
    if not all(x["ok"] for x in algorithm.values()) or not native["ok"]:
        raise RuntimeError("Final executable validation failed")
    interaction = json.loads((ROOT / ".cache" / "interaction-checks.json").read_text(encoding="utf-8"))
    offline = json.loads((ROOT / ".cache" / "unittest-final-summary.json").read_text(encoding="utf-8"))
    if offline["version"] != VERSION or offline["failed"]:
        raise RuntimeError("Run the current version's offline tests before packaging")
    report = {"version": VERSION, "executable": f"Mystery-{VERSION}.exe", "offline_tests": offline,
              "packaged_algorithms": {k: v["ok"] for k, v in algorithm.items()},
              "native_webview": native, "ui_result_pages": interaction.get("result_pages_verified", interaction.get("node_routes_verified", list(algorithm))),
              "interaction_checks": interaction,
              "image_generation": json.loads((ROOT / "desktop" / "web" / "assets" / "manifest.json").read_text(encoding="utf-8-sig")),
              "ai_validation": "Offline mocked streams and follow-up tests; see live_ai_validation when available.",
              "exe_sha256": hashlib.sha256((OUT / "Mystery.exe").read_bytes()).hexdigest(),
              "limitations": ["Requires Microsoft Edge WebView2 Runtime and a WebGL 2 capable driver.",
                              "No code signing certificate configured.", "Lenormand card faces use generated symbols; Tarot includes all 78 original RWS scans."]}
    report["tarot_art"] = json.loads((ROOT / "desktop" / "web" / "assets" / "tarot-rws" / "manifest.json").read_text(encoding="utf-8"))
    report["geography"] = json.loads((ROOT / "desktop/web/assets/geography/manifest.json").read_text(encoding="utf-8"))
    report['place_search'] = json.loads((ROOT / 'desktop/web/assets/geography/place-search-manifest.json').read_text(encoding='utf-8'))
    report['logo'] = json.loads((ROOT / 'desktop/web/assets/mystery-logo-manifest.json').read_text(encoding='utf-8'))
    live_ai = ROOT / '.cache' / ('llm-live-v' + VERSION.replace('.', '') + '.json')
    if live_ai.exists():
        report['live_ai_validation'] = json.loads(live_ai.read_text(encoding='utf-8'))
        if not report['live_ai_validation'].get('ok'):
            raise RuntimeError('Recorded live LLM validation failed')
    installer_manifest = OUT / "installer-manifest.json"
    if installer_manifest.exists():
        installer = json.loads(installer_manifest.read_text(encoding="utf-8"))
        if installer["version"] == VERSION:
            if hashlib.sha256((OUT / installer["filename"]).read_bytes()).hexdigest() != installer["sha256"]:
                raise RuntimeError("Installer hash does not match its manifest")
            report["installer"] = installer
            installer_test = ROOT / ".cache" / "installer-final-test.json"
            if installer_test.exists():
                check = json.loads(installer_test.read_text(encoding="utf-8"))
                if check["version"] == VERSION:
                    if not check["ok"]:
                        raise RuntimeError("Installer lifecycle validation failed")
                    report["installer_validation"] = check
    (OUT / "validation-report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"exe": str(OUT / "Mystery.exe"), "sha256": report["exe_sha256"],
                      "sources": str(source_zip)}, indent=2))


if __name__ == "__main__": main()
