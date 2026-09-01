---
name: timemark-import
description: Gate and triage a Timemark photo import - check the user has supplied BOTH the original images and the Photosheet XLSX export before any work starts, because half an import cannot be completed later. Use whenever someone brings Timemark photos, a Photosheet, or a Work Report PDF into a project.
allowed-tools: Read, Bash(python3 *), Bash(unzip *), Bash(exiftool *)
---

# Importing a Timemark photo set

Timemark (Android stamp camera, `com.oceangalaxy.camera.new`) is good at capture
and deliberately bad at giving the data back. Its exports each throw away half of
what matters, so an import is a **reconstruction**, and it only works if both
halves arrived.

**Run this gate first. Do not start work on a partial set.**

## The gate

Two inputs are required:

1. **The original images** — full-resolution JPEGs, filenames untouched. A
   `Photos_from_Timemark_DD_MM_YYYY.zip` is just these bundled; it is
   byte-identical and adds nothing, so either form is fine.
2. **The Photosheet XLSX** — `Photosheet_<from>_to_<to>.xlsx`, covering the same
   dates as the photos.

If either is missing, **say so and stop**. Ask for the missing half before doing
anything else.

That is not pedantry about inputs. It is because the missing half is *not
recoverable later from what you have*, and the photos usually get cleared off the
phone. Specifically:

- **Images but no photosheet** → you get whatever the filename encoded, and any
  field left empty at capture is gone with no trace it ever existed. You also
  cannot tell a field name from a tag.
- **Photosheet but no images** → you have the values and 720×960 thumbnails. The
  full-resolution pixels exist only on the phone.
- **Only the Work Report PDF** → unusable as data. See below.

## Why: what each export actually preserves

| Input | Full-res pixels | Field values | Tags |
|---|---|---|---|
| **Original images** (or the ZIP of them) | **yes** | filename text only | **filename only** |
| **Photosheet XLSX** | no — 720×960, ~2% of the bytes | **yes, as real columns** | **dropped entirely** |
| **Work Report PDF** | no — 617×823 | prose, **time cut to the minute** | yes, labelled "Tags" |

Measured against a reference export, Timemark v10.0.210, 2026-09-01. Full
measurements: [reference/export-formats.md](../../reference/export-formats.md).

**The PDF can never participate in the join** — it prints `01/09/2026 14 12` with
no seconds, so two frames from the same minute are indistinguishable. It is a
document to hand a person. Never treat it as a data source, however convenient it
looks.

## The join

The two halves are matched on **capture timestamp to the second** — the images
carry it in the filename, the photosheet carries it as `Date` + `Time`.

```bash
python3 scripts/timemark_join.py photos/ \
  --photosheet Photosheet_2026-08-26_to_2026-09-01.xlsx
```

**Read the `counts` block before believing anything.** A join that matched
nothing still exits 0 and still produces output — it just silently contains only
what the filenames held.

- `joined` well below `images` → the photosheet covers a different date range, or
  the photos were renamed in transit (Google Photos does this). Re-export.
- `conflicting_values` non-zero → filename and photosheet disagree. The
  photosheet wins; the disagreement is recorded per record. Usually a value
  containing a hyphen mis-split out of the filename.
- `source: "filename+ambiguous_timestamp"` → two rows share a timestamp to the
  second. Left unjoined rather than guessed.

## Then pick an output

- **[timemark-burn-in](../timemark-burn-in/SKILL.md)** — write the values into
  the image files themselves, so each photo is self-describing wherever it ends
  up.
- **[timemark-archive](../timemark-archive/SKILL.md)** — build a self-contained
  bundle: full images, JSON sidecars, and an index.

They are complementary, not alternatives. The usual answer is both.

## Never rename the images

Tags exist **only** in the filename — the photosheet drops them — and the
timestamp in the filename is the join key. Any tool that renames on import
destroys both, silently and irreversibly. Rename derived copies afterwards if you
must; never the originals.

## What is not worth trying

- **`UserComment`** holds the fields in a ~5–7 KB encrypted blob (7.958 bits/byte
  entropy, grows exactly 788 base64 chars per field). It is not readable. Leave
  it alone.
- **OCR on the burned-in overlay** — tesseract returned garbage on 11 of 13
  frames. If the pixels are genuinely the only source, use a vision model.
- **Standard metadata** — Timemark writes no XMP, IPTC, `ImageDescription` or
  keywords, and strips all camera settings. There is nothing to read.
