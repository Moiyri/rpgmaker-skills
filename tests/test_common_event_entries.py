import json
import sys
import tempfile
import unittest
from pathlib import Path
root=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(root/'skills/rpgmaker-database/scripts'),str(root/'skills/rpgmaker-events/scripts')]
from database_api import Database
from database_core.common_events import blank_event
from database_core.backend import db
from event_api import common_event_settings_plan

class CommonEventEntryTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.project=Path(self.tmp.name);self.data=self.project/'data';self.data.mkdir()
        (self.data/'Items.json').write_text('[null]')
        (self.data/'System.json').write_text('{"switches":["","Test"]}')
        value=blank_event(1);value['name']='Existing';value['list'].insert(0,dict(code=230,indent=0,parameters=[60]))
        self.values=[None,value,blank_event(2)]
        self.path=self.data/'CommonEvents.json';self.path.write_text(json.dumps(self.values)+'\n')
    def test_create_delete_handoff(self):
        d=Database(self.project)
        self.assertIn('Existing',d.common_events.list())
        entry=d.common_events.create(id=2);self.assertEqual(entry.id,2)
        with self.assertRaises(Exception):entry.name='No'
        created=d.common_events.create('New');self.assertEqual(created.id,3)
        d.common_events.delete(1)
        d.commit(d.preview())
        saved=json.loads(self.path.read_text());self.assertEqual(saved[1],blank_event(1));self.assertEqual(len(saved),4)
        plan=common_event_settings_plan(self.project,3,name='003:【功能】测试',trigger='parallel',switch_id=1)
        originals,updated,_=db.prepare(self.data.resolve(),plan);db.commit(self.data.resolve(),originals,updated)
        saved=json.loads(self.path.read_text());self.assertEqual(saved[3]['trigger'],2)
        self.assertEqual(saved[3]['list'],blank_event(3)['list'])
    def test_reject_overwrite_and_stale(self):
        d=Database(self.project)
        with self.assertRaises(ValueError):d.common_events.create('Overwrite',id=1)
        d.common_events.create('New');preview=d.preview()
        self.path.write_text(self.path.read_text()+' ')
        with self.assertRaises(ValueError):d.commit(preview)
        with self.assertRaises(ValueError):common_event_settings_plan(self.project,1,trigger='autorun',switch_id=99)
    def test_unnamed_content_and_noop(self):
        self.values[1]['name']='';self.path.write_text(json.dumps(self.values))
        d=Database(self.project)
        self.assertIn('001',d.common_events.list())
        self.assertNotIn('002',d.common_events.list())
        self.assertIsNone(d.commit(d.preview()))
