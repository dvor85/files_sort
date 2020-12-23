# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, unicode_literals

import os
import sys
import datetime
import re
import string
import fnmatch
import locale
import time
import six

PY2 = sys.version_info[0] == 2
__re_denied = re.compile(r'[^./\wА-яЁё-]|[./]{2}')
__re_spaces = re.compile(r'\s+')
fmt = string.Formatter().format

__all__ = ['md5sum', 'fileDatetime', 'datetimeFromMeta', 'safe_str', 'split', 'parse_str', 'str2num', 'str2int',
           'uniq', 'rListFiles', 'get_encoding', 'uni', 'fs_enc',
           'makedirs', 'fmt', 'strptime']


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
    try:
        s = uni(s)
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


def cmp(a, b):  # @ReservedAssignment
    return (a > b) - (a < b)


def uni(s, from_encoding='utf8'):
    """
    Декодирует строку из кодировки encoding
    :path: строка для декодирования
    :from_encoding: Кодировка из которой декодировать.
    :return: unicode path
    """

    if isinstance(s, six.binary_type):
        return s.decode(from_encoding, 'ignore')
    return s


def str2(s, to_encoding='utf8'):
    """
    PY2 - Кодирует :s: в :to_encoding:
    """
    if PY2 and isinstance(s, unicode):
        return s.encode(to_encoding, 'ignore')
    return str(s)


def fs_enc(path, from_encoding='utf8'):
    """
    windows workaround. Используется в Popen.
    """
    if PY2:
        enc = sys.getfilesystemencoding()
        if enc is None:
            enc = 'utf8'
        return uni(path, from_encoding).encode(enc, 'ignore')
    return uni(path, from_encoding)


def makedirs(path, mode=0x0775):
    try:
        if not os.path.exists(path):
            os.makedirs(path, mode)
    except Exception as e:
        print(e)
