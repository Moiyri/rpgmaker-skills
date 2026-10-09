"""地图删除、缩小的静态引用检查。"""
from .backend import db


def check_map_references(root,map_id,width=None,height=None):
    operations=[];blocked=[]
    def check(mid,x,y,label):
        if mid==map_id and (width is None or not (0<=x<width and 0<=y<height)):blocked.append(label)
    files=['System.json','CommonEvents.json','Troops.json']+[p.name for p in root.glob('Map[0-9]*.json') if p.stem[3:].isdigit()]
    for name in files:
        if not (root/name).exists():continue
        data=db.read_document(db.file_path(root,name).read_bytes())
        operations.append(dict(op='test',file=name,path=[],expect=data))
        if name=='System.json':
            for key in [None,'boat','ship','airship']:
                v=data if key is None else data.get(key,{})
                check(v.get('startMapId'),v.get('startX',0),v.get('startY',0),f'System {key or "player"}')
            continue
        # An event inside a deleted map vanishes with the map.
        if width is None and name==f'Map{map_id:03d}.json':continue
        if name=='CommonEvents.json':lists=[(str(i),e['list']) for i,e in enumerate(data) if e]
        else:
            events=data if name=='Troops.json' else data['events']
            lists=[(f'{i}/page{j+1}',p['list']) for i,e in enumerate(events) if e for j,p in enumerate(e['pages'])]
        for label,commands in lists:
            for index,c in enumerate(commands):
                p=c['parameters'];code=c['code']
                if code==201 and len(p)>=4 and p[0]==0:check(p[1],p[2],p[3],f'{name} {label} command {index}')
                if code==202 and len(p)>=5 and p[1]==0:check(p[2],p[3],p[4],f'{name} {label} vehicle {index}')
    db.require(not blocked,'Map references would become invalid: '+', '.join(blocked))
    return operations
