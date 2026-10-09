"""按原生字段语义查询物品引用，不将任意相同数字当作引用。"""
from dataclasses import dataclass, field
from .backend import db


@dataclass(frozen=True)
class ItemReference:
    """一处引用：文件、原始字段路径、用途。指令／页下标从 0 开始。"""
    file: str
    path: tuple
    usage: str


@dataclass
class ReferenceReport:
    """可遍历的引用报告；未扫描范围与警告始终在文本末尾显示。"""
    matches: list = field(default_factory=list)
    warnings: list = field(default_factory=list)
    def __iter__(self):return iter(self.matches)
    def __len__(self):return len(self.matches)
    def __str__(self):
        lines=[f'原生引用 {len(self)} 处']
        lines.extend(f'{m.file} {list(m.path)} — {m.usage}' for m in self.matches)
        lines.extend(self.warnings)
        lines.append('限制：脚本、伤害公式、备注标签及插件动态引用未解析；无结果不代表无引用。查询磁盘文件，不含未提交修改。')
        return '\n'.join(lines)


def find_item_references(root, item_id):
    report=ReferenceReport()
    def add(file,path,usage):report.matches.append(ItemReference(file,tuple(path),usage))
    def commands(file,path,values):
        for i,c in enumerate(values):
            code=c.get('code');p=c.get('parameters',[]);base=path+[i,'parameters']
            if code==126 and len(p)>=1 and p[0]==item_id:add(file,base+[0],'更改物品')
            elif code==111 and len(p)>=2 and p[0]==8 and p[1]==item_id:add(file,base+[1],'物品持有条件')
            elif code in (302,605) and len(p)>=2 and p[0]==0 and p[1]==item_id:add(file,base+[1],'商店商品')
            elif code==122 and len(p)>=6 and p[3]==3 and p[4]==0 and p[5]==item_id:add(file,base+[5],'变量：物品持有数')
    names=['CommonEvents.json','Troops.json','Enemies.json']
    names += sorted(p.name for p in root.glob('Map[0-9][0-9][0-9]*.json') if p.stem[3:].isdigit())
    for file in names:
        if not (root/file).exists():
            report.warnings.append(f'未扫描：{file} 不存在');continue
        data=db.read_document(db.file_path(root,file).read_bytes())
        if file=='Enemies.json':
            for i,enemy in enumerate(data):
                if not enemy:continue
                for j,drop in enumerate(enemy.get('dropItems',[])):
                    if drop.get('kind')==1 and drop.get('dataId')==item_id:add(file,[i,'dropItems',j,'dataId'],'敌人掉落')
        elif file=='CommonEvents.json':
            for i,event in enumerate(data):
                if event:commands(file,[i,'list'],event['list'])
        else:
            records=data if file=='Troops.json' else data['events']
            for i,event in enumerate(records):
                if not event:continue
                for j,page in enumerate(event['pages']):
                    path=([i] if file=='Troops.json' else ['events',i])+['pages',j]
                    condition=page.get('conditions',{})
                    if file!='Troops.json' and condition.get('itemValid') and condition.get('itemId')==item_id:
                        add(file,path+['conditions','itemId'],'地图页出现条件')
                    commands(file,path+['list'],page['list'])
    return report
