---
name: timemark-export-triage
description: Work out which Timemark export routes a job needs, and what each one destroys. Use whenever someone has Timemark photos, a "Photosheet" XLSX, a Timemark "Work Report" PDF, or a Photos_from_Timemark ZIP, and before asking anyone to re-export from the phone.
allowed-tools: Read, Bash(python3 *), Bash(unzip *), Bash(exiftool *)
---

# Which Timemark export preserves what

Timemark (Android, `com.oceangalaxy.camera.new`) is a stamp camera: it burns
template values into the pixels and treats machine-readable metadata as
something it does not owe you. It has four export routes and they trade off
against each other.

## The answer, first

**No single export preserves both the full-resolution image and the field data.**
Every usable ingest is a **join of two exports**:

> **Photo ZIP** (pixels) **+ Photosheet XLSX** (values), joined on the capture
> timestamp to the second.

Ask the phone for both, from the **same date range**. One without the other is a
loss you cannot recover later from the file.

## What each route carries

| Route | Images | Field values | Tags | Verdict |
|---|---|---|---|---|
| **Photo ZIP** — `Photos_from_Timemark_DD_MM_YYYY.zip` | **full-res originals, byte-identical to the phone** | filename text only | filename text | the only source of pixels |
| **Photosheet XLSX** — `Photosheet_<from>_to_<to>.xlsx` | 720x960 thumbnails, ~2% of original bytes | **real columns, one per template field** | **dropped** | the only source of structured data |
| **Work Report PDF** — `Work Report_<date>_<name>.pdf` | 617x823 @216ppi, ~50 KB | prose only, **time truncated to the minute** | present, labelled "Tags" | human deliverable; unjoinable |
| Raw photos off the filesystem | full-res | filename text only | filename text | equivalent to the ZIP |

Measured against a reference export on 2026-09-01, Timemark v10.0.210,
OnePlus CPH2493. Originals 1920x2560, ~1.2 MB.

### Why the PDF cannot participate in a join

It prints `01/09/2026 14 12` — no seconds. Two photos taken in the same minute
become indistinguishable, and the reference batch had exactly that. Use the PDF
as a report to hand someone, never as a data source.

### The photo ZIP is genuinely lossless

MD5s of the ZIP's contents matched the raw files on the phone byte for byte.
The ZIP is not a re-encode, so prefer it over anything that routes through
Google Photos.

## What lives only in the filename

The values are in the filename, and that is the only copy that travels with the
image:

```
2026-09-01 14.12.23__(Test! )_(Item No-2)_(Item Description-Flip flops).jpg
<--- timestamp ---->  <tag>   <------------ fields ------------------>
```

- One parenthesised group per item; `Key-Value` for a field, split on the
  **first** hyphen.
- A group with **no hyphen** is a **tag**, not a field — `(Test! )` is the tag
  `Test!`. Tags appear in the filename and the PDF and are **absent from the
  XLSX entirely**, so the filename is the only structured route for them.
- The doubled underscore after the timestamp is the app's separator, not
  corruption.

**Filenames must be preserved verbatim on ingest.** Any tool that renames on
import destroys the tags outright and the field values wherever the photosheet
is missing.

## The header row is the closest thing to a template export

Timemark cannot export templates. But the photosheet's **row 1 enumerates the
full template field set, including fields no photo filled** — the reference
export had eight headers and only five ever populated. So:

- To capture a template definition, shoot one throwaway frame with the template
  and export a photosheet. Row 1 is the field list.
- Practical consequence for parsing: the header row is also the disambiguator
  for hyphen-free field names in filenames. Pass it to
  `scripts/timemark_filename.py --fields`.

This is field *names* only — no types, no defaults, no ordering guarantees
beyond column order. It does not make templates portable, but it makes them
transcribable without hand-copying from a phone screen.

## Traps

**XLSX images are not in row order.** `xl/media/imageN.jpg` numbering has nothing
to do with data rows. The real mapping is in `xl/drawings/drawing1.xml`
`<xdr:from><xdr:row>` (0-based). In the reference export: image1→row 3,
image2→row 2, image3→row 4. Zipping media to rows by index attaches the wrong
photo to every row and produces no error. `scripts/timemark_photosheet.py` reads
the anchors; do not hand-roll this.

**GPS tags are present and zeroed when location was off.** Not absent — written
as `0 deg 0' 0.00"` with `GPSLatitudeRef: South`, `GPSLongitudeRef: West`. A
reader that checks for the presence of GPS tags plots every such frame on Null
Island. Check the value, not the tag.

**`OffsetTimeOriginal` is wrong.** It reads standard-time offset regardless of
DST (`+02:00` in a `GMT+3` region). `DateTimeOriginal` is correct local
wall-clock. Any UTC conversion built on the offset tag is an hour out in summer.

**`UserComment` is a 5-7 KB encrypted blob.** The custom fields are in there —
its length grows by exactly 788 base64 chars per field — but it is not readable.
It is not a metadata source; leave it alone. It is also fragile evidence that a
file has not been transcoded: it is the first casualty of any re-encode pass.

**Nothing standard is written.** No XMP, no IPTC, no `ImageDescription`, no
keywords. Camera settings are stripped: no ISO, ExposureTime, FNumber,
FocalLength, LensModel, Flash, MakerNotes or ICC profile. Timemark re-encodes and
writes its own minimal EXIF, so "is this an original capture?" fails by design.

**The burned-in overlay needs a vision model, not OCR.** tesseract returned
garbage on 11 of 13 frames — white text on a busy scene has no reliable
threshold. Budget for a VLM if the pixels are ever the fallback.

## Deciding what to ask for

- Need the data programmatically → **ZIP + XLSX**, same date range. Then
  [timemark-ingest](../timemark-ingest/SKILL.md).
- Need to hand a person a document → **PDF**, and keep the ZIP for the archive.
- Only have the XLSX → you have the data and no usable images. Re-export the ZIP
  before the photos are cleared off the phone.
- Only have photos → you have everything *except* fields whose values contain
  hyphens ambiguously, and you have the tags. Run
  `scripts/timemark_filename.py`; it is lossless for most templates.
