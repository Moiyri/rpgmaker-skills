"""Scene Control（场景控制）指令。"""
from dataclasses import dataclass
from ..base import Command
from .. import compiler as core


@dataclass(eq=False)
class NameInput(Command):
    """Name Input Processing（名字输入处理），为 actor_id 角色输入名字。

    max_chars -- 最大字符数，默认 8，编辑器范围 1–16。
    角色必须存在；战斗中不生效。
    """
    actor_id: int
    max_chars: int = 8

    def to_spec(self):
        return {'type':'name_input','actor_id':self.actor_id,'max_chars':self.max_chars}


@dataclass(eq=False)
class OpenMenu(Command):
    """Open Menu Screen（打开菜单画面），关闭菜单后继续事件；战斗中不生效。"""
    def to_spec(self):
        return {'type':'open_menu'}


@dataclass(eq=False)
class OpenSave(Command):
    """Open Save Screen（打开存档画面），由玩家选择是否存档，不自动保存；战斗中不生效。"""
    def to_spec(self):
        return {'type':'open_save'}


@dataclass(eq=False)
class GameOver(Command):
    """Game Over（游戏结束），切换到游戏结束画面；不会自动保存当前进度。"""
    def to_spec(self):
        return {'type':'game_over'}


@dataclass(eq=False)
class ReturnToTitle(Command):
    """Return to Title Screen（返回标题画面），不会自动保存；未保存的进度会丢失。"""
    def to_spec(self):
        return {'type':'return_to_title'}


SCENES = {'open_menu':(351,OpenMenu),'open_save':(352,OpenSave),
          'game_over':(353,GameOver),'return_to_title':(354,ReturnToTitle)}


def compile_scene(node, indent):
    kind=node['type']
    if kind=='name_input':
        core.fields(node,{'type','actor_id','max_chars'})
        return [core.command(303,indent,[core.integer(node['actor_id'],1),core.integer(node['max_chars'],1,16)])]
    core.require(kind in SCENES,'Unknown scene command')
    core.fields(node,{'type'})
    return [core.command(SCENES[kind][0],indent)]


def decode_scene(code, parameters):
    if code==303:
        core.require(len(parameters)==2,'Expected actor ID and maximum characters')
        return NameInput(*parameters)
    core.require(parameters==[],'Unexpected scene parameters')
    return next(cls() for value,cls in SCENES.values() if value==code)
