import json
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / 'skills/rpgmaker-database/scripts'
sys.path.insert(0, str(SCRIPTS))
from database_api import *
from database_core.effects import decode_effect
from database_core.backend import db


def item(id=1, name='Potion'):
    return dict(id=id,name=name,description='',iconIndex=0,itypeId=1,price=0,
                consumable=True,scope=7,occasion=0,speed=0,successRate=100,
                repeats=1,tpGain=0,hitType=0,animationId=0,note='',effects=[],
                damage=dict(type=0,elementId=0,formula='0',variance=20,critical=False),
                plugin={'encoded':'{"nested":[1,2]}'})


class ItemAPITests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.project=Path(self.temp.name)
        self.data=self.project/'data';self.data.mkdir()
        self.path=self.data/'Items.json'
        self.raw=('\ufeff[\r\nnull,\r\n'+json.dumps(item())+',\r\n'+json.dumps(item(2,''))+'\r\n]\r\n').encode()
        self.path.write_bytes(self.raw)
        for name in ['States','Skills','CommonEvents','Animations']:
            (self.data/(name+'.json')).write_text(json.dumps([None,{'id':1}]))
        (self.data/'System.json').write_text('{"elements":["","Fire"]}')
        self.db=Database(self.project)

    def test_list_find_and_identity(self):
        self.assertIn('0001 Potion',self.db.items.list())
        self.assertNotIn('0002',self.db.items.list())
        self.assertIn('0002',self.db.items.list(include_empty=True))
        self.assertIs(self.db.items.find('POT')[0],self.db.items.get(1))
        for id in [0,3,True]:
            with self.assertRaises(ValueError):self.db.items.get(id)

    def test_all_fields_and_damage(self):
        obj=self.db.items.get(1)
        values=dict(name='药水',description='恢复',icon_index=12,item_type='key_item',price=20,
                    consumable=False,scope='none',occasion='menu',speed=-5,success_rate=90,
                    repeats=2,tp_gain=5,hit_type='physical',animation_id=1,note='<tag>')
        for key,value in values.items():setattr(obj,key,value)
        for key,value in dict(type='hp_recover',element_id=1,formula='100',variance=0,critical=True).items():setattr(obj.damage,key,value)
        preview=self.db.preview()
        self.assertEqual(self.path.read_bytes(),self.raw)
        self.assertTrue(self.db.commit(preview))
        saved=Database(self.project).items.get(1)
        for key,value in values.items():self.assertEqual(getattr(saved,key),value)
        self.assertEqual(saved.damage.type,'hp_recover')
        self.assertEqual(saved.get(['plugin']),item()['plugin'])
        self.assertTrue(self.path.read_bytes().startswith(b'\xef\xbb\xbf[\r\n'))
        self.assertTrue(self.path.read_bytes().endswith(b'\r\n]\r\n'))
        self.assertIn(json.dumps(item(2,'')).encode(),self.path.read_bytes())

    def test_effect_codes_and_roundtrip(self):
        cases=[(RecoverHP(25,10),11,0,.25,10),(RecoverMP(-10,-5),12,0,-.1,-5),
               (GainTP(5),13,0,5,0),(AddState(1,50),21,1,.5,0),(RemoveState(1),22,1,1.,0),
               (AddBuff('attack',3),31,2,3,0),(AddDebuff('defense',2),32,3,2,0),
               (RemoveBuff('agility'),33,6,0,0),(RemoveDebuff('luck'),34,7,0,0),
               (Escape(),41,0,0,0),(GrowParameter('max_hp',10),42,0,10,0),
               (LearnSkill(1),43,1,0,0),(CommonEventEffect(1),44,1,0,0)]
        for effect,code,id,v1,v2 in cases:
            with self.subTest(code=code):
                raw=dict(code=code,dataId=id,value1=v1,value2=v2)
                self.assertEqual(effect.to_data(),raw)
                decoded=decode_effect(raw)
                self.assertIsInstance(decoded,type(effect))
                self.assertEqual(decoded.to_data(),raw)
                self.db.items.get(1).effects.add(effect)
        self.db.commit(self.db.preview())
        self.assertEqual(len(Database(self.project).items.get(1).effects),13)

    def test_effect_edit_and_extensions(self):
        raw=dict(code=11,dataId=0,value1=.29,value2=0,plugin='keep')
        effect=decode_effect(raw)
        self.assertEqual(effect.to_data(),raw)
        effect.amount=20
        self.assertEqual(effect.to_data()['plugin'],'keep')
        self.assertEqual(effect.to_data()['value2'],20)
        unknown=dict(code=999,dataId=1,value1=2,value2=3,extra=[1])
        self.assertIsInstance(decode_effect(unknown),OpaqueEffect)
        self.assertEqual(decode_effect(unknown).to_data(),unknown)
        self.assertIsInstance(decode_effect(dict(code=41,dataId=0,value1=7,value2=0)),OpaqueEffect)

    def test_effect_list_and_binding(self):
        obj=self.db.items.get(1)
        obj.effects.add(RecoverHP(amount=10));obj.bind_common_event(1);obj.bind_common_event(1)
        self.assertEqual(len(obj.effects),2)
        obj.effects.get(0).amount=20
        self.assertIn('20',obj.effects.list())
        obj.effects.remove(0)
        self.assertIsInstance(obj.effects.get(0),CommonEventEffect)
        obj.effects.clear();self.assertEqual(len(obj.effects),0)

    def test_nested_paths(self):
        obj=self.db.items.get(1)
        path=['plugin','encoded',{'decode':'json'},'nested',1]
        obj.set(path,9)
        self.assertEqual(obj.get(path),9)
        copy=obj.get(['plugin']);copy.clear()
        self.assertTrue(obj.get(['plugin']))
        with self.assertRaises(ValueError):obj.set(['id'],2)
        self.db.commit(self.db.preview())
        self.assertEqual(Database(self.project).items.get(1).get(path),9)

    def test_noop_exact_bytes(self):
        self.db.items.list(include_empty=True)
        self.assertIsNone(self.db.commit(self.db.preview()))
        self.assertEqual(self.path.read_bytes(),self.raw)

    def test_stale_preview(self):
        obj=self.db.items.get(1);obj.name='A';preview=self.db.preview();obj.name='B'
        with self.assertRaises(ValueError):self.db.commit(preview)
        self.assertEqual(self.path.read_bytes(),self.raw)

    def test_external_change(self):
        obj=self.db.items.get(1);obj.name='A';preview=self.db.preview()
        self.path.write_bytes(self.raw+b' ')
        with self.assertRaises(ValueError):self.db.commit(preview)

    def test_reference_change(self):
        self.db.items.get(1).bind_common_event(1);preview=self.db.preview()
        (self.data/'CommonEvents.json').write_text('[null,{"id":1,"name":"changed"}]')
        with self.assertRaises(ValueError):self.db.commit(preview)
        self.assertEqual(self.path.read_bytes(),self.raw)

    def test_invalid_fields_and_references(self):
        obj=self.db.items.get(1)
        for key,value in [('consumable',1),('scope','invalid'),('success_rate',101),('repeats',0)]:
            with self.assertRaises(ValueError):setattr(obj,key,value)
        for effect in [RecoverHP(101),AddState(1,-1),AddBuff('bad'),GainTP(True)]:
            with self.assertRaises(ValueError):obj.effects.add(effect)
        obj.bind_common_event(2)
        with self.assertRaises(ValueError):self.db.preview()
        self.assertEqual(self.path.read_bytes(),self.raw)

    def test_restore(self):
        self.db.items.get(1).name='Changed'
        transaction=self.db.commit(self.db.preview())
        originals,updated=db.prepare_restore(self.data.resolve(),Path(transaction))
        db.commit(self.data.resolve(),originals,updated)
        self.assertEqual(self.path.read_bytes(),self.raw)



class ItemManagementTests(unittest.TestCase):
    setUp = ItemAPITests.setUp
    def test_create_clear(self):
        created=self.db.items.create('Key')
        self.assertEqual(created.id,3)
        created.effects.add(RecoverHP(amount=10))
        old=self.db.items.get(1)
        self.assertIs(self.db.items.clear(1),old)
        self.assertEqual(old.name,'')
        self.assertNotIn('plugin',old.to_data())
        self.db.items.create('New',id=1)
        self.assertEqual(old.name,'New')
        preview=self.db.preview()
        self.assertEqual(self.path.read_bytes(),self.raw)
        self.db.commit(preview)
        saved=Database(self.project)
        self.assertEqual(saved.items.get(3).name,'Key')
        self.assertEqual(saved.items.get(3).effects.get(0).amount,10)
        self.assertEqual(saved.items.get(2).to_data(),item(2,''))

    def test_slots_and_refusals(self):
        with self.assertRaises(ValueError):self.db.items.create('Overwrite',id=1)
        # An unnamed record with plugin data is not an empty slot.
        with self.assertRaises(ValueError):self.db.items.create('Overwrite',id=2)
        with self.assertRaises(ValueError):self.db.items.create(id=5)
        self.db.items.clear(2)
        self.db.items.create('New',id=2)
        self.assertEqual(self.db.items.get(2).name,'New')
        self.db.commit(self.db.preview())

    def test_null_slot(self):
        self.path.write_text(json.dumps([None,item(),None]))
        database=Database(self.project)
        database.items.create('Null slot',id=2)
        database.commit(database.preview())
        self.assertEqual(Database(self.project).items.get(2).name,'Null slot')

    def test_references(self):
        def c(code,p):return dict(code=code,parameters=p,indent=0)
        commands=[c(126,[1,0,0,1]),c(111,[8,1]),c(302,[0,1,0,0,False]),
                  c(605,[0,1,0,0]),c(122,[1,1,0,3,0,1,0]),
                  c(302,[1,1,0,0,False]),c(111,[9,1]),c(122,[1,1,0,0,1]),
                  c(355,['$gameParty.gainItem($dataItems[1],1)'])]
        (self.data/'CommonEvents.json').write_text(json.dumps([None,dict(id=1,list=commands)]))
        page=dict(conditions=dict(itemValid=True,itemId=1),list=[])
        (self.data/'Map001.json').write_text(json.dumps(dict(events=[None,dict(pages=[page])])))
        (self.data/'Troops.json').write_text(json.dumps([None,dict(pages=[dict(list=[c(126,[1,0,0,1])])])]))
        (self.data/'Enemies.json').write_text(json.dumps([None,dict(dropItems=[dict(kind=1,dataId=1),dict(kind=2,dataId=1)])]))
        report=self.db.items.references(1)
        self.assertEqual(len(report),8)
        self.assertIn('插件动态引用未解析',str(report))
        self.assertEqual(next(iter(report)).path,(1,'list',0,'parameters',0))
        page['conditions']['itemValid']=False
        (self.data/'Map001.json').write_text(json.dumps(dict(events=[None,dict(pages=[page])])))
        self.assertEqual(len(self.db.items.references(1)),7)
        self.assertEqual(len(self.db.items.references(99)),0)

if __name__=='__main__':unittest.main()
