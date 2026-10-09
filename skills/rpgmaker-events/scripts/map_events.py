#!/usr/bin/env python3
"""查询并编辑地图事件。正式写入委托 database.py，默认仅预览。"""
from pathlib import Path
import argparse
import json
import re
import sys

from event_core.backend import db, require
from event_core.map_events import MapDocument, validate_event
from event_core.event_search import list_map, search_events
from events import source_profile
import hashlib


def page_source_profile(project):
    profile = source_profile(project, True)
    config = db.loads((Path(__file__).parent.parent/'references/engine-profile.json').read_text())
    source = (project/'js/rmmz_objects.js').read_text(encoding='utf-8')
    for name, expected in config['map_event_methods'].items():
        match = re.search(r'^Game_Event\.prototype\.'+re.escape(name)+r' = function\([^)]*\) \{.*?^\};',source,re.M|re.S)
        require(match is not None and hashlib.sha256(match.group().encode()).hexdigest()==expected,
                f'Map event engine method differs: {name}')
    return profile


def prepare(project, plan):
    """校验地图事件计划，生成可审核差异和绑定源数据的预览指纹。"""
    root=db.root_path(project/'data')
    require(plan.get('format')=='preserve','Map plans require format=preserve')
    for op in plan.get('operations',[]):
        require(re.fullmatch(r'Map\d{3,}\.json',op.get('file','')) is not None,'Only existing map files')
        require((op.get('op')=='test' and op.get('path')==[]) or
                (op.get('op')=='set' and op.get('path')==['events']), 'Use MapDocument.to_plan()')
    # Every replacement must be guarded by a preceding original-map assertion.
    guarded=set()
    for op in plan.get('operations',[]):
        if op['op']=='test': guarded.add(op['file'])
        else: require(op['file'] in guarded,'Missing source snapshot test')
    profile=page_source_profile(project)
    originals,updated,_=db.prepare(root,plan)
    changes=[]
    for name,raw in originals.items():
        old=db.read_document(raw); new=db.read_document(updated[name])
        rows=new['events']; require(isinstance(rows,list) and (not rows or rows[0] is None),'Event slot 0 must be null')
        require(len(rows)>=len(old['events']),'Do not shrink event ID array; delete to null')
        for index,value in enumerate(rows):
            prior=old['events'][index] if index<len(old['events']) else None
            if db.equal(value,prior): continue
            if value is not None:
                require(value['id']==index,'Event ID/index mismatch'); validate_event(value,new,prior)
            changes.append({'file':name,'event_id':index,'before':prior,'after':value})
    result=db.preview_result(root,originals,updated,{'map_plan':plan,'source_profile':profile})
    result.update(changes=changes,source_profile=profile)
    result['warnings']=['Page order changes activation priority. Deleted event references are not automatically repaired.']
    return root,originals,updated,result


def run(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project',required=True,type=Path)
    sub=parser.add_subparsers(dest='action',required=True)
    p=sub.add_parser('list');p.add_argument('--map-id',required=True,type=int)
    p=sub.add_parser('inspect');p.add_argument('--map-id',required=True,type=int);p.add_argument('--event-id',required=True,type=int)
    p=sub.add_parser('search')
    p.add_argument('--name');p.add_argument('--switch',type=int);p.add_argument('--variable',type=int)
    p.add_argument('--map-id',type=int);p.add_argument('--kind',choices=['map','common'])
    p=sub.add_parser('apply');p.add_argument('--plan',required=True,type=Path)
    p.add_argument('--write',action='store_true');p.add_argument('--expect-preview')
    args=parser.parse_args(argv);project=args.project.resolve(strict=True)
    if args.action=='list': return list_map(project,args.map_id)
    if args.action=='search': return search_events(project,name=args.name,switch=args.switch,variable=args.variable,map_id=args.map_id,kind=args.kind)
    if args.action=='inspect':
        doc=MapDocument(project,args.map_id)
        return {'map_id':args.map_id,'event':doc.event(args.event_id).to_data(),'map_sha256':db.sha(db.file_path(doc.root,doc.file).read_bytes())}
    plan=db.loads(args.plan.read_text(encoding='utf-8-sig'))
    root,before,after,result=prepare(project,plan)
    require(not args.write or args.expect_preview,'--write requires --expect-preview')
    if args.expect_preview: require(args.expect_preview==result['preview_sha256'],'Preview mismatch; source or plan changed')
    if args.write and result['changed']:
        require(page_source_profile(project)==result['source_profile'],'Engine changed during preparation')
        result['transaction']=db.commit(root,before,after);result['written']=True
    return result


if __name__=='__main__':
    try:
        print(db.dumps({'ok':True,**run()},indent=2))
    except (ValueError,OSError,KeyError,TypeError,IndexError,RecursionError) as exc:
        print(json.dumps({'ok':False,'error':str(exc)},ensure_ascii=False),file=sys.stderr)
        sys.exit(1)
