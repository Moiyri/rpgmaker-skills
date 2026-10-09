"""物品数据库 API。使用 help(Database)、help(Item) 和 help(效果类) 查看用法。"""
from database_core.session import Database, Preview
from database_core.items import Item, Damage, Items, ITEM_TYPES, SCOPES, OCCASIONS, HIT_TYPES, DAMAGE_TYPES
from database_core.effects import (Effects, RecoverHP, RecoverMP, GainTP, AddState, RemoveState,
                                  AddBuff, AddDebuff, RemoveBuff, RemoveDebuff, Escape,
                                  GrowParameter, LearnSkill, CommonEventEffect, OpaqueEffect, PARAMETERS)
__all__=['Database','Preview','Item','Damage','Items','Effects','RecoverHP','RecoverMP','GainTP','AddState','RemoveState',
         'AddBuff','AddDebuff','RemoveBuff','RemoveDebuff','Escape','GrowParameter','LearnSkill','CommonEventEffect',
         'OpaqueEffect','PARAMETERS','ITEM_TYPES','SCOPES','OCCASIONS','HIT_TYPES','DAMAGE_TYPES']

from database_core.actors import Actor, Actors
__all__ += ['Actor', 'Actors']
