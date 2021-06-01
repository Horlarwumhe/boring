import socket
import unittest

from boring.http import HTTPParser, Request


class FakeSocket(socket.socket):
    def recv(self, size):
        request = b'''POST /user/login/?q=hello&page=3 HTTP/1.1
Content-length: 12
Host: boring.com
User-Agent: chrome
Accept-Encoding: gzip

this is body'''.replace(b'\n', b'\r\n')
        return request

    def __del__(self):
        self.close()

    def send(self, data):
        pass


class FakeServer:
    #  server class is not needed for this test
    #  create a fake one to avoid raising attribute error
    pass

    def __getattr__(self):
        return ''


class ParserTest(unittest.TestCase):
    def get_request(self):
        conn = FakeSocket()
        addr = ('localhost', 67712)  # remote addr
        parse = HTTPParser(conn, FakeServer(), addr)
        request = Request(parse())
        return request

    def test_request_method(self):
        req = self.get_request()
        self.assertEqual(req.method, "POST")

    def test_headers(self):
        headers = self.get_request().headers
        headers_len = len(headers)
        self.assertEqual(headers_len, 4)
        self.assertEqual(headers.get('Host'), 'boring.com')
        self.assertEqual(headers.get('User-Agent'), 'chrome')
        self.assertIsNone(headers.get('Encoding'))

    def test_path(self):
        req = self.get_request()
        self.assertEqual(req.path, '/user/login/')
        #query string
        self.assertEqual(req.query, 'q=hello&page=3')

    def test_request_body(self):
        req = self.get_request()
        self.assertEqual(req.body.read(), b'this is body')


class Incomplete(FakeSocket):
    def recv(self, size):
        request = b'''POST /user/login/ HTTP/1.1
Content-length: 10
Host: boring.com
User-Agent: chrome
Accept-Encoding: gzip

this t'''.replace(b'\n', b'\r\n')
        return request


class IncompleteTest(unittest.TestCase):
    '''
    This class test some situations where the
    request body is less than content-length
    specified in the header field.
    eg
            POST / HTTP/1.1
            Content-Length: 10
            Host: localhost

            hello w
    The content-length is 10, but request body size is 7.
    Check if the server will start processing the request
    '''
    def get_parser(self):
        conn = Incomplete()
        addr = ('localhost', 67712)  # remote addr
        parse = HTTPParser(conn, FakeServer(), addr)
        return parse()

    def test_incomplete(self):
        parser = self.get_parser()
        self.assertFalse(parser.begin)

class ExcessData(FakeSocket):
    def recv(self, size):
        request = b'''POST /user/login/ HTTP/1.1
Content-Length: 20
Host: boring.com
User-Agent: chrome
Accept-Encoding: gzip

hello this is request body with excess data'''.replace(b'\n', b'\r\n')
        return request

class TestExcessData(unittest.TestCase):
    '''
    This class test situations where data sent is
    more than the content-length in the header.
    The server only read the size in the header field.
    eg.
        POST / HTTP/1.1
            Content-Length: 20
            Host: localhost

            hello word excess data in the body

    The content-length is 20 but body size is 34
    '''

    def get_request(self):
        conn = ExcessData()
        addr = ('localhost', 67712)  # remote addr
        parse = HTTPParser(conn, FakeServer(), addr)
        return Request(parse())

    def test_excess_size(self):
        request = self.get_request()
        size = request.headers.get("Content-Length")
        self.assertEqual(int(size),len(request.body.read()))


if __name__ == '__main__':
    unittest.main()
