import copy
import importlib.util
import json
import os
from pathlib import Path
import random
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch


SCRIPT = Path(__file__).resolve().parents[1] / "skills/rpgmaker-database/scripts/database.py"
spec = importlib.util.spec_from_file_location("database", SCRIPT)
db = importlib.util.module_from_spec(spec)
spec.loader.exec_module(db)
D = {"decode": "json"}


def operation(action="set", path=None, **kwargs):
    return {"op": action, "file": "custom.json", "path": [] if path is None else path, **kwargs}


def plan(*ops):
    return {"version": 1, "operations": list(ops)}


class DatabaseTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name).resolve()
        self.target = self.root / "custom.json"
        self.original = {"name": "中文", "list": [None, {"id": 1, "value": 7}, {"id": 2}],
                         "opaque": '{ "keep" :  1 }', "0": "numeric key"}
        self.target.write_text(json.dumps(self.original, ensure_ascii=False), encoding="utf-8")
        self.planpath = self.root / "operation-plan.json"

    def cli(self, *args, ok=True):
        result = subprocess.run([sys.executable, str(SCRIPT), "--root", str(self.root), *args],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 0 if ok else 1, result.stderr)
        return json.loads(result.stdout if ok else result.stderr)

    def save_plan(self, *ops):
        self.planpath.write_text(json.dumps(plan(*ops), ensure_ascii=False), encoding="utf-8")

    def preview(self):
        return self.cli("apply", "--plan", str(self.planpath))

    def write(self, preview=None):
        preview = self.preview() if preview is None else preview
        return self.cli("apply", "--plan", str(self.planpath), "--write", "--expect-preview", preview["preview_sha256"])

    def test_read_any_path_and_discover_children(self):
        for path, expected in [([], self.original), (["list", 1, "value"], 7), (["0"], "numeric key")]:
            result = self.cli("inspect", "--file", "custom.json", "--path", json.dumps(path))
            self.assertEqual(result["value"], expected)
        child = self.cli("inspect", "--file", "custom.json", "--path", '["opaque"]', "--children")
        self.assertTrue(child["json_decodable"])
        self.assertEqual(child["decoded_path"], ["opaque", D])
        self.assertEqual(self.cli("inspect", "--file", "custom.json", "--children")["children"][0]["path"], ["name"])

    def test_six_decode_layers_and_untouched_strings(self):
        nested = {"leaf": "before", "sibling": ' {"n":1} '}
        for i in range(6):
            nested = json.dumps(nested, ensure_ascii=False)
        obj = {"nested": nested, "opaque": "true"}
        self.target.write_text(json.dumps(obj), encoding="utf-8")
        path = ["nested"] + [D] * 6 + ["leaf"]
        self.save_plan(operation(path=path, expect="before", value='改\n"\\😀'))
        self.write()
        after = json.loads(self.target.read_text())
        self.assertEqual(after["opaque"], "true")
        decoded = after["nested"]
        for i in range(6):
            decoded = json.loads(decoded)
        self.assertEqual(decoded, {"leaf": '改\n"\\😀', "sibling": ' {"n":1} '})
        self.assertEqual(self.cli("inspect", "--file", "custom.json", "--path", json.dumps(path))["value"], '改\n"\\😀')

    def test_encoded_object_and_array_operations(self):
        original = {"encoded": json.dumps({"rows": [json.dumps({"name": "A", "keep": "1"})]})}
        path = ["encoded", D, "rows", 0, D]
        changed = db.apply_operation(original, operation("put", path + ["new"], value=[1, False]))
        changed = db.apply_operation(changed, operation("remove", path + ["name"], expect="A"))
        self.assertEqual(db.get(changed, path), {"keep": "1", "new": [1, False]})
        changed = db.apply_operation(changed, operation("splice", ["encoded", D, "rows"], index=1, delete_count=0, items=["second"]))
        self.assertEqual(db.get(changed, ["encoded", D, "rows", 1]), "second")

    def test_root_and_all_json_types_can_be_replaced(self):
        for value in [None, False, 0, 1.0, "", [], {}, [None, {"custom": True}]]:
            with self.subTest(value=value):
                result = db.apply_operation(self.original, operation(value=value))
                self.assertTrue(db.equal(result, value))

    def test_type_changes_are_not_lost_as_noops(self):
        for before, after in [(True, 1), (1, True), (1, 1.0), (False, 0), ([True], [1])]:
            raw = json.dumps(before).encode()
            rendered = db.render(raw, before, after)
            self.assertNotEqual(raw, rendered)
            self.assertTrue(db.equal(db.read_document(rendered), after))
        with self.assertRaises(db.Invalid):
            db.apply_operation({"x": True}, operation(path=["x"], expect=1, value=2))

    def test_keys_with_punctuation_empty_and_numeric_strings(self):
        obj = {"": {"a.b/c~[0]": {"0": 1}}, "中文": 2}
        path = ["", "a.b/c~[0]", "0"]
        changed = db.apply_operation(obj, operation(path=path, value=3))
        self.assertEqual(db.get(changed, path), 3)
        self.assertEqual(changed["中文"], 2)

    def test_put_remove_and_splice_are_explicit(self):
        obj = db.apply_operation(self.original, operation("put", ["custom"], value={"new": True}))
        obj = db.apply_operation(obj, operation("remove", ["list", 1], expect={"id": 1, "value": 7}))
        self.assertEqual(obj["list"], [None, None, {"id": 2}])
        obj = db.apply_operation(obj, operation("splice", ["list"], index=1, delete_count=1, items=[{"id": 5}, {"id": 6}]))
        self.assertEqual(obj["list"], [None, {"id": 5}, {"id": 6}, {"id": 2}])
        obj = db.apply_operation(obj, operation("remove", ["custom"]))
        self.assertNotIn("custom", obj)

    def test_invalid_paths_and_operations(self):
        bad = [operation(path=["missing"], value=1), operation(path=["list", 999], value=1),
               operation(path=["list", -1], value=1), operation(path=["list", True], value=1),
               operation(path=["name", D], value=1), operation(path=["list", D], value=1),
               operation(path=[{"decode": "xml"}], value=1), operation(path="name", value=1),
               operation("put", ["name"], value=1), operation("put", ["list", 0], value=1),
               operation("remove", []), operation("splice", ["list"], index=0, delete_count=10, items=[]),
               operation("splice", ["list"], index=True, delete_count=0, items=[]),
               operation(path=["name"], value=1, typo=True)]
        for op in bad:
            with self.subTest(op=op), self.assertRaises(ValueError):
                db.apply_operation(self.original, op)

    def test_strict_json_and_no_execution(self):
        for text in ['{"x":1,"x":2}', 'NaN', 'Infinity', '1e999', '{"x":1,}', '(()=>[])()']:
            with self.subTest(text=text), self.assertRaises(ValueError):
                db.loads(text)
        text = "require('fs').writeFileSync('unexpected', 'x')"
        obj = db.apply_operation(self.original, operation(path=["name"], value=text))
        self.assertEqual(obj["name"], text)
        with self.assertRaises(ValueError):
            db.get(obj, ["name", D])

    def test_preview_no_side_effects_and_exact_restore(self):
        raw = self.target.read_bytes()
        self.target.chmod(0o640)
        self.save_plan(operation(path=["list", 1, "value"], value=9))
        preview = self.preview()
        self.assertTrue(preview["changed"])
        self.assertFalse(preview["written"])
        self.assertEqual(self.target.read_bytes(), raw)
        self.assertFalse((self.root / db.BACKUPS).exists())
        result = self.write(preview)
        self.assertEqual(self.target.stat().st_mode & 0o777, 0o640)
        self.assertTrue(result["written"])
        manifest = json.loads(Path(result["transaction"]).read_text())
        self.assertEqual(manifest["status"], "committed")
        restore = self.cli("restore", "--transaction", result["transaction"])
        self.cli("restore", "--transaction", result["transaction"], "--write", "--expect-preview", restore["preview_sha256"])
        self.assertEqual(self.target.read_bytes(), raw)

    def test_fingerprint_binds_plan_and_all_files(self):
        self.save_plan(operation(path=["name"], value="new"))
        preview = self.preview()
        self.cli("apply", "--plan", str(self.planpath), "--write", ok=False)
        self.save_plan(operation(path=["name"], value="different plan"))
        self.cli("apply", "--plan", str(self.planpath), "--write", "--expect-preview", preview["preview_sha256"], ok=False)
        self.assertEqual(json.loads(self.target.read_text()), self.original)
        preview = self.preview()
        self.target.write_text(json.dumps({**self.original, "external": True}))
        self.cli("apply", "--plan", str(self.planpath), "--write", "--expect-preview", preview["preview_sha256"], ok=False)
        self.assertTrue(json.loads(self.target.read_text())["external"])

    def test_failed_batch_never_writes_valid_first_operation(self):
        raw = self.target.read_bytes()
        self.save_plan(operation(path=["name"], value="changed"), operation(path=["list", 1000], value=1))
        self.cli("apply", "--plan", str(self.planpath), ok=False)
        self.assertEqual(self.target.read_bytes(), raw)
        self.assertFalse((self.root / db.BACKUPS).exists())

    def test_multifile_transaction_and_restore(self):
        second = self.root / "other.json"
        second.write_text('[null,{"id":1,"name":"one"}]')
        raw = {p: p.read_bytes() for p in (self.target, second)}
        self.save_plan(operation(path=["name"], value="changed"),
                       {"op": "set", "file": "other.json", "path": [1, "name"], "value": "two"})
        written = self.write()
        self.assertEqual(len(written["files"]), 2)
        preview = self.cli("restore", "--transaction", written["transaction"])
        self.cli("restore", "--transaction", written["transaction"], "--write", "--expect-preview", preview["preview_sha256"])
        for p, original in raw.items():
            self.assertEqual(p.read_bytes(), original)

    def test_replace_failure_rolls_back_previous_files(self):
        second = self.root / "second.json"
        second.write_bytes(b'{}')
        originals = {"custom.json": self.target.read_bytes(), "second.json": second.read_bytes()}
        updated = {"custom.json": b'{"changed":true}', "second.json": b'{"changed":true}'}
        actual_replace = db.os.replace

        def fail_second(src, dst):
            if Path(dst) == second:
                raise OSError("simulated second file failure")
            return actual_replace(src, dst)

        with patch.object(db.os, "replace", side_effect=fail_second), self.assertRaises(db.Invalid):
            db.commit(self.root, originals, updated)
        for name, raw in originals.items():
            self.assertEqual((self.root / name).read_bytes(), raw)
        manifest = next((self.root / db.BACKUPS).glob("*/transaction.json"))
        self.assertEqual(json.loads(manifest.read_text())["status"], "rolled_back")
        self.assertFalse((self.root / db.LOCK).exists())
        self.assertEqual(list(self.root.glob(".rpgmaker-db-*")), [self.root / db.BACKUPS])

    def test_external_edit_is_not_overwritten_during_rollback(self):
        second = self.root / "second.json"
        second.write_bytes(b'{}')
        originals = {"custom.json": self.target.read_bytes(), "second.json": b'{}'}
        updated = {name: b'{"changed":true}' for name in originals}
        actual_replace = db.os.replace

        def external_change(src, dst):
            if Path(dst) == second:
                self.target.write_bytes(b'{"external":true}')
                raise OSError("external editor")
            return actual_replace(src, dst)

        with patch.object(db.os, "replace", side_effect=external_change), self.assertRaises(db.Invalid):
            db.commit(self.root, originals, updated)
        self.assertEqual(self.target.read_bytes(), b'{"external":true}')
        manifest = next((self.root / db.BACKUPS).glob("*/transaction.json"))
        self.assertEqual(json.loads(manifest.read_text())["status"], "recovery_required")

    def test_backup_failure_and_lock_stop_writes(self):
        raw = self.target.read_bytes()
        lock = self.root / db.LOCK
        lock.touch()
        with self.assertRaises(FileExistsError):
            db.commit(self.root, {"custom.json": raw}, {"custom.json": b'{}'})
        self.assertTrue(lock.exists())
        lock.unlink()
        (self.root / db.BACKUPS).write_text("blocked")
        with self.assertRaises(db.Invalid):
            db.commit(self.root, {"custom.json": raw}, {"custom.json": b'{}'})
        self.assertEqual(self.target.read_bytes(), raw)
        self.assertFalse(lock.exists())

    def test_symlink_and_path_escape_rejected(self):
        link = self.root / "alias.json"
        link.symlink_to(self.target)
        folder = self.root / "aliasdir"
        folder.symlink_to(self.root, target_is_directory=True)
        for name in ["alias.json", "aliasdir/custom.json", "../outside.json", str(self.target), "plugins.js", db.BACKUPS + "/x.json"]:
            with self.subTest(name=name), self.assertRaises(db.Invalid):
                db.file_path(self.root, name)

    def test_corrupt_backup_rejected_and_damaged_target_recoverable(self):
        original = self.target.read_bytes()
        self.save_plan(operation(path=["name"], value="updated"))
        result = self.write()
        self.target.write_bytes(b'broken\xff')
        preview = self.cli("restore", "--transaction", result["transaction"])
        self.cli("restore", "--transaction", result["transaction"], "--write", "--expect-preview", preview["preview_sha256"])
        self.assertEqual(self.target.read_bytes(), original)
        (Path(result["transaction"]).parent / "0.json").write_bytes(b'{}')
        self.cli("restore", "--transaction", result["transaction"], ok=False)
        self.assertEqual(self.target.read_bytes(), original)

    def test_noop_preserves_original_and_nested_format(self):
        raw = b'\xef\xbb\xbf{\r\n  "encoded": "{ \\"x\\" : 1 }"\r\n}\r\n'
        self.target.write_bytes(raw)
        self.save_plan(operation(path=["encoded", D, "x"], value=1))
        result = self.write()
        self.assertFalse(result["written"])
        self.assertEqual(self.target.read_bytes(), raw)
        self.assertFalse((self.root / db.BACKUPS).exists())

    def test_unicode_bom_crlf_and_surrogate(self):
        raw = b'\xef\xbb\xbf{\r\n  "value": 1,\r\n  "str": "\\ud800"\r\n}\r\n'
        original = db.read_document(raw)
        updated = dict(original, value="中文😀")
        rendered = db.render(raw, original, updated)
        self.assertTrue(rendered.startswith(b'\xef\xbb\xbf'))
        self.assertNotIn(b'\n', rendered.replace(b'\r\n', b''))
        self.assertTrue(db.equal(db.read_document(rendered), updated))

    def test_fixed_seed_arbitrary_paths_preserve_other_values(self):
        rng = random.Random(219)
        for _ in range(100):
            leaf = "original"
            tree, path = leaf, []
            for depth in range(rng.randint(1, 12)):
                kind = rng.choice(["object", "array", "encoded"])
                if kind == "object":
                    tree, path = {"target": tree, "keep": "0001"}, ["target"] + path
                elif kind == "array":
                    tree, path = [None, tree, {"opaque": "true"}], [1] + path
                else:
                    tree, path = json.dumps(tree), [D] + path
            original = copy.deepcopy(tree)
            changed = db.apply_operation(tree, operation(path=path, expect=leaf, value="updated"))
            self.assertEqual(db.get(changed, path), "updated")
            restored = db.apply_operation(changed, operation(path=path, value=leaf))
            # Decoded containers may be reformatted; each untouched sibling stays exact.
            before, after = original, changed
            for token in path:
                if token == D:
                    before, after = json.loads(before), json.loads(after)
                else:
                    for k in before.keys() if isinstance(before, dict) else range(len(before)):
                        if k != token:
                            self.assertTrue(db.equal(before[k], after[k]))
                    before, after = before[token], after[token]
            self.assertEqual(db.get(restored, path), leaf)
            self.assertTrue(db.equal(tree, original))

    @unittest.skipUnless(os.environ.get("RPGMAKER_TEST_PROJECT"), "Set RPGMAKER_TEST_PROJECT for read-only integration")
    def test_real_project_arbitrary_fields_on_copies(self):
        source_root = Path(os.environ["RPGMAKER_TEST_PROJECT"]) / "data"
        names = ["Actors.json", "System.json", "CommonEvents.json", "Map001.json", "books.json"]
        originals, operations, expected = {}, [], {}
        for name in names:
            source = source_root / name
            if not source.exists():
                continue
            originals[name] = source.read_bytes()
            value = json.loads(originals[name].decode("utf-8-sig"))
            shutil.copyfile(source, self.root / name)
            if name == "Actors.json":
                index = next(i for i, record in enumerate(value) if isinstance(record, dict))
                path, replacement = [index, "traits"], [{"code": 21, "dataId": 2, "value": 1.25}]
            elif name == "System.json":
                path, replacement = ["switches", 1], "数据库测试"
            elif name == "CommonEvents.json":
                index = next(i for i, record in enumerate(value) if isinstance(record, dict) and record.get("list"))
                path, replacement = [index, "list", 0, "parameters"], ["数据库测试", 1, False, None]
            elif name == "Map001.json":
                path, replacement = ["data", 0], 123
            else:
                path, replacement = ["library"], {"test": [{"nested": {"name": "测试"}}]}
            changed = copy.deepcopy(value)
            cursor = changed
            for token in path[:-1]:
                cursor = cursor[token]
            cursor[path[-1]] = replacement
            expected[name] = changed
            operations.append({"op": "set", "file": name, "path": path, "value": replacement})
        # Actual plugin-command argument: nested JSON text inside event parameters.
        if "CommonEvents.json" in expected:
            def encoded_leaves(value, path=(), layers=0):
                if isinstance(value, str):
                    try:
                        nested = json.loads(value)
                    except ValueError:
                        yield layers, list(path), value
                    else:
                        yield from encoded_leaves(nested, path + (D,), layers + 1)
                elif isinstance(value, dict):
                    for key, child in value.items():
                        yield from encoded_leaves(child, path + (key,), layers)
                elif isinstance(value, list):
                    for index, child in enumerate(value):
                        yield from encoded_leaves(child, path + (index,), layers)
                else:
                    yield layers, list(path), value

            # Construct independent expected data, without using the editor's mutator.
            def change_encoded(value, path, replacement):
                if not path:
                    return replacement
                token, *rest = path
                if token == D:
                    return json.dumps(change_encoded(json.loads(value), rest, replacement), ensure_ascii=False, separators=(",", ":"))
                result = copy.deepcopy(value)
                result[token] = change_encoded(value[token], rest, replacement)
                return result

            depth, path, leaf = max(encoded_leaves(expected["CommonEvents.json"]), key=lambda case: case[0])
            if depth >= 2:
                replacement = not leaf if type(leaf) is bool else leaf + 1 if type(leaf) in (int, float) else "深层测试"
                operations.append({"op": "set", "file": "CommonEvents.json", "path": path, "expect": leaf, "value": replacement})
                expected["CommonEvents.json"] = change_encoded(expected["CommonEvents.json"], path, replacement)
        self.assertGreaterEqual(len(operations), 4)
        self.save_plan(*operations)
        written = self.write()
        for name, value in expected.items():
            self.assertEqual(json.loads((self.root / name).read_text(encoding="utf-8-sig")), value)
        preview = self.cli("restore", "--transaction", written["transaction"])
        self.cli("restore", "--transaction", written["transaction"], "--write", "--expect-preview", preview["preview_sha256"])
        for name, raw in originals.items():
            self.assertEqual((self.root / name).read_bytes(), raw)
            self.assertEqual((source_root / name).read_bytes(), raw)


if __name__ == "__main__":
    unittest.main()
