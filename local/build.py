"""Reproducible local builds using an isolated Docker volume."""
import hashlib
import json
import shutil
import subprocess
import time
import uuid
from pathlib import Path
import devices
import keymap

ROOT=Path(__file__).resolve().parents[1]
CONTAINER='totem-local-builder'
IMAGE='zmkfirmware/zmk-build-arm@sha256:edb1c953438c6f720ddb79c3762f3972013b7fbbaf4fff3592fc869983e7afc5'
REVISION='7823a43f627e5a14fc92238783480d52ae5ed1ce'


def source_hash(root=ROOT):
    h=hashlib.sha256((REVISION+IMAGE).encode())
    for folder in ('config','telemetry'):
        for path in sorted((root/folder).rglob('*')):
            if not path.is_file() or 'backups' in path.parts or path.name=='build_id.h' or path.suffix=='.tmp': continue
            h.update(str(path.relative_to(root)).encode())
            h.update(b'\0'+path.read_bytes()+b'\0')
    return h.hexdigest()


def run(args, log=print):
    process=subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    for line in process.stdout:
        log(line.rstrip())
    if process.wait(): raise RuntimeError('Falha no comando: '+ ' '.join(args[:5]))


def ensure_builder(log):
    p=subprocess.run(['docker','inspect','--format','{{.State.Running}}',CONTAINER],capture_output=True,text=True)
    if p.returncode:
        run(['docker','volume','create','totem-local-workspace'],log)
        run(['docker','run','-d','--name',CONTAINER,'-v','totem-local-workspace:/work','-w','/work',IMAGE,'sleep','infinity'],log)
    elif p.stdout.strip()!='true': run(['docker','start',CONTAINER],log)
    return subprocess.run(['docker','exec',CONTAINER,'test','-f','/work/.totem-toolchain-ready'],capture_output=True).returncode==0


def compile_firmware(side, log=print):
    if side not in ('left','right'): raise ValueError('Metade inválida.')
    ready=ensure_builder(log)
    stage=ROOT/'.build-snapshots'/uuid.uuid4().hex
    stage.mkdir(parents=True)
    for folder in ('config','telemetry'):
        shutil.copytree(ROOT/folder,stage/folder,ignore=shutil.ignore_patterns('backups','*.tmp'))
    fingerprint=source_hash(stage)
    build_id=fingerprint[:8]
    (stage/'telemetry/build_id.h').write_text(f'#define TOTEM_BUILD_ID "{build_id}"\n#define TOTEM_BUILD_NUMBER 0x{build_id}U\n')
    log('Versão: '+build_id)
    run(['docker','exec',CONTAINER,'rm','-rf','/work/config','/work/telemetry'],log)
    for folder in ('config','telemetry'):
        run(['docker','cp',str(stage/folder),CONTAINER+':/work/'+folder],log)
    if not ready:
        # Initial acquisition requires internet; future builds use this volume offline.
        run(['docker','exec',CONTAINER,'sh','-c','test -d .west || west init -l config; west update --narrow -o=--depth=1 && west zephyr-export && touch /work/.totem-toolchain-ready'],log)
    run(['docker','exec',CONTAINER,'west','build','-s','zmk/app','-d','/work/build-'+side,'-b','seeeduino_xiao_ble','-S','zmk-usb-logging','--','-DSHIELD=totem_'+side,'-DZMK_CONFIG=/work/config','-DZMK_EXTRA_MODULES=/work/telemetry'],log)
    artifacts=ROOT/'artifacts'; artifacts.mkdir(exist_ok=True)
    temp=artifacts/('totem-'+side+'.uf2.tmp')
    run(['docker','cp',CONTAINER+':/work/build-'+side+'/zephyr/zmk.uf2',str(temp)],log)
    data=temp.read_bytes(); devices.validate_uf2(data)
    artifact=artifacts/('totem-'+side+'.uf2'); temp.replace(artifact)
    metadata={'side':side,'source_hash':fingerprint,'build':build_id,'sha256':hashlib.sha256(data).hexdigest(),'created':time.time(),'layers':keymap.parse((stage/'config/totem.keymap').read_text())}
    artifact.with_suffix('.json').write_text(json.dumps(metadata,indent=2))
    history=artifacts/'history'; history.mkdir(exist_ok=True)
    (history/(build_id+'-'+side+'.json')).write_text(json.dumps(metadata,indent=2))
    log('Compilação concluída: '+artifact.name)
    return metadata


def artifact_for(side):
    if side not in ('left','right'): raise ValueError('Metade inválida.')
    path=ROOT/'artifacts'/('totem-'+side+'.uf2')
    meta=json.loads(path.with_suffix('.json').read_text())
    data=path.read_bytes()
    if meta['side']!=side or meta['source_hash']!=source_hash() or meta['sha256']!=hashlib.sha256(data).hexdigest():
        raise ValueError('Firmware desatualizado. Compile novamente antes de gravar.')
    devices.validate_uf2(data)
    return path,meta

if __name__=='__main__':
    import sys
    compile_firmware(sys.argv[1])
