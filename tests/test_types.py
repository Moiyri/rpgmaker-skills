import json
import tempfile
import unittest
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'skills/rpgmaker-database/scripts'))
from database_api import Database
from database_core.system import TYPES

class TypesTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name);self.data=self.root/'data';self.data.mkdir()
        (self.data/'Items.json').write_text('[null]')
        value={key:['','Magic','','Magic'] for _,key in TYPES.values()}
        value['extension']={'keep':1}
        self.raw=('\ufeff'+json.dumps(value,indent=2)+'\r\n').encode()
        (self.data/'System.json').write_bytes(self.raw)
        self.db=Database(self.root)
    def test_lists(self):
        self.assertFalse(hasattr(self.db,'lookup'))
        for name in TYPES:
            types=getattr(self.db.types,name)
            self.assertEqual(types.get(1),'Magic')
            self.assertEqual(types.find('magic'),[(1,'Magic'),(3,'Magic')])
            self.assertIn('2 （未命名）',types.list())
            self.assertIn('3 Magic',types.list(search='magic',offset=1,limit=1))
        self.assertIsNone(self.db.commit(self.db.preview()))
        self.assertEqual((self.data/'System.json').read_bytes(),self.raw)
    def test_edit_all(self):
        for name in TYPES:
            types=getattr(self.db.types,name)
            types.set(1,'New');self.assertEqual(types.add('Extra'),4);types.clear(3)
        preview=self.db.preview()
        self.assertEqual((self.data/'System.json').read_bytes(),self.raw)
        self.db.commit(preview)
        saved=Database(self.root)
        for name in TYPES:self.assertEqual(getattr(saved.types,name).get(4),'Extra')
        raw=(self.data/'System.json').read_bytes()
        self.assertTrue(raw.startswith(b'\xef\xbb\xbf'));self.assertTrue(raw.endswith(b'\r\n'))
        self.assertEqual(json.loads(raw.decode('utf-8-sig'))['extension'],{'keep':1})
    def test_invalid_conflicts(self):
        t=self.db.types.elements
        for id in [0,-1,4,True]:
            with self.assertRaises(ValueError):t.set(id,'X')
        with self.assertRaises(ValueError):t.add(None)
        t.set(1,'A');p=self.db.preview();t.set(1,'B')
        with self.assertRaises(ValueError):self.db.commit(p)
        (self.data/'System.json').write_bytes(self.raw+b' ')
        with self.assertRaises(ValueError):self.db.preview()
