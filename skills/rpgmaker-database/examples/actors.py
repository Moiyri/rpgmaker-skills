"""读取和修改角色：python actors.py PROJECT --id 1 --nickname 旅行者 [--write]。"""
import argparse
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from database_api import Database


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('project');parser.add_argument('--id',type=int)
    parser.add_argument('--nickname');parser.add_argument('--write',action='store_true')
    args=parser.parse_args();db=Database(args.project)
    if args.id is None:
        if args.nickname is not None or args.write:parser.error('修改需指定 --id')
        print(db.actors.list());return
    actor=db.actors.get(args.id);print(actor.describe())
    if args.nickname is not None:actor.nickname=args.nickname
    preview=db.preview();print(preview)
    if args.write:print('事务备份:',db.commit(preview))


if __name__=='__main__':main()
