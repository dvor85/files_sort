# -*- coding: utf-8 -*-
# from __future__ import unicode_literals

import os
import sys
from cgi import parse_qs, escape
from UserDict import UserDict
import datetime
import re
import string
import fnmatch


__re_denied = re.compile(ur'[^./\wА-яЁё-]|[./]{2}', re.UNICODE | re.LOCALE)
__re_spaces = re.compile(r'\s+')
fmt = string.Formatter().format


class QueryParam(UserDict):

    def __init__(self, environ, safe=False):
        self.safe = safe
        self.data = parse_qs(environ['QUERY_STRING'])
        if environ['REQUEST_METHOD'].upper() == 'POST':
            try:
                request_body_size = int(environ.get('CONTENT_LENGTH', 0))
            except ValueError:
                request_body_size = 0
            self.data.update(
                parse_qs(environ['wsgi.input'].read(request_body_size)))

    def __getitem__(self, key):
        val = UserDict.__getitem__(self, key)[0]
        if self.safe:
            return safe_str(val)
        return escape(val)


def md5sum(path):
    import hashlib
    return hashlib.md5(open(path, 'rb').read()).hexdigest()


def fileDatetime(path):

    def datetimeFromExif():
        from PIL import Image
        from PIL.ExifTags import TAGS

        exif = Image.open(path)._getexif()
        fields = dict((TAGS.get(k), v) for k, v in exif.iteritems())
        return datetime.datetime.strptime(fields["DateTimeOriginal"], "%Y:%m:%d %H:%M:%S")

    def datetimeFromFS():
        return datetime.datetime.fromtimestamp(os.path.getmtime(path))

    try:
        return datetimeFromExif()
    except Exception:
        return datetimeFromFS()


def datetimeFromMeta(meta, exif_params):
    for x in exif_params:
        try:
            tms = meta[x].split('+')
            if len(tms) == 2:
                tz = tms[1].split(':')
                return datetime.datetime.strptime(tms[0], "%Y:%m:%d %H:%M:%S") + \
                    datetime.timedelta(hours=str2int(tz[0]), minutes=str2int(tz[1]))
            else:
                return datetime.datetime.strptime(meta[x][:19], "%Y:%m:%d %H:%M:%S")
        except Exception:
            pass
    return datetime.datetime.today()


def safe_str(s):
    res = s
    if not isinstance(res, unicode):
        res = res.decode('utf-8', errors='ignore')

    return utf(__re_denied.sub('', res))


def split(s, num=0):
    return __re_spaces.split(s, num)


def parse_str(s):
    try:
        return int(s)
    except:
        try:
            return float(s)
        except:
            if s.lower() == "true":
                return True
            elif s.lower() == "false":
                return False
    return s


def str2num(s, default=0):
    try:
        return int(s)
    except:
        try:
            return float(s)
        except:
            return default


def str2int(str_val, default=0):
    try:
        return int(str_val)
    except:
        return default


def uniq(seq):
    # order preserving
    noDupes = []
    [noDupes.append(i) for i in seq if i not in noDupes]
    return noDupes


def rListFiles(path, _pattern='*.*'):
    files = []
    path = os.path.abspath(os.path.normpath(path))
    if not os.path.isdir(path):
        pattern = os.path.basename(path)
        files += rListFiles(os.path.dirname(path), pattern)
    else:
        for f in os.listdir(path):
            if os.path.isdir(os.path.join(path, f)):
                files += rListFiles(os.path.join(path, f), _pattern)
            elif fnmatch.fnmatch(f, _pattern):
                files.append(os.path.join(path, f))
    return files


def uni(path, from_encoding=None):
    """
    Декодирует строку из кодировки encoding
    :path: строка для декодирования
    :from_encoding: Кодировка из которой декодировать. Если не задана, то sys.getfilesystemencoding()
    :return: unicode path
    """

    if isinstance(path, str):
        if from_encoding is None:
            from_encoding = sys.getfilesystemencoding()
        if from_encoding is None:
            from_encoding = 'utf8'
        path = path.decode(from_encoding, 'ignore')
    return path


def utf(path):
    """
    Кодирует в utf8
    """
    if isinstance(path, unicode):
        return path.encode('utf8', 'ignore')
    return path


def true_enc(path, from_encoding=None):
    """
    Для файловых операций в windows нужен unicode.
    Для остальных - utf8
    """
    if sys.platform.startswith('win'):
        return uni(path, from_encoding)
    return utf(path)


def fs_enc(path):
    """
    windows workaround. Используется в Popen.
    """
    enc = sys.getfilesystemencoding()
    if enc is None:
        enc = 'utf8'
    return uni(path).encode(enc, 'ignore')


def lower(s, from_encoding=None):
    return utf(uni(s, from_encoding).lower())


def get_comp_name():
    __env_var = 'HOSTNAME'
    if sys.platform.startswith('win'):
        __env_var = 'COMPUTERNAME'
    return true_enc(os.getenv(__env_var))


def get_home_dir():
    __env_var = 'HOME'
    if sys.platform.startswith('win'):
        __env_var = 'APPDATA'
    return true_enc(os.getenv(__env_var))


def get_temp_dir():
    if sys.platform.startswith('win'):
        __env_var = 'TEMP'
        return true_enc(os.getenv(__env_var))
    else:
        return "/tmp"


def makedirs(path, mode=0775):
    try:
        if not os.path.exists(path):
            os.makedirs(path, mode)
    except Exception as e:
        print e
