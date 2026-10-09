import json
import sys
import tempfile
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'skills/rpgmaker-database/scripts'))
from database_api import Database

class SwitchVariableTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);(self.root/'data').mkdir()
        (self.root/'data/Items.json').write_text('[null]')
        self.path=self.root/'data/System.json'
        self.raw=('\ufeff'+json.dumps(dict(switches=['','Door','','Door'],variables=['','Count',''],gameTitle='Old',extension={'keep':1}),indent=2)+'\r\n').encode()
        self.path.write_bytes(self.raw);self.db=Database(self.root)
    def test_list_find_noop(self):
        self.assertEqual(self.db.switches.find('door'),[(1,'Door'),(3,'Door')])
        self.assertIn('2 （未命名）',self.db.switches.list())
        self.assertIn('3 Door',self.db.switches.list(search='door',offset=1,limit=1))
        self.assertEqual(self.db.variables.get(1),'Count')
        self.assertFalse(hasattr(self.db.switches,'add'))
        self.assertFalse(hasattr(self.db.variables,'add'))
        self.assertIsNone(self.db.commit(self.db.preview()))
        self.assertEqual(self.path.read_bytes(),self.raw)
    def test_changes_shared_commit(self):
        self.db.switches.set(1,'门已打开');self.db.switches.clear(3)
        self.db.switches.set(2,'测试')
        self.db.variables.set(1,'钟编号')
        self.db.variables.clear(2);self.db.system.game_title='New'
        p=self.db.preview();self.assertEqual(self.path.read_bytes(),self.raw)
        self.db.commit(p);new=Database(self.root)
        self.assertEqual(new.switches.get(2),'测试');self.assertEqual(new.switches.get(3),'')
        self.assertEqual(new.variables.get(1),'钟编号');self.assertEqual(new.system.game_title,'New')
        data=json.loads(self.path.read_bytes().decode('utf-8-sig'))
        self.assertEqual(data['extension'],{'keep':1});self.assertEqual(data['switches'][0],'')
        self.assertTrue(self.path.read_bytes().endswith(b'\r\n'))
    def test_invalid_and_conflict(self):
        for call in [lambda:self.db.switches.set(0,'x'),lambda:self.db.variables.set(99,'x'),lambda:self.db.switches.set(True,'x'),lambda:self.db.variables.set(1,3)]:
            with self.assertRaises(ValueError):call()
        self.db.switches.set(1,'New');p=self.db.preview();self.db.variables.set(1,'Other')
        with self.assertRaises(ValueError):self.db.commit(p)
        self.path.write_bytes(self.raw+b' ')
        with self.assertRaises(ValueError):self.db.preview()
