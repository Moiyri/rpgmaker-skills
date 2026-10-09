from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'skills/rpgmaker-events/scripts'))
from event_api import *
class ChoicesTests(unittest.TestCase):
 def test_choices(self):
  e=EventList([ShowText('插入？'),ShowChoices([('是',[ChangeVariable(201,'set',Constant(1)),ChangeItems(12,Constant(1),'sub')]),('否',[])],cancel=1)])
  raw=e.compile();self.assertEqual(raw[2]['parameters'],[['是','否'],1,0,2,0])
  d=EventList.from_commands(raw);self.assertEqual(d.compile(),raw);self.assertEqual(len(d.find(ChangeItems)),1)
  d.find(ChangeItems)[0].id=13;self.assertIn(13,[c['parameters'][0] for c in d.compile() if c['code']==126])
 def test_invalid(self):
  for node in [ShowChoices([]),ShowChoices([('是',[])],cancel=2)]:
   with self.assertRaises(ValueError):EventList([node]).compile()
