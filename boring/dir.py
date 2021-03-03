import os
import mimetypes

from boring.http import Response
from . import utils

TEMPLATE = '''
<h3> Directory Listing for /{current_path}</h3>
<ul>
<p> files <div style='text-align:center'>size</div>
{paths}
</ul>

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
            links.append('''
                    <li>
                        <a href="/%s">%s</a>
                        <div style='text-align:center'>%skb
                        </div>
                     </li>''' % (abspath, p, os.stat(abspath).st_size // 1024))

        links = '\n'.join(links)
        res = TEMPLATE.format(paths=links, current_path=path)
        header = [
            ("Content-Type", 'text/html'),
            ('Content-Length', len(res)),
        ]
        self.resp.start_response('200 OK', header)
        return [res.encode()]

    def open_file(self, path):

        length = os.stat(path).st_size
        header = []
        filetype, enc = mimetypes.guess_type(path)
        if filetype:
            header.append(('Content-Type', filetype))
        if length > 1_000_000:  # 1 MB
            content = open(path, 'rb')
            header.append(("Transfer-Encoding", 'chunked'))
        else:
            file = open(path, 'rb')
            content = [file.read()]
            file.close()
            header.append(("Content-Length", str(length)))

        # date = utils.http_date(os.stat(path).st_mtime)
        self.resp.start_response('200 OK', header)

        return content
