import unittest
import telemetry

class TelemetryTests(unittest.TestCase):
    def test_decode_packet(self):
        packet=bytes([1,0,80,63,31,2,1])+int(1<<37 | 1).to_bytes(5,'little')+bytes.fromhex('12345678')
        d=telemetry.decode_packet(packet)
        self.assertEqual(d['battery'],80)
        self.assertEqual(d['peer_battery'],63)
        self.assertEqual(d['layer'],2)
        self.assertEqual(d['pressed'],(1<<37)|1)
        self.assertTrue(d['ble'])
        self.assertEqual(d['build'],'78563412')
    def test_reject_invalid_packet(self):
        for d in (b'', bytes(16),bytes([1,0,101,80,0,0,0])+bytes(9)):
            with self.assertRaises(ValueError): telemetry.decode_packet(d)

if __name__=='__main__': unittest.main()

class LiveFeedbackTests(unittest.TestCase):
    def test_events_wake_subscribers_and_expose_output(self):
        monitor=telemetry.Monitor()
        version=getattr(monitor,'version',0)
        monitor.receive({'side':'left','output':{'page':7,'code':6,'mods':8,'pressed':True}},'USB')
        self.assertGreater(getattr(monitor,'version',0),version)
        self.assertEqual(monitor.snapshot().get('produced',{}).get('label'),'⌘ C')
    def test_unknown_and_release_do_not_invent_output(self):
        monitor=telemetry.Monitor()
        monitor.receive({'side':'left','output':{'page':7,'code':4,'mods':0,'pressed':True}},'USB')
        monitor.receive({'side':'left','output':{'page':7,'code':4,'mods':0,'pressed':False}},'USB')
        self.assertEqual(monitor.snapshot().get('produced',{}).get('label'),'A')
