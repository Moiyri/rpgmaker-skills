"""角色记录及集合。"""
from copy import deepcopy
from .backend import db, integer
from .items import Field


def blank_actor(id):
    return dict(id=id,battlerName='',characterIndex=0,characterName='',classId=1,
                equips=[0,0,0,0,0],faceIndex=0,faceName='',traits=[],initialLevel=1,
                maxLevel=99,name='',nickname='',note='',profile='')


class Actor:
    """角色数据库设置；等级与装备是新游戏初始值，不修改存档中的角色。"""
    name=Field('name',str)
    nickname=Field('nickname',str)
    profile=Field('profile',str)
    note=Field('note',str)
    class_id=Field('classId',int,1)
    initial_level=Field('initialLevel',int,1,99)
    max_level=Field('maxLevel',int,1,99)
    character_name=Field('characterName',str)
    character_index=Field('characterIndex',int,0,7)
    face_name=Field('faceName',str)
    face_index=Field('faceIndex',int,0,7)
    battler_name=Field('battlerName',str)

    def __init__(self,data):self._data=deepcopy(data)
    @property
    def id(self):return self._data['id']
    def to_data(self):return deepcopy(self._data)
    def get(self,path):
        """读取嵌套字段副本。"""
        return deepcopy(db.get(self._data,path))
    def set(self,path,value):
        """修改已有嵌套字段，ID 不可改；traits 暂用原生字段路径。"""
        db.require(isinstance(path,list) and path and path[0]!='id','Cannot replace actor root or ID')
        self._data=db.apply_operation(self._data,dict(op='set',file='Actors.json',path=path,value=value))
    @property
    def traits(self):return Traits(self)
    @property
    def equipment(self):
        """初始装备 ID 列表副本，槽位从 0 开始；0 表示无装备。"""
        return deepcopy(self._data['equips'])
    def equip(self,slot,id):
        """设置初始装备；槽位依职业及双持特性确定，0 清空。"""
        integer(slot,0,len(self._data['equips'])-1);integer(id)
        self._data['equips'][slot]=id
    def describe(self):
        return '\n'.join([f'{self.id:04d} {self.name}']+[f'{k}: {v!r}' for k,v in self._data.items() if k not in ('id','name')])


class Actors:
    """角色列表、搜索、创建和清空；不移动已有 ID。"""
    def __init__(self,owner):
        self.owner=owner
        self.raw=db.file_path(owner.root,'Actors.json').read_bytes()
        self.original=db.read_document(self.raw)
        db.require(isinstance(self.original,list) and self.original and self.original[0] is None,'Invalid Actors array')
        self.values=deepcopy(self.original);self.cache={}
    def get(self,id):
        integer(id,1,len(self.values)-1)
        data=self.values[id]
        db.require(isinstance(data,dict) and data.get('id')==id,'Missing actor or mismatched ID')
        if id not in self.cache:self.cache[id]=Actor(data)
        return self.cache[id]
    def find(self,text):
        """按原始名称子串搜索，返回 Actor 列表。"""
        db.require(isinstance(text,str),'Expected text')
        return [self.get(i) for i,v in enumerate(self.values) if i and v and text.casefold() in self.get(i).name.casefold()]
    def list(self,*,include_empty=False,offset=0,limit=50):
        """返回 ID、名称、职业和初始等级的简短文本。"""
        integer(offset);integer(limit,1)
        rows=[a for a in self.find('') if include_empty or a.name]
        return '\n'.join([f'角色 {len(rows)} 项']+[f'{a.id:04d} {a.name or "（未命名）"} | 职业={a.class_id} | 等级={a.initial_level}' for a in rows[offset:offset+limit]])
    def create(self,name='',id=None):
        """追加角色；指定 ID 只使用标准空白记录、null 槽或末尾。"""
        db.require(isinstance(name,str),'Expected name')
        target=len(self.values) if id is None else integer(id,1,len(self.values))
        if target<len(self.values):
            current=self.cache[target].to_data() if target in self.cache else self.values[target]
            db.require(current is None or db.equal(current,blank_actor(target)),'Target actor is not empty')
        data=blank_actor(target);data['name']=name
        if target==len(self.values):self.values.append(data)
        else:self.values[target]=data
        if target in self.cache:self.cache[target]._data=deepcopy(data)
        else:self.cache[target]=Actor(data)
        return self.cache[target]
    def clear(self,id):
        """重置空白角色，保留 ID；移除特性、装备、备注及插件字段，不修改引用。"""
        actor=self.get(id);actor._data=blank_actor(id);return actor
    def references(self,id):
        """查询磁盘中的初始队伍、地图页条件及原生事件角色引用；动态引用不解析。"""
        from .references import ReferenceReport, ItemReference
        integer(id,1);report=ReferenceReport()
        def add(file,path,usage):report.matches.append(ItemReference(file,tuple(path),usage))
        files=['System.json','CommonEvents.json','Troops.json']+[p.name for p in self.owner.root.glob('Map[0-9]*.json') if p.stem[3:].isdigit()]
        for file in files:
            path=self.owner.root/file
            if not path.exists():report.warnings.append(f'未扫描：{file} 不存在');continue
            data=db.read_document(db.file_path(self.owner.root,file).read_bytes())
            if file=='System.json':
                for i,a in enumerate(data.get('partyMembers',[])):
                    if a==id:add(file,['partyMembers',i],'初始队伍')
                continue
            lists=[]
            if file=='CommonEvents.json':
                lists=[([i,'list'],e['list']) for i,e in enumerate(data) if e]
            else:
                for i,e in enumerate(data if file=='Troops.json' else data['events']):
                    if not e:continue
                    for j,page in enumerate(e['pages']):
                        base=([i] if file=='Troops.json' else ['events',i])+['pages',j]
                        c=page.get('conditions',{})
                        if c.get('actorValid') and c.get('actorId')==id:add(file,base+['conditions','actorId'],'角色条件')
                        lists.append((base+['list'],page['list']))
            for base,commands in lists:
                for i,c in enumerate(commands):
                    code=c['code'];p=c['parameters'];slot=None
                    if code in (129,303,320,321,322,324,325) and p and p[0]==id:slot=0
                    elif code==111 and len(p)>1 and p[0]==4 and p[1]==id:slot=1
                    elif code in (311,312,313,314,315,316,317,318,326) and len(p)>1 and p[0]==0 and p[1]==id:slot=1
                    elif code==319 and p and p[0]==id:slot=0
                    elif code==122 and len(p)>5 and p[3]==3 and p[4]==3 and p[5]==id:slot=5
                    if slot is not None:add(file,base+[i,'parameters',slot],f'事件指令 {code}')
        return report

    def prepare(self):
        db.require(db.file_path(self.owner.root,'Actors.json').read_bytes()==self.raw,'Actors.json changed; reload')
        ops=[dict(op='test',file='Actors.json',path=[],expect=self.original)]
        for id,actor in sorted(self.cache.items()):
            value=actor.to_data();old=self.original[id] if id<len(self.original) else None
            if db.equal(value,old):continue
            for f in vars(Actor).values():
                if isinstance(f,Field):
                    holder=type('Fields',(),{})();holder._data={};f.__set__(holder,value[f.key])
            db.require(value['initialLevel']<=value['maxLevel'],'Initial level exceeds max level')
            db.require(isinstance(value['equips'],list),'Expected equipment list')
            for e in value['equips']:integer(e)
            if id<len(self.original):ops.append(dict(op='set',file='Actors.json',path=[id],value=value))
            else:ops.append(dict(op='splice',file='Actors.json',path=[],index=id,delete_count=0,items=[value]))
        return ops


TRAITS = dict(element_rate=11,debuff_rate=12,state_rate=13,state_resist=14,
              parameter_rate=21,extra_parameter=22,special_parameter=23,
              attack_element=31,attack_state=32,attack_speed=33,attack_times=34,
              attack_skill=35,skill_type=41,seal_skill_type=42,skill=43,seal_skill=44,
              weapon_type=51,armor_type=52,lock_equipment=53,seal_equipment=54,
              slot_type=55,action_plus=61,special_flag=62,collapse_type=63,party_ability=64)


class Traits:
    """特性列表。kind 使用 TRAITS 的名称；id 为数据库／参数编号。

    value 沿用引擎单位：比率 1.0 为 100%，概率 0.1 为 10%；固定增加值直接填写。
    id 来源：element_rate/attack_element 查 db.types.elements.list()；
    skill_type/seal_skill_type 查 db.types.skill_types.list()；
    weapon_type/armor_type 查 db.types.weapon_types/armor_types.list()；
    lock_equipment/seal_equipment 查 db.types.equipment_types.list()。
    固定能力、标记编号见 references/engine-enums.md；技能、状态用数据库脚本查询。
    attack_speed/attack_times/action_plus 不使用 id，保留默认 0。
    未识别特性及额外字段原样保留。下标从 0 开始。
    """
    def __init__(self,actor):self.actor=actor
    def list(self):
        names={v:k for k,v in TRAITS.items()}
        return '\n'.join(f'{i}: {names.get(t["code"],t["code"])} id={t["dataId"]} value={t["value"]}' for i,t in enumerate(self.actor._data['traits'])) or '无特性'
    def get(self,index):
        integer(index,0,len(self.actor._data['traits'])-1)
        return deepcopy(self.actor._data['traits'][index])
    def add(self,kind,*,id=0,value=1):
        """追加特性；例如 add('state_resist', id=1) 或 add('parameter_rate', id=2, value=1.2)。"""
        import math
        db.require(kind in TRAITS,'Unknown trait kind');integer(id)
        db.require(type(value) in (int,float) and math.isfinite(value),'Expected finite value')
        self.actor._data['traits'].append(dict(code=TRAITS[kind],dataId=id,value=value))
    def remove(self,index):
        integer(index,0,len(self.actor._data['traits'])-1)
        return self.actor._data['traits'].pop(index)
    def clear(self):self.actor._data['traits'].clear()
