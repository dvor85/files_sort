# -*- coding: utf-8 -*-

import os
import sys
import shutil
import utils
import time
import datetime
import argparse
import subprocess
import tempfile
try:
    import simplejson as json
except ImportError:
    import json


def create_parser():
    parser = argparse.ArgumentParser(prog='foto_sort.py', add_help=True)
    parser.add_argument('--dir', '-d', required=True,
                        help='DIRECTORY for process')
    parser.add_argument('--directory-template', '-t',
                        help='Create directories with TEMPLATE. Default="%%Y-%%m"', default='%Y-%m')
    parser.add_argument('--filename-template', '-f',
                        help='Filename TEMPLATE. Default="%%Y-%%m-%%d_%%H-%%M-%%S"', default="%Y-%m-%d_%H-%M-%S")
    parser.add_argument('--exiftool', '-e',
                        help='Path to exiftool', default='exiftool')
    return parser


def datetimeFromMeta(meta):
    src_dt = datetime.datetime.today()
    for k, v in meta.iteritems():
        try:
            if k != 'SourceFile':
                tms = v.split('+')
                if len(tms) == 2:
                    tz = tms.split(':')
                    sdt = datetime.datetime.strptime(tms[0], "%Y:%m:%d %H:%M:%S") + datetime.timedelta(hours=tz[0], minutes=tz[1])
                else:
                    sdt = datetime.datetime.strptime(v[:19], "%Y:%m:%d %H:%M:%S")
                if sdt < src_dt:
                    src_dt = sdt
        except Exception:
            pass
    return src_dt


def main():
    parser = create_parser()
    options = parser.parse_args()

    path = utils.true_enc(options.dir)
    with tempfile.NamedTemporaryFile() as tmp:
        subprocess.call(utils.fs_enc(
            u'"{exiftool}" -q -m -fast -time:all -json -r "{path}"'.format(
                exiftool=utils.true_enc(options.exiftool),
                path=path)), stdout=tmp)
        srclist = json.load(tmp, encoding='utf8')
    for meta in srclist:
        try:
            src_fn = utils.true_enc(os.path.normpath(meta['SourceFile']))
            src_dt = datetimeFromMeta(meta)

            folder_name = src_dt.strftime(options.directory_template)

            if len(options.filename_template) > 0:
                new_fn = u"{dt}{ext}".format(dt=src_dt.strftime(options.filename_template), ext=os.path.splitext(src_fn)[1])
            else:
                new_fn = os.path.basename(src_fn)

            dst_dir = os.path.join(path, folder_name)

            try:
                os.mkdir(dst_dir)
            except Exception:
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
                    dst_fn = u"{fn}-{i}{ext}".format(fn=split_fn[0], i=i, ext=split_fn[1])

            shutil.move(src_fn, dst_fn)
            print u"{src} -> {dst}".format(src=src_fn, dst=dst_fn)
            try:
                os.rmdir(os.path.dirname(src_fn))
            except OSError:
                pass

            os.utime(dst_fn, (time.mktime(src_dt.timetuple()), time.mktime(src_dt.timetuple())))

        except Exception as e:
            print utils.uni(e.message)


if __name__ == '__main__':
    main()
