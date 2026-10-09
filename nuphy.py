"""Air75 V3 ANSI S4 sidelight control. No firmware or keymap commands."""
import json
import fcntl
import secrets
import time
from pathlib import Path

import hid
from preferences import EFFECTS

VID, PID = 0x19F5, 0x1028


class ProtocolError(RuntimeError):
    pass


def side_settings(color, effect):
    if effect not in EFFECTS or effect == 'system':
        raise ValueError('Unsupported sidelight effect')
    return bytes([EFFECTS[effect], 80, 2, int(effect == 'neon'), 0, *color])


def frame(command, length, address=0, key=0, payload=b""):
    if not 0 <= length <= 56 or len(payload) > 56:
        raise ValueError("Invalid report length")
    out = bytearray(64)
    out[:2] = bytes([0x55, command])
    out[4:8] = bytes(x ^ key for x in (length, address & 255, address >> 8, 0))
    out[8:8 + len(payload)] = bytes(x ^ key for x in payload)
    out[3] = sum(out[4:]) & 255
    return out


def decode(raw, command, length, address, key):
    if len(raw) != 64 or raw[:2] != bytes([0xAA, command]):
        raise ProtocolError("Invalid response frame")
    if raw[3] != sum(raw[4:]) & 255:
        raise ProtocolError("Response checksum mismatch")
    if raw[2] != 0:
        raise ProtocolError(f"Device rejected 0x{command:02x}: status 0x{raw[2]:02x}")
    route = bytes([length, address & 255, address >> 8, 0])
    if raw[4:8] not in (route, bytes(x ^ key for x in route)):
        raise ProtocolError("Response route mismatch")
    return bytes(x ^ key for x in raw[8:8 + length])


def validate_state(state):
    if (len(state) != 17 or state[0] > 21 or state[1] > 100
            or state[3] > 1 or state[4] > 1 or state[9] > 4 or state[12] > 1):
        raise ProtocolError("Unknown lighting state; refusing to write")
    return state


class Keyboard:
    def __init__(self):
        devices = [d for d in hid.enumerate(VID, PID)
                   if d['usage_page'] == 1 and d['usage'] == 0]
        if len(devices) != 1:
            raise ProtocolError("Connect exactly one Air75 V3 ANSI by USB in wired mode")
        lock_path = Path(__file__).parent / 'runtime/hardware.lock'
        lock_path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.lock = lock_path.open('a+')
        try:
            fcntl.flock(self.lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            self.lock.close()
            raise ProtocolError("Another bridge process is using the keyboard") from None
        self.device = hid.device()
        try:
            self.device.open_path(devices[0]['path'])
            self.firmware = self.read(0xA1, 8)
            if self.firmware[3] != 0xAA or self.read(0xD1, 1) != b'\x68':
                raise ProtocolError("Device identity/LED count did not match Air75 V3 ANSI")
            self.state()
        except BaseException:
            self.close()
            raise

    def close(self):
        self.device.close()
        self.lock.close()

    def _exchange(self, packet):
        result = self.device.write(b'\x00' + packet)
        if result not in (64, 65):
            raise ProtocolError("HID write failed")
        deadline = time.monotonic() + 1.5
        while time.monotonic() < deadline:
            response = bytes(self.device.read(64, 100))
            if response[:2] == bytes([0xAA, packet[1]]):
                return response
        raise ProtocolError("Keyboard response timed out")

    def _transaction(self, command, length, address=0, payload=b''):
        # Fresh session per logical transaction; do not assume a previous client's key.
        hello = bytearray(64)
        hello[:2] = b'\x55\xee'
        hello[8:] = secrets.token_bytes(56)
        key = hello[28] or 0xAA
        hello[28] = key
        hello[3] = sum(hello[4:]) & 255
        response = self._exchange(hello)
        if (len(response) != 64 or response[2] != 0
                or response[3] != sum(response[4:]) & 255):
            raise ProtocolError("Session handshake rejected")
        response = self._exchange(frame(command, length, address, key, payload))
        return decode(response, command, length, address, key)

    def read(self, command, length, address=0):
        if command not in (0xA1, 0xD1, 0xD2, 0xD5):
            raise ValueError("Command not allowed")
        return self._transaction(command, length, address)

    def state(self):
        return validate_state(self.read(0xD5, 17))

    def write_state(self, state):
        validate_state(state)
        if self._transaction(0xD6, 17, payload=state) != state:
            raise ProtocolError("Lighting acknowledgement mismatch")
        # Acknowledgement alone does not prove that a write took effect.
        for _ in range(5):
            time.sleep(0.15)
            if self.state() == state:
                return
        raise ProtocolError("Lighting readback mismatch; restoration required")

    def side_colors(self):
        return self.read(0xD2, 30, 84 * 3) + self.read(0xD2, 30, 94 * 3)


def atomic_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    temporary = path.with_name(path.name + '.tmp')
    temporary.write_text(json.dumps(value, indent=2) + '\n')
    temporary.chmod(0o600)
    temporary.replace(path)


class Sidelights:
    def __init__(self, keyboard, backup_path):
        self.keyboard = keyboard
        self.backup_path = Path(backup_path)
        current = keyboard.state()
        if self.backup_path.exists():
            record = json.loads(self.backup_path.read_text())
            if record.get('vid') != VID or record.get('pid') != PID:
                raise ProtocolError("Backup belongs to a different device")
            self.original = bytes(record['original'])
            validate_state(self.original)
        else:
            self.original = current

    def show(self, color, breathe=False, effect=None):
        side = side_settings(color, effect or ('breathe' if breathe else 'static'))
        state = bytearray(self.keyboard.state())
        if not self.backup_path.exists():
            self.original = bytes(state)
            atomic_json(self.backup_path, {'vid': VID, 'pid': PID,
                        'original': list(state), 'firmware': list(self.keyboard.firmware)})
        # Two bars are one zone in stock firmware. Keep all backlight bytes.
        state[9:] = side
        self.keyboard.write_state(bytes(state))

    def restore(self):
        if not self.backup_path.exists():
            return
        state = bytearray(self.keyboard.state())
        state[9:] = self.original[9:]
        if state != self.keyboard.state():
            self.keyboard.write_state(bytes(state))
        # Delete only after verified recovery; next activation captures a fresh baseline.
        self.backup_path.unlink()


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=['probe', 'demo', 'restore'])
    args = parser.parse_args()
    keyboard = Keyboard()
    try:
        print(json.dumps({'firmware_raw': keyboard.firmware.hex(),
                          'lighting': list(keyboard.state()), 'led_count': 104}))
        if args.action != 'probe':
            lights = Sidelights(keyboard, Path(__file__).parent / 'runtime/original-lighting.json')
            if args.action == 'restore':
                lights.restore()
                print('Original sidelights restored and verified')
            else:
                try:
                    for name, color in [('blue', (0, 96, 255)),
                                        ('amber', (255, 128, 0)),
                                        ('green', (0, 255, 64))]:
                        lights.show(color)
                        colors = keyboard.side_colors()
                        print(json.dumps({'demo': name, 'lighting': list(keyboard.state()),
                                          'side_rgb': [list(colors[i:i+3]) for i in range(0, 60, 3)]}),
                              flush=True)
                        time.sleep(2)
                finally:
                    lights.restore()
                    print('Original sidelights restored and verified')
    finally:
        keyboard.close()
