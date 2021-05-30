import socket
import unittest

from boring.http import HTTPParser, Request
from boring.wsgi import WsgiApp


class FakeSocket(socket.socket):
    def recv(self, size):
        request = b'''POST /user/login/ HTTP/1.1
Content-length: 12
Host: boring.com
User-Agent: chrome
Accept-Encoding: gzip

this is body'''.replace(b'\n', b'\r\n')
        return request

    def __del__(self):
    	self.close()

    def send(self,data):
    	pass


class FakeServer:
    pass

    def __getattr__(self):
        return self.__call__

    def __call__(self,*args,**kw):
        return True


class ParserTest(unittest.TestCase):
    def get_request(self):
        conn = FakeSocket()
        addr = ('localhost', 67712)  # remote addr
        parse = HTTPParser(conn, FakeServer(), addr)
        request = Request(parse())
        return request