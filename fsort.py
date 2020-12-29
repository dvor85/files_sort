#!/usr/bin/env python3
# -*- coding: utf-8 -*-

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
import json
import datetime


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
                            help='Recursively scan source path', action='store_true')
        parser.add_argument('--create_ghtumb', '-c',
                            help='Create gthumb catalog. Update modification date from exif.', action='store_true')
        parser.add_argument('--exiftool', '-e',
                            help='Path to exiftool', default='exiftool')

        self.options = parser.parse_args()

    def __call__(self):
        return self.options


EXIF_PARAMS = ['DateTimeOriginal', 'CreateDate', 'ModifyDate', 'FileModifyDate', 'FileCreateDate']


class Fsort():
    def __init__(self):
        self.options = Options.get_instance()()
        self.src_path = os.path.normpath(self.options.src_path)
        self.gthumb_cat = {}
        self.gthumb_root = os.path.expanduser("~/.local/share/gthumb/catalogs")

    def add_gthumb_catalog(self, fn, dt=None):
        if dt is None:
            dt = fileDatetime(fn)
        if dt.strftime('%Y-%m-%d') in self.gthumb_cat:
            self.gthumb_cat[dt.strftime('%Y-%m-%d')].append(fn)
        else:
            self.gthumb_cat[dt.strftime('%Y-%m-%d')] = [fn]

    def write_gthumb_catalogs(self):
        for dt, files in self.gthumb_cat.items():
            _y = dt[:4]
            _xml = """<?xml version="1.0" encoding="UTF-8"?>
<catalog version="1.0">
<date>{date} 00:00:00</date>
<files>\n""".format(date=dt.replace('-', ':'))
            for _f in files:
                _xml += '<file uri="file://{file}" />\n'.format(file=_f.replace('\\', '/').replace(':', ''))
            _xml += "</files>\n</catalog>"
            makedirs(os.path.join(self.gthumb_root, _y))
            with open(os.path.join(self.gthumb_root, _y, "{0}.catalog".format(dt)), mode='w', encoding='utf8') as a_xml:
                a_xml.write(_xml)

    def write_gthumb_last_added(self):
        if len(self.gthumb_cat) > 0:
            name = "добавленные {date}".format(date=datetime.datetime.today().strftime('%Y-%m-%d'))
            _xml = """<?xml version="1.0" encoding="UTF-8"?>
    <catalog version="1.0">
    <date>{date} 00:00:00</date>
    <name>{name}</name>
    <files>\n""".format(date=datetime.datetime.today().strftime('%Y:%m:%d'), name=name)
            for dt, files in self.gthumb_cat.items():
                for _f in files:
                    _xml += '<file uri="file://{file}" />\n'.format(file=_f.replace('\\', '/').replace(':', ''))
            _xml += "</files>\n</catalog>"
            with open(os.path.join(self.gthumb_root, "{0}.catalog".format(name)), mode='w', encoding='utf8') as a_xml:
                a_xml.write(_xml)

    def main(self):
        src_path = os.path.normpath(self.options.src_path)
        with tempfile.NamedTemporaryFile() as tmp:
            subprocess.call(shlex.split(fs_enc(
                '"{exiftool}" -charset filename={charset} -q -m -fast \
                 -json {recurse} {exif_params} "{path}"'.format(
                    exif_params=" ".join(['-%s' % x for x in EXIF_PARAMS + ['SourceFile']]),
                    exiftool=self.options.exiftool,
                    path=src_path,
                    recurse='-r' if self.options.recurse else '',
                    charset=locale.getpreferredencoding()))), stdout=tmp)
            tmp.seek(0)
            srclist = json.load(tmp)
        for meta in srclist:
            try:
                src_fn = os.path.abspath(meta['SourceFile'])
                src_dt = datetimeFromMeta(meta, exif_params=EXIF_PARAMS)
                if self.options.create_ghtumb:
                    self.add_gthumb_catalog(src_fn, src_dt)
                    os.utime(src_fn, (time.mktime(src_dt.timetuple()), time.mktime(src_dt.timetuple())))
                else:
                    folder_name = src_dt.strftime(self.options.directory_template)

                    if len(self.options.filename_template) > 0:
                        new_fn = "{dt}{ext}".format(dt=src_dt.strftime(self.options.filename_template),
                                                    ext=os.path.splitext(src_fn)[1])
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
                            dst_fn = "{fn}-{i}{ext}".format(fn=split_fn[0], i=i, ext=split_fn[1])
                    else:
                        shutil.move(src_fn, dst_fn)
                        print("{src} -> {dst}".format(src=src_fn, dst=dst_fn))

                        try:
                            os.rmdir(os.path.dirname(src_fn))
                        except OSError:
                            pass

                    self.add_gthumb_catalog(dst_fn, src_dt)
                    os.utime(dst_fn, (time.mktime(src_dt.timetuple()), time.mktime(src_dt.timetuple())))

            except Exception as e:
                print(uni(e.message))


if __name__ == '__main__':
    fsort = Fsort()
    fsort.main()
    fsort.write_gthumb_catalogs()
    fsort.write_gthumb_last_added()
