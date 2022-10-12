Get a public link for a local image, uploading only as necessary.

Images are hashed and then uploaded to a public host. The hash and resulting
link are stored together, so future requests for this image will skip uploading
and return the existing link.

```sh
# get link for an image
hashbeam ~/image.jpg
# image path may be read from stdin
echo ~/image.jpg | hashbeam
```

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
