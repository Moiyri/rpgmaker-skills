import importlib.util
from pathlib import Path
import socket
import struct
import time
import unittest

spec=importlib.util.spec_from_file_location('playtest_connection',Path(__file__).resolve().parents[1]/'skills/rpgmaker-playtest/scripts/connection.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
class PlaytestConnectionTests(unittest.TestCase):
    def setUp(self):
        self.a,self.b=socket.socketpair();self.addCleanup(self.a.close);self.addCleanup(self.b.close)
        self.c=m.CDP.__new__(m.CDP);self.c.sock=self.a;self.c.buffer=b'';self.c.serial=0;self.c.events=[]
    def test_fragmented_message_with_ping(self):
        self.b.sendall(b'\x01\x05{"x":'+b'\x89\x01p'+b'\x80\x021}')
        self.assertEqual(self.c._receive(time.monotonic()+1),{'x':1})
        pong=self.b.recv(32);self.assertEqual(pong[0],0x8a);self.assertEqual(pong[-1]^pong[2],ord('p'))
    def test_request_skips_event(self):
        import json
        for value in [{'method':'Runtime.exceptionThrown','params':{}},{'id':1,'result':{'ok':True}}]:
            data=json.dumps(value).encode();self.b.sendall(bytes([129,len(data)])+data)
        self.assertEqual(self.c.request('Runtime.enable'),{'ok':True})
        self.assertEqual(len(self.c.events),1)
    def test_client_masks_long_payload(self):
        data=b'a'*200;self.c._send(data);frame=self.b.recv(512)
        self.assertEqual(frame[:2],b'\x81\xfe');self.assertEqual(struct.unpack('!H',frame[2:4])[0],200)
        self.assertEqual(bytes(v^frame[4+i%4] for i,v in enumerate(frame[8:])),data)
    def test_closed_peer(self):
        self.b.close()
        with self.assertRaises(ConnectionError):self.c._receive(time.monotonic()+1)
