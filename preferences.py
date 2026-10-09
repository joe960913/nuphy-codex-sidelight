"""Validated, versioned preferences shared by the web panel and light controller."""
from copy import deepcopy
import json
import re

EFFECTS = {'flow': 0, 'neon': 1, 'static': 2, 'breathe': 3, 'rhythm': 4, 'system': None}
LANGUAGES = ('zh-CN', 'en')
DEFAULTS = {
    'version': 1,
    'language': 'zh-CN',
    'durations': {'complete': 5, 'error': 5},
    'states': {
        'working': {'color': '#0060FF', 'effect': 'breathe'},
        'waiting': {'color': '#FF8000', 'effect': 'breathe'},
        'complete': {'color': '#00FF40', 'effect': 'static'},
        'error': {'color': '#FF0000', 'effect': 'breathe'},
        'idle': {'color': '#89918E', 'effect': 'system'},
    },
}


class SettingsError(ValueError):
    def __init__(self, code):
        super().__init__(code)
        self.code = code


def default_settings():
    return deepcopy(DEFAULTS)


def validate_duration(value):
    if type(value) is not int or not 2 <= value <= 60:
        raise SettingsError('invalid_duration')
    return value


def validate_durations(values):
    if not isinstance(values, dict) or set(values) != set(DEFAULTS['durations']):
        raise SettingsError('invalid_duration')
    return {state: validate_duration(value) for state, value in values.items()}


def validate_profile(profile):
    if not isinstance(profile, dict) or set(profile) != {'color', 'effect'}:
        raise SettingsError('invalid_profile')
    if not isinstance(profile['color'], str) or not re.fullmatch(r'#[0-9a-fA-F]{6}', profile['color']):
        raise SettingsError('invalid_color')
    if not isinstance(profile['effect'], str) or profile['effect'] not in EFFECTS:
        raise SettingsError('invalid_effect')
    return {'color': profile['color'].upper(), 'effect': profile['effect']}


def load(path):
    try:
        data = json.loads(path.read_text())
    except FileNotFoundError:
        return default_settings()
    except (OSError, ValueError) as error:
        raise SettingsError('settings_corrupt') from error
    try:
        if (not isinstance(data, dict) or data.get('version') != 1
                or data.get('language') not in LANGUAGES
                or not isinstance(data.get('states'), dict)
                or set(data['states']) != set(DEFAULTS['states'])):
            raise SettingsError('settings_corrupt')
        return {'version': 1, 'language': data['language'],
                # Older preferences gain the new defaults without losing custom colors.
                'durations': validate_durations(data.get('durations', DEFAULTS['durations'])),
                'states': {state: validate_profile(profile) for state, profile in data['states'].items()}}
    except (ValueError, TypeError) as error:
        raise SettingsError('settings_corrupt') from error


def update(current, data, reset=False):
    result = deepcopy(current)
    if reset:
        state = data.get('state')
        if state is None:
            result['states'] = default_settings()['states']
            result['durations'] = default_settings()['durations']
        elif isinstance(state, str) and state in result['states']:
            result['states'][state] = deepcopy(DEFAULTS['states'][state])
            if state in result['durations']:
                result['durations'][state] = DEFAULTS['durations'][state]
        else:
            raise SettingsError('invalid_state')
        return result
    if set(data) == {'language'}:
        if data['language'] not in LANGUAGES:
            raise SettingsError('invalid_language')
        result['language'] = data['language']
        return result
    if set(data) == {'state', 'duration', 'expected_duration'}:
        state = data['state']
        if not isinstance(state, str) or state not in result['durations']:
            raise SettingsError('invalid_state')
        value = validate_duration(data['duration'])
        if data['expected_duration'] != result['durations'][state]:
            raise SettingsError('settings_conflict')
        result['durations'][state] = value
        return result
    if set(data) != {'state', 'profile', 'expected'}:
        raise SettingsError('invalid_profile')
    state = data['state']
    if not isinstance(state, str) or state not in result['states']:
        raise SettingsError('invalid_state')
    if data['expected'] != result['states'][state]:
        raise SettingsError('settings_conflict')
    result['states'][state] = validate_profile(data['profile'])
    return result


def rgb(profile):
    return tuple(int(profile['color'][i:i+2], 16) for i in (1, 3, 5))
