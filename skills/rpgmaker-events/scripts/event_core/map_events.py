"""地图事件及事件页对象。"""
from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any
from .backend import db, require
from .compiler import integer, boolean, string, enum, command, index_commands
from .event_list import EventList

TRIGGERS = ['action', 'player_touch', 'event_touch', 'autorun', 'parallel']
PRIORITIES = ['below', 'same', 'above']
MOVEMENT = ['fixed', 'random', 'approach', 'custom']
DIRECTIONS = {'down': 2, 'left': 4, 'right': 6, 'up': 8}
_UNSET = object()


def default_page():
    return {'conditions': {'actorId': 1, 'actorValid': False, 'itemId': 1, 'itemValid': False,
             'selfSwitchCh': 'A', 'selfSwitchValid': False, 'switch1Id': 1, 'switch1Valid': False,
             'switch2Id': 1, 'switch2Valid': False, 'variableId': 1, 'variableValid': False, 'variableValue': 0},
            'directionFix': False, 'image': {'tileId': 0, 'characterName': '', 'direction': 2, 'pattern': 1, 'characterIndex': 0},
            'list': [command(0, 0)], 'moveFrequency': 3,
            'moveRoute': {'list': [{'code': 0, 'parameters': []}], 'repeat': True, 'skippable': False, 'wait': False},
            'moveSpeed': 3, 'moveType': 0, 'priorityType': 0, 'stepAnime': False,
            'through': False, 'trigger': 0, 'walkAnime': True}


class EventPage:
    """Event Page（事件页），编辑条件、图像、移动及指令。

    新页默认无图像、无条件、确定键触发。改变图像不自动改变优先级。
    自动执行页会阻止正常操作，必须设计结束或切换页条件。
    """

    def __init__(self, data: dict[str, Any] | None = None):
        """从原始页复制；省略 data 时创建默认空页。"""
        self._data = deepcopy(default_page() if data is None else data)
        self._commands = None

    @property
    def commands(self) -> EventList:
        """读取或替换页指令；读取时按需解码，未知块保留。"""
        if self._commands is None:
            self._commands = EventList.from_commands(self._data['list'])
        return self._commands

    @commands.setter
    def commands(self, value: EventList):
        require(isinstance(value, EventList), 'commands must be EventList')
        self._commands = value

    def set_conditions(self, *, switch1=_UNSET, switch2=_UNSET, variable=_UNSET,
                       self_switch=_UNSET, item=_UNSET, actor=_UNSET) -> None:
        """设置出现条件；省略项保持原值，None 关闭对应条件。

        switch1/switch2/item/actor -- ID，从 1 开始。
        variable -- (变量 ID, 最小值)，判断变量 >= 最小值。
        self_switch -- A / B / C / D，只判断 ON。
        所有启用条件须同时成立；多个页成立时，最高编号页优先。
        """
        c = deepcopy(self._data['conditions'])
        for key, value in [('switch1', switch1), ('switch2', switch2), ('item', item), ('actor', actor)]:
            if value is not _UNSET:
                c[key+'Valid'] = value is not None
                if value is not None: c[key+'Id'] = integer(value, 1)
        if variable is not _UNSET:
            c['variableValid'] = variable is not None
            if variable is not None:
                require(isinstance(variable, (list, tuple)) and len(variable) == 2, 'variable requires (ID, threshold)')
                c['variableId'] = integer(variable[0], 1)
                require(type(variable[1]) is int, 'Variable threshold must be integer')
                c['variableValue'] = variable[1]
        if self_switch is not _UNSET:
            c['selfSwitchValid'] = self_switch is not None
            if self_switch is not None:
                require(self_switch in ('A', 'B', 'C', 'D'), 'Self switch must be A/B/C/D')
                c['selfSwitchCh'] = self_switch
        self._data['conditions'] = c

    def set_image(self, *, character_name=_UNSET, character_index=_UNSET,
                  tile_id=_UNSET, direction=_UNSET, pattern=_UNSET) -> None:
        """设置页图像，省略项保持不变。

        character_name -- 行走图名，不含扩展名；设置后切换到行走图模式。
        character_index -- 0–7；tile_id -- 图块 ID，正数切换到图块模式。
        direction -- down/left/right/up；pattern -- 0–2。
        资源存在性由调用者核对；图块模式与非空行走图不可同时指定。
        """
        image = deepcopy(self._data['image'])
        require(not (tile_id is not _UNSET and tile_id != 0 and character_name not in (_UNSET, '')),
                'Choose character image or tile image')
        if character_name is not _UNSET:
            image['characterName'] = string(character_name); image['tileId'] = 0
        if character_index is not _UNSET: image['characterIndex'] = integer(character_index, 0, 7)
        if tile_id is not _UNSET:
            image['tileId'] = integer(tile_id)
            if tile_id > 0: image['characterName'] = ''; image['characterIndex'] = 0
        if direction is not _UNSET:
            require(direction in DIRECTIONS, 'Invalid direction'); image['direction'] = DIRECTIONS[direction]
        if pattern is not _UNSET: image['pattern'] = integer(pattern, 0, 2)
        self._data['image'] = image

    def set_movement(self, *, type=_UNSET, speed=_UNSET, frequency=_UNSET, route=_UNSET) -> None:
        """设置自主移动，省略项保持原值。

        type -- fixed/random/approach/custom；speed -- 1–6；frequency -- 1–5。
        route -- 原生 moveRoute 字典（list、repeat、skippable、wait），保留插件扩展。
        移动路线内部命令与事件指令不是同一套编码，不能传 EventList。
        """
        data = deepcopy(self._data)
        if type is not _UNSET: data['moveType'] = enum(type, MOVEMENT)
        if speed is not _UNSET: data['moveSpeed'] = integer(speed, 1, 6)
        if frequency is not _UNSET: data['moveFrequency'] = integer(frequency, 1, 5)
        if route is not _UNSET:
            validate_route(route); data['moveRoute'] = deepcopy(route)
        self._data = data

    def set_options(self, *, walking=_UNSET, stepping=_UNSET, direction_fix=_UNSET, through=_UNSET) -> None:
        """设置行走动画、踏步动画、固定朝向和穿透；参数均为 bool。"""
        data = deepcopy(self._data)
        for key, value in [('walkAnime',walking),('stepAnime',stepping),('directionFix',direction_fix),('through',through)]:
            if value is not _UNSET: data[key] = boolean(value)
        self._data = data

    @property
    def priority(self) -> str:
        """below/same/above，分别为人物下方、同层、上方。"""
        return PRIORITIES[self._data['priorityType']]

    @priority.setter
    def priority(self, value: str): self._data['priorityType'] = enum(value, PRIORITIES)

    @property
    def trigger(self) -> str:
        """action/player_touch/event_touch/autorun/parallel，分别为确定键、接触、事件接触、自动、并行。"""
        return TRIGGERS[self._data['trigger']]

    @trigger.setter
    def trigger(self, value: str): self._data['trigger'] = enum(value, TRIGGERS)

    def clear(self) -> None:
        """将整页恢复为空白默认页，包含条件、图像和指令。"""
        self._data = default_page(); self._commands = None

    def to_data(self) -> dict[str, Any]:
        """返回独立 JSON 数据，保留未修改的插件字段；不写文件。"""
        result = deepcopy(self._data)
        if self._commands is not None: result['list'] = self._commands.compile()
        return result

    def copy(self) -> EventPage:
        """复制整页；副本与原页相互独立。"""
        return EventPage(self.to_data())


def validate_route(route):
    require(isinstance(route, dict), 'route must be native moveRoute object')
    for key in ('repeat','skippable','wait'): boolean(route[key])
    rows = route['list']; require(isinstance(rows,list) and rows, 'Empty move route')
    require(rows[-1].get('code') == 0, 'Move route needs code 0 terminator')
    for c in rows:
        integer(c['code']); require(isinstance(c.get('parameters',[]),list), 'Invalid move parameters')
    db.dumps(route)


class MapEvent:
    """地图事件，维护名称、备注、坐标和事件页。页下标从 0 开始。"""

    def __init__(self, data: dict[str, Any]):
        """复制已有事件；使用 MapDocument.create_event 新建。"""
        self._data = deepcopy(data)
        self.pages = [EventPage(p) for p in data['pages']]

    @property
    def id(self) -> int:
        """只读事件 ID；删除事件不会重排其他 ID。"""
        return self._data['id']

    @property
    def name(self) -> str:
        """事件名称，可赋值。"""
        return self._data['name']

    @name.setter
    def name(self, value): self._data['name'] = string(value)

    @property
    def note(self) -> str:
        """Note（备注），默认留空或保留；仅用于插件标签等明确用途。

        普通逻辑说明使用 Comment 指令，不擅自清空已有标签。
        """
        return self._data['note']

    @note.setter
    def note(self, value): self._data['note'] = string(value)

    @property
    def x(self) -> int:
        """地图横坐标，赋值后在导出时检查地图边界。"""
        return self._data['x']

    @x.setter
    def x(self, value): self._data['x'] = integer(value)

    @property
    def y(self) -> int:
        """地图纵坐标，赋值后在导出时检查地图边界。"""
        return self._data['y']

    @y.setter
    def y(self, value): self._data['y'] = integer(value)

    def page(self, index: int) -> EventPage:
        """读取指定页；index=0 表示编辑器第 1 页。"""
        integer(index, 0, len(self.pages)-1)
        return self.pages[index]

    def add_page(self, page: EventPage | None = None, *, index: int | None = None) -> EventPage:
        """插入新页或粘贴页副本，默认追加到最后；页顺序影响生效优先级。"""
        index = len(self.pages) if index is None else integer(index,0,len(self.pages))
        require(page is None or isinstance(page,EventPage), 'Expected EventPage')
        result = EventPage() if page is None else page.copy()
        self.pages.insert(index,result)
        return result

    def copy_page(self, index: int, *, insert_at: int | None = None) -> EventPage:
        """复制页并插入副本，默认追加。"""
        return self.add_page(self.page(index),index=insert_at)

    def delete_page(self, index: int) -> None:
        """删除指定页；至少保留一页。"""
        self.page(index); require(len(self.pages)>1, 'Cannot delete the last page')
        del self.pages[index]

    def move_page(self, index: int, destination: int) -> None:
        """调整页顺序；destination 是移动后的下标，最高编号有效页优先。"""
        self.page(index); integer(destination,0,len(self.pages)-1)
        self.pages.insert(destination,self.pages.pop(index))

    def clear_page(self, index: int) -> None:
        """清空整页并恢复默认设置，不只是删除指令。"""
        self.page(index).clear()

    def to_data(self) -> dict[str, Any]:
        """返回事件的独立 JSON 数据，不写文件。"""
        require(bool(self.pages) and all(isinstance(p,EventPage) for p in self.pages), 'Event needs at least one EventPage')
        result = deepcopy(self._data); result['pages'] = [p.to_data() for p in self.pages]
        return result


class MapDocument:
    """读取一个地图的事件，导出带源快照的批量修改计划。

    只操作现有地图。所有编辑在内存中进行，使用 map_events.py apply 正式写入。
    """

    def __init__(self, project: str | Path, map_id: int):
        """读取地图快照并构造全部事件对象。"""
        self.root = db.root_path(Path(project).resolve()/'data')
        self.map_id = integer(map_id,1); self.file = f'Map{map_id:03}.json'
        self._original = db.read_document(db.file_path(self.root,self.file).read_bytes())
        require(isinstance(self._original['events'],list), 'Invalid map events')
        self.events = [MapEvent(e) if e is not None else None for e in self._original['events']]
        # Newly created editor maps can store an empty events array.
        if not self.events: self.events = [None]
        require(self.events[0] is None, 'Event index 0 must be null')
        for i,e in enumerate(self.events):
            require(e is None or e.id==i, 'Event ID/index mismatch')

    def event(self, event_id: int) -> MapEvent:
        """按 ID 读取事件；不存在时抛出 ValueError。"""
        integer(event_id,1,len(self.events)-1)
        result = self.events[event_id]; require(result is not None, 'Event does not exist')
        return result

    def create_event(self, name: str, x: int, y: int, *, note: str = '', event_id: int | None = None) -> MapEvent:
        """创建单页空事件，默认使用最小空闲 ID；指定 ID 不能覆盖现有事件。"""
        integer(x,0,self._original['width']-1); integer(y,0,self._original['height']-1)
        if event_id is None: event_id = next((i for i,e in enumerate(self.events[1:],1) if e is None),len(self.events))
        integer(event_id,1)
        require(event_id <= len(self.events), 'Explicit ID must be a free slot or the next ID')
        require(event_id == len(self.events) or self.events[event_id] is None, 'Event ID is occupied')
        result = MapEvent({'id':event_id,'name':string(name),'note':string(note),'pages':[default_page()],'x':x,'y':y})
        if event_id == len(self.events): self.events.append(result)
        else: self.events[event_id] = result
        return result

    def delete_event(self, event_id: int) -> None:
        """删除事件并保留 null 槽位；不会修复其他事件对该 ID 的引用。"""
        self.event(event_id); self.events[event_id] = None

    def to_plan(self) -> dict[str, Any]:
        """返回原生数据库计划，快照冲突时拒绝写入；不修改地图尺寸或图块。"""
        values = [e.to_data() if e is not None else None for e in self.events]
        if not self._original['events'] and values == [None]: values = []
        for i,e in enumerate(values):
            require(e is None or e['id']==i,'Event ID/index mismatch')
            old = self._original['events'][i] if i<len(self._original['events']) else None
            if e is not None and not db.equal(e,old): validate_event(e,self._original,old)
        return {'version':1,'format':'preserve','operations':[
            {'op':'test','file':self.file,'path':[],'expect':deepcopy(self._original)},
            {'op':'set','file':self.file,'path':['events'],'value':values}]}


def validate_event(event, map_data, original=None):
    integer(event['id'],1); string(event['name']); string(event['note'])
    integer(event['x'],0,map_data['width']-1); integer(event['y'],0,map_data['height']-1)
    require(isinstance(event['pages'],list) and event['pages'],'Event needs pages')
    old_pages = original['pages'] if original else []
    for page in event['pages']:
        if any(db.equal(page,old) for old in old_pages): continue
        c=page['conditions']
        for key in ('switch1','switch2','variable','item','actor'):
            boolean(c[key+'Valid']); integer(c[key+'Id'],1)
        boolean(c['selfSwitchValid']); require(c['selfSwitchCh'] in ('A','B','C','D'),'Invalid self switch')
        require(type(c['variableValue']) is int,'Invalid threshold')
        image=page['image']; integer(image['tileId']); string(image['characterName']); integer(image['characterIndex'],0,7)
        require(type(image['direction']) is int and image['direction'] in (2,4,6,8),'Invalid image direction')
        integer(image['pattern'],0,2)
        integer(page['moveType'],0,3); integer(page['moveSpeed'],1,6); integer(page['moveFrequency'],1,5)
        integer(page['priorityType'],0,2); integer(page['trigger'],0,4)
        for key in ('walkAnime','stepAnime','directionFix','through'): boolean(page[key])
        validate_route(page['moveRoute'])
        # Metadata-only edits must not require interpreting untouched plugin commands.
        if not any(db.equal(page['list'],old['list']) for old in old_pages): index_commands(page['list'])
