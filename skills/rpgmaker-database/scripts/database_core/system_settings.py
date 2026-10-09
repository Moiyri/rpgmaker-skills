"""System 1：标题、队伍、载具、位置、战斗、选项及音频。"""
from copy import deepcopy
from .backend import db, integer
from .items import Field

OPTIONS = dict(start_transparent='optTransparent',show_followers='optFollowers',
    death_by_slip_damage='optSlipDeath',death_by_floor_damage='optFloorDeath',
    display_tp='optDisplayTp',exp_for_reserve_members='optExtraExp',
    show_key_item_number='optKeyItemsNumber',autosave='optAutosave',
    splash_screen='optSplashScreen',message_skip='optMessageSkip')
MUSIC = dict(title=('titleBgm',),battle=('battleBgm',),victory=('victoryMe',),
    defeat=('defeatMe',),game_over=('gameoverMe',),boat=('boat','bgm'),
    ship=('ship','bgm'),airship=('airship','bgm'))
SOUNDS = ['cursor','ok','cancel','buzzer','equip','save','load','battle_start','escape',
    'enemy_attack','enemy_damage','enemy_collapse','boss_collapse_1','boss_collapse_2',
    'actor_damage','actor_collapse','recovery','miss','evasion','magic_evasion',
    'reflection','shop','use_item','use_skill']


class View:
    def __init__(self,store,path=()):self.store,self.path=store,path
    @property
    def _data(self):return db.get(self.store._data,list(self.path))
    def get(self):
        """返回设置副本。"""
        return deepcopy(self._data)
    def describe(self):return '\n'.join(f'{k}: {v!r}' for k,v in self._data.items())


class Audio(View):
    """音频：文件名不含扩展名；空名称表示无音频。"""
    name=Field('name',str)
    volume=Field('volume',int,0,100)
    pitch=Field('pitch',int,50,150)
    pan=Field('pan',int,-100,100)
    def clear(self):self.name=''


class AudioList:
    def __init__(self,store,music):self.store,self.music=store,music
    def get(self,name):
        """按用途取音频对象；list() 查看用途名称。"""
        names=MUSIC if self.music else SOUNDS
        db.require(name in names,'Unknown audio usage')
        path=MUSIC[name] if self.music else ('sounds',SOUNDS.index(name))
        db.get(self.store._data,list(path))
        return Audio(self.store,path)
    def list(self):
        return '\n'.join(f'{name}: {self.get(name).name}' for name in (MUSIC if self.music else SOUNDS))
    def clear(self,name):self.get(name).clear()


class Options(View):
    def list(self):return '\n'.join(f'{k}: {self._data.get(v,"不支持")}' for k,v in OPTIONS.items())
    def get(self,name):
        db.require(name in OPTIONS,'Unknown option')
        db.require(OPTIONS[name] in self._data,'Option missing in this engine project')
        return self._data[OPTIONS[name]]
    def set(self,name,on):
        """按 list() 中名称开关选项；缺失字段报错，不猜引擎版本。"""
        self.get(name);db.require(type(on) is bool,'Expected bool');self._data[OPTIONS[name]]=on


class Position(View):
    """初始位置。玩家 map_id 必须大于 0；载具可 clear 为未放置。"""
    def get(self):return {k:self._data[v] for k,v in [('map_id','startMapId'),('x','startX'),('y','startY')]}
    def set(self,map_id,x,y):
        integer(map_id,1);integer(x);integer(y)
        self._data.update(startMapId=map_id,startX=x,startY=y)
    def clear(self):
        db.require(bool(self.path),'Player start cannot be cleared')
        self._data.update(startMapId=0,startX=0,startY=0)


class Vehicle(View):
    character_name=Field('characterName',str)
    character_index=Field('characterIndex',int,0,7)
    @property
    def position(self):return Position(self.store,self.path)
    @property
    def music(self):return Audio(self.store,self.path+('bgm',))
    def clear_image(self):self.character_name='';self.character_index=0


class TitleWindow(View):
    offset_x=Field('offsetX',int,-9999,9999)
    offset_y=Field('offsetY',int,-9999,9999)
    background=Field('background',str,choices={0:'window',1:'dim',2:'transparent'})


class Title(View):
    image1=Field('title1Name',str)
    image2=Field('title2Name',str)
    draw_game_title=Field('optDrawTitle',bool)
    @property
    def command_window(self):return TitleWindow(self.store,('titleCommandWindow',))
    def clear_images(self):self.image1='';self.image2=''


class Party(View):
    def get(self):return deepcopy(self._data['partyMembers'])
    def set(self,ids):
        """按顺序设置初始队伍；不允许重复角色 ID。"""
        db.require(isinstance(ids,list),'Expected actor ID list')
        for id in ids:integer(id,1)
        db.require(len(set(ids))==len(ids),'Duplicate actor IDs')
        self._data['partyMembers']=ids.copy()
    def add(self,id):self.set(self.get()+[id])
    def remove(self,id):
        ids=self.get();db.require(id in ids,'Actor not in starting party');ids.remove(id);self.set(ids)
    def clear(self):self.set([])
    def list(self):return '初始队伍: '+', '.join(str(i) for i in self.get())




class ToggleList(View):
    """按栏目名称开关；get/list 查询，set 修改。"""
    def __init__(self,store,key,names):super().__init__(store);self.key,self.names=key,names
    def get(self,name):
        db.require(name in self.names,'Unknown toggle')
        return self._data[self.key][self.names.index(name)]
    def set(self,name,on):
        self.get(name);db.require(type(on) is bool,'Expected bool')
        self._data[self.key][self.names.index(name)]=on
    def list(self):return '\n'.join(f'{name}: {self.get(name)}' for name in self.names)


class MagicSkills(View):
    """侧视魔法使用的技能类型 ID（不是技能 ID）；通过 db.types.skill_types 查询。"""
    def get(self):return deepcopy(self._data['magicSkills'])
    def set(self,ids):
        db.require(isinstance(ids,list),'Expected skill type IDs')
        for id in ids:integer(id,1,len(self._data['skillTypes'])-1)
        db.require(len(set(ids))==len(ids),'Duplicate skill type IDs')
        self._data['magicSkills']=ids.copy()
    def add(self,id):self.set(self.get()+[id])
    def remove(self,id):
        values=self.get();db.require(id in values,'Skill type not selected');values.remove(id);self.set(values)
    def clear(self):self.set([])
    def list(self):return '\n'.join(f'{id} {self._data["skillTypes"][id]}' for id in self.get()) or '无侧视魔法类型'


class AttackMotion(View):
    """侧视攻击动作。武器图片编号参照引擎 Weapons 图集；0 为无图片。"""
    motion=Field('type',str,choices={0:'thrust',1:'swing',2:'missile'})
    weapon_image_id=Field('weaponImageId',int,0,30)
    def clear(self):self.motion='thrust';self.weapon_image_id=0


class AttackMotions(View):
    def get(self,weapon_type_id):
        """按武器类型 ID 获取；0 表示徒手，其他编号查 db.types.weapon_types。"""
        integer(weapon_type_id,0,len(self._data['attackMotions'])-1)
        return AttackMotion(self.store,('attackMotions',weapon_type_id))
    def list(self):
        return '\n'.join(f'{i} {"Bare Hands" if i==0 else self._data["weaponTypes"][i] if i<len(self._data["weaponTypes"]) else "未登记类型"}: {self.get(i).motion}, image={self.get(i).weapon_image_id}' for i in range(len(self._data['attackMotions'])))
    def set(self,weapon_type_id,*,motion,weapon_image_id):
        """设置动作；新增武器类型对应的末尾行可自动补齐，不改已有行。"""
        integer(weapon_type_id,0,len(self._data['weaponTypes'])-1)
        holder=type('Fields',(),{})();holder._data={}
        AttackMotion.motion.__set__(holder,motion);AttackMotion.weapon_image_id.__set__(holder,weapon_image_id)
        while len(self._data['attackMotions'])<=weapon_type_id:self._data['attackMotions'].append({'type':0,'weaponImageId':0})
        self._data['attackMotions'][weapon_type_id].update(holder._data)
    def clear(self,weapon_type_id):self.get(weapon_type_id).clear()


class EditorSettings(View):
    """编辑器设置；JSON 格式等级只设置编辑器选项，本工具仍保留当前文件格式。"""
    message_width_normal=Field('messageWidth1',int,1)
    message_width_with_face=Field('messageWidth2',int,1)
    json_format_level=Field('jsonFormatLevel',int,0,2)


class AdvancedSettings(View):
    """高级设置。字体文件名含扩展名；game_id 改动可能影响存档识别。"""
    game_id=Field('gameId',int,1)
    screen_width=Field('screenWidth',int,1)
    screen_height=Field('screenHeight',int,1)
    ui_area_width=Field('uiAreaWidth',int,1)
    ui_area_height=Field('uiAreaHeight',int,1)
    main_font_filename=Field('mainFontFilename',str)
    number_font_filename=Field('numberFontFilename',str)
    fallback_fonts=Field('fallbackFonts',str)
    font_size=Field('fontSize',int,1)
    window_opacity=Field('windowOpacity',int,0,255)
    pictures_upper_limit=Field('picturesUpperLimit',int,1)
    @property
    def screen_scale(self):return self._data['screenScale']
    @screen_scale.setter
    def screen_scale(self,value):
        import math
        db.require(type(value) in (int,float) and math.isfinite(value) and value>0,'Expected positive finite scale')
        self._data['screenScale']=value


class SizeField(Field):
    def __init__(self,key,values):super().__init__(key,int);self.values=values
    def __set__(self,obj,value):
        db.require(type(value) is int and value in self.values,f'{self.key}: expected {self.values}')
        super().__set__(obj,value)


class SystemSettings(View):
    """系统编辑器设置；修改后通过 Database.preview/commit 保存。"""
    tile_size=SizeField('tileSize',[48,32,24,16])
    icon_size=SizeField('iconSize',[32,24,16,12,8])
    face_size=SizeField('faceSize',[144,96,48,40,32])
    @property
    def menu_commands(self):return ToggleList(self.store,'menuCommands',['item','skill','equip','status','formation','save'])
    @property
    def item_categories(self):return ToggleList(self.store,'itemCategories',['item','weapon','armor','key_item'])
    @property
    def magic_skills(self):return MagicSkills(self.store)
    @property
    def attack_motions(self):return AttackMotions(self.store)
    @property
    def editor(self):return EditorSettings(self.store,('editor',))
    @property
    def advanced(self):return AdvancedSettings(self.store,('advanced',))
    game_title=Field('gameTitle',str)
    currency_unit=Field('currencyUnit',str)
    side_view=Field('optSideView',bool)
    battle_system=Field('battleSystem',str,choices={0:'turn_based',1:'tpb_active',2:'tpb_wait'})
    @property
    def starting_party(self):return Party(self.store)
    @property
    def title(self):return Title(self.store)
    @property
    def player_start(self):return Position(self.store)
    @property
    def boat(self):return Vehicle(self.store,('boat',))
    @property
    def ship(self):return Vehicle(self.store,('ship',))
    @property
    def airship(self):return Vehicle(self.store,('airship',))
    @property
    def music(self):return AudioList(self.store,True)
    @property
    def sounds(self):return AudioList(self.store,False)
    @property
    def options(self):return Options(self.store)
    @property
    def window_tone(self):return deepcopy(self._data['windowTone'])
    def set_window_tone(self,red,green,blue,gray=0):
        """窗口色调：RGB -255–255，灰度 0–255。"""
        for v in [red,green,blue]:integer(v,-255,255)
        integer(gray,0,255);self._data['windowTone']=[red,green,blue,gray]
    def describe(self):
        keys=['gameTitle','currencyUnit','partyMembers','title1Name','title2Name','optDrawTitle',
              'titleCommandWindow','windowTone','optSideView','battleSystem','startMapId','startX','startY','boat','ship','airship','menuCommands','itemCategories','magicSkills','attackMotions','tileSize','iconSize','faceSize','editor','advanced']
        return '\n'.join(f'{k}: {self._data.get(k)!r}' for k in keys)+'\n'+self.options.list()+'\nMusic\n'+self.music.list()+'\nSound\n'+self.sounds.list()
