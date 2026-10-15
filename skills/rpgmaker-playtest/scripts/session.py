"""启动独立 NW.js 测试会话；上下文结束时关闭自己启动的进程。"""
from contextlib import contextmanager, ExitStack
from pathlib import Path
import socket
import json
import os
import signal
import subprocess
import tempfile
import time
from playtest import Game
from hooks import Hook, Hooks, HookReport

class HookFinished(RuntimeError):
    """A startup hook ended the session before a game connection was available."""

class WindowsJob:
    """Job Object 保留对子进程的所有权，主进程退出后仍能清理。"""
    def __init__(self, process):
        import ctypes
        from ctypes import wintypes as w
        class Basic(ctypes.Structure):
            _fields_=[('per_process',ctypes.c_int64),('per_job',ctypes.c_int64),
                      ('flags',w.DWORD),('min_working',ctypes.c_size_t),('max_working',ctypes.c_size_t),
                      ('active',w.DWORD),('affinity',ctypes.c_size_t),('priority',w.DWORD),('scheduling',w.DWORD)]
        class IO(ctypes.Structure):
            _fields_=[(name,ctypes.c_uint64) for name in ('read_ops','write_ops','other_ops','read_bytes','write_bytes','other_bytes')]
        class Limits(ctypes.Structure):
            _fields_=[('basic',Basic),('io',IO),('process_memory',ctypes.c_size_t),
                      ('job_memory',ctypes.c_size_t),('peak_process',ctypes.c_size_t),('peak_job',ctypes.c_size_t)]
        self.kernel=ctypes.WinDLL('kernel32',use_last_error=True)
        self.kernel.CreateJobObjectW.argtypes=[ctypes.c_void_p,w.LPCWSTR]
        self.kernel.CreateJobObjectW.restype=w.HANDLE
        self.kernel.SetInformationJobObject.argtypes=[w.HANDLE,ctypes.c_int,ctypes.c_void_p,w.DWORD]
        self.kernel.AssignProcessToJobObject.argtypes=[w.HANDLE,w.HANDLE]
        self.kernel.CloseHandle.argtypes=[w.HANDLE]
        self.handle=self.kernel.CreateJobObjectW(None,None)
        if not self.handle:raise ctypes.WinError(ctypes.get_last_error())
        try:
            limits=Limits();limits.basic.flags=0x2000  # JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
            if not self.kernel.SetInformationJobObject(self.handle,9,ctypes.byref(limits),ctypes.sizeof(limits)):
                raise ctypes.WinError(ctypes.get_last_error())
            if not self.kernel.AssignProcessToJobObject(self.handle,int(process._handle)):
                raise ctypes.WinError(ctypes.get_last_error())
        except BaseException:
            self.close();raise
    def close(self):
        if self.handle:
            self.kernel.CloseHandle(self.handle);self.handle=None

def stop_process_tree(process, timeout=5):
    """仅清理本会话启动的独立进程组；Windows 用 taskkill /T。"""
    if os.name=='nt':
        if process.poll() is None:
            subprocess.run(['taskkill','/PID',str(process.pid),'/T','/F'],
                           check=True,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE,timeout=timeout)
        process.wait(timeout=timeout)
        return
    # 子进程可能在主进程退出后继续存在，仍按最初的进程组清理。
    try:os.killpg(process.pid,signal.SIGTERM)
    except ProcessLookupError:pass
    deadline=time.monotonic()+timeout
    while time.monotonic()<deadline:
        process.poll()
        try:os.killpg(process.pid,0)
        except ProcessLookupError:break
        except PermissionError:
            # After SIGTERM, macOS sandboxed NW children can deny group probing.
            if process.poll() is None:raise
            break
        time.sleep(.05)
    else:
        try:os.killpg(process.pid,signal.SIGKILL)
        except ProcessLookupError:pass
    process.wait(timeout=timeout)

@contextmanager
def _launch_process(project, executable, port=19224, timeout=30, *, environment=None, log_path=None, observer=None, startup_poll=None):
    """project 为工程根目录，executable 为 nw.exe 或 nwjs 可执行文件。"""
    project=Path(project).resolve(strict=True)
    executable=Path(executable).resolve(strict=True)
    if not (project/'package.json').is_file():raise ValueError('Missing package.json')
    with socket.socket() as probe:
        probe.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        probe.bind(('127.0.0.1',port))
    env = os.environ.copy()
    if environment:
        env.update(environment)
    with ExitStack() as resources:
        log = resources.enter_context(open(log_path, 'wb')) if log_path else None
        profile = resources.enter_context(tempfile.TemporaryDirectory(prefix='rpgmaker-playtest-'))
        process=subprocess.Popen([str(executable),str(project),'test','--remote-debugging-address=127.0.0.1',f'--remote-debugging-port={port}',f'--user-data-dir={profile}'],start_new_session=(os.name!='nt'),creationflags=(subprocess.CREATE_NEW_PROCESS_GROUP if os.name=='nt' else 0),stdout=log or subprocess.DEVNULL,stderr=log or subprocess.DEVNULL,env=env,cwd=str(project))
        game=None;job=None
        requested=False
        exit_reported=False
        def report_exit():
            nonlocal exit_reported
            if process.poll() is not None and not exit_reported:
                exit_reported=True
                if observer: observer('process.exit', pid=process.pid, code=process.returncode, requested=requested)
        def stop_owned():
            nonlocal requested
            if process.poll() is None: requested=True
            stop_process_tree(process)
            report_exit()
        try:
            if observer and observer('process.start', pid=process.pid):
                raise HookFinished('process.start hook finished the session')
            if os.name=='nt':job=WindowsJob(process)
            deadline=time.monotonic()+timeout
            while time.monotonic()<deadline:
                if process.poll() is not None:raise RuntimeError('NW.js exited before connection')
                try:game=Game(port);break
                except (OSError,RuntimeError):time.sleep(.2)
            if game is None:raise TimeoutError('NW.js connection timeout')
            game.stop_owned_process = stop_owned
            game.owned_process = process
            game.report_owned_exit = report_exit
            while time.monotonic()<deadline:
                if startup_poll and startup_poll(game):
                    raise HookFinished('A hook finished the session during startup')
                if process.poll() is not None:raise RuntimeError('NW.js exited during startup')
                try:
                    status=game.connection.evaluate("({ready: typeof SceneManager !== 'undefined' && (SceneManager._scene instanceof Scene_Title || SceneManager._scene instanceof Scene_Map) && !!SceneManager._scene?.isStarted() && typeof DataManager !== 'undefined' && !!DataManager._globalInfo, test: typeof Utils !== 'undefined' && Utils.isOptionValid('test'), url: location.href, argv: typeof nw !== 'undefined' ? nw.App.argv : null, node: typeof process !== 'undefined' ? process.versions.node : null, error: document.querySelector('#errorPrinter')?.innerText || ''})")
                except RuntimeError:
                    status=None  # 页面仍在初始化，稍后重试；不导航或刷新。
                if status and status.get('error'):
                    raise RuntimeError('Game startup error: ' + status['error'])
                if status and status.get('ready'):
                    if not status.get('test'):raise RuntimeError('NW.js did not enable test mode; startup: '+json.dumps(status,ensure_ascii=False))
                    break
                time.sleep(.2)
            else:raise TimeoutError('Game startup timeout')
            yield game
        finally:
            try:
                if game:game.close()
            finally:
                if process.poll() is None: requested=True
                if job is not None:
                    job.close()
                    process.wait(timeout=10)
                else:
                    stop_process_tree(process)
                report_exit()

@contextmanager
def launch(project, executable, port=19224, timeout=30, *, hooks=None,
           report_dir=None, environment=None, log_path=None, _event_plan=None):
    """Launch a game; optional hooks/reporting use the same Game API as event tests."""
    if hooks is None and report_dir is None and _event_plan is None:
        with _launch_process(project, executable, port, timeout,
                             environment=environment, log_path=log_path) as game:
            yield game
        return
    if hooks is None:
        hooks = Hooks()
        if _event_plan is not None: hooks.add(Hook('eventEnd', on='event.end', action='finish', parentId=None))
        hooks.add(Hook('runtimeError', on='runtime.error', action='record'))
        hooks.add(Hook('fatalError', on='runtime.error', fatal=True, action='finish'))
    if not isinstance(hooks, Hooks): raise TypeError('hooks must be Hooks')
    project = Path(project).resolve()
    directory = Path(report_dir).resolve() if report_dir else Path(tempfile.mkdtemp(prefix='rpgmaker-event-report-'))
    directory.mkdir(parents=True, exist_ok=True)
    if _event_plan is not None: _event_plan.verify()
    report = HookReport(directory, hooks, _event_plan.summary() if _event_plan is not None else {'project': str(project), 'source': 'normal'})
    game = None
    started = False
    def observe(signal, **data):
        report.emit(signal, **data)
        if report.finish and signal == 'process.start':
            report.status = 'finished'; report.write()
            return True
        return False
    def poll_startup(candidate):
        nonlocal game
        if game is None:
            try:
                available = candidate.connection.evaluate("typeof Debug !== 'undefined' && !!Debug.hooks")
            except (OSError, RuntimeError, ConnectionError, TimeoutError): return False
            if not available: return False
            game = candidate
            game._set_report(report)
        game.poll()
        return game.terminated
    try:
        with tempfile.TemporaryDirectory(prefix='rpgmaker-event-config-') as temporary:
            temp = Path(temporary)
            config = temp / 'event.json'
            payload = {'hooks': hooks.to_config()}
            if _event_plan is not None: payload.update(_event_plan.config(temp/'save'))
            config.write_text(json.dumps(payload, ensure_ascii=False), encoding='utf-8')
            with _launch_process(project, executable, port, timeout,
                        environment={**(environment or {}), 'RM_PLAYTEST_CONFIG': str(config)},
                        log_path=log_path or directory/'runtime.log', observer=observe, startup_poll=poll_startup) as game:
                game.check_debug()
                if not game.connection.evaluate("!!Debug.hooks"):
                    raise RuntimeError('Installed Debug.js lacks hooks')
                started = True
                game._set_report(report)
                game.poll()
                try:
                    yield game
                finally:
                    if not game.terminated:
                        game.poll()
                        if not game.terminated:
                            try: game.connection.evaluate('Debug.hooks.clear()', timeout=5)
                            except (OSError, RuntimeError, ConnectionError, TimeoutError): pass
                            report.status = 'cancelled'
                            report.write()
    except HookFinished:
        if game is None:
            game = Game(port, _connect_now=False)
            game._set_report(report)
        game.terminated = True
        yield game
    except BaseException as error:
        if not started:
            report.emit('startup.failed', message=str(error))
        else:
            report.status = 'failed'; report.error = {'message': str(error)}; report.write()
        raise
