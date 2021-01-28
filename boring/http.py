import io
import time
import urllib.parse

from boring import __version__
from boring.exception import BadRequest, InvalidHeader


def http_date(t=None):
    return time.strftime("%a, %d %b %y %H:%M:%S")


class Request:

    def __init__(self, parser, conn=None):

        self._headers = {}
        self.uri = ""
        self.parser = parser
        self.addr = parser.remote_addr  # (addr,port)
        self.remote_addr, self.remote_port = self.addr
        try:
            self.method, self.uri, self.proto = parser.status_line.decode(
            ).split()
        except ValueError:
            raise BadRequest(400, "Invalid Status Line")
        self.uri = urllib.parse.unquote(self.uri)
        self.scheme = 'http'
        q = self.uri.find("?") > -1
        self.query = ''
        if q:
            self.path, query = self.uri.split("?", 1)
            self.query = urllib.parse.unquote(query)
        else:
            self.path = self.uri


    @property
    def headers(self):
        if self._headers:
            return self._headers
        headers = {}
        for k, v in self.parser.headers:
            headers[k.decode()] = v.decode()
        self._headers = headers
        return headers

    @property
    def should_close(self):
        c = self.headers.get("Connection")
        if c and c.lower() == "close":
            return True
        return False

    @property
    def body(self):
        return self.parser.body


class Response:

    def __init__(self, req, conn):

        self.req = req
        self.conn = conn
        self.headers = []
        self.code = ""
        self.reason = ""
        self.sent = 0
        self.headers_set = False
        self.headers_sent = False

    def start_response(self, status, headers):

        if getattr(self, "headers_set", False):
            return
        code, reason = status.split(" ", 1)
        self.code = code
        self.reason = reason
        self.headers.extend(headers)
        self.headers.extend(self.default_headers())
        self.headers_set = True
        #self.headers = headers

    def get_length(self):
        for name, value in self.headers:
            if name.lower() == 'content-length':
                return int(value)
        return 0

    def is_chunck(self):
        for k, v in self.headers:
            if k.lower() == 'transfer-encoding':
                return v == 'chunked'
        return False

    def default_headers(self):
        return [
            ("Date", http_date()),
            ("Server", "Boring-Server/%s" % __version__),
        ]

    def process_headers(self, headers):
        header = []
        for k, v in headers:
            header.append("%s: %s\r\n" % (k, v))
        header.append("\r\n")
        return "".join(header).encode()

    def write_response(self, data):
        if not self.headers_set:
            raise TypeError("start_response not called")
        size = self.get_length()
        chunck = False
        if not size:
            chunck = True
            if not self.is_chunck():
                self.headers.append(("Transfer-Encoding", 'chunked'))
        status = [
            b"HTTP/1.1",
            str(self.code).encode(),
            self.reason.encode(), b"\r\n"
        ]
        status = b" ".join(status)
        self.write(status)
        #self.conn.send(status)
        connection = self.req.headers.get('Connection', 'close')
        self.headers.append(("Connection", connection))
        header = self.process_headers(self.headers)
        #self.write_body(h)
        self.write(header)
        self.headers_sent = True
        self.write_body(data, size, chunck)

    def write_chunck(self, data):
        iterator = iter(data)
        try:
            while 1:
                try:
                    chunck = next(iterator)
                except StopIteration:
                    break
                size = ('%x' % len(chunck)).encode()
                body = b"%s\r\n%s\r\n" % (size, chunck)
                self.conn.send(body)
            self.conn.send(b'0\r\n\r\n')
        finally:
            if hasattr(data, 'close'):
                data.close()

    def write_body(self, data, size=None, chunck=False):
        assert size is not None
        if chunck:
            self.write_chunck(data)
            return
        try:
            iterator = iter(data)
            while 1:
                try:
                    data_chunck = next(iterator)
                except StopIteration:
                    break
                if self.sent >= size:
                    return
                remain = size - self.sent
                self.write(data_chunck[:remain])
                self.sent += len(data_chunck[:remain])
        finally:
            if hasattr(data, "close"):
                data.close()

    def write(self, data):
        self.conn.send(data)
        #self.conn.close()


class BodyReader:

    def __init__(self, buf=None, conn=None):
        self.buf = io.BytesIO()
        self.conn = conn
        self.chunk_left = 0
        self.is_chunk = False
        self.start = False

    def write(self, data):
        self.buf.write(data)

    def tell(self):
        return self.buf.tell()

    @property
    def size(self):
        return self.tell

    def seek(self, pos):
        self.buf.seek(pos)

    def getvalue(self):
        return self.buf.getvalue()

    def read(self, size=None):
        if not self.start:
            self.buf.seek(0)
            self.start = True
        return self.buf.read(size)

    def readline(self, size=None):
        if not self.start:
            self.buf.seek(0)
            self.start = True
        return self.buf.readline(size)


class HTTPParser:

    def __init__(self, sock, server, addr):
        self.server = server
        self.buf = io.BytesIO()
        self.conn = self.sock = sock
        self.seen_status = False
        self.seen_headers = False
        self.body = BodyReader(conn=sock)
        self.remote_addr = addr
        self.begin = False
        self.is_alive = True
        self.headers = []
        self.status_line = ''

    def read(self, n=1000):
        return self.buf.read(n)

    def write(self, data):
        self.buf.write(data)

    def readbuf(self):
        return self.buf.getvalue()

    def read_chunck(self):
        buf = io.BytesIO()
        buf.write(self.buf.getvalue())
        buf.seek(0)
        while 1:
            line = buf.readline()
            if not line:
                #  create new buf to write request body
                #  the previous one has been consumed
                self.buf = io.BytesIO()
                break
            size = line.strip(b'\r\n')
            try:
                size = int(size, 16)
            except ValueError:
                raise BadRequest(400, 'invalid chunck tranfer')
            if size == 0:
                self.begin = True
                return
            chunck = buf.readline(size)
            if len(chunck) != size:
                while len(chunck) < size:
                    # This fixes chunck  length less than size
                    # caused by .readline()
                    chunck += buf.readline(size - len(chunck))
            buf.readline()  # discard trailing \r\n
            self.body.write(chunck)

    def read_body(self):
        if self.status_line.split()[0] == b"GET":
            self.begin = True
            return
        size = 0
        for k, v in self.headers:
            if k.lower() == b"content-length":
                size = int(v)
            elif k.lower() == b"transfer-encoding" and v.lower() == b"chunked":
                #self.chunk = True
                self.body.is_chunk = True
                self.read_chunck()
                return
        buf_size = self.buf.tell()
        if not size:
            # no content-length, then can start processing the request
            self.begin = True
            return
        if size and buf_size >= size:
            # size (content-length) is >= amount in the buf
            self.begin = True
            self.buf.seek(0)
            self.body.write(self.buf.read(size))
            self.buf.read(size)
            # self.body_set = True

    def __call__(self, conn=None):
        data = self.conn.recv(1024)
        if not data:
            #client close connection
            self.is_alive = False
            return self
        self.buf.write(data)
        self.read_headers()
        return self

    def __bool__(self):
        return bool(self.headers)

    def parse_header(self, line):
        k, v = line.strip(b"\r\n").split(b" ", 1)
        return k.rstrip(b":"), v

    def read_headers(self):
        if self.seen_headers:
            if self.body.is_chunk:
                self.read_chunck()
            else:
                self.read_body()
            return
        headers = []
        done = self.buf.getvalue().find(b"\r\n\r\n") > -1
        if done:
            self.seen_headers = True
            self.buf.seek(0)
            status = self.buf.readline()
            while 1:
                header = self.buf.readline()
                if header == b"\r\n":
                    break
                try:
                    header = self.parse_header(header)
                except (ValueError, TypeError):
                    raise InvalidHeader(reason="invalid header field")
                headers.append(header)
            self.headers = headers
            self.status_line = status
            buf = io.BytesIO()
            buf.write(self.buf.read())
            self.buf = buf
            self.read_body()

    def get_headers(self):
        if not self.headers:
            self.read_headers()
        return self.headers
