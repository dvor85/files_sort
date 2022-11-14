# -*- coding: utf-8 -*-

import os
import sys
import datetime
import re
import string
from pathlib import Path
import locale
import time
import shutil

PY2 = sys.version_info[0] == 2
__re_denied = re.compile(r'[^./\wА-яЁё-]|[./]{2}')
__re_spaces = re.compile(r'\s+')
fmt = string.Formatter().format


__all__ = ['md5sum', 'fileDatetime', 'datetimeFromMeta', 'safe_str', 'split', 'parse_str', 'str2num', 'str2int',
           'uniq', 'rListFiles', 'get_encoding', 'uni', 'fs_enc', 'get_comp_name', 'get_home_dir', 'get_temp_dir',
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
    return hashlib.md5(Path(path).read_bytes()).hexdigest()


def fileDatetime(path):
    """
    :return: Дата файла. Если изображение, то DateTimeOriginal из exif данных
    """

    def datetimeFromExif():
        from PIL import Image
        from PIL.ExifTags import TAGS

        exif = Image.open(path)._getexif()
        fields = dict((TAGS.get(k), v) for k, v in exif.items())
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


def safe_str(s):
    return __re_denied.sub('', uni(s))


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


def get_encoding(s):
    """
    Функция определения кодировки с помощью chardet, иначе
    locale.getpreferredencoding() или sys.getfilesystemencoding()
    :s: строка для определения кодировки
    :return: кодровка, None (если s - unicode)
    :ValueError: Если кодировка не определена
    """

    encoding = None
    if isinstance(s, bytes):
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
    :s: строка для декодирования
    :from_encoding: Кодировка из которой декодировать.
    :return: unicode
    """

    if isinstance(s, bytes):
        return s.decode(from_encoding, 'ignore')
    return str(s)


def utf(s, to_encoding='utf8'):
    """
    PY2 - Кодирует :s: в :to_encoding:
    """
    if isinstance(s, bytes):
        return s
    return str(s).encode(to_encoding, errors='ignore')


def fs_enc(path):
    """
    windows workaround. Используется в Popen.
    """
    return uni(path).encode(sys.getfilesystemencoding(), 'ignore')


def get_comp_name():
    __env_var = 'HOSTNAME'
    if sys.platform.startswith('win'):
        __env_var = 'COMPUTERNAME'
    return os.getenv(__env_var)


def get_home_dir():
    __env_var = 'HOME'
    if sys.platform.startswith('win'):
        __env_var = 'APPDATA'
    return os.getenv(__env_var)


def get_temp_dir():
    if sys.platform.startswith('win'):
        __env_var = 'TEMP'
        return os.getenv(__env_var)
    else:
        return "/tmp"


def mkdir(path, mode=0o775, parents=True, exist_ok=True):
    path = Path(path)
    if not path.is_dir():
        m = os.umask(0o000)
        path.mkdir(mode=mode, parents=parents, exist_ok=exist_ok)
        os.umask(m)


def rmdir(path):
    path = Path(path)
    shutil.rmtree(path.as_posix())
    return not path.exists()
