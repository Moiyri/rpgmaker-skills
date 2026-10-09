import sys,json,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parent))
import test_maps_api as fixture
from database_api import Database
from database_core.backend import db

class LifecycleTests(unittest.TestCase):
    setUp=fixture.MapAPITests.setUp
    def test_gap_create_restore(self):
        before=(self.data/'MapInfos.json').read_bytes()
        m=self.db.maps.create('New',width=3,height=2)
        self.assertEqual(m.id,2);p=self.db.preview();tx=self.db.commit(p)
        raw=(self.data/'Map002.json').read_bytes();value=json.loads(raw)
        self.assertEqual(value['events'],[]);self.assertEqual(value['data'],[0]*36)
        self.assertTrue(raw.endswith(b'"events":[\n]\n}'))
        root=self.data.resolve();originals,updated=db.prepare_restore(root,Path(tx))
        db.commit(root,originals,updated)
        self.assertFalse((self.data/'Map002.json').exists());self.assertEqual((self.data/'MapInfos.json').read_bytes(),before)
    def test_occupied_and_commit_race(self):
        (self.data/'Map002.json').write_text('{}')
        self.assertEqual(self.db.maps.create('New').id,4)
        with self.assertRaises(ValueError):self.db.maps.create(id=2)
        p=self.db.preview();(self.data/'Map004.json').write_text('{"occupied":true}')
        with self.assertRaises(ValueError):self.db.commit(p)
        self.assertEqual((self.data/'Map004.json').read_text(),'{"occupied":true}')
    def test_delete_and_restore(self):
        with self.assertRaises(ValueError):self.db.maps.delete(1)
        self.db.maps.delete(3);tx=self.db.commit(self.db.preview())
        self.assertFalse((self.data/'Map003.json').exists())
        self.assertIsNone(json.loads((self.data/'MapInfos.json').read_bytes())[3])
        root=self.data.resolve();a,b=db.prepare_restore(root,Path(tx));db.commit(root,a,b)
        self.assertEqual((self.data/'Map003.json').read_bytes(),self.raw)
    def test_resize_layers(self):
        data=json.loads(self.raw);data['width']=3;data['height']=2;data['data']=list(range(36))
        (self.data/'Map001.json').write_text(json.dumps(data))
        m=self.db.maps.get(1);m.resize(4,3)
        self.assertEqual(m._data['data'][:12],[0,1,2,0,3,4,5,0,0,0,0,0])
        self.assertEqual(m._data['data'][12:16],[6,7,8,0])
        m.resize(2,1);self.db.commit(self.db.preview())
        self.assertEqual(json.loads((self.data/'Map001.json').read_bytes())['data'],[0,1,6,7,12,13,18,19,24,25,30,31])
    def test_references_block(self):
        (self.data/'System.json').write_text('{"startMapId":3,"startX":16,"startY":12}')
        self.db.maps.get(3).resize(3,3)
        with self.assertRaises(ValueError):self.db.preview()
        d=Database(self.root);d.maps.delete(3)
        with self.assertRaises(ValueError):d.preview()
    def test_creation_link_race_rolls_back(self):
        m=self.db.maps.create('New');p=self.db.preview();before=(self.data/'MapInfos.json').read_bytes()
        def occupied(source,target):
            Path(target).write_text('external')
            raise FileExistsError('collision')
        with patch.object(db.os,'link',side_effect=occupied):
            with self.assertRaises(ValueError):self.db.commit(p)
        self.assertEqual((self.data/'MapInfos.json').read_bytes(),before)
        self.assertEqual((self.data/'Map002.json').read_text(),'external')
