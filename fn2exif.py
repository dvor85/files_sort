#!/usr/bin/env python
# -*- coding: utf-8 -*-

import argparse
import subprocess
import utils
import locale
import os
import datetime
import time
import re
import shlex

fmt = utils.fmt

__re_filename = re.compile(
    ur'(?P<Y>\d{4})[\s_.-]*(?P<m>\d{2})[\s_.-]*(?P<d>\d{2})[\s_.-]*(?P<H>\d{2})[\s_.-]*(?P<M>\d{2})[\s_.-]*(?P<S>\d{2})',
    re.UNICODE | re.LOCALE)


def create_parser():
    parser = argparse.ArgumentParser(prog='fn2exif.py', add_help=True)
    parser.add_argument('path',
                        help='Source path')
    parser.add_argument('--exiftool', '-e',
                        help='Path to exiftool', default='exiftool')

    return parser


def main():
    parser = create_parser()
    options = parser.parse_args()

    src_path = os.path.normpath(utils.true_enc(options.path))
    srclist = utils.rListFiles(src_path)
    for src_fn in srclist:
        try:
            fn_m = __re_filename.search(utils.uni(src_fn))
            if fn_m:
                src_dt = datetime.datetime.strptime("{Y}{m}{d}{H}{M}{S}".format(
                    Y=fn_m.group('Y'),
                    m=fn_m.group('m'),
                    d=fn_m.group('d'),
                    H=fn_m.group('H'),
                    M=fn_m.group('M'),
                    S=fn_m.group('S'),
                ), "%Y%m%d%H%M%S")
                print fmt("set alldates={cdate} of {src}", src=src_fn, cdate=src_dt.strftime("%Y:%m:%d %H:%M:%S"))
                subprocess.check_call(shlex.split(utils.fs_enc(
                    fmt('"{exiftool}" -charset filename={charset} -overwrite_original -q -m -fast -alldates="{cdate}" "{src}"',
                        exiftool=utils.true_enc(options.exiftool),
                        src=utils.true_enc(src_fn),
                        cdate=src_dt.strftime("%Y:%m:%d %H:%M:%S"),
                        charset=locale.getpreferredencoding())))
                )
                os.utime(src_fn, (time.mktime(src_dt.timetuple()), time.mktime(src_dt.timetuple())))
        except Exception as e:
            print utils.uni(e)


if __name__ == '__main__':
    main()
