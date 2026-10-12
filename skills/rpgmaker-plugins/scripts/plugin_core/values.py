"""Declaration-driven plugin parameter paths. Encoded containers are traversed only as declared."""
import json
import math
import re
from decimal import Decimal
from .declarations import _plugin_metadata

MISSING = object()

def metadata(project, name, language='zh'):
    return _plugin_metadata(project, name, language=language)

def field(fields, name):
    matches = [f for f in fields if f['name'] == name]
    if len(matches) != 1: raise ValueError('Missing or ambiguous declaration: ' + str(name))
    return matches[0]

def path_parts(path):
    path = [path] if isinstance(path, str) else list(path)
    if not path or not isinstance(path[0], str): raise ValueError('Path must start with parameter name')
    if any(type(p) not in (str,int) for p in path): raise ValueError('Path components must be field names or integer indexes')
    return path

def kind(spec): return spec.get('type', 'string')

def container(spec, raw, meta):
    t = kind(spec)
    if t.endswith('[]'):
        expected = list; child = dict(spec, type=t[:-2])
    elif re.fullmatch(r'struct<[^>]+>', t):
        expected = dict; name = t[7:-1]
        if name not in meta['structs']: raise ValueError('Missing struct declaration: ' + name)
        child = meta['structs'][name]
    else: raise ValueError('Path cannot descend into declared scalar: ' + t)
    if raw is MISSING: raise ValueError('Container missing; explicitly set it first')
    try: value = json.loads(raw) if isinstance(raw,str) else raw
    except (ValueError,TypeError) as exc: raise ValueError('Invalid encoded '+t) from exc
    if not isinstance(value,expected): raise ValueError('Expected '+t+' container')
    return value,child

def repack(value,original):
    return json.dumps(value,ensure_ascii=False,separators=(',',':')) if isinstance(original,str) else value

def walk(spec,raw,parts,meta,replacement=MISSING,operation=None):
    if not parts:
        if operation is not None:return operation(spec,raw)
        return (spec,raw) if replacement is MISSING else encode(spec,replacement,meta,raw)
    values,children=container(spec,raw,meta);key=parts[0]
    if isinstance(values,list):
        if type(key) is not int or not 0 <= key < len(values): raise ValueError('Array index out of range')
        child=children
    else:
        if not isinstance(key,str): raise ValueError('Struct field must be a name')
        child=field(children,key)
    value=walk(child,values[key] if key in values else MISSING,parts[1:],meta,replacement,operation) if isinstance(values,dict) else walk(child,values[key],parts[1:],meta,replacement,operation)
    if replacement is MISSING and operation is None:return value
    values[key]=value
    return repack(values,raw)

def encode(spec,value,meta,old=MISSING):
    """Native Python value -> declared engine encoding; unknown sibling fields stay untouched."""
    t=kind(spec)
    if t.endswith('[]'):
        if not isinstance(value,list):raise ValueError('Expected Python list')
        prior=[] if old is MISSING else container(spec,old,meta)[0]
        child=dict(spec,type=t[:-2])
        # Arrays produced by the RM editor store entries as strings.
        result=[encode(child,v,meta,prior[i] if i<len(prior) else MISSING) for i,v in enumerate(value)]
        return repack(result,old if old is not MISSING else '')
    if re.fullmatch(r'struct<[^>]+>',t):
        if not isinstance(value,dict):raise ValueError('Expected Python dict for struct')
        fields=meta['structs'].get(t[7:-1])
        if fields is None:raise ValueError('Missing struct declaration: '+t)
        result={} if old is MISSING else container(spec,old,meta)[0].copy()
        for key,v in value.items():result[key]=encode(field(fields,key),v,meta,result.get(key,MISSING))
        return repack(result,old if old is not MISSING else '')
    if t=='note':
        if not isinstance(value,str):raise ValueError('Expected string for note')
        if old is not MISSING:
            try: decoded=json.loads(old)
            except (ValueError,TypeError) as exc:raise ValueError('Invalid encoded note') from exc
            if not isinstance(decoded,str):raise ValueError('Expected encoded note string')
        return json.dumps(value,ensure_ascii=False)
    if t=='boolean':
        if type(value) is not bool:raise ValueError('Expected Python bool')
        native=value;text='true' if value else 'false'
    elif t=='number' or t in ('actor','class','skill','item','weapon','armor','enemy','troop','state','animation','tileset','common_event','switch','variable'):
        if type(value) not in (int,float) or not math.isfinite(value):raise ValueError('Expected finite number')
        decimals=int(spec.get('decimals','0')) if t=='number' else 0
        if Decimal(str(value)) != Decimal(str(value)).quantize(Decimal(1).scaleb(-decimals)):raise ValueError('Too many decimal places')
        for bound,check in [('min',lambda n:value<n),('max',lambda n:value>n)]:
            if bound in spec and check(float(spec[bound])):raise ValueError('Outside declared '+bound)
        native=value;text=str(value)
    elif t=='select':
        text=str(value) if type(value) in (str,int,float) else None
        if text not in [o['value'] for o in spec.get('options',[])]:raise ValueError('Expected declared option value')
        native=value
    else:
        if not isinstance(value,str):raise ValueError('Expected string for '+t)
        native=value;text=value
    return native if old is not MISSING and not isinstance(old,str) else text

def describe(spec,raw,path):
    limits=' '.join(k+'='+spec[k] for k in ('min','max','decimals') if k in spec)
    if raw is MISSING:current='未配置'
    elif kind(spec).endswith('[]'):
        try:current=f'{len(json.loads(raw) if isinstance(raw,str) else raw)} 项'
        except (ValueError,TypeError):current='编码无效'
    elif kind(spec).startswith('struct<'):current='结构体'
    else:
        if kind(spec)=='note':
            try:raw=json.loads(raw)
            except (ValueError,TypeError):pass
        current=repr(raw);current=current if len(current)<=70 else current[:67]+'…'
    text=f'{path!r} | {spec.get("text",spec["name"])} | {kind(spec)} | 当前 {current}'
    if raw is MISSING and 'default' in spec:text+=' | 默认 '+repr(spec['default'])[:70]
    if spec.get('desc'):text+='\n  '+' '.join(spec['desc'].split())
    if spec.get('options'):text+='\n  可选：'+'; '.join(o['value']+'='+o['text'] for o in spec['options'])
    if limits:text+='\n  '+limits
    return text

def decode(spec,raw,meta):
    """Decode declared fields to native values; unknown struct fields remain raw."""
    if raw is MISSING:raise ValueError('Parameter is not configured')
    t=kind(spec)
    if t.endswith('[]') or t.startswith('struct<'):
        values,children=container(spec,raw,meta)
        if isinstance(values,list):return [decode(children,v,meta) for v in values]
        result=values.copy()
        for s in children:
            if s['name'] in result:result[s['name']]=decode(s,result[s['name']],meta)
        return result
    if t=='note':
        result=json.loads(raw)
        if not isinstance(result,str):raise ValueError('Invalid note')
        return result
    if t=='boolean':
        if raw in ('true',True):return True
        if raw in ('false',False):return False
        raise ValueError('Invalid boolean')
    if t=='number':
        result=json.loads(raw) if isinstance(raw,str) else raw
        if type(result) not in (int,float):raise ValueError('Invalid number')
        return result
    return raw


def default_value(spec,meta,seen=()):
    """Decode explicitly declared defaults for a new array item."""
    if 'default' in spec:return decode(spec,spec['default'],meta)
    t=kind(spec)
    if t.endswith('[]'):raise ValueError('No declared default: '+spec['name'])
    if t.startswith('struct<'):
        name=t[7:-1]
        if name in seen:raise ValueError('Recursive default requires explicit values')
        fields=meta['structs'].get(name)
        if fields is None:raise ValueError('Missing struct '+name)
        return {s['name']:default_value(s,meta,seen+(name,)) for s in fields if 'default' in s or kind(s).startswith('struct<')}
    raise ValueError('No declared default: '+spec['name'])
