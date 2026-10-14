"""读取选中的事件指令，通过 Debug 调用引擎原版事件测试流程。"""
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from copy import deepcopy
import hashlib
import json
import tempfile
import time
from hooks import Hook, Hooks, HookReport, PROCESS_SIGNALS


def _integer(value, name, minimum=0):
    if type(value) is not int or value < minimum:
        raise ValueError(f'{name} must be an integer >= {minimum}')
    return value


@dataclass(frozen=True)
class EventTestPlan:
    project: Path
    source: dict
    start: int
    end: int
    commands: list
    source_file: str
    source_sha256: str

    def summary(self):
        return {'project': str(self.project), 'source': dict(self.source),
                'range': [self.start, self.end],
                'codes': [c['code'] for c in self.commands]}

    def config(self, save_directory):
        return {**self.summary(), 'commands': deepcopy(self.commands),
                'saveDirectory': str(save_directory)}

    def verify(self):
        path = self.project / 'data' / self.source_file
        if hashlib.sha256(path.read_bytes()).hexdigest() != self.source_sha256:
            raise RuntimeError('Source changed; prepare the event test again: ' + self.source_file)


def prepare_event_test(project, *, map_id=None, event_id=None,
                       common_event_id=None, page=1, commands=None):
    """编号仅定位源指令；page 从 1 起，commands 为原始下标 [start,end)。"""
    project = Path(project).resolve(strict=True)
    if (event_id is None) == (common_event_id is None):
        raise ValueError('Choose event_id or common_event_id')
    page = _integer(page, 'page', 1)
    if common_event_id is not None:
        identifier = _integer(common_event_id, 'common_event_id', 1)
        if map_id is not None or page != 1:
            raise ValueError('Common events do not use map_id or page')
        filename = 'CommonEvents.json'
        origin = {'common_event_id': identifier}
    else:
        _integer(map_id, 'map_id', 1)
        identifier = _integer(event_id, 'event_id', 1)
        filename = f'Map{map_id:03}.json'
        origin = {'map_id': map_id, 'event_id': identifier, 'page': page}
    raw = (project / 'data' / filename).read_bytes()
    data = json.loads(raw)
    entries = data if common_event_id is not None else data['events']
    if identifier >= len(entries) or not entries[identifier] or entries[identifier]['id'] != identifier:
        raise ValueError('Event does not exist')
    event = entries[identifier]
    if common_event_id is not None:
        source = event['list']
    else:
        if page > len(event['pages']):
            raise ValueError('Event page does not exist')
        source = event['pages'][page - 1]['list']
    if commands is None:
        start, end = 0, len(source)
    else:
        if not isinstance(commands, (tuple, list)) or len(commands) != 2:
            raise ValueError('commands must be (start,end)')
        start, end = [_integer(v, 'command index') for v in commands]
        if not 0 <= start < end <= len(source):
            raise ValueError('Invalid command range')
    # Preserve the selected records exactly; the engine handles list exhaustion.
    return EventTestPlan(project, origin, start, end, deepcopy(source[start:end]),
                         filename, hashlib.sha256(raw).hexdigest())


class EventTestSession:
    def __init__(self, game, report):
        self.game, self.report = game, report
        self.report_dir = report.directory
        self.cursor = 0
        self.terminated = False

    def add_hook(self, hook):
        if self.terminated: raise RuntimeError('Session has ended')
        if not isinstance(hook, Hook): raise TypeError('Expected Hook')
        data = hook.to_config()
        if any(h['id'] == data['id'] for h in self.list_hooks()):
            raise ValueError('Duplicate hook: ' + data['id'])
        if data['on'] in PROCESS_SIGNALS:
            self.report.process_hooks[data['id']] = {**data, 'active': True}
            return deepcopy(data)
        return self.game.connection.evaluate('Debug.hooks.add(' + json.dumps(data) + ')')

    def list_hooks(self):
        local = list(self.report.process_hooks.values())
        remote = [] if self.terminated else self.game.connection.evaluate('Debug.hooks.list()')
        return deepcopy(local + remote)

    def remove_hook(self, name):
        if name in self.report.process_hooks:
            del self.report.process_hooks[name]
            return True
        if self.terminated: return False
        return self.game.connection.evaluate('Debug.hooks.remove(' + json.dumps(name) + ')')

    def clear_hooks(self):
        self.report.process_hooks.clear()
        if not self.terminated: self.game.connection.evaluate('Debug.hooks.clear()')

    def poll(self):
        if self.terminated: return self.read_report()
        if self.game.owned_process.poll() is not None:
            self.game.report_owned_exit()
            self.report.status = 'exited'
            self.report.write()
            self.terminated = True
            return self.read_report()
        try:
            self.game._connect()
            result = self.game.connection.evaluate(f'Debug.hooks.poll({self.cursor})', timeout=5)
            for entry in result['events']: self.report.append(entry)
            self.cursor = result['cursor']
            if result['finish']:
                self.report.finish = True
                errors = [e for e in result['events'] if e['signal'] == 'runtime.error']
                self.report.status = 'failed' if errors else 'completed'
                if errors: self.report.error = errors[-1]
            self.report.write()
            if self.report.finish:
                self.game.connection.evaluate('Debug.hooks.clear()', timeout=5)
                self.game.stop_owned_process()
                self.game.close()
                self.terminated = True
        except (OSError, RuntimeError, ConnectionError, TimeoutError) as error:
            self.report.status = 'failed'
            self.report.error = {'origin': 'connection', 'message': str(error)}
            self.report.write()
            self.game.stop_owned_process()
            self.game.close()
            self.terminated = True
        return self.read_report()

    def status(self): return self.poll()

    def wait(self, timeout=30, poll_interval=.2):
        if timeout < 0 or poll_interval <= 0: raise ValueError('Invalid wait duration')
        end = time.monotonic() + timeout
        while True:
            result = self.poll()
            if result['status'] != 'running' or time.monotonic() >= end: return result
            time.sleep(min(poll_interval, max(0, end-time.monotonic())))

    def screenshot(self, path): self.game.screenshot(path)
    def read_report(self):
        return json.loads((self.report_dir / 'session.json').read_text(encoding='utf-8'))


@contextmanager
def launch_event_test(project, executable, *, map_id=None, event_id=None,
                      common_event_id=None, page=1, commands=None, hooks=None,
                      port=19224, timeout=30, report_dir=None):
    """Hooks 在启动前安装；显式配置 event.end/finish 可在事件结束后关闭游戏。"""
    from session import launch, HookFinished
    if hooks is None:
        hooks = Hooks()
        hooks.add(Hook('eventEnd', on='event.end', action='finish', parentId=None))
        hooks.add(Hook('runtimeError', on='runtime.error', action='finish'))
    if not isinstance(hooks, Hooks): raise TypeError('hooks must be Hooks')
    plan = prepare_event_test(project, map_id=map_id, event_id=event_id,
                              common_event_id=common_event_id, page=page, commands=commands)
    directory = Path(report_dir).resolve() if report_dir else Path(tempfile.mkdtemp(prefix='rpgmaker-event-report-'))
    directory.mkdir(parents=True, exist_ok=True)
    plan.verify()
    report = HookReport(directory, hooks, plan.summary())
    test = None
    started = False
    def observe(signal, **data):
        report.emit(signal, **data)
        if report.finish and signal == 'process.start':
            report.status = 'completed'; report.write()
            return True
        return False
    def poll_startup(game):
        nonlocal test
        if test is None:
            try:
                available = game.connection.evaluate("typeof Debug !== 'undefined' && !!Debug.hooks")
            except (OSError, RuntimeError, ConnectionError, TimeoutError): return False
            if not available: return False
            test = EventTestSession(game, report)
        test.poll()
        return test.terminated
    try:
        with tempfile.TemporaryDirectory(prefix='rpgmaker-event-config-') as temporary:
            temp = Path(temporary)
            config = temp / 'event.json'
            config.write_text(json.dumps({**plan.config(temp/'save'), 'hooks': hooks.to_config()}, ensure_ascii=False), encoding='utf-8')
            with launch(plan.project, executable, port, timeout,
                        environment={'RM_EVENT_TEST_CONFIG': str(config)},
                        log_path=directory/'runtime.log', observer=observe, startup_poll=poll_startup) as game:
                game.check_debug()
                if not game.connection.evaluate("!!Debug.hooks"):
                    raise RuntimeError('Installed Debug.js lacks hooks')
                started = True
                if test is None: test = EventTestSession(game, report)
                test.poll()
                try:
                    yield test
                finally:
                    if not test.terminated:
                        test.poll()
                        if not test.terminated:
                            try: game.connection.evaluate('Debug.hooks.clear()', timeout=5)
                            except (OSError, RuntimeError, ConnectionError, TimeoutError): pass
                            report.status = 'cancelled'
                            report.write()
    except HookFinished:
        if test is None: test = EventTestSession(None, report)
        test.terminated = True
        yield test
    except BaseException as error:
        if not started:
            report.emit('startup.failed', message=str(error))
        else:
            report.status = 'failed'; report.error = {'message': str(error)}; report.write()
        raise


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('project')
    parser.add_argument('--map-id', type=int)
    target = parser.add_mutually_exclusive_group(required=True)
    target.add_argument('--event-id', type=int)
    target.add_argument('--common-event-id', type=int)
    parser.add_argument('--page', type=int, default=1)
    parser.add_argument('--start', type=int)
    parser.add_argument('--end', type=int)
    parser.add_argument('--executable')
    parser.add_argument('--run', action='store_true')
    parser.add_argument('--report-dir')
    parser.add_argument('--port', type=int, default=19224)
    args = parser.parse_args()
    if (args.start is None) != (args.end is None): parser.error('--start and --end are used together')
    selection = None if args.start is None else (args.start,args.end)
    options = dict(map_id=args.map_id, event_id=args.event_id,
                   common_event_id=args.common_event_id, page=args.page, commands=selection)
    if not args.run:
        print(json.dumps(prepare_event_test(args.project,**options).summary(),ensure_ascii=False,indent=2))
    else:
        if not args.executable: parser.error('--run requires --executable')
        with launch_event_test(args.project,args.executable,**options,port=args.port,report_dir=args.report_dir) as test:
            print(json.dumps({'report_dir':str(test.report_dir),'status':test.status()},ensure_ascii=False),flush=True)
            while True:
                result = test.wait(timeout=10)
                if result['status'] != 'running':
                    print(json.dumps(result,ensure_ascii=False),flush=True)
                    break
        if result['status'] == 'failed': raise SystemExit(1)
