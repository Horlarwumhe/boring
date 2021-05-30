'''serving directory on http.
   this works like `python -m http.server`

'''

import mimetypes
import os

from boring.exception import BadRequest
from boring.http import Response

from . import utils

TEMPLATE = '''
<h1> Directory listing for /{current_path}/</h1>
<table style="border-spacing:15px 0px;">
  <tr>
    <th><h2>files</h2></th>
    <th> <h2>size</h2> </th>
    <th> <h2> Type </h2>
  </tr>
  <tr><th><hr></th></tr>

      {paths}
</table>
'''


class DirectoryServer:
    def __init__(self, conn, request, server):
        self.log = server.log
        self.resp = Response(request, conn)
        self.request = request
        self.base_dir = os.path.abspath(os.getcwd())
        self.server = server
        self.conn = conn

    def serve(self):
        path = self.request.path.replace('/', '', 1)
        if path.startswith('/'):
            # avoid revealing system root directory
            raise BadRequest()
        if path == '':
            path = '.'
            resp = self.listdir(path)
        if os.path.exists(path):
            if os.path.isfile(path):
                resp = self.open_file(path)
            else:
                resp = self.listdir(path)
        else:
            resp = self.not_found(path)

        self.resp.write_response(resp)

        return [resp]

    def run(self):
        try:
            self.serve()
        except OSError as e:
            self.resp.start_response('403 Forbidden',
                                     [('Content-Length', len(str(e)))])
            r = [str(e).encode()]
            self.resp.write_response(r)
        self.log.access(self.request, self.resp)

    def check_modify(self):
        pass

    def not_found(self, path):
        self.resp.start_response('404 Not Found', [])
        return b'file not found %s' % path.encode(),

    def listdir(self, path):
        links = []
        if path == '.':
            directory = os.listdir()
        else:
            directory = os.listdir(path)
        for p in directory:
            abspath = os.path.join(path, p)
            _type = 'file' if os.path.isfile(abspath) else 'folder'
            links.append('''
                <tr>
                    <td style="font-size: 30px;">
                        <a href="/%s">%s</a>
                    </td>
                    <td> 
                       %s KB 
                    </td>
                    <td>
                    %s
                    </td>
                </tr>
                    ''' %
                         (abspath, p, os.stat(abspath).st_size // 1024, _type))

        links = '\n'.join(links)
        res = TEMPLATE.format(paths=links, current_path=path)
        res = res.encode()
        header = [
            ("Content-Type", 'text/html'),
            ('Content-Length', len(res)),
        ]
        self.resp.start_response('200 OK', header)
        return [res]

    def open_file(self, path):

        length = os.stat(path).st_size
        header = []
        filetype, enc = mimetypes.guess_type(path)
        if filetype:
            if enc:
                filetype = filetype + ', charset=%s' % enc
            header.append(('Content-Type', filetype))
        header.append(("Content-Length", str(length)))
        self.resp.start_response('200 OK', header)

        return open(path, 'rb')


# if __name__ == '__main__':
#     from boring.server import Server
