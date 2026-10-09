"""RPG Maker 事件接口统一入口。

从本模块导入 EventList、命令、条件和操作数；使用 help(对象) 查看参数。
实现按职责放在 event_core 包中。
"""
from event_core.commands.screen import FadeoutScreen, FadeinScreen, TintScreen, FlashScreen, ShakeScreen, SetWeatherEffect
from event_core.commands.audio_video import PlayBGM, FadeoutBGM, SaveBGM, ReplayBGM, PlayBGS, FadeoutBGS, PlayME, PlaySE, StopSE, PlayMovie
from event_core.commands.scene_control import NameInput, OpenMenu, OpenSave, GameOver, ReturnToTitle
from event_core.commands.picture import ShowPicture, MovePicture, RotatePicture, TintPicture, ErasePicture
from event_core.commands.movement import TransferPlayer, SetVehicleLocation, SetEventLocation, ScrollMap, SetMovementRoute, GetOnOffVehicle, Route, RouteStep
from event_core.plugin_help import plugin_help
from event_core.map_events import MapDocument, MapEvent, EventPage
from event_core.event_search import list_map, search_events
from event_core.event_list import EventList
from event_core.commands.message import ShowChoices, ShowText
from event_core.commands.game_progression import SetSwitch, ChangeVariable, SetSelfSwitch, StartTimer, StopTimer
from event_core.commands.flow_control import Label, JumpToLabel, ExitEvent, If, Loop, BreakLoop, CommonEvent, Comment
from event_core.commands.party import ChangeGold, ChangeItems
from event_core.commands.timing import Wait
from event_core.commands.map_commands import EraseEvent
from event_core.commands.advanced import Script, PluginCommand
from event_core.commands.opaque import OpaqueCommand
from event_core.conditions import Switch, Variable, Actor, Character, Button, Item, SelfSwitch, ScriptCondition
from event_core.operands import Constant, VariableValue, RandomValue, ScriptValue

__all__ = ['ShowChoices', 'Label', 'JumpToLabel', 'ExitEvent', 'FadeoutScreen', 'FadeinScreen', 'TintScreen', 'FlashScreen', 'ShakeScreen', 'SetWeatherEffect', 'PlayBGM', 'FadeoutBGM', 'SaveBGM', 'ReplayBGM', 'PlayBGS', 'FadeoutBGS', 'PlayME', 'PlaySE', 'StopSE', 'PlayMovie', 'NameInput', 'OpenMenu', 'OpenSave', 'GameOver', 'ReturnToTitle', 'ShowPicture', 'MovePicture', 'RotatePicture', 'TintPicture', 'ErasePicture', 'SetVehicleLocation', 'SetEventLocation', 'ScrollMap', 'SetMovementRoute', 'GetOnOffVehicle', 'Route', 'RouteStep', 'plugin_help', 'PluginCommand', 'MapDocument', 'MapEvent', 'EventPage', 'list_map', 'search_events', 'Comment', 'ChangeGold', 'ChangeItems', 'TransferPlayer', 'Wait', 'EraseEvent', 'Script', 'SetSelfSwitch', 'StartTimer', 'StopTimer', 'EventList', 'ShowText', 'SetSwitch', 'ChangeVariable', 'If', 'CommonEvent',
           'Loop', 'BreakLoop', 'Switch', 'Variable', 'Constant', 'VariableValue', 'RandomValue',
           'ScriptValue', 'ScriptCondition', 'OpaqueCommand', 'Actor', 'Character', 'Button', 'Item', 'SelfSwitch']

from event_core.common_event_settings import common_event_settings_plan
__all__ += ['common_event_settings_plan']
