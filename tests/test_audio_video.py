import copy
import json
from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'skills/rpgmaker-events/scripts'))
from event_api import *

class AudioVideoTests(unittest.TestCase):
    def test_exact_parameters_and_roundtrip(self):
        nodes=[PlayBGM('Theme',80,110,-20),FadeoutBGM(3),SaveBGM(),ReplayBGM(),PlayBGS('Rain'),FadeoutBGS(0),PlayME('Victory'),PlaySE('Bell'),StopSE(),PlayMovie('intro/opening')]
        raw=EventList(nodes).compile()
        self.assertEqual([c['code'] for c in raw],[241,242,243,244,245,246,249,250,251,261,0])
        self.assertEqual(raw[0]['parameters'],[{'name':'Theme','volume':80,'pitch':110,'pan':-20}])
        self.assertEqual(raw[1]['parameters'],[3]);self.assertEqual(raw[5]['parameters'],[0])
        for i in (2,3,8):self.assertEqual(raw[i]['parameters'],[])
        for i,name in [(4,'Rain'),(6,'Victory'),(7,'Bell')]:self.assertEqual(raw[i]['parameters'],[{'name':name,'volume':90,'pitch':100,'pan':0}])
        self.assertEqual(raw[9]['parameters'],['intro/opening'])
        event=EventList.from_commands(raw);self.assertFalse(event.find(OpaqueCommand));self.assertEqual(event.compile(),raw)

    def test_real_editor_fixtures(self):
        values=json.loads((Path(__file__).parent/'fixtures/events/audio-video.json').read_text())
        self.assertEqual(len(values),8)
        for c in values.values():
            c=copy.deepcopy(c);c['indent']=0
            raw=[c,{'code':0,'indent':0,'parameters':[]}]
            event=EventList.from_commands(raw)
            self.assertFalse(event.find(OpaqueCommand));self.assertEqual(event.compile(),raw)

    def test_nested_edit_and_empty_names(self):
        raw=EventList([If(Switch(1).is_on(),[PlayBGM(''),PlayBGS(''),PlayME(''),PlaySE(''),PlayMovie('')])]).compile()
        event=EventList.from_commands(raw);self.assertEqual(event.compile(),raw)
        node=event.find(PlayBGM)[0];node.name='New';node.volume=0;node.pitch=50;node.pan=100
        self.assertEqual(event.compile()[1],{'code':241,'indent':1,'parameters':[{'name':'New','volume':0,'pitch':50,'pan':100}]})

    def test_invalid_parameters(self):
        nodes=[FadeoutBGM(-1),FadeoutBGS(True),FadeoutBGM(1.5),PlayMovie(1)]
        for cls in (PlayBGM,PlayBGS,PlayME,PlaySE):
            nodes += [cls(1),cls('x',volume=101),cls('x',pitch=49),cls('x',pan=-101),cls('x',volume=True)]
        for node in nodes:
            with self.subTest(node=node),self.assertRaises(ValueError):EventList([node]).compile()

    def test_extensions_remain_opaque(self):
        for node in [PlayBGM('x'),FadeoutBGM(1),SaveBGM(),ReplayBGM(),PlayBGS('x'),FadeoutBGS(1),PlayME('x'),PlaySE('x'),StopSE(),PlayMovie('x')]:
            raw=EventList([node]).compile();raw[0]['parameters'].append('extra')
            event=EventList.from_commands(raw);self.assertTrue(event.find(OpaqueCommand));self.assertEqual(event.compile(),raw)
        raw=EventList([PlaySE('x')]).compile();raw[0]['parameters'][0]['pluginOption']=True
        event=EventList.from_commands(raw);self.assertTrue(event.find(OpaqueCommand));self.assertEqual(event.compile(),raw)
