from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'skills/rpgmaker-events/examples'))
from item_common_event import build_event
from event_api import *

class ItemExampleTests(unittest.TestCase):
    def test_label_codes_roundtrip_and_extensions(self):
        raw=EventList([If(Switch(1).is_on(),[JumpToLabel('fail')]),ExitEvent(),Label('fail')]).compile()
        self.assertEqual(raw[1],{'code':119,'indent':1,'parameters':['fail']})
        self.assertEqual(raw[-3:], [{'code':115,'indent':0,'parameters':[]},{'code':118,'indent':0,'parameters':['fail']},{'code':0,'indent':0,'parameters':[]}])
        self.assertEqual(EventList.from_commands(raw).compile(),raw)
        self.assertFalse(EventList.from_commands(raw).find(OpaqueCommand))
        for node in (Label(''),JumpToLabel(1)):
            with self.assertRaises(ValueError):EventList([node]).compile()
        raw[-2]['parameters'].append('extra')
        self.assertTrue(EventList.from_commands(raw).find(OpaqueCommand))
        self.assertEqual(EventList.from_commands(raw).compile(),raw)

    def test_matches_reference1204_without_python_comments(self):
        import json
        reference=json.loads((Path(__file__).parent/'fixtures/events/item1204.json').read_text())
        expected=[]
        skip=False
        for c in reference:
            if c['code']==108:
                skip=c['parameters'][0].lstrip().startswith('//')
            elif c['code']!=408:
                skip=False
            if not skip:expected.append(c)
        event=build_event()
        self.assertEqual(event.compile(),expected)
        self.assertEqual(EventList.from_commands(expected).compile(),expected)
        self.assertEqual(len(event.find(Comment)),2)
        self.assertTrue(all(not c.text.startswith('//') for c in event.find(Comment)))

    def test_branch_order_and_failure_label(self):
        event=build_event();outer=event[0]
        self.assertEqual(len(event),1)
        self.assertEqual(outer.then[0].then[0].name,'Use Fail')
        self.assertIsInstance(outer.then[1].then[-1],ExitEvent)
        self.assertIsInstance(outer.then[3],ChangeItems)
        self.assertNotIsInstance(outer.then[-1],ExitEvent)
        self.assertIsInstance(outer.otherwise[0].then[-1],ExitEvent)
        self.assertIsInstance(outer.otherwise[1],Label)
        self.assertEqual(outer.otherwise[1].name,'Use Fail')
        self.assertEqual(len(event.find(ExitEvent)),2)
