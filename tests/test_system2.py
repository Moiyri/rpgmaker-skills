import json
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from test_system_settings import SystemSettingsTests
from database_api import Database
import unittest

class System2Tests(unittest.TestCase):
    def setUp(self):
        SystemSettingsTests.setUp(self)
        p=self.data/'System.json';d=json.loads(p.read_text())
        d.update(menuCommands=[True]*6,itemCategories=[True]*4,magicSkills=[],
                 skillTypes=['','Magic'],weaponTypes=['','Sword'],attackMotions=[{'type':0,'weaponImageId':0},{'type':1,'weaponImageId':2,'extra':1}],
                 tileSize=48,iconSize=32,faceSize=144,
                 editor=dict(messageWidth1=60,messageWidth2=47,jsonFormatLevel=1,extra=1),
                 advanced=dict(gameId=1,screenWidth=816,screenHeight=624,uiAreaWidth=816,uiAreaHeight=624,screenScale=1,
                 mainFontFilename='a.ttf',numberFontFilename='b.ttf',fallbackFonts='sans-serif',fontSize=26,windowOpacity=255,picturesUpperLimit=100,extra=1))
        p.write_text(json.dumps(d));self.raw=p.read_bytes();self.db=Database(self.root)
    def test_fields_roundtrip(self):
        s=self.db.system
        for name in ['item','skill','equip','status','formation','save']:s.menu_commands.set(name,False)
        for name in ['item','weapon','armor','key_item']:s.item_categories.set(name,False)
        s.magic_skills.add(1);self.assertIn('Magic',s.magic_skills.list())
        s.attack_motions.set(1,motion='missile',weapon_image_id=7)
        new=self.db.types.weapon_types.add('New');s.attack_motions.set(new,motion='swing',weapon_image_id=1)
        s.tile_size=32;s.icon_size=24;s.face_size=96
        s.editor.message_width_normal=50;s.editor.message_width_with_face=35;s.editor.json_format_level=2
        vals=dict(game_id=2,screen_width=1280,screen_height=720,ui_area_width=1000,ui_area_height=600,
                  screen_scale=1.5,main_font_filename='x.ttf',number_font_filename='y.ttf',fallback_fonts='serif',font_size=30,window_opacity=200,pictures_upper_limit=150)
        for k,v in vals.items():setattr(s.advanced,k,v)
        preview=self.db.preview();self.assertEqual((self.data/'System.json').read_bytes(),self.raw)
        self.db.commit(preview);r=Database(self.root).system
        for k,v in vals.items():self.assertEqual(getattr(r.advanced,k),v)
        self.assertEqual(r.attack_motions.get(1).get()['extra'],1)
        self.assertEqual(r.editor.get()['extra'],1)
        self.assertEqual(r.magic_skills.get(),[1]);self.assertEqual(r.tile_size,32)
    def test_invalid_clear_noop(self):
        s=self.db.system
        for f in [lambda:s.menu_commands.set('item',1),lambda:s.magic_skills.add(2),lambda:setattr(s,'tile_size',30),lambda:setattr(s.advanced,'screen_scale',float('nan')),lambda:s.attack_motions.set(1,motion='wrong',weapon_image_id=1)]:
            with self.assertRaises(ValueError):f()
        self.assertIsNone(self.db.commit(self.db.preview()))
        db=Database(self.root);db.system.magic_skills.add(1);db.system.magic_skills.remove(1)
        db.system.attack_motions.clear(1)
        db.commit(db.preview());self.assertEqual(Database(self.root).system.attack_motions.get(1).weapon_image_id,0)
