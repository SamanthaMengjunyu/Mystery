"""Native macOS app/DMG build entry; macOS execution is required for validation."""
import argparse
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import platform
from runpy import run_path
import shutil
import subprocess
import struct
import sys
import zipfile
import urllib.request

from source_bundle import write_source_zip

ROOT = Path(__file__).resolve().parent.parent
VERSION = run_path(str(ROOT / 'desktop/__init__.py'))['VERSION']
SWISS_URL = 'https://files.pythonhosted.org/packages/66/a6/db70d67a00dda42ebd033538c086879328f4c17f670eafe8aca2f11abfef/pyswisseph-2.10.3.2.tar.gz'
SWISS_HASH = 'c54c305e83dbd5d2b71e58d8a69d8ee41de24c4d3328ce09e2af860a3537624d'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--node', type=Path, default=Path(shutil.which('node') or 'node'))
    parser.add_argument('--node-license', type=Path, required=True, help='LICENSE from the exact Node distribution being bundled')
    parser.add_argument('--python-license', type=Path, required=True, help='License of the Python distribution being bundled')
    parser.add_argument('--bundle-id', required=True, help='Stable reverse-domain identifier controlled by the publisher')
    parser.add_argument('--format', choices=('dmg', 'pkg'), default='dmg', help='Installer format')
    parser.add_argument('--identity', help='Developer ID Application identity; omitted means ad-hoc development build')
    parser.add_argument('--swiss-source', type=Path, help='Use the supplied verified source tarball instead of downloading it')
    args = parser.parse_args()
    if sys.platform != 'darwin':
        raise SystemExit('Run this script on macOS, using native Python and Node for the target architecture.')
    arch = platform.machine()
    if arch not in {'arm64', 'x86_64'}:
        raise SystemExit(f'Unsupported architecture: {arch}')
    if not (ROOT / 'LICENSE').is_file():
        raise SystemExit('Confirm the project license and add LICENSE before building a distributable app.')
    node = args.node.resolve()
    if not node.is_file() or not args.node_license.is_file() or not args.python_license.is_file():
        raise SystemExit('Supply macOS Node and the matching Node/Python license files.')
    node_arch = subprocess.check_output([str(node), '-p', 'process.arch'], text=True).strip()
    if node_arch != {'arm64': 'arm64', 'x86_64': 'x64'}[arch]:
        raise SystemExit('Python and Node architectures must match; build arm64 and x86_64 separately.')
    work = ROOT / '.cache' / f'macos-{arch}'
    out = ROOT / 'output/macos' / arch
    for path in (work / 'runtime', work / 'sources', out):
        path.mkdir(parents=True, exist_ok=True)
    shutil.copy2(node, work / 'runtime/node')
    (work / 'runtime/node').chmod(0o755)
    notices = work / 'licenses'
    shutil.copytree(ROOT / 'licenses', notices, dirs_exist_ok=True)
    shutil.copy2(ROOT / 'LICENSE', notices / 'Mystery-LICENSE.txt')
    shutil.copy2(ROOT / 'COPYRIGHT', notices / 'Mystery-COPYRIGHT.txt')
    shutil.copy2(args.node_license, notices / 'Node-LICENSE.txt')
    shutil.copy2(args.python_license, notices / 'Python-LICENSE.txt')
    # Include every installed distribution's notices, including platform PyObjC dependencies.
    for dist in importlib.metadata.distributions():
        for file in dist.files or []:
            if any(word in file.name.lower() for word in ('license', 'copying', 'notice')):
                source = dist.locate_file(file)
                if source.is_file():
                    name = dist.metadata['Name'] + '-' + str(file).replace('/', '_').replace('\\', '_')
                    shutil.copy2(source, notices / name)
    swiss = work / 'sources/pyswisseph-2.10.3.2.tar.gz'
    if args.swiss_source:
        shutil.copy2(args.swiss_source, swiss)
    elif not swiss.exists():
        with urllib.request.urlopen(SWISS_URL, timeout=60) as response:
            swiss.write_bytes(response.read())
    if hashlib.sha256(swiss.read_bytes()).hexdigest() != SWISS_HASH:
        raise SystemExit('pyswisseph source SHA-256 mismatch')
    (work / 'sources/source-manifest.json').write_text(json.dumps({
        'pyswisseph': {'version': '2.10.3.2', 'url': SWISS_URL, 'sha256': SWISS_HASH}}, indent=2), encoding='utf-8')
    write_source_zip(ROOT, work / 'sources' / f'Mystery-{VERSION}-source.zip')
    iconset = work / 'Mystery.iconset'
    iconset.mkdir(exist_ok=True)
    for size in (16, 32, 128, 256, 512):
        for scale in (1, 2):
            suffix = '@2x' if scale == 2 else ''
            subprocess.run(['sips', '-z', str(size * scale), str(size * scale),
                            str(ROOT / 'desktop/web/assets/mystery-logo.png'), '--out',
                            str(iconset / f'icon_{size}x{size}{suffix}.png')], check=True, capture_output=True)
    # PNG-backed ICNS avoids iconutil failures on some macOS installations.
    chunks = []
    for kind, name in ((b'icp4', 'icon_16x16.png'), (b'icp5', 'icon_32x32.png'),
                       (b'icp6', 'icon_32x32@2x.png'), (b'ic07', 'icon_128x128.png'),
                       (b'ic08', 'icon_256x256.png'), (b'ic09', 'icon_512x512.png'),
                       (b'ic10', 'icon_512x512@2x.png')):
        png = (iconset / name).read_bytes()
        chunks.append(kind + struct.pack('>I', len(png) + 8) + png)
    payload = b''.join(chunks)
    (work / 'Mystery.icns').write_bytes(b'icns' + struct.pack('>I', len(payload) + 8) + payload)
    env = dict(os.environ, MYSTERY_MAC_ARCH=arch, MYSTERY_BUNDLE_ID=args.bundle_id,
               MYSTERY_CODESIGN_IDENTITY=args.identity or '')
    subprocess.run([sys.executable, '-m', 'PyInstaller', '--noconfirm', '--clean',
                    '--distpath', str(out), '--workpath', str(work / 'pyinstaller'),
                    str(ROOT / 'scripts/macos.spec')], check=True, cwd=ROOT, env=env)
    app = out / 'Mystery.app'
    subprocess.run(['codesign', '--verify', '--deep', '--strict', str(app)], check=True)
    report_path = work / 'self-test.json'
    subprocess.run([str(app / 'Contents/MacOS/Mystery'), '--self-test', str(report_path),
                    '--data-dir', str(work / 'self-test-data')], check=True, timeout=180)
    report = json.loads(report_path.read_text(encoding='utf-8'))
    if not report or not all(item.get('ok') is True for item in report.values()):
        raise SystemExit(f'Frozen algorithm self-test failed; inspect {report_path}')
    if args.format == 'pkg':
        dmg = out / f'Mystery-{VERSION}-macos-{arch}.pkg'
        subprocess.run(['pkgbuild', '--component', str(app), '--install-location',
                        '/Applications', '--identifier', args.bundle_id, '--version',
                        VERSION, str(dmg)], check=True)
    else:
        # A fresh staging directory avoids including obsolete files from earlier builds.
        import tempfile
        with tempfile.TemporaryDirectory(prefix='dmg-', dir=work) as temp:
            stage = Path(temp)
            shutil.copytree(app, stage / 'Mystery.app', symlinks=True)
            (stage / 'Applications').symlink_to('/Applications')
            shutil.copytree(work / 'licenses', stage / 'licenses')
            shutil.copytree(work / 'sources', stage / 'sources')
            shutil.copy2(ROOT / 'docs/MACOS_BUILD.md', stage / 'Mac使用与构建说明.md')
            dmg = out / f'Mystery-{VERSION}-macos-{arch}.dmg'
            subprocess.run(['hdiutil', 'create', '-volname', f'Mystery {VERSION}', '-srcfolder',
                            str(stage), '-ov', '-format', 'UDZO', str(dmg)], check=True)
    manifest = {'version': VERSION, 'platform': 'macOS', 'architecture': arch,
                'python': sys.version, 'node': subprocess.check_output([str(node), '--version'], text=True).strip(),
                'bundle_id': args.bundle_id, 'signing': 'Developer ID' if args.identity else 'ad-hoc development',
                'notarized': False, 'ui_verified': False, 'frozen_self_test': report,
                'filename': dmg.name, 'bytes': dmg.stat().st_size,
                'sha256': hashlib.sha256(dmg.read_bytes()).hexdigest()}
    (out / 'build-manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')
    (out / 'requirements-macos-resolved.txt').write_text(
        subprocess.check_output([sys.executable, '-m', 'pip', 'freeze'], text=True), encoding='utf-8')
    # Keep exact corresponding source and license attachments outside the DMG too.
    shutil.copytree(work / 'sources', out / 'sources', dirs_exist_ok=True)
    with zipfile.ZipFile(out / f'Mystery-{VERSION}-macos-{arch}-licenses.zip', 'w', zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(notices.rglob('*')):
            if path.is_file():
                archive.write(path, 'licenses/' + path.relative_to(notices).as_posix())
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
