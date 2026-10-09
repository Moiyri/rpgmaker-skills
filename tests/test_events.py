import copy
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest

SCRIPTS = Path(__file__).resolve().parents[1] / 'skills/rpgmaker-events/scripts'
sys.path.insert(0, str(SCRIPTS))
import events
from event_api import *

FIXTURES = Path(__file__).parent / 'fixtures/events'


def reference_event():
    return EventList([
        ShowText('1', speaker='2'),
        ShowText('3', speaker='4', background='dim', position='middle'),
        SetSwitch(6, on=True),
        If(Switch(6).is_on(), then=[
            Loop([
                ChangeVariable(1, operation='add', value=Constant(1)),
                If(Variable(1).greater_or_equal(10), then=[BreakLoop()]),
            ]),
            SetSwitch(6, on=False),
        ]),
    ])


class EventApiTests(unittest.TestCase):
    def test_reference165_exact_structure_and_compact_bytes(self):
        expected = json.loads((FIXTURES / 'common165.json').read_text())['list']
        actual = reference_event().compile()
        self.assertEqual(actual, expected)
        self.assertEqual(json.dumps(actual, ensure_ascii=False, separators=(',', ':')),
                         json.dumps(expected, ensure_ascii=False, separators=(',', ':')))
        self.assertEqual(len(events.index_commands(actual)), 9)

    def test_editor_else_and_call(self):
        reference = json.loads((FIXTURES / 'extra-editor-commands.json').read_text())
        actual = EventList([If(Switch(6).is_off(), [], []), CommonEvent(113)]).compile()
        self.assertIn(reference['411']['command'], actual)
        self.assertIn(reference['117']['command'], actual)
        self.assertEqual([c['code'] for c in actual], [111, 0, 411, 0, 412, 117, 0])
        self.assertNotIn(411, [c['code'] for c in EventList([If(Switch(6).is_on())]).compile()])

    def test_operands_and_operations(self):
        values = [(Constant(-2), [0, -2]), (VariableValue(3), [1, 3]),
                  (RandomValue(-2, 4), [2, -2, 4]), (ScriptValue('throw new Error()'), [4, 'throw new Error()'])]
        for op, operation in enumerate(['set', 'add', 'sub', 'mul', 'div', 'mod']):
            for value, tail in values:
                with self.subTest(operation=operation, value=value):
                    result = EventList([ChangeVariable(2, operation, value, end=4)]).compile()
                    self.assertEqual(result[0]['parameters'], [2, 4, op] + tail)
        for index, name in enumerate(['equal_to', 'greater_or_equal', 'less_or_equal', 'greater_than', 'less_than', 'not_equal_to']):
            cond = getattr(Variable(2), name)(VariableValue(3))
            self.assertEqual(EventList([If(cond)]).compile()[0]['parameters'], [1, 2, 1, 3, index])
        self.assertEqual(EventList([If(ScriptCondition('false'))]).compile()[0]['parameters'], [12, 'false'])

    def test_nested_edits_identity_and_mutable_fields(self):
        event = reference_event()
        first = event.find(ShowText)[0]
        first.lines = ['修改', '第二行']; first.speaker = '旁白'
        self.assertEqual(event.compile()[0]['parameters'][-1], '旁白')
        inner = event.find(ChangeVariable)[0]
        added = ShowText('循环内')
        event.insert_after(inner, added)
        self.assertEqual(event.compile()[9]['indent'], 2)
        event.replace(added, SetSwitch(7))
        event.remove(inner)
        self.assertEqual(len(event.find(ChangeVariable)), 0)
        self.assertEqual(len(event.find(SetSwitch)), 3)
        self.assertEqual(len(event.find(SetSwitch, recursive=False)), 1)
        with self.assertRaises(ValueError): event.remove(ShowText('循环内'))

    def test_validation_errors(self):
        bad = [BreakLoop(), SetSwitch(True), SetSwitch(5, end=3), SetSwitch(1, on=1),
               ShowText('a\nb'), ShowText(['a'] * 5), ShowText('x', background='bad'),
               ChangeVariable(1, 'set', 3), ChangeVariable(1, 'set', RandomValue(5, 2)),
               ChangeVariable(1, 'bad', Constant(1)), If(Variable(1).equal_to(True)), CommonEvent(0)]
        for node in bad:
            with self.subTest(node=node), self.assertRaises(ValueError): EventList([node]).compile()
        loop = Loop(); loop.body.append(loop)
        with self.assertRaisesRegex(ValueError, 'Cyclic'): EventList([loop]).compile()

    def test_plan_export_and_same_compiler(self):
        event = reference_event()
        target = {'kind': 'common', 'id': 165}
        plan = event.to_plan(target)
        self.assertEqual(events.compile_nodes(plan['edits'][0]['commands']) + [events.command(0, 0)], event.compile())
        with self.assertRaises(ValueError): event.to_plan(target, op='replace', index=0)
        indexed = EventList([BreakLoop()]).to_plan(target, op='insert_before', index=9, expect_list_sha256='fingerprint')
        self.assertEqual(indexed['edits'][0]['index'], 9)  # Context checked when applying.

    def test_preserving_serializer_and_restore(self):
        db = events.db
        for prefix, nl, suffix in [(b'', b'\n', b''), (b'\xef\xbb\xbf', b'\r\n', b'\r\n')]:
            with self.subTest(newline=nl), tempfile.TemporaryDirectory() as directory:
                root = Path(directory).resolve()
                raw = prefix + b'{'+nl+b'"keep":1e2,"escaped":"\\u4e2d",'+nl+b'"list":[{"code":0,"indent":0,"parameters":[]}]}'+suffix
                (root / 'Map001.json').write_bytes(raw)
                plan = {'version': 1, 'format': 'preserve', 'operations': [
                    {'op': 'set', 'file': 'Map001.json', 'path': ['list'], 'value': reference_event().compile()}]}
                originals, updated, _ = db.prepare(root, plan)
                self.assertEqual(updated['Map001.json'].split(b'"list":')[0], raw.split(b'"list":')[0])
                self.assertTrue(updated['Map001.json'].endswith(b'}'+suffix))
                self.assertEqual(updated['Map001.json'].count(nl), raw.count(nl))
                transaction = db.commit(root, originals, updated)
                before, restored = db.prepare_restore(root, transaction)
                db.commit(root, before, restored)
                self.assertEqual((root / 'Map001.json').read_bytes(), raw)

    @unittest.skipUnless(os.environ.get('RPGMAKER_EVENTS_PROJECT'), 'Set RPGMAKER_EVENTS_PROJECT for read-only project integration')
    def test_real_project_reference_and_copy_apply(self):
        project = Path(os.environ['RPGMAKER_EVENTS_PROJECT'])
        original = (project / 'data/CommonEvents.json').read_bytes()
        self.assertEqual(json.loads(original)[165]['list'], reference_event().compile())
        self.assertTrue(events.source_profile(project, True)['profile_matches'])
        with tempfile.TemporaryDirectory() as directory:
            import shutil
            replica = Path(directory).resolve()
            (replica / 'data').mkdir(); (replica / 'js').mkdir()
            shutil.copyfile(project / 'js/rmmz_objects.js', replica / 'js/rmmz_objects.js')
            shutil.copyfile(project / 'data/CommonEvents.json', replica / 'data/CommonEvents.json')
            target = {'kind': 'common', 'id': 165}
            plan = reference_event().to_plan(target)
            root, before, after, result = events.prepare(replica, plan)
            self.assertFalse(result['changed'])
            self.assertEqual(after['CommonEvents.json'], original)
            plan = EventList([ShowText('新文本')]).to_plan(target, op='replace', index=0,
                    expect_list_sha256=events.digest(reference_event().compile()))
            root, before, after, result = events.prepare(replica, plan)
            old_doc, new_doc = json.loads(original), json.loads(after['CommonEvents.json'])
            self.assertEqual(new_doc[:165], old_doc[:165]); self.assertEqual(new_doc[166:], old_doc[166:])
            self.assertEqual(after['CommonEvents.json'].count(b'\n'), original.count(b'\n'))
            old_lines, new_lines = original.splitlines(keepends=True), after['CommonEvents.json'].splitlines(keepends=True)
            self.assertEqual([i for i, pair in enumerate(zip(old_lines, new_lines)) if pair[0] != pair[1]], [166])
            events.db.commit(root, before, after)
        self.assertEqual((project / 'data/CommonEvents.json').read_bytes(), original)


class MessageDecoderTests(unittest.TestCase):
    def test_reference_roundtrip_and_source_independence(self):
        raw = reference_event().compile()
        event = EventList.from_commands(raw)
        self.assertEqual(len(event.find(ShowText)), 2)
        self.assertEqual(event.compile(), raw)
        event.find(ShowText)[0].speaker = '旁白'
        changed = event.compile()
        expected = copy.deepcopy(raw); expected[0]['parameters'][4] = '旁白'
        self.assertEqual(changed, expected)
        self.assertEqual(raw[0]['parameters'][4], '2')
        changed[0]['parameters'][4] = '外部修改'
        self.assertEqual(event.compile()[0]['parameters'][4], '旁白')

    def test_nested_dialogue_and_unknown_commands(self):
        raw = EventList([If(Switch(1).is_on(), [ShowText('旧文本')])]).compile()
        raw.insert(0, {'code': 999, 'indent': 0, 'parameters': [{'plugin': [1, 'x']}]})
        event = EventList.from_commands(raw)
        message = event.find(ShowText)[0]
        message.lines = ['第一行', '第二行']
        updated = event.compile()
        self.assertEqual(updated[0], raw[0])
        self.assertEqual(updated[2]['indent'], 1)
        self.assertEqual(updated[3:5], [events.command(401, 1, ['第一行']), events.command(401, 1, ['第二行'])])
        plan = event.to_plan({'kind': 'common', 'id': 1})
        edit = plan['edits'][0]
        self.assertNotIn('index', edit)
        self.assertEqual(edit['expect_list_sha256'], events.digest(raw))
        self.assertEqual(edit['op'], 'replace_all')

    def test_extensions_preserved_and_plan_rejected(self):
        raw = EventList([ShowText(['a','b'])]).compile()
        raw[0]['parameters'].append({'custom': True}); raw[0]['plugin'] = 7
        raw[1]['parameters'].append('extension'); raw[1]['plugin'] = 9
        event = EventList.from_commands(raw)
        self.assertEqual(event.compile(), raw)
        event.find(ShowText)[0].lines = ['new', 'b']
        expected = copy.deepcopy(raw); expected[1]['parameters'][0] = 'new'
        self.assertEqual(event.compile(), expected)
        plan = event.to_plan({'kind':'common','id':1})
        self.assertEqual(events.compile_nodes(plan['edits'][0]['commands']) + [events.command(0,0)], expected)

    def test_unrepresentable_text_stays_opaque(self):
        for params in [['',0,8,2,''], ['',0,0,2], ['',0,0,2,'',None]]:
            raw = [events.command(101,0,params), events.command(401,0,['x']), events.command(0,0)]
            event = EventList.from_commands(raw)
            self.assertEqual(event.compile(),raw)
        raw = [events.command(101,0,['',0,0,2,'']), events.command(401,1,['wrong indent']),events.command(0,0)]
        with self.assertRaises(ValueError): EventList.from_commands(raw)
        with self.assertRaises(ValueError):ShowText.from_commands(raw[:-1])
        with self.assertRaises(ValueError):EventList.from_commands(raw[:-1])

    def test_imported_structural_edits_and_invalid_fields_rejected(self):
        event = EventList.from_commands(reference_event().compile())
        node = event.find(ShowText)[0]
        added = event.append(ShowText('新增'))
        event.insert_before(node, SetSwitch(10))
        event.replace(added, CommonEvent(100))
        self.assertEqual(event.compile()[-2], events.command(117,0,[100]))
        event.remove(event.find(CommonEvent)[0])
        self.assertEqual(event.compile()[0], events.command(121,0,[10,10,0]))
        event.to_document()
        event.to_plan({'kind':'common','id':1})
        node.lines = ['a'] * 5
        with self.assertRaises(ValueError):event.compile()

    def test_decoded_plan_applies_through_shared_backend_on_copy(self):
        from unittest.mock import patch
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory).resolve(); (project / 'data').mkdir()
            raw = reference_event().compile()
            document = [None, {'id':1,'list':raw,'name':'测试'}]
            source = ('[\nnull,\n'+json.dumps(document[1],ensure_ascii=False,separators=(',',':'))+'\n]').encode()
            target = project/'data/CommonEvents.json'; target.write_bytes(source)
            event = EventList.from_commands(raw)
            event.find(ShowText)[1].lines = ['已修改']
            plan = event.to_plan({'kind':'common','id':1})
            with patch.object(events, 'source_profile', return_value={'profile_matches':True}):
                root,before,after,preview = events.prepare(project,plan)
            self.assertEqual(json.loads(after['CommonEvents.json'])[1]['list'],event.compile())
            expected=source.replace('"parameters":["3"]'.encode(),'"parameters":["已修改"]'.encode())
            self.assertEqual(after['CommonEvents.json'],expected)
            events.db.commit(root,before,after)
            self.assertEqual(target.read_bytes(),expected)


class FullDecoderTests(unittest.TestCase):
    def test_reference_tree_and_nested_edits(self):
        raw = reference_event().compile()
        event = EventList.from_commands(raw)
        self.assertEqual(event.compile(),raw)
        self.assertEqual(len(event.find(If)),2)
        self.assertEqual(len(event.find(Loop)),1)
        self.assertEqual(len(event.find(BreakLoop)),1)
        self.assertEqual(len(event.find(SetSwitch)),2)
        self.assertEqual(len(event.find(ChangeVariable)),1)
        event.find(ChangeVariable)[0].value = Constant(2)
        event.find(If)[1].otherwise = [CommonEvent(100)]
        changed = event.compile()
        self.assertIn(events.command(117,3,[100]),changed)
        self.assertIn(events.command(122,2,[1,1,1,0,2]),changed)
        self.assertEqual(EventList.from_commands(changed).compile(),changed)
        loop=event.find(Loop)[0]
        event.remove(loop)
        self.assertEqual(event.find(BreakLoop),[])
        event.append(BreakLoop())
        with self.assertRaises(ValueError):event.compile()

    def test_all_operands_and_conditions_roundtrip(self):
        values=[Constant(-1),VariableValue(2),RandomValue(-2,4),ScriptValue('1+2')]
        conditions=[Switch(1).is_off(),Variable(1).equal_to(VariableValue(2)),ScriptCondition('false'),Actor(1).in_party(),Actor(1).name_equals('1')]
        event=EventList([ChangeVariable(1,operation,value,end=3) for operation in events.OPERATIONS for value in values])
        event.extend([If(cond,[CommonEvent(100)],[]) for cond in conditions])
        decoded=EventList.from_commands(event.compile())
        self.assertEqual(decoded.compile(),event.compile())
        self.assertEqual(len(decoded.find(ChangeVariable)),24)
        self.assertEqual(len(decoded.find(If)),5)
        self.assertEqual(len(decoded.find(CommonEvent)),5)
        self.assertEqual(len(decoded.find(OpaqueCommand)),0)

    def test_unknown_condition_preserves_block_and_rebases(self):
        raw=[events.command(111,0,[3,60,0]),events.command(117,1,[100]),events.command(0,1),events.command(412,0),events.command(0,0)]
        decoded=EventList.from_commands(raw)
        self.assertEqual(decoded.compile(),raw)
        self.assertIsInstance(decoded[0],OpaqueCommand)
        nested=EventList([Loop([decoded[0],BreakLoop()])]).compile()
        self.assertEqual(nested[1],events.command(111,1,[3,60,0]))
        self.assertEqual(nested[2],events.command(117,2,[100]))

    def test_actor_party_expected_structure(self):
        event=EventList([If(Actor(1).in_party(),then=[SetSwitch(1,on=True),CommonEvent(100)])])
        expected=[events.command(111,0,[4,1,0]),events.command(121,1,[1,1,0]),events.command(117,1,[100]),events.command(0,1),events.command(412,0),events.command(0,0)]
        self.assertEqual(event.compile(),expected)
        self.assertEqual(EventList.from_commands(expected).compile(),expected)
        with self.assertRaises(ValueError):EventList([If(Actor(1).name_equals(1))]).compile()


class AdditionalConditionTests(unittest.TestCase):
    def test_compile_decode_and_edit(self):
        cases = [(Character(-1).facing('down'),[6,-1,2]),
                 (Character(0).facing('left'),[6,0,4]),
                 (Character(3).facing('right'),[6,3,6]),
                 (Character(1).facing('up'),[6,1,8]),
                 (Button('ok').is_pressed(),[11,'ok',0]),
                 (Button('cancel').is_triggered(),[11,'cancel',1]),
                 (Button('shift').is_repeated(),[11,'shift',2]),
                 (Item(1).is_owned(),[8,1]),
                 (SelfSwitch('A').is_on(),[2,'A',0]),
                 (SelfSwitch('D').is_off(),[2,'D',1])]
        for condition,params in cases:
            with self.subTest(params=params):
                raw=EventList([If(condition,[SetSwitch(1)],[])]).compile()
                self.assertEqual(raw[0]['parameters'],params)
                decoded=EventList.from_commands(raw)
                self.assertIsInstance(decoded[0],If)
                self.assertEqual(decoded.compile(),raw)
                decoded[0].then.append(CommonEvent(100))
                self.assertIn(events.command(117,1,[100]),decoded.compile())

    def test_invalid_parameters_and_unknown_variants(self):
        cases=[Character(-2).facing('up'),Character(True).facing('up'),Character(1).facing('north'),
               Button('Enter').is_pressed(),Item(0).is_owned(),SelfSwitch('E').is_on()]
        for condition in cases:
            with self.subTest(condition=condition),self.assertRaises(ValueError):
                EventList([If(condition)]).compile()
        for params in ([11,'ok'],[11,'plugin_button',0],[6,1,3],[2,'A',True]):
            raw=[events.command(111,0,params),events.command(0,1),events.command(412,0),events.command(0,0)]
            decoded=EventList.from_commands(raw)
            self.assertIsInstance(decoded[0],OpaqueCommand)
            self.assertEqual(decoded.compile(),raw)


class SelfSwitchTimerTests(unittest.TestCase):
    def test_compile_and_decode(self):
        event=EventList([SetSelfSwitch('A'),SetSelfSwitch('D',False),StartTimer(60),StopTimer()])
        expected=[events.command(123,0,['A',0]),events.command(123,0,['D',1]),
                  events.command(124,0,[0,60]),events.command(124,0,[1]),events.command(0,0)]
        self.assertEqual(event.compile(),expected)
        decoded=EventList.from_commands(expected)
        self.assertEqual(len(decoded.find(SetSelfSwitch)),2)
        self.assertEqual(len(decoded.find(StartTimer)),1)
        self.assertEqual(len(decoded.find(StopTimer)),1)
        decoded.find(StartTimer)[0].seconds=25
        expected[2]['parameters']=[0,25]
        self.assertEqual(decoded.compile(),expected)

    def test_nested_and_invalid_parameters(self):
        event=EventList([If(Switch(1).is_on(),[StartTimer(0),SetSelfSwitch('B')],[StopTimer()])])
        self.assertEqual(EventList.from_commands(event.compile()).compile(),event.compile())
        for node in [StartTimer(-1),StartTimer(1.5),StartTimer(True),SetSelfSwitch('E'),SetSelfSwitch('a'),SetSelfSwitch('A',1)]:
            with self.subTest(node=node),self.assertRaises(ValueError):EventList([node]).compile()
        for code,params in [(123,['A',True]),(123,['A',0,'extra']),(124,[1,30]),(124,[2]),(124,[0,-1])]:
            raw=[events.command(code,0,params),events.command(0,0)]
            decoded=EventList.from_commands(raw)
            self.assertIsInstance(decoded[0],OpaqueCommand)
            self.assertEqual(decoded.compile(),raw)


class MoreCommandTests(unittest.TestCase):
    def test_expected_parameters_and_roundtrip(self):
        cases=[(Comment('a\nb'),[(108,['a']),(408,['b'])]),
               (Script('let x=1;\nx++;'),[(355,['let x=1;']),(655,['x++;'])]),
               (ChangeGold(Constant(10)),[(125,[0,0,10])]),
               (ChangeGold(VariableValue(2),'sub'),[(125,[1,1,2])]),
               (ChangeItems(3,Constant(2),'sub'),[(126,[3,1,0,2])]),
               (ChangeItems(3,VariableValue(2)),[(126,[3,0,1,2])]),
               (TransferPlayer(1,0,2),[(201,[0,1,0,2,0,0])]),
               (TransferPlayer(VariableValue(1),VariableValue(2),VariableValue(3),'up','none'),[(201,[1,1,2,3,8,2])]),
               (Wait(60),[(230,[60])]),(EraseEvent(),[(214,[])])]
        for node,rows in cases:
            with self.subTest(node=node):
                raw=EventList([node]).compile()
                self.assertEqual(raw,[events.command(code,0,p) for code,p in rows]+[events.command(0,0)])
                decoded=EventList.from_commands(raw)
                self.assertIsInstance(decoded[0],type(node))
                self.assertEqual(decoded.compile(),raw)
                nested=EventList([If(Switch(1).is_on(),[decoded[0]])]).compile()
                self.assertEqual(EventList.from_commands(nested).compile(),nested)

    def test_edit_and_multiline_edges(self):
        for cls in (Comment,Script):
            for text in ('','a\n','\n','a\r\nb'):
                event=EventList([cls(text)])
                raw=event.compile();decoded=EventList.from_commands(raw)
                self.assertEqual(decoded.compile(),raw)
                decoded[0].text='changed\nnext'
                self.assertEqual(len(decoded.compile()),3)
        event=EventList.from_commands(EventList([ChangeItems(1,Constant(1)),TransferPlayer(2,3,4),Wait(1)]).compile())
        event[0].value=VariableValue(5);event[1].fade='white';event[2].frames=120
        result=event.compile()
        self.assertEqual(result[0]['parameters'],[1,0,1,5])
        self.assertEqual(result[1]['parameters'][-1],1)
        self.assertEqual(result[2]['parameters'],[120])

    def test_invalid_and_extensions(self):
        invalid=[Wait(0),Wait(True),Wait(1.5),ChangeGold(Constant(-1)),ChangeGold(RandomValue(1,2)),
                 ChangeItems(0,Constant(1)),TransferPlayer(0,1,1),TransferPlayer(1,-1,1),
                 TransferPlayer(1,VariableValue(2),3),TransferPlayer(1,1,1,fade='bad'),Script(1)]
        for node in invalid:
            with self.subTest(node=node),self.assertRaises(ValueError):EventList([node]).compile()
        for code,params in [(125,[0,0,1,'extra']),(126,[1,0,0,-1]),(201,[0,1,1,1,0,0,'extra']),(214,[1]),(230,[0]),(355,['x',1])]:
            raw=[events.command(code,0,params),events.command(0,0)]
            event=EventList.from_commands(raw)
            self.assertIsInstance(event[0],OpaqueCommand)
            self.assertEqual(event.compile(),raw)
