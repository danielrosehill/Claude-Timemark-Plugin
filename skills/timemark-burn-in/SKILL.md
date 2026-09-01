---
name: timemark-burn-in
description: Write joined Timemark field values permanently into the image files as XMP, so each photo is self-describing and survives being moved, copied or re-filed. Use after timemark-import has verified both halves are present.
allowed-tools: Read, Write, Bash(python3 *), Bash(exiftool *)
---

# Burning the values into the files

After the join, the values live in a manifest. That is a link, and links break:
move the file, let a sync tool touch it, and the photo is an anonymous JPEG
again. This writes the values *into* each image so the association travels with
the pixels.

**Metadata, not pixels.** Timemark already burns the values visibly into the
image at capture. This does the opposite and better thing — writes them where a
script can read them, changing no pixel.

## Run it

```bash
python3 scripts/timemark_join.py photos/ \
  --photosheet Photosheet_2026-08-26_to_2026-09-01.xlsx \
  --sidecars --embed-xmp --manifest manifest.json
```

- `--embed-xmp` writes fields into the JPEGs.
- `--sidecars` also writes `IMG.jpg.json` beside each image. Keep both: the
  sidecar is diffable and reviewable, the XMP is what survives the file being
  moved on its own.
- `--dry-run` with `--embed-xmp` prints the exiftool commands instead of running
  them.

Requires `exiftool`. **Take a copy first if the originals are the only copy** —
`-overwrite_original` is used, and there is no undo.

## Where the values land

Fields go to a custom XMP namespace, tags to standard `dc:Subject`:

```
[XMP-timemark]  Item No             : 1
[XMP-timemark]  Item Description    : Penguin
[XMP-dc]        Subject             : Test!
```

XMP is the right target precisely because it is XML and takes arbitrary
namespaces — a field called `Item No` is legal there rather than a hack. EXIF has
nowhere to put one, which is why Timemark resorted to an encrypted blob.

The namespace URI is written into the packet, so **the tags read back on any
machine with a stock exiftool**, no config file needed. Default URI is
`http://ns.timemark-plugin.org/timemark/1.0/`; override with `--xmp-uri` to use a
namespace you own. Nothing dereferences it — it is an identifier, not an address.

Verified after a write: pixels bit-identical (`compare -metric AE` = 0), and
Timemark's `UserComment` blob left intact.

## The trap this handles for you

**exiftool silently refuses to write an XMP tag it has never heard of.**

```
$ exiftool -m -XMP-xmp:ItemNo=1 photo.jpg
$ exiftool -XMP:all photo.jpg
[XMP-x]  XMP Toolkit : Image::ExifTool 13.50      # and nothing else
```

Exit code 0. No stderr. Nothing written. `-m` does not help — it suppresses minor
*warnings*, it does not permit undeclared tags. The tags must be declared in a
`-config` file, and since Timemark field names come from whatever the template
says, that config has to be **generated per export**. The script does that, then
**reads the tags back** to confirm they landed rather than trusting the exit
code.

If you ever hand-roll an exiftool call for these values, do the read-back too.
This failure mode looks exactly like success.

## Check it worked

The manifest's `xmp.results` reports `tags_written` against `tags_expected` per
image. Any row where those differ, or `ok` is false, did not fully land.

```bash
exiftool -XMP:all -G1 photos/*.jpg | head
```
