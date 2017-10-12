#!/usr/bin/env python
# -*- coding: utf-8 -*-

import subprocess
import os
import time
import utils
import locale
import tempfile
import argparse
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
    parser.add_argument('--recode', '-r', action="store_true",
                        help='If set, then recode with "libx264, bitrate 5000k", else only copy')
    return parser


def main():
    parser = create_parser()
    options = parser.parse_args()

    src_path = utils.true_enc(options.src_path)
    dst_path = utils.true_enc(options.dst_path)

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
            if os.path.isdir(src_path):
                dst_fn = os.path.join(dst_path, os.path.basename(src_fn))
            else:
                dst_fn = dst_path

            dst_fn = "%s.mp4" % os.path.splitext(dst_fn)[0]

            print u"convert {src} -> {dst}".format(src=src_fn, dst=dst_fn)
            try:
                os.makedirs(os.path.dirname(dst_fn))
            except OSError:
                pass

            src_dt = utils.datetimeFromMeta(meta, exif_params=EXIF_PARAMS)

            vcodec = "libx264 -b:v 5000k" if options.recode else "copy"
            subprocess.call(utils.fs_enc(u'"{ffmpeg}" -loglevel error -threads auto -i "{src}" -c:v {vcodec} -c:a copy \
                                                                -metadata creation_time="{cdate}" {dst}"'.format(
                ffmpeg=utils.true_enc(options.ffmpeg),
                vcodec=vcodec,
                src=src_fn,
                dst=dst_fn,
                cdate=src_dt.strftime("%Y-%m-%d %H:%M:%S")))
            )

            subprocess.call(utils.fs_enc(
                u'"{exiftool}" -charset filename={charset} -overwrite_original -p -q -m -fast \
                                                                -tagsfromfile "{src}" "{dst}"'.format(
                    exiftool=utils.true_enc(options.exiftool),
                    src=src_fn,
                    dst=dst_fn,
                    charset=locale.getpreferredencoding()))
            )

            os.utime(dst_fn, (time.mktime(src_dt.timetuple()), time.mktime(src_dt.timetuple())))

        except Exception as e:
            print utils.uni(e.message)


if __name__ == '__main__':
    main()
