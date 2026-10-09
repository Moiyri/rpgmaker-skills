import json
from pathlib import Path
import sys
import tempfile
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'skills/rpgmaker-plugins/scripts'))
from plugin_api import Plugins

DECL='''/*:
 * @param Config
 * @text 配置
 * @type struct<Config>
 */
/*~struct~Config:
 * @param Rows
 * @type struct<Row>[]
 * @param Title
 * @type string
 */
/*~struct~Row:
 * @param Enabled
 * @type boolean
 * @param Count
 * @type number
 * @min 1
 * @max 9
 * @param Mode
 * @type select
 * @option 普通
 * @value normal
 * @option 困难
 * @value hard
 * @param Script
 * @type note
 * @param Names
 * @type string[]
 */'''
class ParameterPathTests(unittest.TestCase):
    def setUp(self):
        self.t=tempfile.TemporaryDirectory();self.addCleanup(self.t.cleanup);self.root=Path(self.t.name)
        (self.root/'js/plugins').mkdir(parents=True);self.src=self.root/'js/plugins/Test.js';self.src.write_text(DECL)
        self.row=json.dumps({'Enabled':'false','Count':'3','Mode':'normal','Names':json.dumps(['甲','乙']),'Script':json.dumps('old\nscript'),'unknown':' { "keep" : 1 } '})
        self.config=json.dumps({'Rows':json.dumps([self.row,self.row]),'Title':'old','unknown':'\n untouched'})
        self.file=self.root/'js/plugins.js';self.file.write_text('var $plugins = '+json.dumps([{'name':'Test','status':True,'description':'','parameters':{'Config':self.config,'other':'literal'}}])+';')
        self.api=Plugins(self.root)
    def test_nested_updates_and_help(self):
        before=self.file.read_bytes()
        self.assertIn("['Config', 'Rows', 0, 'Enabled']",self.api.parameter_help('Test',['Config','Rows',0]))
        self.assertIn('normal=普通',self.api.parameter_help('Test',['Config','Rows',0,'Mode']))
        self.api.set_parameter('Test',['Config','Rows',0,'Enabled'],True)
        self.api.set_parameter('Test',['Config','Rows',0,'Count'],8)
        self.api.set_parameter('Test',['Config','Rows',0,'Names',1],'新的值')
        self.api.set_parameter('Test',['Config','Title'],'new')
        p=self.api.preview();self.assertEqual(before,self.file.read_bytes());self.api.commit(p)
        params=self.api.get('Test')['parameters'];config=json.loads(params['Config']);rows=json.loads(config['Rows']);row=json.loads(rows[0])
        self.assertEqual(row['Enabled'],'true');self.assertEqual(row['Count'],'8');self.assertEqual(json.loads(row['Names']),['甲','新的值'])
        self.assertEqual(rows[1],self.row);self.assertEqual(row['unknown'],' { "keep" : 1 } ');self.assertEqual(params['other'],'literal')
        self.assertEqual(config['Title'],'new')
    def test_reject_invalid_paths_and_types(self):
        for path,value in [(['Config','Rows',9,'Count'],2),(['Config','Rows',0,'Enabled'],'true'),(['Config','Rows',0,'Count'],10),(['Config','Rows',0,'Mode'],'invented'),(['Config','unknown'],'change')]:
            with self.assertRaises(ValueError):self.api.set_parameter('Test',path,value)
        self.assertEqual(self.api.operations,[])
    def test_note_encoding(self):
        self.api.set_parameter('Test',['Config','Rows',0,'Script'],'return "中文";\n')
        self.api.commit(self.api.preview())
        rows=json.loads(json.loads(self.api.get('Test')['parameters']['Config'])['Rows'])
        self.assertEqual(json.loads(json.loads(rows[0])['Script']),'return "中文";\n')
    def test_source_conflicts(self):
        self.api.set_parameter('Test',['Config','Title'],'new');self.src.write_text(DECL+'\n')
        with self.assertRaises(ValueError):self.api.preview()
    def test_manifest_conflict_before_preview(self):
        self.api.set_parameter('Test',['Config','Title'],'new');self.file.write_text(self.file.read_text()+'\n')
        with self.assertRaises(ValueError):self.api.preview()
    def test_array_replace_and_empty(self):
        self.api.set_parameter('Test',['Config','Rows',0,'Names'],['x','y'])
        self.api.set_parameter('Test',['Config','Rows'],[])
        self.api.commit(self.api.preview())
        self.assertEqual(json.loads(json.loads(self.api.get('Test')['parameters']['Config'])['Rows']),[])
