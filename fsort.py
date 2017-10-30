#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import unicode_literals
import os
import shutil
import utils
import time
import argparse
import subprocess
import tempfile
import locale
import shlex
try:
    import simplejson as json
except ImportError:
    import json

fmt = utils.fmt


def create_parser():
    parser = argparse.ArgumentParser(prog='fsort.py', add_help=True)
    parser.add_argument('src_path',
                        help='Source path template')
    parser.add_argument('--directory-template', '-d',
                        help='Create directories with TEMPLATE. Default="%%Y-%%m"', default="%Y-%m")
    parser.add_argument('--filename-template', '-f',
                        help='Filename TEMPLATE. Default="%%Y-%%m-%%d_%%H-%%M-%%S"', default="%Y-%m-%d_%H-%M-%S")
    parser.add_argument('--exiftool', '-e',
                        help='Path to exiftool', default='exiftool')
    return parser


EXIF_PARAMS = ('DateTimeOriginal', 'CreateDate', 'ModifyDate', 'FileModifyDate', 'FileCreateDate')


def main():
    parser = create_parser()
    options = parser.parse_args()

    src_path = os.path.normpath(utils.uni(options.src_path))
    with tempfile.NamedTemporaryFile() as tmp:
        subprocess.call(shlex.split(utils.fs_enc(
            fmt('"{exiftool}" -charset filename={charset} -q -m -fast \
             -json -r "{path}"',
                exif_params=" ".join(['-%s' % x for x in EXIF_PARAMS]),
                exiftool=utils.uni(options.exiftool),
                path=src_path,
                charset=locale.getpreferredencoding()))), stdout=tmp)
        tmp.seek(0)
        srclist = json.load(tmp)
    for meta in srclist:
        try:
            src_fn = utils.uni(os.path.normpath(meta['SourceFile']))
            src_dt = utils.datetimeFromMeta(meta, exif_params=EXIF_PARAMS)

            folder_name = src_dt.strftime(options.directory_template)

            if len(options.filename_template) > 0:
                new_fn = fmt("{dt}{ext}", dt=src_dt.strftime(options.filename_template), ext=os.path.splitext(src_fn)[1])
            else:
                new_fn = os.path.basename(src_fn)

            if os.path.isdir(src_path):
                dst_dir = os.path.join(src_path, folder_name)
            else:
                dst_dir = os.path.join(os.path.dirname(src_path), folder_name)

            try:
                os.mkdir(dst_dir)
            except OSError:
                pass

            dst_fn = os.path.normpath(os.path.join(dst_dir, new_fn))
            split_fn = os.path.splitext(dst_fn)

            i = 0
            while os.path.isfile(dst_fn):
                if shutil._samefile(src_fn, dst_fn):
                    break
                if os.path.getsize(src_fn) == os.path.getsize(dst_fn) and utils.md5sum(src_fn) == utils.md5sum(dst_fn):
                    os.unlink(dst_fn)
                else:
                    i += 1
                    dst_fn = fmt("{fn}-{i}{ext}", fn=split_fn[0], i=i, ext=split_fn[1])
            else:
                shutil.move(src_fn, dst_fn)
                print fmt("{src} -> {dst}", src=src_fn, dst=dst_fn)

                try:
                    os.rmdir(os.path.dirname(src_fn))
                except OSError:
                    pass

                os.utime(dst_fn, (time.mktime(src_dt.timetuple()), time.mktime(src_dt.timetuple())))

        except Exception as e:
            print utils.uni(e.message)


if __name__ == '__main__':
    main()
