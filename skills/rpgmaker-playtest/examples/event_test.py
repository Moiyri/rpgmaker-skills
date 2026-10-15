"""python3 event_test.py PROJECT NW_EXECUTABLE COMMON_EVENT_ID --report-dir PATH"""
import argparse
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from event_test import launch_event_test
from hooks import Hook, Hooks

if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('project');parser.add_argument('executable')
    parser.add_argument('common_event_id',type=int)
    parser.add_argument('--report-dir',required=True)
    args=parser.parse_args()
    hooks=Hooks()
    hooks.add(Hook('ready',on='game.ready'))
    hooks.add(Hook('errors',on='runtime.error'))
    hooks.add(Hook('fatalError',on='runtime.error',fatal=True,action='finish'))
    hooks.add(Hook('done',on='event.end',parentId=None,action='finish'))
    hooks.add(Hook('exit',on='process.exit'))
    with launch_event_test(args.project,args.executable,common_event_id=args.common_event_id,report_dir=args.report_dir,hooks=hooks) as game:
        print('用户可在游戏中操作对白与选项；报告位置：',game.report_dir,flush=True)
        result=game.wait(timeout=30)
        while result['status'] in ('pending','running'):
            result=game.wait(timeout=30)
        print(result,flush=True)
