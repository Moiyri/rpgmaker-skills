"""生成公共事件 167 的追加计划。

运行本示例，将输出传给 events.py apply 预览，再使用预览指纹写入。
角色 0001 在队伍中时，开启开关 1 并调用公共事件 100。
"""
from pathlib import Path
import json
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from event_api import EventList, If, Actor, SetSwitch, CommonEvent


def build_event() -> EventList:
    """返回包含角色入队条件的测试事件片段。"""
    return EventList([
        If(Actor(1).in_party(), then=[
            SetSwitch(1, on=True),
            CommonEvent(100),
        ]),
    ])


if __name__ == '__main__':
    event = build_event()
    event.compile()
    print(json.dumps(event.to_plan({'kind': 'common', 'id': 167}, op='append'),
                     ensure_ascii=False, indent=2))
