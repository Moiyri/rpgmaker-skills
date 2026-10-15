"""读取选中的事件指令，通过 Debug 调用引擎原版事件测试流程。"""
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from copy import deepcopy
import hashlib
import json


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


@contextmanager
def launch_event_test(project, executable, *, map_id=None, event_id=None,
                      common_event_id=None, page=1, commands=None, hooks=None,
                      port=19224, timeout=30, report_dir=None):
    """Prepare event commands; return the same Game as launch()."""
    from session import launch
    plan = prepare_event_test(project, map_id=map_id, event_id=event_id,
                              common_event_id=common_event_id, page=page, commands=commands)
    with launch(project, executable, port, timeout, hooks=hooks,
                report_dir=report_dir, _event_plan=plan) as game:
        yield game


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
        with launch_event_test(args.project,args.executable,**options,port=args.port,report_dir=args.report_dir) as game:
            print(json.dumps({'report_dir':str(game.report_dir),'status':game.status()},ensure_ascii=False),flush=True)
            while True:
                result = game.wait(timeout=10)
                if result['status'] != 'running':
                    print(json.dumps(result,ensure_ascii=False),flush=True)
                    break
        if result['status'] == 'failed': raise SystemExit(1)
