import copy
from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'skills/rpgmaker-events/scripts'))
from event_api import *

class SceneControlTests(unittest.TestCase):
    def test_exact_codes_and_parameters(self):
        raw=EventList([NameInput(1,8),OpenMenu(),OpenSave(),GameOver(),ReturnToTitle()]).compile()
        self.assertEqual(raw,[{'code':code,'indent':0,'parameters':params} for code,params in
                             [(303,[1,8]),(351,[]),(352,[]),(353,[]),(354,[]),(0,[])]])
        event=EventList.from_commands(raw)
        self.assertFalse(event.find(OpaqueCommand));self.assertEqual(event.compile(),raw)

    def test_nested_and_edit(self):
        raw=EventList([If(Switch(1).is_on(),[NameInput(2,1),OpenMenu(),OpenSave()], [ReturnToTitle()])]).compile()
        event=EventList.from_commands(raw);self.assertEqual(event.compile(),raw)
        node=event.find(NameInput)[0];node.actor_id=3;node.max_chars=16
        self.assertEqual(event.compile()[1],{'code':303,'indent':1,'parameters':[3,16]})

    def test_invalid_inputs(self):
        for node in [NameInput(0),NameInput(True),NameInput(1,0),NameInput(1,17),NameInput(1,False)]:
            with self.subTest(node=node),self.assertRaises(ValueError):EventList([node]).compile()

    def test_unknown_extensions_remain_opaque(self):
        for node in [NameInput(1),OpenMenu(),OpenSave(),GameOver(),ReturnToTitle()]:
            raw=EventList([node]).compile();raw[0]['parameters'].append('extension')
            event=EventList.from_commands(raw)
            self.assertTrue(event.find(OpaqueCommand));self.assertEqual(event.compile(),raw)
