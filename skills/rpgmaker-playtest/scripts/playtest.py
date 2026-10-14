"""Standard-library client for Debug.js. No third-party packages."""
import argparse
import base64
import json
import uuid
from copy import deepcopy
from pathlib import Path
from connection import CDP

class OperationTimeout(TimeoutError):
    """等待超时，不代表游戏操作终止；用 operation(id) 查询，勿重发。"""
    def __init__(self, operation_id):
        self.operation_id=operation_id
        super().__init__('Operation '+operation_id+' timed out; query operation(id), do not retry the command')

class Game:
    def __init__(self, port=19224):
        self.port=port;self.connection=CDP(port);self._commands=None;self._disconnected=False
    def close(self):
        self.connection.close();self._disconnected=True
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
