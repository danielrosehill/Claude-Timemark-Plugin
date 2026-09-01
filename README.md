# Claude Timemark Plugin

Handle exports from **Timemark** (Android stamp camera,
`com.oceangalaxy.camera.new`) without losing either the pixels or the data.

## The one thing to know

**No single Timemark export preserves both the full-resolution image and the
field values.**

| Route | Full-res image | Field values | Tags |
|---|---|---|---|
| Photo ZIP | **yes — byte-identical** | filename text only | filename text |
| Photosheet XLSX | no — 720x960 thumbs | **yes — real columns** | **no** |
| Work Report PDF | no — 617x823 | prose, **time cut to the minute** | yes |

So a usable ingest is always a **join of two exports** — the photo ZIP for
pixels, the photosheet XLSX for values, joined on the capture timestamp to the
second. Ask the phone for both, over the same date range. The PDF cannot
participate: it drops the seconds.

## Install

```
/plugin marketplace add danielrosehill/Claude-Code-Plugins-Private
/plugin install timemark@danielrosehill-private
```

## Use

```bash
unzip -q Photos_from_Timemark_01_09_2026.zip -d photos/

python3 scripts/timemark_ingest.py photos/ \
  --photosheet Photosheet_2026-08-26_to_2026-09-01.xlsx \
  --sidecars --embed-xmp --manifest manifest.json
```

Writes `IMG.jpg.json` beside each image (the Google Takeout convention, which
exiftool can merge straight into tags) and, with `--embed-xmp`, the values into
a custom XMP namespace so the file is self-describing. Read the `counts` block
in the manifest before believing the result — a join that matched nothing still
exits 0.

Or: `/timemark:ingest <directory>`.

## Contents

| Path | What |
|---|---|
| `skills/timemark-export-triage/` | which route to ask for, and what each destroys |
| `skills/timemark-ingest/` | running the join, and reading the counts |
| `commands/ingest.md` | `/timemark:ingest` |
| `scripts/timemark_filename.py` | filename encoding → JSON |
| `scripts/timemark_photosheet.py` | XLSX → rows + correctly anchored thumbnails |
| `scripts/timemark_ingest.py` | the join, sidecars, XMP embed |
| `reference/export-formats.md` | full measured teardown |
| `examples/` | reference manifest and photosheet fragments |

Scripts are stdlib-only Python 3 (no `openpyxl`). `--embed-xmp` needs `exiftool`.

## Traps this exists to avoid

- **XLSX images are not in row order.** `xl/media/imageN.jpg` numbering is
  unrelated to data rows; the real mapping is in `xl/drawings/drawing1.xml`.
  Index-order zipping attaches the wrong photo to every row, silently.
- **exiftool silently drops undeclared XMP tags.** `-XMP-xmp:ItemNo=1` exits 0
  and writes nothing. Custom fields need a generated `-config`.
- **GPS is written zeroed, not omitted, when location is off** — testing for tag
  presence puts every frame on Null Island.
- **`OffsetTimeOriginal` ignores DST**, so UTC conversion off it is an hour out.
- **Filenames must be preserved verbatim.** Tags exist *only* there — the
  photosheet drops them — and the timestamp is the join key.

Full detail and measurements: [reference/export-formats.md](reference/export-formats.md).

## Related

- [`Field-Photo-Metadata-Capture`](https://github.com/danielrosehill/Field-Photo-Metadata-Capture)
  — the capture-app selection research this came out of.
