"""Standard-library client for Debug.js. No third-party packages."""
import argparse
import base64
import json
import uuid
import time
from hooks import Hook, PROCESS_SIGNALS
from copy import deepcopy
from pathlib import Path
from connection import CDP

class OperationTimeout(TimeoutError):
    """等待超时，不代表游戏操作终止；用 operation(id) 查询，勿重发。"""
    def __init__(self, operation_id):
        self.operation_id=operation_id
        super().__init__('Operation '+operation_id+' timed out; query operation(id), do not retry the command')

class Game:
    def __init__(self, port=19224, *, _connect_now=True):
        self.port=port;self.connection=CDP(port) if _connect_now else None;self._commands=None;self._disconnected=False
        self.report=None; self.report_dir=None; self.connected=False; self.terminated=False
    def _set_report(self, report):
        self.report=report; self.report_dir=report.directory
    def close(self):
        if self.connection is not None: self.connection.close()
        self._disconnected=True; self.connected=False
    def _connect(self):
        if self._disconnected:
            self.connection=CDP(self.port);self._disconnected=False;self._commands=None
    def commands(self, *, refresh=False):
        self._connect()
        if refresh or self._commands is None:
            self._commands=self.connection.evaluate('Debug.commands()')
        return deepcopy(self._commands)
    def help(self,name):
        for command in self.commands():
            if command['name']==name:return command
        raise ValueError('Unknown command: '+name+'; commands(refresh=True) after registering new commands')
    def call(self,name,*,timeout=45,**args):
        if timeout<=0:raise ValueError('timeout must be positive')
        self.help(name)
        operation_id=uuid.uuid4().hex
        payload=json.dumps({'id':operation_id,'name':name,'args':args},ensure_ascii=True)
        try:
            return self.connection.evaluate('(({id,name,args}) => Debug.track(id,name,args))('+payload+')',timeout=timeout)
        except TimeoutError as exc:
            self.close()
            raise OperationTimeout(operation_id) from exc
        except (ConnectionError,OSError):
            self.close();raise
        except RuntimeError:
            self._commands=None;raise
    def operation(self,operation_id):
        """超时后重新连接并查询；unknown 表示页面已重载、记录被清理或请求未到达，不能视为撤销。"""
        self._connect()
        return self.connection.evaluate('Debug.operation('+json.dumps(operation_id)+')')
    def screenshot(self,path):
        result=self.connection.request('Page.captureScreenshot',{'format':'png'})
        Path(path).write_bytes(base64.b64decode(result['data']))
    def check_debug(self):
        """验证已安装的 Debug；不自动注入或安装插件。"""
        if not self.connection.evaluate("typeof Debug !== 'undefined' && ['commands','track','operation'].every(name => typeof Debug[name] === 'function')"):
            raise RuntimeError('Debug commands/track/operation interfaces required; check plugin enablement and test mode')
    def add_hook(self, hook):
        if self.report is None: raise RuntimeError('Use launch with hooks/report_dir to collect a report')
        if self.terminated: raise RuntimeError('Session has ended')
        if not isinstance(hook, Hook): raise TypeError('Expected Hook')
        data = hook.to_config()
        if any(h['id'] == data['id'] for h in self.list_hooks()):
            raise ValueError('Duplicate hook: ' + data['id'])
        if data['on'] in PROCESS_SIGNALS:
            self.report.process_hooks[data['id']] = {**data, 'active': True}
            return deepcopy(data)
        return self.connection.evaluate('Debug.hooks.add(' + json.dumps(data) + ')')

    def list_hooks(self):
        if self.report is None: raise RuntimeError('Use launch with hooks/report_dir to collect a report')
        local = list(self.report.process_hooks.values())
        remote = [] if self.terminated else self.connection.evaluate('Debug.hooks.list()')
        return deepcopy(local + remote)

    def remove_hook(self, name):
        if self.report is None: raise RuntimeError('Use launch with hooks/report_dir to collect a report')
        if name in self.report.process_hooks:
            del self.report.process_hooks[name]
            return True
        if self.terminated: return False
        return self.connection.evaluate('Debug.hooks.remove(' + json.dumps(name) + ')')

    def clear_hooks(self):
        if self.report is None: raise RuntimeError('Use launch with hooks/report_dir to collect a report')
        self.report.process_hooks.clear()
        if not self.terminated: self.connection.evaluate('Debug.hooks.clear()')

    def _attach(self):
        self._connect()
        if self.connected: return
        connection = self.connection
        def receive(params):
            if params.get('name') != '__rmHookRecord': return
            entry = json.loads(params['payload'])
            self.report.append(entry)
            if entry.get('finish') and not self.report.finish:
                self.report.finish = True
                self.report.status = 'failed' if entry['signal'] == 'runtime.error' else 'finished'
                self.report.end_reason = 'error' if entry['signal'] == 'runtime.error' else 'hook'
                self.report.triggered_hook = entry.get('finishHooks', [])
                if entry['signal'] == 'runtime.error': self.report.error = entry
            self.report.write()
        connection.on('Runtime.bindingCalled', receive)
        connection.request('Runtime.addBinding', {'name': '__rmHookRecord'})
        connection.evaluate("Debug.hooks.connect('__rmHookRecord')")
        self.connected = True

    def poll(self, timeout=0):
        if self.report is None: raise RuntimeError('Use launch with hooks/report_dir to collect a report')
        if self.terminated: return self.read_report()
        try:
            self._attach()
            # Drain delivered events, then wait only for socket activity.
            self.connection.receive_event(timeout)
            while self.connection.receive_event(0):
                if self.report.finish: break
            if self.report.finish:
                self.report.write()
                self.connection.evaluate('Debug.hooks.clear(); Debug.hooks.disconnect()', timeout=5)
                self.stop_owned_process()
                self.close()
                self.terminated = True
            elif self.owned_process.poll() is not None:
                self.report_owned_exit()
                self.terminated = True
        except (OSError, RuntimeError, ConnectionError, TimeoutError) as error:
            # A user closing NW.js may close CDP shortly before the process exits.
            import subprocess
            try: self.owned_process.wait(timeout=.5)
            except subprocess.TimeoutExpired:
                self.report.status = 'failed'
                self.report.end_reason = 'connection'
                self.report.error = {'origin': 'connection', 'message': str(error)}
                self.report.write()
                self.stop_owned_process()
            else: self.report_owned_exit()
            self.close()
            self.terminated = True
        self.report.write()
        return self.read_report()

    def status(self): return self.poll()

    def wait(self, timeout=None, poll_interval=.2):
        if (timeout is not None and timeout < 0) or poll_interval <= 0: raise ValueError('Invalid wait duration')
        end = float('inf') if timeout is None else time.monotonic() + timeout
        while True:
            result = self.poll(timeout=min(poll_interval,max(0,end-time.monotonic())))
            if result['status'] != 'running' or time.monotonic() >= end: return result

    def read_report(self):
        if self.report is None: raise RuntimeError('Use launch with hooks/report_dir to collect a report')
        return json.loads((self.report_dir / 'session.json').read_text(encoding='utf-8'))


    def __enter__(self): return self
    def __exit__(self, *exc): self.close()

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--port',type=int,default=19224);parser.add_argument('--slot',type=int);parser.add_argument('--screenshot')
    args=parser.parse_args();game=Game(args.port)
    try:
        game.check_debug()
        for c in game.commands():print(c['name'],json.dumps(c['parameters'],ensure_ascii=False),c['description'])
        if args.slot is not None:print(json.dumps(game.call('loadGame',slot=args.slot),ensure_ascii=False))
        if args.screenshot:game.screenshot(args.screenshot)
    finally:game.close()
