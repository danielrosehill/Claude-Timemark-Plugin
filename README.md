# Timemark Plugin

Import photo sets from **Timemark** (Android stamp camera,
`com.oceangalaxy.camera.new`) without losing either the pixels or the data —
and work around the fact that Timemark will not give you both.

## The problem this exists for

**No Timemark export preserves the full-resolution image and the field values
together.**

| Input | Full-res pixels | Field values | Tags |
|---|---|---|---|
| **Original images** (a `Photos_from_Timemark` ZIP is just these bundled, byte-identical) | **yes** | filename text only | **filename only** |
| **Photosheet XLSX** | no — 720×960, ~2% of the bytes | **yes, as real columns** | dropped |
| **Work Report PDF** | no — 617×823 | prose, **time cut to the minute** | yes |

So an import is a reconstruction: the **images and the photosheet, joined on the
capture timestamp to the second**. The PDF can never participate — it drops the
seconds, so two frames from the same minute are indistinguishable.

The practical consequence, and the reason the first skill is a gate: if only half
the export arrives, the other half is **not recoverable later** from what you
have, and the photos usually get cleared off the phone.

## Skills

| Skill | Does |
|---|---|
| `timemark-import` | the gate — verify **both** halves are present, then join. Run first, always |
| `timemark-burn-in` | write the values into the images as XMP, so each photo is self-describing |
| `timemark-archive` | build a self-contained bundle: full images + JSON sidecars + an index |

Burn-in and archive are complementary, not alternatives.

## Use

```
/timemark:import ./exports
```

Or directly:

```bash
python3 scripts/timemark_archive.py photos/ \
  --photosheet Photosheet_2026-08-26_to_2026-09-01.xlsx \
  --out inventory-2026-09-01 --embed-xmp --zip
```

Producing `timemark-archive/1`:

```
inventory-2026-09-01/
├── index.json          every record: image path, values, tags, sha256, provenance
├── README.md           generated — explains the format to whoever opens it
└── images/
    ├── <original filename>.jpg        full resolution, untouched, unrenamed
    └── <original filename>.jpg.json   sidecar, Google Takeout convention
```

Scripts are stdlib-only Python 3 — no `openpyxl`. XMP embedding needs `exiftool`.

## Traps this handles for you

- **exiftool silently drops undeclared XMP tags.** `-XMP-xmp:ItemNo=1` exits 0,
  prints nothing, writes nothing. Custom fields need a generated `-config`, so
  the plugin generates one per export and reads the tags back to confirm.
- **XLSX images are not in row order.** `xl/media/imageN.jpg` numbering is
  unrelated to data rows — the real mapping is the anchors in
  `xl/drawings/drawing1.xml`. Index-order zipping mislabels every photo, silently.
- **Filenames must be preserved verbatim.** Tags exist *only* there, and the
  timestamp is the join key.
- **GPS is written zeroed, not omitted, when location was off** — testing for tag
  presence puts every frame on Null Island.
- **`OffsetTimeOriginal` ignores DST**, so UTC conversion off it is an hour out.
- **`UserComment` is a 5–7 KB encrypted blob.** The fields are in there and are
  not readable. Don't spend time on it.

Full measurements: [reference/export-formats.md](reference/export-formats.md).
