"""启动独立 NW.js 测试会话；上下文结束时关闭自己启动的进程。"""
from contextlib import contextmanager
from pathlib import Path
import socket
import subprocess
import tempfile
import time
from playtest import Game

@contextmanager
def launch(project, executable, port=19224, timeout=30):
    """project 为工程根目录，executable 为 nw.exe 或 nwjs 可执行文件。"""
    project=Path(project).resolve(strict=True)
    executable=Path(executable).resolve(strict=True)
    if not (project/'package.json').is_file():raise ValueError('Missing package.json')
    with socket.socket() as probe:probe.bind(('127.0.0.1',port))
    with tempfile.TemporaryDirectory(prefix='rpgmaker-playtest-') as profile:
        process=subprocess.Popen([str(executable),'--remote-debugging-address=127.0.0.1',f'--remote-debugging-port={port}',f'--user-data-dir={profile}',str(project)],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        game=None
        try:
            deadline=time.monotonic()+timeout
            while time.monotonic()<deadline:
                if process.poll() is not None:raise RuntimeError('NW.js exited before connection')
                try:game=Game(port);break
                except (OSError,RuntimeError):time.sleep(.2)
            if game is None:raise TimeoutError('NW.js connection timeout')
            url=game.connection.evaluate('location.href').split('?')[0]+'?test'
            game.connection.request('Page.navigate',{'url':url})
            while time.monotonic()<deadline:
                try:
                    if game.connection.evaluate("typeof SceneManager !== 'undefined' && SceneManager._scene?.isStarted() && typeof DataManager !== 'undefined' && !!DataManager._globalInfo"):break
                except RuntimeError:pass
                time.sleep(.2)
            else:raise TimeoutError('Game startup timeout')
            yield game
        finally:
            if game:game.close()
            if process.poll() is None:
                process.terminate()
                try:process.wait(timeout=10)
                except subprocess.TimeoutExpired:process.kill();process.wait()
