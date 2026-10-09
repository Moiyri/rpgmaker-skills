import copy
import json
from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'skills/rpgmaker-events/scripts'))
from event_api import *

class ScreenTests(unittest.TestCase):
    def test_exact_parameters_and_roundtrip(self):
        raw=EventList([FadeoutScreen(),FadeinScreen(),TintScreen(-68,-68,0,68,30,False),FlashScreen(255,0,0,170,60,True),ShakeScreen(2,3,45,False),SetWeatherEffect('rain',7,60,True)]).compile()
        expected=[(221,[]),(222,[]),(223,[[-68,-68,0,68],30,False]),(224,[[255,0,0,170],60,True]),(225,[2,3,45,False]),(236,['rain',7,60,True]),(0,[])]
        self.assertEqual(raw,[{'code':c,'indent':0,'parameters':p} for c,p in expected])
        event=EventList.from_commands(raw);self.assertFalse(event.find(OpaqueCommand));self.assertEqual(event.compile(),raw)

    def test_editor_fixtures(self):
        values=json.loads((Path(__file__).parent/'fixtures/events/screen.json').read_text())
        self.assertEqual(len(values),5)
        for c in values.values():
            c=copy.deepcopy(c);c['indent']=0
            raw=[c,{'code':0,'indent':0,'parameters':[]}]
            event=EventList.from_commands(raw);self.assertFalse(event.find(OpaqueCommand));self.assertEqual(event.compile(),raw)

    def test_weather_variants_and_nested_edit(self):
        for weather in ('none','rain','storm','snow'):
            raw=EventList([If(Switch(1).is_on(),[SetWeatherEffect(weather,1,0,False),TintScreen(duration=0)])]).compile()
            event=EventList.from_commands(raw);self.assertEqual(event.compile(),raw)
            event.find(SetWeatherEffect)[0].power=9
            self.assertEqual(event.compile()[1],{'code':236,'indent':1,'parameters':[weather,9,0,False]})
            event.find(TintScreen)[0].red=-255
            self.assertEqual(event.compile()[2]['parameters'][0],[-255,0,0,0])

    def test_invalid_inputs(self):
        for node in [TintScreen(red=-256),TintScreen(gray=-1),TintScreen(duration=-1),TintScreen(wait=1),FlashScreen(red=-1),FlashScreen(intensity=256),FlashScreen(duration=0),ShakeScreen(power=0),ShakeScreen(speed=10),ShakeScreen(duration=0),SetWeatherEffect('wind'),SetWeatherEffect('rain',0),SetWeatherEffect(duration=-1)]:
            with self.subTest(node=node),self.assertRaises(ValueError):EventList([node]).compile()

    def test_extensions_remain_opaque(self):
        for node in [FadeoutScreen(),FadeinScreen(),TintScreen(),FlashScreen(),ShakeScreen(),SetWeatherEffect()]:
            raw=EventList([node]).compile();raw[0]['parameters'].append('extra')
            event=EventList.from_commands(raw);self.assertTrue(event.find(OpaqueCommand));self.assertEqual(event.compile(),raw)
