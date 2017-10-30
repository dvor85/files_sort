#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import argparse
import subprocess
import utils
import locale
import os
import datetime
import time
import re
import shlex
import threading
import psutil

fmt = utils.fmt

_re_filename = re.compile(
    ur'(?P<Y>\d{4})[\s_.-]*(?P<m>\d{2})[\s_.-]*(?P<d>\d{2})[\s_.-]*(?P<H>\d{2})[\s_.-]*(?P<M>\d{2})[\s_.-]*(?P<S>\d{2})',
    re.UNICODE | re.LOCALE)


def create_parser():
    parser = argparse.ArgumentParser(prog='fn2exif.py', add_help=True)
    parser.add_argument('path',
                        help='Source path')
    parser.add_argument('--exiftool', '-e',
                        help='Path to exiftool', default='exiftool')

    return parser


class setTagsThread(threading.Thread):
    def __init__(self, src_fn, exiftool, msema):
        threading.Thread.__init__(self)
        self.daemon = False
        self.src_fn = utils.uni(src_fn)
        self.exiftool = utils.uni(exiftool)
        self.msema = msema

    def run(self):
        try:
            fn_m = _re_filename.search(self.src_fn)
            if fn_m:
                src_dt = datetime.datetime.strptime("{Y}{m}{d}{H}{M}{S}".format(
                    Y=fn_m.group('Y'),
                    m=fn_m.group('m'),
                    d=fn_m.group('d'),
                    H=fn_m.group('H'),
                    M=fn_m.group('M'),
                    S=fn_m.group('S'),
                ), "%Y%m%d%H%M%S")
                print fmt("set alldates={cdate} of {src}", src=self.src_fn, cdate=src_dt.strftime("%Y:%m:%d %H:%M:%S"))
                subprocess.check_call(shlex.split(utils.fs_enc(
                    fmt('"{exiftool}" -charset filename={charset} -overwrite_original -q -m -fast -alldates="{cdate}" "{src}"',
                        exiftool=self.exiftool,
                        src=self.src_fn,
                        cdate=src_dt.strftime("%Y:%m:%d %H:%M:%S"),
                        charset=locale.getpreferredencoding())))
                )
                os.utime(self.src_fn, (time.mktime(src_dt.timetuple()), time.mktime(src_dt.timetuple())))
        except Exception as e:
            print fmt("{fn}: {e}", fn=self.src_fn, e=e)
        finally:
            self.msema.release()


def main():
    parser = create_parser()
    options = parser.parse_args()

    Msema = threading.Semaphore(psutil.cpu_count())
    src_path = os.path.normpath(utils.uni(options.path))
    srclist = utils.rListFiles(src_path)
    for src_fn in srclist:
        try:
            Msema.acquire()
            setTagsThread(src_fn, options.exiftool, Msema).start()
        except Exception as e:
            Msema.release()
            print utils.uni(e.message)


if __name__ == '__main__':
    main()
