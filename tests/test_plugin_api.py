import json
from pathlib import Path
import sys
import tempfile
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'skills/rpgmaker-plugins/scripts'))
from plugin_api import Plugins
class PluginApiTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
        (self.root/'js/plugins').mkdir(parents=True)
        for n in ['A','B']:(self.root/f'js/plugins/{n}.js').write_text('')
        self.file=self.root/'js/plugins.js';self.file.write_text('var $plugins = [];')
    def test_add_update_move_remove(self):
        api=Plugins(self.root);api.add('A');api.add('B',enabled=True)
        preview=api.preview();self.assertEqual(self.file.read_text(),'var $plugins = [];');api.commit(preview)
        api.update('A',parameters={'nested':json.dumps({'x':'值'})},enabled=True);api.move('B',before='A');api.commit(api.preview())
        self.assertEqual([p['name'] for p in api.list()],['B','A'])
        self.assertEqual(json.loads(api.get('A')['parameters']['nested']),{'x':'值'})
        api.update('A',unset_parameters=['nested']);api.remove('B');api.commit(api.preview())
        self.assertEqual(api.get('A')['parameters'],{});self.assertTrue((self.root/'js/plugins/B.js').exists())
    def test_conflicts(self):
        api=Plugins(self.root);api.add('A');preview=api.preview();api.update('A',enabled=True)
        with self.assertRaises(ValueError):api.commit(preview)
        preview=api.preview();self.file.write_text('var $plugins = [];\n')
        with self.assertRaises(ValueError):api.commit(preview)
    def test_missing_file_and_invalid_parameters(self):
        api=Plugins(self.root)
        with self.assertRaises(ValueError):api.add('Missing')
        api.add('A',parameters={'x':1})
        with self.assertRaises(ValueError):api.preview()
