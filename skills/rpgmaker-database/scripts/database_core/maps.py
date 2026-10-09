"""地图目录和属性；事件、图块及尺寸变更不在本接口范围内。"""
from copy import deepcopy
from .backend import db, integer
from .items import Field
from .system_settings import Audio


class Map:
    """已有地图属性。width/height/id 只读；name 为编辑器名，display_name 为游戏显示名。"""
    display_name=Field('displayName',str)
    tileset_id=Field('tilesetId',int,1)
    scroll_type=Field('scrollType',str,choices={0:'none',1:'vertical',2:'horizontal',3:'both'})
    autoplay_bgm=Field('autoplayBgm',bool)
    autoplay_bgs=Field('autoplayBgs',bool)
    disable_dashing=Field('disableDashing',bool)
    specify_battleback=Field('specifyBattleback',bool)
    battleback1_name=Field('battleback1Name',str)
    battleback2_name=Field('battleback2Name',str)
    parallax_name=Field('parallaxName',str)
    parallax_loop_x=Field('parallaxLoopX',bool)
    parallax_loop_y=Field('parallaxLoopY',bool)
    parallax_sx=Field('parallaxSx',int,-32,32)
    parallax_sy=Field('parallaxSy',int,-32,32)
    parallax_show=Field('parallaxShow',bool)
    encounter_step=Field('encounterStep',int,1)
    note=Field('note',str)
    def __init__(self,owner,id):
        self.owner,self._id=owner,id;self.file=f'Map{id:03d}.json'
        self.raw=db.file_path(owner.owner.root,self.file).read_bytes()
        self.original=db.read_document(self.raw);self._data=deepcopy(self.original)
    @property
    def id(self):return self._id
    @property
    def width(self):return self._data['width']
    @property
    def height(self):return self._data['height']
    @property
    def name(self):return self.owner._infos[self.id]['name']
    @name.setter
    def name(self,value):
        db.require(isinstance(value,str),'Expected name');self.owner._infos[self.id]['name']=value
    @property
    def parent_id(self):return self.owner._infos[self.id]['parentId']
    @parent_id.setter
    def parent_id(self,value):
        integer(value)
        if value:self.owner._info(value)
        current=value;seen={self.id}
        while current:
            db.require(current not in seen,'Map parent cycle');seen.add(current)
            current=self.owner._info(current)['parentId']
        self.owner._infos[self.id]['parentId']=value
    @property
    def bgm(self):return Audio(self,('bgm',))
    @property
    def bgs(self):return Audio(self,('bgs',))
    def resize(self,width,height):
        """左上角锚定调整六层；右侧、底部补零或裁剪，越界事件拒绝。"""
        integer(width,1,256);integer(height,1,256)
        oldw,oldh=self.width,self.height
        db.require(len(self._data['data'])==oldw*oldh*6,'Invalid map data length')
        for e in self._data['events']:
            db.require(not e or 0<=e['x']<width and 0<=e['y']<height,'Event outside resized map')
        data=[0]*(width*height*6);n=min(oldw,width)
        for z in range(6):
            for y in range(min(oldh,height)):
                a=(z*oldh+y)*oldw;b=(z*height+y)*width
                data[b:b+n]=self._data['data'][a:a+n]
        if width<oldw or height<oldh:self.owner._shrunk.add(self.id)
        self._data.update(width=width,height=height,data=data)

    def describe(self):
        lines=[f'{self.id:03d} {self.name} | {self.width}×{self.height} | parent={self.parent_id}']
        lines.extend(f'{k}: {v!r}' for k,v in self._data.items() if k not in ['data','events'])
        return '\n'.join(lines)


class Maps:
    """按 MapInfos 编号查询地图，保留空槽和未知字段。"""
    def __init__(self,owner):
        self.owner=owner;self.raw=db.file_path(owner.root,'MapInfos.json').read_bytes()
        self.original=db.read_document(self.raw)
        db.require(isinstance(self.original,list),'Expected MapInfos array')
        self._infos=deepcopy(self.original);self._cache={};self._deleted=set();self._shrunk=set()
    def _info(self,id):
        integer(id,1,len(self._infos)-1)
        value=self._infos[id]
        db.require(isinstance(value,dict) and value.get('id')==id,'Missing map or mismatched ID')
        return value
    def get(self,id):
        self._info(id)
        if id not in self._cache:self._cache[id]=Map(self,id)
        return self._cache[id]
    def find(self,text):
        """按编辑器名称子串搜索，返回 Map 对象。"""
        db.require(isinstance(text,str),'Expected search text')
        return [self.get(i) for i,v in enumerate(self._infos) if i and v and text.casefold() in v['name'].casefold()]
    def list(self,*,search='',offset=0,limit=50):
        """显示地图编号、名称、尺寸、父级和图块集。"""
        integer(offset);integer(limit,1)
        rows=self.find(search);shown=rows[offset:offset+limit]
        lines=[f'地图 {len(rows)} 项']+[f'{m.id:03d} {m.name} | {m.width}×{m.height} | parent={m.parent_id} | tileset={m.tileset_id}' for m in shown]
        if offset+len(shown)<len(rows):lines.append(f'还有更多：offset={offset+len(shown)}')
        return '\n'.join(lines)
    def create(self,name='',*,width=17,height=13,tileset_id=1,parent_id=0,id=None):
        """创建空地图；默认最小空闲 ID，目录和文件必须同时未占用。"""
        import os
        db.require(isinstance(name,str),'Expected name');integer(width,1,256);integer(height,1,256);integer(tileset_id,1);integer(parent_id)
        if parent_id:self._info(parent_id)
        def free(i):
            return i not in self._deleted and (i>=len(self._infos) or self._infos[i] is None) and not os.path.lexists(self.owner.root/f'Map{i:03d}.json')
        if id is None:
            id=1
            while not free(id):id+=1
        integer(id,1,999)
        db.require(free(id),'Map ID or file already occupied')
        while len(self._infos)<=id:self._infos.append(None)
        order=max((v.get('order',0) for v in self._infos if v),default=0)+1
        self._infos[id]=dict(id=id,expanded=False,name=name or f'MAP{id:03d}',order=order,parentId=parent_id,scrollX=0,scrollY=0,quick=False)
        m=Map.__new__(Map);m.owner=self;m._id=id;m.file=f'Map{id:03d}.json';m.raw=None;m.original=None
        audio=dict(name='',pan=0,pitch=100,volume=90)
        m._data=dict(autoplayBgm=False,autoplayBgs=False,battleback1Name='',battleback2Name='',bgm=deepcopy(audio),bgs=deepcopy(audio),disableDashing=False,displayName='',encounterList=[],encounterStep=30,height=height,note='',parallaxLoopX=False,parallaxLoopY=False,parallaxName='',parallaxShow=True,parallaxSx=0,parallaxSy=0,scrollType=0,specifyBattleback=False,tilesetId=tileset_id,width=width,data=[0]*(width*height*6),events=[])
        self._cache[id]=m
        return m
    def delete(self,id):
        """删除地图文件和目录条目；有子地图或静态引用则拒绝，不移动其他 ID。"""
        self._info(id)
        db.require(not any(v and v.get('parentId')==id for v in self._infos),'Map has children')
        m=self.get(id);db.require(m.raw is not None,'Commit new map before deleting it')
        self._deleted.add(id);self._infos[id]=None
    def tree(self):
        """按父级和 order 列出全部地图；异常父级或循环报错。"""
        lines=[];visited=set()
        def walk(parent,depth):
            for v in sorted((v for v in self._infos if v and v['parentId']==parent),key=lambda v:(v.get('order',0),v['id'])):
                db.require(v['id'] not in visited,'Map parent cycle');visited.add(v['id'])
                lines.append('  '*depth+f'{v["id"]:03d} {v["name"]}');walk(v['id'],depth+1)
        walk(0,0)
        db.require(len(visited)==sum(v is not None for v in self._infos),'Unreachable maps in hierarchy')
        return '\n'.join(lines)
    def prepare(self):
        import os
        from .map_safety import check_map_references
        db.require(db.file_path(self.owner.root,'MapInfos.json').read_bytes()==self.raw,'MapInfos changed; reload')
        ops=[dict(op='test',file='MapInfos.json',path=[],expect=self.original)]
        # Reference assertions precede all mutations and bind preview to source files.
        for id in self._deleted|self._shrunk:
            m=self._cache[id]
            ops.extend(check_map_references(self.owner.root,id,*(() if id in self._deleted else (m.width,m.height))))
        for id,value in enumerate(self._infos):
            if id>=len(self.original):ops.append(dict(op='splice',file='MapInfos.json',path=[],index=id,delete_count=0,items=[value]))
            elif not db.equal(value,self.original[id]):ops.append(dict(op='set',file='MapInfos.json',path=[id],value=value))
        for id,m in self._cache.items():
            if m.raw is not None:
                db.require(db.file_path(self.owner.root,m.file).read_bytes()==m.raw,f'{m.file} changed; reload')
                if id not in self._deleted:ops.append(dict(op='test',file=m.file,path=[],expect=m.original))
            else:db.require(not os.path.lexists(self.owner.root/m.file),'New map file occupied')
            if id in self._deleted:
                ops.append(dict(op='delete_file',file=m.file));continue
            if m.original is None or m.tileset_id!=m.original['tilesetId']:
                tilesets=db.read_document(db.file_path(self.owner.root,'Tilesets.json').read_bytes())
                db.require(m.tileset_id<len(tilesets) and isinstance(tilesets[m.tileset_id],dict) and tilesets[m.tileset_id].get('id')==m.tileset_id,'Missing tileset')
                ops.append(dict(op='test',file='Tilesets.json',path=[m.tileset_id],expect=tilesets[m.tileset_id]))
            if m.original is None:
                value=m._data;compact=lambda x:db.dumps(x,separators=(',',':'))
                attrs=compact({k:v for k,v in value.items() if k not in ('data','events')})[1:-1]
                text='{\n'+attrs+',\n"data":'+compact(value['data'])+',\n"events":[\n]\n}'
                ops.append(dict(op='create_file',file=m.file,text=text))
            else:
                for key,value in m._data.items():
                    if not db.equal(value,m.original[key]):ops.append(dict(op='set',file=m.file,path=[key],value=value))
        return ops
