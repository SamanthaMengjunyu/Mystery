"""Build the versioned, per-user Windows installer with the installed Inno compiler."""
import argparse
import hashlib
import json
import os
from pathlib import Path
from runpy import run_path
import shutil
import subprocess

ROOT = Path(__file__).resolve().parent.parent
VERSION = run_path(str(ROOT / 'desktop' / '__init__.py'))['VERSION']


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--compiler', type=Path)
    args = parser.parse_args()
    compiler = args.compiler or next((p for p in (
        Path(shutil.which('ISCC') or '__missing__'),
        Path(os.environ.get('ProgramFiles', 'C:/Program Files')) / 'Inno Setup 7/ISCC.exe',
        Path(os.environ.get('ProgramFiles(x86)', 'C:/Program Files (x86)')) / 'Inno Setup 6/ISCC.exe',
    ) if p.is_file()), None)
    if not compiler:
        raise SystemExit('Install Inno Setup from https://jrsoftware.org/isinfo.php or pass --compiler.')
    out = ROOT / 'output' / 'release'
    manifest = json.loads((out / 'build-manifest.json').read_text(encoding='utf-8'))
    app = out / f'Mystery-{VERSION}.exe'
    if manifest['version'] != VERSION or hashlib.sha256(app.read_bytes()).hexdigest() != manifest['sha256']:
        raise RuntimeError('Build and validate the current desktop EXE first.')
    if not (out / 'sources' / f'Mystery-{VERSION}-source.zip').is_file():
        raise RuntimeError('Run package_release.py before building the installer.')
    subprocess.run([str(compiler), f'/DAppVersion={VERSION}', f'/DSourceRoot={ROOT}',
                    str(ROOT / 'scripts' / 'installer.iss')], check=True, cwd=ROOT)
    setup = out / f'Mystery-{VERSION}-setup.exe'
    report = {'version': VERSION, 'filename': setup.name, 'bytes': setup.stat().st_size,
              'sha256': hashlib.sha256(setup.read_bytes()).hexdigest(),
              'installed_exe': app.name, 'installed_exe_sha256': manifest['sha256'],
              'scope': 'current user', 'data_preserved_on_uninstall': True}
    (out / 'installer-manifest.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
