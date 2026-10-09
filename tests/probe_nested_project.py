"""Exercise nested parameter edits on a COPY through the public CLI only.

Usage: python3 tests/probe_nested_project.py /path/to/js/plugins.js
Project data and plans are saved in a temporary directory, never in this repo.
JSON decoding here is fixture analysis, not inference of plugin parameter types.
"""

import copy
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile


SCRIPT = Path(__file__).resolve().parents[1] / "skills/rpgmaker-plugins/scripts/plugins_js.py"


def read_independently(raw):
    # Independent of the editor parser; this probe targets standard generated files.
    text = raw.decode("utf-8-sig")
    return json.loads(text[text.index("["):text.rindex("]") + 1])


def leaves(value, path=(), layers=0):
    if isinstance(value, str):
        try:
            decoded = json.loads(value)
        except ValueError:
            yield layers, path, value
        else:
            yield from leaves(decoded, path + (("decode", None),), layers + 1)
    elif isinstance(value, dict):
        for key, item in value.items():
            yield from leaves(item, path + (("key", key),), layers)
    elif isinstance(value, list):
        for index, item in enumerate(value):
            yield from leaves(item, path + (("index", index),), layers)
    else:
        yield layers, path, value


def replace_leaf(value, path, replacement):
    if not path:
        return replacement
    (kind, key), *rest = path
    if kind == "decode":
        return json.dumps(replace_leaf(json.loads(value), rest, replacement), ensure_ascii=False)
    result = copy.deepcopy(value)
    result[key] = replace_leaf(value[key], rest, replacement)
    return result


def verify_single_leaf(before, after, path, replacement):
    if not path:
        assert after == replacement and before != after
        return
    (kind, key), *rest = path
    assert type(before) is type(after)
    if kind == "decode":
        verify_single_leaf(json.loads(before), json.loads(after), rest, replacement)
        return
    assert len(before) == len(after)
    if isinstance(before, dict):
        assert list(before) == list(after)
        positions = before.keys()
    else:
        positions = range(len(before))
    for position in positions:
        if position == key:
            verify_single_leaf(before[position], after[position], rest, replacement)
        else:
            # Untargeted encoded siblings must stay identical, not just decode alike.
            assert before[position] == after[position]


def changed_leaf(value):
    if isinstance(value, str):
        return value + '\n探针测试 "quoted" \\path 😀'
    if type(value) is bool:
        return not value
    if type(value) in (int, float):
        return value + 1
    return "nested-probe"


def main():
    source = Path(sys.argv[1]).resolve()
    raw = source.read_bytes()
    original_hash = hashlib.sha256(raw).hexdigest()
    folder = Path(tempfile.mkdtemp(prefix="rpgmaker-nested-probe-"))
    target = folder / "plugins.js"
    shutil.copyfile(source, target)

    def cli(*args, expected=0):
        result = subprocess.run([sys.executable, str(SCRIPT), "--file", str(target), *args],
                                capture_output=True, text=True)
        assert result.returncode == expected, result.stderr
        return json.loads(result.stdout if expected == 0 else result.stderr)

    inspected = cli("inspect")
    original = read_independently(raw)
    assert inspected["plugins"] == original
    assert inspected["sha256"] == original_hash
    names = [p["name"] for p in original]
    assert len(set(names)) == len(names), "Probe requires unique names"
    cases, operations = [], []
    flat_tested = False
    for item in original:
        parameters = {}
        for key, value in item["parameters"].items():
            candidates = list(leaves(value))
            if not candidates:
                continue
            depth, path, leaf = max(candidates, key=lambda item: item[0])
            if depth < 2:
                if depth != 0 or flat_tested:
                    continue
                flat_tested = True
            replacement = changed_leaf(leaf)
            parameters[key] = replace_leaf(value, path, replacement)
            cases.append({"plugin": item["name"], "parameter": key, "decode_layers": depth,
                          "path": path, "replacement": replacement})
        if parameters:
            operations.append({"op": "update", "name": item["name"], "parameters": parameters})
    assert any(c["decode_layers"] >= 2 for c in cases), "No nested cases found"
    planpath = folder / "plan.json"
    planpath.write_text(json.dumps({"version": 1, "operations": operations}, ensure_ascii=False), encoding="utf-8")
    preview = cli("apply", "--plan", str(planpath))
    assert preview["changed"] and not preview["written"]
    assert target.read_bytes() == raw
    assert not (folder / ".plugins-js-backups").exists()
    written = cli("apply", "--plan", str(planpath), "--write", "--expect-sha256", preview["sha256"])
    assert written["written"]
    assert Path(written["backup"]).read_bytes() == raw
    output = target.read_bytes()
    after = cli("inspect")["plugins"]
    assert read_independently(output) == after
    assert len(after) == len(original)
    case_map = {(c["plugin"], c["parameter"]): c for c in cases}
    untouched = 0
    for before_plugin, after_plugin in zip(original, after):
        assert before_plugin.keys() == after_plugin.keys()
        for key in before_plugin:
            if key != "parameters":
                assert before_plugin[key] == after_plugin[key]
        assert before_plugin["parameters"].keys() == after_plugin["parameters"].keys()
        for key, value in before_plugin["parameters"].items():
            actual = after_plugin["parameters"][key]
            case = case_map.get((before_plugin["name"], key))
            if case:
                verify_single_leaf(value, actual, case["path"], case["replacement"])
            else:
                assert value == actual
                untouched += 1
    syntax = "not available"
    if shutil.which("node"):
        result = subprocess.run(["node", "--check", str(target)], capture_output=True, text=True)
        assert result.returncode == 0, result.stderr
        syntax = "passed"
    # Repeating the same plan must not rewrite or add a backup.
    backup_count = len(list((folder / ".plugins-js-backups").iterdir()))
    repeated = cli("apply", "--plan", str(planpath), "--write", "--expect-sha256", written["after_sha256"])
    assert not repeated["changed"] and not repeated["written"]
    assert len(list((folder / ".plugins-js-backups").iterdir())) == backup_count
    cli("apply", "--plan", str(planpath), "--write", "--expect-sha256", original_hash, expected=1)
    assert target.read_bytes() == output
    badplan = folder / "invalid-plan.json"
    badplan.write_text(json.dumps({"version": 1, "operations": [
        {"op": "update", "name": original[0]["name"], "status": not original[0]["status"]},
        {"op": "update", "name": original[0]["name"], "parameters": {"invalid": {"nested": True}}}
    ]}), encoding="utf-8")
    cli("apply", "--plan", str(badplan), "--write", "--expect-sha256", written["after_sha256"], expected=1)
    assert target.read_bytes() == output
    # Keep modified evidence separately; restore the test target through the script.
    shutil.copyfile(target, folder / "modified-evidence.js")
    restore_preview = cli("restore", "--backup", written["backup"])
    cli("restore", "--backup", written["backup"], "--write", "--expect-sha256", restore_preview["sha256"])
    assert target.read_bytes() == raw
    assert source.read_bytes() == raw, "Original source changed during probe"
    report = {"source": str(source), "source_bytes": len(raw), "source_sha256": original_hash,
              "source_unchanged": True, "plugins": len(original),
              "parameters": sum(len(p["parameters"]) for p in original),
              "tested_parameters": len(cases), "nested_parameters_tested": sum(c["decode_layers"] >= 2 for c in cases),
              "untouched_parameters_identical": untouched, "max_decode_layers": max(c["decode_layers"] for c in cases),
              "changed_plugins": len(operations), "node_syntax": syntax,
              "checks": ["independent JSON read agrees", "preview does not write", "one leaf per selected parameter",
                         "all sibling fields preserved", "backup equals original", "repeated apply is no-op",
                         "stale fingerprint rejected", "invalid batch does not write", "restore byte-exact", "source unchanged"],
              "cases": [{k: v for k, v in c.items() if k != "replacement"} for c in cases],
              "artifacts": str(folder)}
    (folder / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({k: v for k, v in report.items() if k != "cases"}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
