"""编辑已有地图事件并输出计划。

用法：python3 map_event.py PROJECT MAP_ID EVENT_ID
示例修改名称和第 1 页设置，并复制出独立开关 A 生效的第 2 页。
输出交给 map_events.py apply 预览，确认范围后使用预览指纹写入。
"""
import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from event_api import MapDocument, ShowText, SetSelfSwitch


def build_plan(project, map_id, event_id):
    """在内存中修改指定事件，返回带原地图快照的计划。"""
    document=MapDocument(project,map_id)
    event=document.event(event_id)
    event.name='交互示例'
    page=event.page(0)
    page.set_conditions(switch1=1)
    page.priority='same'
    page.trigger='action'
    page.commands.append(ShowText('第一次交互'))
    page.commands.append(SetSelfSwitch('A'))
    second=event.copy_page(0)
    second.set_conditions(self_switch='A')
    from event_api import EventList
    second.commands=EventList([ShowText('已完成交互')])
    return document.to_plan()


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('project');parser.add_argument('map_id',type=int);parser.add_argument('event_id',type=int)
    args=parser.parse_args()
    print(json.dumps(build_plan(args.project,args.map_id,args.event_id),ensure_ascii=False,indent=2))
