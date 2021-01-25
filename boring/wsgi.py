import os
import socket
import sys
import traceback

from boring.exception import HttpException
from boring.http import Response


class WsgiApp:
    def __init__(self, app, request, conn, server, log):
        self.server = server
        self.req = request
        self.app = app
        self.conn = conn
        self.resp = Response(self.req, self.conn)
        self.log = log

    def wsgi_headers(self):
        environ = {
            "wsgi.version": (1, 0),
            "wsgi.url_scheme": self.req.scheme,
            "wsgi.input": self.req.body,
            "wsgi.errors": sys.stderr,
            "wsgi.multithread": False,
            "wsgi.multiprocess": False,
            "wsgi.run_once": False,
            "SERVER_SOFTWARE": "Boring/0.0.1",
            "REQUEST_METHOD": self.req.method,
            "SCRIPT_NAME": "",
            "PATH_INFO": self.req.path,
            "QUERY_STRING": self.req.query,
            "REQUEST_URI": self.req.uri,
            "RAW_URI": self.req.uri,
            "REMOTE_ADDR": self.req.remote_addr,
            "REMOTE_PORT": self.req.remote_port,
            "SERVER_NAME": "",
            "SERVER_PORT": "",
            "SERVER_PROTOCOL": self.req.proto
        }
        headers = self.req.headers.items()
        #(headers,"headee")
        for k, v in headers:
            if k not in ("Content-Length", "Content-Type"):
                k = "HTTP_" + k.replace("-", "_")
            else:
                k = k.replace("-", "_")
            environ[k.upper()] = v
        return environ

    def start_app(self, app):
        app_resp = app(self.wsgi_headers(), self.resp.start_response)
        self.resp.write_response(app_resp)
        #resp = Response(self.req,self.conn,self.server)

    def dispatch_request(self):
        try:
            self.start_app(self.app)
        except Exception as e:
            self.handle_error(e)
            traceback.print_exc()
        self.log.access(self.req, self.resp)
        if self.req.should_close:
            self.server.close_connection(self.conn)
        else:
            self.server.reuse_connection(self.conn, self.req)

    def log_request(self):
        pass

    def handle_error(self, exc):
        if self.resp.headers_sent:
            # headers have been sent before exception occurs
            self.server.close_connection(self.conn)
            return
        if isinstance(exc, HttpException):
            self.resp.code = exc.code
            self.resp.reason = exc.reason
        else:
            self.resp.code = "500"
            self.resp.reason = 'Internal Server Error'
            exc = HttpException(code=500, reason="Internal Server Error")
        try:
            exc.write_error(self.conn)
        except socket.error:
            pass


def load_app(args):
    app = args.app
    try:
        module, func = app.split(":")
    except (ValueError, TypeError):
        module, func = app, "application"
    try:
        sys.path.insert(0, os.getcwd())
        app = __import__(module)
        func = getattr(app, func)
    except ImportError as e:
        raise ImportError("could'nt import app %s , %s" % (module, e))
    except AttributeError:
        raise AttributeError(" module %s has no attribute %s " %
                             (module, func))
    if not hasattr(func, '__call__'):
        sys.exit("app must be a callable object")
    return func
