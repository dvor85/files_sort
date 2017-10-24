#!/usr/bin/env python
# -*- coding: utf-8 -*-

import requests
import os
import utils
import argparse
import eyed3


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


def request(url, method='get', params=None, **kwargs):

    if not url:
        return
    kwargs.setdefault('allow_redirects', True)
    kwargs.setdefault('headers', {'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) \
            Chrome/45.0.2454.99 Safari/537.36'})
    kwargs.setdefault('timeout', 10)

    r = requests.request(method, url, params=params, **kwargs)
    r.raise_for_status()
    return r


def getBestImageOf(info):
    for im in info['image']:
        if im['size'] == 'extralarge':
            if im['#text'] != '':
                r = request(im['#text'])
                return {'img_data': r.content, 'mime_type': r.headers['Content-Type']}
    return {'img_data': None, 'mime_type': None}


def getGenres(info):
    return [g['name'] for g in info['tag']]


def trackSearch(title):
    params = PARAMS.copy()
    params['track'] = title
    params['method'] = 'track.search'
    params['limit'] = 1
    r = request(URL, params=params)
    ts = r.json()
    if ts.get('error'):
        raise ValueError(fmt("{msg}: {desc}", msg=ts.get('message'), desc=LFM_ERRORS[ts['error']]))
    if utils.str2int(ts['results']["opensearch:totalResults"]) == 0:
        raise ValueError('No tracks found')

    return dict(artist=ts['results']['trackmatches']['track'][0]['artist'],
                title=ts['results']['trackmatches']['track'][0]['name'])


def getInfo(title, artist=None):
    params = PARAMS.copy()
    params['track'] = title

    if not artist:
        ts = trackSearch(title)
        artist = ts['artist']
        title = ts.get('title', title)

    params['artist'] = artist
    params['track'] = title
    params['method'] = 'track.getinfo'
    params['autocorrect'] = 1

    r = request(URL, params=params)
    info = r.json()

    if info.get('error'):
        raise ValueError(fmt("{msg}: {desc}", msg=info.get('message'), desc=LFM_ERRORS[info['error']]))

    return dict(album=info['track']['album']['title'],
                image=getBestImageOf(info['track']['album']),
                artist=info['track']['artist']['name'],
                title=info['track']['name'],
                genres=getGenres(info['track']['toptags']))


def main():
    parser = create_parser()
    options = parser.parse_args()

    eyed3.log.setLevel("ERROR")

    src_path = os.path.normpath(utils.true_enc(options.src_path))
    srclist = utils.rListFiles(src_path)

    for f in srclist:
        try:
            src_fn = utils.true_enc(os.path.normpath(f))
            print fmt("{0:-^100s}", "-")
            print src_fn
            afile = eyed3.load(utils.uni(src_fn))
            info = getInfo(afile.tag.title, afile.tag.artist)

            afile.tag.artist = utils.uni(info['artist'])
            print fmt("artist = {artist}", artist=afile.tag.artist)

            afile.tag.title = utils.uni(info['title'])
            print fmt("title = {title}", title=afile.tag.title)

            afile.tag.album = utils.uni(info['album'])
            print fmt("album = {album}", album=afile.tag.album)

            for g in info['genres']:
                afile.tag.genre = utils.uni(g)
                if afile.tag.genre.id is not None:
                    print fmt("genre = {genre}", genre=afile.tag.genre.name)
                    break
            try:
                afile.tag.images.set(3, img_data=info['image']['img_data'], mime_type=info['image']['mime_type'], img_url=None)
            except Exception as e:
                print fmt("Error add image: {msg}", msg=utils.true_enc(e.message))

            afile.tag.save(encoding='utf8')

        except Exception as e:
            print utils.true_enc(e.message)


if __name__ == '__main__':
    main()
