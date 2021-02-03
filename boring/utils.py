''' No function or class here yet'''
import argparse
import os
import time
from datetime import datetime

from boring import __version__

months = "Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec"
MONTHS = {}

_count = 1
for month in months.split():
    MONTHS[month] = _count
    _count += 1


def parse_header_date(date_str):
    #  'Thu, 23 Apr 2020 21:00:22 GMT
    # crude way to parse header date
    date_list = date_str.split()
    if len(date_list) == 6:
        _, day, month, year, _time, tzone = date_list
        hour, minute, second = map(int, _time.split(':'))
        if len(year) == 2:
            # most browser accept both 2-digit and 4-digit year
            year = '20' + year
        return datetime(int(year), int(MONTHS.get(month)), int(day), hour,
                        minute, second)
    else:
        return datetime.utcfromtimestamp(time.time())


def http_date():
    return datetime.utcnow().strftime("%a, %d %b %y %H:%M:%S GMT")


def create_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("app", help='wsgi app to load')
    parser.add_argument("-p",
                        "--port",
                        default=int(os.environ.get("PORT", 8000)),
                        help='port number to use, default 8000')
    parser.add_argument("--reload",
                        action='store_true',
                        help="enable auto reload")
    parser.add_argument('-b',
                        '--bind',
                        default='0.0.0.0',
                        help='bind to this address')
    parser.add_argument('--use-config',
                        action='store_true',
                        help='use configuration for boring')
    parser.add_argument('-v',
                        '--version',
                        version=__version__,
                        action='version')
    args = parser.parse_args()
    return args
