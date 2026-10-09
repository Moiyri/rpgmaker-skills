"""Screen（画面）指令。"""
from dataclasses import dataclass
from ..base import Command
from .. import compiler as core


class FadeoutScreen(Command):
    """Fadeout Screen（淡出画面），变黑并等待完成；时长由引擎决定，默认 24 帧。"""
    def to_spec(self):
        return {'type':'fadeout_screen'}


class FadeinScreen(Command):
    """Fadein Screen（淡入画面），从黑屏恢复并等待完成；时长由引擎决定，默认 24 帧。"""
    def to_spec(self):
        return {'type':'fadein_screen'}


@dataclass(eq=False)
class TintScreen(Command):
    """Tint Screen（画面色调），RGB 为 -255–255，gray 为 0–255；全零恢复正常。

    duration 为非负整数帧数，0 立即改变；wait 表示等待完成。色调会持续，临时效果结束后需恢复。
    """
    red: int = 0
    green: int = 0
    blue: int = 0
    gray: int = 0
    duration: int = 60
    wait: bool = True

    def to_spec(self):
        return {'type':'tint_screen','tone':[self.red,self.green,self.blue,self.gray],'duration':self.duration,'wait':self.wait}


@dataclass(eq=False)
class FlashScreen(Command):
    """Flash Screen（闪烁画面），RGB 和 intensity 为 0–255。

    duration 为正整数帧数；wait 表示等待完成。闪光强度在该时长内逐渐降至 0。
    """
    red: int = 255
    green: int = 255
    blue: int = 255
    intensity: int = 170
    duration: int = 60
    wait: bool = True

    def to_spec(self):
        return {'type':'flash_screen','color':[self.red,self.green,self.blue,self.intensity],'duration':self.duration,'wait':self.wait}


@dataclass(eq=False)
class ShakeScreen(Command):
    """Shake Screen（震动画面），power/speed 为 1–9，duration 为正整数帧数。

    wait 表示等待指定时长；引擎震动可能在随后回到中心时才完全停止。
    """
    power: int = 5
    speed: int = 5
    duration: int = 60
    wait: bool = True

    def to_spec(self):
        return {'type':'shake_screen','power':self.power,'speed':self.speed,'duration':self.duration,'wait':self.wait}


@dataclass(eq=False)
class SetWeatherEffect(Command):
    """Set Weather Effect（设置天气效果），weather 为 none/rain/storm/snow，power 为 1–9。

    duration 为非负整数帧数，0 立即改变；wait 表示等待过渡完成。
    none 关闭天气，power 不影响结果。天气持续至再次更改；战斗中不生效。
    """
    weather: str = 'none'
    power: int = 5
    duration: int = 60
    wait: bool = True

    def to_spec(self):
        return {'type':'weather','weather':self.weather,'power':self.power,'duration':self.duration,'wait':self.wait}


def compile_screen(node, indent):
    kind=node['type']
    if kind in ('fadeout_screen','fadein_screen'):
        core.fields(node,{'type'})
        return [core.command(221 if kind=='fadeout_screen' else 222,indent)]
    if kind in ('tint_screen','flash_screen'):
        key='tone' if kind=='tint_screen' else 'color'
        core.fields(node,{'type',key,'duration','wait'})
        values=node[key];core.require(isinstance(values,list) and len(values)==4,'Expected four color components')
        for i,v in enumerate(values):core.integer(v,-255 if key=='tone' and i<3 else 0,255)
        return [core.command(223 if key=='tone' else 224,indent,[list(values),core.integer(node['duration'],0 if key=='tone' else 1),core.boolean(node['wait'])])]
    if kind=='shake_screen':
        core.fields(node,{'type','power','speed','duration','wait'})
        return [core.command(225,indent,[core.integer(node['power'],1,9),core.integer(node['speed'],1,9),core.integer(node['duration'],1),core.boolean(node['wait'])])]
    core.require(kind=='weather','Unknown screen command')
    core.fields(node,{'type','weather','power','duration','wait'})
    core.enum(node['weather'],['none','rain','storm','snow'])
    return [core.command(236,indent,[node['weather'],core.integer(node['power'],1,9),core.integer(node['duration']),core.boolean(node['wait'])])]


def decode_screen(code,p):
    if code in (221,222):
        core.require(p==[],'Unexpected fade parameters')
        return FadeoutScreen() if code==221 else FadeinScreen()
    if code in (223,224):
        core.require(len(p)==3 and isinstance(p[0],list) and len(p[0])==4,'Expected color, duration, wait')
        cls=TintScreen if code==223 else FlashScreen
        return cls(*p[0],duration=p[1],wait=p[2])
    core.require(len(p)==4,'Expected four screen parameters')
    return ShakeScreen(*p) if code==225 else SetWeatherEffect(*p)
