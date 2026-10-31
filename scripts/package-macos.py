#!/usr/bin/env python3
"""Build a self-contained universal macOS app; toolchain runs locally."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile

ROOT=Path(__file__).resolve().parents[1]
CACHE=ROOT/'.package-cache'
DIST=ROOT/'dist'
PYTHON_VERSION='3.13.18'
PYTHON_RELEASE='20261026'
PYTHONS={
    'arm64':('aarch64','8392b6ea51d94391befb2c31ebe75463f045d0b69dfcf5e1bb3234e1f5fa3405'),
    'x86_64':('x86_64','7412c19d896c99431b74a18a5643e110449a7f9590fbab179c3e5ab27b9aa9e3'),
}
sys.path.insert(0,str(ROOT/'local'))
import build


def run(*args):
    subprocess.run([str(a) for a in args],check=True)


def main():
    CACHE.mkdir(exist_ok=True); DIST.mkdir(exist_ok=True)
    app=DIST/'TOTEM Local.app'
    if app.exists(): shutil.rmtree(app)
    contents=app/'Contents'; binaries=contents/'MacOS'; resources=contents/'Resources'
    binaries.mkdir(parents=True); resources.mkdir()
    shutil.copy2(ROOT/'native/Info.plist',contents/'Info.plist')
    shutil.copy2(ROOT/'native/assets/AppIcon.icns',resources/'AppIcon.icns')
    built=[]
    for arch,(python_arch,checksum) in PYTHONS.items():
        name=f'cpython-{PYTHON_VERSION}+{PYTHON_RELEASE}-{python_arch}-apple-darwin-install_only_stripped.tar.gz'
        archive=CACHE/name
        if not archive.exists():
            run('gh','release','download',PYTHON_RELEASE,'--repo','astral-sh/python-build-standalone','--pattern',name,'--dir',CACHE)
        if hashlib.sha256(archive.read_bytes()).hexdigest()!=checksum: raise RuntimeError('Python runtime checksum mismatch')
        target=resources/('Python-'+arch); target.mkdir()
        with tarfile.open(archive) as tar:
            # Archives are hash-pinned upstream binaries; reject path escapes as well.
            for member in tar.getmembers():
                if not (target/member.name).resolve().is_relative_to(target.resolve()): raise ValueError('Unsafe archive path')
            tar.extractall(target,filter='data')
        output=CACHE/('TotemLocal-'+arch)
        run('xcrun','swiftc','-target',arch+'-apple-macosx13.0',ROOT/'native/TotemApp.swift',ROOT/'native/NativeMonitor.swift','-o',output,'-framework','Cocoa','-framework','WebKit','-framework','SwiftUI','-framework','CoreBluetooth')
        built.append(output)
    run('lipo','-create',*built,'-output',binaries/'TotemLocal')
    workspace=resources/'Workspace'; workspace.mkdir()
    shutil.copytree(ROOT/'config',workspace/'config',ignore=shutil.ignore_patterns('backups','*.tmp'))
    shutil.copytree(ROOT/'telemetry',workspace/'telemetry')
    local=workspace/'local'; local.mkdir()
    for name in ('server.py','build.py','devices.py','keymap.py','telemetry.py'):
        shutil.copy2(ROOT/'local'/name,local/name)
    shutil.copytree(ROOT/'local/static',local/'static')
    artifacts=workspace/'artifacts'; (artifacts/'history').mkdir(parents=True)
    for side in ('left','right'):
        path,metadata=build.artifact_for(side)
        shutil.copy2(path,artifacts/path.name)
        shutil.copy2(path.with_suffix('.json'),artifacts/path.with_suffix('.json').name)
        (artifacts/'history'/(metadata['build']+'-'+side+'.json')).write_text(json.dumps(metadata,indent=2))
    for name in ('LICENSE','THIRD_PARTY.md'):
        shutil.copy2(ROOT/name,resources/name)
    run('codesign','--force','--deep','--sign','-',app)
    run('codesign','--verify','--deep','--strict',app)
    zip_path=DIST/'TOTEM-Local-macOS-universal.zip'
    if zip_path.exists(): zip_path.unlink()
    run('ditto','-c','-k','--keepParent','--norsrc',app,zip_path)
    checksum=hashlib.sha256(zip_path.read_bytes()).hexdigest()
    (DIST/'SHA256SUMS.txt').write_text(checksum+'  '+zip_path.name+'\n')
    print('Created '+str(zip_path))

if __name__=='__main__': main()
