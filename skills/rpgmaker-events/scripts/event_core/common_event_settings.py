"""公共事件元数据计划；指令沿用 EventList/events.py。"""
from pathlib import Path
from .backend import db


def common_event_settings_plan(project,id,*,name=None,trigger=None,switch_id=None):
    """返回正式数据库计划，仅修改给出的名称／触发设置，保留全部指令。

    trigger: none / autorun / parallel。目标须已存在；创建、删除交给数据库技能。
    用 database.py apply 预览和提交。省略字段不改变。
    """
    root=db.root_path(Path(project)/'data')
    records=db.read_document(db.file_path(root,'CommonEvents.json').read_bytes())
    db.require(type(id) is int and 0<id<len(records) and isinstance(records[id],dict) and records[id]['id']==id,'Missing common event')
    ops=[dict(op='test',file='CommonEvents.json',path=[id],expect=records[id])]
    updates={}
    if name is not None:
        db.require(isinstance(name,str),'Expected name');updates['name']=name
    if trigger is not None:
        db.require(trigger in ['none','autorun','parallel'],'Unknown trigger');updates['trigger']=['none','autorun','parallel'].index(trigger)
    if switch_id is not None:
        db.require(type(switch_id) is int and switch_id>0,'Expected positive switch ID');updates['switchId']=switch_id
    if updates.get('trigger',records[id]['trigger'])!=0 or switch_id is not None:
        system=db.read_document(db.file_path(root,'System.json').read_bytes())
        sid=updates.get('switchId',records[id]['switchId'])
        db.require(type(sid) is int and 0<sid<len(system['switches']),'Missing trigger switch')
        ops.append(dict(op='test',file='System.json',path=['switches'],expect=system['switches']))
    for key,value in updates.items():ops.append(dict(op='set',file='CommonEvents.json',path=[id,key],value=value))
    return dict(version=1,format='preserve',operations=ops)
