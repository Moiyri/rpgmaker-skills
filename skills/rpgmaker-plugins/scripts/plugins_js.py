#!/usr/bin/env python3
"""Edit RPG Maker plugins.js as data, never execute JavaScript. Python >= 3.10."""

import argparse
import copy
import difflib
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import sys
import tempfile


class Invalid(ValueError):
    pass


def require(condition, message):
    if not condition:
        raise Invalid(message)


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, f"Duplicate JSON key: {key}")
        result[key] = value
    return result


def invalid_constant(value):
    raise Invalid(f"Non-JSON constant: {value}")


DECODER = json.JSONDecoder(object_pairs_hook=unique_object, parse_constant=invalid_constant)
TRIVIA = r"(?:\s|//[^\r\n]*(?:\r\n|\r|\n|$)|/\*[\s\S]*?\*/)"
PREFIX = re.compile(r"\A\ufeff?" + TRIVIA + r"*var\s+\$plugins\s*=\s*")
SUFFIX = re.compile(r"\A" + TRIVIA + r"*;?" + TRIVIA + r"*\Z")


def json_read(path):
    return DECODER.decode(Path(path).read_text(encoding="utf-8-sig"))


def validate(plugins):
    require(isinstance(plugins, list), "$plugins must be an array")
    for i, plugin in enumerate(plugins):
        require(isinstance(plugin, dict), f"Plugin {i} must be an object")
        require(isinstance(plugin.get("name"), str), f"Plugin {i}: name must be a string")
        require(type(plugin.get("status")) is bool, f"Plugin {i}: status must be boolean")
        require(isinstance(plugin.get("description"), str), f"Plugin {i}: description must be a string")
        parameters = plugin.get("parameters")
        require(isinstance(parameters, dict), f"Plugin {i}: parameters must be an object")
        require(all(isinstance(v, str) for v in parameters.values()),
                f"Plugin {i}: every parameter value must be a string")


def parse(raw):
    text = raw.decode("utf-8")
    match = PREFIX.match(text)
    require(match is not None, "Expected comments followed by var $plugins = JSON array")
    plugins, end = DECODER.raw_decode(text, match.end())
    require(SUFFIX.fullmatch(text[end:]) is not None,
            "Unexpected JavaScript after $plugins; refusing to execute or discard it")
    validate(plugins)
    return text, match.end(), end, plugins


def locate(plugins, name):
    require(isinstance(name, str) and bool(name), "Selector name must be a nonempty string")
    matches = [i for i, p in enumerate(plugins) if p["name"] == name]
    require(len(matches) == 1, f"Expected one plugin named {name!r}; found {len(matches)}")
    return matches[0]


def keys(value, allowed, required):
    require(isinstance(value, dict), "Operation must be an object")
    require(not (value.keys() - allowed), f"Unknown fields: {sorted(value.keys() - allowed)}")
    require(required <= value.keys(), f"Missing fields: {sorted(required - value.keys())}")


def place(plugins, plugin, op, required=False):
    positions = [key for key in ("before", "after") if key in op]
    require(len(positions) == 1 if required else len(positions) <= 1,
            "Use exactly one of before/after for move; at most one for add")
    index = len(plugins)
    if positions:
        key = positions[0]
        index = locate(plugins, op[key]) + (key == "after")
    plugins.insert(index, plugin)


def transform(plugins, plan):
    keys(plan, {"version", "operations"}, {"version", "operations"})
    require(type(plan["version"]) is int and plan["version"] == 1, "Plan version must be 1")
    require(isinstance(plan["operations"], list) and bool(plan["operations"]),
            "operations must be a nonempty array")
    result = copy.deepcopy(plugins)
    for op in plan["operations"]:
        require(isinstance(op, dict), "Operation must be an object")
        action = op.get("op")
        if action == "add":
            keys(op, {"op", "plugin", "before", "after"}, {"op", "plugin"})
            plugin = copy.deepcopy(op["plugin"])
            validate([plugin])
            require(bool(plugin["name"]), "Added plugin must have a nonempty name")
            require(not any(p["name"].casefold() == plugin["name"].casefold() for p in result),
                    "Added plugin name already exists (case-insensitive)")
            place(result, plugin, op)
        elif action == "remove":
            keys(op, {"op", "name"}, {"op", "name"})
            result.pop(locate(result, op["name"]))
        elif action == "move":
            keys(op, {"op", "name", "before", "after"}, {"op", "name"})
            plugin = result.pop(locate(result, op["name"]))
            place(result, plugin, op, required=True)
        elif action == "update":
            fields = {"status", "description", "parameters", "unset_parameters"}
            keys(op, fields | {"op", "name"}, {"op", "name"})
            require(bool(fields & op.keys()), "update needs at least one changed field")
            plugin = result[locate(result, op["name"])]
            for field in ("status", "description"):
                if field in op:
                    plugin[field] = op[field]
            parameters = op.get("parameters", {})
            unset = op.get("unset_parameters", [])
            require(isinstance(parameters, dict), "parameters must be an object")
            require(isinstance(unset, list) and all(isinstance(k, str) for k in unset),
                    "unset_parameters must be an array of strings")
            require(len(set(unset)) == len(unset), "Duplicate unset_parameters")
            require(not (set(unset) & parameters.keys()), "Cannot set and unset the same parameter")
            for key in unset:
                require(key in plugin["parameters"], f"Parameter does not exist: {key}")
                del plugin["parameters"][key]
            plugin["parameters"].update(parameters)
        else:
            raise Invalid(f"Unknown operation: {action!r}")
        validate(result)
    return result


def render(parsed, plugins):
    text, start, end, original = parsed
    if plugins == original:
        return text.encode("utf-8")
    newline = "\r\n" if "\r\n" in text else "\n"
    # One entry per line, matching the editor's usual compact layout.
    rows = [json.dumps(p, ensure_ascii=False, separators=(",", ":"), allow_nan=False)
            .replace("\u2028", "\\u2028").replace("\u2029", "\\u2029") for p in plugins]
    array = "[" + newline + ("," + newline).join(rows) + newline + "]"
    return (text[:start] + array + text[end:]).encode("utf-8")


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def target_path(value):
    path = Path(value).absolute()
    require(path.name == "plugins.js", "Target filename must be plugins.js")
    require(not path.is_symlink() and path.is_file(), "Target must be an existing regular non-symlink file")
    return path


def commit(path, original, updated):
    lock = path.with_name(path.name + ".rpgmaker.lock")
    # Exclusive lock coordinates instances of this script, not the RPG Maker editor.
    fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    temporary = None
    try:
        os.close(fd)
        require(not path.is_symlink() and path.read_bytes() == original,
                "Target changed during operation; read and preview again")
        mode = stat.S_IMODE(path.stat().st_mode)
        backup_dir = path.parent / ".plugins-js-backups"
        backup_dir.mkdir(exist_ok=True)
        with tempfile.NamedTemporaryFile(prefix="plugins-", suffix=".js", dir=backup_dir,
                                         delete=False) as backup:
            backup_path = Path(backup.name)
            backup.write(original)
            backup.flush()
            os.fsync(backup.fileno())
        with tempfile.NamedTemporaryFile(prefix=".plugins-", dir=path.parent, delete=False) as out:
            temporary = Path(out.name)
            out.write(updated)
            out.flush()
            os.fchmod(out.fileno(), mode)
            os.fsync(out.fileno())
        require(not path.is_symlink() and path.read_bytes() == original,
                "Target changed before replacement; original left untouched")
        os.replace(temporary, path)
        temporary = None
        return str(backup_path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
        lock.unlink(missing_ok=True)


def run(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--file", required=True, help="Explicit path to existing plugins.js")
    subs = parser.add_subparsers(dest="command", required=True)
    inspect = subs.add_parser("inspect", help="Read and validate; emit plugins and SHA-256")
    inspect.add_argument("--name", help="Select a unique exact plugin name, including subfolders")
    inspect.add_argument("--summary", action="store_true", help="Omit parameter values and descriptions")
    subs.add_parser("validate", help="Validate supported format and schema")
    for command in ("apply", "restore"):
        sub = subs.add_parser(command)
        sub.add_argument("--plan" if command == "apply" else "--backup", required=True)
        sub.add_argument("--write", action="store_true", help="Write; otherwise preview only")
        sub.add_argument("--expect-sha256", help="Required with --write; fingerprint of current target")
    args = parser.parse_args(argv)
    path = target_path(args.file)
    original = path.read_bytes()
    result = {"file": str(path), "sha256": digest(original), "command": args.command}
    # Restore can recover a syntactically damaged target, but the backup must validate.
    if args.command == "restore":
        updated = Path(args.backup).read_bytes()
        parse(updated)
    else:
        parsed = parse(original)
        if args.command in ("inspect", "validate"):
            result["count"] = len(parsed[3])
            if args.command == "inspect":
                items = parsed[3]
                if args.name is not None:
                    items = [items[locate(items, args.name)]]
                result["plugins"] = ([{"name": p["name"], "status": p["status"],
                                       "parameter_count": len(p["parameters"])} for p in items]
                                     if args.summary else items)
            return result
        updated = render(parsed, transform(parsed[3], json_read(args.plan)))
        parse(updated)
    require(not args.write or args.expect_sha256, "--write requires --expect-sha256 from preview/inspect")
    if args.expect_sha256:
        require(args.expect_sha256 == digest(original), "SHA-256 mismatch; read and preview again")
    result.update(changed=original != updated, written=False, after_sha256=digest(updated))
    result["diff"] = "".join(difflib.unified_diff(
        original.decode("utf-8", errors="replace").splitlines(keepends=True),
        updated.decode("utf-8").splitlines(keepends=True),
        fromfile=str(path), tofile=str(path) + " (planned)"))
    if args.write and result["changed"]:
        result["backup"] = commit(path, original, updated)
        result["written"] = True
    return result


def main():
    try:
        result = run()
    except (Invalid, OSError, ValueError, UnicodeError, RecursionError) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=True), file=sys.stderr)
        return 1
    print(json.dumps({"ok": True, **result}, ensure_ascii=True, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
