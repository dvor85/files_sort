#!/usr/bin/env python
# -*- coding: utf-8 -*-

import subprocess
import requests
import os
import utils
import tempfile
import locale
import argparse
import shlex
try:
    import simplejson as json
except ImportError:
    import json

fmt = utils.fmt


API = 'b25b959554ed76058ac220b7b2e0a026'
URL = 'http://ws.audioscrobbler.com/2.0/'
PARAMS = dict(method='artist.getinfo',
              artist=None,
              api_key=API,
              format='json')

EXIF_PARAMS = ('Artist',)

TMP = os.path.join(os.path.dirname(__file__), 'tmp/')


def create_parser():
    parser = argparse.ArgumentParser(prog='fsort.py', add_help=True)
    parser.add_argument('src_path',
                        help='Source path template')
    parser.add_argument('--exiftool', '-e',
                        help='Path to exiftool', default='exiftool')
    parser.add_argument('--eyed3',
                        help='Path to eyeD3', default='eyeD3')
    return parser


def request(url, method='get', params=None, **kwargs):

    if not url:
        return
    kwargs.setdefault('allow_redirects', True)
    kwargs.setdefault('headers', {'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) \
            Chrome/45.0.2454.99 Safari/537.36'})
    kwargs.setdefault('timeout', 3.05)

    r = requests.request(method, url, params=params, **kwargs)
    r.raise_for_status()
    return r


def getArtistImage(name):
    PARAMS['artist'] = name

    aimagelist = [f for f in os.listdir(TMP) if utils.lower(os.path.splitext(f)[0]) == utils.lower(name)]
    if len(aimagelist) > 0:
        return utils.true_enc(os.path.join(TMP, aimagelist[0]))

    r = request(URL, params=PARAMS)
    artist = r.json()

    for im in artist['artist']['image']:
        if im['size'] == 'extralarge':
            reqimage = request(im['#text'])
            aimagepath = utils.true_enc(os.path.join(TMP, fmt("{f}{n}", f=name, n=os.path.splitext(im['#text'])[1])))
            with open(aimagepath, 'wb') as image:
                image.write(reqimage.content)
                return aimagepath


def main():
    parser = create_parser()
    options = parser.parse_args()

    src_path = os.path.normpath(utils.true_enc(options.src_path))

    with tempfile.NamedTemporaryFile() as tmp:
        subprocess.call(shlex.split(utils.fs_enc(
            fmt('"{exiftool}" -charset filename={charset} {exif_params} -q -m -fast \
             -json -r "{path}"',
                exif_params=" ".join(['-%s' % x for x in EXIF_PARAMS]),
                exiftool=utils.true_enc(options.exiftool),
                path=src_path,
                charset=locale.getpreferredencoding()))), stdout=tmp)
        tmp.seek(0)
        srclist = json.load(tmp)

    try:
        os.makedirs(TMP)
    except OSError:
        pass

    for meta in srclist:
        try:
            src_fn = utils.true_enc(os.path.normpath(meta['SourceFile']))
            imagepath = getArtistImage(meta['Artist'])

            subprocess.check_call(shlex.split(utils.fs_enc(
                fmt('"{eyed3}" -Q --fs-encoding {charset} --add-image "{image}":FRONT_COVER "{path}"',
                    eyed3=utils.true_enc(options.eyed3),
                    path=src_fn,
                    image=utils.true_enc(imagepath),
                    charset=locale.getpreferredencoding())))
            )
        except Exception as e:
            print utils.true_enc(e.message)


if __name__ == '__main__':
    main()
