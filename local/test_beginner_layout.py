import unittest
from pathlib import Path
import keymap

class BeginnerLayoutTests(unittest.TestCase):
    def test_three_layers_and_no_letter_hold_taps(self):
        layers=keymap.parse((Path(__file__).parents[1]/'config/totem.keymap').read_text())
        self.assertEqual(len(layers),3)
        base=layers[0]['bindings']
        for letter in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ': self.assertIn('&kp '+letter,base)
        self.assertTrue(all(not x.startswith(('&mt','&lt')) for x in base))
        for binding in ('&kp LSHFT','&kp LGUI','&kp LCTRL','&kp SPACE','&kp ENTER','&kp BSPC','&mo 1'):
            self.assertIn(binding,base)
    def test_adjust_requires_navigation_then_escape(self):
        layers=keymap.parse((Path(__file__).parents[1]/'config/totem.keymap').read_text())
        self.assertIn('&mo 2',layers[1]['bindings'])
        self.assertFalse(any('BT_' in b for b in layers[0]['bindings']))

if __name__=='__main__': unittest.main()
