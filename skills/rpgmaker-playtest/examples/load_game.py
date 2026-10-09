"""python3 load_game.py PROJECT NW_EXECUTABLE --slot 2 --screenshot loaded.png"""
import argparse
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from session import launch

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('project');p.add_argument('executable');p.add_argument('--slot',type=int,default=2)
    p.add_argument('--port',type=int,default=19224);p.add_argument('--screenshot',default='loaded.png')
    a=p.parse_args()
    with launch(a.project,a.executable,a.port) as game:
        game.check_debug()
        for command in game.commands():print(command['name'],command['description'])
        print(game.help('loadGame'))
        print(game.call('loadGame',slot=a.slot))
        game.screenshot(a.screenshot)
