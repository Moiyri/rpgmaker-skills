import json
import sys
import tempfile
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'skills/rpgmaker-database/scripts'))
from database_api import Database

class MapAPITests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);self.data=self.root/'data';self.data.mkdir()
        (self.data/'Items.json').write_text('[null]')
        (self.data/'MapInfos.json').write_text(json.dumps([None,dict(id=1,name='Town',parentId=0,order=1),None,dict(id=3,name='House',parentId=1,order=2)]))
        (self.data/'Tilesets.json').write_text('[null,{"id":1},{"id":2}]')
        audio=dict(name='',volume=90,pitch=100,pan=0)
        self.map=dict(width=17,height=13,displayName='',tilesetId=1,scrollType=0,autoplayBgm=False,autoplayBgs=False,bgm=audio,bgs=audio,disableDashing=False,specifyBattleback=False,battleback1Name='',battleback2Name='',parallaxName='',parallaxLoopX=False,parallaxLoopY=False,parallaxSx=0,parallaxSy=0,parallaxShow=True,encounterStep=30,encounterList=[],note='',events=[None],data=[0]*1326,extension={'keep':1})
        self.raw=(json.dumps(self.map)+'\r\n').encode()
        for id in [1,3]:(self.data/f'Map{id:03d}.json').write_bytes(self.raw)
        self.db=Database(self.root)
    def test_edit_preservation(self):
        m=self.db.maps.get(3);m.name='Room';m.display_name='房间';m.parent_id=0;m.tileset_id=2
        m.scroll_type='both';m.autoplay_bgm=True;m.bgm.name='Theme';m.bgm.volume=80
        m.parallax_name='Sky';m.parallax_loop_x=True;m.parallax_sx=-2;m.note='<test>'
        p=self.db.preview();self.assertEqual((self.data/'Map003.json').read_bytes(),self.raw)
        self.db.commit(p);new=Database(self.root).maps.get(3)
        self.assertEqual(new.name,'Room');self.assertEqual(new.parent_id,0);self.assertEqual(new.bgm.volume,80)
        saved=json.loads((self.data/'Map003.json').read_bytes())
        for k in ['data','events','extension','encounterList']:self.assertEqual(saved[k],self.map[k])
        self.assertEqual((self.data/'Map001.json').read_bytes(),self.raw)
    def test_list_noop(self):
        self.assertIn('17×13',self.db.maps.list());self.assertEqual(self.db.maps.find('HOUSE')[0].id,3)
        self.assertIsNone(self.db.commit(self.db.preview()))
    def test_validation_conflict(self):
        with self.assertRaises(ValueError):self.db.maps.get(1).parent_id=3
        with self.assertRaises(ValueError):self.db.maps.get(2)
        m=self.db.maps.get(3);m.tileset_id=99
        with self.assertRaises(ValueError):self.db.preview()
        m.tileset_id=1;m.display_name='X';p=self.db.preview();m.name='Y'
        with self.assertRaises(ValueError):self.db.commit(p)
        (self.data/'Map003.json').write_bytes(self.raw+b' ')
        with self.assertRaises(ValueError):self.db.preview()
