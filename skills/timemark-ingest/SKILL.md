---
name: timemark-ingest
description: Turn a Timemark export set into full-resolution images carrying their field values - as JSON sidecars or embedded XMP. Use after timemark-export-triage, once a photo ZIP and a Photosheet XLSX are both in hand.
allowed-tools: Read, Write, Bash(python3 *), Bash(unzip *), Bash(exiftool *)
---

# Ingesting a Timemark export set

The goal: full-resolution pixels and structured field values in the same place,
so the association survives the file being moved, copied or re-filed.

## Procedure

```bash
unzip -q "Photos_from_Timemark_01_09_2026.zip" -d photos/

python3 scripts/timemark_ingest.py photos/ \
  --photosheet "Photosheet_2026-08-26_to_2026-09-01.xlsx" \
  --sidecars \
  --manifest manifest.json
```

Add `--embed-xmp` to also write the values into each JPEG. Sidecars and XMP are
complementary, not alternatives: the sidecar is the authoritative record and is
diffable; the XMP makes the file self-describing.

## Read the counts before believing the output

The manifest opens with a `counts` block. **Check it.** A join that silently
matched nothing still exits 0 and still writes sidecars — they just contain only
what the filename carried.

```json
"counts": {
  "images": 3, "photosheet_rows": 3, "joined": 3,
  "images_without_a_row": 0, "rows_without_an_image": 0,
  "conflicting_values": 0
}
```

- `joined` well below `images` → the photosheet covers a different date range, or
  the photos came from Google Photos and were renamed. Re-export.
- `rows_without_an_image` non-zero → the photosheet's range is wider than the ZIP's.
  Usually harmless; confirm nothing wanted is in the gap.
- `conflicting_values` non-zero → the filename and the photosheet disagree for a
  field. The photosheet wins in the merge (it is not truncated by filename length
  limits), and the disagreement is recorded per-record under `conflicts`. A
  conflict usually means a value containing a hyphen was mis-split out of the
  filename — check before trusting either.
- `source: "filename+ambiguous_timestamp"` → two photosheet rows share a
  timestamp to the second. The record is left unjoined rather than guessed.

## What lands where

`IMG.jpg.json` beside `IMG.jpg`, the Google Takeout convention, which exiftool can
merge straight into tags:

```json
{
  "timestamp": "2026-09-01 14:14:23",
  "fields": {"Item No": "1", "Item Description": "Penguin"},
  "tags": ["Test!"],
  "source": "filename+photosheet"
}
```

With `--embed-xmp`, values go to a custom XMP namespace
(`http://ns.danielrosehill.com/timemark/1.0/`, prefix `timemark`) and tags go to
standard `dc:Subject`. The namespace URI is written into the packet, so the tags
read back on any machine without the config file:

```
[XMP-timemark]  Item No            : 1
[XMP-dc]        Subject            : Test!
```

Verified: pixels bit-identical after the write, and Timemark's `UserComment`
blob left intact.

## The exiftool trap this handles for you

**exiftool silently refuses to write an XMP tag it has never heard of.**
`exiftool -XMP-xmp:ItemNo=1 photo.jpg` exits 0, prints nothing, writes nothing.
Custom fields require a `-config` file declaring the namespace, and because
Timemark field names are whatever the template says, that config has to be
generated per export. `timemark_ingest.py` generates it from the discovered
fields and then **reads the tags back to confirm they landed** rather than
trusting the exit code.

If you ever hand-roll an exiftool call for these, do the read-back too.

## Preserve the filenames

Do not rename on import, and do not let a sync tool do it. Tags exist **only** in
the filename — the photosheet drops them — and the timestamp in the filename is
the join key. Rename after ingest, from the manifest, if renaming is wanted at
all.

## Extracting the thumbnails instead

If the full-res ZIP is genuinely unavailable, the photosheet's 720x960
thumbnails are better than nothing, but only if attached to the right rows:

```bash
python3 scripts/timemark_photosheet.py Photosheet_*.xlsx \
  --extract-thumbnails thumbs/
```

Writes `rowNN.jpg` using the drawing anchors, not the media file order. See
[timemark-export-triage](../timemark-export-triage/SKILL.md) for why that
distinction is load-bearing.
