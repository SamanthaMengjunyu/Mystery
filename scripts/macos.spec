# Build only through build_macos.py, on the target Mac architecture.
import os
from pathlib import Path
from runpy import run_path
from PyInstaller.utils.hooks import collect_data_files, collect_submodules, copy_metadata

root = Path(SPECPATH).parent
version = run_path(str(root / 'desktop/__init__.py'))['VERSION']
work = root / '.cache' / ('macos-' + os.environ['MYSTERY_MAC_ARCH'])
datas = [(str(root / 'desktop/web'), 'desktop/web'),
         (str(root / 'mystery/ziwei/bridge.cjs'), 'mystery/ziwei'),
         (str(root / 'mystery/ziwei/vendor'), 'mystery/ziwei/vendor'),
         (str(work / 'licenses'), 'licenses'),
         (str(work / 'sources'), 'sources')]
datas += collect_data_files('tzdata') + collect_data_files('tzfpy')
datas += collect_data_files('webview') + copy_metadata('lunar-python')
identity = os.environ.get('MYSTERY_CODESIGN_IDENTITY') or None
a = Analysis([str(root / 'run_desktop.py')], pathex=[str(root)],
             binaries=[(str(work / 'runtime/node'), 'runtime')], datas=datas,
             hiddenimports=collect_submodules('mystery') + ['webview.platforms.cocoa', 'tzfpy'],
             excludes=['tkinter', 'pytest', 'IPython', 'PyQt5', 'PyQt6', 'PySide6'])
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name='Mystery',
          console=False, target_arch=os.environ['MYSTERY_MAC_ARCH'],
          codesign_identity=identity,
          entitlements_file=str(root / 'scripts/macos-entitlements.plist') if identity else None)
coll = COLLECT(exe, a.binaries, a.datas, name='Mystery')
app = BUNDLE(coll, name='Mystery.app', icon=str(work / 'Mystery.icns'),
             bundle_identifier=os.environ['MYSTERY_BUNDLE_ID'],
             info_plist={'CFBundleShortVersionString': version,
                         'CFBundleVersion': version,
                         'NSHighResolutionCapable': True,
                         'NSLocationUsageDescription': '经你同意，仅在本机临时使用大致位置。',
                         'NSLocationWhenInUseUsageDescription': '经你同意，仅在本机临时使用大致位置。'})
