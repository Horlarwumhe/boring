from boring import __version__
from boring.utils import http_date

HTML_ERROR = """<html>
      <head>
        <title>{reason}</title>
      </head>
      <body>
        <h1><p>{reason}</p></h1>
        {body}
      </body>
    </html>
"""


class HttpException(Exception):

    code = 500
    reason = "Internal Server Error"
    body = "Internal Server Error"

    def __init__(self, code=None, reason=""):
        self.headers = [("Server", "Boring-Server/%s" % __version__)]
        self.code = code or self.code
        self.reason = reason or self.reason

    def write_error(self, conn, req=None, resp=None):
        error = HTML_ERROR.format(reason=self.reason, body=self.body)
        status = "HTTP/1.1 %s %s\r\n" % (self.code, self.reason)  # encode()
        status = status.encode()
        self.headers.extend([("Content-Length", len(error.encode())),
                             ("Date", http_date()), ("Connection", 'close')])
        headers = ["%s: %s\r\n" % (k, v) for k, v in self.headers]
        headers.append("\r\n")
        conn.send(status)
        conn.send("".join(headers).encode())
        conn.send(error.encode())


class BadRequest(HttpException):
    body = 'Bad Request'
    code = 400
    reason = "Bad Request"


class InvalidHeader(BadRequest):
    pass
