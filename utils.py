# -*- coding: utf-8 -*-
# from __future__ import unicode_literals

import os
import sys
from cgi import parse_qs, escape
from UserDict import UserDict
import re
import string


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
    import datetime

    def datetimeFromExif(path):
        from PIL import Image
        from PIL.ExifTags import TAGS

        exif = Image.open(path)._getexif()
        fields = dict((TAGS.get(k), v) for k, v in exif.iteritems())
        return datetime.datetime.strptime(fields["DateTimeOriginal"], "%Y:%m:%d %H:%M:%S")

    def datetimeFromFS(path):
        return datetime.datetime.fromtimestamp(os.path.getmtime(path))

    try:
        return datetimeFromExif(path)
    except Exception:
        return datetimeFromFS(path)


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


def str2num(s):
    try:
        return int(s)
    except:
        try:
            return float(s)
        except:
            return 0


def uniq(seq):
    # order preserving
    noDupes = []
    [noDupes.append(i) for i in seq if i not in noDupes]
    return noDupes


def rListFiles(path):
    files = []
    for f in os.listdir(path):
        if os.path.isdir(os.path.join(path, f)):
            files += rListFiles(os.path.join(path, f))
        else:
            files.append(os.path.join(path, f))
    return files


def uni(path):
    """
    Декодирует строку из кодировки файловой системы
    """
    if isinstance(path, str):
        path = path.decode(sys.getfilesystemencoding(), errors='ignore')
    return path


def utf(path):
    """
    Кодирует в utf8
    """
    if isinstance(path, unicode):
        return path.encode('utf8', errors='ignore')
    return path


def true_enc(path):
    """
    Для файловых операций в windows нужен unicode.
    Для остальных - utf8
    """
    if sys.platform.startswith('win'):
        return uni(path)
    return utf(path)


def fs_enc(path):
    """
    windows workaround. Используется в Popen.
    """
    return uni(path).encode(sys.getfilesystemencoding(), 'ignore')


def get_user_name():
    """
    If running on windows, first Try get username via _get_user_of_session2.
    If it failed, then try via get_user_of_session. Other get username from environment variable.
    """
    __env_var = 'USER'
    if sys.platform.startswith('win'):
        try:
            __env_var = 'USERNAME'
            sess = get_session_of_pid(os.getpid())
            try:
                sessuser = get_user_of_session(sess)
            except Exception:
                sessuser = os.getenv(__env_var)

            if len(sessuser) > 0:
                return true_enc(sessuser)

        except Exception:
            pass
    return true_enc(os.getenv(__env_var))


def get_session_of_pid(pid):
    try:
        return _get_session_of_pid2(pid)
    except Exception:
        try:
            return _get_session_of_pid(pid)
        except Exception:
            return 0


def get_user_of_session(sess):
    """
    Return Loggedon username of session via pywin32
    :sess: Logon session
    :return: Loggedon username
    """
    if sys.platform.startswith('win'):
        for sessdata in enumerate_logonsessions():
            try:
                if sessdata.get('Session') == sess:
                    if sessdata.get('UserName'):
                        return true_enc(sessdata.get('UserName'))
            except Exception:
                pass
    raise Exception(fmt('Session user of "{sess}" not defined', sess))


def _get_session_of_pid(pid):
    """
    Get logon session via tasklist
    :pid: process id
    :return: logon session or raise Exception
    """
    if sys.platform.startswith('win'):
        from subprocess import check_output
        tasklist = check_output(fmt('tasklist /fi "PID eq {pid}" /fo csv /nh', pid=pid), shell=True).splitlines()
        for t in tasklist:
            try:
                task = t.replace('"', '').split(',')
                if int(task[1]) == int(pid):
                    return int(task[3])
            except Exception:
                pass
        raise Exception(fmt('Session id of "{pid}" not defined', pid))


def _get_session_of_pid2(pid):
    """
    Returns the session ID for the process with the given ID.
    :pid: process id
    :return: logon session or raise Exception
    """
    if sys.platform.startswith('win'):
        from ctypes.wintypes import DWORD
        from ctypes import windll, byref
        sess = DWORD()
        try:
            result = windll.kernel32.ProcessIdToSessionId(DWORD(pid), byref(sess))
        except Exception:  # may be running on windows xp where no ProcessIdToSessionId function
            return 0L
        if not result:
            raise OSError(3, 'No such process')
        return sess.value


def _enumerate_logonsessions():
    """
    :return: generator dict(Session, UserName, LogonType)
    """
    if sys.platform.startswith('win'):
        import winreg
        branch = 'SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Authentication\\LogonUI\\SessionData'
        i = 0
        try:
            key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, branch, 0, winreg.KEY_READ | winreg.KEY_WOW64_64KEY)
            while True:
                key_sess = None
                try:
                    sess = winreg.EnumKey(key, i)
                    branch_sess = fmt("{0}\\{1}", branch, sess)
                    key_sess = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, branch_sess, 0, winreg.KEY_READ | winreg.KEY_WOW64_64KEY)
                    j = 0
                    while True:
                        try:
                            value = winreg.EnumValue(key_sess, j)
                            if value[0] in ('LoggedOnUsername', 'LoggedOnUser', 'LoggedOnSAMUser'):
                                if len(os.path.basename(value[1])) > 0:
                                    yield dict(Session=int(sess), UserName=os.path.basename(value[1]), LogonType=2)
                                    break
                            j += 1
                        except WindowsError:
                            break
                    i += 1
                except WindowsError:
                    break
                finally:
                    if key_sess:
                        winreg.CloseKey(key_sess)
        finally:
            if key:
                winreg.CloseKey(key)


def _enumerate_logonsessions2():
    """
    Enumerate logon sessions via pywin32
    """
    if sys.platform.startswith('win'):
        import win32security
        for s in win32security.LsaEnumerateLogonSessions():
            try:
                yield win32security.LsaGetLogonSessionData(s)
            except Exception:
                pass


def enumerate_logonsessions():
    try:
        for sessdata in _enumerate_logonsessions():
            yield sessdata
    except Exception:
        pass
    for sessdata in _enumerate_logonsessions2():
        yield sessdata


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
