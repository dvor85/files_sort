#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import time
import argparse
import subprocess
import tempfile
import locale
import shlex
import threading
import utils
import json
from pathlib import Path
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
        parser = argparse.ArgumentParser(prog=Path('__file__').name, add_help=True)
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
        self.src_path = Path(self.options.src_path).absolute()
        self.gthumb_cat = {}
        self.gthumb_root = Path("~/.local/share/gthumb/catalogs").expanduser()

    def add_gthumb_catalog(self, fn, dt=None):
        _fn = Path(fn).absolute()
        if dt is None:
            dt = utils.fileDatetime(_fn)
        self.gthumb_cat.setdefault(dt.strftime(self.options.directory_template), []).append(_fn)

    def write_gthumb_catalogs(self):
        for dt, files in self.gthumb_cat.items():
            _y = dt[:4]
            _lines = []
            _fn = self.gthumb_root / _y / f"{dt}.catalog"
            _xml_b = f"""<?xml version="1.0" encoding="UTF-8"?>
<catalog version="1.0">
<date>{dt.replace('-', ':')} 00:00:00</date>
<files>\n"""
            if not self.options.create_ghtumb:
                if _fn.is_file():
                    _lines = [x.rstrip('\n') for x in _fn.read_text().splitlines() if 'file://' in x]
            for _f in files:
                _l = f'<file uri="{_f.as_uri()}" />'
                if _l not in _lines:
                    _lines.append(_l)

            utils.mkdir(self.gthumb_root / _y)
            with _fn.open(mode='w') as a_xml:
                a_xml.write(_xml_b)
                a_xml.write("\n".join(_lines))
                a_xml.write("\n</files>\n</catalog>")

    def write_gthumb_last_added(self):
        if len(self.gthumb_cat) > 0:
            name = "Добавленные {date}".format(date=datetime.datetime.today().strftime('%Y-%m-%d'))
            _xml_b = f"""<?xml version="1.0" encoding="UTF-8"?>
    <catalog version="1.0">
    <date>{datetime.datetime.today():%Y:%m:%d} 00:00:00</date>
    <name>{name}</name>
    <files>\n"""
            _fn = self.gthumb_root / f"{name}.catalog"
            _lines = []
            if not self.options.create_ghtumb:
                if _fn.is_file():
                    _lines = [x.rstrip('\n') for x in _fn.read_text().splitlines() if 'file://' in x]
            for files in self.gthumb_cat.values():
                for _f in files:
                    _l = f'<file uri="{_f.as_uri()}" />'
                    if _l not in _lines:
                        _lines.append(_l)

            with _fn.open(mode='w') as a_xml:
                a_xml.write(_xml_b)
                a_xml.write("\n".join(_lines))
                a_xml.write("\n</files>\n</catalog>")

    def main(self):
        src_path = Path(self.options.src_path).absolute()
        srclist = []
        with tempfile.NamedTemporaryFile() as tmp:
            subprocess.call(shlex.split(
                '"{exiftool}" -charset filename={charset} -q -m -fast \
                 -json {recurse} {exif_params} "{path}"'.format(
                    exif_params=" ".join(f'-{x}' for x in EXIF_PARAMS + ['SourceFile']),
                    exiftool=self.options.exiftool,
                    path=src_path,
                    recurse='-r' if self.options.recurse else '',
                    charset=locale.getpreferredencoding())), stdout=tmp)
            tmp.seek(0)
            if len(tmp.read(1)) > 0:
                tmp.seek(0)
                srclist = json.load(tmp)

        for meta in srclist:
            try:
                src_fn = Path(meta['SourceFile']).absolute()
                src_dt = utils.datetimeFromMeta(meta, exif_params=EXIF_PARAMS)
                if self.options.create_ghtumb:
                    self.add_gthumb_catalog(src_fn, src_dt)
                    os.utime(src_fn, (time.mktime(src_dt.timetuple()), time.mktime(src_dt.timetuple())))
                else:
                    folder_name = src_dt.strftime(self.options.directory_template)

                    if len(self.options.filename_template) > 0:
                        new_fn = f"{src_dt.strftime(self.options.filename_template)}{src_fn.suffix}"
                    else:
                        new_fn = src_fn.name

                    if src_path.is_dir():
                        dst_dir = src_path / folder_name
                    else:
                        dst_dir = src_path.parent / folder_name

                    try:
                        utils.mkdir(dst_dir)
                    except OSError:
                        pass

                    dst_fn = (dst_dir / new_fn).absolute()

                    i = 0
                    while dst_fn.is_file():
                        if src_fn.samefile(dst_fn):
                            break
                        if src_fn.stat().st_size == dst_fn.stat().st_size and utils.md5sum(src_fn) == utils.md5sum(dst_fn):
                            dst_fn.unlink()
                        else:
                            i += 1
                            dst_fn = dst_fn.with_name(f"{dst_fn.stem}-{i}{dst_fn.suffix}")
                    else:
                        src_fn.replace(dst_fn)
                        print(f"{src_fn} -> {dst_fn}")

                        try:
                            utils.rmdir(src_fn)
                        except OSError:
                            pass

                    self.add_gthumb_catalog(dst_fn, src_dt)
                    os.utime(dst_fn, (time.mktime(src_dt.timetuple()), time.mktime(src_dt.timetuple())))

            except Exception as e:
                print(e.message)


if __name__ == '__main__':
    fsort = Fsort()
    fsort.main()
    fsort.write_gthumb_catalogs()
    fsort.write_gthumb_last_added()
