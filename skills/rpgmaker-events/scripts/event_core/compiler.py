"""将语义描述编译为引擎指令，校验参数和控制流边界。"""
from __future__ import annotations

import copy
from .backend import db, require, fields

NAMES = {102:'choices', 115:'exit_event', 118:'label', 119:'jump_to_label', 221: 'fadeout_screen', 222: 'fadein_screen', 223: 'tint_screen', 224: 'flash_screen', 225: 'shake_screen', 236: 'weather', 241: 'play_bgm', 242: 'fadeout_bgm', 243: 'save_bgm', 244: 'replay_bgm', 245: 'play_bgs', 246: 'fadeout_bgs', 249: 'play_me', 250: 'play_se', 251: 'stop_se', 261: 'play_movie', 303: "name_input", 351: "open_menu", 352: "open_save", 353: "game_over", 354: "return_to_title", 231: "show_picture", 232: "move_picture", 233: "rotate_picture", 234: "tint_picture", 235: "erase_picture", 202: "vehicle_location", 203: "event_location", 204: "scroll_map", 205: "movement_route", 206: "get_on_off_vehicle", 357: 'plugin_command', 108: 'comment', 125: 'gold', 126: 'items', 201: 'transfer', 214: 'erase_event', 230: 'wait', 355: 'script', 123: 'set_self_switch', 124: 'timer', 101: 'text', 401: 'text_line', 121: 'switch', 122: 'variable',
         111: 'if', 411: 'else', 412: 'end_if', 117: 'call', 112: 'loop',
         113: 'break', 413: 'repeat', 0: 'end'}
CONTINUATIONS = {101: 401, 105: 405, 108: 408, 355: 655, 205: 505, 302: 605, 357: 657}
BLOCKS = {111: ({411}, 412), 112: (set(), 413), 102: ({402, 403}, 404),
          301: ({601, 602, 603}, 604), 109: (set(), 409)}
MARKERS = {0, 411, 412, 413, 402, 403, 404, 601, 602, 603, 604, 409} | set(CONTINUATIONS.values())
OPERATIONS = ['set', 'add', 'sub', 'mul', 'div', 'mod']
COMPARISONS = ['eq', 'ge', 'le', 'gt', 'lt', 'ne']




def integer(value, minimum=0, maximum=None):
    require(type(value) is int and value >= minimum and (maximum is None or value <= maximum),
            f'Expected integer in {minimum}..{maximum}, got {value!r}')
    return value


def string(value):
    require(isinstance(value, str), 'Expected string')
    return value


def boolean(value):
    require(type(value) is bool, 'Expected boolean')
    return value


def number(value):
    require(type(value) in (int, float), 'Expected number')
    db.dumps(value)
    return value


def enum(value, choices):
    require(value in choices, f'Expected one of {choices}')
    return choices.index(value)


def command(code, indent, parameters=()):
    return {'code': code, 'indent': indent, 'parameters': list(parameters)}


def condition(data):
    require(isinstance(data, dict), 'condition must be an object')
    kind = data.get('type')
    if kind == 'switch':
        fields(data, {'type', 'id', 'on'})
        return [0, integer(data['id'], 1), 0 if boolean(data['on']) else 1]
    if kind == 'variable':
        fields(data, {'type', 'id', 'compare', 'value'}, {'value_type'})
        variable = enum(data.get('value_type', 'constant'), ['constant', 'variable'])
        value = integer(data['value'], 1) if variable else number(data['value'])
        return [1, integer(data['id'], 1), variable, value, enum(data['compare'], COMPARISONS)]
    if kind == 'self_switch':
        fields(data, {'type', 'key', 'on'})
        require(data['key'] in ('A', 'B', 'C', 'D'), 'Self switch must be A/B/C/D')
        return [2, data['key'], 0 if boolean(data['on']) else 1]
    if kind == 'direction':
        fields(data, {'type', 'id', 'direction'})
        direction = enum(data['direction'], ['down', 'left', 'right', 'up'])
        return [6, integer(data['id'], -1), [2, 4, 6, 8][direction]]
    if kind == 'item':
        fields(data, {'type', 'id'})
        return [8, integer(data['id'], 1)]
    if kind == 'button':
        fields(data, {'type', 'key', 'mode'})
        require(data['key'] in ('ok', 'cancel', 'shift', 'down', 'left', 'right', 'up', 'pageup', 'pagedown'),
                'Expected an engine input symbol, such as ok or cancel')
        return [11, data['key'], enum(data['mode'], ['pressed', 'triggered', 'repeated'])]
    if kind == 'actor':
        fields(data, {'type', 'id', 'test'}, {'name'})
        actor_id = integer(data['id'], 1)
        if data['test'] == 'in_party':
            require('name' not in data, 'in_party has no name parameter')
            return [4, actor_id, 0]
        require(data['test'] == 'name' and 'name' in data, 'Actor test must be in_party or name')
        return [4, actor_id, 1, string(data['name'])]
    if kind == 'script':
        fields(data, {'type', 'expression'})
        return [12, string(data['expression'])]
    raise db.Invalid(f'Unsupported condition type: {kind!r}')


def operand(data):
    require(isinstance(data, dict), 'operand must be an object')
    kind = data.get('type')
    if kind in ('constant', 'variable', 'script'):
        fields(data, {'type', 'value'})
        value = (number(data['value']) if kind == 'constant' else integer(data['value'], 1)
                 if kind == 'variable' else string(data['value']))
        return [{'constant': 0, 'variable': 1, 'script': 4}[kind], value]
    if kind == 'random':
        fields(data, {'type', 'min', 'max'})
        require(type(data['min']) is int and type(data['max']) is int and data['min'] <= data['max'],
                'Random bounds must be ordered integers')
        return [2, data['min'], data['max']]
    raise db.Invalid('Initial operands: constant, variable, random, script; game_data remains readable')


def compile_nodes(nodes, indent=0, loop_depth=0):
    require(isinstance(nodes, list), 'commands/body/then/else must be arrays')
    output = []
    for node in nodes:
        require(isinstance(node, dict), 'Command must be an object')
        kind = node.get('type')
        if kind == 'raw':
            fields(node, {'type', 'commands'})
            raw = copy.deepcopy(node['commands'])
            require(isinstance(raw, list) and bool(raw), 'Empty opaque command')
            base = integer(raw[0]['indent'])
            for item in raw:
                integer(item['code']); integer(item['indent'])
                require(isinstance(item['parameters'], list), 'Invalid opaque parameters')
                item['indent'] += indent - base
                require(item['indent'] >= indent, 'Opaque block escapes its enclosing scope')
            output.extend(raw)
        elif kind == 'text':
            fields(node, {'type', 'lines'}, {'face', 'face_index', 'background', 'position', 'speaker'})
            lines = node['lines']
            require(isinstance(lines, list) and 1 <= len(lines) <= 4, 'text requires 1..4 lines; use another text node for more')
            for line in lines:
                require('\n' not in string(line) and '\r' not in line, 'One string per dialogue line')
            output.append(command(101, indent, [string(node.get('face', '')), integer(node.get('face_index', 0), 0, 7),
                integer(node.get('background', 0), 0, 2), integer(node.get('position', 2), 0, 2), string(node.get('speaker', ''))]))
            output.extend(command(401, indent, [line]) for line in lines)
        elif kind in ('switch', 'variable'):
            required = {'type', 'start', 'on'} if kind == 'switch' else {'type', 'start', 'operation', 'operand'}
            fields(node, required, {'end'})
            start = integer(node['start'], 1)
            end = integer(node.get('end', start), start)
            params = [start, end]
            if kind == 'switch':
                params.append(0 if boolean(node['on']) else 1)
            else:
                params += [enum(node['operation'], OPERATIONS)] + operand(node['operand'])
            output.append(command(121 if kind == 'switch' else 122, indent, params))
        elif kind == 'set_self_switch':
            fields(node, {'type', 'key', 'on'})
            require(node['key'] in ('A', 'B', 'C', 'D'), 'Self switch must be A/B/C/D')
            output.append(command(123, indent, [node['key'], 0 if boolean(node['on']) else 1]))
        elif kind == 'start_timer':
            fields(node, {'type', 'seconds'})
            output.append(command(124, indent, [0, integer(node['seconds'])]))
        elif kind == 'stop_timer':
            fields(node, {'type'})
            output.append(command(124, indent, [1]))
        elif kind in ('comment', 'script'):
            fields(node, {'type', 'text'})
            lines = string(node['text']).replace('\r\n', '\n').replace('\r', '\n').split('\n')
            first, continuation = (108, 408) if kind == 'comment' else (355, 655)
            output.extend(command(first if i == 0 else continuation, indent, [line]) for i, line in enumerate(lines))
        elif kind in ('gold', 'items'):
            fields(node, {'type', 'operation', 'value'} | ({'id'} if kind == 'items' else set()))
            value = node['value']
            fields(value, {'type', 'value'})
            mode = enum(value['type'], ['constant', 'variable'])
            amount = integer(value['value'], 1 if mode else 0)
            params = [enum(node['operation'], ['add', 'sub']), mode, amount]
            if kind == 'items': params.insert(0, integer(node['id'], 1))
            output.append(command(125 if kind == 'gold' else 126, indent, params))
        elif kind in ('play_bgm', 'fadeout_bgm', 'save_bgm', 'replay_bgm', 'play_bgs', 'fadeout_bgs', 'play_me', 'play_se', 'stop_se', 'play_movie'):
            from .commands.audio_video import compile_audio_video
            output.extend(compile_audio_video(node, indent))
        elif kind in ('fadeout_screen', 'fadein_screen', 'tint_screen', 'flash_screen', 'shake_screen', 'weather'):
            from .commands.screen import compile_screen
            output.extend(compile_screen(node, indent))
        elif kind in ('name_input','open_menu','open_save','game_over','return_to_title'):
            from .commands.scene_control import compile_scene
            output.extend(compile_scene(node, indent))
        elif kind in ('show_picture','move_picture','rotate_picture','tint_picture','erase_picture'):
            from .commands.picture import compile_picture
            output.extend(compile_picture(node, indent))
        elif kind in ('vehicle_location','event_location','scroll_map','movement_route','get_on_off_vehicle'):
            from .commands.movement import compile_movement
            output.extend(compile_movement(node, indent))
        elif kind == 'transfer':
            fields(node, {'type', 'variables', 'destination', 'direction', 'fade'})
            indirect = boolean(node['variables'])
            destination = node['destination']
            require(isinstance(destination, list) and len(destination) == 3, 'Transfer requires map, x, y')
            for i, value in enumerate(destination): integer(value, 1 if indirect or i == 0 else 0)
            direction = [0, 2, 4, 6, 8][enum(node['direction'], ['keep', 'down', 'left', 'right', 'up'])]
            output.append(command(201, indent, [int(indirect), *destination, direction, enum(node['fade'], ['black', 'white', 'none'])]))
        elif kind == 'wait':
            fields(node, {'type', 'frames'})
            output.append(command(230, indent, [integer(node['frames'], 1)]))
        elif kind == 'erase_event':
            fields(node, {'type'})
            output.append(command(214, indent))
        elif kind == 'plugin_command':
            fields(node, {'type','plugin','command','display_name','args','annotations'})
            require(bool(string(node['plugin'])) and bool(string(node['command'])), 'Plugin and command IDs must not be empty')
            string(node['display_name'])
            require(isinstance(node['args'],dict) and all(isinstance(k,str) and isinstance(v,str) for k,v in node['args'].items()),
                    'Plugin arguments must be strings')
            require(isinstance(node['annotations'],list),'annotations must be an array')
            output.append(command(357,indent,[node['plugin'],node['command'],node['display_name'],copy.deepcopy(node['args'])]))
            output.extend(command(657,indent,[string(line)]) for line in node['annotations'])
        elif kind in ('label','jump_to_label'):
            fields(node, {'type','name'})
            require(bool(string(node['name'])), 'Label name must not be empty')
            output.append(command(118 if kind=='label' else 119, indent, [node['name']]))
        elif kind == 'exit_event':
            fields(node, {'type'})
            output.append(command(115, indent))
        elif kind == 'choices':
            fields(node, {'type','choices','default','cancel'})
            choices=node['choices']
            require(isinstance(choices,list) and 1<=len(choices)<=6, 'Expected 1-6 choices')
            for choice in choices: fields(choice, {'text','body'})
            texts=[string(c['text']) for c in choices]
            output.append(command(102,indent,[texts,integer(node['cancel'],-1,len(choices)-1),integer(node['default'],-1,len(choices)-1),2,0]))
            for i,c in enumerate(choices):
                output.append(command(402,indent,[i,texts[i]]))
                output += compile_nodes(c['body'],indent+1,loop_depth)+[command(0,indent+1)]
            output.append(command(404,indent))
        elif kind == 'call':
            fields(node, {'type', 'id'})
            output.append(command(117, indent, [integer(node['id'], 1)]))
        elif kind == 'if':
            fields(node, {'type', 'condition', 'then'}, {'else'})
            output.append(command(111, indent, condition(node['condition'])))
            output += compile_nodes(node['then'], indent + 1, loop_depth) + [command(0, indent + 1)]
            if 'else' in node:
                output.append(command(411, indent))
                output += compile_nodes(node['else'], indent + 1, loop_depth) + [command(0, indent + 1)]
            output.append(command(412, indent))
        elif kind == 'loop':
            fields(node, {'type', 'body'})
            output.append(command(112, indent))
            output += compile_nodes(node['body'], indent + 1, loop_depth + 1)
            output += [command(0, indent + 1), command(413, indent)]
        elif kind == 'break':
            fields(node, {'type'})
            require(loop_depth > 0, 'break requires an enclosing loop')
            output.append(command(113, indent))
        else:
            raise db.Invalid(f'Unsupported command type: {kind!r}')
    return output


def compile_document(document):
    fields(document, {'version', 'commands'})
    integer(document['version'], 1, 1)
    result = compile_nodes(document['commands']) + [command(0, 0)]
    index_commands(result)
    return result


def digest(value):
    return db.sha(db.dumps(value, sort_keys=True, separators=(',', ':')).encode())


def index_commands(commands):
    """Structural ranges, original zero-based indices. Unknown leaves stay opaque."""
    require(isinstance(commands, list) and commands, 'Missing event list')
    for c in commands:
        require(isinstance(c, dict) and {'code', 'indent', 'parameters'} <= c.keys(), 'Malformed command')
        integer(c['code']); integer(c['indent'])
        require(isinstance(c['parameters'], list), 'parameters must be an array')
    require(commands[-1] == command(0, 0), 'List must end with code 0 at indent 0')
    nodes = []
    def sequence(pos, indent, loops, stops):
        while pos < len(commands):
            c = commands[pos]; code = c['code']
            if c['indent'] < indent or (c['indent'] == indent and code in stops):
                return pos
            require(c['indent'] == indent, f'Unexpected indent at {pos}')
            if code == 0:
                require(c['parameters'] == [], f'Invalid end marker at {pos}')
                return pos
            require(code not in MARKERS, f'Orphan continuation/end marker at {pos}')
            node = {'index': pos, 'end': pos + 1, 'indent': indent, 'loop_depth': loops,
                    'type': NAMES.get(code, 'opaque'), 'code': code, 'parameters': c['parameters']}
            nodes.append(node)
            start = pos; pos += 1
            if code in BLOCKS:
                branches, closing = BLOCKS[code]
                # Choices/battle may begin immediately with a same-indent branch label.
                while True:
                    pos = sequence(pos, indent + 1, loops + (code == 112), set())
                    require(pos < len(commands), f'Unclosed block at {start}')
                    if commands[pos]['code'] == 0 and commands[pos]['indent'] == indent + 1:
                        pos += 1
                    require(pos < len(commands) and commands[pos]['indent'] == indent,
                            f'Missing block terminator at {start}')
                    marker = commands[pos]['code']
                    if marker == closing:
                        pos += 1; break
                    require(marker in branches, f'Wrong branch marker at {pos}')
                    pos += 1
            elif code in CONTINUATIONS:
                while pos < len(commands) and commands[pos]['code'] == CONTINUATIONS[code] and commands[pos]['indent'] == indent:
                    pos += 1
            if code == 113:
                require(loops > 0, f'break outside loop at {start}')
            node['end'] = pos
        return pos
    end = sequence(0, 0, 0, set())
    require(end == len(commands) - 1, f'Unexpected terminator at {end}')
    return sorted(nodes, key=lambda n: n['index'])
