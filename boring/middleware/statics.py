""" This module  handles serving statics files.
    if the server is configured  to serve static files.
    It is implemented as wsgi middleware

"""
import mimetypes
import os
import re
from datetime import datetime

from boring import __version__, utils

DATE_RE = re.compile(
    r'''
    # Thu, 23 Apr 2020 21:00:22
    (?P<week>[a-zA-Z]{3,}).?\s*
      (?P<day>[0-9]{2,4})\s*
      (?P<month>[a-zA-Z]){3,}\s*
      (?P<year>[0-9]{4})\s*
      (?P<time>\d\d:\d\d:\d\d)

    ''', re.VERBOSE | re.IGNORECASE)


class StaticsHandler:
    def __init__(self, app, req, config=None, log=None):
        self.req = req
        self.app = app
        self.config = config
        self.headers = [("Date", utils.http_date()), ('Connection', 'close'),
                        ('Server', "Boring-Server/%s" % __version__)]

        url = self.config.STATIC_URL
        if not url.endswith('/'):
            # do some padding here, so regex can match the url
            config.STATIC_URL += '/'
        self.static_url = self.config.STATIC_URL
        regex = self.static_url + '(?P<path>.+)'
        self.regex = re.compile(regex)
        self.static_dir = config.STATIC_ROOT
        self.log = log

    def has_changed(self, file):
        ''' check if  the file has been modified '''
        #  eg.  'If-Modified-Since': 'Thu, 23 Apr 2020 21:00:22
        last_modified = datetime.utcfromtimestamp(int(os.stat(file).st_mtime))
        cached_time = self.req.headers.get('If-Modified-Since')
        if not cached_time:
            return True
        cached_time = utils.parse_header_date(cached_time)
        if last_modified > cached_time:
            return True
        return False

    def get_file_path(self):
        match = self.regex.search(self.req.path)
        if match:
            path = match.group('path')
            path = os.path.join(self.static_dir, path)
            return path
        return ''

    def serve(self, env, start_response):
        path = self.get_file_path()
        if not os.path.exists(path) or not os.path.isfile(path):
            return self.resp_not_found(env, start_response)
        if not self.has_changed(path):
            return self.resp_not_modified(env, start_response)
        return self.serve_static(env, start_response, path)

    def resp_not_modified(self, env, start_response):
        headers = self.headers
        headers.append(("Content-Length", '0'))
        start_response('304 Not Modified', headers)
        return b''

    def resp_not_found(self, env, start_response):
        headers = self.headers
        headers.append(("Content-Length", '0'))
        start_response('404 Not Found', headers)
        return b''

    def serve_static(self, env, start_response, file):
        headers = self.headers
        last_modified = datetime.utcfromtimestamp(
            os.stat(file).st_mtime).strftime('%a, %d %b %y %H:%M:%S GMT')
        size = os.stat(file).st_size
        mime_type, _ = mimetypes.guess_type(file)
        if mime_type:
            self.headers.append(('Content-Type', mime_type))

        headers.extend([("Content-Length", str(size)),
                        ('Last-Modified', last_modified)])
        try:
            static = open(file, 'rb')
            #  the file will be closed once it is delivered ..
        except PermissionError:
            #  this is only error likely occurs here
            print(
                '[INFO]  PermissionError: permission denied while opening %s' %
                file)
            return self.resp_not_found(env, start_response)
        start_response('200 OK', headers)
        return static

    def __call__(self, env, start_response):
        if not self.req.path.startswith(self.static_url):
            return self.app(env, start_response)
        return self.serve(env, start_response)
