"""临时图片：渐显 → 停留 → 渐隐 → 消除。

用法：python3 picture.py inspected.json --image PictureName > plan.json
inspected.json 来自 events.py inspect；计划追加到该公共事件或地图事件页。
将 plan.json 交给 events.py apply 预览并写入。

图片名相对 img/pictures，不含扩展名。使用未被其他流程占用的图片编号。
默认渐显至 opacity=255（完全不透明）；所有时长以帧计。
"""
import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from event_api import EventList, ShowPicture, MovePicture, Wait, ErasePicture


def build_event(image, *, picture_id=1, x=400, y=300, origin='center',
                scale_x=100, scale_y=100, blend='normal', opacity=255,
                fade_in=60, hold=120, fade_out=60):
    """构造临时图片流程；渐显渐隐保持位置、原点、缩放及混合模式。"""
    appearance = dict(x=x, y=y, origin=origin, scale_x=scale_x,
                      scale_y=scale_y, blend=blend)
    event = EventList([
        ShowPicture(picture_id, image, **appearance, opacity=0),
        MovePicture(picture_id, **appearance, opacity=opacity,
                    duration=fade_in, wait=True),
        Wait(hold),
        MovePicture(picture_id, **appearance, opacity=0,
                    duration=fade_out, wait=True),
        ErasePicture(picture_id),
    ])
    event.compile()
    return event


def build_plan(snapshot, image, **options):
    """根据 inspect 快照生成追加计划，绑定原指令列表指纹。"""
    return build_event(image, **options).to_plan(
        snapshot['target'], op='append',
        expect_list_sha256=snapshot['list_sha256'],
    )


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('snapshot', type=Path)
    parser.add_argument('--image', required=True)
    for name, default in [('picture-id', 1), ('x', 400), ('y', 300),
                          ('scale-x', 100), ('scale-y', 100), ('opacity', 255),
                          ('fade-in', 60), ('hold', 120), ('fade-out', 60)]:
        parser.add_argument('--' + name, type=int, default=default)
    parser.add_argument('--origin', choices=['upper_left', 'center'], default='center')
    parser.add_argument('--blend', choices=['normal', 'add', 'multiply', 'screen'], default='normal')
    options = vars(parser.parse_args())
    snapshot = json.loads(options.pop('snapshot').read_text(encoding='utf-8-sig'))
    print(json.dumps(build_plan(snapshot, **options), ensure_ascii=False, indent=2))
