"""将引擎指令解码成可编辑对象。"""
from __future__ import annotations

from copy import deepcopy
from typing import Any, TYPE_CHECKING
from . import compiler as core
from .commands.message import ShowChoices, ShowText
from .commands.game_progression import SetSwitch, ChangeVariable, SetSelfSwitch, StartTimer, StopTimer
from .commands.flow_control import Label, JumpToLabel, ExitEvent, If, Loop, BreakLoop, CommonEvent, Comment
from .commands.party import ChangeGold, ChangeItems
from .commands.timing import Wait
from .commands.map_commands import EraseEvent
from .commands.advanced import Script, PluginCommand
from .commands.opaque import OpaqueCommand
from .commands.movement import TransferPlayer
from .conditions import SwitchCondition, VariableCondition, ScriptCondition, SelfSwitchCondition, SelfSwitch, DirectionCondition, Character, ItemCondition, Item, ButtonCondition, Button, ActorCondition, Actor, Switch, Variable
from .operands import Constant, VariableValue, RandomValue, ScriptValue
if TYPE_CHECKING:
    from .event_list import EventList

def decode_commands(commands: list[dict[str, Any]]) -> EventList:
    """将完整事件数组还原成嵌套对象，未知指令块保留原始数据。"""
    from .event_list import EventList
    ranges = {n['index']: n for n in core.index_commands(commands)}

    def decode(start, stop):
        result = EventList()
        while start < stop:
            entry = ranges.get(start)
            core.require(entry is not None and entry['end'] <= stop, 'Invalid block boundary')
            end = entry['end']; raw = deepcopy(commands[start:end])
            params = raw[0]['parameters']; code = raw[0]['code']
            node = None
            try:
                if code == 101:
                    node = ShowText.from_commands(raw)
                elif code == 121:
                    core.require(len(params) == 3 and type(params[2]) is int and params[2] in (0, 1), 'Unknown switch shape')
                    node = SetSwitch(params[0], params[2] == 0, params[1])
                elif code == 122:
                    value = _decode_operand(params[3:])
                    node = ChangeVariable(params[0], core.OPERATIONS[params[2]], value, params[1])
                elif code == 123:
                    core.require(len(params) == 2 and type(params[1]) is int and params[1] in (0, 1), 'Unknown self switch shape')
                    node = SetSelfSwitch(params[0], params[1] == 0)
                elif code == 124:
                    if len(params) == 2 and type(params[0]) is int and params[0] == 0:
                        node = StartTimer(params[1])
                    elif len(params) == 1 and type(params[0]) is int and params[0] == 1:
                        node = StopTimer()
                elif code in (108, 355):
                    text = '\n'.join(c['parameters'][0] for c in raw)
                    node = Comment(text) if code == 108 else Script(text)
                elif code in (125, 126):
                    offset = 1 if code == 126 else 0
                    operation = ['add', 'sub'][params[offset]]
                    value = _decode_operand(params[offset+1:])
                    node = ChangeGold(value, operation) if code == 125 else ChangeItems(params[0], value, operation)
                elif code in (202,203,204,205,206):
                    from .commands.movement import decode_movement
                    node = decode_movement(code, params)
                elif code == 201:
                    core.require(len(params) == 6 and type(params[0]) is int and params[0] in (0, 1), 'Unknown transfer shape')
                    values = [VariableValue(v) for v in params[1:4]] if params[0] else params[1:4]
                    node = TransferPlayer(*values, direction={0:'keep',2:'down',4:'left',6:'right',8:'up'}[params[4]], fade=['black','white','none'][params[5]])
                elif code in (231,232,233,234,235):
                    from .commands.picture import decode_picture
                    node = decode_picture(code, params)
                elif code in (303,351,352,353,354):
                    from .commands.scene_control import decode_scene
                    node = decode_scene(code, params)
                elif code in (241, 242, 243, 244, 245, 246, 249, 250, 251, 261):
                    from .commands.audio_video import decode_audio_video
                    node = decode_audio_video(code, params)
                elif code in (221, 222, 223, 224, 225, 236):
                    from .commands.screen import decode_screen
                    node = decode_screen(code, params)
                elif code == 230:
                    node = Wait(params[0])
                elif code == 214:
                    node = EraseEvent()
                elif code == 357:
                    node = PluginCommand.from_commands(raw)
                elif code in (118,119):
                    node = (Label if code==118 else JumpToLabel)(*params)
                elif code == 115:
                    node = ExitEvent()
                elif code == 102:
                    core.require(len(params)==5 and params[3:]==[2,0], 'Unsupported choice display')
                    markers=[i for i in range(start+1,end-1) if commands[i]['indent']==entry['indent'] and commands[i]['code'] in (402,403)]
                    core.require(len(markers)==len(params[0]), 'Unsupported choice branches')
                    choices=[]
                    for i,m in enumerate(markers):
                        stop=markers[i+1] if i+1<len(markers) else end-1
                        core.require(commands[m]['code']==402 and commands[m]['parameters']==[i,params[0][i]], 'Unexpected choice branch')
                        core.require(commands[stop-1]==core.command(0,entry['indent']+1), 'Missing choice cap')
                        choices.append((params[0][i],decode(m+1,stop-1)))
                    node=ShowChoices(choices,default=params[2],cancel=params[1])
                elif code == 117:
                    node = CommonEvent(params[0])
                elif code == 113:
                    node = BreakLoop()
                elif code == 112:
                    core.require(commands[end-2] == core.command(0, entry['indent']+1), 'Missing loop cap')
                    node = Loop(decode(start+1, end-2))
                elif code == 111:
                    cond = _decode_condition(params)
                    markers = [i for i in range(start+1, end-1) if commands[i]['code'] == 411 and commands[i]['indent'] == entry['indent']]
                    core.require(len(markers) <= 1, 'Multiple else markers')
                    boundary = markers[0] if markers else end-1
                    core.require(commands[boundary-1] == core.command(0, entry['indent']+1), 'Missing branch cap')
                    yes = decode(start+1, boundary-1)
                    no = None
                    if markers:
                        core.require(commands[end-2] == core.command(0, entry['indent']+1), 'Missing else cap')
                        no = decode(boundary+1, end-2)
                    node = If(cond, yes, no)
                if node is not None and not isinstance(node, ShowText):
                    generated = core.compile_nodes([node.to_spec()], entry['indent'], entry['loop_depth'])
                    # Noncanonical extensions stay opaque instead of losing parameters.
                    if not core.db.equal(generated, raw):
                        node = None
            except (ValueError, IndexError, TypeError, KeyError):
                node = None
            result.append(node if node is not None else OpaqueCommand(raw))
            start = end
        return result

    event = decode(0, len(commands)-1)
    event._source_raw = deepcopy(commands)
    return event


def _decode_operand(params):
    if params[0] == 0 and len(params) == 2: return Constant(params[1])
    if params[0] == 1 and len(params) == 2: return VariableValue(params[1])
    if params[0] == 2 and len(params) == 3: return RandomValue(params[1], params[2])
    if params[0] == 4 and len(params) == 2: return ScriptValue(params[1])
    raise ValueError('Unsupported variable operand')


def _decode_condition(params):
    if params[0] == 0 and len(params) == 3 and type(params[2]) is int and params[2] in (0, 1):
        return SwitchCondition(params[1], params[2] == 0)
    if params[0] == 1 and len(params) == 5 and params[2] in (0, 1):
        value = Constant(params[3]) if params[2] == 0 else VariableValue(params[3])
        return VariableCondition(params[1], core.COMPARISONS[params[4]], value)
    if params[0] == 2 and len(params) == 3 and type(params[2]) is int and params[2] in (0, 1):
        return SelfSwitchCondition(params[1], params[2] == 0)
    if params[0] == 6 and len(params) == 3:
        return Character(params[1]).facing({2: 'down', 4: 'left', 6: 'right', 8: 'up'}[params[2]])
    if params[0] == 8 and len(params) == 2: return Item(params[1]).is_owned()
    if params[0] == 11 and len(params) == 3:
        return ButtonCondition(params[1], ['pressed', 'triggered', 'repeated'][params[2]])
    if params[0] == 12 and len(params) == 2: return ScriptCondition(params[1])
    if params[0] == 4:
        if params[2] == 0 and len(params) == 3: return Actor(params[1]).in_party()
        if params[2] == 1 and len(params) == 4: return Actor(params[1]).name_equals(params[3])
    raise ValueError('Unsupported condition; preserve entire branch')
