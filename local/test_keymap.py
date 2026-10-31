import unittest
import tempfile
from pathlib import Path
import keymap

REAL = Path(__file__).parent / 'fixtures/original.keymap'

class KeymapTests(unittest.TestCase):
    def test_real_roundtrip_and_nested_binding(self):
        source = REAL.read_text()
        layers = keymap.parse(source)
        self.assertEqual(len(layers), 7)
        self.assertTrue(all(len(x['bindings']) == 38 for x in layers))
        self.assertEqual(keymap.update(source, []), source)
        changed = keymap.update(source, [{'layer': 0, 'position': 0, 'binding': '&kp LC(LS(A))'}])
        self.assertEqual(keymap.parse(changed)[0]['bindings'][0], '&kp LC(LS(A))')
        self.assertIn('hold-trigger-key-positions', changed)
        self.assertEqual(keymap.parse(changed)[1:], layers[1:])

    def test_reject_escape_and_multiple_bindings(self):
        for binding in ['&kp A>; }; evil { bindings = <&kp B', '&kp A &kp B', '&kp LC(A', '&kp A\n#include "bad"', '']:
            with self.subTest(binding=binding), self.assertRaises(ValueError):
                keymap.update(REAL.read_text(), [{'layer': 0, 'position': 0, 'binding': binding}])

    def test_comments_are_not_bindings(self):
        source = REAL.read_text().replace('&kp Q', '/* &kp BAD */ &kp Q', 1)
        self.assertEqual(len(keymap.parse(source)[0]['bindings']), 38)

    def test_save_rejects_stale_and_makes_backup(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / 'totem.keymap'
            p.write_bytes(REAL.read_bytes())
            old = p.read_bytes()
            with self.assertRaises(ValueError):
                keymap.save(p, [], 'wrong')
            self.assertEqual(p.read_bytes(), old)
            keymap.save(p, [{'layer': 0, 'position': 0, 'binding': '&kp B'}], keymap.digest(old))
            backups = list((p.parent / 'backups').glob('*.keymap'))
            self.assertEqual(len(backups), 1)
            self.assertEqual(backups[0].read_bytes(), old)
            self.assertEqual(keymap.parse(p.read_text())[0]['bindings'][0], '&kp B')

if __name__ == '__main__':
    unittest.main()
