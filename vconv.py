#!/usr/bin/env python
# -*- coding: utf-8 -*-

import subprocess
import os
import time
import utils
import locale
import tempfile
import argparse
import shutil
try:
    import simplejson as json
except ImportError:
    import json


EXIF_PARAMS = ('DateTimeOriginal', 'CreateDate', 'ModifyDate', 'FileModifyDate', 'FileCreateDate')


def create_parser():
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
    return parser


def main():
    parser = create_parser()
    options = parser.parse_args()

    src_path = os.path.normpath(utils.true_enc(options.src_path))
    dst_path = os.path.normpath(utils.true_enc(options.dst_path))

    with tempfile.NamedTemporaryFile() as tmp:
        subprocess.call(utils.fs_enc(
            u'"{exiftool}" -charset filename={charset} -q -m -fast -json -r "{path}"'.format(
                exif_params=" ".join(['-%s' % x for x in EXIF_PARAMS]),
                exiftool=utils.true_enc(options.exiftool),
                path=src_path,
                charset=locale.getpreferredencoding())), stdout=tmp)
        tmp.seek(0)
        srclist = json.load(tmp)
    for meta in srclist:
        try:
            src_fn = utils.true_enc(os.path.normpath(meta['SourceFile']))
            if os.path.isdir(src_path) or os.path.isdir(dst_path):
                dst_fn = os.path.join(dst_path, os.path.basename(src_fn))
            else:
                dst_fn = dst_path

            dst_fn = u"{f}{overwrite}.mp4".format(f=os.path.splitext(dst_fn)[0],
                                                  overwrite="_encoded_" if options.overwrite else "")

            print u"convert {src} -> {dst}".format(src=src_fn, dst=dst_fn)
            try:
                os.makedirs(os.path.dirname(dst_fn))
            except OSError:
                pass

            src_dt = utils.datetimeFromMeta(meta, exif_params=EXIF_PARAMS)

            vcodec = "libx264 -b:v {bitrate}".format(bitrate=options.bitrate) if options.recode else "copy"
            subprocess.check_call(utils.fs_enc(u'"{ffmpeg}" -loglevel error -threads auto -i "{src}" -c:v {vcodec} -c:a copy \
                                                                -metadata creation_time="{cdate}" "{dst}"'.format(
                ffmpeg=utils.true_enc(options.ffmpeg),
                vcodec=vcodec,
                src=src_fn,
                dst=dst_fn,
                cdate=src_dt.strftime("%Y-%m-%d %H:%M:%S")))
            )

            subprocess.check_call(utils.fs_enc(
                u'"{exiftool}" -charset filename={charset} -overwrite_original -q -m -fast \
                                                                -tagsfromfile "{src}" "{dst}"'.format(
                    exiftool=utils.true_enc(options.exiftool),
                    src=src_fn,
                    dst=dst_fn,
                    charset=locale.getpreferredencoding()))
            )

            os.utime(dst_fn, (time.mktime(src_dt.timetuple()), time.mktime(src_dt.timetuple())))
            if options.overwrite:
                shutil.move(dst_fn, src_fn)

        except Exception as e:
            print utils.uni(e.message)


if __name__ == '__main__':
    main()