"""Exercise the real installer in an isolated workspace directory and registration."""
import hashlib
import argparse
import json
from pathlib import Path
from runpy import run_path
import subprocess
import time
import winreg

ROOT = Path(__file__).resolve().parent.parent
VERSION = run_path(str(ROOT / 'desktop' / '__init__.py'))['VERSION']
OUT = ROOT / 'output' / 'release'
BASE = ROOT / '.cache' / f'installer-verify-{VERSION}'
TARGET = BASE / 'installed'
REGISTRATION = r'Software\Microsoft\Windows\CurrentVersion\Uninstall\{A596F34B-C8C2-42F4-870D-AFBE7432BFA5}-Verification_is1'


def run(args):
    subprocess.run([str(a) for a in args], check=True, timeout=90,
                   creationflags=subprocess.CREATE_NO_WINDOW, cwd=ROOT)


def main():
    global BASE, TARGET
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--work-dir', type=Path, default=BASE)
    args = parser.parse_args()
    BASE = args.work_dir.resolve()
    if not BASE.is_relative_to((ROOT / '.cache').resolve()):
        raise RuntimeError('Verification must stay inside the project .cache directory.')
    TARGET = BASE / 'installed'
    if TARGET.exists():
        raise RuntimeError('Verification directory already exists; inspect it before rerunning.')
    BASE.mkdir(parents=True, exist_ok=True)
    setup = OUT / f'Mystery-{VERSION}-setup.exe'
    expected = json.loads((OUT / 'build-manifest.json').read_text(encoding='utf-8'))['sha256']
    install_args = [setup, '/VERYSILENT', '/SUPPRESSMSGBOXES', '/NORESTART', '/SP-',
                    '/VERIFYINSTALL=1', f'/DIR={TARGET}', '/NOICONS', '/TASKS=']
    report = {'version': VERSION, 'ok': False, 'setup': setup.name,
              'setup_sha256': hashlib.sha256(setup.read_bytes()).hexdigest(),
              'installed_exe_sha256': expected}
    uninstaller = TARGET / 'unins000.exe'
    data = BASE / 'user-data'
    data.mkdir(exist_ok=True)
    sentinel = data / 'preserve-test.txt'
    sentinel.write_text('Personal data must survive install/upgrade/uninstall.', encoding='utf-8')
    try:
        run([*install_args, f'/LOG={BASE / "install.log"}'])
        app = TARGET / f'Mystery-{VERSION}.exe'
        assert hashlib.sha256(app.read_bytes()).hexdigest() == expected
        assert (TARGET / 'licenses' / 'Tarot-RWS-LICENSE.txt').is_file()
        assert (TARGET / 'sources' / f'Mystery-{VERSION}-source.zip').is_file()
        assert (TARGET / 'licenses' / 'Mystery-LICENSE.txt').read_bytes() == (ROOT / 'LICENSE').read_bytes()
        assert (TARGET / 'sources' / f'Mystery-{VERSION}-source.zip').read_bytes() == (OUT / 'sources' / f'Mystery-{VERSION}-source.zip').read_bytes()
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, REGISTRATION, 0, winreg.KEY_READ | winreg.KEY_WOW64_64KEY) as key:
            assert winreg.QueryValueEx(key, 'DisplayVersion')[0] == VERSION
        report['install_and_registered_version'] = True
        result = BASE / 'installed-self-test.json'
        run([app, '--self-test', result, '--data-dir', data])
        assert all(v['ok'] for v in json.loads(result.read_text(encoding='utf-8')).values())
        report['installed_exe_algorithms'] = True
        before = hashlib.sha256((data / 'records.sqlite3').read_bytes()).hexdigest()
        run([*install_args, f'/LOG={BASE / "upgrade.log"}'])
        assert hashlib.sha256(app.read_bytes()).hexdigest() == expected
        assert hashlib.sha256((data / 'records.sqlite3').read_bytes()).hexdigest() == before
        report['reinstall_preserves_records'] = True
        run([uninstaller, '/VERYSILENT', '/SUPPRESSMSGBOXES', '/NORESTART', f'/LOG={BASE / "uninstall.log"}'])
        for _ in range(75):
            if not app.exists():
                break
            time.sleep(.2)
        assert not app.exists()
        assert sentinel.read_text(encoding='utf-8') == 'Personal data must survive install/upgrade/uninstall.'
        assert hashlib.sha256((data / 'records.sqlite3').read_bytes()).hexdigest() == before
        report['uninstall_preserves_records'] = True
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, REGISTRATION):
                raise AssertionError('Verification uninstall registration was not removed')
        except FileNotFoundError:
            pass
        report['verification_registration_cleaned'] = True
        report['ok'] = True
    finally:
        if not report['ok'] and uninstaller.exists():
            run([uninstaller, '/VERYSILENT', '/SUPPRESSMSGBOXES', '/NORESTART'])
        (ROOT / '.cache' / 'installer-final-test.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
