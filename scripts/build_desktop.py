"""Build a self-contained Windows executable from a clean desktop virtualenv."""
import argparse
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import shutil
import struct
import subprocess
import sys
from runpy import run_path
import zlib

ROOT = Path(__file__).resolve().parent.parent
VERSION = run_path(str(ROOT / 'desktop' / '__init__.py'))['VERSION']


def make_icon(path):
    # Prepared multi-resolution ICO; all sizes preserve the source aspect ratio.
    shutil.copy2(ROOT / 'desktop/web/assets/mystery-logo.ico', path)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--node', type=Path, default=Path(shutil.which('node') or 'node.exe'))
    parser.add_argument('--reuse-build', action='store_true', help='Reuse analysis cache after an interrupted build')
    args = parser.parse_args()
    if os.name != 'nt': raise SystemExit('Windows executable must be built on Windows')
    if not args.node.is_file(): raise SystemExit('Node.js executable was not found')
    work = ROOT / '.cache' / 'desktop-build'
    runtime = work / 'runtime'
    notices = work / 'licenses'
    runtime.mkdir(parents=True, exist_ok=True)
    notices.mkdir(exist_ok=True)
    shutil.copytree(ROOT / 'desktop' / 'licenses', notices, dirs_exist_ok=True)
    shutil.copytree(ROOT / 'licenses', notices, dirs_exist_ok=True)
    if (ROOT / 'LICENSE').is_file():
        shutil.copy2(ROOT / 'LICENSE', notices / 'Mystery-LICENSE.txt')
    if (ROOT / 'COPYRIGHT').is_file():
        shutil.copy2(ROOT / 'COPYRIGHT', notices / 'Mystery-COPYRIGHT.txt')
    shutil.copy2(args.node, runtime / 'node.exe')
    node_license = args.node.parent / 'LICENSE'
    if node_license.exists(): shutil.copy2(node_license, notices / 'Node-LICENSE.txt')
    for package in ('pywebview','pythonnet','clr_loader','pyswisseph','lunar-python','tzdata','cffi','tzfpy'):
        dist = importlib.metadata.distribution(package)
        for file in dist.files or []:
            if any(k in file.name.lower() for k in ('license','copying','notice')) and dist.locate_file(file).is_file():
                shutil.copy2(dist.locate_file(file), notices / (package + '-' + file.name))
    icon = work / 'Mystery.ico'
    make_icon(icon)
    version = work / 'version.txt'
    version_tuple = tuple(map(int, VERSION.split('.'))) + (0,)
    version.write_text(f"VSVersionInfo(ffi=FixedFileInfo(filevers={version_tuple},prodvers={version_tuple},mask=0x3f,flags=0,OS=0x40004,fileType=0x1,subtype=0,date=(0,0)),kids=[StringFileInfo([StringTable('040904B0',[StringStruct('CompanyName','Mystery'),StringStruct('FileDescription','Mystery Desktop'),StringStruct('FileVersion','{VERSION}'),StringStruct('InternalName','Mystery'),StringStruct('ProductName','Mystery'),StringStruct('ProductVersion','{VERSION}')])]),VarFileInfo([VarStruct('Translation',[1033,1200])])])",encoding='utf-8')
    cmd = [sys.executable,'-m','PyInstaller','--noconfirm',*([] if args.reuse_build else ['--clean']),'--onefile','--windowed','--name','Mystery',
           '--distpath',str(ROOT/'output'/'release'),'--workpath',str(work/'pyinstaller'),'--specpath',str(work),
           '--paths',str(ROOT),'--icon',str(icon),'--version-file',str(version),
           '--collect-submodules','mystery','--collect-data','mystery',
           '--collect-data','tzfpy','--hidden-import','tzfpy',
           '--collect-data','tzdata','--copy-metadata','lunar-python',
           '--add-data',str(ROOT/'desktop'/'web')+';desktop/web',
           '--add-data',str(ROOT/'mystery'/'ziwei'/'vendor')+';mystery/ziwei/vendor',
           '--add-data',str(ROOT/'mystery'/'ziwei'/'bridge.cjs')+';mystery/ziwei',
           '--add-data',str(notices)+';licenses','--add-binary',str(runtime/'node.exe')+';runtime',
           '--exclude-module','tkinter','--exclude-module','pytest','--exclude-module','IPython',
           str(ROOT/'run_desktop.py')]
    subprocess.run(cmd,cwd=ROOT,check=True)
    exe = ROOT/'output'/'release'/'Mystery.exe'
    versioned = exe.with_name(f'Mystery-{VERSION}.exe')
    shutil.copy2(exe, versioned)
    manifest = {'product':'Mystery','version':VERSION,'platform':'Windows x64','python':sys.version,
                'filename':versioned.name,
                'node':subprocess.check_output([str(args.node),'--version'],text=True).strip(),
                'sha256':hashlib.sha256(exe.read_bytes()).hexdigest(),'bytes':exe.stat().st_size,
                'dependencies':{p:importlib.metadata.version(p) for p in ('pywebview','pyinstaller','lunar-python','pyswisseph','tzdata','tzfpy')}}
    (exe.parent/'build-manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    shutil.copytree(notices,exe.parent/'licenses',dirs_exist_ok=True)
    print(json.dumps(manifest,indent=2))


if __name__ == '__main__': main()
