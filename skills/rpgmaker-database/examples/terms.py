"""用语查询和修改：python terms.py PROJECT messages --key saveMessage --text 请选择存档 [--write]。"""
import argparse
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from database_api import Database


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('project');parser.add_argument('group',choices=['basic','params','commands','messages'])
    parser.add_argument('--key');parser.add_argument('--text');parser.add_argument('--write',action='store_true')
    args=parser.parse_args();db=Database(args.project);group=getattr(db.terms,args.group)
    print(group.list())
    if args.text is not None:
        if args.key is None:parser.error('--text 需要 --key')
        key=args.key if args.group=='messages' else int(args.key)
        group.set(key,args.text)
    preview=db.preview();print(preview)
    if args.write:print('事务备份:',db.commit(preview))


if __name__=='__main__':main()
