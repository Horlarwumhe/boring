import argparse
import errno
import importlib
import logging
import os
import selectors
import signal
import socket
import sys
import threading
import traceback

from boring import wsgi
from boring.exception import HttpException
from boring.http import HTTPParser, Request
from boring.wsgi import WsgiApp


def create_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("app")
    parser.add_argument("-p", "--port", default=8000)
    parser.add_argument("--reload", action='store_true')
    parser.add_argument('-b', '--bind', default='127.0.0.1')
    args = parser.parse_args()
    return args


class Logger:
    # [23/Jan/2021 12:43:30] code 501, message Unsupported method ('POST')
    def __init__(self):
        logging.basicConfig(
            level=logging.DEBUG,
            format=
            '[%(asctime)s] %(method)s %(path)s %(proto)s %(code)s -- %(message)s',
            datefmt='%d/%m/%Y %H:%M:%S')

        self.log = logging

    def access(self, req=None, resp=None):
        extras = {'method': '', "path": '', 'code': '', 'proto': ''}
        r = {}
        if req:
            r = {
                'method': req.method,
                'path': req.uri,
                'proto': req.proto,
            }
            if resp:
                r.update({'code': resp.code})
        extras.update(r)
        self.log.info('', extra=extras)


class SignalHandler:
    def __init__(self, server):
        self.server = server

    def sigterm(self, *args):
        pass

    def sigint(self, *args):
        print("[INFO] quiting server .......")
        self.server.shutdown()

    def unknown(self, *args):
        print('[INFO] ignoring unknown signal,', args[0])


class Server:
    def __init__(self):
        self.sel = selectors.DefaultSelector()
        self.sock = socket.socket()
        self.signals = ['SIGTERM', "SIGINT"]
        self.signal_class = SignalHandler(self)
        self.app = None
        self.args = None
        self.active = []
        self.log = Logger()
        self.stop = False

    def init_socket(self):
        port = self.args.port
        addr = self.args.bind
        try:
            self.sock.bind((addr, int(port)))
        except OSError as e:
            print("[ERROR] could't bind to address %s:%s" % (addr, port), e)
        self.sock.listen(100)
        self.sock.setblocking(False)
        self.sel.register(self.sock, selectors.EVENT_READ,
                          self.handle_connection)

        print('[INFO] starting server on ', addr, 'port', port)

    def start(self):
        self.init()
        self.init_socket()
        print("[INFO]", 'server started, press control-c to stop')
        self.start_reload()
        while 1:
            events = self.sel.select(0)
            for key, mask in events:
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

    def init_signals(self):
        for sig in self.signals:
            sig_func = getattr(self.signal_class, sig.lower(),
                               self.signal_class.unknown)
            sig = getattr(signal, sig, None)
            if sig:
                signal.signal(sig, sig_func)

    def init(self):
        self.init_signals()
        self.args = create_args()
        self.load_app()
        # self.start_reload()

    def start_reload(self):
        if self.args.reload:
            threading.Thread(target=reload, args=[self]).start()
            print('[INFO] auto reload starting')

    def load_app(self):
        self.app = wsgi.load_app(self.args)

    def handle_connection(self, sock):
        conn, addr = sock.accept()
        conn.setblocking(False)
        self.sel.register(conn,
                          selectors.EVENT_READ,
                          data=HTTPParser(conn, self, addr))
        #self.sel.unregister(conn)

    def handle_request(self, conn, parser):
        #nn.close()
        try:
            parser = parser()
        except socket.error:
            pass
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
            wsgiapp = WsgiApp(self.app, request, conn, self, self.log)
            wsgiapp.dispatch_request()
        except socket.error:
            self.close_connection(conn)
            return
        except HttpException as e:
            e.write_error(conn)
            self.close_connection(conn)
        except Exception as e:
            self.close_connection(conn)
            #conn.recv(1000)
            traceback.print_exc()

    def handle_filechange(self, file):
        ''' this function is called from another thread when files change'''
        importlib.reload(file)
        self.load_app()

    def close_connection(self, conn):
        ''' Close the connection after serving the request '''
        if conn._closed:
            return
        try:
            self.sel.unregister(conn)
            conn.close()
        except (ValueError, KeyError):  # raised by selectors.unregister
            pass

    def reuse_connection(self, conn, req):
        """ re-use connection for keep-alive header"""
        try:
            self.sel.unregister(conn)
            self.sel.register(conn,
                              selectors.EVENT_READ,
                              data=HTTPParser(conn, self, req.addr))
        except (KeyError, ValueError):
            pass

    def shutdown(self):
        ''' shutdown the server'''
        self.sock.close()
        self.sel.close()
        self.stop = True
        sys.exit(0)

def reload(server):
    mtimes = {}
    for module_name, module in sys.modules.items():
        if hasattr(module, '__file__') and module.__file__ is not None:
            mtime = os.stat(module.__file__).st_mtime
            mtimes[module] = mtime
    while 1:
        for mod in mtimes:
            if server.stop:
                sys.exit(0)
            s = os.stat(mod.__file__).st_mtime
            if s > mtimes[mod]:
                print(mod.__file__, 'changed')
                mtimes[mod] = s
                try:
                    server.handle_filechange(mod)
                except Exception:
                    print("[CRITICAL] error loading file", mod.__file__)
                    traceback.print_exc()
