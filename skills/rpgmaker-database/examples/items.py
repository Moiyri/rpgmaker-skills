"""列出、查看或修改已有物品：python items.py PROJECT --id 1 --name 药水 [--write]。"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from database_api import Database, RecoverHP


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('project')
    parser.add_argument('--id', type=int)
    parser.add_argument('--find')
    parser.add_argument('--name')
    parser.add_argument('--recover-hp', type=int, help='追加固定 HP 恢复效果')
    parser.add_argument('--common-event', type=int, help='绑定公共事件')
    parser.add_argument('--write', action='store_true')
    args = parser.parse_args()
    database = Database(args.project)
    if args.find is not None:
        for item in database.items.find(args.find):
            print(f'{item.id:04d} {item.name}')
    elif args.id is None:
        print(database.items.list())
    if args.id is None:
        if args.name is not None or args.recover_hp is not None or args.common_event is not None or args.write:
            parser.error('编辑必须指定 --id')
        return
    item = database.items.get(args.id)
    print(item.describe())
    if args.name is not None:
        item.name = args.name
    if args.recover_hp is not None:
        item.effects.add(RecoverHP(amount=args.recover_hp))
    if args.common_event is not None:
        item.bind_common_event(args.common_event)
    preview = database.preview()
    print(preview)
    if args.write:
        print('事务备份:', database.commit(preview))


if __name__ == '__main__':
    main()
