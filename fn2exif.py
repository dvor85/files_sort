#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import subprocess
import locale
import os
import time
import re
import shlex
import threading
import psutil
from pathlib import Path
import utils


_re_filename = re.compile(
    r'(?P<Y>\d{4})[\s_.-]*(?P<m>\d{2})[\s_.-]*(?P<d>\d{2})[\s_.-]*(?P<H>\d{2})[\s_.-]*(?P<M>\d{2})[\s_.-]*(?P<S>\d{2})')


class setTagsThread(threading.Thread):
    def __init__(self, src_fn, msema):
        threading.Thread.__init__(self)
        self.daemon = False
        self.options = Options.get_instance()()
        self.src_fn = Path(src_fn)
        self.exiftool = Path(self.options.exiftool)
        self.msema = msema

    def run(self):
        try:
            fn_m = _re_filename.search(self.src_fn)
            if fn_m:
                src_dt = utils.strptime("{Y}{m}{d}{H}{M}{S}".format(
                    Y=fn_m.group('Y'),
                    m=fn_m.group('m'),
                    d=fn_m.group('d'),
                    H=fn_m.group('H'),
                    M=fn_m.group('M'),
                    S=fn_m.group('S'),
                ), "%Y%m%d%H%M%S")
                print("set alldates={cdate} of {src}".format(src=self.src_fn, cdate=src_dt.strftime("%Y:%m:%d %H:%M:%S")))
                if not self.options.timeonly:
                    subprocess.check_call(shlex.split(
                        f'"{self.exiftool}" -charset filename={locale.getpreferredencoding()} -overwrite_original -q -m -fast \
                        -alldates="{src_dt:%Y:%m:%d %H:%M:%S}" "{self.src_fn}"'))

                os.utime(self.src_fn, (time.mktime(src_dt.timetuple()), time.mktime(src_dt.timetuple())))
        except Exception as e:
            print(f"{self.src_fn}: {e}")
        finally:
            self.msema.release()


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
        parser.add_argument('path',
                            help='Source path')
        parser.add_argument('--timeonly', '-t', action='store_true', default=False,
                            help='Update only modified time')
        parser.add_argument('--exiftool', '-e',
                            help='Path to exiftool', default='exiftool')

        self.options = parser.parse_args()

    def __call__(self):
        return self.options


def main():
    options = Options.get_instance()()

    Msema = threading.Semaphore(psutil.cpu_count())
    src_path = Path(options.path)
    for src_fn in src_path.rglob('*'):
        try:
            Msema.acquire()
            setTagsThread(src_fn, Msema).start()
        except Exception as e:
            Msema.release()
            print(e.message)


if __name__ == '__main__':
    main()
