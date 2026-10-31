import struct
import unittest
import devices

def uf2():
    return struct.pack('<8I', 0x0A324655,0x9E5D5157,0x2000,0x27000,256,0,1,0xADA52840) + bytes(476) + struct.pack('<I',0x0AB16F30)

class DeviceTests(unittest.TestCase):
    def test_valid_uf2(self):
        devices.validate_uf2(uf2())
    def test_reject_invalid_family_and_incomplete_blocks(self):
        bad = bytearray(uf2()); bad[28:32] = struct.pack('<I', 123)
        for data in [b'', uf2()[:-1], bytes(bad), uf2()+uf2()]:
            with self.subTest(length=len(data)), self.assertRaises(ValueError):
                devices.validate_uf2(data)
    def test_never_guess_side(self):
        boots = [{'serial':'one','location':10,'mount':'/Volumes/XIAO'}]
        with self.assertRaises(ValueError):
            devices.select_target('left', boots, {})
        self.assertEqual(devices.select_target('left',boots,{'left':{'boot_serial':'one'}}),boots[0])
        with self.assertRaises(ValueError):
            devices.select_target('right',boots,{'left':{'boot_serial':'one'}})
    def test_ambiguous_serial_rejected(self):
        b={'serial':'same','location':1,'mount':'/Volumes/A'}
        with self.assertRaises(ValueError):
            devices.select_target('left',[b,b],{'left':{'boot_serial':'same'}})

if __name__ == '__main__': unittest.main()

class InventoryTests(unittest.TestCase):
    def test_hub_does_not_inherit_child_disk_or_hid(self):
        import plistlib
        from unittest.mock import patch
        child={'IOObjectClass':'IOUSBHostDevice','idVendor':1,'USB Serial Number':'board','locationID':2,'IORegistryEntryChildren':[{'BSD Name':'disk6','bInterfaceClass':3}]}
        hub={'idVendor':2,'USB Serial Number':'hub','locationID':1,'IORegistryEntryChildren':[child]}
        with patch('devices.command',return_value=plistlib.dumps([hub])):
            result=devices.usb_inventory()
        self.assertEqual(result[0]['disks'],[])
        self.assertFalse(result[0]['hid'])
        self.assertEqual(result[1]['disks'],['disk6'])
