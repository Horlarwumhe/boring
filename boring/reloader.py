import subprocess
import sys
import signal
import os
import threading
import time

def sig_winch(*args):
    sys.exit(111)


def start_new_process():
    while 1:
        argv = sys.argv
        env = os.environ.copy()
        env['BORING_RELOAD_PROC'] = 'true'
        try:
            code = subprocess.call(argv, env=env)
        except OSError as e:
            if e.errno in (2,193,8,13):
                py = os.path.basename(sys.executable)
                argv.insert(0,py)
                code = subprocess.call(argv, env=env)
            else:
                raise
        if code == 111:
            continue
        return code


def start(server):
    def main():
        mtimes = {}
        while not server.started:
            # wait till server starts
            if server.stop:
                sys.exit(0)
        print('[INFO] auto reload starting')
        mods = list(sys.modules.items()).copy()
        for module_name, module in mods:
            if hasattr(module, '__file__') and module.__file__ is not None:
                mtime = os.stat(module.__file__).st_mtime
                mtimes[module] = mtime
        while 1:
            for mod in mtimes:
                if server.stop:
                    #  signal from main thread to stop
                    sys.exit(0)
                s = os.stat(mod.__file__).st_mtime
                if s > mtimes[mod]:
                    print(mod.__file__, 'changed restarting')
                    os.kill(os.getpid(),signal.SIGWINCH)
                    break
            time.sleep(1)
    threading.Thread(target=main).start()

