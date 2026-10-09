import json
import sys
import tempfile
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'skills/rpgmaker-database/scripts'))
from database_api import Database
from database_core.system_settings import OPTIONS,SOUNDS
from database_core.actors import blank_actor

class SystemSettingsTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name);self.data=self.root/'data';self.data.mkdir()
        audio=dict(name='Test',volume=90,pitch=100,pan=0,plugin=1)
        vehicle=dict(characterName='Vehicle',characterIndex=0,startMapId=0,startX=0,startY=0,bgm=audio)
        value=dict(gameTitle='Old',currencyUnit='G',optSideView=False,battleSystem=0,
            partyMembers=[1],title1Name='A',title2Name='B',optDrawTitle=True,
            titleCommandWindow=dict(offsetX=0,offsetY=0,background=0),windowTone=[0,0,0,0],
            startMapId=1,startX=0,startY=0,boat=vehicle,ship=vehicle,airship=vehicle,
            titleBgm=audio,battleBgm=audio,victoryMe=audio,defeatMe=audio,gameoverMe=audio,
            sounds=[audio for _ in SOUNDS],elements=['','Fire'],extension={'keep':1})
        value.update({key:False for key in OPTIONS.values()})
        self.raw=json.dumps(value,indent=2).encode()+b'\r\n'
        (self.data/'System.json').write_bytes(self.raw)
        (self.data/'Items.json').write_text('[null]')
        (self.data/'Actors.json').write_text(json.dumps([None,blank_actor(1),blank_actor(2)]))
        (self.data/'Classes.json').write_text('[null,{"id":1}]')
        (self.data/'Map001.json').write_text('{"width":10,"height":8}')
        self.db=Database(self.root)
    def test_edit_and_preserve(self):
        s=self.db.system;s.game_title='New';s.currency_unit='金币'
        s.starting_party.add(2);s.starting_party.remove(1)
        s.title.clear_images();s.title.draw_game_title=False
        s.title.command_window.offset_x=20;s.title.command_window.background='dim'
        s.side_view=True;s.battle_system='tpb_wait';s.set_window_tone(-10,20,30,5)
        s.player_start.set(1,5,6);s.boat.position.set(1,2,3);s.ship.clear_image()
        for option in OPTIONS:s.options.set(option,True)
        for name in ['title','battle','victory','defeat','game_over','boat','ship','airship']:
            audio=s.music.get(name);audio.name='New';audio.volume=50;audio.pitch=120;audio.pan=-20
        for name in SOUNDS:s.sounds.clear(name)
        self.db.types.elements.set(1,'火')
        p=self.db.preview();self.assertEqual((self.data/'System.json').read_bytes(),self.raw)
        self.db.commit(p)
        new=Database(self.root);self.assertEqual(new.system.game_title,'New')
        self.assertEqual(new.system.starting_party.get(),[2])
        self.assertEqual(new.types.elements.get(1),'火')
        self.assertEqual(new.system.music.get('boat').get()['plugin'],1)
        self.assertEqual(new.system.player_start.get(),dict(map_id=1,x=5,y=6))
        self.assertEqual(new.system.sounds.get('cursor').name,'')
        self.assertTrue((self.data/'System.json').read_bytes().endswith(b'\r\n'))
    def test_validation(self):
        s=self.db.system
        for f in [lambda:s.music.get('title').__setattr__('volume',101),lambda:s.options.set('autosave',1),lambda:s.starting_party.set([1,1]),lambda:s.player_start.clear(),lambda:s.music.get('unknown')]:
            with self.assertRaises(ValueError):f()
        s.player_start.set(1,10,0)
        with self.assertRaises(ValueError):self.db.preview()
        s.player_start.set(1,0,0);s.starting_party.add(99)
        with self.assertRaises(ValueError):self.db.preview()
    def test_noop_and_conflict(self):
        self.db.system.describe();self.assertIsNone(self.db.commit(self.db.preview()))
        self.assertEqual((self.data/'System.json').read_bytes(),self.raw)
        d=Database(self.root);d.system.game_title='X';p=d.preview();d.system.game_title='Y'
        with self.assertRaises(ValueError):d.commit(p)
    def test_new_actor_and_party(self):
        a=self.db.actors.create('New');self.db.system.starting_party.add(a.id)
        self.db.commit(self.db.preview())
        self.assertEqual(Database(self.root).system.starting_party.get(),[1,3])
