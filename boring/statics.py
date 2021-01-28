""" This module  handles serving statics files. if the server is
    configure  to server static files.

    ::
        Upcoming in the later version

"""

import re

DATE_RE = re.compile(
    r'''(?P<week>[a-zA-Z]{3,}).?\s*
      (?P<day>[0-9]{2})\s*
      (?P<month>[a-zA-Z]+){3,}\s*
      (?P<year>[0-9]{4})\s*
      (?P<time>\d\d:\d\d:\d\d)

    ''', re.VERBOSE | re.IGNORECASE)


class StaticHandler:
    pass
    # def __init__(self,req,conn,config=None):
    #   pass

    # def _modified(self,file):
    #   ''' check if  the file has been modified '''
    #   # 'If-Modified-Since': 'Thu, 23 Apr 2020 21:00:22
    #   last_modified = os.stat(file).st_mtime
    #   cached_time = self.req.headers.get('If-Modified-Since')
    #   if not cached_time:
    #     return True
