import copy
import json
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'skills/rpgmaker-events/scripts'))
from event_api import EventList, PluginCommand, If, Switch, OpaqueCommand


class PluginCommandTests(unittest.TestCase):
    def fixture(self):
        return json.loads((Path(__file__).parent / 'fixtures/events/plugin-command.json').read_text()) + [{'code': 0, 'indent': 0, 'parameters': []}]

    def test_editor_fixture_roundtrip_and_edit(self):
        raw = self.fixture()
        event = EventList.from_commands(raw)
        node = event.find(PluginCommand)[0]
        self.assertEqual(event.compile(), raw)
        node.args['EventId'] = '2'
        result = event.compile()
        self.assertEqual(result[0]['parameters'][3]['EventId'], '2')
        self.assertEqual(result[1]['parameters'], ['Center Event ID = 2'])
        self.assertEqual(result[4]['parameters'], ['Scale = 2.00'])

    def test_new_nested_encoded_arguments(self):
        args = {'data': '["{\\"id\\":\\"1\\"}"]', 'flag': 'false', 'empty': '', 'zero': '0'}
        node = PluginCommand('folder/Test', 'run', args, '运行', {'data': '数据'})
        event = EventList([If(Switch(1).is_on(), [node])])
        raw = event.compile()
        self.assertEqual(raw[1], {'code':357, 'indent':1, 'parameters':['folder/Test','run','运行',args]})
        self.assertEqual(raw[2]['parameters'], ['数据 = ' + args['data']])
        self.assertEqual(EventList.from_commands(raw).compile(), raw)

    def test_no_arguments(self):
        raw = EventList([PluginCommand('Test', 'run', {})]).compile()
        self.assertEqual([c['code'] for c in raw], [357, 0])
        self.assertEqual(raw[0]['parameters'], ['Test', 'run', 'run', {}])

    def test_invalid_inputs(self):
        nodes = [PluginCommand('', 'run', {}), PluginCommand('Test', '', {}),
                 PluginCommand('Test', 'run', {'x': 1}), PluginCommand('Test', 'run', {'x': False}),
                 PluginCommand('Test', 'run', {'x': {} }), PluginCommand('Test', 'run', {1:'x'}),
                 PluginCommand('Test', 'run', {}, argument_labels={'unknown':'未知'})]
        for node in nodes:
            with self.subTest(node=node), self.assertRaises(ValueError):
                EventList([node]).compile()

    def test_nonstandard_annotations_preserved_until_explicit_labels(self):
        raw = self.fixture()
        raw[1]['parameters'] = ['编辑器特殊显示']
        event = EventList.from_commands(raw)
        node = event.find(PluginCommand)[0]
        self.assertEqual(event.compile(), raw)
        node.args['EventId'] = '3'
        with self.assertRaises(ValueError):
            event.compile()
        node.argument_labels = {k:k for k in node.args}
        self.assertEqual(event.compile()[1]['parameters'], ['EventId = 3'])

    def test_extensions_preserved_as_opaque(self):
        for mutate in (lambda r:r[0].update(extra=True), lambda r:r[0]['parameters'].append('extra')):
            raw = self.fixture()
            mutate(raw)
            event = EventList.from_commands(raw)
            self.assertTrue(event.find(OpaqueCommand))
            self.assertEqual(event.compile(), raw)
