"""插件查询入口：列表、安装状态、当前参数和声明用法。"""
import argparse
import importlib.util
from pathlib import Path
import sys

SKILLS = Path(__file__).resolve().parents[2]


def _module(name, path):
    if not path.is_file():
        raise ValueError(f'缺少依赖：{path}')
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _inventory(project):
    root = Path(project).resolve(strict=True)
    parser = _module('plugin_manifest_query', SKILLS / 'rpgmaker-plugins/scripts/plugins_js.py')
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


def plugin_help(project, plugin, **options) -> str:
    """查询参数声明、命令和用法；默认命令概要，command/section/struct 展开详情。"""
    root,records,files = _inventory(project)
    name,_ = _select(records,files,plugin)
    if name not in files:raise ValueError('插件文件不存在：'+name)
    helper=_module('plugin_declaration_query', SKILLS/'rpgmaker-events/scripts/event_core/plugin_help.py')
    return helper.plugin_help(root,name,**options)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project',required=True)
    sub=parser.add_subparsers(dest='action',required=True)
    p=sub.add_parser('list');p.add_argument('--search',default='');p.add_argument('--enabled',action='store_true')
    for action in ('check','parameters','help'):
        p=sub.add_parser(action);p.add_argument('--plugin',required=True)
        if action=='parameters':p.add_argument('--parameter')
        if action=='help':
            p.add_argument('--command');p.add_argument('--struct')
            p.add_argument('--section',choices=['commands','parameters','help'],default='commands')
            p.add_argument('--language',default='zh')
    args=parser.parse_args()
    try:
        if args.action=='list':result=list_plugins(args.project,search=args.search,enabled_only=args.enabled)
        elif args.action=='check':result=check_plugin(args.project,args.plugin)
        elif args.action=='parameters':result=plugin_parameters(args.project,args.plugin,parameter=args.parameter)
        else:result=plugin_help(args.project,args.plugin,command=args.command,section=args.section,struct=args.struct,language=args.language)
        print(result);return 0
    except (ValueError,OSError,UnicodeError) as exc:
        print(str(exc),file=sys.stderr);return 1


if __name__=='__main__':
    sys.exit(main())
