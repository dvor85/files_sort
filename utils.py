# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, unicode_literals

import os
import sys
from cgi import parse_qs, escape
from UserDict import UserDict
import datetime
import re
import string
import fnmatch
import locale
import time
import datetime


__re_denied = re.compile(ur'[^./\wА-яЁё-]|[./]{2}', re.UNICODE | re.LOCALE)
__re_spaces = re.compile(r'\s+')
fmt = string.Formatter().format

__all__ = ['QueryParam', 'md5sum', 'fileDatetime', 'datetimeFromMeta', 'safe_str', 'split', 'parse_str', 'str2num', 'str2int',
           'uniq', 'rListFiles', 'get_encoding', 'uni', 'utf', 'true_enc', 'fs_enc', 'lower', 'get_comp_name', 'get_home_dir',
           'get_temp_dir', 'makedirs', 'fmt', 'strptime']


class QueryParam(UserDict):
    """
    Класс для представления переданных через wsgi параметров в виде словаря.
    """

    def __init__(self, environ, safe=False):
        self.safe = safe
        self.data = parse_qs(environ['QUERY_STRING'])
        if environ['REQUEST_METHOD'].upper() == 'POST':
            try:
                request_body_size = int(environ.get('CONTENT_LENGTH', 0))
            except ValueError:
                request_body_size = 0
            self.data.update(parse_qs(environ['wsgi.input'].read(request_body_size)))

    def __getitem__(self, key):
        val = UserDict.__getitem__(self, key)[0]
        if self.safe:
            return safe_str(val)
        return escape(val)


def strptime(date_string, sformat):
    try:
        return datetime.datetime.strptime(uni(date_string), sformat)
    except TypeError:
        return datetime.datetime(*(time.strptime(uni(date_string), sformat)))


def md5sum(path):
    """
    :return: md5 сумма файла
    """
    import hashlib
    return hashlib.md5(open(path, 'rb').read()).hexdigest()


def fileDatetime(path):
    """
    :return: Дата файла. Если изображение, то DateTimeOriginal из exif данных
    """

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
    """
    :return: Выбирает лучшую дату из переданных exif_params (список) из переданного словаря meta, полученного из exiftool
    """
    for x in exif_params:
        try:
            #             tms = meta[x].split('+')
            #             if len(tms) == 2:
            #                 tz = tms[1].split(':')
            #                 return datetime.datetime.strptime(tms[0], "%Y:%m:%d %H:%M:%S") + \
            #                     datetime.timedelta(hours=str2int(tz[0]), minutes=str2int(tz[1]))
            #             else:
            return datetime.datetime.strptime(meta[x][:19], "%Y:%m:%d %H:%M:%S")
        except Exception:
            pass
    return datetime.datetime.today()


def safe_str(s, encoding=None):
    """
    :return: Строка s с удаленными запрещенными символами соответствующими __re_denied
    :ValueError: Если кодировка не определена
    """
    if isinstance(s, str):
        if encoding is None:
            encoding = get_encoding(s)
        res = uni(s, encoding)
        return __re_denied.sub(u'', res).encode(encoding, 'ignore')
    else:
        return __re_denied.sub(u'', res)


def split(s, num=0):
    """
    :return: Разделяет строку s. Разделитель - пробельные символы
    """
    return __re_spaces.split(s, num)


def parse_str(s):
    """
    :return: parse s to int, float, bool or s
    """
    try:
        return int(s)
    except Exception:
        try:
            return float(s)
        except Exception:
            if lower(s) == "true":
                return True
            elif lower(s) == "false":
                return False
    return s


def str2num(s, default=0):
    """
    :return: Число (возможно с дробное или целое) из строки s либо default (если строка не может быть числом)
    """
    try:
        return int(s)
    except Exception:
        try:
            return float(s)
        except Exception:
            return default


def str2int(s, default=0):
    """
    :return: Целое число из строки s либо default (если строка не может быть целым числом)
    """
    try:
        return int(s)
    except Exception:
        return default


def uniq(seq):
    """
    :return: seq без дублей. Порядок сохраняется
    """
    noDupes = []
    [noDupes.append(i) for i in seq if i not in noDupes]
    return noDupes


def rListFiles(path, _pattern='*.*'):
    """
    :path: Директория или шаблон
    :_pattern: Необязательный параметр
    :return: Возвращает рекурсивный список файлов
    """
    files = []
    path = os.path.abspath(path)
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


def get_encoding(s):
    """
    Функция определения кодировки с помощью chardet, иначе
    locale.getpreferredencoding() или sys.getfilesystemencoding()
    :s: строка для определения кодировки
    :return: кодровка, None (если s - unicode)
    :ValueError: Если кодировка не определена
    """

    encoding = None
    if isinstance(s, str):
        try:
            import chardet
            stat = chardet.detect(s)
            if stat['confidence'] >= 0.99:
                encoding = stat['encoding']
            else:
                raise ValueError('Confidence less then 0.99')
        except Exception:
            encoding = locale.getpreferredencoding()
            if encoding is None:
                encoding = sys.getfilesystemencoding()
            if encoding is None:
                raise ValueError("Can't determine encoding")
    return encoding


def uni(s, encoding=None):
    """
    Декодирует строку из кодировки encoding
    :s: строка для декодирования
    :encoding: Кодировка из которой декодировать. Если не задана, то будет определена
    :return: unicode s
    :ValueError: Если кодировка не определена
    """

    if isinstance(s, str):
        if encoding is None:
            encoding = get_encoding(s)

        s = s.decode(encoding, 'ignore')
    return s


def utf(s):
    """
    Кодирует в utf8
    :ValueError: Если кодировка не определена
    """
    return uni(s).encode('utf8', 'ignore')


def true_enc(s, encoding=None):
    """
    Для файловых операций в windows нужен unicode.
    Для остальных - utf8
    :ValueError: Если кодировка не определена
    """
    if sys.platform.startswith('win'):
        return uni(s, encoding)
    return utf(s)


def fs_enc(s):
    """
    subprocess.Popen workaround.
    :ValueError: Если кодировка не определена
    """
    enc = sys.getfilesystemencoding()
    if enc is None:
        enc = get_encoding(s)
    return uni(s).encode(enc, 'ignore')


def lower(s, encoding=None):
    """
    :ValueError: Если кодировка не определена
    """
    if isinstance(s, str):
        if encoding is None:
            encoding = get_encoding(s)
        return uni(s, encoding).lower().encode(encoding, 'ignore')
    else:
        return s.lower()


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
