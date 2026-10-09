import json
import sys
import tempfile
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'skills/rpgmaker-database/scripts'))
from database_api import Database

class TermsTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name);self.data=self.root/'data';self.data.mkdir()
        (self.data/'Items.json').write_text('[null]')
        commands=['Command']*26;commands[20]=None;commands[23]=None
        value=dict(gameTitle='Title',elements=['','Fire'],terms=dict(basic=['Text']*10,params=['Param']*10,commands=commands,messages={'saveMessage':'${Save Message}','levelUp':'%1 %2 %3','extension':'Keep'}),extension={'untouched':1})
        self.raw=('\ufeff'+json.dumps(value,indent=2)+'\r\n').encode()
        (self.data/'System.json').write_bytes(self.raw);self.db=Database(self.root)
    def test_edit_all_and_shared_commit(self):
        t=self.db.terms
        self.assertIn('0 等级',t.basic.list())
        self.assertIn('0 最大HP',t.params.list())
        self.assertEqual(t.messages.find('save'),[('saveMessage','${Save Message}')])
        t.basic.set(0,'等级');t.params.set(0,'最大生命');t.commands.set(18,'开始游戏')
        t.messages.set('levelUp','%1 升至 %2 %3！');t.messages.clear('saveMessage')
        self.db.types.elements.set(1,'火');self.db.system.game_title='新标题'
        p=self.db.preview();self.assertEqual((self.data/'System.json').read_bytes(),self.raw)
        self.db.commit(p);new=Database(self.root)
        self.assertEqual(new.terms.messages.get('levelUp'),'%1 升至 %2 %3！')
        self.assertEqual(new.terms.commands.get(20),None)
        self.assertEqual(new.terms.messages.get('extension'),'Keep')
        self.assertEqual(new.terms.basic.get(0),'等级')
        self.assertEqual(new.types.elements.get(1),'火')
        self.assertEqual(new.system.game_title,'新标题')
        self.assertTrue((self.data/'System.json').read_bytes().endswith(b'\r\n'))
    def test_noop_and_invalid(self):
        self.db.terms.describe();self.assertIsNone(self.db.commit(self.db.preview()))
        self.assertEqual((self.data/'System.json').read_bytes(),self.raw)
        db=Database(self.root)
        for call in [lambda:db.terms.commands.set(20,'x'),lambda:db.terms.basic.set(-1,'x'),lambda:db.terms.messages.set('missing','x'),lambda:db.terms.basic.set(0,None)]:
            with self.assertRaises(ValueError):call()
    def test_stale_preview(self):
        self.db.terms.basic.set(0,'A');p=self.db.preview();self.db.terms.basic.set(0,'B')
        with self.assertRaises(ValueError):self.db.commit(p)
