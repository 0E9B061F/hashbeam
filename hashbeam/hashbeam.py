import sys
import os
import argparse
import hashlib
import json
import pathlib
import requests
from xdg import xdg_config_home


HOME = os.path.join(xdg_config_home(), 'hashbeam')
HASHRC = os.path.join(HOME, 'hashrc.json')
HASHDB = os.path.join(HOME, 'hashdb.json')
BUFFER = 65536 * 10
API = 'https://api.imgur.com/3/image'


class ConfigurationError(Exception):
    pass

class UploadError(Exception):
    pass

def eprint(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)

class ImgurHandler:
    def __init__(self, rc):
        self.rc = rc
        if not self.rc.has('imgur'):
            raise ConfigurationError()
        self.conf = self.rc.get('imgur')
        if not 'client_id' in self.conf:
            raise ConfigurationError()
        self.params = dict(
            client_id=self.conf["client_id"]
        )

    def upload(self, path):
        file = open(path, 'rb')
        files = dict(
            image=(None, file),
            name=(None, ''),
            type=(None, 'file'),
        )
        try:
            r = requests.post(API, files=files, params=self.params)
            if (r.status_code == 200):
                data = json.loads(r.text)
                if (data['status'] == 200):
                    return data['data']['link']
                else:
                    raise UploadError()
            else:
                raise UploadError()
        except:
            raise UploadError()

handlers = {
    "imgur": ImgurHandler,
}

class RC:
    def __init__(self, path):
        if os.path.isfile(path):
            data = open(path, 'r')
            self.rc = json.load(data)
        else:
            self.rc = {}
        if "handler" not in self.rc:
            raise ConfigurationError('no handler configured')
        if self.rc['handler'] not in handlers:
            raise ConfigurationError('invalid handler')
        self.handler = handlers[self.rc['handler']](self)

    def has(self, prop):
        return prop in self.rc

    def get(self, prop):
        return self.rc[prop]

class HashDB:
    def __init__(self, path):
        self.path = path
        if os.path.isfile(self.path):
            data = open(self.path, 'r')
            self.data = json.load(data)
        else:
            self.data = {}

    def get(self, hash):
        if hash in self.data:
            return self.data[hash]
        else:
            return False

    def insert(self, hash, link):
        self.data[hash] = link
        self.save()

    def save(self):
        json.dump(self.data, open(self.path, 'w'))

class ImgDB:
    def __init__(self, rc):
        self.rc = rc
        self.hashdb = HashDB(HASHDB)

    def link(self, path):
        hash = self.hash(path)
        link = self.hashdb.get(hash)
        if link == False:
            try:
                link = self.rc.handler.upload(path)
            except UploadError:
                eprint('ERROR: upload failed')
                exit(1)
            self.hashdb.insert(hash, link)
        return link
  
    def hash(self, path):
        md5 = hashlib.md5()
        with open(path, 'rb') as f:
            while True:
                data = f.read(BUFFER)
                if not data:
                    break
                md5.update(data)
        return md5.hexdigest()

def execute():
    pathlib.Path(HOME).mkdir(parents=True, exist_ok=True)

    parser = argparse.ArgumentParser(description='Get a publicly hosted URL for an image on your harddrive.')
    parser.add_argument(
        '-c',
        dest='rcpath',
        type=str,
        nargs='?',
        default=HASHRC,
        help='Config file to read from',
    )
    parser.add_argument(
        'path',
        metavar='PATH',
        type=str,
        nargs='?',
        help='Image to link'
    )
    parser.add_argument(
        'stdin',
        nargs='?',
        type=argparse.FileType('r'),
        default=(None if sys.stdin.isatty() else sys.stdin),
        help='Read path from STDIN'
    )
    args = parser.parse_args()
    
    if args.path:
        path = args.path
    elif args.stdin:
        path = args.stdin.read().splitlines()[0]
    else:
        eprint("ERROR: no input given")
        exit(1)

    try:
        rc = RC(args.rcpath)
    except ConfigurationError:
        eprint(f"ERROR: run control malformed ({args.rcpath})")
        exit(1)
    imgdb = ImgDB(rc)
    link = imgdb.link(path)
    print(link, end='')
