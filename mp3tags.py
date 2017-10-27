#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import unicode_literals
import requests
import os
import utils
import argparse
import eyed3
import threading
import time
import re
import psutil

fmt = utils.fmt


_re_filename = re.compile(r'(?P<artist>.*?)[\s_]*-+[\s_]*(?P<title>.*)',  re.UNICODE | re.LOCALE)
_re_strip = re.compile(r'\(.*?\)',  re.UNICODE | re.LOCALE)


def create_parser():
    parser = argparse.ArgumentParser(prog='mp3tags.py', add_help=True)
    parser.add_argument('src_path',
                        help='Source path template')
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


def _strip(s):
    return _re_strip.sub('', s)


class LastFM():
    ERRORS = {
        1: "This error does not exist",
        2: "Invalid service -This service does not exist",
        3: "Invalid Method - No method with that name in this package",
        4: "Authentication Failed - You do not have permissions to access the service",
        5: "Invalid format - This service doesn't exist in that format",
        6: "Invalid parameters - Your request is missing a required parameter",
        7: "Invalid resource specified",
        8: "Operation failed - Most likely the backend service failed. Please try again.",
        9: "Invalid session key - Please re-authenticate",
        10: "Invalid API key - You must be granted a valid key by last.fm",
        11: "Service Offline - This service is temporarily offline. Try again later.",
        12: "Subscribers Only - This station is only available to paid last.fm subscribers",
        13: "Invalid method signature supplied",
        14: "Unauthorized Token - This token has not been authorized",
        15: "This item is not available for streaming.",
        16: "The service is temporarily unavailable, please try again.",
        17: "Login: User requires to be logged in",
        18: "Trial Expired - This user has no free radio plays left. Subscription required.",
        19: "This error does not exist",
        20: "Not Enough Content - There is not enough content to play this station",
        21: "Not Enough Members - This group does not have enough members for radio",
        22: "Not Enough Fans - This artist does not have enough fans for for radio",
        23: "Not Enough Neighbours - There are not enough neighbours for radio",
        24: "No Peak Radio - This user is not allowed to listen to radio during peak usage",
        25: "Radio Not Found - Radio station not found",
        26: "API Key Suspended - This application is not allowed to make requests to the web services",
        27: "Deprecated - This type of request is no longer supported",
        29: "Rate Limit Exceded - Your IP has made too many requests in a short period, exceeding our API guidelines"
    }

    _instance = None
    _lock = threading.Lock()

    @staticmethod
    def get_instance(url='http://ws.audioscrobbler.com/2.0/', api_key='b25b959554ed76058ac220b7b2e0a026', sema=None):
        if LastFM._instance is None:
            with LastFM._lock:
                LastFM._instance = LastFM(url, api_key, sema)
        return LastFM._instance

    def __init__(self, url='http://ws.audioscrobbler.com/2.0/', api_key='b25b959554ed76058ac220b7b2e0a026', sema=None):
        self.sema = sema
        self.url = url
        self.api_key = api_key

    def getBestImageOf(self, info):
        try:
            for im in info['image']:
                if im['size'] == 'extralarge':
                    if im['#text'] != '':
                        r = request(im['#text'], sema=self.sema)
                        return {'img_data': r.content, 'mime_type': r.headers['Content-Type']}
        except Exception:
            return {'img_data': None, 'mime_type': None}

    def getGenres(self, info):
        return [g['name'] for g in info['tag']]

    def artistGetInfo(self, artist):
        if not artist:
            raise ValueError('Artist not set')
        params = dict(
            api_key=self.api_key,
            format='json',
            artist=artist,
            method='artist.getinfo')

        r = request(self.url, params=params, sema=self.sema)
        info = r.json()
        if info.get('error'):
            raise ValueError(fmt("{msg}: {desc}", msg=info.get('message'), desc=LastFM.ERRORS[info['error']]))

        return dict(artist=info['artist']['name'],
                    image=self.getBestImageOf(info['artist']),
                    genres=self.getGenres(info['artist']['tags']))

    def trackSearch(self, title, artist=None):
        if not title:
            raise ValueError('Title not set')
        params = dict(
            api_key=self.api_key,
            format='json',
            track=title,
            artist=artist if artist else '',
            method='track.search',
            limit=10)

        r = request(self.url, params=params, sema=self.sema)
        ts = r.json()
        if ts.get('error'):
            raise ValueError(fmt("{msg}: {desc}", msg=ts.get('message'), desc=LastFM.ERRORS[ts['error']]))
        if utils.str2int(ts['results']["opensearch:totalResults"]) == 0:
            raise ValueError('No tracks found')

        tracks = ts['results']['trackmatches']['track']
        if artist:
            for track in tracks:
                if utils.lower(track['artist']) in utils.lower(artist):
                    return dict(artist=track['artist'],
                                title=track['name'])

        return dict(artist=tracks[0]['artist'],
                    title=tracks[0]['name'])

    def trackGetInfo(self, title, artist=None):
        if not title:
            raise ValueError('Title not set')
        params = dict(
            api_key=self.api_key,
            format='json',
            artist=artist,
            track=title,
            method='track.getinfo',
            autocorrect=1)

        r = request(self.url, params=params, sema=self.sema)
        info = r.json()

        if info.get('error'):
            raise ValueError(fmt("{msg}: {desc}", msg=info.get('message'), desc=LastFM.ERRORS[info['error']]))

        return dict(
            artist=info['track']['artist']['name'],
            title=info['track']['name'],
            album=info['track']['album']['title'] if 'album' in info['track'] else '',
            genres=self.getGenres(info['track']['toptags']),
            image=self.getBestImageOf(info['track'].get('album')))


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


class setTagsThread(threading.Thread):
    TAG_COMMENT = r"Fetched from last.fm by mp3tags"

    def __init__(self, src_fn, tsema, msema):
        threading.Thread.__init__(self)
        self.daemon = False
        self.src_fn = src_fn
        self.sema = tsema
        self.msema = msema

    def getInfo(self, title, artist=None):
        lfm = LastFM.get_instance(sema=self.sema)
        if not artist:
            ts = lfm.trackSearch(title, artist)
            artist = ts['artist']
            title = ts['title']

        info = lfm.trackGetInfo(title, artist)

        if not info['album']:
            info.update(lfm.artistGetInfo(artist))
        elif not info['image']['img_data']:
            ainfo = lfm.artistGetInfo(artist)
            info['image'] = ainfo['image']
        elif not info['genres']:
            ainfo = lfm.artistGetInfo(artist)
            info['genres'] = ainfo['genres']

        return info

    def getInfoFromFilename(self):
        fn = _strip(os.path.splitext(os.path.basename(self.src_fn))[0].replace('_', ' '))
        art_title = _re_filename.search(fn)
        if art_title:
            return dict(title=art_title.group('title'),
                        artist=art_title.group('artist'))
        else:
            return dict(title=' '.join(f for f in fn.split(' ') if utils.str2num(f) == 0),
                        artist='')

    def run(self):
        try:
            afile = eyed3.load(self.src_fn)
            if not afile:
                raise ValueError('Unsupported file')
            if not afile.tag:
                afile.initTag()
            comment = afile.tag.comments
            if comment.get('') and comment.get('').text == setTagsThread.TAG_COMMENT:
                return

            title = afile.tag.title
            artist = afile.tag.artist
            if not title:
                fi = self.getInfoFromFilename()
                artist = fi['artist']
                title = fi['title']
            try:
                info = self.getInfo(title, artist)
            except Exception as e:
                info = self.getInfoFromFilename()
                print fmt("{fn}: {a} - {t}", fn=self.src_fn, a=info['artist'], t=info['title'])

            afile.tag.artist = utils.uni(info.get('artist', ''))
            afile.tag.title = utils.uni(info.get('title', ''))
            afile.tag.album = utils.uni(info.get('album', ''))

            for g in info.get('genres'):
                try:
                    afile.tag.genre = utils.uni(g)
                    if afile.tag.genre.id is not None:
                        break
                except Exception:
                    pass
            try:
                afile.tag.images.set(3, img_data=info['image']['img_data'],
                                     mime_type=info['image']['mime_type'], img_url=None)
            except Exception as e:
                print fmt("{fn}: {e}", fn=self.src_fn, e="Error add image")

            comment.set(setTagsThread.TAG_COMMENT, '')

            afile.tag.save(encoding='utf8')
        except Exception as e:
            print fmt("{fn}: {e}", fn=self.src_fn, e=e)
        finally:
            self.msema.release()


def main():
    parser = create_parser()
    options = parser.parse_args()

    eyed3.log.setLevel("ERROR")

    src_path = os.path.normpath(utils.uni(options.src_path))
    srclist = utils.rListFiles(src_path)

    Tsema = TimeLimitedSemaphore(5, 1)
    Msema = threading.Semaphore(psutil.cpu_count())

    for f in srclist:
        try:
            Msema.acquire()
            src_fn = utils.uni(os.path.normpath(f))
            setTagsThread(src_fn, Tsema, Msema).start()
        except Exception as e:
            Msema.release()
            print(utils.uni(e.message))


if __name__ == '__main__':
    main()
