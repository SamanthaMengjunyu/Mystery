"""Export the clean GitHub repository and validated current Windows release assets."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
from runpy import run_path
import shutil
import zipfile

from source_bundle import source_files

ROOT = Path(__file__).resolve().parent.parent
VERSION = run_path(str(ROOT / "desktop/__init__.py"))["VERSION"]


def sha256(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest() if hasattr(hashlib, "file_digest") else hashlib.sha256(stream.read()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "output" / f"Mystery-{VERSION}-opensource")
    parser.add_argument("--zip", action="store_true", help="Also create a transport ZIP next to the handoff folder")
    args = parser.parse_args()
    target = args.output.resolve()
    if target.exists():
        raise SystemExit("Output already exists; choose a new --output to preserve earlier handoffs.")
    zip_path = target.with_name(target.name + ".zip")
    if args.zip and zip_path.exists():
        raise SystemExit("Transport ZIP already exists; choose a new --output.")
    files = source_files(ROOT)
    if not (ROOT / 'LICENSE').is_file() or not (ROOT / 'COPYRIGHT').is_file():
        raise SystemExit('Project LICENSE and COPYRIGHT are required.')
    # Fail without printing matching contents, which may themselves be credentials.
    patterns = [rb"sk-[A-Za-z0-9_-]{24,}", rb"gh[pousr]_[A-Za-z0-9]{24,}",
                rb"github_pat_[A-Za-z0-9_]{24,}", rb"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"]
    for path in files:
        if path.suffix.lower() in {".png", ".jpg", ".ico", ".icns"}:
            continue
        content = path.read_bytes()
        if any(re.search(pattern, content) for pattern in patterns):
            raise SystemExit(f"Potential credential in {path.relative_to(ROOT)}; inspect locally before exporting.")
    release = ROOT / "output/release"
    build = json.loads((release / "build-manifest.json").read_text(encoding="utf-8"))
    installer = json.loads((release / "installer-manifest.json").read_text(encoding="utf-8"))
    for manifest in (build, installer):
        if manifest["version"] != VERSION or Path(manifest["filename"]).name != manifest["filename"]:
            raise SystemExit("Windows manifest version or filename mismatch")
        binary = release / manifest["filename"]
        if sha256(binary) != manifest["sha256"]:
            raise SystemExit(f"Windows checksum mismatch: {binary.name}")
    if installer['installed_exe_sha256'] != build['sha256']:
        raise SystemExit('Installer does not contain the current EXE.')
    validation = json.loads((release / 'validation-windows.json').read_text(encoding='utf-8'))
    if not validation['ok'] or validation['setup_sha256'] != installer['sha256'] or validation['exe_sha256'] != build['sha256']:
        raise SystemExit('Current Windows validation report is missing or stale.')
    source_manifest = json.loads((release / "sources/source-manifest.json").read_text(encoding="utf-8"))
    upstream = release / "sources/pyswisseph-2.10.3.2.tar.gz"
    if sha256(upstream) != source_manifest["pyswisseph"]["sha256"]:
        raise SystemExit("pyswisseph source checksum mismatch")
    corresponding = release / "sources" / f"Mystery-{VERSION}-source.zip"
    if sha256(corresponding) != validation['source_sha256']:
        raise SystemExit('Windows validation source hash mismatch.')
    with zipfile.ZipFile(corresponding) as archive:
        if set(archive.namelist()) != {p.relative_to(ROOT).as_posix() for p in files}:
            raise SystemExit('Corresponding source file list differs from current repository.')
        for path in files:
            if archive.read(path.relative_to(ROOT).as_posix()) != path.read_bytes():
                raise SystemExit(f'Corresponding source differs: {path.relative_to(ROOT)}')
        for info in archive.infolist():
            archived_path = Path(info.filename)
            if archived_path.is_absolute() or '..' in archived_path.parts or any(
                    part in {'.cache', '.git', '.venv', '__pycache__', 'node_modules'}
                    for part in archived_path.parts) or archived_path.suffix in {'.db', '.sqlite3', '.p12', '.pfx', '.key'}:
                raise SystemExit(f"Unexpected private/build path in corresponding source: {info.filename}")
            if archived_path.suffix.lower() in {'.py', '.js', '.mjs', '.cjs', '.json', '.md', '.txt', '.toml'}:
                if any(re.search(pattern, archive.read(info)) for pattern in patterns):
                    raise SystemExit(f"Potential credential in corresponding source: {info.filename}")
    target.mkdir(parents=True)
    repo = target / "repository"
    repo.mkdir()
    for path in files:
        dest = repo / path.relative_to(ROOT)
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, dest)
    ref = target / "release-assets"
    ref.mkdir()
    # The installer already embeds the Windows EXE; do not duplicate that 66 MB file.
    for path in (release / installer["filename"], release / "build-manifest.json",
                 release / "installer-manifest.json", corresponding, upstream,
                 release / "sources/source-manifest.json", release / 'validation-windows.json'):
        shutil.copy2(path, ref / path.name)
    with zipfile.ZipFile(ref / f'Mystery-{VERSION}-windows-licenses.zip', 'w', zipfile.ZIP_DEFLATED) as archive:
        for path in sorted((release / 'licenses').rglob('*')):
            if path.is_file():
                archive.write(path, 'licenses/' + path.relative_to(release / 'licenses').as_posix())
    (ref / 'SHA256SUMS.txt').write_text(''.join(
        f'{sha256(p)}  {p.name}\n' for p in sorted(ref.iterdir()) if p.is_file()), encoding='utf-8')
    shutil.copy2(ROOT / "docs/OPEN_SOURCE_HANDOFF.md", target / "先读交接说明.md")
    report = {
        "version": VERSION,
        "project_license_confirmed": (repo / "LICENSE").is_file(),
        "source_file_count": len(files),
        "prepared_at_utc": datetime.now(timezone.utc).isoformat(),
        "credential_scan": "No matches for known private-key and token patterns; not a guarantee of absence.",
        "macos_validation": "Not built or run on macOS; see repository/docs/MACOS_BUILD.md.",
        "windows_release": "Rebuilt 0.11.1 with current frosted silver UI, license and corresponding source.",
        "repository_source": "Matches Windows corresponding source ZIP file for file.",
        "project_license": "AGPL-3.0-only",
        "copyright_holder": "SaSa (SamanthaMengjunyu)",
        "files": {p.relative_to(target).as_posix(): {"bytes": p.stat().st_size, "sha256": sha256(p)}
                  for p in sorted(target.rglob("*")) if p.is_file()},
    }
    (target / "HANDOFF_MANIFEST.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (target / "SHA256SUMS.txt").write_text("".join(
        f"{sha256(p)}  {p.relative_to(target).as_posix()}\n"
        for p in sorted(target.rglob("*")) if p.is_file() and p.name != "SHA256SUMS.txt"), encoding="utf-8")
    if args.zip:
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as archive:
            for path in sorted(target.rglob("*")):
                if path.is_file():
                    archive.write(path, target.name + "/" + path.relative_to(target).as_posix())
        zip_path.with_suffix(".zip.sha256").write_text(f"{sha256(zip_path)}  {zip_path.name}\n", encoding="utf-8")
    print(json.dumps({"directory": str(target), "source_files": len(files),
                      "license_confirmed": report["project_license_confirmed"],
                      "zip": str(zip_path) if args.zip else None}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
