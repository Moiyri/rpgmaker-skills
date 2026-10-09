import json
from pathlib import Path
import sys
import tempfile
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'skills/rpgmaker-plugin/scripts'))
from plugin import check_plugin,list_plugins,plugin_parameters,plugin_help
class PluginQueryTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)
  folder=self.root/'js/plugins/a';folder.mkdir(parents=True)
  (folder/'Test.js').write_text('/*:\n * @command Run\n * @arg x\n * @default 1\n */')
  (folder/'Unused.js').write_text('')
  self.rows=[{'name':n,'status':s,'description':'','parameters':{'x':'1'}} for n,s in [('a/Test',True),('Missing',False)]]
  self.save()
 def save(self): (self.root/'js/plugins.js').write_text('var $plugins = '+json.dumps(self.rows)+';')
 def test_status_list_help_params(self):
  self.assertIn('已启用',check_plugin(self.root,'Test'))
  self.assertIn('文件缺失',check_plugin(self.root,'Missing'))
  self.assertIn('未注册',check_plugin(self.root,'Unused'))
  self.assertIn('未安装',check_plugin(self.root,'Absent'))
  self.assertIn('未注册',list_plugins(self.root))
  self.assertNotIn('Unused',list_plugins(self.root,enabled_only=True))
  self.assertIn('x = 1',plugin_parameters(self.root,'Test',parameter='x'))
  self.assertIn('Run',plugin_help(self.root,'Test'))
  self.rows[0]['status']=False;self.save();self.assertIn('已禁用',check_plugin(self.root,'Test'))
 def test_ambiguity_and_invalid_config(self):
  (self.root/'js/plugins/Test.js').write_text('')
  with self.assertRaises(ValueError):check_plugin(self.root,'Test')
  self.assertIn('已启用',check_plugin(self.root,'a/Test'))
  with self.assertRaises(ValueError):check_plugin(self.root,'../Test')
  self.rows.append(self.rows[0]);self.save()
  with self.assertRaises(ValueError):check_plugin(self.root,'a/Test')
  (self.root/'js/plugins.js').write_text('var $plugins = execute();')
  with self.assertRaises(ValueError):list_plugins(self.root)
