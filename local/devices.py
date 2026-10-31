"""USB inventory and conservative UF2 target selection for macOS."""
import plistlib
import struct
import subprocess
import time
from pathlib import Path


def command(args):
    for attempt in range(3):
        try: return subprocess.check_output(args, timeout=15)
        except subprocess.SubprocessError:
            if attempt == 2: raise
            time.sleep(0.2)


def walk(node):
    yield node
    for child in node.get('IORegistryEntryChildren', []):
        yield from walk(child)


def own_children(node):
    yield node
    for child in node.get('IORegistryEntryChildren', []):
        if child.get('IOObjectClass') != 'IOUSBHostDevice':
            yield from own_children(child)


def usb_inventory():
    roots = plistlib.loads(command(['/usr/sbin/ioreg', '-a', '-r', '-c', 'IOUSBHostDevice', '-l']))
    result = []
    seen = set()
    for root in roots:
        for node in walk(root):
            if 'idVendor' not in node or 'USB Serial Number' not in node:
                continue
            serial = node['USB Serial Number']
            identity = (serial, node.get('locationID'))
            if identity in seen:
                continue
            seen.add(identity)
            children = list(own_children(node))
            result.append({'serial': serial, 'location': node.get('locationID'),
                'vendor': node.get('USB Vendor Name', ''), 'product': node.get('USB Product Name', ''),
                'hid': any(n.get('bInterfaceClass') == 3 for n in children),
                'ports': [n['IOCalloutDevice'] for n in children if 'IOCalloutDevice' in n],
                'disks': [n['BSD Name'] for n in children if 'BSD Name' in n]})
    return result


def bootloaders(inventory):
    boots = []
    for mount in Path('/Volumes').iterdir():
        info = mount / 'INFO_UF2.TXT'
        if not info.is_file():
            continue
        try:
            text = info.read_text()
            normalized = text.lower().replace('_', '').replace(' ', '').replace('-', '')
            if 'xiao' not in normalized or 'nrf52840' not in normalized:
                continue
            disk = plistlib.loads(command(['/usr/sbin/diskutil', 'info', '-plist', str(mount)]))['DeviceIdentifier']
            candidates = [u for u in inventory if disk in u['disks']]
            if len(candidates) != 1 or not candidates[0]['serial']:
                continue
            boots.append({**candidates[0], 'mount': str(mount), 'info': text})
        except (OSError, ValueError, subprocess.SubprocessError):
            continue
    return boots


def select_target(side, boots, mappings):
    if side not in ('left', 'right'):
        raise ValueError('Metade inválida.')
    serial = mappings.get(side, {}).get('boot_serial')
    matches = [b for b in boots if serial and b['serial'] == serial]
    if len(matches) != 1:
        raise ValueError('Metade não identificada em modo de gravação. Acione RESET duas vezes na metade escolhida.')
    return matches[0]


def validate_uf2(data):
    if not data or len(data) % 512:
        raise ValueError('Firmware UF2 incompleto.')
    count = len(data) // 512
    indices = set()
    addresses = set()
    for offset in range(0, len(data), 512):
        m0, m1, flags, address, size, index, total, family = struct.unpack_from('<8I', data, offset)
        end = struct.unpack_from('<I', data, offset + 508)[0]
        if (m0, m1, end) != (0x0A324655, 0x9E5D5157, 0x0AB16F30) or not flags & 0x2000 or flags & 1:
            raise ValueError('UF2 inválido ou fora do formato esperado.')
        if family != 0xADA52840 or total != count or index >= count or index in indices:
            raise ValueError('UF2 não corresponde ao nRF52840 ou tem blocos inválidos.')
        if size != 256 or address % 256 or not 0x27000 <= address or address + size > 0xED000 or address in addresses:
            raise ValueError('UF2 fora da região de firmware esperada.')
        indices.add(index)
        addresses.add(address)
