"""HTTP integration uses an isolated workspace and no keyboard writes."""
import http.client,json,tempfile,threading,unittest
from pathlib import Path
from http.server import ThreadingHTTPServer
import server
from profiles import Store

class ProfileAPITest(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.root=Path(self.tmp.name); (self.root/'config').mkdir()
        self.source=(Path(__file__).parent/'fixtures/beginner.keymap').read_text()
        (self.root/'config/totem.keymap').write_text(self.source)
        self.previous=(server.PROFILES,server.KEYMAP,server.PORT)
        server.PROFILES=Store(self.root); server.KEYMAP=self.root/'config/totem.keymap'
        self.http=ThreadingHTTPServer(('127.0.0.1',0),server.Handler);server.PORT=self.http.server_port
        self.thread=threading.Thread(target=self.http.serve_forever,daemon=True);self.thread.start()
    def tearDown(self):
        self.http.shutdown();self.http.server_close();self.thread.join();server.PROFILES,server.KEYMAP,server.PORT=self.previous;self.tmp.cleanup()
    def call(self,action,body,token=None):
        connection=http.client.HTTPConnection('127.0.0.1',server.PORT)
        connection.request('POST','/api/profile/'+action,json.dumps(body),{'Content-Type':'application/json','X-Totem-Token':token if token is not None else server.TOKEN})
        response=connection.getresponse();result=(response.status,json.loads(response.read()));connection.close();return result
    def test_preview_apply_hash_and_backup(self):
        code,data=self.call('preview',{'template':'programming'});self.assertEqual(code,200)
        self.assertEqual(server.KEYMAP.read_text(),self.source)
        code,data=self.call('apply',{'source':data['source'],'hash':server.keymap.digest(self.source)})
        self.assertEqual(code,200);self.assertTrue(list((self.root/'config/backups').glob('*')))
        self.assertEqual(self.call('apply',{'source':self.source,'hash':server.keymap.digest(self.source)})[0],400)
    def test_authentication_busy_and_path_rejection(self):
        self.assertEqual(self.call('create',{'name':'safe'},token='wrong')[0],403)
        server.OPERATION.acquire()
        try:self.assertEqual(self.call('create',{'name':'safe'})[0],400)
        finally:server.OPERATION.release()
        self.assertEqual(self.call('export',{'id':'../config/totem'})[0],400)
    def test_full_source_roundtrip(self):
        source=self.source+'\n// preserve custom definitions\n'
        code,data=self.call('create',{'name':'Custom','source':source});self.assertEqual(code,200)
        code,data=self.call('export',{'id':data['id']});self.assertEqual(code,200);self.assertEqual(data['source'],source)
