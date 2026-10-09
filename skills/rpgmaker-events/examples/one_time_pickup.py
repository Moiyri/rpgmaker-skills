"""创建一次性物品拾取事件。

用法：python3 one_time_pickup.py PROJECT MAP_ID X Y ITEM_ID --image sparkle > plan.json
再使用 map_events.py apply --plan plan.json 预览并写入。

image 使用工程已有的闪光行走图，如 sparkle/light，不含扩展名；按素材选择 index 和 direction。
角色站在物品上按确定键拾取。地图坐标、物品 ID 和素材需事先核对。
"""
import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from event_api import MapDocument, EventList, ChangeItems, Constant, SetSelfSwitch


def build_plan(project, map_id, x, y, item_id, *, image, image_index=0,
               direction='down', amount=1, name='拾取物品'):
    """新建两页拾取事件，返回地图编辑计划；amount 必须为正整数。"""
    if type(amount) is not int or amount < 1:
        raise ValueError('amount must be a positive integer')

    document = MapDocument(project, map_id)
    event = document.create_event(name, x, y)

    # 第 1 页：闪光动画，站在物品上按确定键拾取。
    pickup = event.page(0)
    pickup.set_image(character_name=image, character_index=image_index,
                     direction=direction, pattern=1)
    pickup.set_options(walking=False, stepping=True)
    pickup.priority = 'below'
    pickup.trigger = 'action'
    pickup.commands = EventList([
        ChangeItems(item_id, Constant(amount)),
        SetSelfSwitch('A'),
    ])

    # 第 2 页优先级更高：A 开启后切换到无图像、无指令的空白页。
    hidden = event.add_page()
    hidden.set_conditions(self_switch='A')
    hidden.set_image(character_name='', character_index=0)
    hidden.set_options(walking=False, stepping=False)
    hidden.priority = 'below'
    hidden.trigger = 'action'
    hidden.commands = EventList()

    return document.to_plan()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('project')
    parser.add_argument('map_id', type=int)
    parser.add_argument('x', type=int)
    parser.add_argument('y', type=int)
    parser.add_argument('item_id', type=int)
    parser.add_argument('--image', required=True)
    parser.add_argument('--image-index', type=int, default=0)
    parser.add_argument('--direction', choices=['down', 'left', 'right', 'up'], default='down')
    parser.add_argument('--amount', type=int, default=1)
    parser.add_argument('--name', default='拾取物品')
    print(json.dumps(build_plan(**vars(parser.parse_args())), ensure_ascii=False, indent=2))
