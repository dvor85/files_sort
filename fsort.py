#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import unicode_literals
import os
import shutil
import time
import argparse
import subprocess
import tempfile
import locale
import shlex
import threading
from utils import *
try:
    import simplejson as json
except ImportError:
    import json


class Options():
    _instance = None
    _lock = threading.Lock()

    @staticmethod
    def get_instance():
        if Options._instance is None:
            with Options._lock:
                Options._instance = Options()
        return Options._instance

    def __init__(self):
        parser = argparse.ArgumentParser(prog='fsort.py', add_help=True)
        parser.add_argument('src_path',
                            help='Source path template')
        parser.add_argument('--directory-template', '-d',
                            help='Create directories with TEMPLATE. Default="%%Y-%%m"', default="%Y-%m")
        parser.add_argument('--filename-template', '-f',
                            help='Filename TEMPLATE. Default="%%Y-%%m-%%d_%%H-%%M-%%S"', default="%Y-%m-%d_%H-%M-%S")
        parser.add_argument('--recurse', '-r',
                            help='Recursively rescan source path', action='store_true')
        parser.add_argument('--exiftool', '-e',
                            help='Path to exiftool', default='exiftool')

        self.options = parser.parse_args()

    def __call__(self):
        return self.options


EXIF_PARAMS = ('DateTimeOriginal', 'CreateDate', 'ModifyDate', 'FileModifyDate', 'FileCreateDate')


def main():
    options = Options.get_instance()()

    src_path = os.path.normpath(uni(options.src_path))
    with tempfile.NamedTemporaryFile() as tmp:
        subprocess.call(shlex.split(fs_enc(
            fmt('"{exiftool}" -charset filename={charset} -q -m -fast \
             -json {recurse} "{path}"',
                exif_params=" ".join(['-%s' % x for x in EXIF_PARAMS]),
                exiftool=uni(options.exiftool),
                path=src_path,
                recurse='-r' if options.recurse else '',
                charset=locale.getpreferredencoding()))), stdout=tmp)
        tmp.seek(0)
        srclist = json.load(tmp)
    for meta in srclist:
        try:
            src_fn = uni(os.path.normpath(meta['SourceFile']))
            src_dt = datetimeFromMeta(meta, exif_params=EXIF_PARAMS)

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
                if os.path.getsize(src_fn) == os.path.getsize(dst_fn) and md5sum(src_fn) == md5sum(dst_fn):
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
            print uni(e.message)


if __name__ == '__main__':
    main()
