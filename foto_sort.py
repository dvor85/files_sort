# -*- coding: utf-8 -*-

import os
import shutil
import utils
import time
import datetime
import argparse
import subprocess
try:
    import simplejson as json
except ImportError:
    import json


EXIFTOOL = ur"d:\progs\exiftool\exiftool.exe"


def create_parser():
    parser = argparse.ArgumentParser(prog='foto_sort.py', add_help=True)
    parser.add_argument('--dir', '-d', required=True, help='DIRECTORY for process')
    parser.add_argument('--directory-template', '-t', help='Create directories with TEMPLATE. Default="%%Y-%%m"', default='%Y-%m')
    parser.add_argument('--dont-rename', '-r', action='store_true', help='Dont rename files')
    return parser


def main():
    parser = create_parser()
    options = parser.parse_args()

    path = utils.true_enc(options.dir)
    srclist = json.loads(utils.true_enc(subprocess.check_output(utils.fs_enc(
        u'"{exiftool}" -q -L -createdate -json -r "{path}"'.format(exiftool=EXIFTOOL, path=path)))))
    for item in srclist:
        try:
            src_fn = utils.true_enc(item['SourceFile'])
            src_dt = item['CreateDate']
            file_dt = datetime.datetime.strptime(src_dt, "%Y:%m:%d %H:%M:%S")

            folder_name = file_dt.strftime(options.directory_template)
            if not options.dont_rename:
                new_fn = u"{dt}{ext}".format(dt=file_dt.strftime("%Y-%m-%d %H-%M-%S"), ext=os.path.splitext(src_fn)[1])
            else:
                new_fn = os.path.basename(src_fn)

            dst_dir = os.path.join(path, folder_name)

            try:
                os.mkdir(dst_dir)
            except Exception:
                pass

            dst_fn = os.path.normpath(os.path.join(dst_dir, new_fn))
            split_fn = os.path.splitext(dst_fn)
            if os.path.normcase(os.path.normpath(src_fn)) != os.path.normcase(os.path.normpath(dst_fn)):
                i = 0
                while os.path.isfile(dst_fn):
                    if os.path.getsize(src_fn) == os.path.getsize(dst_fn) and utils.md5sum(src_fn) == utils.md5sum(dst_fn):
                        os.unlink(dst_fn)
                    else:
                        i += 1
                        dst_fn = u"{fn} ({i}){ext}".format(fn=split_fn[0], i=i, ext=split_fn[1])

                shutil.move(src_fn, dst_fn)
                print u"{src} -> {dst}".format(src=src_fn, dst=dst_fn)
                try:
                    os.rmdir(os.path.dirname(src_fn))
                except OSError:
                    pass

            os.utime(dst_fn, (time.mktime(file_dt.timetuple()), time.mktime(file_dt.timetuple())))

        except Exception as e:
            print utils.uni(e.message)


if __name__ == '__main__':
    main()
