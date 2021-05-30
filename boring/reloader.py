import subprocess
import sys
import os
import threading
import time
# use code 111 for reload


def start_new_process():
    while 1:
        argv = sys.argv
        env = os.environ.copy()
        env['BORING_RELOAD_PROC'] = 'true'
        code = subprocess.call(argv, env=env)
        if code == 3:
            continue
        print('returned ',code)
        return code


def start(server):
    def main():
        mtimes = {}
        while not server.started:
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
                    mtimes[mod] = s
                    os.kill(os.getpid(), 3)
            time.sleep(1)
    threading.Thread(target=main).start()