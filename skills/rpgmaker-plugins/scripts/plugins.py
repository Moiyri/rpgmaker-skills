"""插件统一入口：查询声明、编辑参数、管理注册及安全写入。

Python 使用 Plugins；CLI 使用 --project 查询，--file 执行底层预览、写入与恢复。
"""
import argparse
import sys
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import tempfile
from plugin_core import storage

class Plugins:
    """注册项编辑器。收集修改后 preview，再 commit(preview)；不编辑插件源码文件。"""
    def __init__(self,project):
        self.file=Path(project).resolve(strict=True)/'js/plugins.js'
        self.operations=[]
        self._parameter_source=None
        self._declarations={}
    def list(self):
        return storage.run(['--file',str(self.file),'inspect'])['plugins']
    def get(self,name):
        from plugin_core.model import Plugin
        record=storage.run(['--file',str(self.file),'inspect','--name',name])['plugins'][0]
        return Plugin(self,record)
    def add(self,name,*,enabled=False,description='',parameters=None,before=None,after=None):
        """注册插件，默认禁用。name 是相对路径，不含 .js；源码文件需先创建。"""
        path=Path(name)
        if path.is_absolute() or '..' in path.parts or '\\' in name:raise ValueError('Invalid plugin path')
        source=self.file.parent/'plugins'/path.with_suffix('.js')
        if not source.is_file() or not source.resolve().is_relative_to((self.file.parent/'plugins').resolve()):raise ValueError('Plugin source missing or outside plugins directory')
        op={'op':'add','plugin':{'name':name,'status':enabled,'description':description,'parameters':parameters or {}}}
        if before is not None:op['before']=before
        if after is not None:op['after']=after
        self.operations.append(op)
    def update(self,name,*,enabled=None,description=None,parameters=None,unset_parameters=None):
        """修改启停、说明或参数；参数值必须为字符串，未指定项保留。"""
        op={'op':'update','name':name}
        for key,value in [('status',enabled),('description',description),('parameters',parameters),('unset_parameters',unset_parameters)]:
            if value is not None:op[key]=value
        self.operations.append(op)
    def remove(self,name):
        """仅移除注册，不删除 .js 文件。"""
        self.operations.append({'op':'remove','name':name})
    def move(self,name,*,before=None,after=None):
        """调整加载顺序，before/after 必须且只能指定一项。"""
        op={'op':'move','name':name}
        if before is not None:op['before']=before
        if after is not None:op['after']=after
        self.operations.append(op)
    def _parameter_context(self,name,language):
        from plugin_core.values import metadata
        source=self.file.read_bytes()
        if self._parameter_source is not None and source!=self._parameter_source:
            raise ValueError('Plugin configuration changed; create a new Plugins object')
        records=storage.parse(source)[3]
        if self.operations:records=storage.transform(records,self._plan())
        matches=[p for p in records if p['name']==name]
        if len(matches)!=1:raise ValueError('Use exact registered plugin path')
        meta=metadata(self.file.parent.parent,name,language)
        return source,matches[0]['parameters'],meta
    def set_parameter(self,name,path,value,*,language='zh'):
        """按声明修改参数。路径如 ['Settings','Entries',0,'Enabled']，无需手工 JSON 编解码。

        数组下标从 0 开始；布尔值用 bool，数值用 int/float；结构体 dict 合并字段。
        缺失声明、非法编码、错误类型、越界下标或超出声明范围均拒绝。
        """
        from plugin_core.values import path_parts,field,walk,MISSING
        source,parameters,meta=self._parameter_context(name,language)
        path=path_parts(path);spec=field(meta['parameters'],path[0])
        updated=walk(spec,parameters.get(path[0],MISSING),path[1:],meta,value)
        declaration=Path(meta['source']);raw=declaration.read_bytes()
        if declaration in self._declarations and self._declarations[declaration]!=raw:
            raise ValueError('Plugin declaration changed; create a new Plugins object')
        self._parameter_source=source;self._declarations[declaration]=raw
        self.update(name,parameters={path[0]:updated})
    def _check_parameter_sources(self):
        if self._parameter_source is not None and self.file.read_bytes()!=self._parameter_source:
            raise ValueError('Plugin configuration changed; read parameters again')
        for path,source in self._declarations.items():
            if path.read_bytes()!=source:raise ValueError('Plugin declaration changed; read parameters again')
    def _plan(self):return {'version':1,'operations':deepcopy(self.operations)}
    def _fingerprint(self):return hashlib.sha256(json.dumps(self._plan(),sort_keys=True,ensure_ascii=True).encode()).hexdigest()
    def _run(self,preview=None):
        self._check_parameter_sources()
        with tempfile.TemporaryDirectory() as folder:
            plan=Path(folder)/'plan.json';plan.write_text(json.dumps(self._plan(),ensure_ascii=False),encoding='utf-8')
            args=['--file',str(self.file),'apply','--plan',str(plan)]
            if preview is not None:
                if preview['plan_sha256']!=self._fingerprint():raise ValueError('Plan changed; preview again')
                args+=['--write','--expect-sha256',preview['sha256']]
            result=storage.run(args);result['plan_sha256']=self._fingerprint();return result
    def preview(self):return self._run()
    def commit(self,preview):
        result=self._run(preview);self.operations.clear();self._parameter_source=None;self._declarations.clear();return result


def _inventory(project):
    root = Path(project).resolve(strict=True)
    parser = storage
    records = parser.parse((root / 'js/plugins.js').read_bytes())[3]
    folder = root / 'js/plugins'
    files = {}
    if folder.is_dir():
        for path in sorted(folder.rglob('*.js')):
            if not path.resolve().is_relative_to(folder.resolve()):
                continue
            files[path.relative_to(folder).with_suffix('').as_posix()] = path
    return root, records, files


def _name(value):
    if not isinstance(value,str) or not value or '\\' in value:
        raise ValueError('插件名无效')
    value = value[:-3] if value.endswith('.js') else value
    if Path(value).is_absolute() or '..' in Path(value).parts:
        raise ValueError('请使用插件相对路径')
    return value


def _select(records, files, plugin):
    query = _name(plugin)
    names = {r['name'] for r in records if r['name']} | set(files)
    matches = sorted(n for n in names if n==query or ('/' not in query and n.rsplit('/',1)[-1]==query))
    if len(matches)>1:
        raise ValueError('插件名不唯一，请指定路径：' + ', '.join(matches))
    name = matches[0] if matches else query
    rows = [(i,r) for i,r in enumerate(records) if r['name']==name]
    if len(rows)>1:
        raise ValueError('插件重复注册：' + name)
    return name, rows


def check_plugin(project, plugin) -> str:
    """返回文件、注册和启用状态；短名称有歧义时要求完整子目录路径。"""
    _,records,files = _inventory(project)
    name,rows = _select(records,files,plugin)
    exists = name in files
    registered = bool(rows)
    enabled = registered and rows[0][1]['status']
    state = '已启用' if exists and enabled else '文件缺失' if registered and not exists else '已禁用' if registered else '未注册' if exists else '未安装'
    return f'{name}：{state}\n文件：{"存在" if exists else "不存在"}；注册：{"是" if registered else "否"}；启用：{"是" if enabled else "否"}'


def list_plugins(project, *, search='', enabled_only=False) -> str:
    """按加载顺序列出注册项，再列出未注册文件；可按名称筛选。"""
    _,records,files = _inventory(project)
    lines=[]
    registered=set()
    for i,r in enumerate(records):
        name=r['name']
        if not name:continue
        registered.add(name)
        if search.lower() not in name.lower() or (enabled_only and not r['status']):continue
        state='启用' if r['status'] else '禁用'
        if name not in files:state+='，文件缺失'
        lines.append(f'{i+1}. {name} — {state}')
    if not enabled_only:
        lines.extend(f'{name} — 未注册' for name in sorted(set(files)-registered) if search.lower() in name.lower())
    return '\n'.join(lines) or '无匹配插件'


def plugin_parameters(project, plugin, *, parameter=None) -> str:
    """查询 plugins.js 当前参数值；指定 parameter 返回完整字符串，其余长值简写。"""
    _,records,files = _inventory(project)
    name,rows = _select(records,files,plugin)
    if not rows:raise ValueError('插件未注册：'+name)
    params=rows[0][1]['parameters']
    if parameter is not None:
        if parameter not in params:raise ValueError('参数不存在：'+parameter)
        return name+'\n'+parameter+' = '+params[parameter]
    return '\n'.join([name]+[k+' = '+(repr(v) if len(repr(v))<=100 else repr(v)[:100]+'…') for k,v in params.items()])


def plugin_help(project, plugin, *, struct=None, language='zh') -> str:
    """查询顶层结构；struct 指定结构体名称。"""
    root,records,files = _inventory(project)
    name,_ = _select(records,files,plugin)
    if name not in files:raise ValueError('插件文件不存在：'+name)
    from plugin_core.declarations import _plugin_metadata
    from plugin_core.model import structure_help
    return structure_help(_plugin_metadata(root,name,language=language),struct)


def plugin_manual(project, plugin, *, language='zh') -> str:
    """读取插件 @help 使用说明，不执行源码；缺失说明明确返回提示。"""
    root,records,files = _inventory(project)
    name,_ = _select(records,files,plugin)
    if name not in files:raise ValueError('插件文件不存在：'+name)
    from plugin_core.declarations import plugin_help as declaration_help
    return declaration_help(root,name,language=language,section='help')


def main():
    if any(arg == "--file" or arg.startswith("--file=") for arg in sys.argv[1:]):
        return storage.main()
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project',required=True)
    sub=parser.add_subparsers(dest='action',required=True)
    p=sub.add_parser('list');p.add_argument('--search',default='');p.add_argument('--enabled',action='store_true')
    for action in ('check','parameters','help','manual'):
        p=sub.add_parser(action);p.add_argument('--plugin',required=True)
        if action=='parameters':p.add_argument('--parameter')
        if action=='help':p.add_argument('--struct')
        if action in ('help','manual'):p.add_argument('--language',default='zh')
    args=parser.parse_args()
    try:
        if args.action=='list':result=list_plugins(args.project,search=args.search,enabled_only=args.enabled)
        elif args.action=='check':result=check_plugin(args.project,args.plugin)
        elif args.action=='parameters':result=plugin_parameters(args.project,args.plugin,parameter=args.parameter)
        elif args.action=='manual':result=plugin_manual(args.project,args.plugin,language=args.language)
        else:result=plugin_help(args.project,args.plugin,struct=args.struct,language=args.language)
        print(result);return 0
    except (ValueError,OSError,UnicodeError) as exc:
        print(str(exc),file=sys.stderr);return 1


if __name__=='__main__':
    sys.exit(main())
