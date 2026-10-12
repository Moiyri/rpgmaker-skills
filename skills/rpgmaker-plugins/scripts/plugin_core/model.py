"""Plugin model: compact declaration catalog and group details with editable paths."""
from pathlib import Path
from . import values as v

class Parameters:
    def __init__(self, plugin):self.plugin=plugin
    def _context(self):
        return self.plugin.owner._parameter_context(self.plugin['name'],'zh')
    def list(self,struct=None):
        """无参数列出总目录；传结构体名称列出其全部直接字段和类型。"""
        _,_,meta=self._context()
        if struct is not None:
            if not isinstance(struct,str) or struct not in meta['structs']:
                raise ValueError('Unknown struct: '+str(struct))
            fields=meta['structs'][struct]
            return '\n'.join([meta['plugin']+' — '+struct]+[
                '  '+field['name']+' : '+v.kind(field) for field in fields
            ]+([] if fields else ['  无字段']))
        lines=[meta['plugin'], '', '顶层参数']
        lines.extend('  '+field['name']+' : '+v.kind(field) for field in meta['parameters'])
        if not meta['parameters']:lines.append('  无')
        lines+=['', '结构体']
        lines.extend('  '+name for name in meta['structs'])
        if not meta['structs']:lines.append('  无')
        return '\n'.join(lines)
    def help(self,struct=None):
        _,params,meta=self._context()
        return structure_help(meta,struct)
    def get(self,path):
        _,params,meta=self._context();parts=v.path_parts(path)
        spec,raw=v.walk(v.field(meta['parameters'],parts[0]),params.get(parts[0],v.MISSING),parts[1:],meta)
        return v.decode(spec,raw,meta)
    def set(self,path,value):self.plugin.owner.set_parameter(self.plugin['name'],path,value)
    def item_defaults(self,path):
        """New array item from declared defaults; caller fills required fields before append."""
        _,params,meta=self._context();parts=v.path_parts(path)
        spec,_=v.walk(v.field(meta['parameters'],parts[0]),params.get(parts[0],v.MISSING),parts[1:],meta)
        if not v.kind(spec).endswith('[]'):raise ValueError('Expected array')
        # Array default is not an element default.
        child={k:value for k,value in spec.items() if k!='default'};child['type']=v.kind(spec)[:-2]
        return v.default_value(child,meta)
    def append(self,path,value):
        """Append one native value without rewriting existing encoded array items."""
        owner=self.plugin.owner;source,params,meta=self._context();parts=v.path_parts(path)
        def append_value(spec,raw):
            if not v.kind(spec).endswith('[]'):raise ValueError('Expected array')
            items,child=v.container(spec,raw,meta)
            items.append(v.encode(child,value,meta))
            return v.repack(items,raw)
        updated=v.walk(v.field(meta['parameters'],parts[0]),params.get(parts[0],v.MISSING),parts[1:],meta,operation=append_value)
        declaration=Path(meta['source']);raw=declaration.read_bytes()
        if declaration in owner._declarations and owner._declarations[declaration]!=raw:raise ValueError('Declaration changed')
        owner._parameter_source=source;owner._declarations[declaration]=raw
        owner.update(self.plugin['name'],parameters={parts[0]:updated})

class Commands:
    def __init__(self,plugin):self.plugin=plugin
    def list(self):
        from .declarations import plugin_help
        return plugin_help(self.plugin.owner.file.parent.parent,self.plugin['name'])
    def help(self,name):
        from .declarations import plugin_help
        return plugin_help(self.plugin.owner.file.parent.parent,self.plugin['name'],command=name)

class Plugin(dict):
    """Dictionary-compatible registered plugin plus declaration-driven helpers."""
    def __init__(self,owner,record):
        super().__init__(record);self.owner=owner;self.parameters=Parameters(self);self.commands=Commands(self)
    def help(self,struct=None):return self.parameters.help(struct)

def structure_help(meta,struct=None):
    """列出顶层参数或指定结构体的直接字段，不展开实例数据。"""
    if struct is not None and not isinstance(struct,str):
        raise ValueError('struct 必须是结构体名称')
    if struct is None:
        fields=meta['parameters'];title=meta['plugin']+' — 顶层结构'
    else:
        if struct not in meta['structs']:raise ValueError('Unknown struct: '+struct)
        fields=meta['structs'][struct];title=meta['plugin']+' — struct '+struct
    def label(field):
        return field.get('text',field['name'])
    parents={f.get('parent') for f in fields if f.get('parent')}
    groups={f['name']:f for f in fields if f['name'] in parents and v.kind(f) in ('string','text')}
    def decorative(f):
        text=f.get('text',f['name']).strip()
        return (text and all(c in '-=─ ' for c in text)) or (
            meta['plugin'].rsplit('/',1)[-1]=='VisuMZ_1_MessageCore' and
            f['name'] in ('MessageCore','ATTENTION','End Of'))
    lines=[title];options={};last_group=None
    for field in fields:
        if decorative(field) or field['name'] in groups:continue
        parent=field.get('parent')
        if parent in groups and parent!=last_group:
            lines+=['',label(groups[parent])];last_group=parent
        kind=v.kind(field)
        type_text={'boolean':'布尔','number':'数值','string':'文本','text':'文本','multiline_string':'多行文本','file':'资源文件'}.get(kind,kind)
        if kind.startswith('struct<'):type_text=kind[7:].replace('>','')
        choices=field.get('options',[])
        if choices:
            key=tuple((o['value'],o['text']) for o in choices)
            if len(choices)<=4:
                type_text=' / '.join(o['value'] if o['value']==o['text'] else o['value']+' ('+o['text']+')' for o in choices)
            else:
                if key not in options:options[key]='选项'+str(len(options)+1)
                type_text=options[key]
            if kind.endswith('[]'):type_text+=' 列表'
        limits=[]
        for key in ('min','max','decimals'):
            if key in field:limits.append(key+'='+field[key])
        if limits:type_text+=' ('+', '.join(limits)+')'
        lines.append('  '+field['name']+' | '+label(field)+' | '+type_text)
    for choices,name in options.items():
        lines+=['',name+'：'+', '.join(value if value==text else value+' ('+text+')' for value,text in choices)]
    if len(lines)==1:lines.append('无字段')
    return '\n'.join(lines)
