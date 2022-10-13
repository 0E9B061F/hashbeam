Get a public link for a local image, uploading only as necessary.

Images are hashed and then uploaded to a public host. The hash and resulting
link are stored together, so future requests for this image will skip uploading
and return the existing link.

# Usage

Getting a link for an image:

```sh
hashbeam ~/image.jpg
# multiple images may given at once:
hashbeam ~/foo.png /tmp/bar.png /tmp/baz.jpg
# image path may be read from stdin
echo ~/image.jpg | hashbeam
```

Deleting upload for an image:

```sh
hashbeam -d ~/image.jpg
hashbeam -d ~/foo.png ~/bar.png
echo ~/image.jpg | hashbeam -d
```

Listing uploads:

```sh
# list all in `HASH: LINK` format
hashbeam -l
# list only hashes, seperated by newlines
hashbeam -H -l
```

Uploads can be referenced by their hash when using `-H`:

```sh
hashbeam -H f68f0e514a646ecea9ef18c3dafa0c6b
echo f68f0e514a646ecea9ef18c3dafa0c6b | hashbeam -H
hashbeam -H -d f68f0e514a646ecea9ef18c3dafa0c6b
echo f68f0e514a646ecea9ef18c3dafa0c6b | hashbeam -H -d
```

To delete all uploads:

```sh
hashbeam -H -l | hashbeam -H -d
```

# Handlers

Currently only Imgur is supported but additional handlers will be added in the
future. For Imgur, you'll need to register an application and supply your
`clent_id`. This is configured in `$XDG_CONFIG_HOME/hashbeam/hashrc.json`,
which should look like:

```json
{
  "handler": "imgur",
  "imgur": {
    "client_id": "CLIENT_ID"
  }
}
```
