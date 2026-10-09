import json
import sys
import tempfile
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'skills/rpgmaker-database/scripts'))
from database_api import Database
from database_core.actors import blank_actor


class ActorTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name);self.data=self.root/'data';self.data.mkdir()
        (self.data/'Items.json').write_text('[null]')
        (self.data/'Classes.json').write_text('[null,{"id":1}]')
        actor=blank_actor(1);actor['name']='Hero';actor['extension']={'v':1}
        self.raw=json.dumps([None,actor,blank_actor(2)])+'\r\n'
        (self.data/'Actors.json').write_bytes(self.raw.encode())
        self.db=Database(self.root)
    def test_edit_create_clear(self):
        a=self.db.actors.get(1);self.assertIn('Hero',self.db.actors.list())
        self.assertIs(self.db.actors.find('hero')[0],a)
        a.nickname='勇者';a.initial_level=5;a.character_name='Actor1';a.equip(0,0)
        a.traits.add('state_resist',id=1)
        new=self.db.actors.create('Mage');self.assertEqual(new.id,3)
        self.db.actors.clear(2);self.db.actors.create('Guard',id=2)
        preview=self.db.preview();self.assertEqual((self.data/'Actors.json').read_bytes(),self.raw.encode())
        self.db.commit(preview)
        saved=Database(self.root);self.assertEqual(saved.actors.get(1).nickname,'勇者')
        self.assertEqual(saved.actors.get(1).get(['extension','v']),1)
        self.assertEqual(saved.actors.get(1).traits.get(0)['code'],14)
        self.assertEqual(saved.actors.get(3).name,'Mage')
        self.assertTrue((self.data/'Actors.json').read_bytes().endswith(b'\r\n'))
    def test_invalid_and_conflict(self):
        with self.assertRaises(ValueError):self.db.actors.create('Overwrite',id=1)
        a=self.db.actors.get(1)
        with self.assertRaises(ValueError):a.face_index=8
        a.initial_level=50;a.max_level=20
        with self.assertRaises(ValueError):self.db.preview()
        a.max_level=99;p=self.db.preview();a.name='Other'
        with self.assertRaises(ValueError):self.db.commit(p)
    def test_references(self):
        (self.data/'System.json').write_text('{"partyMembers":[1]}')
        (self.data/'CommonEvents.json').write_text(json.dumps([None,{'list':[{'code':129,'parameters':[1,0,False]},{'code':311,'parameters':[1,1,0,0,10,False]}]}]))
        report=self.db.actors.references(1)
        self.assertEqual(len(report),2)
    def test_noop(self):
        self.db.actors.list();self.assertIsNone(self.db.commit(self.db.preview()))
        self.assertEqual((self.data/'Actors.json').read_bytes(),self.raw.encode())
