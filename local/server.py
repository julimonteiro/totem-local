"""Loopback-only TOTEM companion service."""
import json, mimetypes, os, secrets, threading, time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse
import build, devices, keymap
from telemetry import Monitor, decode_packet
ROOT=build.ROOT
PORT=8767
TOKEN=secrets.token_urlsafe(32)
KEYMAP=ROOT/'config/totem.keymap'
LOCK=threading.RLock()
OPERATION=threading.Lock()
MONITOR=Monitor()
INVENTORY=[]
BOOTS=[]
MAP_PATH=ROOT/'devices.json'
MAPPINGS=json.loads(MAP_PATH.read_text()) if MAP_PATH.exists() else {}
JOB={'active':False,'phase':'idle','message':'Pronto','log':[]}

def log(message):
    with LOCK:
        JOB['log']=(JOB['log']+[str(message)])[-180:]
        JOB['message']=str(message)

def phase(value,message):
    with LOCK: JOB.update(phase=value,message=message)
    log(message)

def refresh_devices():
    global INVENTORY,BOOTS
    inventory=devices.usb_inventory(); boots=devices.bootloaders(inventory)
    changed=False
    with LOCK:
        for side in ('left','right'):
            matches=[u for u in inventory if u['vendor']=='ZMK Project' and u['hid']==(side=='left')]
            if len(matches)==1:
                u=matches[0]; current=MAPPINGS.get(side,{})
                if current.get('app_serial') not in (None,u['serial']): continue
                new={**current,'app_serial':u['serial'],'location':u['location']}
                if current!=new: MAPPINGS[side]=new; changed=True
        if changed: MAP_PATH.write_text(json.dumps(MAPPINGS,indent=2))
        INVENTORY=inventory; BOOTS=boots
        ports={p:side for side,mapping in MAPPINGS.items() for u in inventory if u['serial']==mapping.get('app_serial') for p in u['ports']}
    MONITOR.set_ports(ports)

def device_loop():
    while True:
        try: refresh_devices()
        except Exception as exc:
            with MONITOR.lock: MONITOR.errors=(MONITOR.errors+[str(exc)])[-8:]
        time.sleep(2)

def enroll_at_known_port(side):
    with LOCK:
        mapping=MAPPINGS.get(side,{})
        if mapping.get('boot_serial'): return
        other='right' if side=='left' else 'left'
        matches=[b for b in BOOTS if b['location']==mapping.get('location') and b['serial']!=MAPPINGS.get(other,{}).get('boot_serial')]
        if len(matches)==1 and matches[0]['serial']:
            MAPPINGS[side]={**mapping,'boot_serial':matches[0]['serial']}
            MAP_PATH.write_text(json.dumps(MAPPINGS,indent=2))
            log('Bootloader identificado pela porta USB da metade '+side)

def flash(side):
    artifact,meta=build.artifact_for(side)
    label='esquerda' if side=='left' else 'direita'
    phase('waiting','Dê dois toques rápidos no RESET da metade '+label+'. Mantenha os cabos nas mesmas portas.')
    target=None; deadline=time.monotonic()+240
    while time.monotonic()<deadline:
        refresh_devices(); enroll_at_known_port(side)
        try:
            with LOCK: target=devices.select_target(side,BOOTS,MAPPINGS)
            break
        except ValueError: time.sleep(1)
    if target is None: raise ValueError('Tempo esgotado aguardando RESET. Clique em Carregar para tentar novamente.')
    refresh_devices()
    with LOCK: target=devices.select_target(side,BOOTS,MAPPINGS)
    phase('flashing','Gravando a metade '+label+'…')
    data=artifact.read_bytes(); devices.validate_uf2(data)
    attempt_started=time.time()
    try:
        with (Path(target['mount'])/'TOTEM.UF2').open('wb') as handle:
            handle.write(data); handle.flush(); os.fsync(handle.fileno())
    except OSError:
        log('Unidade desconectou durante a cópia; verificando o firmware.')
    phase('verifying','Aguardando reinício e confirmação da versão '+meta['build']+'…')
    deadline=time.monotonic()+35
    while time.monotonic()<deadline:
        refresh_devices(); state=MONITOR.snapshot()['sides'].get(side,{})
        if state.get('fresh') and state.get('seen',0)>=attempt_started and state.get('build')==meta['build']:
            phase('done','Metade '+label+' atualizada e confirmada: '+meta['build']+'.'); return
        time.sleep(1)
    raise RuntimeError('Cópia tentada, mas o firmware não confirmou a versão. Confira cabo e RESET.')

def load(side):
    try: build.artifact_for(side)
    except (OSError,ValueError,KeyError):
        phase('building','Compilando '+side+'…'); build.compile_firmware(side,log)
    flash(side)

def start_job(action,side):
    if action not in ('load','build') or side not in ('left','right'): raise ValueError('Operação inválida.')
    if not OPERATION.acquire(blocking=False): raise ValueError('Há uma operação em andamento.')
    with LOCK: JOB.update(active=True,phase='starting',message='Iniciando…',log=[])
    def worker():
        try:
            if action=='load': load(side)
            else:
                phase('building','Compilando…'); build.compile_firmware(side,log)
                phase('done','Firmware compilado. Pronto para carregar.')
        except Exception as exc: phase('error',str(exc))
        finally:
            with LOCK: JOB['active']=False
            OPERATION.release()
    threading.Thread(target=worker,daemon=True).start()

def snapshot():
    source=KEYMAP.read_bytes()
    runtime=None
    live=MONITOR.snapshot()
    firmware_id=live['sides'].get('left',{}).get('build','')
    if len(firmware_id)==8 and all(c in '0123456789abcdef' for c in firmware_id):
        history=ROOT/'artifacts/history'/(firmware_id+'-left.json')
        if history.exists(): runtime=json.loads(history.read_text()).get('layers')
    with LOCK:
        return {'runtime_build':firmware_id if runtime else None,'runtime_layers':runtime,'hash':keymap.digest(source),'layers':keymap.parse(source.decode()),'token':TOKEN,
            'devices':list(INVENTORY),'bootloaders':list(BOOTS),'mappings':dict(MAPPINGS),
            'job':dict(JOB),'telemetry':MONITOR.snapshot()}

def allowed_request(host,origin,token,expected_token):
    return host in {f'127.0.0.1:{PORT}',f'localhost:{PORT}'} and origin in (None,f'http://{host}') and secrets.compare_digest(token or '',expected_token)

class Handler(BaseHTTPRequestHandler):
    def log_message(self,*args): pass
    def reply(self,status,data,content_type='application/json'):
        body=json.dumps(data).encode() if content_type=='application/json' else data
        self.send_response(status)
        self.send_header('Content-Type',content_type+'; charset=utf-8')
        self.send_header('Cache-Control','no-store')
        self.send_header('X-Content-Type-Options','nosniff')
        self.send_header('Content-Security-Policy',"default-src 'self'; script-src 'self'; style-src 'self'; connect-src 'self'; img-src 'self' data:; frame-ancestors 'none'")
        self.send_header('Content-Length',str(len(body))); self.end_headers(); self.wfile.write(body)
    def do_GET(self):
        if self.headers.get('Host') not in (f'127.0.0.1:{PORT}',f'localhost:{PORT}'): return self.reply(403,{'error':'Host inválido.'})
        path=urlparse(self.path).path
        if path=='/api/events':
            self.send_response(200)
            self.send_header('Content-Type','text/event-stream')
            self.send_header('Cache-Control','no-store')
            self.send_header('Connection','keep-alive')
            self.end_headers()
            cursor=-1
            try:
                while True:
                    with MONITOR.condition:
                        if cursor==MONITOR.version: MONITOR.condition.wait(timeout=1)
                        payload=MONITOR.snapshot(); cursor=MONITOR.version
                    self.wfile.write(('data: '+json.dumps(payload)+'\n\n').encode())
                    self.wfile.flush()
            except (BrokenPipeError,ConnectionResetError,OSError): pass
            return
        if path=='/api/state':
            try: return self.reply(200,snapshot())
            except Exception as exc: return self.reply(500,{'error':str(exc)})
        if path=='/api/job':
            with LOCK: return self.reply(200,dict(JOB))
        names={'/':'index.html','/app.js':'app.js','/style.css':'style.css','/tutorial.js':'tutorial.js','/tutorial-core.js':'tutorial-core.js'}
        if path not in names: return self.reply(404,{'error':'Não encontrado.'})
        p=ROOT/'local/static'/names[path]
        self.reply(200,p.read_bytes(),mimetypes.guess_type(str(p))[0] or 'text/plain')
    def do_POST(self):
        if not allowed_request(self.headers.get('Host'),self.headers.get('Origin'),self.headers.get('X-Totem-Token'),TOKEN): return self.reply(403,{'error':'Requisição local não autorizada.'})
        try:
            size=int(self.headers.get('Content-Length','0'))
            if not 0<size<262144: raise ValueError('Requisição inválida.')
            body=json.loads(self.rfile.read(size)); path=urlparse(self.path).path
            if path=='/api/save':
                if not OPERATION.acquire(blocking=False): raise ValueError('Aguarde a compilação/gravação terminar.')
                try: result={'hash':keymap.save(KEYMAP,body['edits'],body['hash'])}
                finally: OPERATION.release()
            elif path in ('/api/load','/api/build'):
                start_job(path.rsplit('/',1)[1],body.get('side')); result={'started':True}
            elif path=='/api/bluetooth': MONITOR.connect_bluetooth(); result={'started':True}
            elif path=='/api/native':
                if 'status' in body:
                    if not isinstance(body['status'],str) or len(body['status'])>300: raise ValueError('Status inválido.')
                    MONITOR.ble_status=body['status']
                if 'packet' in body: MONITOR.receive(decode_packet(bytes(body['packet'])),'Bluetooth')
                if 'output' in body:
                    packet=bytes(body['output'])
                    if len(packet)!=8 or packet[0]!=1: raise ValueError('Saída inválida.')
                    MONITOR.receive({'side':'left','output':{'page':int.from_bytes(packet[1:3],'little'),'code':int.from_bytes(packet[3:5],'little'),'mods':packet[5],'pressed':bool(packet[6])}},'Bluetooth')
                result={'ok':True}
            else: return self.reply(404,{'error':'Operação desconhecida.'})
            self.reply(200,result)
        except (ValueError,KeyError,TypeError) as exc: self.reply(400,{'error':str(exc)})
        except Exception as exc: self.reply(500,{'error':str(exc)})

def main():
    refresh_devices(); threading.Thread(target=device_loop,daemon=True).start()
    print(f'TOTEM Local em http://127.0.0.1:{PORT}',flush=True)
    ThreadingHTTPServer(('127.0.0.1',PORT),Handler).serve_forever()
if __name__=='__main__': main()
