"""物品使用公共事件，参考工程公共事件 1204。

按实际物品替换位置、开关、提示和成功演出；公共事件按物品命名。
由物品使用触发，不重复检查触发物品的持有数量。
成功才扣除物品时，物品数据库 Consumable 设为 No，效果登记调用该公共事件。
"""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from event_api import (EventList, If, ScriptCondition, Switch, ShowText, Comment,
                       ChangeItems, Constant, Label, JumpToLabel, ExitEvent)


def build_event() -> EventList:
    """正确位置检查使用条件；其他位置处理特殊引导或一般失败提示。"""
    return EventList([
        If(ScriptCondition(
            '$gameMap.mapId() === 2 && $gamePlayer.x === 7 && $gamePlayer.y === 9 && $gamePlayer.direction() === 8 && $gameMap.event(2) && $gameMap.event(2).pos($gamePlayer.x, $gamePlayer.y - 1)'
        ), then=[
            If(Switch(90).is_off(), [
                # 判断物品是否满足使用条件，一般检查条件为 OFF 后单独处理或直接跳转。
                JumpToLabel('Use Fail'),
            ]),
            If(Switch(28).is_off(), [
                ShowText('【特殊引导】你没有拿到XXX'),
                # 出现特殊引导后直接退出事件处理，而不是跳转到一般失败提示。
                ExitEvent(),
            ]),
            Comment('==================== 满足使用条件 ===================='),
            ChangeItems(2, Constant(1), operation='sub'),
            ShowText('【提示性语句】打开了某处的门'),
            ShowText('【此处继续演出流程，直到演出结束】'),
            # 成功分支自然结束，不需要额外跳转或退出指令。
        ], otherwise=[
            If(ScriptCondition(
                '$gameMap.mapId() === 3 && $gamePlayer.x === 5 && $gamePlayer.y === 4 && $gamePlayer.direction() === 8 && $gameMap.event(2) && $gameMap.event(2).pos($gamePlayer.x, $gamePlayer.y - 1)'
            ), [
                # 使用时改成实际交互对象或情境，例如“对书架使用”；不要照抄“特殊事件”。
                Comment('==================== 对【特殊事件】使用 ===================='),
                ShowText('【提示性语句】特殊引导'),
                # 特殊处理结束后退出事件，避免继续显示一般失败提示。
                ExitEvent(),
            ]),
            # 此处可叠加多个特殊处理。
            Label('Use Fail'),
            # 一般引导；也可替换为调用提示公共事件。
            ShowText('该物品不能使用。'),
        ]),
    ])


if __name__ == '__main__':
    print(build_event().compile())
