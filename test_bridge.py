import tempfile
import unittest
import json
from unittest.mock import patch
from pathlib import Path

from bridge import aggregate, transition, reconcile, task_events, transcript_path
from nuphy import ProtocolError, Sidelights, decode, frame
import preferences
import bridge


class InstallationTests(unittest.TestCase):
    def test_fresh_home_install_is_repeatable(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            home = root / 'home'
            with patch('bridge.Path.home', return_value=home), \
                    patch('bridge.ROOT', root), patch('bridge.RUNTIME', root / 'runtime'), \
                    patch('builtins.print'):
                bridge.install()
                path = home / '.codex/hooks.json'
                first = json.loads(path.read_text())
                bridge.install()
                self.assertEqual(json.loads(path.read_text()), first)
                self.assertEqual(set(first['hooks']), set(bridge.EVENTS))
                self.assertTrue(all(len(groups) == 1 for groups in first['hooks'].values()))

    def test_install_and_uninstall_preserve_other_hooks_and_backup(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / '.codex/hooks.json'
            path.parent.mkdir()
            original = {'description': 'Other integrations', 'hooks': {
                'Stop': [{'matcher': '*', 'hooks': [
                    {'type': 'command', 'command': 'echo another-hook'}]}],
                'SessionStart': [{'hooks': [{'type': 'command', 'command': 'echo start'}]}]}}
            path.write_text(json.dumps(original))
            with patch('bridge.Path.home', return_value=root), \
                    patch('bridge.ROOT', root), patch('bridge.RUNTIME', root / 'runtime'), \
                    patch('builtins.print'):
                bridge.install()
                bridge.install()
                backup = json.loads((root / 'runtime/hooks-before-install.json').read_text())
                self.assertEqual(backup, original)
                bridge.install(uninstall=True)
                self.assertEqual(json.loads(path.read_text()), original)


class EventsTests(unittest.TestCase):
    def event(self, name, sid='one', turn='a'):
        return {'hook_event_name': name, 'session_id': sid, 'turn_id': turn}

    def test_one_completion_cannot_hide_another_working_session(self):
        sessions = transition({}, self.event('UserPromptSubmit'), 100)
        sessions = transition(sessions, self.event('UserPromptSubmit', 'two'), 101)
        sessions = transition(sessions, self.event('Stop'), 102)
        self.assertEqual(aggregate(sessions, 103), 'working')

    def test_waiting_has_priority_and_clears_after_tool_return(self):
        sessions = transition({}, self.event('UserPromptSubmit'), 100)
        sessions = transition(sessions, self.event('PermissionRequest'), 101)
        sessions = transition(sessions, self.event('UserPromptSubmit', 'two'), 102)
        self.assertEqual(aggregate(sessions, 103), 'waiting')
        sessions = transition(sessions, self.event('PostToolUse'), 104)
        self.assertEqual(aggregate(sessions, 105), 'working')

    def test_completion_expires(self):
        sessions = transition({}, self.event('Stop'), 100)
        self.assertEqual(aggregate(sessions, 104.99), 'complete')
        self.assertEqual(aggregate(sessions, 105), 'idle')

    def test_error_also_defaults_to_five_seconds(self):
        sessions = {'one': {'state': 'error', 'updated': 100}}
        self.assertEqual(aggregate(sessions, 104.99), 'error')
        self.assertEqual(aggregate(sessions, 105), 'idle')

    def test_independent_durations_survive_event_processing_and_expire_at_boundary(self):
        durations = {'complete': 12, 'error': 20}
        sessions = {'one': {'state': 'complete', 'updated': 100, 'turn_id': 'a'},
                    'two': {'state': 'error', 'updated': 100, 'turn_id': 'b'}}
        # A later hook and the controller's reconciliation must use the same durations.
        sessions = transition(sessions, self.event('SessionEnd', 'other'), 108, durations)
        sessions = reconcile(sessions, 108, durations)
        self.assertEqual(set(sessions), {'one', 'two'})
        self.assertEqual(aggregate(sessions, 119.99, durations), 'error')
        self.assertEqual(aggregate(sessions, 120, durations), 'idle')
        self.assertEqual(set(bridge.prune(sessions, 112, durations)), {'two'})

    def test_duration_bounds_and_test_mode_override(self):
        for state in ('complete', 'error'):
            for duration in (2, 60):
                durations = dict(preferences.DEFAULTS['durations'], **{state: duration})
                sessions = {'one': {'state': state, 'updated': 100}}
                self.assertEqual(aggregate(sessions, 100 + duration - .01, durations), state)
                self.assertEqual(aggregate(sessions, 100 + duration, durations), 'idle')
                control = {'mode': 'test', 'state': state, 'expires_at': 200}
                self.assertEqual(bridge.desired_light(sessions, control, 170, durations)[:2],
                                 (state, 'test'))

    def test_shortening_duration_expires_an_existing_notification(self):
        sessions = {'one': {'state': 'complete', 'updated': 100}}
        self.assertEqual(aggregate(sessions, 108, {'complete': 12, 'error': 5}), 'complete')
        self.assertEqual(aggregate(sessions, 108, {'complete': 5, 'error': 5}), 'idle')

    def test_interruption_and_end_remove_only_their_session(self):
        for event in ('Interrupt', 'SessionEnd'):
            sessions = transition({}, self.event('UserPromptSubmit'), 100)
            sessions = transition(sessions, self.event('UserPromptSubmit', 'two'), 101)
            sessions = transition(sessions, self.event(event), 102)
            self.assertEqual(set(sessions), {'two'})

    def test_late_tool_events_do_not_resurrect_completion_or_replace_new_turn(self):
        sessions = transition({}, self.event('Stop'), 100)
        self.assertEqual(transition(sessions, self.event('PostToolUse'), 101), sessions)
        sessions = transition(sessions, self.event('UserPromptSubmit', turn='b'), 102)
        self.assertEqual(transition(sessions, self.event('PostToolUse'), 103), sessions)

    def test_no_prompt_or_tool_content_retained(self):
        event = self.event('UserPromptSubmit') | {'prompt': 'secret', 'tool_input': {'secret': 1}}
        result = transition({}, event, 100)
        self.assertEqual(set(result['one']), {'state', 'updated', 'turn_id', 'last_event'})

    def test_unrelated_parallel_tool_completion_preserves_waiting(self):
        event = self.event('PermissionRequest') | {'tool_name': 'Bash'}
        sessions = transition({}, event, 100)
        sessions = transition(sessions, self.event('PostToolUse') | {'tool_name': 'read_file'}, 101)
        self.assertEqual(aggregate(sessions, 102), 'waiting')
        sessions = transition(sessions, self.event('PostToolUse') | {'tool_name': 'Bash'}, 103)
        self.assertEqual(aggregate(sessions, 104), 'working')


class ProtocolTests(unittest.TestCase):
    def response(self, key=0x5A, plain=False, status=0):
        response = frame(0xD5, 17, key=key, payload=bytes(range(17)))
        response[0] = 0xAA
        response[2] = status
        if plain:
            response[4:8] = bytes([17, 0, 0, 0])
            response[3] = sum(response[4:]) & 255
        return bytes(response)

    def test_both_firmware_route_encodings(self):
        for plain in (False, True):
            self.assertEqual(decode(self.response(plain=plain), 0xD5, 17, 0, 0x5A), bytes(range(17)))

    def test_dongle_ff_is_rejection_even_with_valid_checksum(self):
        with self.assertRaisesRegex(ProtocolError, 'status 0xff'):
            decode(self.response(status=255), 0xD5, 17, 0, 0x5A)

    def test_corrupt_or_unrelated_response_rejected(self):
        for index in (1, 3, 5, 8):
            response = bytearray(self.response())
            response[index] ^= 1
            with self.assertRaises(ProtocolError):
                decode(bytes(response), 0xD5, 17, 0, 0x5A)


class TranscriptRecoveryTests(unittest.TestCase):
    def test_model_error_without_stop_becomes_red_then_expires(self):
        with tempfile.TemporaryDirectory() as directory, patch('bridge.TRANSCRIPTS', Path(directory)):
            path = Path(directory) / 'session.jsonl'
            path.write_text(json.dumps({'type': 'event_msg', 'payload': {
                'type': 'task_complete', 'turn_id': 'a', 'error': {'message': 'private'}}}) + '\n')
            sessions = {'one': {'state': 'working', 'updated': 100, 'turn_id': 'a',
                                'transcript_path': str(path), 'offset': 0}}
            result = reconcile(sessions, 101)
            self.assertEqual(aggregate(result, 102), 'error')
            self.assertNotIn('private', json.dumps(result))
            self.assertEqual(aggregate(result, 117), 'idle')

    def test_old_turn_completion_does_not_override_new_turn(self):
        with tempfile.TemporaryDirectory() as directory, patch('bridge.TRANSCRIPTS', Path(directory)):
            path = Path(directory) / 'session.jsonl'
            path.write_text(json.dumps({'type': 'event_msg', 'payload': {
                'type': 'task_complete', 'turn_id': 'old', 'error': None}}) + '\n')
            sessions = {'one': {'state': 'working', 'updated': 100, 'turn_id': 'new',
                                'transcript_path': str(path), 'offset': 0}}
            self.assertEqual(aggregate(reconcile(sessions, 101), 102), 'working')

    def test_partial_record_is_retried_and_tool_content_is_skipped(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'session.jsonl'
            ignored = json.dumps({'type': 'event_msg', 'payload': {'type': 'item_completed', 'item': 'private'}}) + '\n'
            last = json.dumps({'type': 'event_msg', 'payload': {'type': 'task_complete', 'turn_id': 'a'}})
            path.write_text(ignored + last)
            events, offset = task_events(path)
            self.assertEqual(events, [])
            self.assertEqual(offset, len(ignored))
            with path.open('a') as output:
                output.write('\n')
            events, offset = task_events(path, offset)
            self.assertEqual([e['type'] for e in events], ['task_complete'])

    def test_path_outside_codex_sessions_is_ignored(self):
        self.assertIsNone(transcript_path('/tmp/unrelated.jsonl'))


class FakeKeyboard:
    def __init__(self):
        self.current = bytes([13, 25, 2, 0, 0, 0, 48, 64, 63, 4, 80, 2, 0, 0, 255, 79, 61])
        self.firmware = b'example'
        self.fail = False

    def state(self):
        return self.current

    def write_state(self, state):
        self.current = bytes(state)
        if self.fail:
            raise ProtocolError('simulated lost acknowledgement')

    def close(self):
        pass


class ControllerTimingTests(unittest.TestCase):
    def test_controller_reads_saved_durations_and_restores_after_each_notification(self):
        for durations in ({'complete': 5, 'error': 5}, {'complete': 7, 'error': 3}):
            with self.subTest(durations=durations), tempfile.TemporaryDirectory() as directory:
                runtime = Path(directory)
                settings = preferences.default_settings()
                settings['durations'] = durations
                bridge.save(runtime / 'preferences.json', settings)
                bridge.save(runtime / 'sessions.json', {'one': {'state': 'complete', 'updated': 100}})
                bridge.save(runtime / 'control.json', {'ui_expires_at': 200})
                keyboard = FakeKeyboard()
                original = keyboard.state()
                clock = [100.0]
                handlers = {}
                receipts = []
                real_save = bridge.save

                def save(path, data):
                    if path.name == 'status.json' and data.get('verified'):
                        receipt = (data['state'], data['time'])
                        if not receipts or receipts[-1] != receipt:
                            receipts.append(receipt)
                    real_save(path, data)

                def advance(seconds):
                    clock[0] += seconds
                    if clock[0] == 110:
                        real_save(runtime / 'sessions.json', {'two': {'state': 'error', 'updated': 110}})
                    if clock[0] >= 120:
                        handlers[bridge.signal.SIGTERM]()

                with patch('bridge.RUNTIME', runtime), patch('nuphy.Keyboard', return_value=keyboard), \
                        patch('bridge.time.time', side_effect=lambda: clock[0]), \
                        patch('bridge.time.monotonic', side_effect=lambda: clock[0]), \
                        patch('bridge.time.sleep', side_effect=advance), \
                        patch('bridge.signal.signal', side_effect=lambda signum, handler: handlers.update({signum: handler})), \
                        patch('bridge.save', side_effect=save), patch('builtins.print'):
                    bridge.run()
                self.assertEqual(receipts, [('complete', 100), ('idle', 100 + durations['complete']),
                                            ('error', 110), ('idle', 110 + durations['error'])])
                self.assertEqual(keyboard.state(), original)
                self.assertFalse((runtime / 'original-lighting.json').exists())


class RecoveryTests(unittest.TestCase):
    def test_all_supported_native_effects_preserve_backlight_and_restore(self):
        for name, code in preferences.EFFECTS.items():
            if name == 'system':
                continue
            with self.subTest(effect=name), tempfile.TemporaryDirectory() as directory:
                keyboard = FakeKeyboard()
                original = keyboard.state()
                lights = Sidelights(keyboard, Path(directory) / 'backup.json')
                lights.show((12, 34, 56), effect=name)
                self.assertEqual(keyboard.state()[:9], original[:9])
                self.assertEqual(keyboard.state()[9:], bytes([code, 80, 2, int(name == 'neon'), 0, 12, 34, 56]))
                lights.restore()
                self.assertEqual(keyboard.state(), original)

    def test_main_backlight_preserved_and_later_user_baseline_respected(self):
        with tempfile.TemporaryDirectory() as directory:
            keyboard = FakeKeyboard()
            path = Path(directory) / 'backup.json'
            original = keyboard.state()
            lights = Sidelights(keyboard, path)
            lights.show((0, 96, 255))
            self.assertEqual(keyboard.state()[:9], original[:9])
            keyboard.current = bytes([6]) + keyboard.current[1:]
            lights.restore()
            self.assertEqual(keyboard.state()[0], 6)
            self.assertEqual(keyboard.state()[9:], original[9:])
            self.assertFalse(path.exists())
            keyboard.current = keyboard.current[:9] + bytes([1, 80, 2, 1, 0, 0, 0, 0])
            changed = keyboard.state()
            lights.show((0, 255, 0))
            lights.restore()
            self.assertEqual(keyboard.state(), changed)

    def test_failed_write_retains_snapshot_for_new_process_recovery(self):
        with tempfile.TemporaryDirectory() as directory:
            keyboard = FakeKeyboard()
            original = keyboard.state()
            path = Path(directory) / 'backup.json'
            lights = Sidelights(keyboard, path)
            keyboard.fail = True
            with self.assertRaises(ProtocolError):
                lights.show((255, 128, 0))
            self.assertTrue(path.exists())
            keyboard.fail = False
            Sidelights(keyboard, path).restore()
            self.assertEqual(keyboard.state(), original)
            self.assertFalse(path.exists())


if __name__ == '__main__':
    unittest.main()
