"""Movement 指令与移动路线；路线步骤不是 EventList 事件指令。"""
from dataclasses import dataclass
from typing import Any, Literal
from copy import deepcopy
from ..base import Command
from ..operands import VariableValue
from .. import compiler as core

DIRECTIONS = {'keep': 0, 'down': 2, 'left': 4, 'right': 6, 'up': 8}
MOVES = ['down','left','right','up','lower_left','lower_right','upper_left','upper_right','random','toward_player','away_from_player','forward','backward']
TURNS = ['down','left','right','up','right_90','left_90','180','random_90','random','toward_player','away_from_player']
FLAGS = ['walking','stepping','direction_fix','through','transparent']


def destination(values, map_location=False):
    indirect = all(isinstance(v, VariableValue) for v in values)
    core.require(indirect or all(type(v) is int for v in values), 'Use all integers or all VariableValue')
    result = [v.id for v in values] if indirect else list(values)
    for i, v in enumerate(result):
        core.integer(v, 1 if indirect or (map_location and i == 0) else 0)
    return int(indirect), result


@dataclass(eq=False)
class SetVehicleLocation(Command):
    """Set Vehicle Location（设置交通工具位置），vehicle 为 boat / ship / airship。

    map_id、x、y 全部为整数或全部为 VariableValue。不检查地图边界。
    """
    vehicle: str
    map_id: int | VariableValue
    x: int | VariableValue
    y: int | VariableValue

    def to_spec(self):
        mode, values = destination([self.map_id, self.x, self.y], True)
        return {'type':'vehicle_location','vehicle':self.vehicle,'mode':mode,'destination':values}


@dataclass(eq=False)
class SetEventLocation(Command):
    """Set Event Location（设置事件位置），0 为本事件，正整数为当前地图事件 ID。

    x/y 同为整数或 VariableValue；交换位置时只传 exchange=另一事件 ID。
    direction 为 keep/down/left/right/up；本事件需要地图事件上下文。
    """
    event_id: int
    x: int | VariableValue | None = None
    y: int | VariableValue | None = None
    direction: str = 'keep'
    exchange: int | None = None

    def to_spec(self):
        if self.exchange is not None:
            core.require(self.x is None and self.y is None, 'Exchange cannot also specify coordinates')
            mode, values = 2, [core.integer(self.exchange), 0]
        else:
            mode, values = destination([self.x, self.y])
        return {'type':'event_location','event_id':self.event_id,'mode':mode,'destination':values,'direction':self.direction}


@dataclass(eq=False)
class ScrollMap(Command):
    """Scroll Map（滚动地图），direction 为 down/left/right/up，distance 为格数。

    speed 为 1–6，wait 表示等待完成；地图边界可能限制滚动，战斗中不生效。
    """
    direction: str
    distance: int
    speed: int = 4
    wait: bool = False

    def to_spec(self):
        return {'type':'scroll_map','direction':self.direction,'distance':self.distance,'speed':self.speed,'wait':self.wait}


@dataclass(eq=False)
class GetOnOffVehicle(Command):
    """Get on/off Vehicle（乘降交通工具），按玩家位置切换乘降；必须满足引擎乘降条件。"""
    def to_spec(self):
        return {'type':'get_on_off_vehicle'}


@dataclass
class RouteStep:
    """可编辑路线步骤。使用 Route 的帮助方法创建；修改 values 中具名字段。"""
    action: str
    values: dict
    editor_indent: bool = True

    def to_spec(self):
        return {'action':self.action,'values':deepcopy(self.values),'editor_indent':self.editor_indent}


class Route:
    """移动路线步骤工厂；返回 RouteStep，用于 SetMovementRoute.steps。"""
    @staticmethod
    def move(direction):
        """移动一步：down/left/right/up/lower_left/lower_right/upper_left/upper_right/random/toward_player/away_from_player/forward/backward。"""
        return RouteStep('move', {'direction':direction})
    @staticmethod
    def turn(direction):
        """转向：down/left/right/up/right_90/left_90/180/random_90/random/toward_player/away_from_player。"""
        return RouteStep('turn', {'direction':direction})
    @staticmethod
    def jump(x, y):
        """Jump（跳跃），x/y 为相对格数，可为负数。"""
        return RouteStep('jump', {'x':x,'y':y})
    @staticmethod
    def wait(frames):
        """Wait（等待），正整数帧数。"""
        return RouteStep('wait', {'frames':frames})
    @staticmethod
    def switch(id, on=True):
        """Switch ON/OFF（开关），控制普通开关。"""
        return RouteStep('switch', {'id':id,'on':on})
    @staticmethod
    def speed(value):
        """Change Speed（更改速度），1–6。"""
        return RouteStep('speed', {'value':value})
    @staticmethod
    def frequency(value):
        """Change Frequency（更改频率），1–5。"""
        return RouteStep('frequency', {'value':value})
    @staticmethod
    def option(name, on=True):
        """切换 walking/stepping/direction_fix/through/transparent；开启穿透会忽略碰撞。"""
        return RouteStep('option', {'name':name,'on':on})
    @staticmethod
    def image(name, index=0):
        """Change Image（更改图像），行走图名不含扩展名，index 为 0–7。"""
        return RouteStep('image', {'name':name,'index':index})
    @staticmethod
    def opacity(value):
        """Change Opacity（更改不透明度），0–255。"""
        return RouteStep('opacity', {'value':value})
    @staticmethod
    def blend(mode):
        """Change Blend Mode（混合模式），normal/add/multiply/screen。"""
        return RouteStep('blend', {'mode':mode})
    @staticmethod
    def se(name, volume=90, pitch=100, pan=0):
        """Play SE（播放音效），文件名不含扩展名；音量 0–100，音调 50–150，声像 -100–100。"""
        return RouteStep('se', {'name':name,'volume':volume,'pitch':pitch,'pan':pan})
    @staticmethod
    def script(text):
        """Script（脚本），this 指向移动角色；只存储，不执行或检查 JavaScript。"""
        return RouteStep('script', {'text':text})


@dataclass(eq=False)
class SetMovementRoute(Command):
    """Set Movement Route（设置移动路线），target=-1 玩家、0 本事件、正整数地图事件。

    steps 为 Route 步骤列表，可增删改序。repeat 重复、skippable 受阻跳过、wait 等待完成。
    禁止 repeat 与 wait 同时开启；不跳过且路径受阻时也可能一直等待。
    本事件需要地图事件上下文；不检查地图碰撞或资源存在性。
    """
    target: int
    steps: list[RouteStep]
    repeat: bool = False
    skippable: bool = False
    wait: bool = True

    def to_spec(self):
        core.require(isinstance(self.steps,list) and all(isinstance(s,RouteStep) for s in self.steps),'Expected RouteStep list')
        return {'type':'movement_route','target':self.target,'steps':[s.to_spec() for s in self.steps],
                'repeat':self.repeat,'skippable':self.skippable,'wait':self.wait}


def compile_step(step):
    core.fields(step, {'action','values','editor_indent'})
    a, v = step['action'], step['values']
    schemas = {'move':{'direction'},'turn':{'direction'},'jump':{'x','y'},'wait':{'frames'},'switch':{'id','on'},
               'speed':{'value'},'frequency':{'value'},'option':{'name','on'},'image':{'name','index'},
               'opacity':{'value'},'blend':{'mode'},'se':{'name','volume','pitch','pan'},'script':{'text'}}
    core.require(a in schemas, 'Unknown route action')
    core.fields(v, schemas[a]); p = []
    if a == 'move': code = core.enum(v['direction'], MOVES) + 1
    elif a == 'turn': code = core.enum(v['direction'], TURNS) + 16
    elif a == 'jump': code,p = 14,[core.integer(v['x'],-9999,9999),core.integer(v['y'],-9999,9999)]
    elif a == 'wait': code,p = 15,[core.integer(v['frames'],1)]
    elif a == 'switch': code,p = 27 + int(not core.boolean(v['on'])),[core.integer(v['id'],1)]
    elif a in ('speed','frequency','opacity'):
        code = {'speed':29,'frequency':30,'opacity':42}[a]
        p = [core.integer(v['value'],0 if a=='opacity' else 1,{'speed':6,'frequency':5,'opacity':255}[a])]
    elif a == 'option': code = 31 + core.enum(v['name'], FLAGS)*2 + int(not core.boolean(v['on']))
    elif a == 'image': code,p = 41,[core.string(v['name']),core.integer(v['index'],0,7)]
    elif a == 'blend': code,p = 43,[core.enum(v['mode'],['normal','add','multiply','screen'])]
    elif a == 'se':
        code,p = 44,[{'name':core.string(v['name']),'volume':core.integer(v['volume'],0,100),
                      'pitch':core.integer(v['pitch'],50,150),'pan':core.integer(v['pan'],-100,100)}]
    elif a == 'script': code,p = 45,[core.string(v['text'])]
    result = {'code':code,'parameters':p}
    if core.boolean(step['editor_indent']): result['indent'] = None
    return result


def compile_movement(node, indent):
    t = node['type']
    if t == 'vehicle_location':
        core.fields(node, {'type','vehicle','mode','destination'})
        mode = core.integer(node['mode'],0,1); v = node['destination']
        core.require(isinstance(v,list) and len(v)==3,'Expected map,x,y')
        for i,x in enumerate(v): core.integer(x,1 if mode or i==0 else 0)
        return [core.command(202,indent,[core.enum(node['vehicle'],['boat','ship','airship']),mode,*v])]
    if t == 'event_location':
        core.fields(node, {'type','event_id','mode','destination','direction'})
        mode=core.integer(node['mode'],0,2);v=node['destination']
        core.require(isinstance(v,list) and len(v)==2,'Expected two coordinates')
        for x in v: core.integer(x,1 if mode==1 else 0)
        core.require(mode!=2 or v[1]==0,'Exchange filler must be zero')
        core.require(node['direction'] in DIRECTIONS,'Unknown direction')
        return [core.command(203,indent,[core.integer(node['event_id']),mode,*v,DIRECTIONS[node['direction']]])]
    if t == 'scroll_map':
        core.fields(node, {'type','direction','distance','speed','wait'})
        core.require(node['direction'] in DIRECTIONS and node['direction']!='keep','Unknown direction')
        return [core.command(204,indent,[DIRECTIONS[node['direction']],core.integer(node['distance'],1),core.integer(node['speed'],1,6),core.boolean(node['wait'])])]
    if t == 'get_on_off_vehicle':
        core.fields(node, {'type'});return [core.command(206,indent)]
    core.fields(node, {'type','target','steps','repeat','skippable','wait'})
    core.require(isinstance(node['steps'],list),'Expected route steps')
    route = {k:core.boolean(node[k]) for k in ('repeat','skippable','wait')}
    core.require(not (route['repeat'] and route['wait']),'Repeat plus wait never completes')
    steps = [compile_step(s) for s in node['steps']]
    route = {'list':steps+[{'code':0}],**route}
    return [core.command(205,indent,[core.integer(node['target'],-1),route])] + [core.command(505,indent,[deepcopy(s)]) for s in steps]


def decode_step(raw):
    code,p=raw['code'],raw.get('parameters',[])
    if 1<=code<=13: node=Route.move(MOVES[code-1])
    elif 16<=code<=26: node=Route.turn(TURNS[code-16])
    elif code==14: node=Route.jump(*p)
    elif code==15: node=Route.wait(*p)
    elif code in (27,28): node=Route.switch(p[0],code==27)
    elif code==29: node=Route.speed(*p)
    elif code==30: node=Route.frequency(*p)
    elif 31<=code<=40: node=Route.option(FLAGS[(code-31)//2],code%2==1)
    elif code==41: node=Route.image(*p)
    elif code==42: node=Route.opacity(*p)
    elif code==43: node=Route.blend(['normal','add','multiply','screen'][p[0]])
    elif code==44: node=Route.se(**p[0])
    elif code==45: node=Route.script(*p)
    else: raise ValueError('Unknown route step')
    node.editor_indent = 'indent' in raw
    core.require(core.db.equal(compile_step(node.to_spec()),raw),'Extended route step')
    return node


def decode_movement(code,p):
    if code==202:
        core.require(type(p[1]) is int and p[1] in (0,1),'Unknown vehicle mode')
        return SetVehicleLocation(['boat','ship','airship'][p[0]], *([VariableValue(v) for v in p[2:]] if p[1] else p[2:]))
    if code==203:
        direction={v:k for k,v in DIRECTIONS.items()}[p[4]]
        core.require(type(p[1]) is int and p[1] in (0,1,2),'Unknown event location mode')
        if p[1]==2: return SetEventLocation(p[0],exchange=p[2],direction=direction)
        return SetEventLocation(p[0], *([VariableValue(v) for v in p[2:4]] if p[1] else p[2:4]),direction=direction)
    if code==204: return ScrollMap({v:k for k,v in DIRECTIONS.items()}[p[0]],*p[1:])
    if code==206: return GetOnOffVehicle()
    r=p[1]
    core.require(r['list'] and r['list'][-1]=={'code':0},'Unknown route end')
    return SetMovementRoute(p[0],[decode_step(s) for s in r['list'][:-1]],r['repeat'],r['skippable'],r['wait'])


@dataclass(eq=False)
class TransferPlayer(Command):
    """Transfer Player（移动玩家），将玩家传送到指定地图坐标。

    map_id / x / y -- 地图 ID 和坐标，必须全部为整数或全部为 VariableValue。
    direction -- keep / down / left / right / up，默认 keep。
    fade -- black / white / none，默认 black。
    地图必须存在且坐标有效；编译不检查地图边界，战斗中不能执行传送。
    """

    map_id: int | VariableValue
    x: int | VariableValue
    y: int | VariableValue
    direction: Literal['keep', 'down', 'left', 'right', 'up'] = 'keep'
    fade: Literal['black', 'white', 'none'] = 'black'

    def to_spec(self) -> dict[str, Any]:
        """返回直接或变量指定的传送目标。"""
        values = [self.map_id, self.x, self.y]
        indirect = all(isinstance(v, VariableValue) for v in values)
        core.require(indirect or all(type(v) is int for v in values), 'Transfer coordinates must be all integers or all VariableValue')
        return {'type': 'transfer', 'variables': indirect,
                'destination': [v.id for v in values] if indirect else values,
                'direction': self.direction, 'fade': self.fade}

