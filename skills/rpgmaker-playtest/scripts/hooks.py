"""Typed hook declarations and report collection; no command registry involved."""
from copy import deepcopy
import json
import time

FIELDS = {
    'process.start': {'pid'}, 'game.ready': set(),
    'startup.failed': {'message'}, 'runtime.error': {'origin', 'fatal'},
    'runtime.warning': {'origin'}, 'process.exit': {'code', 'requested'},
    'event.start': {'mapId', 'eventId', 'commonEventId', 'executionId', 'parentId'},
    'event.call': {'mapId', 'eventId', 'commonEventId', 'executionId', 'parentId'},
    'event.command': {'mapId', 'eventId', 'commonEventId', 'executionId', 'parentId', 'index', 'sourceIndex', 'code', 'phase'},
    'event.end': {'mapId', 'eventId', 'commonEventId', 'executionId', 'parentId'},
    'variable.change': {'id', 'value'}, 'switch.change': {'id', 'value'},
}
PROCESS_SIGNALS = {'process.start', 'startup.failed', 'process.exit'}

class Hook:
    def __init__(self, name, *, on, action='record', once=False, **match):
        if not isinstance(name, str) or not name.strip():
            raise ValueError('Hook name must be a nonempty string')
        if on not in FIELDS: raise ValueError('Unknown signal: ' + str(on))
        if action not in ('record', 'finish'): raise ValueError('Unknown action')
        if type(once) is not bool: raise ValueError('once must be bool')
        if match.keys() - FIELDS[on]: raise ValueError('Unsupported filter for ' + on)
        for key, value in match.items():
            if key in ('id', 'pid', 'eventId', 'commonEventId', 'executionId', 'index', 'sourceIndex', 'code', 'mapId', 'parentId'):
                if value is not None and type(value) is not int: raise ValueError(key + ' must be an integer')
            if key == 'phase' and value not in ('before', 'after'): raise ValueError('Invalid phase')
            if key in ('requested', 'fatal') and type(value) is not bool: raise ValueError(key + ' must be bool')
            if on == 'switch.change' and key == 'value' and type(value) is not bool: raise ValueError('Switch value must be bool')
        json.dumps(match, allow_nan=False)
        self._data = {'id': name, 'on': on, 'action': action, 'once': once, 'match': deepcopy(match)}

    def to_config(self): return deepcopy(self._data)

class Hooks:
    def __init__(self): self._items = {}
    def add(self, hook):
        if not isinstance(hook, Hook): raise TypeError('Expected Hook')
        data = hook.to_config()
        if data['id'] in self._items: raise ValueError('Duplicate hook: ' + data['id'])
        self._items[data['id']] = data
        return hook
    def remove(self, name): return self._items.pop(name, None) is not None
    def clear(self): self._items.clear()
    def to_config(self): return deepcopy(list(self._items.values()))

class HookReport:
    def __init__(self, directory, hooks, target):
        self.directory = directory
        self.target = target
        self.process_hooks = {h['id']: {**h, 'active': True} for h in hooks.to_config() if h['on'] in PROCESS_SIGNALS}
        self.status = 'running'
        self.finish = False
        self.error = None
        self.started = time.time()
        self.seq = 0
        self.errors = 0
        self.warnings = 0
        self.end_reason = None
        self.triggered_hook = []
        self.process = None
        self.write()

    def append(self, entry):
        self.seq += 1
        entry = {**entry, 'seq': self.seq}
        if entry['signal'] == 'runtime.error': self.errors += 1
        if entry['signal'] == 'runtime.warning': self.warnings += 1
        with (self.directory / 'events.jsonl').open('a', encoding='utf-8') as stream:
            stream.write(json.dumps(entry, ensure_ascii=False) + '\n')
            stream.flush()

    def emit(self, signal, **data):
        hits = []
        for hook in self.process_hooks.values():
            if hook['active'] and hook['on'] == signal and all(type(data.get(k)) is type(v) and data.get(k) == v for k,v in hook['match'].items()):
                hits.append(hook['id'])
                if hook['once']: hook['active'] = False
                if hook['action'] == 'finish': self.finish = True
        # Process lifecycle always retained to diagnose startup/exit, even without matching hooks.
        self.append({'time': int(time.time()*1000), 'signal': signal, 'hooks': hits, **data})
        if signal == 'startup.failed':
            self.status = 'failed'; self.error = data; self.end_reason = 'startup.failed'
        if signal == 'process.exit':
            self.process = {'exitCode': data['code'], 'closedByTool': data['requested']}
            if self.status == 'running': self.status = 'exited'; self.end_reason = 'process.exit'
        self.write()

    def write(self):
        path = self.directory / 'session.json'
        tmp = path.with_suffix('.tmp')
        tmp.write_text(json.dumps({'test': self.target, 'status': self.status, 'finish': self.finish, 'error': self.error, 'endReason': self.end_reason,
            'triggeredHook': self.triggered_hook, 'durationMs': round((time.time()-self.started)*1000),
            'errors': self.errors, 'warnings': self.warnings, 'process': self.process}, ensure_ascii=False, indent=2), encoding='utf-8')
        tmp.replace(path)
