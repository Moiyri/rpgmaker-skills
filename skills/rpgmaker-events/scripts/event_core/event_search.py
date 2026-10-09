"""按名称、开关和变量查询地图与公共事件；不执行脚本。"""
from __future__ import annotations
from pathlib import Path
import re
from .backend import db, require
from .compiler import integer


def map_files(root):
    return sorted(p.name for p in root.glob('Map[0-9]*.json') if re.fullmatch(r'Map\d{3,}\.json',p.name))


def map_names(root):
    file=root/'MapInfos.json'
    if not file.exists(): return {}
    data=db.read_document(db.file_path(root,'MapInfos.json').read_bytes())
    return {entry['id']:entry['name'] for entry in data if entry}


def page_summary(page, index):
    return {'page_index':index,'page_number':index+1,'conditions':page['conditions'],
            'image':page['image'],'trigger':page['trigger'],'priority':page['priorityType'],
            'movement':{k:page[k] for k in ('moveType','moveSpeed','moveFrequency')},
            'options':{k:page[k] for k in ('walkAnime','stepAnime','directionFix','through')},
            'command_count':len(page['list'])}


def list_map(project, map_id):
    """列出指定地图所有事件，每个事件一条，包含坐标和页摘要。"""
    root=db.root_path(Path(project).resolve()/'data'); integer(map_id,1)
    name=f'Map{map_id:03}.json'; raw=db.file_path(root,name).read_bytes(); data=db.read_document(raw)
    names=map_names(root)
    return {'map_id':map_id,'map_name':names.get(map_id,''),'width':data['width'],'height':data['height'],
            'file_sha256':db.sha(raw),'events':[
                {'event_id':e['id'],'name':e['name'],'note':e['note'],'x':e['x'],'y':e['y'],
                 'pages':[page_summary(p,i) for i,p in enumerate(e['pages'])]} for e in data['events'] if e]}


def references(commands, kind, wanted):
    """查找已知原生指令的静态 ID 引用，不匹配普通数值常量。"""
    matches=[]
    def add(index, role, ids):
        if wanted in ids: matches.append({'command_index':index,'role':role})
    for i,c in enumerate(commands):
        code=c['code']; p=c['parameters']
        try:
            if kind=='switch':
                if code==121 and p[0]<=wanted<=p[1]: add(i,'write', [wanted])
                if code==111 and p[0]==0: add(i,'read',[p[1]])
                if code==205:
                    for j,route in enumerate(p[1]['list']):
                        if route['code'] in (27,28) and route['parameters'][0]==wanted:
                            matches.append({'command_index':i,'route_index':j,'role':'write'})
            else:
                if code==122:
                    if p[0]<=wanted<=p[1]: add(i,'write',[wanted])
                    if p[3]==1: add(i,'read',[p[4]])
                elif code==111 and p[0]==1:
                    add(i,'read',[p[1]])
                    if p[2]==1: add(i,'read_operand',[p[3]])
                elif code in (103,104): add(i,'write',[p[0]])
                elif code==201 and p[0]==1: add(i,'read',p[1:4])
                elif code==202 and p[1]==1: add(i,'read',p[2:5])
                elif code==203 and p[1]==1: add(i,'read',p[2:4])
                elif code in (231,232) and p[3]==1: add(i,'read',p[4:6])
                elif code==285:
                    add(i,'write',[p[0]])
                    if p[2]==1: add(i,'read',p[3:5])
                elif code==301 and p[0]==1: add(i,'read',[p[1]])
                elif code==125 and p[1]==1: add(i,'read',[p[2]])
                elif code in (126,127,128) and p[2]==1: add(i,'read',[p[3]])
                elif code in (311,312,315,316,326):
                    if p[0]==1: add(i,'read_actor',[p[1]])
                    if p[3]==1: add(i,'read_operand',[p[4]])
                elif code==317:
                    if p[0]==1: add(i,'read_actor',[p[1]])
                    if p[4]==1: add(i,'read_operand',[p[5]])
                elif code in (313,314,318) and p[0]==1: add(i,'read_actor',[p[1]])
                elif code in (331,332,342) and p[2]==1: add(i,'read_operand',[p[3]])
        except (IndexError,KeyError,TypeError):
            matches.append({'command_index':i,'role':'unparsed','warning':'Malformed or extended parameters; inspect manually'})
    return matches


def search_events(project, *, name=None, switch=None, variable=None, map_id=None, kind=None):
    """全局按事件名或开关／变量引用查询；多个条件按 AND 组合。

    搜索页出现条件、公共事件触发开关、原生事件指令及移动路线开关。
    脚本、插件参数和动态计算 ID 不作静态推断，结果不代表动态引用完整。
    """
    require(any(x is not None for x in (name,switch,variable)), 'Provide name, switch or variable')
    require(kind in (None,'common','map'),'Invalid kind')
    if switch is not None: integer(switch,1)
    if variable is not None: integer(variable,1)
    if map_id is not None: integer(map_id,1)
    root=db.root_path(Path(project).resolve()/'data'); names=map_names(root); results=[]
    def collect(target,event_name,commands,conditions=None,route=None,trigger_switch=None,extra=None):
        if name is not None and name.casefold() not in event_name.casefold(): return
        hits=[]
        for category,wanted in [('switch',switch),('variable',variable)]:
            if wanted is None: continue
            found=references(commands,category,wanted)
            # Parse warnings cannot count as an actual reference match.
            found=[h for h in found if h['role']!='unparsed']
            if conditions:
                for key in (('switch1','switch2') if category=='switch' else ('variable',)):
                    if conditions.get(key+'Valid') and conditions.get(key+'Id')==wanted:
                        found.append({'source':'page_condition','field':key,'role':'read'})
            if category=='switch':
                if trigger_switch==wanted: found.append({'source':'common_trigger','role':'read'})
                if route:
                    for i,c in enumerate(route['list']):
                        if c['code'] in (27,28) and c.get('parameters',[])==[wanted]:
                            found.append({'source':'autonomous_route','route_index':i,'role':'write'})
            if not found: return
            hits.extend({'kind':category,'id':wanted,**h} for h in found)
        results.append({'target':target,'name':event_name,'matches':hits,**(extra or {})})
    if kind!='map' and map_id is None and (root/'CommonEvents.json').exists():
        for e in db.read_document(db.file_path(root,'CommonEvents.json').read_bytes()):
            if e: collect({'kind':'common','id':e['id']},e['name'],e['list'],
                          trigger_switch=e['switchId'] if e['trigger'] in (1,2) else None)
    if kind!='common':
        for file in map_files(root):
            mid=int(Path(file).stem[3:])
            if map_id is not None and mid!=map_id: continue
            data=db.read_document(db.file_path(root,file).read_bytes())
            for e in data['events']:
                if not e: continue
                for i,p in enumerate(e['pages']):
                    collect({'kind':'map','map_id':mid,'event_id':e['id'],'page_index':i},e['name'],p['list'],
                            p['conditions'],p['moveRoute'],extra={'map_name':names.get(mid,''),'x':e['x'],'y':e['y'],'page_number':i+1})
    return {'total':len(results),'results':results,
            'scope':'Map/common events; page conditions, common triggers, known native command references and movement switches',
            'limitations':['Script/plugin/dynamic references are not resolved.','Malformed or unknown parameter formats may require manual inspection.']}
