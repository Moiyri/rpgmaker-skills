"""启动独立 NW.js 测试会话；上下文结束时关闭自己启动的进程。"""
from contextlib import contextmanager
from pathlib import Path
import socket
import os
import signal
import subprocess
import tempfile
import time
from playtest import Game

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
        time.sleep(.05)
    else:
        try:os.killpg(process.pid,signal.SIGKILL)
        except ProcessLookupError:pass
    process.wait(timeout=timeout)

@contextmanager
def launch(project, executable, port=19224, timeout=30):
    """project 为工程根目录，executable 为 nw.exe 或 nwjs 可执行文件。"""
    project=Path(project).resolve(strict=True)
    executable=Path(executable).resolve(strict=True)
    if not (project/'package.json').is_file():raise ValueError('Missing package.json')
    with socket.socket() as probe:probe.bind(('127.0.0.1',port))
    with tempfile.TemporaryDirectory(prefix='rpgmaker-playtest-') as profile:
        process=subprocess.Popen([str(executable),'--remote-debugging-address=127.0.0.1',f'--remote-debugging-port={port}',f'--user-data-dir={profile}',str(project),'test'],start_new_session=(os.name!='nt'),creationflags=(subprocess.CREATE_NEW_PROCESS_GROUP if os.name=='nt' else 0),stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        game=None;job=None
        try:
            if os.name=='nt':job=WindowsJob(process)
            deadline=time.monotonic()+timeout
            while time.monotonic()<deadline:
                if process.poll() is not None:raise RuntimeError('NW.js exited before connection')
                try:game=Game(port);break
                except (OSError,RuntimeError):time.sleep(.2)
            if game is None:raise TimeoutError('NW.js connection timeout')
            while time.monotonic()<deadline:
                if process.poll() is not None:raise RuntimeError('NW.js exited during startup')
                try:
                    status=game.connection.evaluate("({ready: typeof SceneManager !== 'undefined' && !!SceneManager._scene?.isStarted() && typeof DataManager !== 'undefined' && !!DataManager._globalInfo, test: typeof Utils !== 'undefined' && Utils.isOptionValid('test')})")
                except RuntimeError:
                    status=None  # 页面仍在初始化，稍后重试；不导航或刷新。
                if status and status.get('ready'):
                    if not status.get('test'):raise RuntimeError('NW.js did not enable test mode; check startup arguments')
                    break
                time.sleep(.2)
            else:raise TimeoutError('Game startup timeout')
            yield game
        finally:
            try:
                if game:game.close()
            finally:
                if job is not None:
                    job.close()
                    process.wait(timeout=10)
                else:
                    stop_process_tree(process)
