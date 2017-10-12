#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import argparse
import subprocess
import utils
import locale
import datetime


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

    src_path = utils.true_enc(options.path)
    srclist = utils.rListFiles(src_path)
    for src_fn in srclist:
        try:
            src_sdt = os.path.splitext(os.path.basename(src_fn))[0]
            src_dt = datetime.datetime.strptime(src_sdt, "%Y%m%d_%H%M%S")
            print u"set alldates={cdate} of {src}".format(src=src_fn, cdate=src_dt.strftime("%Y:%m:%d %H:%M:%S"))
            subprocess.call(utils.fs_enc(
                u'"{exiftool}" -charset filename={charset} -overwrite_original -p -q -m -fast -alldates="{cdate}" "{src}"'.format(
                    exiftool=utils.true_enc(options.exiftool),
                    src=utils.true_enc(src_fn),
                    cdate=src_dt.strftime("%Y:%m:%d %H:%M:%S"),
                    charset=locale.getpreferredencoding()))
            )
        except Exception as e:
            print utils.uni(e)


if __name__ == '__main__':
    main()
