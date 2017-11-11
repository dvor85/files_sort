#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import unicode_literals
import subprocess
import os
import time
import locale
import tempfile
import argparse
import shutil
import shlex
from utils import *
import threading
try:
    import simplejson as json
except ImportError:
    import json


EXIF_PARAMS = ('DateTimeOriginal', 'CreateDate', 'ModifyDate', 'FileModifyDate', 'FileCreateDate')


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
        parser = argparse.ArgumentParser(prog='vconv.py', add_help=True)
        parser.add_argument('src_path',
                            help='Source path template')
        parser.add_argument('dst_path',
                            help='Destination path')
        parser.add_argument('--exiftool', '-e',
                            help='Path to exiftool', default='exiftool')
        parser.add_argument('--ffmpeg', '-f',
                            help='Path to ffmpeg', default='ffmpeg')
        parser.add_argument('--bitrate', '-b',
                            help='Video bitrate', default='5000k')
        parser.add_argument('--recode', '-r', action="store_true",
                            help='If set, then recode with libx264 and bitrate BITRATE, else only copy.')
        parser.add_argument('--overwrite', '-o', action="store_true",
                            help='If set, then source file will be overwriten by converted file, independent of destination path.')

        self.options = parser.parse_args()

    def __call__(self):
        return self.options


def isWebLink(s):
    return '://' in s


def main():
    options = Options.get_instance()()
    src_path = uni(options.src_path)
    dst_path = os.path.normpath(uni(options.dst_path))

    if not isWebLink(src_path):
        src_path = os.path.normpath(src_path)

        with tempfile.NamedTemporaryFile() as tmp:
            subprocess.call(shlex.split(fs_enc(
                fmt('"{exiftool}" -charset filename={charset} -q -m -fast -json -r "{path}"',
                    exif_params=" ".join(['-%s' % x for x in EXIF_PARAMS]),
                    exiftool=uni(options.exiftool),
                    s=src_path,
                    charset=locale.getpreferredencoding()))), stdout=tmp)
            tmp.seek(0)
            srclist = json.load(tmp)
    else:
        options.overwrite = False
        srclist = {'SourceFile': src_path}
    for meta in srclist:
        try:
            src_fn = uni(os.path.normpath(meta['SourceFile'])) if not isWebLink(meta['SourceFile']) else meta['SourceFile']
            if not isWebLink(src_fn) and (os.path.isdir(src_path) or os.path.isdir(dst_path)):
                dst_fn = os.path.join(dst_path, os.path.basename(src_fn))
            else:
                dst_fn = dst_path

            dst_fn = fmt("{f}{overwrite}.mp4", f=os.path.splitext(dst_fn)[0],
                         overwrite="_encoded_" if options.overwrite else "")

            print fmt("convert {src} -> {dst}", src=src_fn, dst=dst_fn)
            try:
                os.makedirs(os.path.dirname(dst_fn))
            except OSError:
                pass

            src_dt = datetimeFromMeta(meta, exif_params=EXIF_PARAMS)

            vcodec = "libx264 -b:v {bitrate}".format(bitrate=options.bitrate) if options.recode else "copy"
            subprocess.check_call(shlex.split(fs_enc(fmt('"{ffmpeg}" -loglevel error -threads auto -i "{src}" -c:v {vcodec} -c:a copy \
                                                                -metadata creation_time="{cdate}" "{dst}"',
                                                         ffmpeg=uni(options.ffmpeg),
                                                         vcodec=vcodec,
                                                         src=src_fn,
                                                         dst=dst_fn,
                                                         cdate=src_dt.strftime("%Y-%m-%d %H:%M:%S"))))
                                  )

            if not isWebLink(src_fn):
                subprocess.check_call(shlex.split(fs_enc(
                    fmt('"{exiftool}" -charset filename={charset} -overwrite_original -q -m -fast \
                                                                    -tagsfromfile "{src}" "{dst}"',
                        exiftool=uni(options.exiftool),
                        src=src_fn,
                        dst=dst_fn,
                        charset=locale.getpreferredencoding())))
                )

            os.utime(dst_fn, (time.mktime(src_dt.timetuple()), time.mktime(src_dt.timetuple())))
            if options.overwrite:
                shutil.move(dst_fn, src_fn)

        except Exception as e:
            print uni(e.message)


if __name__ == '__main__':
    main()
