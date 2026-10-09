"""物品管理：python manage_items.py PROJECT create 药水 [--id 91] [--write]。"""
import argparse
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from database_api import Database


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('project')
    sub = parser.add_subparsers(dest='action', required=True)
    create = sub.add_parser('create'); create.add_argument('name')
    create.add_argument('--id', type=int)
    create.add_argument('--write', action='store_true')
    clear = sub.add_parser('clear'); clear.add_argument('id', type=int)
    clear.add_argument('--write', action='store_true')
    refs = sub.add_parser('references'); refs.add_argument('id', type=int)
    args = parser.parse_args()
    database = Database(args.project)
    if args.action == 'references':
        print(database.items.references(args.id)); return
    if args.action == 'create':
        item = database.items.create(args.name, id=args.id)
    else:
        print(database.items.references(args.id))
        item = database.items.clear(args.id)
    print(f'目标物品：{item.id:04d} {item.name}')
    preview = database.preview()
    print(preview)
    if args.write:
        print('事务备份:', database.commit(preview))


if __name__ == '__main__':
    main()
