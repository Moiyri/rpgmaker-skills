from pathlib import Path
import sys
import tempfile
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'skills/rpgmaker-events/scripts'))
from event_core.plugin_help import _plugin_metadata as plugin_help
from event_api import plugin_help as text_help
import events

SOURCE = '''/*:
 * @plugindesc Test
 * @param setting
 * @type struct<Data>[]
 * @default []
 * @command run
 * @text Run
 * @arg mode
 * @type select
 * @option First
 * @value 0
 * @option Second
 * @value 1
 * @default 0
 * @desc Choose mode.
 * More description.
 * @arg empty
 * @default
 * @help Usage line one.
 * Usage line two.
 */
/*~struct~Data:
 * @param child
 * @type struct<Child>
 */
/*~struct~Child:
 * @param value
 * @type boolean
 * @default false
 */
throw new Error('must never execute');
'''

class PluginHelpTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.project = Path(self.tmp.name)
        self.root = self.project / 'js/plugins'
        (self.root / 'folder').mkdir(parents=True)
        (self.root / 'folder/Test.js').write_text(SOURCE)

    def test_fields_structs_options_help_and_cli(self):
        result = plugin_help(self.project, 'Test')
        self.assertEqual(result['plugin'], 'folder/Test')
        self.assertEqual(result['parameters'][0]['default'], '[]')
        args = result['commands'][0]['arguments']
        self.assertEqual(args[0]['options'], [{'text':'First','value':'0'}, {'text':'Second','value':'1'}])
        self.assertEqual(args[0]['desc'], 'Choose mode.\nMore description.')
        self.assertEqual(args[1]['default'], '')
        self.assertEqual(result['structs']['Child'][0]['default'], 'false')
        self.assertEqual(result['help'], 'Usage line one.\nUsage line two.')
        self.assertEqual(result['warnings'], [])
        self.assertEqual(events.run(['--project',str(self.project),'plugin-help','--plugin','folder/Test.js']), text_help(self.project, 'Test'))

    def test_localization_and_fallback(self):
        with (self.root/'folder/Test.js').open('a') as f:
            f.write('/*:zh\n * @command run\n * @text 运行\n * @help 中文帮助\n */')
        result = plugin_help(self.project, 'Test', language='zh-CN')
        self.assertEqual(result['commands'][0]['text'], '运行')
        self.assertEqual(result['languages']['plugin'], 'zh')
        self.assertIn('Child', result['structs'])
        self.assertEqual(plugin_help(self.project, 'Test', language='fr')['commands'][0]['text'], 'Run')

    def test_ambiguous_and_unsafe_paths(self):
        (self.root/'Test.js').write_text(SOURCE)
        for name in ('Test', '../Test', '/tmp/Test', 'missing'):
            with self.subTest(name=name), self.assertRaises(ValueError):
                plugin_help(self.project, name)
        self.assertEqual(plugin_help(self.project, 'folder/Test')['plugin'], 'folder/Test')
        outside = self.project/'Outside.js'
        outside.write_text(SOURCE)
        (self.root/'Escape.js').symlink_to(outside)
        with self.assertRaises(ValueError):
            plugin_help(self.project, 'Escape')

    def test_missing_metadata_and_duplicate_warning(self):
        path = self.root/'folder/Test.js'
        path.write_text('throw new Error("do not execute")')
        self.assertTrue(plugin_help(self.project, 'Test')['warnings'])
        path.write_text('/*:\n * @param x\n * @type struct<Missing>\n * @param x\n */')
        result = plugin_help(self.project, 'Test')
        self.assertEqual(len(result['parameters']), 2)
        self.assertEqual(len(result['warnings']), 2)

    def test_visumz_annotation_separator_does_not_pollute_defaults(self):
        (self.root/'folder/Test.js').write_text('/*:\n * @command Volume\n * @arg volume:eval\n * @default 100\n * @ --------------------------------------------------------------------------\n * @command Next\n * @desc Next command\n * @ --------------------------------------------------------------------------\n */')
        result = plugin_help(self.project, 'Test')
        self.assertEqual(result['commands'][0]['arguments'][0]['default'], '100')
        self.assertEqual(result['commands'][1]['desc'], 'Next command')

    def test_concise_text_and_detail(self):
        summary = text_help(self.project, 'Test')
        self.assertIsInstance(summary, str)
        self.assertIn("mode (select) = '0'", summary)
        self.assertNotIn('Usage line one.', summary)
        self.assertNotIn('metadata', summary)
        detail = text_help(self.project, 'Test', command='run')
        self.assertIn('Choose mode.', detail)
        self.assertIn('0 (First); 1 (Second)', detail)
        self.assertIn('struct<Data>[]', text_help(self.project, 'Test', section='parameters'))
        self.assertIn('struct<Child>', text_help(self.project, 'Test', struct='Data'))
        self.assertIn('Usage line two.', text_help(self.project, 'Test', section='help'))
        with self.assertRaises(ValueError):
            text_help(self.project, 'Test', command='missing')

    def test_long_defaults_only_abbreviated_in_summary(self):
        value = 'x' * 200
        (self.root/'folder/Test.js').write_text('/*:\n * @command Run\n * @arg x\n * @default ' + value + '\n */')
        self.assertNotIn(value, text_help(self.project, 'Test'))
        self.assertIn(value, text_help(self.project, 'Test', command='Run'))
