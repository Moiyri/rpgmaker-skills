#!/usr/bin/env python3
"""Read and edit any JSON database field via explicit paths. Python >= 3.10."""

import argparse
import copy
import difflib
import hashlib
import json
import math
import os
from pathlib import Path
import re
import stat
import sys
import tempfile


BACKUPS = ".rpgmaker-db-backups"
LOCK = ".rpgmaker-db.lock"
DECODE = {"decode": "json"}


class Invalid(ValueError):
    pass


def require(condition, message):
    if not condition:
        raise Invalid(message)


def fields(obj, required, optional=()):
    require(isinstance(obj, dict), "Expected an object")
    require(set(required) <= obj.keys(), f"Missing fields: {sorted(set(required) - obj.keys())}")
    require(obj.keys() <= set(required) | set(optional),
            f"Unknown fields: {sorted(obj.keys() - set(required) - set(optional))}")


def pairs(items):
    result = {}
    for key, value in items:
        require(key not in result, f"Duplicate JSON key: {key!r}")
        result[key] = value
    return result


def bad_constant(value):
    raise Invalid(f"Invalid JSON number: {value}")


def finite_float(value):
    result = float(value)
    require(math.isfinite(result), f"JSON number is outside finite float range: {value}")
    return result


def loads(text):
    return json.loads(text, object_pairs_hook=pairs, parse_constant=bad_constant, parse_float=finite_float)


def dumps(value, **kwargs):
    # Preserve Unicode, including valid JSON escape sequences for lone surrogates.
    return json.dumps(value, ensure_ascii=False, allow_nan=False, **kwargs).encode(
        "utf-8", errors="backslashreplace").decode("utf-8")


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def equal(a, b):
    # Python considers True == 1 == 1.0; a JSON edit must not lose such changes.
    if type(a) is not type(b):
        return False
    if isinstance(a, dict):
        return a.keys() == b.keys() and all(equal(a[k], b[k]) for k in a)
    if isinstance(a, list):
        return len(a) == len(b) and all(equal(x, y) for x, y in zip(a, b))
    return a == b


def root_path(value):
    root = Path(value).resolve(strict=True)
    require(root.is_dir(), "--root must be an existing database directory")
    return root


def file_path(root, name, allow_missing=False):
    require(isinstance(name, str) and bool(name), "file must be a nonempty relative JSON path")
    relative = Path(name)
    require(not relative.is_absolute() and ".." not in relative.parts,
            "file must stay inside --root")
    require(relative.suffix.lower() == ".json", "Only JSON database files are supported")
    require(relative.parts[0] not in (BACKUPS, LOCK), "Reserved transaction path")
    target = root / relative
    require(target.resolve() == target, "Symlink paths are not supported")
    require(target.is_file() or (allow_missing and not os.path.lexists(target)), f"Database file does not exist or is not regular: {name}")
    return target


def read_document(raw):
    return loads(raw.decode("utf-8-sig"))


def render(raw, original, updated):
    if equal(original, updated):
        return raw
    text = raw.decode("utf-8-sig")
    newline = "\r\n" if "\r\n" in text else "\n"
    indentation = re.search(r"\n([ \t]+)\S", text)
    if indentation:
        output = dumps(updated, indent=indentation.group(1))
    elif "\n" in text.strip() and isinstance(updated, list):
        output = "[\n" + ",\n".join(dumps(v, separators=(",", ":")) for v in updated) + "\n]"
    else:
        output = dumps(updated, separators=(",", ":"))
    leading = text[:len(text) - len(text.lstrip())]
    trailing = text[len(text.rstrip()):]
    output = leading + output.replace("\n", newline) + trailing
    return (b"\xef\xbb\xbf" if raw.startswith(b"\xef\xbb\xbf") else b"") + output.encode("utf-8")


class JsonSpan:
    """JSON value plus its original lexical boundaries. No JavaScript evaluation."""

    def __init__(self, text, position=0):
        while position < len(text) and text[position].isspace():
            position += 1
        self.start = position
        self.children = []
        decoder = json.JSONDecoder()
        opener = text[position]
        if opener in "[{":
            self.value = [] if opener == "[" else {}
            closer = "]" if opener == "[" else "}"
            position += 1
            while True:
                while text[position].isspace():
                    position += 1
                if text[position] == closer:
                    self.end = position + 1
                    break
                if opener == "{":
                    key, position = decoder.raw_decode(text, position)
                    while text[position].isspace():
                        position += 1
                    require(text[position] == ":", "Expected object colon")
                    position += 1
                else:
                    key = len(self.children)
                node = JsonSpan(text, position)
                self.children.append((key, node))
                if opener == "[":
                    self.value.append(node.value)
                else:
                    self.value[key] = node.value
                position = node.end
                while text[position].isspace():
                    position += 1
                if text[position] == ",":
                    position += 1
                else:
                    require(text[position] == closer, "Expected JSON container end")
        else:
            self.value, self.end = decoder.raw_decode(text, position)


def encode_like(value, text, example=None):
    """Use the local container's whitespace for new values; retain JSON types."""
    if example is not None and type(value) is type(example.value):
        return patch_span(text, example, value)
    return dumps(value, separators=(",", ":"))


def patch_span(text, node, updated):
    before = node.value
    if equal(before, updated):
        return text[node.start:node.end]
    if isinstance(before, dict) and isinstance(updated, dict) and before.keys() == updated.keys():
        pieces, cursor = [], node.start
        for key, child_node in node.children:
            pieces.extend((text[cursor:child_node.start], patch_span(text, child_node, updated[key])))
            cursor = child_node.end
        pieces.append(text[cursor:node.end])
        return "".join(pieces)
    if isinstance(before, list) and isinstance(updated, list):
        children = [child for _, child in node.children]
        if len(before) == len(updated):
            pieces, cursor = [], node.start
            for child_node, value in zip(children, updated):
                pieces.extend((text[cursor:child_node.start], patch_span(text, child_node, value)))
                cursor = child_node.end
            pieces.append(text[cursor:node.end])
            return "".join(pieces)
        # Retain matching command lexemes when insertions shift subsequent indices.
        signature = lambda v: dumps(v, sort_keys=True, separators=(",", ":"))
        matcher = difflib.SequenceMatcher(a=[signature(v) for v in before],
                                         b=[signature(v) for v in updated], autojunk=False)
        entries = []
        for tag, a, b, c, d in matcher.get_opcodes():
            if tag == "equal":
                entries.extend((text[x.start:x.end], i) for i, x in enumerate(children[a:b], a))
            else:
                for offset, value in enumerate(updated[c:d]):
                    index = a + offset
                    example = children[index] if index < b else next(
                        (x for x in children if type(x.value) is type(value)), None)
                    entries.append((encode_like(value, text, example), index if index < b else None))
        if not children:
            whitespace = text[node.start + 1:node.end - 1]
            return "[" + whitespace + ",".join(x[0] for x in entries) + "]"
        prefix = text[node.start + 1:children[0].start]
        suffix = text[children[-1].end:node.end - 1]
        separators = [text[a.end:b.start] for a, b in zip(children, children[1:])]
        default_separator = separators[0] if separators else "," + prefix
        output = "[" + prefix
        for index, (entry, original_index) in enumerate(entries):
            if index:
                output += (separators[original_index - 1] if original_index is not None and original_index > 0
                           else default_separator)
            output += entry
        return output + suffix + "]"
    # Whole-type changes or object-key changes have no stable child mapping.
    local = text[node.start:node.end]
    indentation = re.search(r"\n([ \t]+)\S", local)
    output = dumps(updated, indent=indentation.group(1)) if indentation else dumps(updated, separators=(",", ":"))
    return output.replace("\n", "\r\n") if "\r\n" in local else output


def render_preserving(raw, original, updated):
    """Patch changed JSON values, preserving all unaffected lexical regions."""
    if equal(original, updated):
        return raw
    text = raw.decode("utf-8-sig")
    node = JsonSpan(text)
    require(equal(node.value, original), "JSON span parser disagrees with strict decoder")
    output = text[:node.start] + patch_span(text, node, updated) + text[node.end:]
    rendered = (b"\xef\xbb\xbf" if raw.startswith(b"\xef\xbb\xbf") else b"") + output.encode("utf-8")
    require(equal(read_document(rendered), updated), "Preserving serializer mismatch")
    return rendered


def path_tokens(path):
    require(isinstance(path, list), "path must be an array")
    for token in path:
        require(isinstance(token, str) or (type(token) is int and token >= 0)
                or (isinstance(token, dict) and token == DECODE),
                'Path tokens must be field strings, nonnegative integers, or {"decode":"json"}')
    return path


def child(value, token):
    if isinstance(token, dict):
        require(isinstance(value, str), "JSON decode step requires a string")
        return loads(value)
    if isinstance(token, str):
        require(isinstance(value, dict), f"Field {token!r} requires an object")
        require(token in value, f"Field does not exist: {token!r}")
        return value[token]
    require(isinstance(value, list), f"Index {token} requires an array")
    require(token < len(value), f"Array index {token} out of bounds (length {len(value)})")
    return value[token]


def get(value, path):
    for token in path_tokens(path):
        value = child(value, token)
    return value


def mutate(value, path, function):
    if not path:
        return function(value)
    token, *rest = path
    before = child(value, token)
    after = mutate(before, rest, function)
    if equal(before, after):
        return value
    if isinstance(token, dict):
        return dumps(after, separators=(",", ":"))
    result = value.copy()
    result[token] = after
    return result


def check_expected(value, op):
    if "expect" in op:
        require(equal(value, op["expect"]), "Expected value mismatch")


def apply_operation(value, op):
    common = {"op", "file", "path"}
    require(isinstance(op, dict) and isinstance(op.get("op"), str), "Operation needs a string op")
    action = op["op"]
    if action == "set":
        fields(op, common | {"value"}, {"expect"})
    elif action == "put":
        fields(op, common | {"value"})
    elif action in ("remove", "test"):
        fields(op, common | ({"expect"} if action == "test" else set()), {"expect"})
    elif action == "splice":
        fields(op, common | {"index", "delete_count", "items"}, {"expect"})
    else:
        raise Invalid(f"Unknown operation: {action}")
    path = path_tokens(op["path"])
    if action in ("put", "remove"):
        require(bool(path) and not isinstance(path[-1], dict),
                "put/remove needs an object field or array index; use set for root/decoded root")
        last = path[-1]

        def edit_parent(parent):
            if action == "put":
                require(isinstance(parent, dict) and isinstance(last, str), "put requires an object field")
                require(last not in parent, "put requires a missing field; use set to replace")
                result = parent.copy()
                result[last] = copy.deepcopy(op["value"])
            else:
                current = child(parent, last)
                check_expected(current, op)
                result = parent.copy()
                if isinstance(parent, dict):
                    del result[last]
                else:
                    # Do not shift RPG Maker record IDs. splice explicitly shifts.
                    result[last] = None
            return result

        return mutate(value, path[:-1], edit_parent)

    def edit_target(target):
        check_expected(target, op)
        if action == "test":
            return target
        if action == "set":
            return copy.deepcopy(op["value"])
        require(isinstance(target, list), "splice target must be an array")
        index, count = op["index"], op["delete_count"]
        require(type(index) is int and 0 <= index <= len(target), "splice index out of bounds")
        require(type(count) is int and 0 <= count <= len(target) - index, "splice delete_count out of bounds")
        require(isinstance(op["items"], list), "splice items must be an array")
        return target[:index] + copy.deepcopy(op["items"]) + target[index + count:]

    return mutate(value, path, edit_target)


def describe(value):
    types = {dict: "object", list: "array", str: "string", int: "integer",
             float: "number", bool: "boolean", type(None): "null"}
    result = {"type": types[type(value)]}
    if isinstance(value, (dict, list, str)):
        result["size"] = len(value)
    encoded = dumps(value, separators=(",", ":"))
    if len(encoded) <= 240:
        result["value"] = value
    else:
        result.update(preview=encoded[:240], truncated=True, value_sha256=sha(encoded.encode("utf-8")))
    return result


def prepare(root, plan):
    fields(plan, {"version", "operations"}, {"format"})
    require(plan.get("format", "normalized") in ("normalized", "preserve"), "Unknown format")
    require(type(plan["version"]) is int and plan["version"] == 1, "Plan version must be 1")
    require(isinstance(plan["operations"], list) and bool(plan["operations"]), "operations must be a nonempty array")
    originals, documents, changed, log = {}, {}, {}, []
    lifecycle = {}
    for index, op in enumerate(plan["operations"]):
        try:
            require(isinstance(op, dict) and "file" in op, "Operation requires file")
            name = op["file"]
            if op.get('op') in ('create_file','delete_file'):
                require(re.fullmatch(r'Map[0-9]{3,}\.json',name), 'File lifecycle limited to map files')
                require(name not in lifecycle and (name not in originals or (op['op']=='delete_file' and equal(documents[name],changed[name]))), 'Lifecycle target already modified')
                fields(op, {'op','file','text'} if op['op']=='create_file' else {'op','file'})
                target=file_path(root,name,allow_missing=True)
                if op['op']=='create_file':
                    require(not os.path.lexists(target), 'Map file already exists')
                    require(isinstance(op['text'],str),'Expected JSON text')
                    raw=op['text'].encode('utf-8');read_document(raw)
                    originals[name]=None;lifecycle[name]=raw
                else:
                    require(target.is_file(),'Map file missing')
                    originals[name]=target.read_bytes();lifecycle[name]=None
                log.append({'operation':index,'file':name,'op':op['op']})
                continue
            require(name not in lifecycle,'Cannot edit lifecycle target again')
            target = file_path(root, name)
            require(target.relative_to(root).as_posix() == name, "Use canonical relative POSIX paths")
            if name not in originals:
                originals[name] = target.read_bytes()
                documents[name] = read_document(originals[name])
                changed[name] = documents[name]
            value = changed[name]
            # Validate the operation before attempting to summarize its path.
            result = apply_operation(value, op)
            before = {"missing": True} if op["op"] == "put" else describe(get(value, op["path"]))
            after = ({"missing": True} if op["op"] == "remove" and isinstance(op["path"][-1], str)
                     else describe(get(result, op["path"])))
            changed[name] = result
            log.append({"operation": index, "file": name, "op": op["op"],
                        "path": op["path"], "before": before, "after": after})
        except (Invalid, ValueError, OSError) as exc:
            raise Invalid(f"Operation {index}: {exc}") from exc
    serializer = render_preserving if plan.get("format") == "preserve" else render
    updated = {name: serializer(raw, documents[name], changed[name]) for name, raw in originals.items() if name not in lifecycle}
    for name, raw in updated.items():
        require(equal(read_document(raw), changed[name]), f"Serialization mismatch: {name}")
    updated.update(lifecycle)
    return originals, updated, log


def stage(target, raw, mode):
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(prefix=".rpgmaker-db-", dir=target.parent, delete=False) as out:
            temporary = Path(out.name)
            out.write(raw)
            out.flush()
            os.fchmod(out.fileno(), mode)
            os.fsync(out.fileno())
        return temporary
    except BaseException:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
        raise


def save_manifest(path, value):
    temporary = stage(path, dumps(value, indent=2).encode("utf-8"), 0o600)
    try:
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def current_bytes(root,name):
    target=file_path(root,name,allow_missing=True)
    return target.read_bytes() if target.exists() else None


def commit(root, originals, updated):
    names = [name for name in originals if originals[name] != updated[name]]
    if not names:
        return None
    lock = root / LOCK
    fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    os.close(fd)
    temps, replaced, modes = {}, [], {}
    manifest_path = None
    try:
        for name, raw in originals.items():
            require(current_bytes(root, name) == raw, f"Source changed: {name}")
        backup_root = root / BACKUPS
        require(not backup_root.is_symlink(), "Backup directory cannot be a symlink")
        backup_root.mkdir(exist_ok=True)
        transaction = Path(tempfile.mkdtemp(prefix="txn-", dir=backup_root))
        manifest_path = transaction / "transaction.json"
        manifest = {"version": 1, "root": str(root), "status": "prepared", "files": []}
        for index, name in enumerate(names):
            target = file_path(root, name,allow_missing=True)
            modes[name] = stat.S_IMODE(target.stat().st_mode) if target.exists() else 0o644
            backup_name = f"{index}.json"
            if originals[name] is not None:
                with (transaction / backup_name).open("xb") as out:
                    out.write(originals[name]);out.flush();os.fsync(out.fileno())
            else:backup_name=None
            manifest["files"].append({"file": name, "backup": backup_name,
                                      "before_sha256": sha(originals[name]) if originals[name] is not None else None, "after_sha256": sha(updated[name]) if updated[name] is not None else None})
            if updated[name] is not None:temps[name] = stage(target, updated[name], modes[name])
        save_manifest(manifest_path, manifest)
        for name, raw in originals.items():
            require(current_bytes(root, name) == raw, f"Source changed before replacement: {name}")
        for name in names:
            target = file_path(root, name,allow_missing=True)
            require(current_bytes(root,name) == originals[name], f"Source changed before replacement: {name}")
            if updated[name] is None:target.unlink()
            elif originals[name] is None:
                os.link(temps[name],target)  # Atomic no-overwrite publication.
            else:os.replace(temps[name], target)
            replaced.append(name)
        manifest["status"] = "committed"
        save_manifest(manifest_path, manifest)
        return str(manifest_path)
    except (Exception, KeyboardInterrupt) as exc:
        recovery_errors = []
        for name in reversed(replaced):
            recovery_temp = None
            try:
                target = file_path(root, name,allow_missing=True)
                require(current_bytes(root,name) == updated[name], f"New external edit at {name}; not overwritten")
                if originals[name] is None:target.unlink()
                else:
                    recovery_temp = stage(target, originals[name], modes[name])
                    if updated[name] is None:os.link(recovery_temp,target)
                    else:os.replace(recovery_temp, target)
            except Exception as recovery:
                recovery_errors.append(f"{name}: {recovery}")
            finally:
                if recovery_temp is not None:
                    recovery_temp.unlink(missing_ok=True)
        if manifest_path is not None:
            manifest["status"] = "recovery_required" if recovery_errors else "rolled_back"
            manifest["error"] = str(exc)
            manifest["recovery_errors"] = recovery_errors
            try:
                save_manifest(manifest_path, manifest)
            except Exception as failure:
                recovery_errors.append(f"Could not update transaction log: {failure}")
        raise Invalid(f"Write failed: {exc}; transaction={manifest_path}; recovery_errors={recovery_errors}") from exc
    finally:
        for temporary in temps.values():
            temporary.unlink(missing_ok=True)
        lock.unlink(missing_ok=True)


def prepare_restore(root, location):
    manifest_path = Path(location).absolute()
    require(manifest_path.resolve() == manifest_path, "Transaction path cannot contain symlinks")
    require(manifest_path.name == "transaction.json" and manifest_path.parent.parent == root / BACKUPS,
            "Transaction must belong to this root's backup directory")
    manifest = loads(manifest_path.read_text(encoding="utf-8"))
    fields(manifest, {"version", "root", "status", "files"}, {"error", "recovery_errors"})
    require(type(manifest["version"]) is int and manifest["version"] == 1 and manifest["root"] == str(root),
            "Transaction version/root mismatch")
    require(isinstance(manifest["files"], list) and bool(manifest["files"]), "Empty/invalid transaction")
    originals, updated = {}, {}
    for entry in manifest["files"]:
        fields(entry, {"file", "backup", "before_sha256", "after_sha256"})
        name = entry["file"]
        target = file_path(root, name,allow_missing=True)
        require(name not in originals, "Duplicate transaction file")
        backup = entry["backup"]
        if backup is None:
            require(entry['before_sha256'] is None and re.fullmatch(r'Map[0-9]{3,}\.json',name),'Invalid creation backup')
            originals[name]=current_bytes(root,name)
            require(originals[name] is not None and sha(originals[name])==entry['after_sha256'],'Created map changed; refusing removal')
            updated[name]=None
            continue
        require(isinstance(backup, str) and re.fullmatch(r"[0-9]+\.json", backup), "Invalid backup filename")
        backup_path = manifest_path.parent / backup
        require(not backup_path.is_symlink(), "Backup cannot be a symlink")
        updated[name] = backup_path.read_bytes()
        require(sha(updated[name]) == entry["before_sha256"], f"Backup checksum mismatch: {name}")
        read_document(updated[name])
        originals[name] = current_bytes(root,name)
        if entry['after_sha256'] is None:require(originals[name] is None,'Deleted map path is occupied')
    return originals, updated


def preview_result(root, originals, updated, intent):
    files = [{"file": name, "before_sha256": sha(raw) if raw is not None else None, "after_sha256": sha(updated[name]) if updated[name] is not None else None,
              "changed": raw != updated[name]} for name, raw in originals.items()]
    token = sha(dumps({"root": str(root), "files": files, "intent": intent},
                     sort_keys=True, separators=(",", ":")).encode("utf-8"))
    return {"root": str(root), "files": files, "changed": any(f["changed"] for f in files),
            "written": False, "preview_sha256": token}


def run(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", required=True, help="Explicit database directory, usually PROJECT/data")
    commands = parser.add_subparsers(dest="command", required=True)
    inspect = commands.add_parser("inspect")
    inspect.add_argument("--file", required=True)
    inspect.add_argument("--path", default="[]", help="JSON path array; use --path-file for complex paths")
    inspect.add_argument("--path-file")
    inspect.add_argument("--summary", action="store_true")
    inspect.add_argument("--children", action="store_true", help="List immediate child paths and types")
    validate = commands.add_parser("validate", help="JSON syntax only; not game semantics")
    validate.add_argument("--file", required=True)
    for action in ("apply", "restore"):
        command = commands.add_parser(action)
        command.add_argument("--plan" if action == "apply" else "--transaction", required=True)
        command.add_argument("--write", action="store_true")
        command.add_argument("--expect-preview", help="Required with --write: preview_sha256 from preview")
    args = parser.parse_args(argv)
    root = root_path(args.root)
    if args.command in ("inspect", "validate"):
        raw = file_path(root, args.file).read_bytes()
        document = read_document(raw)
        result = {"file": args.file, "sha256": sha(raw), "validation": "json-syntax"}
        if args.command == "validate":
            return result
        require(not args.path_file or args.path == "[]", "Use either --path or --path-file")
        path = loads(Path(args.path_file).read_text(encoding="utf-8-sig")) if args.path_file else loads(args.path)
        value = get(document, path)
        result.update(path=path, summary=describe(value))
        if not args.summary and not args.children:
            result["value"] = value
        if args.children:
            iterator = value.items() if isinstance(value, dict) else enumerate(value) if isinstance(value, list) else ()
            result["children"] = [{"path": path + [key], "summary": describe(item)} for key, item in iterator]
            if isinstance(value, str):
                try:
                    decoded = loads(value)
                except ValueError:
                    result["json_decodable"] = False
                else:
                    result.update(json_decodable=True, decoded_path=path + [DECODE], decoded_summary=describe(decoded))
        return result
    if args.command == "apply":
        plan = loads(Path(args.plan).read_text(encoding="utf-8-sig"))
        originals, updated, log = prepare(root, plan)
        result = preview_result(root, originals, updated, {"command": "apply", "plan": plan})
        result["changes"] = log
    else:
        originals, updated = prepare_restore(root, args.transaction)
        result = preview_result(root, originals, updated, {"command": "restore", "transaction": str(Path(args.transaction).absolute())})
    require(not args.write or args.expect_preview, "--write requires --expect-preview from a preview")
    if args.expect_preview:
        require(args.expect_preview == result["preview_sha256"], "Preview mismatch: source or plan changed; preview again")
    if args.write and result["changed"]:
        result["transaction"] = commit(root, originals, updated)
        result["written"] = True
    return result


def main():
    try:
        result = run()
    except (ValueError, OSError, UnicodeError, RecursionError) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=True), file=sys.stderr)
        return 1
    print(json.dumps({"ok": True, **result}, ensure_ascii=True, indent=2, allow_nan=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
