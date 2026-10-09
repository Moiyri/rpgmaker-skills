import copy
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

SCRIPTS=Path(__file__).resolve().parents[1]/'skills/rpgmaker-events/scripts'
sys.path.insert(0,str(SCRIPTS))
from event_api import (MapDocument, EventPage, EventList, ShowText, SetSwitch, ChangeVariable,
                       Constant, VariableValue, If, Switch, Variable, Wait, list_map, search_events)
from event_core.map_events import default_page
from event_core.backend import db
import map_events


class MapEventTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.project=Path(self.temp.name).resolve();self.root=self.project/'data';self.root.mkdir()
        page=default_page();page['pluginField']={'keep':[1,'中文']}
        page['list']=EventList([ShowText('保留文本'),SetSwitch(3,end=7),
                   ChangeVariable(10,'set',VariableValue(20)),If(Variable(30).equal_to(40),[Wait(1)])]).compile()
        e={'id':1,'name':'门卫','note':'<keep>','x':2,'y':3,'pages':[page],'pluginEvent':'keep'}
        self.doc={'width':10,'height':10,'events':[None,e,None,dict(copy.deepcopy(e),id=3,name='商人')],'data':[1,2,3]}
        self.raw=('\ufeff{\r\n"width":10,"height":10,"events":'+json.dumps(self.doc['events'],ensure_ascii=False,separators=(',',':'))+',\r\n"data":[1,2,3]}\r\n').encode()
        (self.root/'Map001.json').write_bytes(self.raw)
        (self.root/'MapInfos.json').write_text(json.dumps([None,{'id':1,'name':'城镇'}]))
        common=[None,{'id':1,'name':'门卫公共','trigger':2,'switchId':9,'list':EventList([SetSwitch(15),ChangeVariable(16,'set',Constant(40))]).compile()}]
        (self.root/'CommonEvents.json').write_text(json.dumps(common))

    def prepare(self,plan):
        with patch.object(map_events,'page_source_profile',return_value={'profile_matches':True}):
            return map_events.prepare(self.project,plan)

    def test_new_editor_map_empty_array(self):
        data=copy.deepcopy(self.doc);data['events']=[]
        raw=json.dumps(data).encode();(self.root/'Map001.json').write_bytes(raw)
        doc=MapDocument(self.project,1)
        self.assertEqual(self.prepare(doc.to_plan())[2]['Map001.json'],raw)
        npc=doc.create_event('NPC',4,4)
        self.assertEqual(npc.id,1)
        rows=json.loads(self.prepare(doc.to_plan())[2]['Map001.json'])['events']
        self.assertIsNone(rows[0]);self.assertEqual(rows[1]['id'],1)

    def test_noop_preserves_every_byte_and_lazy_commands(self):
        doc=MapDocument(self.project,1)
        root,before,after,result=self.prepare(doc.to_plan())
        self.assertFalse(result['changed']);self.assertEqual(after['Map001.json'],self.raw)
        self.assertEqual(doc.event(1).page(0).commands.compile(),self.doc['events'][1]['pages'][0]['list'])
        self.assertEqual(self.prepare(doc.to_plan())[2]['Map001.json'],self.raw)

    def test_full_page_edit_keeps_unknown_fields(self):
        doc=MapDocument(self.project,1);event=doc.event(1)
        event.name='测试';event.note='<new>';event.x=4;event.y=5
        p=event.page(0)
        p.set_conditions(switch1=1,switch2=2,variable=(3,10),self_switch='B',item=4,actor=5)
        p.set_image(character_name='Actor1',character_index=2,direction='left',pattern=0)
        route={'list':[{'code':27,'parameters':[8]},{'code':0,'parameters':[]}],'repeat':True,'skippable':True,'wait':False}
        p.set_movement(type='custom',speed=4,frequency=5,route=route)
        p.set_options(walking=False,stepping=True,direction_fix=True,through=True)
        p.priority='same';p.trigger='parallel';p.commands.append(ShowText('新增'))
        root,before,after,result=self.prepare(doc.to_plan())
        data=json.loads(after['Map001.json']);changed=data['events'][1]
        self.assertEqual(changed['name'],'测试');self.assertEqual(changed['note'],'<new>')
        self.assertEqual(changed['pages'][0]['conditions']['variableValue'],10)
        self.assertEqual(changed['pages'][0]['image']['direction'],4)
        self.assertEqual(changed['pages'][0]['trigger'],4)
        self.assertEqual(changed['pages'][0]['pluginField'],{'keep':[1,'中文']})
        self.assertEqual(changed['pluginEvent'],'keep')
        self.assertEqual(data['events'][3],self.doc['events'][3]);self.assertEqual(data['data'],[1,2,3])
        self.assertTrue(after['Map001.json'].startswith(b'\xef\xbb\xbf'))
        self.assertEqual(after['Map001.json'].count(b'\r\n'),self.raw.count(b'\r\n'))
        txn=db.commit(root,before,after);current,restore=db.prepare_restore(root,txn);db.commit(root,current,restore)
        self.assertEqual((self.root/'Map001.json').read_bytes(),self.raw)

    def test_create_delete_reuse_and_id_stability(self):
        doc=MapDocument(self.project,1)
        e=doc.create_event('新事件',0,0);self.assertEqual(e.id,2)
        self.assertEqual(doc.create_event('末尾',1,1).id,4)
        doc.delete_event(1)
        data=json.loads(self.prepare(doc.to_plan())[2]['Map001.json'])
        self.assertIsNone(data['events'][1]);self.assertEqual(data['events'][3]['id'],3)
        self.assertEqual(data['events'][2]['pages'][0]['list'],[{'code':0,'indent':0,'parameters':[]}])
        with self.assertRaises(ValueError):doc.create_event('覆盖',0,0,event_id=3)
        with self.assertRaises(ValueError):doc.create_event('越界',10,0)
        with self.assertRaises(ValueError):doc.delete_event(0)

    def test_page_copy_paste_move_delete_clear(self):
        e=MapDocument(self.project,1).event(1)
        second=e.copy_page(0);second.set_conditions(switch1=8)
        second.commands.find(ShowText)[0].lines='副本'
        self.assertEqual(e.page(0).commands.find(ShowText)[0].lines,['保留文本'])
        e.move_page(1,0);self.assertIs(e.page(0),second)
        copied=e.add_page(e.page(0),index=1);self.assertIsNot(copied,second)
        e.delete_page(2);e.clear_page(1);self.assertEqual(e.page(1).to_data(),default_page())
        e.delete_page(1)
        with self.assertRaises(ValueError):e.delete_page(0)
        with self.assertRaises(ValueError):e.page(-1)

    def test_disabled_condition_preserves_stored_id(self):
        page=EventPage();page.set_conditions(switch1=12,variable=(8,-1))
        page.set_conditions(switch1=None)
        c=page.to_data()['conditions'];self.assertFalse(c['switch1Valid']);self.assertEqual(c['switch1Id'],12)
        self.assertTrue(c['variableValid']);self.assertEqual(c['variableValue'],-1)
        with self.assertRaises(ValueError):page.set_conditions(switch1=0)
        with self.assertRaises(ValueError):page.set_options(walking=1)
        with self.assertRaises(ValueError):page.set_movement(speed=7)
        with self.assertRaises(ValueError):page.set_image(character_name='Actor1',tile_id=10)
        page.set_image(tile_id=10);self.assertEqual(page.to_data()['image']['characterName'],'')

    def test_search_name_switch_variable_and_no_constant_false_positive(self):
        self.assertEqual(search_events(self.project,name='门卫')['total'],2)
        self.assertEqual(search_events(self.project,switch=5)['total'],2)
        self.assertEqual(search_events(self.project,switch=9)['results'][0]['target'],{'kind':'common','id':1})
        self.assertEqual(search_events(self.project,variable=20)['total'],2)
        self.assertEqual(search_events(self.project,variable=30)['total'],2)
        self.assertEqual(search_events(self.project,variable=40)['total'],0)
        self.assertEqual(search_events(self.project,name='商人',switch=5)['total'],1)
        self.assertEqual(search_events(self.project,name='门卫',map_id=1)['total'],1)
        rows=list_map(self.project,1);self.assertEqual(len(rows['events']),2)
        self.assertEqual(rows['map_name'],'城镇');self.assertEqual(rows['events'][0]['x'],2)

    def test_search_page_conditions_and_routes(self):
        doc=MapDocument(self.project,1);p=doc.event(1).page(0)
        p.set_conditions(switch1=40,variable=(50,60))
        route=p.to_data()['moveRoute'];route['list'].insert(0,{'code':27,'parameters':[70]})
        p.set_movement(type='custom',route=route)
        root,before,after,_=self.prepare(doc.to_plan());db.commit(root,before,after)
        self.assertEqual(search_events(self.project,switch=40)['results'][0]['matches'][0]['source'],'page_condition')
        self.assertEqual(search_events(self.project,variable=50)['total'],1)
        self.assertEqual(search_events(self.project,variable=60)['total'],0)
        self.assertEqual(search_events(self.project,switch=70)['results'][0]['matches'][0]['source'],'autonomous_route')

    def test_snapshot_conflict_and_invalid_plan(self):
        doc=MapDocument(self.project,1);doc.event(1).name='编辑'
        plan=doc.to_plan();changed=copy.deepcopy(self.doc);changed['data'][0]=9
        (self.root/'Map001.json').write_text(json.dumps(changed))
        with self.assertRaises(ValueError):self.prepare(plan)
        plan['operations']=plan['operations'][1:]
        with self.assertRaises(ValueError):self.prepare(plan)
        doc=MapDocument(self.project,1);doc.event(1).x=10
        with self.assertRaises(ValueError):doc.to_plan()

    def test_cli_read_only(self):
        result=subprocess.run([sys.executable,str(SCRIPTS/'map_events.py'),'--project',str(self.project),'search','--variable','20'],capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stderr);self.assertEqual(json.loads(result.stdout)['total'],2)
        self.assertEqual((self.root/'Map001.json').read_bytes(),self.raw)

    @unittest.skipUnless(os.environ.get('RPGMAKER_EVENTS_PROJECT'),'Set RPGMAKER_EVENTS_PROJECT for integration')
    def test_real_map_copy_cli_apply_and_restore(self):
        original=Path(os.environ['RPGMAKER_EVENTS_PROJECT'])
        file=next((original/'data').glob('Map[0-9]*.json'));mid=int(file.stem[3:])
        raw=file.read_bytes()
        (self.project/'js').mkdir();shutil.copyfile(original/'js/rmmz_objects.js',self.project/'js/rmmz_objects.js')
        shutil.copyfile(file,self.root/file.name)
        doc=MapDocument(self.project,mid);event=doc.create_event('接口副本测试',0,0)
        page=event.page(0);page.set_conditions(switch1=1);page.commands.append(ShowText('测试'))
        event.copy_page(0).set_conditions(self_switch='A')
        plan=self.project/'plan.json';plan.write_text(json.dumps(doc.to_plan(),ensure_ascii=False))
        cmd=[sys.executable,str(SCRIPTS/'map_events.py'),'--project',str(self.project),'apply','--plan',str(plan)]
        preview=subprocess.run(cmd,capture_output=True,text=True);self.assertEqual(preview.returncode,0,preview.stderr)
        token=json.loads(preview.stdout)['preview_sha256']
        written=subprocess.run(cmd+['--write','--expect-preview',token],capture_output=True,text=True)
        self.assertEqual(written.returncode,0,written.stderr)
        result=json.loads(written.stdout);self.assertTrue(result['written'])
        current,restored=db.prepare_restore(self.root,result['transaction']);db.commit(self.root,current,restored)
        self.assertEqual((self.root/file.name).read_bytes(),raw);self.assertEqual(file.read_bytes(),raw)
