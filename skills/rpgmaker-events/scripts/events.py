#!/usr/bin/env python3
"""RPG Maker MZ common/map event query and structured command editor (Python 3.10+)."""
import argparse
from collections import Counter
import json
from pathlib import Path
import re
import sys

from event_core.backend import db, require, fields
from event_core.compiler import (
    integer, string, boolean, number, enum, command, condition, operand, compile_nodes, compile_document, digest, index_commands,
    NAMES, CONTINUATIONS, BLOCKS, MARKERS, OPERATIONS, COMPARISONS,
)
from event_core.targets import locate


def targets(root, kind=None, map_id=None):
    if kind != 'map' and map_id is None and (root / 'CommonEvents.json').exists():
        values = db.read_document(db.file_path(root, 'CommonEvents.json').read_bytes())
        for index, event in enumerate(values):
            if event is not None:
                require(event['id'] == index, f'Common event ID/index mismatch: {index}')
                yield {'kind': 'common', 'id': index}, event.get('name', ''), event['list']
    if kind != 'common':
        for file in sorted(root.glob('Map[0-9]*.json')):
            if not re.fullmatch(r'Map\d{3,}\.json', file.name):
                continue
            mid = int(file.stem[3:])
            if map_id is not None and mid != map_id:
                continue
            value = db.read_document(db.file_path(root, file.name).read_bytes())
            for index, event in enumerate(value['events']):
                if event is not None:
                    require(event['id'] == index, f'{file.name} event ID/index mismatch: {index}')
                    for page, data in enumerate(event['pages']):
                        yield {'kind': 'map', 'map_id': mid, 'event_id': index, 'page_index': page}, event.get('name', ''), data['list']


def source_profile(project, enforce=False):
    source = (project / 'js/rmmz_objects.js').read_bytes()
    profile = db.loads((Path(__file__).resolve().parents[1] / 'references/engine-profile.json').read_text())
    methods = {}
    for name, expected in profile['methods'].items():
        owner, method = name.split('.', 1) if '.' in name else ('Game_Interpreter', name)
        match = re.search(r'^' + re.escape(owner) + r'\.prototype\.' + re.escape(method) + r' = function\([^)]*\) \{.*?^\};', source.decode('utf-8'), re.M | re.S)
        methods[name] = db.sha(match.group().encode()) if match else None
    mismatches = [name for name, value in methods.items() if value != profile['methods'][name]]
    require(not enforce or not mismatches, f'Engine methods differ from verified profile: {mismatches}; inspect source before extending profile')
    return {'engine_sha256': db.sha(source), 'profile_matches': not mismatches, 'mismatched_methods': mismatches,
            'validation_scope': 'core command serialization; plugin behavior and playtest are not verified'}


def prepare(project, plan):
    fields(plan, {'version', 'edits'})
    integer(plan['version'], 1, 1)
    require(isinstance(plan['edits'], list) and plan['edits'], 'edits must be a nonempty array')
    root = db.root_path(project / 'data')
    profile = source_profile(project, True)
    operations, results, seen = [], [], set()
    for edit in plan['edits']:
        fields(edit, {'target', 'op'}, {'commands', 'index', 'expect_list_sha256'})
        name, path = locate(edit['target'])
        key = (name, tuple(path))
        require(key not in seen, 'Use one edit per event page/list per plan; apply further edits after re-inspecting')
        seen.add(key)
        value = db.read_document(db.file_path(root, name).read_bytes())
        current = db.get(value, path)
        require(isinstance(current, list), 'Target is not an event list')
        if 'expect_list_sha256' in edit:
            require(edit['expect_list_sha256'] == digest(current), 'Event list fingerprint mismatch')
        op = edit['op']
        require(op in ('replace_all', 'append', 'insert_before', 'insert_after', 'replace', 'delete'), 'Unknown edit op')
        require(('commands' in edit) == (op != 'delete'), 'commands required except for delete')
        if op == 'replace_all':
            require('index' not in edit, 'replace_all does not use index')
            new = compile_nodes(edit['commands']) + [command(0, 0)]
        else:
            nodes = index_commands(current)
            if op == 'append':
                require('index' not in edit, 'append does not use index')
                start = end = len(current) - 1; indent = loops = 0
            else:
                require('index' in edit and 'expect_list_sha256' in edit, 'Indexed edits require index and expect_list_sha256 from inspect')
                integer(edit['index'])
                node = next((n for n in nodes if n['index'] == edit['index']), None)
                require(node is not None, 'index must select a command/block start, not a continuation or terminator')
                start, end, indent, loops = node['index'], node['end'], node['indent'], node['loop_depth']
                if op == 'insert_before': end = start
                if op == 'insert_after': start = end
            inserted = [] if op == 'delete' else compile_nodes(edit['commands'], indent, loops)
            new = current[:start] + inserted + current[end:]
        index_commands(new)
        # Calls generated by this edit must reference existing common events.
        common = None
        for c in new:
            if c['code'] == 117 and c not in current:
                if common is None:
                    common = db.read_document(db.file_path(root, 'CommonEvents.json').read_bytes())
                cid = c['parameters'][0]
                require(cid < len(common) and common[cid] is not None, f'Missing common event {cid}')
        operations.extend([{'op': 'test', 'file': name, 'path': path, 'expect': current},
                           {'op': 'set', 'file': name, 'path': path, 'value': new}])
        results.append({'target': edit['target'], 'before': current, 'after': new, 'list_sha256': digest(new)})
    originals, updated, _ = db.prepare(root, {'version': 1, 'format': 'preserve', 'operations': operations})
    result = db.preview_result(root, originals, updated, {'events_plan': plan, 'source_profile': profile})
    result.update(changes=results, source_profile=profile)
    return root, originals, updated, result


def run(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project', type=Path, required=True)
    sub = parser.add_subparsers(dest='action', required=True)
    for action in ('scan', 'list', 'find'):
        p = sub.add_parser(action)
        p.add_argument('--kind', choices=['common', 'map'])
        p.add_argument('--map-id', type=int)
        p.add_argument('--name', help='Case-sensitive substring')
        if action == 'find':
            p.add_argument('--code', type=int)
            p.add_argument('--text', help='Literal substring in parameters, recursively; no evaluation')
            p.add_argument('--calls', type=int)
        p.add_argument('--offset', type=int, default=0)
        p.add_argument('--limit', type=int, default=100)
    p = sub.add_parser('plugin-help')
    p.add_argument('--plugin', required=True)
    p.add_argument('--language', default='zh')
    p.add_argument('--command')
    p.add_argument('--section', choices=['commands', 'parameters', 'help'], default='commands')
    p.add_argument('--struct')
    p = sub.add_parser('inspect')
    p.add_argument('--target', required=True, help='JSON target object')
    p = sub.add_parser('compile')
    p.add_argument('--input', type=Path, required=True)
    p = sub.add_parser('apply')
    p.add_argument('--plan', type=Path, required=True)
    p.add_argument('--write', action='store_true')
    p.add_argument('--expect-preview')
    args = parser.parse_args(argv)
    project = args.project.resolve(strict=True)
    if args.action == 'plugin-help':
        from event_core.plugin_help import plugin_help
        return plugin_help(project, args.plugin, language=args.language, command=args.command, section=args.section, struct=args.struct)
    root = db.root_path(project / 'data')
    if args.action == 'compile':
        profile = source_profile(project, True)
        value = compile_document(db.loads(args.input.read_text(encoding='utf-8-sig')))
        return {'commands': value, 'source_profile': profile}
    if args.action == 'apply':
        plan = db.loads(args.plan.read_text(encoding='utf-8-sig'))
        root, originals, updated, result = prepare(project, plan)
        require(not args.write or args.expect_preview, '--write requires --expect-preview')
        if args.expect_preview:
            require(args.expect_preview == result['preview_sha256'], 'Preview mismatch: plan, source or engine changed')
        if args.write and result['changed']:
            require(source_profile(project, True) == result['source_profile'], 'Engine changed during preparation')
            result['transaction'] = db.commit(root, originals, updated)
            result['written'] = True
        return result
    if args.action == 'inspect':
        target = db.loads(args.target)
        name, path = locate(target)
        raw = db.file_path(root, name).read_bytes()
        value = db.get(db.read_document(raw), path)
        result = {'target': target, 'file': name, 'path': path, 'file_sha256': db.sha(raw),
                  'list_sha256': digest(value), 'commands': value}
        try: result['nodes'] = index_commands(value)
        except db.Invalid as exc: result['structure_warning'] = str(exc)
        return result
    integer(args.offset); integer(args.limit, 1)
    records, counts, warnings, total_lists = [], Counter(), [], 0
    for target, name, commands in targets(root, args.kind, args.map_id):
        if args.name is not None and args.name not in name: continue
        total_lists += 1
        counts.update(str(c['code']) for c in commands)
        if args.action == 'scan':
            try: index_commands(commands)
            except (ValueError, KeyError, TypeError) as exc: warnings.append({'target': target, 'warning': str(exc)})
        elif args.action == 'list':
            records.append({'target': target, 'name': name, 'command_count': len(commands)})
        else:
            for index, c in enumerate(commands):
                if args.code is not None and c['code'] != args.code: continue
                if args.calls is not None and not (c['code'] == 117 and c['parameters'] == [args.calls]): continue
                if args.text is not None and args.text not in db.dumps(c['parameters']): continue
                records.append({'target': target, 'name': name, 'index': index, **c})
    if args.action == 'scan':
        return {'event_lists': total_lists, 'code_counts': dict(sorted(counts.items(), key=lambda x: int(x[0]))),
                'structure_warnings': warnings, 'source_profile': source_profile(project)}
    return {'total': len(records), 'offset': args.offset, 'results': records[args.offset:args.offset + args.limit]}


def main():
    try:
        result = run()
        print(result if isinstance(result, str) else db.dumps({'ok': True, **result}, indent=2))
        return 0
    except (ValueError, OSError, UnicodeError, KeyError, TypeError, IndexError, RecursionError) as exc:
        print(json.dumps({'ok': False, 'error': str(exc)}, ensure_ascii=True), file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
