"""Live data transport; key positions are held in memory only."""
import asyncio
import copy
import fcntl
import json
import os
import select
import struct
import termios
import threading
import time

SERVICE='5fbc1000-6c8d-4f43-a01a-a6d18a88c001'
CHARACTERISTIC='5fbc1001-6c8d-4f43-a01a-a6d18a88c001'
OUTPUT_CHARACTERISTIC='5fbc1002-6c8d-4f43-a01a-a6d18a88c001'


def output_label(output):
    page,code,mods=output.get('page'),output.get('code'),output.get('mods',0)
    if page==7:
        names={40:'↩',41:'⎋',42:'⌫',43:'⇥',44:'Espaço',45:'−',46:'=',47:'[',48:']',49:'\\',51:';',52:"'",53:'`',54:',',55:'.',56:'/',57:'Caps Lock',73:'Insert',74:'Home',75:'Page Up',76:'⌦',77:'End',78:'Page Down',79:'→',80:'←',81:'↓',82:'↑',224:'⌃',225:'⇧',226:'⌥',227:'⌘',228:'⌃',229:'⇧',230:'⌥',231:'⌘'}
        if 4<=code<=29: key=chr(65+code-4)
        elif 30<=code<=39: key=str((code-29)%10)
        elif 58<=code<=69: key='F'+str(code-57)
        else: key=names.get(code,f'Tecla HID {code}')
        if 224<=code<=231: return key
        prefix=''.join(symbol for bits,symbol in ((0x11,'⌃'),(0x22,'⇧'),(0x44,'⌥'),(0x88,'⌘')) if mods&bits)
        return (prefix+' '+key).strip()
    if page==12:
        return {0xE9:'Volume +',0xEA:'Volume −',0xE2:'Mudo',0xCD:'Reproduzir / pausar',0xB5:'Próxima faixa',0xB6:'Faixa anterior'}.get(code,f'Mídia HID {code}')
    return f'HID {page}:{code}'


def decode_packet(data):
    if len(data)!=16 or data[0]!=1 or data[1] not in (0,1) or any(x>100 and x!=255 for x in data[2:4]):
        raise ValueError('Pacote de telemetria inválido.')
    flags=data[4]
    return {'side':'left' if data[1]==0 else 'right','battery':-1 if data[2]==255 else data[2],
        'peer_battery':-1 if data[3]==255 else data[3], 'usb':bool(flags&1),'usb_hid':bool(flags&2),
        'ble':bool(flags&4),'split':bool(flags&8),'endpoint':1 if flags&16 else 0,
        'layer':-1 if data[5]==255 else data[5],'profile':-1 if data[6]==255 else data[6],
        'pressed':int.from_bytes(data[7:12],'little'),'build':f'{int.from_bytes(data[12:16],"little"):08x}'}


class Monitor:
    def __init__(self):
        self.lock=threading.RLock()
        self.condition=threading.Condition(self.lock)
        self.version=0
        self.produced={}
        self.sides={}
        self.keys=set()
        self.flashes={}
        self.readers={}
        self.ble_status='Desconectado'
        self.ble_thread=None
        self.last_key=0
        self.errors=[]
        self.ports={}
        self.ports_lock=threading.Lock()

    def receive(self, data, channel):
        side=data.get('side')
        if side not in ('left','right'): return
        now=time.time()
        with self.lock:
            if 'output' in data:
                output=data['output']
                if output.get('pressed'):
                    self.produced={**output,'label':output_label(output),'seen':now}
            elif 'battery' in data:
                previous=self.sides.get(side,{})
                # Prefer USB if it is live; Bluetooth remains a fallback.
                if channel=='Bluetooth' and previous.get('channel')=='USB' and now-previous.get('seen',0)<3: return
                self.sides[side]={**data,'seen':now,'channel':channel}
                if side=='left' or now-self.sides.get('left',{}).get('seen',0)>4:
                    mask=int(data.get('pressed',0))
                    self.keys={p for p in range(38) if mask&(1<<p)}
                if side=='left' and data.get('peer_battery',-1)>=0 and data.get('split'):
                    right=self.sides.get('right',{})
                    if now-right.get('seen',0)>3 or right.get('channel')=='Via esquerda':
                        self.sides['right']={**right,'battery':data['peer_battery'],'seen':now,'channel':'Via esquerda','split':True}
            elif 'position' in data:
                p=data['position']
                if type(p) is not int or not 0<=p<38: return
                if data.get('pressed'):
                    self.keys.add(p); self.flashes[p]=now
                else: self.keys.discard(p)
                self.last_key=now
            self.version+=1
            self.condition.notify_all()

    def snapshot(self):
        now=time.time()
        with self.lock:
            sides=copy.deepcopy(self.sides)
            for side,data in sides.items():
                data['fresh']=now-data.get('seen',0)<4
                data['age']=round(now-data.get('seen',now),1)
            fresh=any(d['fresh'] for d in sides.values())
            return {'sides':sides,'pressed':sorted(self.keys) if fresh else [],'produced':dict(self.produced),'version':self.version,
                'flashes':[p for p,t in self.flashes.items() if now-t<0.2],
                'ble_status':self.ble_status,'errors':self.errors[-8:]}

    def set_ports(self, ports):
        with self.ports_lock:
            self.ports=dict(ports)
        for port,side in ports.items():
            if port not in self.readers or not self.readers[port].is_alive():
                thread=threading.Thread(target=self.read_serial,args=(port,side),daemon=True)
                self.readers[port]=thread; thread.start()

    def read_serial(self, port, side):
        fd=None
        try:
            fd=os.open(port,os.O_RDWR|os.O_NOCTTY|os.O_NONBLOCK)
            attrs=termios.tcgetattr(fd)
            attrs[0]=0; attrs[1]=0; attrs[2]=termios.CS8|termios.CREAD|termios.CLOCAL; attrs[3]=0
            attrs[4]=attrs[5]=termios.B115200; attrs[6][termios.VMIN]=0; attrs[6][termios.VTIME]=0
            termios.tcsetattr(fd,termios.TCSANOW,attrs)
            fcntl.ioctl(fd,termios.TIOCMBIS,struct.pack('I',termios.TIOCM_DTR))
            buffer=b''
            while True:
                with self.ports_lock:
                    if port not in self.ports: break
                if not select.select([fd],[],[],1)[0]: continue
                chunk=os.read(fd,4096)
                if not chunk: break
                buffer=(buffer+chunk)[-32768:]
                while b'\n' in buffer:
                    line,buffer=buffer.split(b'\n',1)
                    text=line.decode(errors='replace')
                    for marker in ('TOTEM_STATE ','TOTEM_KEY ','TOTEM_OUTPUT '):
                        if marker not in text: continue
                        try:
                            data=json.loads(text.split(marker,1)[1]); self.receive(data,'USB')
                        except (ValueError,TypeError): pass
        except (OSError,termios.error) as exc:
            with self.lock: self.errors.append(f'{side}: {exc}')
        finally:
            if fd is not None: os.close(fd)

    def connect_bluetooth(self):
        if self.ble_thread and self.ble_thread.is_alive(): return
        self.ble_thread=threading.Thread(target=lambda:asyncio.run(self._bluetooth()),daemon=True)
        self.ble_thread.start()

    async def _bluetooth(self):
        try:
            from bleak import BleakClient,BleakScanner
            self.ble_status='Procurando TOTEM…'
            candidates=await BleakScanner.discover(timeout=7)
            candidates=[d for d in candidates if d.name and 'TOTEM' in d.name.upper()]
            if not candidates: raise RuntimeError('TOTEM não encontrado. Confira o pareamento e o perfil ativo.')
            if len(candidates)!=1: raise RuntimeError('Mais de um TOTEM encontrado; deixe somente o seu acessível.')
            async with BleakClient(candidates[0],timeout=15) as client:
                def receive(_,data):
                    try: self.receive(decode_packet(bytes(data)),'Bluetooth')
                    except ValueError: pass
                await client.start_notify(CHARACTERISTIC,receive)
                def receive_output(_,data):
                    if len(data)==8 and data[0]==1:
                        self.receive({'side':'left','output':{'page':int.from_bytes(data[1:3],'little'),'code':int.from_bytes(data[3:5],'little'),'mods':data[5],'pressed':bool(data[6])}},'Bluetooth')
                try: await client.start_notify(OUTPUT_CHARACTERISTIC,receive_output)
                except Exception: pass
                receive(None,await client.read_gatt_char(CHARACTERISTIC))
                self.ble_status='Conectado'
                while client.is_connected: await asyncio.sleep(1)
            self.ble_status='Desconectado'
        except Exception as exc:
            self.ble_status='Falha: '+str(exc)
