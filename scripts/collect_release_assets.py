"""Collect final Windows and macOS release attachments without publishing anything."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from runpy import run_path
import shutil

ROOT = Path(__file__).resolve().parent.parent
VERSION = run_path(str(ROOT / 'desktop/__init__.py'))['VERSION']


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify_checksums(folder):
    for line in (folder / 'SHA256SUMS.txt').read_text(encoding='utf-8').splitlines():
        digest, name = line.split('  ', 1)
        path = (folder / name).resolve()
        if not path.is_relative_to(folder.resolve()) or sha256(path) != digest:
            raise ValueError(f'Attachment checksum mismatch: {name}')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--windows-dir', type=Path, required=True)
    parser.add_argument('--macos-dir', type=Path, action='append', required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    windows = args.windows_dir.resolve()
    verify_checksums(windows)
    items = [(p, p.name) for p in sorted(windows.iterdir())
             if p.is_file() and p.name != 'SHA256SUMS.txt']
    mac_records = []
    for folder in args.macos_dir:
        manifest = json.loads((folder / 'build-manifest.json').read_text(encoding='utf-8'))
        arch = manifest['architecture']
        if manifest['version'] != VERSION or arch not in {'arm64', 'x86_64'}:
            raise ValueError('Unexpected macOS version or architecture')
        filename = manifest.get('filename', f'Mystery-{VERSION}-macos-{arch}.dmg')
        if filename not in {f'Mystery-{VERSION}-macos-{arch}.{ext}' for ext in ('dmg', 'pkg')}:
            raise ValueError('Unexpected macOS installer filename')
        dmg = folder / filename
        # Recompute from the final file: notarization stapling changes the DMG hash.
        manifest.update(sha256=sha256(dmg), bytes=dmg.stat().st_size)
        items.extend([(dmg, dmg.name),
                      (folder / 'requirements-macos-resolved.txt', f'requirements-macos-{arch}.txt'),
                      (folder / 'sources' / f'Mystery-{VERSION}-source.zip', f'Mystery-{VERSION}-macos-{arch}-source.zip'),
                      (folder / f'Mystery-{VERSION}-macos-{arch}-licenses.zip', f'Mystery-{VERSION}-macos-{arch}-licenses.zip')])
        mac_records.append((f'build-macos-{arch}.json', manifest))
    for path, name in items:
        if not path.is_file() or path.is_symlink():
            raise ValueError(f'Missing release attachment: {path}')
    names = [name for _, name in items] + [name for name, _ in mac_records]
    if len(set(names)) != len(names):
        raise ValueError('Duplicate attachment or repeated macOS architecture')
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=False)
    for path, name in items:
        shutil.copy2(path, out / name)
    for name, manifest in mac_records:
        (out / name).write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    report = {'version': VERSION, 'collected_at_utc': datetime.now(timezone.utc).isoformat(),
              'files': {p.name: {'bytes': p.stat().st_size, 'sha256': sha256(p)} for p in sorted(out.iterdir())}}
    (out / 'release-manifest.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    (out / 'SHA256SUMS.txt').write_text(''.join(
        f'{sha256(p)}  {p.name}\n' for p in sorted(out.iterdir())), encoding='utf-8')
    print(f'Release attachments ready: {out}; final hashes refreshed. Nothing uploaded.')


if __name__ == '__main__':
    main()
