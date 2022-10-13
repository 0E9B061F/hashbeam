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

class DeleteError(Exception):
    pass

class DBError(Exception):
    pass

def eprint(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)

class ImgurHandler:
    def __init__(self, rc):
        self.rc = rc
        if not self.rc.has('imgur'):
            raise ConfigurationError("imgur handler configuration missing")
        self.conf = self.rc.get('imgur')
        if not 'client_id' in self.conf:
            raise ConfigurationError("client_id missing for imgur handler")
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
                if data['success']:
                    return {
                        'type': 'imgur',
                        'link': data['data']['link'],
                        'deletehash': data['data']['deletehash'],
                    }
                else:
                    raise UploadError('upload failed')
            else:
                raise UploadError('upload failed')
        except:
            raise UploadError('upload failed')

    def delete(self, item):
        try:
            dhash = item['deletehash']
        except IndexError:
            raise DeleteError('no deletion hash for upload. unable to delete')
        r = requests.delete(
            f'https://api.imgur.com/3/image/{dhash}',
            params=self.params
        )
        if r.status_code != 200:
            raise DeleteError('delete failed')
        data = json.loads(r.text)
        if not data['success']:
            raise DeleteError('delete failed')

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
        self.handler = self.getHandler(self.rc['handler'])

    def getHandler(self, name):
        if name not in handlers:
            raise ConfigurationError('invalid handler')
        return handlers[name](self)

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
        try:
            return self.data[hash]
        except:
            return None

    def insert(self, hash, item):
        self.data[hash] = item
        self.save()

    def remove(self, hash):
        self.data.pop(hash, None)
        self.save()

    def save(self):
        json.dump(self.data, open(self.path, 'w'))

    def print(self):
        for hash, item in self.data.items():
            print(f"{hash}: {item['link']}")

    def printHashes(self):
        for hash, item in self.data.items():
            print(hash)

class ImgDB:
    def __init__(self, rc):
        self.rc = rc
        self.hashdb = HashDB(HASHDB)

    def link(self, paths):
        links = []
        for path in paths:
            try:
                hash = self.hash(path)
                item = self.hashdb.get(hash)
                if not item:
                    item = self.rc.handler.upload(path)
                    self.hashdb.insert(hash, item)
                links.append(item['link'])
            except UploadError as e:
                eprint(f"ERROR: {e} ({path})")
        return links
  
    def linkHash(self, hashes):
        links = []
        for hash in hashes:
            try:
                item = self.hashdb.get(hash)
                if item:
                    links.append(item['link'])
                else:
                    raise DBError('hash not found')
            except DBError as e:
                eprint(f"ERROR: {e} ({hash})")
        return links

    def delete(self, hashes):
        out = []
        for hash in hashes:
            item = self.hashdb.get(hash)
            if item:
                try:
                    handler = self.rc.getHandler(item['type'])
                    handler.delete(item)
                    self.hashdb.remove(hash)
                    out.append(hash)
                except DeleteError as e:
                    eprint(f"ERROR: {e} ({hash})")
            else:
                eprint(f"ERROR: hash not found ({hash})")
        return out

    def deleteFile(self, paths):
        return self.delete([self.hash(path) for path in paths])

    def hash(self, path):
        md5 = hashlib.md5()
        with open(path, 'rb') as f:
            while True:
                data = f.read(BUFFER)
                if not data:
                    break
                md5.update(data)
        return md5.hexdigest()

    def list(self):
        self.hashdb.print()

    def listHashes(self):
        self.hashdb.printHashes()

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
        '-l',
        dest='list',
        action='store_true',
        default=False,
        help='List stored hashes',
    )
    parser.add_argument(
        '-d',
        dest='delete',
        action='store_true',
        default=False,
        help='Delete uploaded image',
    )
    parser.add_argument(
        '-H',
        dest='hash',
        action='store_true',
        default=False,
        help='Specify a stored item by its hash',
    )
    parser.add_argument(
        'path',
        metavar='PATH',
        type=str,
        nargs='*',
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
        path = args.stdin.read().splitlines()
    elif not args.list:
        eprint("ERROR: no input given")
        exit(1)
    else:
        path = []

    hash = path

    try:
        rc = RC(args.rcpath)
    except ConfigurationError as e:
        eprint(f"ERROR: run control malformed ({args.rcpath})")
        eprint(f"       {e}")
        exit(1)
    imgdb = ImgDB(rc)

    if args.list:
        if args.hash:
            imgdb.listHashes()
        else:
            imgdb.list()
        exit(0)

    if args.delete:
        if args.hash:
            hashes = imgdb.delete(hash)
        else:
            hashes = imgdb.deleteFile(path)
        hashes = [f"DELETED: {hash}" for hash in hashes]
        print("\n".join(hashes), end='')

    else:
        if args.hash:
            links = imgdb.linkHash(hash)
        else:
            links = imgdb.link(path)
        print("\n".join(links), end='')
