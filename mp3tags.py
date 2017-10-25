#!/usr/bin/env python
# -*- coding: utf-8 -*-

import requests
import os
import utils
import argparse
import eyed3
import threading
import time

fmt = utils.fmt


API_KEY = 'b25b959554ed76058ac220b7b2e0a026'
URL = 'http://ws.audioscrobbler.com/2.0/'
PARAMS = {'api_key': API_KEY, 'format': 'json'}

LFM_ERRORS = {
    2: "Invalid service - This service does not exist",
    3: "Invalid Method - No method with that name in this package",
    4: "Authentication Failed - You do not have permissions to access the service",
    5: "Invalid format - This service doesn't exist in that format",
    6: "Invalid parameters - Your request is missing a required parameter",
    7: "Invalid resource specified",
    8: "Operation failed - Something else went wrong",
    9: "Invalid session key - Please re-authenticate",
    10: "Invalid API key - You must be granted a valid key by last.fm",
    11: "Service Offline - This service is temporarily offline. Try again later.",
    13: "Invalid method signature supplied",
    16: "There was a temporary error processing your request. Please try again",
    26: "Suspended API key - Access for your account has been suspended, please contact Last.fm",
    29: "Rate limit exceeded - Your IP has made too many requests in a short period"
}


def create_parser():
    parser = argparse.ArgumentParser(prog='mp3tags.py', add_help=True)
    parser.add_argument('src_path',
                        help='Source path template')
    parser.add_argument('--exiftool', '-e',
                        help='Path to exiftool', default='exiftool')
    parser.add_argument('--eyed3',
                        help='Path to eyeD3', default='eyeD3')
    return parser


def request(url, method='get', params=None, sema=None, **kwargs):
    if sema:
        sema.acquire()
    try:
        params_str = "?" + "&".join((fmt("{0}={1}", *i)
                                     for i in params.iteritems())) if params is not None and method == 'get' else ""
#         print(fmt("{t} | {u}{p}", u=url, p=params_str, t=time.time()))
        if not url:
            return
        kwargs.setdefault('allow_redirects', True)
        kwargs.setdefault('headers', {'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) \
                Chrome/45.0.2454.99 Safari/537.36'})
        kwargs.setdefault('timeout', 10)

        r = requests.request(method, url, params=params, **kwargs)
        r.raise_for_status()
        return r
    finally:
        if sema:
            sema.release()


def getBestImageOf(info, sema=None):
    for im in info['image']:
        if im['size'] == 'extralarge':
            if im['#text'] != '':
                r = request(im['#text'], sema=sema)
                return {'img_data': r.content, 'mime_type': r.headers['Content-Type']}
    return {'img_data': None, 'mime_type': None}


def getGenres(info):
    return [g['name'] for g in info['tag']]


def artistGetInfo(artist, sema=None):
    if not artist:
        raise ValueError('Artist not set')
    params = PARAMS.copy()
    params['artist'] = artist
    params['method'] = 'artist.getinfo'

    r = request(URL, params=params, sema=sema)
    info = r.json()
    if info.get('error'):
        raise ValueError(fmt("{msg}: {desc}", msg=info.get('message'), desc=LFM_ERRORS[info['error']]))

    return dict(artist=info['artist']['name'],
                image=getBestImageOf(info['artist'], sema=sema),
                genres=getGenres(info['artist']['tags']))


def trackSearch(title, artist=None, sema=None):
    if not title:
        raise ValueError('Title not set')
    params = PARAMS.copy()
    params['track'] = title
    params['artist'] = artist if artist else ''
    params['method'] = 'track.search'
    params['limit'] = 10
    r = request(URL, params=params, sema=sema)
    ts = r.json()
    if ts.get('error'):
        raise ValueError(fmt("{msg}: {desc}", msg=ts.get('message'), desc=LFM_ERRORS[ts['error']]))
    if utils.str2int(ts['results']["opensearch:totalResults"]) == 0:
        raise ValueError('No tracks found')

    tracks = ts['results']['trackmatches']['track']
    for track in tracks:
        if artist and utils.lower(track['artist']) in utils.lower(artist):
            return dict(artist=track['artist'],
                        title=track['name'])

    return dict(artist=tracks[0]['artist'],
                title=tracks[0]['name'])


def trackGetInfo(title, artist=None, sema=None):
    if not title:
        raise ValueError('Title not set')
    params = PARAMS.copy()
    params['track'] = title

    if not artist:
        ts = trackSearch(title, artist, sema=sema)
        artist = ts['artist']
        title = ts.get('title', title)

    params['artist'] = artist
    params['track'] = title
    params['method'] = 'track.getinfo'
    params['autocorrect'] = 1

    r = request(URL, params=params, sema=sema)
    info = r.json()

    if info.get('error'):
        raise ValueError(fmt("{msg}: {desc}", msg=info.get('message'), desc=LFM_ERRORS[info['error']]))

    artist = info['track']['artist']['name']
    title = info['track']['name']
    if not info['track'].get('album'):
        ainfo = artistGetInfo(artist, sema=sema)
        album = ainfo['artist']
        image = ainfo['image']
        genres = ainfo['genres']
    else:
        album = info['track']['album']['title']
        image = getBestImageOf(info['track']['album'], sema=sema)
        genres = getGenres(info['track']['toptags'])

    return dict(album=album,
                image=image,
                artist=artist,
                title=title,
                genres=genres,
                )


class TimeLimitedSemaphore(threading._Semaphore):
    def __init__(self, value=1, perseconds=1, verbose=None):
        threading._Semaphore.__init__(self, value=value, verbose=verbose)
        self._perseconds = perseconds
        self._time = 0

    def acquire(self, blocking=1):
        rc = threading._Semaphore.acquire(self, blocking)
        if self._Semaphore__value == 0:
            self._time = time.time()
        dt = time.time() - self._time
        if dt < self._perseconds:
            if blocking:
                time.sleep(self._perseconds - dt)

        return rc


class updateThread(threading.Thread):
    def __init__(self, src_fn, sema):
        threading.Thread.__init__(self)
        self.daemon = False
        self.src_fn = src_fn
        self.sema = sema

    def run(self):
        try:
            afile = eyed3.load(utils.uni(self.src_fn))
            if not afile.tag.title:
                raise ValueError(fmt("{fn}: Tag title not set", fn=self.src_fn))
            info = trackGetInfo(afile.tag.title, afile.tag.artist, sema=self.sema)
            print(fmt("{0:-^100s}", "-"))
            print(self.src_fn)
            afile.tag.artist = utils.uni(info['artist'])
            print(fmt("artist = {artist}", artist=afile.tag.artist))

            afile.tag.title = utils.uni(info['title'])
            print(fmt("title = {title}", title=afile.tag.title))

            afile.tag.album = utils.uni(info['album'])
            print(fmt("album = {album}", album=afile.tag.album))

            for g in info['genres']:
                afile.tag.genre = utils.uni(g)
                if afile.tag.genre.id is not None:
                    print(fmt("genre = {genre}", genre=afile.tag.genre.name))
                    break
            try:
                afile.tag.images.set(3, img_data=info['image']['img_data'], mime_type=info['image']['mime_type'], img_url=None)
            except Exception as e:
                print("Error add image")

            afile.tag.save(encoding='utf8')

        except Exception as e:
            print(utils.true_enc(e.message))


def main():
    parser = create_parser()
    options = parser.parse_args()

    eyed3.log.setLevel("ERROR")

    src_path = os.path.normpath(utils.true_enc(options.src_path))
    srclist = utils.rListFiles(src_path)

    Tsema = TimeLimitedSemaphore(5, 1)
    Msema = threading.Semaphore(5)

    for f in srclist:
        try:
            with Msema:
                src_fn = utils.true_enc(os.path.normpath(f))
                updateThread(src_fn, Tsema).start()
        except Exception as e:
            print(utils.true_enc(e.message))


if __name__ == '__main__':
    main()
