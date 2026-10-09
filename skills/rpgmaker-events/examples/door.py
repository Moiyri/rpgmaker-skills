"""创建交互式传送门，转向用于切换门动画帧。

用法：python3 door.py PROJECT MAP_ID X Y DEST_MAP DEST_X DEST_Y --image '!Door1' --destination-name 商店 > plan.json
加 --unlock-switch 30 可创建上锁门；钥匙成功使用后开启该开关，进入第 2 页。
再用 map_events.py apply --plan plan.json 预览并写入。

素材使用 down 关闭、left/right/up 逐步打开的四向门图，需核对索引及目标坐标。
从门正面交互。跨地图传送后门在再次进入原地图时恢复；同地图传送需另加关门和关闭穿透流程。
"""
import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from event_api import MapDocument, EventList, ShowText, PlaySE, SetMovementRoute, Route, TransferPlayer


def build_plan(project, map_id, x, y, dest_map, dest_x, dest_y, *, image,
               destination_name, image_index=0, english=False, open_se='Open1',
               transfer_se='Move1', direction='keep', unlock_switch=None,
               locked_text='门锁着，需要一把钥匙。'):
    """创建门事件；unlock_switch 指定时，第 1 页锁门提示，第 2 页开门。"""
    if not destination_name.strip():
        raise ValueError('destination_name must not be empty')
    document = MapDocument(project, map_id)
    name = f'{"Door" if english else "门"}（{destination_name}）'
    event = document.create_event(name, x, y)
    page = event.page(0)
    page.set_image(character_name=image, character_index=image_index,
                   direction='down', pattern=1)
    page.set_movement(type='fixed')
    page.set_options(walking=False, stepping=False, direction_fix=True, through=False)
    page.priority = 'same'
    page.trigger = 'action'
    if unlock_switch is not None:
        page.commands = EventList([ShowText(locked_text)])
        page = event.copy_page(0)
        page.set_conditions(switch1=unlock_switch)
    page.commands = EventList([
        PlaySE(open_se),
        # 平时固定朝向，动画期间临时解除，结束后恢复。
        SetMovementRoute(0, [
            Route.option('direction_fix', False),
            Route.turn('left'),
            Route.wait(3),
            Route.turn('right'),
            Route.wait(3),
            Route.turn('up'),
            Route.option('direction_fix', True),
            Route.option('through', True),
        ], wait=True),
        SetMovementRoute(-1, [Route.move('forward')], skippable=True, wait=True),
        PlaySE(transfer_se),
        TransferPlayer(dest_map, dest_x, dest_y, direction=direction),
    ])
    return document.to_plan()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('project')
    for arg in ('map_id', 'x', 'y', 'dest_map', 'dest_x', 'dest_y'):
        parser.add_argument(arg, type=int)
    parser.add_argument('--image', required=True)
    parser.add_argument('--image-index', type=int, default=0)
    parser.add_argument('--destination-name', required=True)
    parser.add_argument('--english', action='store_true')
    parser.add_argument('--unlock-switch', type=int)
    parser.add_argument('--locked-text', default='门锁着，需要一把钥匙。')
    parser.add_argument('--open-se', default='Open1')
    parser.add_argument('--transfer-se', default='Move1')
    parser.add_argument('--direction', choices=['keep', 'down', 'left', 'right', 'up'], default='keep')
    print(json.dumps(build_plan(**vars(parser.parse_args())), ensure_ascii=False, indent=2))
