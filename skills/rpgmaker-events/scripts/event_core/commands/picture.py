"""Picture（图片）指令。"""
from dataclasses import dataclass
from ..base import Command
from ..operands import VariableValue
from .. import compiler as core

ORIGINS = ['upper_left', 'center']
BLENDS = ['normal', 'add', 'multiply', 'screen']
EASINGS = ['linear', 'ease_in', 'ease_out', 'ease_in_out']


def _position(node, kind):
    values = [node.x, node.y]
    indirect = all(isinstance(v, VariableValue) for v in values)
    core.require(indirect or all(type(v) is int for v in values), 'x/y must both be integers or VariableValue')
    return {'type':kind,'id':node.id,'origin':node.origin,'variables':indirect,
            'position':[v.id for v in values] if indirect else values,
            'scale_x':node.scale_x,'scale_y':node.scale_y,'opacity':node.opacity,'blend':node.blend}


@dataclass(eq=False)
class ShowPicture(Command):
    """Show Picture（显示图片），占用指定图片编号，同编号会被替换。

    id -- 1–100；name -- img/pictures 下的文件名，可含子目录，不含扩展名。
    x/y -- 像素坐标，可为负数；或同时传 VariableValue。
    origin -- upper_left / center；scale_x/scale_y -- 百分比，100 为原尺寸。
    opacity -- 0–255；blend -- normal/add/multiply/screen。
    图片资源需存在；地图和战斗的图片槽位相互独立。
    """
    id: int
    name: str
    x: int | VariableValue = 0
    y: int | VariableValue = 0
    origin: str = 'upper_left'
    scale_x: int = 100
    scale_y: int = 100
    opacity: int = 255
    blend: str = 'normal'

    def to_spec(self):
        return {**_position(self,'show_picture'),'name':self.name}


@dataclass(eq=False)
class MovePicture(Command):
    """Move Picture（移动图片），改变已显示图片的位置、缩放和透明度。

    x/y、origin、scale_x/scale_y、opacity、blend 同 ShowPicture。
    duration -- 正整数帧数；wait -- 等待完成。
    easing -- linear/ease_in/ease_out/ease_in_out（匀速／慢起／慢停／慢起慢停）。
    必须先显示同编号图片；未显示时不会创建图片，wait 仍会等待指定帧数。
    """
    id: int
    x: int | VariableValue = 0
    y: int | VariableValue = 0
    origin: str = 'upper_left'
    scale_x: int = 100
    scale_y: int = 100
    opacity: int = 255
    blend: str = 'normal'
    duration: int = 60
    wait: bool = True
    easing: str = 'linear'

    def to_spec(self):
        return {**_position(self,'move_picture'),'duration':self.duration,'wait':self.wait,'easing':self.easing}


@dataclass(eq=False)
class RotatePicture(Command):
    """Rotate Picture（旋转图片），speed 为 -90–90，0 停止旋转。

    正值顺时针，负值逆时针；为持续旋转速度，不是目标角度，不等待完成。
    """
    id: int
    speed: int = 0

    def to_spec(self):
        return {'type':'rotate_picture','id':self.id,'speed':self.speed}


@dataclass(eq=False)
class TintPicture(Command):
    """Tint Picture（图片色调），red/green/blue 为 -255–255，gray 为 0–255。

    duration -- 正整数帧数；wait -- 等待完成。全零恢复正常色调。
    必须先显示同编号图片；未显示时不会创建图片，wait 仍会等待。
    """
    id: int
    red: int = 0
    green: int = 0
    blue: int = 0
    gray: int = 0
    duration: int = 60
    wait: bool = True

    def to_spec(self):
        return {'type':'tint_picture','id':self.id,'tone':[self.red,self.green,self.blue,self.gray],
                'duration':self.duration,'wait':self.wait}


@dataclass(eq=False)
class ErasePicture(Command):
    """Erase Picture（消除图片），清除指定编号的图片。"""
    id: int

    def to_spec(self):
        return {'type':'erase_picture','id':self.id}


def compile_picture(node, indent):
    kind=node['type']; id=core.integer(node['id'],1,100)
    if kind in ('show_picture','move_picture'):
        common={'type','id','origin','variables','position','scale_x','scale_y','opacity','blend'}
        core.fields(node, common | ({'name'} if kind=='show_picture' else {'duration','wait','easing'}))
        indirect=core.boolean(node['variables']);xy=node['position']
        core.require(isinstance(xy,list) and len(xy)==2,'Expected x/y pair')
        for v in xy:
            core.require(type(v) is int,'Coordinates must be integers')
            if indirect:core.integer(v,1)
        p=[id,core.string(node['name']) if kind=='show_picture' else 0,core.enum(node['origin'],ORIGINS),int(indirect),*xy,
           core.integer(node['scale_x']),core.integer(node['scale_y']),core.integer(node['opacity'],0,255),core.enum(node['blend'],BLENDS)]
        if kind=='move_picture':
            p += [core.integer(node['duration'],1),core.boolean(node['wait']),core.enum(node['easing'],EASINGS)]
        return [core.command(231 if kind=='show_picture' else 232,indent,p)]
    if kind=='rotate_picture':
        core.fields(node,{'type','id','speed'})
        return [core.command(233,indent,[id,core.integer(node['speed'],-90,90)])]
    if kind=='tint_picture':
        core.fields(node,{'type','id','tone','duration','wait'})
        tone=node['tone'];core.require(isinstance(tone,list) and len(tone)==4,'Tone requires red,green,blue,gray')
        for i,v in enumerate(tone):core.integer(v,0 if i==3 else -255,255)
        return [core.command(234,indent,[id,list(tone),core.integer(node['duration'],1),core.boolean(node['wait'])])]
    core.require(kind=='erase_picture','Unknown picture command')
    core.fields(node,{'type','id'})
    return [core.command(235,indent,[id])]


def decode_picture(code,p):
    if code in (231,232):
        core.require(len(p)==(10 if code==231 else 13),'Unknown picture parameters')
        core.require(type(p[3]) is int and p[3] in (0,1),'Unknown coordinate mode')
        xy=[VariableValue(v) for v in p[4:6]] if p[3] else p[4:6]
        kw={'x':xy[0],'y':xy[1],'origin':ORIGINS[p[2]],'scale_x':p[6],'scale_y':p[7],'opacity':p[8],'blend':BLENDS[p[9]]}
        if code==231:return ShowPicture(p[0],p[1],**kw)
        return MovePicture(p[0],**kw,duration=p[10],wait=p[11],easing=EASINGS[p[12]])
    if code==233:return RotatePicture(*p)
    if code==234:
        core.require(len(p)==4 and isinstance(p[1],list) and len(p[1])==4,'Unknown tone parameters')
        return TintPicture(p[0],*p[1],duration=p[2],wait=p[3])
    return ErasePicture(*p)
