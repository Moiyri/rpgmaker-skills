"""Background manual-test collector. Execution scripts live in PROJECT/test/."""
from pathlib import Path
from datetime import datetime
import json
import os
import subprocess
import sys
import tempfile
import time
import traceback

ENV_REPORT = 'RM_MANUAL_REPORT'

def _write(path, data):
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
    temporary.replace(path)

def read_report(directory):
    """Read persisted state without connecting to the game or polling it."""
    directory = Path(directory).resolve(strict=True)
    result = {'report_dir': str(directory)}
    for name in ('collector', 'session'):
        path = directory / (name + '.json')
        result[name] = json.loads(path.read_text(encoding='utf-8')) if path.exists() else None
    return result

def start_manual(project, script, *, timeout=45):
    """Start a detached script, wait only for startup acknowledgement, return report path."""
    if timeout <= 0: raise ValueError('timeout must be positive')
    project = Path(project).resolve(strict=True)
    script = Path(script).resolve(strict=True)
    if not script.is_file() or script.suffix != '.py' or not script.is_relative_to(project / 'test'):
        raise ValueError('Execution script must be a Python file inside PROJECT/test/')
    reports = project / 'test/reports'
    reports.mkdir(parents=True, exist_ok=True)
    directory = Path(tempfile.mkdtemp(prefix=script.stem+'-'+datetime.now().strftime('%Y%m%d-%H%M%S')+'-', dir=reports))
    _write(directory/'collector.json', {'status':'starting','script':str(script)})
    env = os.environ.copy()
    env[ENV_REPORT] = str(directory)
    flags = 0
    if os.name == 'nt': flags = subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP
    try:
        with (directory/'collector.log').open('wb') as log:
            process = subprocess.Popen([sys.executable, '-u', str(script)], cwd=project,
                env=env, stdin=subprocess.DEVNULL, stdout=log, stderr=log,
                start_new_session=os.name != 'nt', creationflags=flags, close_fds=True)
        _write(directory/'launch.json', {'pid':process.pid,'script':str(script),'project':str(project)})
    except BaseException as error:
        _write(directory/'collector.json', {'status':'failed','error':str(error)})
        raise
    deadline = time.monotonic() + timeout
    while True:
        report = read_report(directory)
        if report['collector']['status'] != 'starting': return report
        code = process.poll()
        if code is not None:
            # Re-read after exit to avoid replacing a final worker acknowledgement.
            report = read_report(directory)
            if report['collector']['status'] == 'starting':
                _write(directory/'collector.json', {'status':'failed','pid':process.pid,
                    'error':'Execution script exited before collector acknowledgement','code':code})
            return read_report(directory)
        if time.monotonic() >= deadline:
            # A timeout is not startup success; retain the locator for inspection/cleanup.
            report['startup_wait_expired'] = True
            return report
        time.sleep(.1)

def collect_manual(open_session):
    """Called by the detached script. open_session(report_dir) returns an owned session context."""
    value = os.environ.get(ENV_REPORT)
    if not value: raise RuntimeError('Start this script through start_manual or the manual_test.py start CLI')
    directory = Path(value).resolve(strict=True)
    path = directory/'collector.json'
    def acknowledge(status, **details):
        _write(path, {'status':status,'pid':os.getpid(),'updated':time.time(),**details})
    acknowledge('starting')
    try:
        with open_session(directory) as game:
            current = game.poll()
            if current['status'] == 'running':
                acknowledge('running')
                while current['status'] == 'running':
                    current = game.wait(timeout=1)
        # Written only after the session context has closed its processes/temp files.
        acknowledge('finished', result=game.read_report()['status'])
        return read_report(directory)
    except BaseException as error:
        acknowledge('failed', error=str(error))
        traceback.print_exc()
        raise

if __name__ == '__main__':
    import argparse
    parser=argparse.ArgumentParser(description=__doc__)
    sub=parser.add_subparsers(dest='command',required=True)
    start=sub.add_parser('start')
    start.add_argument('project'); start.add_argument('script')
    start.add_argument('--timeout',type=float,default=45)
    report=sub.add_parser('report'); report.add_argument('directory')
    args=parser.parse_args()
    if args.command == 'start': result=start_manual(args.project,args.script,timeout=args.timeout)
    else: result=read_report(args.directory)
    print(json.dumps(result,ensure_ascii=False,indent=2))
