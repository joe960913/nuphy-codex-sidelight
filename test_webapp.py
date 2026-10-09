import http.client
import json
from pathlib import Path
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

import bridge
import webapp
import preferences


class PanelTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.runtime = Path(directory.name)
        self.enterContext(patch.object(bridge, 'RUNTIME', self.runtime))
        self.ensure = self.enterContext(patch.object(bridge, 'ensure_daemon'))
        self.alive = self.enterContext(patch('webapp.daemon_alive', return_value=True))
        self.panel = webapp.Panel()
        self.environment = {'mac': True, 'os_version': 'test',
                            'keyboard': {'wired_count': 1, 'receiver': True},
                            'codex': {'installed': True, 'running': True, 'hook_count': 7}}
        self.enterContext(patch.object(self.panel, 'environment', return_value=self.environment))
        self.hardware = {'connected': True, 'verified': True, 'updated_at': time.time(),
                         'state': 'working', 'mode': 'auto', 'request_id': None}
        bridge.save(self.runtime / 'status.json', self.hardware)
        bridge.save(self.runtime / 'sessions.json', {'private-session': {
            'state': 'working', 'updated': time.time(), 'turn_id': 'private-turn',
            'transcript_path': '/private/path'}})

    def test_expired_override_returns_latest_codex_state_without_mutating_sessions(self):
        sessions = {'a': {'state': 'waiting', 'updated': 100}}
        control = {'mode': 'test', 'state': 'complete', 'expires_at': 120, 'request_id': 'one'}
        self.assertEqual(bridge.desired_light(sessions, control, 119), ('complete', 'test', 'one'))
        self.assertEqual(bridge.desired_light(sessions, control, 120), ('waiting', 'auto', 'one'))
        self.assertEqual(sessions['a']['state'], 'waiting')

    def test_test_action_is_pending_until_hardware_receipt_matches(self):
        result = self.panel.action('test', {'state': 'complete'}, 'owner')
        status = self.panel.snapshot('owner')
        self.assertTrue(status['test']['active'])
        self.assertTrue(status['test']['owner'])
        self.assertEqual(status['light']['state'], 'working')
        self.assertNotEqual(status['light']['applied_request_id'], result['request_id'])
        self.assertEqual(status['codex']['state'], 'working')
        self.ensure.assert_called_once()

    def test_heartbeat_only_renews_live_owner_and_never_resurrects_expired_test(self):
        self.panel.action('test', {'state': 'error'}, 'owner')
        initial = bridge.read_control()
        self.panel.action('heartbeat', {}, 'other')
        self.assertEqual(bridge.read_control()['expires_at'], initial['expires_at'])
        initial['expires_at'] = time.time() - 1
        bridge.save(self.runtime / 'control.json', initial)
        self.panel.action('heartbeat', {}, 'owner')
        self.assertEqual(bridge.read_control()['expires_at'], initial['expires_at'])
        self.assertFalse(self.panel.snapshot('owner')['test']['active'])

    def test_second_page_cannot_override_live_test_but_can_resume_auto(self):
        self.panel.action('test', {'state': 'waiting'}, 'owner')
        with self.assertRaisesRegex(ValueError, '另一个页面'):
            self.panel.action('test', {'state': 'error'}, 'other')
        self.assertFalse(self.panel.snapshot('other')['test']['owner'])
        self.panel.action('auto', {}, 'other')
        status = self.panel.snapshot('other')
        self.assertFalse(status['test']['active'])
        self.assertEqual(status['codex']['state'], 'working')

    def test_no_pass_on_receiver_only_stale_receipt_or_stopped_daemon(self):
        for failure in ('receiver', 'stale', 'stopped', 'unacknowledged'):
            with self.subTest(failure=failure):
                self.environment['keyboard']['wired_count'] = 0 if failure == 'receiver' else 1
                bridge.save(self.runtime / 'status.json', self.hardware | {
                    'updated_at': time.time() - 10 if failure == 'stale' else time.time(),
                    'connected': failure != 'unacknowledged'})
                self.alive.return_value = failure != 'stopped'
                self.assertFalse(self.panel.snapshot()['connection']['verified'])
                with self.assertRaisesRegex(ValueError, 'USB'):
                    self.panel.action('test', {'state': 'working'}, 'owner')

    def test_status_does_not_expose_session_identifiers_or_paths(self):
        status = json.dumps(self.panel.snapshot('owner'))
        self.assertNotIn('private-', status)
        self.assertNotIn('/private/', status)

    def test_unknown_state_does_not_write_control_or_start_daemon(self):
        with self.assertRaises(ValueError):
            self.panel.action('test', {'state': 'rainbow'}, 'owner')
        self.assertFalse((self.runtime / 'control.json').exists())
        self.ensure.assert_not_called()

    def test_preferences_survive_new_panel_and_do_not_need_connected_keyboard(self):
        self.alive.return_value = False
        expected = preferences.default_settings()['states']['working']
        desired = {'color': '#ab12ef', 'effect': 'flow'}
        result = self.panel.action('settings', {'state': 'working', 'profile': desired,
                                   'expected': expected}, 'owner')
        self.assertEqual(result['settings']['states']['working'], {'color': '#AB12EF', 'effect': 'flow'})
        with patch.object(webapp.Panel, 'environment', return_value=self.environment):
            other = webapp.Panel().snapshot()
        self.assertEqual(other['settings'], result['settings'])
        self.assertFalse(other['connection']['verified'])

    def test_language_is_persistent_and_does_not_start_hardware(self):
        self.panel.action('settings', {'language': 'en'}, 'owner')
        self.assertEqual(preferences.load(self.runtime / 'preferences.json')['language'], 'en')
        self.ensure.assert_not_called()

    def test_reset_one_state_preserves_other_states_and_language(self):
        current = preferences.default_settings()
        current['language'] = 'en'
        for state in ('working', 'idle'):
            current['states'][state] = {'color': '#AA12EF', 'effect': 'flow'}
        bridge.save(self.runtime / 'preferences.json', current)
        self.panel.action('reset_settings', {'state': 'working'}, 'owner')
        result = preferences.load(self.runtime / 'preferences.json')
        self.assertEqual(result['states']['working'], preferences.DEFAULTS['states']['working'])
        self.assertEqual(result['states']['idle'], current['states']['idle'])
        self.assertEqual(result['language'], 'en')
        self.panel.action('reset_settings', {}, 'owner')
        result = preferences.load(self.runtime / 'preferences.json')
        self.assertEqual(result['states'], preferences.DEFAULTS['states'])
        self.assertEqual(result['language'], 'en')

    def test_invalid_settings_never_overwrite_existing_preferences(self):
        current = preferences.default_settings()
        path = self.runtime / 'preferences.json'
        bridge.save(path, current)
        for profile in ({'color': '#FFF', 'effect': 'flow'}, {'color': '#112233', 'effect': 'wave'},
                        {'color': '#112233', 'effect': []}, {'color': 123, 'effect': 'static'}):
            with self.assertRaises(preferences.SettingsError):
                self.panel.action('settings', {'state': 'working', 'profile': profile,
                    'expected': current['states']['working']}, 'owner')
            self.assertEqual(preferences.load(path), current)

    def test_stale_editor_cannot_overwrite_a_newer_state_setting(self):
        before = preferences.default_settings()['states']['working']
        data = {'state': 'working', 'profile': {'color': '#112233', 'effect': 'neon'}, 'expected': before}
        self.panel.action('settings', data, 'first')
        with self.assertRaisesRegex(preferences.SettingsError, 'settings_conflict'):
            self.panel.action('settings', data | {'profile': {'color': '#AABBCC', 'effect': 'flow'}}, 'second')
        self.assertEqual(preferences.load(self.runtime / 'preferences.json')['states']['working'], data['profile'])

    def test_corrupt_preferences_are_visible_and_require_explicit_reset(self):
        path = self.runtime / 'preferences.json'
        path.write_text('broken')
        self.assertEqual(self.panel.snapshot()['settings_error'], 'settings_corrupt')
        with self.assertRaisesRegex(preferences.SettingsError, 'settings_corrupt'):
            self.panel.action('settings', {'language': 'en'}, 'owner')
        self.assertEqual(path.read_text(), 'broken')
        self.panel.action('reset_settings', {}, 'owner')
        self.assertIsNone(self.panel.snapshot()['settings_error'])


class HTTPTests(unittest.TestCase):
    def setUp(self):
        self.server = webapp.ThreadingHTTPServer(('127.0.0.1', 0), webapp.Handler)
        self.server.panel = webapp.Panel()
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.addCleanup(self.stop)

    def stop(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()

    def request(self, method='GET', path='/api/status', headers=None, body=None):
        connection = http.client.HTTPConnection('127.0.0.1', self.server.server_port, timeout=3)
        try:
            connection.request(method, path, body=body, headers=headers or {})
            response = connection.getresponse()
            return response.status, response.getheaders(), response.read()
        finally:
            connection.close()

    def test_auth_cross_site_and_host_checks(self):
        self.assertEqual(self.request()[0], 403)
        self.assertEqual(self.request(path='/api/bootstrap', headers={'Origin': 'https://untrusted.example'})[0], 403)
        self.assertEqual(self.request(path='/api/bootstrap', headers={'Host': 'untrusted.example'})[0], 403)
        code, headers, body = self.request(path='/api/bootstrap')
        self.assertEqual(code, 200)
        self.assertEqual(json.loads(body)['token'], self.server.panel.token)
        self.assertNotIn('Access-Control-Allow-Origin', dict(headers))
        self.assertEqual(dict(headers)['X-Frame-Options'], 'DENY')

    def test_invalid_state_and_large_payload_rejected(self):
        headers = {'X-Sidelight-Key': self.server.panel.token, 'X-Client-Id': 'test',
                   'Content-Type': 'application/json'}
        for body in ('{"state":"rainbow"}', '[]', 'x' * 4096):
            self.assertEqual(self.request('POST', '/api/test', headers, body)[0], 400)

    def test_static_cannot_read_runtime_or_parent_files(self):
        for path in ('/runtime/sessions.json', '/../bridge.py', '/%2e%2e/bridge.py'):
            self.assertEqual(self.request(path=path)[0], 404)


if __name__ == '__main__':
    unittest.main()
