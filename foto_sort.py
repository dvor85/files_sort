# -*- coding: utf-8 -*-

import os
import shutil
import utils
import time
import argparse
import subprocess
import tempfile
import locale
try:
    import simplejson as json
except ImportError:
    import json


def create_parser():
    parser = argparse.ArgumentParser(prog='foto_sort.py', add_help=True)
    parser.add_argument('dir',
                        help='DIRECTORY for process')
    parser.add_argument('--directory-template', '-t',
                        help='Create directories with TEMPLATE. Default="%%Y-%%m"', default='%Y-%m')
    parser.add_argument('--filename-template', '-f',
                        help='Filename TEMPLATE. Default="%%Y-%%m-%%d_%%H-%%M-%%S"', default="%Y-%m-%d_%H-%M-%S")
    parser.add_argument('--exiftool', '-e',
                        help='Path to exiftool', default='exiftool')
    return parser


EXIF_PARAMS = ('DateTimeOriginal', 'CreateDate', 'ModifyDate', 'FileModifyDate', 'FileCreateDate')


def main():
    parser = create_parser()
    options = parser.parse_args()

    path = utils.true_enc(options.dir)
    with tempfile.NamedTemporaryFile() as tmp:
        subprocess.call(utils.fs_enc(
            u'"{exiftool}" -charset filename={charset} -q -m -fast \
             -json -r "{path}"'.format(
                exif_params=" ".join(['-%s' % x for x in EXIF_PARAMS]),
                exiftool=utils.true_enc(options.exiftool),
                path=path,
                charset=locale.getpreferredencoding())), stdout=tmp)
        tmp.seek(0)
        srclist = json.load(tmp)
    for meta in srclist:
        try:
            src_fn = utils.true_enc(os.path.normpath(meta['SourceFile']))
            src_dt = utils.datetimeFromMeta(meta, exif_params=EXIF_PARAMS)

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
            else:
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
