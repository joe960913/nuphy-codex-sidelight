"""Local Codex lifecycle -> Air75 V3 sidelights. Never retains chat/tool content."""
import argparse
import contextlib
import fcntl
import json
import os
import re
from pathlib import Path
import signal
import subprocess
import sys
import time
import preferences

ROOT = Path(__file__).resolve().parent
RUNTIME = ROOT / 'runtime'
EVENTS = ('UserPromptSubmit', 'PreToolUse', 'PostToolUse', 'PermissionRequest',
          'Stop', 'Interrupt', 'SessionEnd')
ACTIVE_SECONDS = 24 * 60 * 60
TRANSCRIPTS = Path.home() / '.codex/sessions'
LIGHT_STATES = {'working': (0, 96, 255), 'waiting': (255, 128, 0),
                'complete': (0, 255, 64), 'error': (255, 0, 0), 'idle': None}


def read_preferences():
    with lock(RUNTIME / 'preferences.lock'):
        try:
            return preferences.load(RUNTIME / 'preferences.json'), None
        except preferences.SettingsError as error:
            return preferences.default_settings(), error.code


def read_control():
    with lock(RUNTIME / 'control.lock'):
        try:
            return json.loads((RUNTIME / 'control.json').read_text())
        except (FileNotFoundError, ValueError):
            return {}


def desired_light(sessions, control, now, durations=None):
    if (control.get('mode') == 'test' and control.get('expires_at', 0) > now
            and control.get('state') in LIGHT_STATES):
        return control['state'], 'test', control.get('request_id')
    return aggregate(sessions, now, durations), 'auto', control.get('request_id')


def save(path, data):
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps(data, indent=2) + '\n')
    temporary.chmod(0o600)
    temporary.replace(path)


@contextlib.contextmanager
def lock(path, blocking=True):
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    with path.open('a+') as stream:
        fcntl.flock(stream, fcntl.LOCK_EX | (0 if blocking else fcntl.LOCK_NB))
        try:
            yield
        finally:
            fcntl.flock(stream, fcntl.LOCK_UN)


def read_sessions():
    try:
        return json.loads((RUNTIME / 'sessions.json').read_text())
    except FileNotFoundError:
        return {}


def prune(sessions, now, durations=None):
    durations = preferences.DEFAULTS['durations'] if durations is None else durations
    return {sid: row for sid, row in sessions.items()
            if 0 <= now - row['updated'] < durations.get(row['state'], ACTIVE_SECONDS)}


def transcript_path(value):
    if not isinstance(value, str):
        return None
    path = Path(value).resolve()
    if path.suffix == '.jsonl' and path.is_relative_to(TRANSCRIPTS.resolve()):
        return path
    return None


def task_events(path, offset=0):
    """Use only appended lifecycle metadata; skip message and tool records."""
    events = []
    with path.open('rb') as stream:
        stream.seek(offset if path.stat().st_size >= offset else 0)
        while True:
            before = stream.tell()
            line = stream.readline()
            if not line or not line.endswith(b'\n'):
                return events, before
            if (b'"event_msg"' not in line[:200].split(b'"payload"', 1)[0]
                    or not re.search(rb'"payload"\s*:\s*\{\s*"type"\s*:\s*"(?:task_started|task_complete|turn_aborted)"', line[:350])):
                continue
            try:
                row = json.loads(line)
            except ValueError:
                continue
            payload = row.get('payload', {})
            if row.get('type') == 'event_msg' and payload.get('type') in ('task_started', 'task_complete', 'turn_aborted'):
                events.append({'type': payload['type'], 'turn_id': payload.get('turn_id'),
                               'error': bool(payload.get('error'))})


def reconcile(sessions, now, durations=None):
    result = {sid: dict(row) for sid, row in sessions.items()}
    for sid, row in list(result.items()):
        path = transcript_path(row.get('transcript_path'))
        if path is None:
            continue
        try:
            events, offset = task_events(path, row.get('offset', 0))
        except OSError:
            continue
        row['offset'] = offset
        for event in events:
            if event['turn_id'] != row.get('turn_id'):
                continue
            if event['type'] == 'task_complete':
                row.update(state='error' if event['error'] else 'complete', updated=now)
                row.pop('waiting_for', None)
            elif event['type'] == 'turn_aborted':
                result.pop(sid, None)
    return prune(result, now, durations)


def transition(sessions, event, now, durations=None):
    """Store identifiers/state only. Stop is turn completion, not proof of success."""
    result = prune(sessions, now, durations)
    sid = event.get('session_id')
    name = event.get('hook_event_name')
    if not isinstance(sid, str) or not sid or name not in EVENTS:
        return result
    if name in ('SessionEnd', 'Interrupt'):
        result.pop(sid, None)
        return result
    previous = result.get(sid, {})
    turn = event.get('turn_id') or previous.get('turn_id')
    # Do not let a late tool return change a newer turn, or resurrect Stop.
    if name in ('PostToolUse', 'PreToolUse', 'PermissionRequest'):
        if previous.get('turn_id') and turn != previous['turn_id']:
            return result
        if previous.get('state') in ('complete', 'error'):
            return result
    state = 'working'
    waiting_for = None
    if name == 'PermissionRequest':
        state = 'waiting'
        waiting_for = event.get('tool_name')
    elif name == 'Stop':
        state = 'complete'
    elif name == 'PreToolUse':
        tool = str(event.get('tool_name', '')).split('__')[-1]
        if tool in ('request_user_input', 'functions.request_user_input'):
            state = 'waiting'
            waiting_for = event.get('tool_name')
        elif previous.get('state') == 'waiting':
            state = 'waiting'
            waiting_for = previous.get('waiting_for')
    elif name == 'PostToolUse' and previous.get('state') == 'waiting':
        if previous.get('waiting_for') != event.get('tool_name'):
            state = 'waiting'
            waiting_for = previous.get('waiting_for')
    result[sid] = {'state': state, 'updated': now, 'turn_id': turn, 'last_event': name}
    path = transcript_path(event.get('transcript_path') or previous.get('transcript_path'))
    if path is not None:
        result[sid].update(transcript_path=str(path), offset=previous.get('offset', 0))
    if state == 'waiting':
        result[sid]['waiting_for'] = waiting_for
    return result


def aggregate(sessions, now, durations=None):
    states = {row['state'] for row in prune(sessions, now, durations).values()}
    return next((s for s in ('error', 'waiting', 'working', 'complete') if s in states), 'idle')


def ensure_daemon():
    try:
        with lock(RUNTIME / 'daemon.lock', blocking=False):
            pass
    except BlockingIOError:
        return
    with (RUNTIME / 'bridge.log').open('ab') as log:
        subprocess.Popen([sys.executable, str(Path(__file__).resolve()), 'run'],
                         stdin=subprocess.DEVNULL, stdout=log, stderr=log,
                         start_new_session=True, close_fds=True)


def hook():
    # Advisory only: never block an agent action or grant an approval.
    try:
        event = json.load(sys.stdin)
        if not isinstance(event, dict):
            return
        settings, _ = read_preferences()
        with lock(RUNTIME / 'sessions.lock'):
            sessions = transition(read_sessions(), event, time.time(), settings['durations'])
            save(RUNTIME / 'sessions.json', sessions)
        ensure_daemon()
    except Exception as error:
        RUNTIME.mkdir(parents=True, exist_ok=True, mode=0o700)
        with (RUNTIME / 'bridge.log').open('a') as log:
            log.write(f'hook failed: {type(error).__name__}\n')
    finally:
        # Stop requires JSON; the same non-steering output is valid for all hooks.
        print('{}')


def run():
    from nuphy import Keyboard, Sidelights
    stopped = False

    def stop(*_):
        nonlocal stopped
        stopped = True

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    keyboard = lights = None
    last_state = None
    next_connect = 0.0
    last_write = 0.0
    idle_since = None
    last_error = None
    last_checked = 0.0
    probe_id = None
    receipt = {}
    try:
        while not stopped:
            now = time.time()
            settings, settings_error = read_preferences()
            durations = settings['durations']
            with lock(RUNTIME / 'sessions.lock'):
                before = read_sessions()
                sessions = reconcile(before, now, durations)
                if sessions != before:
                    save(RUNTIME / 'sessions.json', sessions)
            control = read_control()
            desired, mode, request_id = desired_light(sessions, control, now, durations)
            profile = settings['states'][desired]
            key = (desired, mode, request_id, profile['color'], profile['effect'])
            ui_alive = control.get('ui_expires_at', 0) > now
            idle_since = (idle_since or now) if (desired == 'idle' and profile['effect'] == 'system'
                                                and not ui_alive and mode == 'auto') else None
            if idle_since is not None and now - idle_since > 30:
                break
            requested_probe = control.get('probe_id')
            if requested_probe != probe_id:
                next_connect = 0
            if keyboard is None and time.monotonic() >= next_connect:
                try:
                    keyboard = Keyboard()
                    lights = Sidelights(keyboard, RUNTIME / 'original-lighting.json')
                    last_state = None
                    last_error = None
                    last_checked = 0
                except Exception as error:
                    if keyboard is not None:
                        keyboard.close()
                    keyboard = lights = None
                    message = str(error)
                    if message != last_error:
                        print(f'Keyboard unavailable: {message}', flush=True)
                        last_error = message
                    save(RUNTIME / 'status.json', {'state': 'unavailable', 'verified': False,
                        'connected': False, 'error': message, 'time': now,
                        'updated_at': now, 'probe_id': requested_probe, 'mode': mode})
                    probe_id = requested_probe
                    next_connect = time.monotonic() + 5
            if keyboard is not None and key != last_state:
                # D6 is a configuration write. Avoid per-token/tool-frame updates.
                # Built-in breathing runs on the keyboard without streaming frames.
                if time.monotonic() - last_write >= 2:
                    try:
                        if profile['effect'] == 'system':
                            lights.restore()
                        else:
                            lights.show(preferences.rgb(profile), effect=profile['effect'])
                        expected_side = list(keyboard.state()[9:])
                        print(json.dumps({'time': now, 'state': desired, 'verified': True}), flush=True)
                        receipt = {'state': desired, 'verified': True, 'time': now,
                                   'mode': mode, 'request_id': request_id,
                                   'profile': profile, 'expected_side': expected_side}
                        last_state = key
                        last_checked = 0
                        last_write = time.monotonic()
                    except Exception as error:
                        print(f'Lighting stopped: {error}', flush=True)
                        last_error = str(error)
                        save(RUNTIME / 'status.json', {'state': 'unavailable', 'verified': False,
                            'connected': False, 'error': str(error), 'time': now,
                            'updated_at': now, 'probe_id': requested_probe, 'mode': mode})
                        # The finally block attempts one restoration, then exits.
                        break
            if keyboard is not None and (time.monotonic() - last_checked >= 2 or requested_probe != probe_id):
                try:
                    raw = keyboard.state()
                    verified = list(raw[9:]) == receipt.get('expected_side')
                    receipt.update(connected=True, updated_at=time.time(), probe_id=requested_probe,
                                   verified=verified, lighting=list(raw), led_count=104)
                    if requested_probe != probe_id:
                        colors = keyboard.side_colors()
                        receipt['side_rgb'] = [list(colors[i:i+3]) for i in range(0, 60, 3)]
                    save(RUNTIME / 'status.json', receipt)
                    last_checked = time.monotonic()
                    probe_id = requested_probe
                except Exception as error:
                    last_error = str(error)
                    save(RUNTIME / 'status.json', {'state': 'unavailable', 'verified': False,
                        'connected': False, 'error': str(error), 'time': now,
                        'updated_at': now, 'probe_id': requested_probe, 'mode': mode})
                    keyboard.close()
                    keyboard = lights = None
                    next_connect = time.monotonic() + 5
                    probe_id = requested_probe
            time.sleep(0.25)
    finally:
        if lights is not None:
            try:
                lights.restore()
                print('Original sidelights restored on exit', flush=True)
            except Exception as error:
                print(f'Restore pending; run nuphy.py restore after reconnect: {error}', flush=True)
        if keyboard is not None:
            keyboard.close()
        save(RUNTIME / 'status.json', {'state': 'idle', 'verified': False,
            'connected': False, 'stopped': True, 'time': time.time(), 'updated_at': time.time(),
            'error': last_error})


def config():
    import shlex
    command = shlex.join([sys.executable, str(Path(__file__).resolve()), 'hook'])
    return {'description': 'NuPhy Codex Sidelight; local lifecycle metadata only.',
            'hooks': {event: [{'hooks': [{'type': 'command', 'command': command,
                                         'timeout': 3}]}] for event in EVENTS}}


def install(uninstall=False):
    """Merge only this bridge's entries. Hook trust remains user-controlled."""
    path = Path.home() / '.codex/hooks.json'
    existing = json.loads(path.read_text()) if path.exists() else {'hooks': {}}
    before = json.loads(json.dumps(existing))
    ours = config()
    command = ours['hooks']['Stop'][0]['hooks'][0]['command']
    for event in EVENTS:
        groups = existing.setdefault('hooks', {}).get(event, [])
        kept = []
        for group in groups:
            group = dict(group)
            group['hooks'] = [h for h in group.get('hooks', []) if h.get('command') != command]
            if group['hooks']:
                kept.append(group)
        if not uninstall:
            kept.extend(ours['hooks'][event])
        if kept:
            existing['hooks'][event] = kept
        else:
            existing['hooks'].pop(event, None)
    RUNTIME.mkdir(parents=True, exist_ok=True, mode=0o700)
    if path.exists() and not (RUNTIME / 'hooks-before-install.json').exists():
        save(RUNTIME / 'hooks-before-install.json', before)
    path.parent.mkdir(parents=True, exist_ok=True)
    save(path, existing)
    save(ROOT / 'hooks.preview.json', ours)
    print(f'{"Removed" if uninstall else "Installed"} bridge definitions in {path}')
    if not uninstall:
        print('Review and trust these hooks in Codex /hooks before they can run.')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=['hook', 'run', 'status', 'install', 'uninstall', 'track'])
    parser.add_argument('transcript', nargs='?')
    args = parser.parse_args()
    RUNTIME.mkdir(parents=True, exist_ok=True, mode=0o700)
    if args.action == 'hook':
        hook()
    elif args.action == 'run':
        try:
            with lock(RUNTIME / 'daemon.lock', blocking=False):
                run()
        except BlockingIOError:
            pass
    elif args.action == 'track':
        path = transcript_path(args.transcript)
        if path is None:
            raise ValueError('Expected a local Codex session transcript')
        with path.open() as source:
            metadata = json.loads(source.readline()).get('payload', {})
        sid = metadata.get('id') or metadata.get('session_id')
        events, offset = task_events(path)
        if not sid or not events:
            raise ValueError('No session identity/lifecycle event')
        latest = events[-1]
        state = ('working' if latest['type'] == 'task_started' else
                 'error' if latest['error'] else 'complete')
        with lock(RUNTIME / 'sessions.lock'):
            sessions = read_sessions()
            sessions[sid] = {'state': state, 'turn_id': latest['turn_id'],
                             'updated': time.time(), 'transcript_path': str(path), 'offset': offset}
            save(RUNTIME / 'sessions.json', sessions)
        ensure_daemon()
        print(json.dumps({'session_id': sid, 'observed_event': latest['type'], 'state': state}))
    elif args.action == 'status':
        settings, _ = read_preferences()
        with lock(RUNTIME / 'sessions.lock'):
            sessions = prune(read_sessions(), time.time(), settings['durations'])
        print(json.dumps({'aggregate': aggregate(sessions, time.time(), settings['durations']),
                          'sessions': sessions}, indent=2))
    else:
        install(uninstall=args.action == 'uninstall')


if __name__ == '__main__':
    main()
