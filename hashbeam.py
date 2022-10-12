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

class RC:
    def __init__(self, path):
        if os.path.isfile(path):
            data = open(path, 'r')
            self.rc = json.load(data)
        else:
            self.rc = {}
        if "client_id" not in self.rc:
            raise ConfigurationError("run control malformed")

    def get(self, prop):
        return self.rc[prop]

class ImgDB:
    def __init__(self, rc):
        self.rc = rc
        self.client_id = self.rc.get("client_id")
        self.params = dict(
            client_id=self.client_id
        )
        self.hashdb = HashDB(HASHDB)

    def link(self, path):
        hash = self.hash(path)
        link = self.hashdb.get(hash)
        if link == False:
            link = self.upload(path)
            if link != False:
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

    def upload(self, path):
        file = open(path, 'rb')
        files = dict(
            image=(None, file),
            name=(None, ''),
            type=(None, 'file'),
        )
        r = requests.post(API, files=files, params=self.params)
        if (r.status_code == 200):
            data = json.loads(r.text)
            if (data['status'] == 200):
                return data['data']['link']
            else:
                return False
        else:
            return False

pathlib.Path(HOME).mkdir(parents=True, exist_ok=True)

parser = argparse.ArgumentParser(description='Get a publicly hosted URL for an image on your harddrive.')
parser.add_argument('path',
    metavar='PATH',
    type=str,
    nargs='?',
    help='Image to link'
)
parser.add_argument('stdin',
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
  print("ERROR: no input given")
  exit(1)

try:
    rc = RC(HASHRC)
except ConfigurationError:
    print(f"ERROR: run control malformed ({HASHRC})")
    exit(1)
imgdb = ImgDB(rc)
link = imgdb.link(path)
if link == False:
    print('ERROR: failed getting link')
    exit(1)
else:
    print(link, end='')
