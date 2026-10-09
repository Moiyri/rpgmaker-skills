"""使用对象接口重建公共事件 165。

在仓库根目录运行：
    python3 skills/rpgmaker-events/examples/common165.py

输出计划的操作是 replace_all，应用后会替换公共事件 165 的整段指令。
接口说明直接使用 help(ShowText)、help(If) 或 help(EventList) 查看。
"""
from pathlib import Path
import json
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from event_api import (EventList, ShowText, SetSwitch, If, Switch, Loop,
                       ChangeVariable, Constant, Variable, BreakLoop)


def build_event():
    """返回包含对话、开关、变量、嵌套条件与循环的入门示例。"""
    return EventList([
        ShowText('1', speaker='2'),
        ShowText('3', speaker='4', background='dim', position='middle'),
        SetSwitch(6, on=True),
        If(Switch(6).is_on(), then=[
            Loop([
                ChangeVariable(1, operation='add', value=Constant(1)),
                If(Variable(1).greater_or_equal(10), then=[BreakLoop()]),
            ]),
            SetSwitch(6, on=False),
        ]),
    ])


if __name__ == '__main__':
    event = build_event()
    event.compile()  # Validate operands and control flow before exporting.
    print(json.dumps(event.to_plan({'kind': 'common', 'id': 165}), ensure_ascii=False, indent=2))
