"""Local NW.js CDP client, Python standard library only; one in-flight request."""
import base64
import hashlib
import json
import select
import secrets
import socket
import struct
import time
from urllib.parse import urlsplit
from urllib.request import urlopen

class CDP:
    def __init__(self, port=19224):
        with urlopen(f'http://127.0.0.1:{port}/json/list', timeout=5) as response:
            pages = [p for p in json.load(response) if p['type']=='page' and '/index.html' in p['url']]
        if len(pages)!=1: raise RuntimeError('Expected exactly one game page')
        u=urlsplit(pages[0]['webSocketDebuggerUrl'])
        if u.scheme!='ws' or u.hostname not in ('127.0.0.1','localhost','::1'): raise ValueError('Local websocket required')
        self.sock=socket.create_connection((u.hostname,u.port),5)
        self.buffer=b''; self.serial=0; self.events=[]; self.listeners={}
        key=base64.b64encode(secrets.token_bytes(16)).decode()
        self.sock.sendall((f'GET {u.path} HTTP/1.1\r\nHost: {u.netloc}\r\nUpgrade: websocket\r\nConnection: Upgrade\r\nSec-WebSocket-Key: {key}\r\nSec-WebSocket-Version: 13\r\n\r\n').encode())
        while b'\r\n\r\n' not in self.buffer:
            part=self.sock.recv(4096)
            if not part: raise ConnectionError('Closed during handshake')
            self.buffer+=part
            if len(self.buffer)>65536: raise ValueError('Oversized handshake')
        header,self.buffer=self.buffer.split(b'\r\n\r\n',1)
        lines=header.decode().split('\r\n')
        expected=base64.b64encode(hashlib.sha1((key+'258EAFA5-E914-47DA-95CA-C5AB0DC85B11').encode()).digest()).decode()
        # Header values are case-sensitive (notably Sec-WebSocket-Accept).
        headers={k.lower():v.strip() for k,v in (line.split(':',1) for line in lines[1:])}
        if lines[0].split()[1]!='101' or headers.get('sec-websocket-accept')!=expected:
            self.close(); raise ConnectionError('Invalid WebSocket handshake')
    def close(self): self.sock.close()
    def _read(self,n):
        while len(self.buffer)<n:
            part=self.sock.recv(max(4096,n-len(self.buffer)))
            if not part: raise ConnectionError('WebSocket closed')
            self.buffer+=part
        data,self.buffer=self.buffer[:n],self.buffer[n:]
        return data
    def _send(self,data,opcode=1):
        mask=secrets.token_bytes(4);n=len(data)
        size=bytes([n|128]) if n<126 else bytes([126|128])+struct.pack('!H',n) if n<65536 else bytes([127|128])+struct.pack('!Q',n)
        self.sock.sendall(bytes([128|opcode])+size+mask+bytes(v^mask[i%4] for i,v in enumerate(data)))
    def _receive(self,deadline):
        parts=[];active=False
        while True:
            remaining=deadline-time.monotonic()
            if remaining<=0: raise TimeoutError('CDP timeout; operation may still be running')
            self.sock.settimeout(remaining)
            a,b=self._read(2);opcode=a&15;n=b&127
            if a&112 or b&128: raise ValueError('Unsupported WebSocket frame')
            if n==126:n=struct.unpack('!H',self._read(2))[0]
            elif n==127:n=struct.unpack('!Q',self._read(8))[0]
            if n>32*1024*1024: raise ValueError('Frame too large')
            data=self._read(n)
            if opcode==8: raise ConnectionError('Peer closed connection')
            if opcode==9:self._send(data,10);continue
            if opcode==10:continue
            if opcode==1 and not active:active=True
            elif opcode!=0 or not active:raise ValueError('Unexpected frame')
            parts.append(data)
            if sum(map(len,parts))>32*1024*1024:raise ValueError('Message too large')
            if a&128:return json.loads(b''.join(parts))
    def on(self, method, callback):
        self.listeners[method] = callback
    def _dispatch(self, message):
        callback = self.listeners.get(message.get('method'))
        if callback:
            callback(message.get('params', {}))
        else:
            self.events.append(message)
            self.events = self.events[-200:]
    def receive_event(self, timeout=.2):
        """Wait for server events; no Runtime.evaluate polling."""
        if not self.buffer and not select.select([self.sock], [], [], timeout)[0]: return False
        self._dispatch(self._receive(time.monotonic()+5))
        return True
    def request(self,method,params=None,timeout=45):
        self.serial+=1;request_id=self.serial
        self._send(json.dumps({'id':request_id,'method':method,'params':params or {}}).encode())
        deadline=time.monotonic()+timeout
        try:
            while True:
                message=self._receive(deadline)
                if message.get('id')==request_id:
                    if 'error' in message:raise RuntimeError(message['error'])
                    return message.get('result',{})
                self._dispatch(message)
        except (TimeoutError,ConnectionError,OSError):
            self.close();raise
    def evaluate(self,expression,timeout=45):
        result=self.request('Runtime.evaluate',{'expression':expression,'awaitPromise':True,'returnByValue':True},timeout)
        if 'exceptionDetails' in result:raise RuntimeError(result['exceptionDetails'])
        return result.get('result',{}).get('value')
