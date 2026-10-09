"""Standard-library client for Debug.js. No third-party packages."""
import argparse
import base64
import json
from pathlib import Path
from connection import CDP

class Game:
    def __init__(self, port=19224): self.connection=CDP(port)
    def close(self): self.connection.close()
    def commands(self): return self.connection.evaluate('Debug.commands()')
    def help(self,name):
        for command in self.commands():
            if command['name']==name:return command
        raise ValueError('Unknown command: '+name)
    def call(self,name,**args):
        self.help(name)
        payload=json.dumps({'name':name,'args':args},ensure_ascii=True)
        return self.connection.evaluate('(({name,args}) => Debug[name](args))('+payload+')')
    def screenshot(self,path):
        result=self.connection.request('Page.captureScreenshot',{'format':'png'})
        Path(path).write_bytes(base64.b64decode(result['data']))
    def check_debug(self):
        """验证已安装的 Debug；不自动注入或安装插件。"""
        if not self.connection.evaluate("typeof Debug !== 'undefined' && Debug.version === 1"):
            raise RuntimeError('Debug.js version 1 required; install only when requested, then start test mode')
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
