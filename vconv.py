#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import subprocess
import os
import time
import locale
import tempfile
import argparse
import shutil
import shlex
import utils
from pathlib import Path
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
        parser = argparse.ArgumentParser(prog=Path('__file__').name, add_help=True)
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
        parser.add_argument('--accel', '-a', action="store_true",
                            help='If set, use hardware acceleration.')
        parser.add_argument('--overwrite', '-o', action="store_true",
                            help='If set, then source file will be overwriten by converted file, independent of destination path.')

        self.options = parser.parse_args()

    def __call__(self):
        return self.options


def main():
    options = Options.get_instance()()
    src_path = options.src_path
    dst_path = Path(options.dst_path).absolute()
    overwrite = "_encoded_" if not options.overwrite else ""

    with tempfile.NamedTemporaryFile() as tmp:
        subprocess.call(shlex.split(
            f'"{options.exiftool}" -charset filename={locale.getpreferredencoding()} ' +
            " ".join(f"-{x}" for x in EXIF_PARAMS + ("SourceFile", "MIMEType", "AvgBitrate")) +
            f' -q -m -fast -json -r "{src_path}"'), stdout=tmp)
        tmp.seek(0)
        srclist = json.load(tmp)

    for meta in srclist:
        if 'video' in meta['MIMEType']:
            try:
                if "mp4" not in meta['MIMEType'] or float(meta.get("AvgBitrate", "0 0").split()[0]) * 1024 > float(options.bitrate[:-1]):
                    src_fn = Path(meta['SourceFile']).absolute()
                    dst_fn = dst_path / f"{src_fn.stem}{overwrite}.mp4"
                    print(f"convert {src_fn} -> {dst_fn}")
                    utils.mkdir(dst_fn.parent)
                    src_dt = utils.datetimeFromMeta(meta, exif_params=EXIF_PARAMS)

                    accel = ""
                    if not options.recode:
                        vcodec = "copy"
                    elif options.accel:
                        vcodec = f"h264_vaapi -b:v {options.bitrate}"
                        accel = "-hwaccel vaapi -hwaccel_device /dev/dri/renderD128 -hwaccel_output_format vaapi"
                    else:
                        vcodec = f"libx264 -b:v {options.bitrate}"
                    overwr = '-y' if options.overwrite else ''
                    subprocess.check_call(shlex.split(f'"{options.ffmpeg}" {overwr} -loglevel error \
                                                            -threads auto {accel} -i "{src_fn}" -c:v {vcodec} -c:a copy \
                                                            -metadata creation_time="{src_dt:%Y-%m-%d %H:%M:%S}" "{dst_fn}"'))
                    subprocess.check_call(shlex.split(f'"{options.exiftool}" -charset filename={locale.getpreferredencoding()} -overwrite_original -q -m -fast \
                                                                            -tagsfromfile "{src_fn}" "{dst_fn}"'))

                    os.utime(dst_fn, (time.mktime(src_dt.timetuple()), time.mktime(src_dt.timetuple())))
                    if options.overwrite:
                        dst_fn.replace(src_fn)

            except Exception as e:
                print(e)


if __name__ == '__main__':
    main()
