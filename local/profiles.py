"""Named full-source keymaps; filenames are generated locally, never supplied paths."""
import json, os, re, uuid
from datetime import datetime, timezone
from pathlib import Path
import keymap

class Store:
    def __init__(self,root):
        self.root=Path(root); self.directory=self.root/'profiles'
    def path(self,identity):
        if not isinstance(identity,str) or not re.fullmatch(r'[a-f0-9]{32}',identity): raise ValueError('Perfil inválido.')
        return self.directory/(identity+'.json')
    def validate(self,source):
        if not isinstance(source,str) or len(source.encode())>200000: raise ValueError('Keymap inválido ou muito grande.')
        layers=keymap.parse(source)
        for layer in layers:
            for binding in layer['bindings']: keymap.validate(binding)
        return layers
    def name(self,name):
        if not isinstance(name,str) or not name.strip() or len(name)>80: raise ValueError('Use um nome de até 80 caracteres.')
        return name.strip()
    def write(self,data):
        self.directory.mkdir(exist_ok=True)
        path=self.path(data['id']); tmp=path.with_suffix('.tmp')
        tmp.write_text(json.dumps(data,ensure_ascii=False)); os.replace(tmp,path)
    def create(self,name,source):
        self.validate(source)
        data={'id':uuid.uuid4().hex,'name':self.name(name),'created':datetime.now(timezone.utc).isoformat(),'source':source}
        self.write(data); return {k:v for k,v in data.items() if k!='source'}
    def read(self,identity):
        data=json.loads(self.path(identity).read_text()); self.validate(data['source']); return data
    def list(self):
        result=[]
        for path in sorted(self.directory.glob('*.json')):
            try: result.append({k:v for k,v in self.read(path.stem).items() if k!='source'})
            except (ValueError,OSError,KeyError): continue
        return sorted(result,key=lambda x:x['created'],reverse=True)
    def rename(self,identity,name):
        data=self.read(identity); data['name']=self.name(name); self.write(data)
    def delete(self,identity): self.path(identity).unlink()
    def template(self,name):
        if name not in ('beginner','programming'): raise ValueError('Modelo desconhecido.')
        source=(Path(__file__).parent/'fixtures/beginner.keymap').read_text()
        if name=='programming':
            symbols=['LBRC','RBRC','LPAR','RPAR','LBKT','RBKT','LT','GT','BSLH','GRAVE']
            source=keymap.update(source,[{'layer':1,'position':i+10,'binding':'&kp '+code} for i,code in enumerate(symbols)])
        return source
    def backup(self,identity):
        if not isinstance(identity,str) or not re.fullmatch(r'\d{8}-\d{6}-\d{6}\.keymap',identity): raise ValueError('Backup inválido.')
        source=(self.root/'config/backups'/identity).read_text(); self.validate(source); return source
    def backups(self):
        return sorted([p.name for p in (self.root/'config/backups').glob('*.keymap') if re.fullmatch(r'\d{8}-\d{6}-\d{6}\.keymap',p.name)],reverse=True)
