# Timemark export formats — measured teardown

Timemark v10.0.210, Android, `com.oceangalaxy.camera.new`. There are three
things it will give you — the images, an XLSX and a PDF — and none of them holds
both the pixels and the data. Measured 2026-09-01
against a 3-frame reference export shot on a OnePlus CPH2493, using exiftool
13.50, poppler-utils and ImageMagick. Everything below is **confirmed by
measurement** unless marked *inferred*.

This supersedes the "the data is unrecoverable" conclusion reached on the same
date from the *photos alone*. That conclusion was correct about the photo files
and wrong about the app: the field values are recoverable, just not from the
image. See "What the earlier teardown got wrong", below.

## The reference export set

```
Timemark_Test/
├── Exports/
│   ├── Photos_from_Timemark_01_09_2026.zip           3.6 MB, 3 JPEGs
│   ├── Photosheet_2026-08-26_to_2026-09-01.xlsx       76 KB
│   └── Work Report_09_01_2026_<name>.pdf           276 KB
└── Raw_Photos/                                        3 JPEGs, 1920x2560, ~1.2 MB each
```

Template in use: 8 fields (`Item No`, `Item Description`, `UTM band`,
`Storage ID`, `WMS`, plus the built-in `Photo`/`Date`/`Time`), of which two were
filled, and one tag (`Test!`).

## The images (and the ZIP that bundles them)

`Photos_from_Timemark_DD_MM_YYYY.zip`. Flat, no directory structure, no manifest.

**The ZIP is a delivery mechanism, not a format.** Three JPEGs, flat, no
manifest, no sidecar, no directory entries — and every MD5 matched the raw file
on the phone exactly. It adds nothing over copying the photos off yourself, so
treat "the images" and "the ZIP" as the same input. It is worth confirming only
because it proves Timemark does not re-encode on the way out.

This is the only source of full-resolution pixels. Field values travel with it
solely as filename text.

## Photosheet XLSX

`Photosheet_<from>_to_<to>.xlsx`. A genuine OOXML workbook (`Application:
Microsoft Excel`, `AppVersion 16.0300`), two sheets: `Photos` and `Data summary`.

**This is the only export that carries field values as structured data.**

### Sheet 1 layout

Row 1 is the header; each subsequent row is one photo, newest first.

| A | B | C | D… |
|---|---|---|---|
| Photo | Date | Time | one column per template field |

- Column A (`Photo`) is **always empty as a cell value**. The picture is a
  floating drawing anchored over the cell, not cell content.
- `Date` is `YYYY-MM-DD`, `Time` is `HH:MM:SS`. Together they are the join key.
- **The header enumerates the template's full field set, not just populated
  columns.** Reference export: 8 headers, 5 columns ever populated, and rows
  declared `spans="1:5"` while the header declared `spans="1:8"`. Empty fields
  emit no `<c>` element at all.
- **Tags are absent.** `Test!` appears in the filename and the PDF, and in no
  column of the photosheet.

### The image-anchor trap

`xl/media/imageN.jpg` numbering does **not** follow row order. The authoritative
mapping is `xl/drawings/drawing1.xml`:

```xml
<xdr:twoCellAnchor editAs="oneCell">
  <xdr:from><xdr:col>0</xdr:col><xdr:row>2</xdr:row></xdr:from>
  ...<a:blip r:embed="rId1"/>
```

`<xdr:row>` is **0-based**, so `row 2` means spreadsheet row 3. `r:embed`
resolves through `xl/drawings/_rels/drawing1.xml.rels` to the media part.

Observed in the reference export:

| media part | anchored row | subject |
|---|---|---|
| `xl/media/image1.jpg` | 3 | Spray bottle |
| `xl/media/image2.jpg` | 2 | Penguin |
| `xl/media/image3.jpg` | 4 | Flip flops |

**Verified independently**, not just read off the XML: each thumbnail was
RMSE-compared against all three originals downscaled to 720x960, and the nearest
match agreed with the anchor in all three cases. Naive index-order zipping would
have mislabelled all three.

### Thumbnail quality

720x960 (originals are 1920x2560), 18–26 KB (originals ~1.2 MB) — roughly 2% of
the original bytes. Adequate for a visual check, not for an archive.

## Work Report PDF

`Work Report_<MM_DD_YYYY>_<name>.pdf`. Cover page plus one photo per page with a
field table.

- Images: **617x823 @ 216 ppi**, ~46–63 KB, JPEG-in-PDF.
- Field values render as label/value pairs; tags render under a `Tags` heading —
  the only export besides the filename that carries tags in a labelled way.
- **Time is truncated to the minute** (`01/09/2026 14 12`). This alone
  disqualifies the PDF as a join source: two frames in the same minute are
  indistinguishable, and the reference batch contained exactly that pair
  (14:12:23 and 14:12:42).
- Cover page carries a summary: period, photo count, location count, preparer,
  generation time.

Treat it as a deliverable for a person, never as data.

## The filename encoding

```
YYYY-MM-DD HH.MM.SS_[_(Group)]*.jpg
2026-09-01 14.12.23__(Test! )_(Item No-2)_(Item Description-Flip flops).jpg
```

- Timestamp is the first 19 characters, `.`-separated time.
- The doubled underscore is the app's separator, not corruption.
- Each `(...)` group is either a **field** — `Key-Value`, split on the first
  hyphen — or a **tag**, which has no hyphen and a trailing space: `(Test! )`.
- Disambiguating a hyphen-free field name from a tag is impossible from the
  filename alone. Pass the photosheet header row to
  `timemark_filename.py --fields` and the ambiguity disappears.

**Untested limits**, carried over and still not hit: filesystem name length, and
what Timemark does to values containing hyphens, parentheses or non-Latin
characters.

## What is in the image files

Retained: `Make`, `Model`, `Software` = `Timemark v10.0.210`, `Artist` =
`Timemark`, `DateTimeOriginal`/`CreateDate`/`ModifyDate`, `Orientation`, an
embedded thumbnail, `ImageUniqueID` (a UUIDv4 in IFD0, and a zero-padded 16-byte
hex in ExifIFD — both populated simultaneously).

Discarded: ISO, ExposureTime, FNumber, FocalLength, LensModel, WhiteBalance,
Flash, MeteringMode, MakerNotes, XMP, IPTC, ICC profile. Timemark re-encodes and
writes its own minimal EXIF.

### `UserComment` is encrypted and not worth pursuing

Base64, ~4.2 KB payload, **7.958 bits/byte** Shannon entropy — indistinguishable
from random. All frames share an identical 213-character prefix, then diverge.

Its length is a deterministic function of what the template rendered — measured
across a separate 13-frame batch:

```
frames  template content              UserComment (base64 chars)
4       no accuracy, no custom tags   5632
7       accuracy only                 5656   (= 5632 + 24)
1       accuracy + 1 custom field     6444   (= 5656 + 788)
1       accuracy + 2 custom fields    7232   (= 5656 + 1576 = 2 × 788)
```

Exactly **788 base64 chars (591 raw bytes) per custom field**. That is an exact
length correlation, **not a decryption** — the values were never read out.
Grepping the whole file for known field values in ASCII and UTF-16LE returned
zero hits.

The blob does have one use: it is the first casualty of any transcoding pass, so
an intact 5–7 KB `UserComment` is decent evidence a file has not been through
Google Photos.

### GPS is written zeroed, not omitted, when location is off

```
GPSLatitudeRef  : South      GPSLatitude  : 0 deg 0' 0.00"
GPSLongitudeRef : West       GPSLongitude : 0 deg 0' 0.00"
GPSAltitudeRef  : Below Sea Level
```

A reader that tests for the *presence* of GPS tags will plot every location-off
frame on Null Island at 0°S 0°W. Test the value.

### `OffsetTimeOriginal` is wrong

Reads `+02:00` on every frame in a region on `GMT+3` DST. `DateTimeOriginal`
itself is correct local wall-clock. Timemark appears to write a standard-time
offset regardless of DST, so any UTC conversion built on the offset tag is an
hour out in summer.

### GPS accuracy exists only in the pixels

The overlay prints a radius; there is no `GPSHPositioningError` or `GPSDOP` to
match it. It is conditional — some frames print no accuracy at all.

## Reading the burned-in overlay

tesseract on the cropped overlay panel returned garbage on **11 of 13** frames.
White text over a busy scene has no reliable threshold. A VLM reading the same
crop was clean. If the pixels are ever the fallback, budget for a vision model,
not OCR.

## The exiftool custom-namespace trap

Writing a custom XMP tag without declaring it **fails silently**:

```
$ exiftool -m -XMP-xmp:ItemNo=1 photo.jpg
$ exiftool -XMP:all photo.jpg
[XMP-x]  XMP Toolkit : Image::ExifTool 13.50      # and nothing else
```

Exit code 0. No stderr. Nothing written. `-m` does not help — it suppresses minor
*warnings*, it does not permit undeclared tags. The tags must be declared in a
`-config` file:

```perl
%Image::ExifTool::UserDefined = (
    'Image::ExifTool::XMP::Main' => {
        timemark => { SubDirectory => {
            TagTable => 'Image::ExifTool::UserDefined::timemark' } },
    },
);
%Image::ExifTool::UserDefined::timemark = (
    GROUPS    => { 0 => 'XMP', 1 => 'XMP-timemark', 2 => 'Image' },
    NAMESPACE => { 'timemark' => 'http://ns.timemark-plugin.org/timemark/1.0/' },
    WRITABLE  => 'string',
    ItemNo => { Name => 'ItemNo' },
);
1;
```

Because Timemark's field names come from the template, this config has to be
**generated per export** — `timemark_ingest.py` does that from the discovered
field set. Once written, the namespace URI is embedded in the XMP packet, so the
tags read back on any machine **without** the config file.

Confirmed after a write: pixels bit-identical (`compare -metric AE` = 0) and the
`UserComment` blob untouched.

## What an earlier photos-only teardown got wrong

An earlier teardown of the same date, working from the image files alone,
concluded the custom fields were
"preserved in the file and useless to you", and that the filename was "the only
machine-readable copy". Both statements are true **of the image file** and led to
a false conclusion **about the app**: that Timemark data is unrecoverable and
that template definitions cannot be got out at all.

The error was scoping the investigation to the artefact in hand. The photos were
what had been shared, so the photos were what got examined; the app's own export
menu was never exercised. If you arrive at this repo from a set of Timemark
photos, that is the trap to avoid — ask for the photosheet. The photosheet XLSX answers both questions — structured
per-photo values, and a header row that enumerates the template's fields.

The generalisable form: when a conclusion is "this data is unrecoverable",
check that every route the vendor ships has actually been tried, not just the
one the sample arrived by.

## What the vendor documents

Effectively nothing at field level. No developer or API documentation for the
EXIF layout exists; the sources are marketing and app-store pages. Their stated
design is explicitly the opposite of extractable metadata: *"instead of hidden
background metadata, the important information is visible on the photo itself."*

They describe "unique photo codes link each photo to its original metadata",
matching a per-photo alphanumeric code rendered vertically at the right edge of
every frame beside "Timemark Verified". That code is a **server-side lookup
handle**: the authoritative record lives on Timemark's servers. *Inferred* from
the marketing copy plus the presence of the code; the lookup endpoint was not
exercised.

The sibling app **TimemarkEdit** explicitly rewrites EXIF capture time and GPS on
save, overwriting prior values. Timemark-family EXIF is therefore not evidence of
camera truth.
