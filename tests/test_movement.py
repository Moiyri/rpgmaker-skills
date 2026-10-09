import copy
import json
from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'skills/rpgmaker-events/scripts'))
from event_api import *
from event_core.commands.movement import MOVES,TURNS,FLAGS
from event_core.compiler import compile_document

class MovementTests(unittest.TestCase):
    def test_event_parameters_and_roundtrip(self):
        nodes=[SetVehicleLocation('ship',2,3,4),SetVehicleLocation('airship',VariableValue(1),VariableValue(2),VariableValue(3)),
               SetEventLocation(0,4,5,'up'),SetEventLocation(2,VariableValue(3),VariableValue(4)),
               SetEventLocation(3,exchange=4,direction='left'),ScrollMap('right',5,6,True),GetOnOffVehicle()]
        raw=EventList(nodes).compile()
        self.assertEqual([c['parameters'] for c in raw[:-1]],[[1,0,2,3,4],[2,1,1,2,3],[0,0,4,5,8],[2,1,3,4,0],[3,2,4,0,4],[6,5,6,True],[]])
        decoded=EventList.from_commands(raw)
        self.assertFalse(decoded.find(OpaqueCommand))
        self.assertEqual(decoded.compile(),raw)
        decoded.find(SetEventLocation)[0].x=9
        self.assertEqual(decoded.compile()[2]['parameters'][2],9)

    def test_all_45_route_codes_and_nested_roundtrip(self):
        steps=[Route.move(d) for d in MOVES]+[Route.jump(-2,3),Route.wait(60)]+[Route.turn(d) for d in TURNS]
        steps += [Route.switch(2,True),Route.switch(2,False),Route.speed(6),Route.frequency(5)]
        steps += [Route.option(n,b) for n in FLAGS for b in (True,False)]
        steps += [Route.image('Actor1',7),Route.opacity(128),Route.blend('screen'),Route.se('Bell',90,100,-10),Route.script('this.setOpacity(255);')]
        event=EventList([If(Switch(1).is_on(),[SetMovementRoute(-1,steps,skippable=True)])])
        raw=event.compile(); route=raw[1]['parameters'][1]
        self.assertEqual([s['code'] for s in route['list']],list(range(1,46))+[0])
        self.assertEqual([c['parameters'][0] for c in raw[2:47]],route['list'][:-1])
        self.assertTrue(all(c['indent']==1 for c in raw[1:47]))
        decoded=EventList.from_commands(raw)
        self.assertEqual(len(decoded.find(SetMovementRoute)),1)
        self.assertEqual(decoded.compile(),raw)
        node=decoded.find(SetMovementRoute)[0]
        node.steps[0]=Route.move('up');node.steps.pop();node.steps.append(Route.wait(1))
        changed=decoded.compile()
        self.assertEqual(changed[1]['parameters'][1]['list'][0]['code'],4)
        self.assertEqual(changed[2]['parameters'][0]['code'],4)

    def test_real_editor_route_fixtures(self):
        fixtures=json.loads((Path(__file__).parent/'fixtures/events/movement-routes.json').read_text())
        for block in fixtures:
            block=copy.deepcopy(block)
            for c in block:c['indent']=0
            raw=block+[{'code':0,'indent':0,'parameters':[]}]
            decoded=EventList.from_commands(raw)
            self.assertEqual(len(decoded.find(SetMovementRoute)),1)
            self.assertEqual(decoded.compile(),raw)
            self.assertEqual(json.dumps(decoded.compile(),ensure_ascii=False,separators=(',',':')),json.dumps(raw,ensure_ascii=False,separators=(',',':')))

    def test_route_without_indent_and_empty_route(self):
        node=Route.move('down');node.editor_indent=False
        for steps in ([],[node]):
            raw=EventList([SetMovementRoute(0,steps,repeat=True,wait=False)]).compile()
            self.assertEqual(EventList.from_commands(raw).compile(),raw)
            self.assertTrue(EventList.from_commands(raw).find(SetMovementRoute))

    def test_extensions_and_mismatched_505_are_opaque(self):
        original=EventList([SetMovementRoute(-1,[Route.wait(3)])]).compile()
        for mutate in (lambda r:r[0]['parameters'][1].update(extra=1),lambda r:r[1]['parameters'][0].update(parameters=[4]),
                       lambda r:r[0]['parameters'][1]['list'][0].update(code=999)):
            raw=copy.deepcopy(original);mutate(raw)
            decoded=EventList.from_commands(raw)
            self.assertTrue(decoded.find(OpaqueCommand));self.assertEqual(decoded.compile(),raw)

    def test_invalid_arguments(self):
        nodes=[SetVehicleLocation('car',1,0,0),SetVehicleLocation('boat',1,VariableValue(2),0),SetEventLocation(-1,0,0),
               SetEventLocation(1,1,2,exchange=3),ScrollMap('keep',1),ScrollMap('up',0),ScrollMap('up',1,7),
               SetMovementRoute(-2,[]),SetMovementRoute(-1,[],repeat=True,wait=True)]
        badsteps=[Route.move('bad'),Route.jump(True,0),Route.wait(0),Route.switch(0),Route.speed(7),Route.frequency(6),
                  Route.option('walking',1),Route.image('x',8),Route.opacity(256),Route.blend('bad'),Route.se('x',101),Route.script(5)]
        nodes += [SetMovementRoute(-1,[s]) for s in badsteps]
        for node in nodes:
            with self.subTest(node=node),self.assertRaises(ValueError):EventList([node]).compile()

    def test_route_write_preserves_format_and_restores(self):
        import tempfile
        from event_core.backend import db
        for nl in (b'\n',b'\r\n'):
            with tempfile.TemporaryDirectory() as directory:
                root=Path(directory).resolve()
                original=b'\xef\xbb\xbf{'+nl+b'"keep":1e2,"list":[{"code":0,"indent":0,"parameters":[]}]}'+nl
                file=root/'Map001.json';file.write_bytes(original)
                commands=EventList([SetMovementRoute(-1,[Route.move('left'),Route.se('Bell')])]).compile()
                plan={'version':1,'format':'preserve','operations':[{'op':'set','file':'Map001.json','path':['list'],'value':commands}]}
                before,after,_=db.prepare(root,plan)
                self.assertEqual(after['Map001.json'].count(nl),original.count(nl))
                self.assertTrue(after['Map001.json'].startswith(original.split(b'"list":')[0]))
                transaction=db.commit(root,before,after)
                self.assertEqual(db.read_document(file.read_bytes())['list'],commands)
                before,after=db.prepare_restore(root,transaction);db.commit(root,before,after)
                self.assertEqual(file.read_bytes(),original)
