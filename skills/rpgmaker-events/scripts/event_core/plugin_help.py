"""只读解析 RPG Maker 插件声明，不执行 JavaScript。"""
from pathlib import Path
import re

_BLOCK = re.compile(r'/\*(?::(?P<locale>[\w-]*)|~struct~(?P<struct>[^:\s]+):(?P<slocale>[\w-]*))(?P<body>.*?)\*/', re.S)


def _parse(body):
    result = {'parameters': [], 'commands': [], 'help': '', 'metadata': {}}
    current = result['metadata']
    command = None
    last = None
    for raw in body.splitlines():
        line = re.sub(r'^\s*\* ?', '', raw).rstrip()
        match = re.match(r'^\s*@([\w-]+)(?:\s+(.*))?$', line)
        if match:
            tag, value = match[1], match[2] or ''
            if tag in ('param', 'command', 'arg'):
                current = {'name': value, 'metadata': {}}
                if tag == 'command':
                    current['arguments'] = []
                    result['commands'].append(current)
                    command = current
                elif tag == 'param':
                    result['parameters'].append(current)
                    command = None
                elif command is not None:
                    command['arguments'].append(current)
                else:
                    raise ValueError('@arg outside @command')
                last = None
            elif tag == 'help':
                current = result
                current['help'] = value
                last = 'help'
            elif tag == 'option':
                current.setdefault('options', []).append({'text': value, 'value': value})
                last = None
            elif tag == 'value' and current.get('options'):
                current['options'][-1]['value'] = value
                last = None
            elif tag in ('text', 'desc', 'type', 'default', 'min', 'max', 'decimals', 'parent'):
                current[tag] = value
                last = tag
            else:
                current.setdefault('metadata', {}).setdefault(tag, []).append(value)
                last = None
        elif re.match(r'^\s*@(?:\s|$)', line):
            last = None  # Decorative annotation separator, not a value continuation.
        elif last and line.strip():
            current[last] += '\n' + line
        elif last == 'help':
            current[last] += '\n'
    result['help'] = result['help'].strip()
    return result


def _plugin_metadata(project, plugin: str, *, language: str = 'zh') -> dict:
    """查询插件用法、配置参数、命令参数和结构体，返回可 JSON 序列化的字典。

    project -- 工程目录。
    plugin -- 插件名或相对子目录路径，可省略 .js；同名文件必须指定子目录。
    language -- 声明语言，默认 zh；依次回退基础语言、无语言声明、首个声明。

    仅提取插件声明，不执行代码；默认值保持字符串，缺失时不猜测。
    声明不能证明运行时注册有效；缺少声明时返回警告，不要求 agent 手读源码。
    """
    root = (Path(project).resolve(strict=True) / 'js/plugins').resolve(strict=True)
    if not isinstance(plugin, str) or not plugin or '\\' in plugin:
        raise ValueError('Invalid plugin name')
    name = plugin[:-3] if plugin.endswith('.js') else plugin
    relative = Path(name + '.js')
    if relative.is_absolute() or '..' in relative.parts:
        raise ValueError('Plugin must be inside js/plugins')
    candidates = [root / relative] if len(relative.parts) > 1 else list(root.rglob(relative.name))
    candidates = [p for p in candidates if p.is_file()]
    if len(candidates) != 1:
        raise ValueError(f'Expected one plugin, found {len(candidates)}: {[str(p.relative_to(root)) for p in candidates]}')
    path = candidates[0]
    if not path.resolve().is_relative_to(root):
        raise ValueError('Plugin symlink escapes js/plugins')
    groups = {}
    for match in _BLOCK.finditer(path.read_text(encoding='utf-8-sig')):
        key = match['struct'] or ''
        groups.setdefault(key, {})[match['slocale'] if key else match['locale']] = match['body']
    warnings = []
    locales = {}
    def select(key):
        variants = groups.get(key, {})
        if not variants:
            return _parse('')
        chosen = next((v for v in (language, language.split('-')[0], '') if v in variants), next(iter(variants)))
        locales[key or 'plugin'] = chosen
        return _parse(variants[chosen])
    result = select('')
    result['plugin'] = path.relative_to(root).with_suffix('').as_posix()
    result['source'] = str(path)
    result['structs'] = {key: select(key)['parameters'] for key in groups if key}
    result['languages'] = locales
    if '' not in groups:
        warnings.append('No RPG Maker plugin metadata declaration found')
    all_fields = result['parameters'] + [arg for cmd in result['commands'] for arg in cmd['arguments']]
    all_fields += [field for fields in result['structs'].values() for field in fields]
    for field in all_fields:
        for struct in re.findall(r'struct<([^>]+)>', field.get('type', '')):
            if struct not in result['structs']:
                warnings.append(f'Missing struct declaration: {struct}')
    for fields in [result['parameters'], result['commands']] + [c['arguments'] for c in result['commands']] + list(result['structs'].values()):
        names = [f['name'] for f in fields]
        for duplicate in sorted({n for n in names if names.count(n) > 1}):
            warnings.append(f'Duplicate declaration retained: {duplicate}')
    result['warnings'] = warnings
    result['scope'] = 'Plugin metadata only; runtime registration, enabled status and behavior are not verified.'
    return result


def plugin_help(project, plugin: str, *, language: str = 'zh', command: str | None = None,
                section: str = 'commands', struct: str | None = None) -> str:
    """返回简短文本帮助，默认每条命令一行。

    command -- 命令 ID；指定时展开参数、默认值、选项和使用限制。
    section -- commands 命令概要、parameters 配置参数、help 完整插件说明。
    struct -- 结构体名；指定时展开字段，可继续查询嵌套结构体。
    默认值始终是字符串；长值仅在概要中省略，详情保留完整值。
    """
    if section not in ('commands', 'parameters', 'help'):
        raise ValueError('Unknown help section')
    if command is not None and struct is not None:
        raise ValueError('Choose command or struct, not both')
    data = _plugin_metadata(project, plugin, language=language)
    lines = [data['plugin']]

    def compact(value, limit=None):
        text = ' '.join(value.split())
        return text if limit is None or len(text) <= limit else text[:limit] + '…'

    def field(item, detail=False):
        text = item['name']
        if item.get('type'):
            text += ' (' + item['type'] + ')'
        if 'default' in item:
            value = repr(item['default'])
            text += ' = ' + (value if detail else compact(value, 60))
        elif detail:
            text += ' [未声明默认值]'
        if detail:
            if item.get('text'):
                text += ' — ' + item['text']
            if item.get('desc'):
                text += '\n    ' + compact(item['desc'])
            if item.get('options'):
                text += '\n    可选：' + '; '.join(o['value'] + ' (' + o['text'] + ')' for o in item['options'])
            limits = [key + '=' + item[key] for key in ('min','max','decimals','parent') if key in item]
            if limits:
                text += '\n    ' + ', '.join(limits)
            if item.get('metadata'):
                text += '\n    ' + '; '.join(k + ': ' + ' / '.join(v) for k,v in item['metadata'].items())
        return text

    if command is not None:
        matches = [c for c in data['commands'] if c['name'] == command]
        if len(matches) != 1:
            raise ValueError('Command missing or ambiguous: ' + command)
        item = matches[0]
        lines += [item['name'] + ' — ' + item.get('text', item['name'])]
        if item.get('desc'):
            lines.append(compact(item['desc']))
        lines.extend('  ' + field(arg, True) for arg in item['arguments'])
        if not item['arguments']:
            lines.append('无参数')
    elif struct is not None:
        if struct not in data['structs']:
            raise ValueError('Unknown struct: ' + struct)
        lines.append('结构体 ' + struct)
        lines.extend('  ' + field(item, True) for item in data['structs'][struct])
    elif section == 'parameters':
        lines.extend('  ' + field(item, True) for item in data['parameters'])
    elif section == 'help':
        lines.append(data['help'] or '未声明用法说明')
    else:
        for item in data['commands']:
            if item['name'].startswith('Separator_') and item.get('text') == '-':
                continue
            args = ', '.join(field(arg) for arg in item['arguments']) or '无参数'
            lines.append(item['name'] + ' — ' + item.get('text', item['name']) + '：' + args)
        if not data['commands']:
            lines.append('未声明插件命令')
        lines.append('详情：command=命令ID；配置：section="parameters"；结构体：struct=名称；完整说明：section="help"')
    lines.extend('注意：' + warning for warning in data['warnings'])
    return '\n'.join(lines)
