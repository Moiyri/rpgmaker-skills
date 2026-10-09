"""系统设置：python system.py PROJECT [--title 名称] [--write]。"""
import argparse
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from database_api import Database


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('project');parser.add_argument('--title');parser.add_argument('--write',action='store_true')
    args=parser.parse_args();db=Database(args.project)
    print(db.system.describe())
    if args.title is not None:db.system.game_title=args.title
    preview=db.preview();print(preview)
    if args.write:print('事务备份:',db.commit(preview))


if __name__=='__main__':main()
