"""Loopback-only web control panel for the existing sidelight daemon."""
import argparse
import json
import mimetypes
import platform
import secrets
import shutil
import subprocess
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

import bridge
import preferences

ROOT = Path(__file__).resolve().parent
LEASE_SECONDS = 20
ERROR_CODES = {
    '请求格式不正确。': 'invalid_request', '请刷新页面后重试。': 'refresh_page',
    '未知的灯光状态。': 'invalid_state', '未知操作。': 'invalid_request',
    '请先用 USB 数据线连接键盘，再点击“测试连接”。': 'connect_usb',
    '另一个页面正在测试；请先在那里退出测试模式。': 'other_owner',
    '仅允许本机访问。': 'local_only', '不允许跨站请求。': 'cross_origin',
    '页面已过期，请刷新。': 'refresh_page', '页面不存在。': 'not_found',
    '操作不存在。': 'not_found',
}


def daemon_alive():
    try:
        with bridge.lock(bridge.RUNTIME / 'daemon.lock', blocking=False):
            return False
    except BlockingIOError:
        return True


def hardware_inventory():
    if platform.system() != 'Darwin':
        return {'wired_count': 0, 'receiver': False, 'error': '当前服务需要在 macOS 运行。'}
    try:
        import hid
        devices = hid.enumerate(0x19F5, 0)
        configurations = {(d['product_id'], d['path']) for d in devices
                          if d['usage_page'] == 1 and d['usage'] == 0}
        return {'wired_count': sum(pid == 0x1028 for pid, _ in configurations),
                'receiver': any(pid == 0x2620 for pid, _ in configurations)}
    except Exception:
        return {'wired_count': 0, 'receiver': False, 'error': '无法读取键盘设备，请检查输入监控权限。'}


def codex_info():
    app_present = any(p.exists() for p in (
        Path('/Applications/Codex.app'),
        Path('/Applications/ChatGPT.app/Contents/Resources/codex-cli/CodexCLI.app')))
    cli_present = bool(shutil.which('codex') or (Path.home() / '.local/bin/codex').exists())
    running = False
    try:
        processes = subprocess.check_output(['ps', '-axo', 'comm='], text=True, timeout=2).splitlines()
        running = any('/CodexCLI.app/' in p
                      or p.endswith('/codex') or '/Codex.app/Contents/MacOS/' in p for p in processes)
    except (OSError, subprocess.SubprocessError):
        pass
    configured = 0
    try:
        hooks = json.loads((Path.home() / '.codex/hooks.json').read_text()).get('hooks', {})
        configured = sum(any(str(ROOT / 'bridge.py') in h.get('command', '')
                             for g in hooks.get(event, []) for h in g.get('hooks', []))
                         for event in bridge.EVENTS)
    except (OSError, ValueError, TypeError):
        pass
    return {'installed': app_present or cli_present, 'running': running,
            'app': app_present, 'cli': cli_present, 'hook_count': configured}


class Panel:
    def __init__(self):
        self.token = secrets.token_urlsafe(32)
        self._cache_lock = threading.Lock()
        self._checked = 0
        self._environment = {}

    def environment(self, force=False):
        with self._cache_lock:
            if force or time.monotonic() - self._checked > 3:
                self._environment = {'mac': platform.system() == 'Darwin',
                                     'os_version': platform.mac_ver()[0],
                                     'keyboard': hardware_inventory(), 'codex': codex_info()}
                self._checked = time.monotonic()
            return self._environment

    def snapshot(self, client=''):
        now = time.time()
        environment = self.environment()
        with bridge.lock(bridge.RUNTIME / 'sessions.lock'):
            sessions = bridge.prune(bridge.read_sessions(), now)
        try:
            hardware = json.loads((bridge.RUNTIME / 'status.json').read_text())
        except (FileNotFoundError, ValueError):
            hardware = {}
        alive = daemon_alive()
        connected = (environment['keyboard']['wired_count'] == 1 and alive
                     and hardware.get('connected', False) and now - hardware.get('updated_at', 0) < 7)
        control = bridge.read_control()
        desired, mode, request_id = bridge.desired_light(sessions, control, now)
        last_event = max((r.get('updated', 0) for r in sessions.values()), default=0)
        settings, settings_error = bridge.read_preferences()
        return {'environment': environment,
                'settings': settings, 'settings_error': settings_error,
                'codex': {'state': bridge.aggregate(sessions, now), 'sessions': len(sessions),
                          'last_event_at': last_event},
                'connection': {'verified': bool(connected), 'daemon': alive,
                               'checked_at': hardware.get('updated_at'),
                               'probe_id': hardware.get('probe_id'),
                               'error': hardware.get('error') if not connected else None},
                'light': {'state': hardware.get('state', 'unavailable') if connected else 'unavailable',
                          'verified': bool(connected and hardware.get('verified')),
                          'mode': hardware.get('mode', 'auto'),
                          'applied_request_id': hardware.get('request_id'),
                          'profile': hardware.get('profile'),
                          'changed_at': hardware.get('time')},
                'test': {'active': mode == 'test', 'state': desired,
                         'owner': mode == 'test' and control.get('client') == client,
                         'expires_at': control.get('expires_at', 0), 'request_id': request_id},
                'time': now}

    def action(self, name, data, client):
        if not isinstance(data, dict):
            raise ValueError('请求格式不正确。')
        if not client or len(client) > 100:
            raise ValueError('请刷新页面后重试。')
        if name in ('settings', 'reset_settings'):
            with bridge.lock(bridge.RUNTIME / 'preferences.lock'):
                try:
                    current = preferences.load(bridge.RUNTIME / 'preferences.json')
                except preferences.SettingsError:
                    if name != 'reset_settings' or data.get('state') is not None:
                        raise
                    current = preferences.default_settings()
                updated = preferences.update(current, data, reset=name == 'reset_settings')
                bridge.save(bridge.RUNTIME / 'preferences.json', updated)
            # Language changes do not touch the hardware or start its controller.
            if updated['states'] != current['states']:
                bridge.ensure_daemon()
            return {'settings': updated}
        now = time.time()
        if name == 'test' and data.get('state') not in bridge.LIGHT_STATES:
            raise ValueError('未知的灯光状态。')
        if name == 'test' and not self.snapshot(client)['connection']['verified']:
            raise ValueError('请先用 USB 数据线连接键盘，再点击“测试连接”。')
        if name not in ('heartbeat', 'probe', 'test', 'auto'):
            raise ValueError('未知操作。')
        with bridge.lock(bridge.RUNTIME / 'control.lock'):
            try:
                control = json.loads((bridge.RUNTIME / 'control.json').read_text())
            except (FileNotFoundError, ValueError):
                control = {}
            control['ui_expires_at'] = now + LEASE_SECONDS
            if name == 'heartbeat':
                if control.get('client') == client and control.get('expires_at', 0) > now:
                    control['expires_at'] = now + LEASE_SECONDS
            elif name == 'probe':
                control['probe_id'] = secrets.token_hex(12)
            elif name == 'test':
                if (control.get('mode') == 'test' and control.get('expires_at', 0) > now
                        and control.get('client') != client):
                    raise ValueError('另一个页面正在测试；请先在那里退出测试模式。')
                control.update(mode='test', state=data['state'], client=client,
                               expires_at=now + LEASE_SECONDS, request_id=secrets.token_hex(12))
            elif name == 'auto':
                control.update(mode='auto', expires_at=0, request_id=secrets.token_hex(12))
            bridge.save(bridge.RUNTIME / 'control.json', control)
        if name != 'heartbeat':
            bridge.ensure_daemon()
        if name == 'probe':
            self.environment(force=True)
        return {'request_id': control.get('request_id'), 'probe_id': control.get('probe_id')}


class Handler(BaseHTTPRequestHandler):
    server_version = 'NuPhyCodexSidelight'

    def log_message(self, *_):
        pass

    def reply(self, code, body, content_type='application/json; charset=utf-8'):
        if isinstance(body, dict) and 'error' in body and 'code' not in body:
            body['code'] = ERROR_CODES.get(body['error'], 'operation_failed')
        if not isinstance(body, bytes):
            body = json.dumps(body, ensure_ascii=False).encode()
        self.send_response(code)
        self.send_header('Content-Type', content_type)
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('X-Frame-Options', 'DENY')
        self.send_header('Content-Security-Policy', "default-src 'self'; style-src 'self' 'unsafe-inline'; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'")
        self.end_headers()
        try:
            self.wfile.write(body)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def allowed(self, api=False):
        port = self.server.server_port
        hosts = {f'127.0.0.1:{port}', f'localhost:{port}'}
        if self.headers.get('Host') not in hosts:
            self.reply(403, {'error': '仅允许本机访问。'})
            return False
        origin = self.headers.get('Origin')
        if origin and origin not in {f'http://{host}' for host in hosts}:
            self.reply(403, {'error': '不允许跨站请求。'})
            return False
        if api and not secrets.compare_digest(self.headers.get('X-Sidelight-Key', ''), self.server.panel.token):
            self.reply(403, {'error': '页面已过期，请刷新。'})
            return False
        return True

    def do_GET(self):
        path = urlsplit(self.path).path
        if not self.allowed(api=path.startswith('/api/') and path != '/api/bootstrap'):
            return
        if path == '/api/bootstrap':
            self.reply(200, {'token': self.server.panel.token})
            return
        if path == '/api/status':
            self.reply(200, self.server.panel.snapshot(self.headers.get('X-Client-Id', '')))
            return
        dist = (ROOT / 'dist').resolve()
        file = (dist / ('index.html' if path == '/' else path.lstrip('/'))).resolve()
        if not file.is_relative_to(dist) or not file.is_file():
            self.reply(404, {'error': '页面不存在。'})
            return
        mime = mimetypes.guess_type(str(file))[0] or 'application/octet-stream'
        self.reply(200, file.read_bytes(), mime + '; charset=utf-8')

    def do_POST(self):
        if not self.allowed(api=True):
            return
        try:
            length = int(self.headers.get('Content-Length', 0))
            if not 0 < length < 4096 or self.headers.get_content_type() != 'application/json':
                raise ValueError('请求格式不正确。')
            data = json.loads(self.rfile.read(length))
            path = urlsplit(self.path).path
            if not path.startswith('/api/'):
                self.reply(404, {'error': '操作不存在。'})
                return
            result = self.server.panel.action(path[5:], data, self.headers.get('X-Client-Id', ''))
            self.reply(200, result)
        except (ValueError, TypeError) as error:
            self.reply(409 if getattr(error, 'code', '') == 'settings_conflict' else 400,
                       {'error': str(error), 'code': getattr(error, 'code',
                            ERROR_CODES.get(str(error), 'operation_failed'))})


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', type=int, default=8765)
    args = parser.parse_args()
    bridge.RUNTIME.mkdir(parents=True, exist_ok=True)
    server = ThreadingHTTPServer(('127.0.0.1', args.port), Handler)
    server.panel = Panel()
    print(f'NuPhy Codex Sidelight is ready: http://127.0.0.1:{server.server_port}', flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == '__main__':
    main()
