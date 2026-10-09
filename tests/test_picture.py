import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'skills/rpgmaker-events/scripts'))
from event_api import *
from event_core.backend import db

class PictureTests(unittest.TestCase):
    def test_exact_parameters(self):
        raw=EventList([ShowPicture(1,'folder/Image',-20,30,origin='center',scale_x=80,scale_y=120,opacity=128,blend='add'),
                       MovePicture(1,VariableValue(8),VariableValue(9),duration=45,wait=False,easing='ease_in_out'),
                       RotatePicture(1,-10),TintPicture(1,-68,-68,0,68,30,False),ErasePicture(1)]).compile()
        self.assertEqual([c['parameters'] for c in raw[:-1]],[
            [1,'folder/Image',1,0,-20,30,80,120,128,1],
            [1,0,0,1,8,9,100,100,255,0,45,False,3],
            [1,-10],[1,[-68,-68,0,68],30,False],[1]])
        decoded=EventList.from_commands(raw)
        self.assertFalse(decoded.find(OpaqueCommand));self.assertEqual(decoded.compile(),raw)

    def test_editor_fixtures(self):
        fixtures=json.loads((Path(__file__).parent/'fixtures/events/pictures.json').read_text())
        self.assertEqual(set(fixtures),{'231','232','235'})
        for command in fixtures.values():
            raw=[command,{'code':0,'indent':0,'parameters':[]}]
            decoded=EventList.from_commands(raw)
            self.assertFalse(decoded.find(OpaqueCommand));self.assertEqual(decoded.compile(),raw)

    def test_variants_nested_and_edit(self):
        for origin in ('upper_left','center'):
            for blend in ('normal','add','multiply','screen'):
                for easing in ('linear','ease_in','ease_out','ease_in_out'):
                    event=EventList([If(Switch(1).is_on(),[
                        ShowPicture(100,'A',VariableValue(1),VariableValue(2),origin=origin,blend=blend),
                        MovePicture(100,-1,-2,origin=origin,blend=blend,easing=easing),
                        RotatePicture(100,0),TintPicture(100,255,-255,255,255),ErasePicture(100)])])
                    raw=event.compile();decoded=EventList.from_commands(raw)
                    self.assertFalse(decoded.find(OpaqueCommand));self.assertEqual(decoded.compile(),raw)
                    decoded.find(MovePicture)[0].opacity=0
                    self.assertEqual(decoded.compile()[2]['parameters'][8],0)
                    self.assertTrue(all(c['indent']==1 for c in raw[1:6]))

    def test_invalid_parameters(self):
        nodes=[ShowPicture(0,'A'),ShowPicture(101,'A'),ShowPicture(True,'A'),ShowPicture(1,4),
               ShowPicture(1,'A',VariableValue(1),0),ShowPicture(1,'A',VariableValue(0),VariableValue(1)),
               ShowPicture(1,'A',origin='bad'),ShowPicture(1,'A',scale_x=-1),ShowPicture(1,'A',opacity=256),
               ShowPicture(1,'A',blend='bad'),MovePicture(1,duration=0),MovePicture(1,wait=1),
               MovePicture(1,easing='bad'),RotatePicture(1,91),TintPicture(1,red=-256),TintPicture(1,gray=-1),
               TintPicture(1,duration=0),ErasePicture(-1)]
        for node in nodes:
            with self.subTest(node=node),self.assertRaises(ValueError):EventList([node]).compile()

    def test_legacy_and_extensions_preserved(self):
        original=EventList([MovePicture(1)]).compile()
        for mutate in (lambda r:r[0]['parameters'].pop(),lambda r:r[0]['parameters'].__setitem__(1,'extension'),
                       lambda r:r[0]['parameters'].append(99),lambda r:r[0].update(extra=True)):
            raw=copy.deepcopy(original);mutate(raw)
            event=EventList.from_commands(raw)
            self.assertTrue(event.find(OpaqueCommand));self.assertEqual(event.compile(),raw)

    def test_write_and_restore_preserve_format(self):
        for nl in (b'\n',b'\r\n'):
            with tempfile.TemporaryDirectory() as directory:
                root=Path(directory).resolve();file=root/'Map001.json'
                raw=b'\xef\xbb\xbf{'+nl+b'"keep":1e2,"list":[{"code":0,"indent":0,"parameters":[]}]}'+nl
                file.write_bytes(raw)
                commands=EventList([ShowPicture(1,'A'),MovePicture(1,10,20),RotatePicture(1,2),TintPicture(1,gray=255),ErasePicture(1)]).compile()
                plan={'version':1,'format':'preserve','operations':[{'op':'set','file':'Map001.json','path':['list'],'value':commands}]}
                before,after,_=db.prepare(root,plan)
                self.assertEqual(after['Map001.json'].count(nl),raw.count(nl))
                self.assertTrue(after['Map001.json'].startswith(raw.split(b'"list":')[0]))
                transaction=db.commit(root,before,after)
                self.assertEqual(db.read_document(file.read_bytes())['list'],commands)
                before,after=db.prepare_restore(root,transaction);db.commit(root,before,after)
                self.assertEqual(file.read_bytes(),raw)
