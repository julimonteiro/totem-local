import tempfile, unittest
from pathlib import Path
import keymap
try:
    from profiles import Store
except ImportError:
    Store = None

class ProfilesTest(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.root=Path(self.tmp.name)
        (self.root/'config').mkdir(); self.source=(Path(__file__).parent.parent/'config/totem.keymap').read_text()
        (self.root/'config/totem.keymap').write_text(self.source)
    def tearDown(self): self.tmp.cleanup()
    def store(self):
        self.assertIsNotNone(Store, 'Profile store is missing')
        return Store(self.root)
    def test_preserves_complete_source_and_validates_ids(self):
        store=self.store(); p=store.create('Meu mapa',self.source)
        self.assertEqual(store.read(p['id'])['source'],self.source)
        with self.assertRaises(ValueError): store.read('../config/totem')
        store.rename(p['id'],'Outro nome'); self.assertEqual(store.list()[0]['name'],'Outro nome')
        store.delete(p['id']); self.assertEqual(store.list(),[])
        self.assertEqual((self.root/'config/totem.keymap').read_text(),self.source)
    def test_replace_has_backup_and_compare_and_swap(self):
        self.store(); path=self.root/'config/totem.keymap'; replacement=self.source.replace('&kp Q','&kp F1',1)
        keymap.replace(path,replacement,keymap.digest(self.source))
        self.assertEqual(next((path.parent/'backups').glob('*')).read_text(),self.source)
        with self.assertRaises(ValueError): keymap.replace(path,self.source,keymap.digest(self.source))
    def test_templates_and_invalid_source(self):
        store=self.store()
        for name in ('beginner','programming'): self.assertEqual(len(keymap.parse(store.template(name))),3)
        with self.assertRaises(ValueError): store.create('Ruim','not a keymap')
        with self.assertRaises(ValueError): store.create('',self.source)
