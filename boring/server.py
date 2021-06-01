import argparse
import contextlib
import importlib
import logging
import os
import selectors
import signal
import socket
import sys
import time
import threading
import traceback

from boring import __version__, utils, wsgi
from boring.config import BadConfigFile, Config, DummyConfig
from boring.exception import HttpException
from boring.http import HTTPParser, Request
from boring.wsgi import WsgiApp

from .dir import DirectoryServer
from . import reloader


class Logger:

    # 127.0.0.1 -- [2021-03-20 08:05:16,814] GET / HTTP/1.1 200
    def __init__(self):
        self._access = logging.getLogger('boring.server')
        self._access.setLevel(logging.DEBUG)
        ch = logging.StreamHandler()
        ch.setLevel(logging.DEBUG)

        formatter = logging.Formatter(
            ' %(addr)s -- [%(asctime)s] %(method)s %(path)s %(proto)s %(code)s -- %(message)s'
        )
        ch.setFormatter(formatter)
        ##
        ### add ch to logger
        self._access.addHandler(ch)

        self._log = logging.getLogger('__')
        self._log.setLevel(logging.DEBUG)

    def access(self, req=None, resp=None):
        extras = {
            'method': '',
            "path": '',
            'code': '',
            'proto': '',
            'addr': ''
        }
        r = {}
        if req:
            r = {
                'method': req.method,
                'path': req.uri,
                'proto': req.proto,
                'addr': req.remote_addr
            }
            if resp:
                r.update({'code': resp.code})
        extras.update(r)
        self._access.info('', extra=extras)

    def log(self, message):
        self._log.info(message)


class SignalHandler:
    # more signals will be added
    def __init__(self, server):
        self.server = server

    def sigterm(self, *args):
        self.sigint(*args)

    def sigint(self, *args):
        print("[INFO] quiting server .......")
        self.server.shutdown()

    def unknown(self, *args):
        print('[INFO] ignoring unknown signal,', args[0])


class Server:
    def __init__(self, app=None, config=None, args=None):
        self.sel = selectors.DefaultSelector()
        self.sock = socket.socket()
        self.signals = ['SIGTERM', "SIGINT"]
        self.signal_class = SignalHandler(self)
        self.module = None
        self.app = app
        self.args = None
        self.log = Logger()
        self.stop = False
        self.config = config or DummyConfig()
        self._active_conns = {}
        self.started = False

    def init_socket(self):
        port = self.args.port
        addr = self.args.bind
        try:
            self.sock.bind((addr, int(port)))
        except OSError as e:
            print("[ERROR] could't bind to address %s:%s" % (addr, port), e)
            sys.exit(1)
        self.sock.listen(100)
        self.sock.setblocking(False)
        self.sel.register(self.sock, selectors.EVENT_READ,
                          self.handle_connection)

        print('[INFO] starting server on ', addr, 'port', port)

    def start(self):
        self.init()
        self.init_socket()
        print("[INFO]", 'server started, press control-c to stop')
        self.started = True
        reloader.start(self)
        while 1:
            events = self.sel.select(0)
            for key, _ in events:
                if key.fileobj is self.sock:

                    self.handle_connection(self.sock)
                else:
                    try:
                        self.handle_request(key.fileobj, key.data)
                    except socket.error:
                        self.close_connection(key.fileobj)
                    except Exception:
                        traceback.print_exc()
                        self.close_connection(key.fileobj)
                        #key.fileobj.send(b"h")
            self.manage_connections()

    def init_signals(self):
        for sig in self.signals:
            sig_func = getattr(self.signal_class, sig.lower(),
                               self.signal_class.unknown)
            sig = getattr(signal, sig, None)
            if sig:
                try:
                    signal.signal(sig, sig_func)
                except OSError:
                    continue

    def init(self):
        self.init_signals()
        args = self.create_args()
        self.check_reload_arg()
        if self.args.use_config:
            self.config = Config(self.args)
            self.config.load()
        if self.args.app == ".":
            self.module = DirectoryServer
        else:
            self.load_app()
        # self.start_reload()

    def check_reload_arg(self):
        if  not self.args.reload:
            return
        reload_proc = os.environ.get("BORING_RELOAD_PROC")
        if not reload_proc:
            # main process
                code = reloader.start_new_process()
                sys.exit(code)

    def load_app(self):
        self.app = wsgi.load_app(self.args)

    def create_args(self):
        args = utils.create_args()
        self.args = args
        return args

    def handle_connection(self, sock):
        try:
            conn, addr = sock.accept()
        except socket.error:
            return
        conn.setblocking(False)
        self.sel.register(conn,
                          selectors.EVENT_READ,
                          data=HTTPParser(conn, self, addr))
        self._active_conns[conn] = int(time.time())
        #self.sel.unregister(conn)

    def handle_request(self, conn, parser):
        #nn.close()
        try:
            parser = parser()
        except socket.error:
            self.close_connection(conn)
            return
        except HttpException as e:
            e.write_error(conn)
            self.close_connection(conn)
            return
        except Exception as e:
            self.close_connection(conn)
            traceback.print_exc()
            return
        if not parser.is_alive:
            # client close connection
            self.close_connection(conn)
            return
        if not parser.begin:
            #can't start processing the request.
            # client might be sending the request one by one
            return
        try:
            request = Request(parser)
            self.run(request, conn)
        except socket.error:
            self.close_connection(conn)
            return
        except HttpException as e:
            e.write_error(conn)
            self.close_connection(conn)
        except Exception as e:
            self.close_connection(conn)
            traceback.print_exc()

    def run(self, request, conn):
        if self.module:
            self.module(conn, request, self).run()
            self.close_connection(conn)
            return
        wsgiapp = WsgiApp(self.app, request, conn, self.log, self, self.config)
        wsgiapp.run()
        # wsgiapp = WsgiApp(self.app, request, conn, self, self.log,
        #                       self.config)
        #     wsgiapp.dispatch_request()

    def close_connection(self, conn):
        ''' Close the connection after serving the request '''
        if conn._closed:
            return
        try:
            self.sel.unregister(conn)
        except (ValueError, KeyError):  # raised by selectors.unregister
            pass
        try:
            conn.close()
        except OSError:
            pass
        with contextlib.suppress(KeyError):
            del self._active_conns[conn]

    def reuse_connection(self, conn, req):
        """ re-use connection for keep-alive header"""
        try:
            self.sel.unregister(conn)
            self.sel.register(conn,
                              selectors.EVENT_READ,
                              data=HTTPParser(conn, self, req.addr))
        except (KeyError, ValueError):
            self.close_connection(conn)
        else:
            self._active_conns[conn] = int(time.time())

    def manage_connections(self):
        '''  remove some connections that are inactive for some time'''
        active = self._active_conns.items()
        timeout_conns = []
        for conn, conn_time in active:
            if int(time.time()) - conn_time > 45:
                timeout_conns.append(conn)
        for conn in timeout_conns:
            self.close_connection(conn)

    def shutdown(self):
        ''' shutdown the server'''
        self.sock.close()
        self.sel.close()
        self.stop = True
        sys.exit(0)

