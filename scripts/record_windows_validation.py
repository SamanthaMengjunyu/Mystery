"""Record current Windows validation evidence bound to the release file hashes."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from runpy import run_path

ROOT = Path(__file__).resolve().parent.parent
VERSION = run_path(str(ROOT / 'desktop/__init__.py'))['VERSION']


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--evidence-dir', type=Path, required=True)
    args = parser.parse_args()
    evidence = args.evidence_dir
    out = ROOT / 'output/release'
    build = read(out / 'build-manifest.json')
    installer = read(out / 'installer-manifest.json')
    lifecycle = read(ROOT / '.cache/installer-final-test.json')
    offline = read(ROOT / '.cache/unittest-final-summary.json')
    algorithms = read(evidence / 'frozen-self-test.json')
    browser = read(evidence / 'browser-ui.json')
    frontend = read(evidence / 'frontend-checks.json')
    assets = read(evidence / 'bundled-assets.json')
    assert build['version'] == installer['version'] == lifecycle['version'] == offline['version'] == VERSION
    assert sha256(out / build['filename']) == build['sha256'] == installer['installed_exe_sha256'] == lifecycle['installed_exe_sha256']
    assert sha256(out / installer['filename']) == installer['sha256'] == lifecycle['setup_sha256']
    assert offline['failed'] == 0 and offline['passed'] >= 128
    assert len(algorithms) == 14 and all(item['ok'] is True for item in algorithms.values())
    assert len(frontend) == 9 and all(item['ok'] is True for item in frontend)
    assert browser['version'] == VERSION and browser['sceneReady'] == 'true'
    assert browser['art'] == 'loaded' and browser['fallback'] is False and browser['overflow'] is False
    assert assets['ok'] and assets['palette_sha256'] == sha256(ROOT / 'desktop/web/palette.css')
    assert lifecycle['ok'] is True
    report = {'version': VERSION, 'ok': True, 'checked_at_utc': datetime.now(timezone.utc).isoformat(),
              'exe_sha256': build['sha256'], 'setup_sha256': installer['sha256'],
              'source_sha256': sha256(out / 'sources' / f'Mystery-{VERSION}-source.zip'),
              'offline_tests': offline, 'frozen_algorithms': {k: v['ok'] for k, v in algorithms.items()},
              'frontend_checks': frontend, 'bundled_assets': assets, 'browser_ui': browser,
              'ui_method': 'Background browser connected to frozen EXE loopback server',
              'native_webview_tested_this_build': False, 'installer_lifecycle': lifecycle,
              'macos_tested': False, 'windows_code_signed': False}
    (out / 'validation-windows.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print('Current Windows evidence validated and recorded with EXE/setup/source hashes.')


if __name__ == '__main__':
    main()
