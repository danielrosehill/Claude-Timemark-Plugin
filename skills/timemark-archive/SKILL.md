---
name: timemark-archive
description: Build a self-contained Timemark archive - full-resolution images, per-image JSON sidecars, and an index.json referencing them all with hashes. Use after timemark-import when the photo set needs to land in a repo or be handed on as one unit.
allowed-tools: Read, Write, Bash(python3 *)
---

# Building the archive

The output Timemark should have produced: one directory holding the full
images, their values, and an index tying the two together — readable years later
by someone who has never heard of Timemark.

## Run it

```bash
python3 scripts/timemark_archive.py photos/ \
  --photosheet Photosheet_2026-08-26_to_2026-09-01.xlsx \
  --out inventory-2026-09-01 \
  --zip
```

## The format

`timemark-archive/1`:

```
inventory-2026-09-01/
├── index.json          every record: image path, values, tags, sha256, bytes
├── README.md           generated - explains the format to whoever opens it
└── images/
    ├── <original filename>.jpg        full resolution, untouched, unrenamed
    └── <original filename>.jpg.json   sidecar, Google Takeout convention
```

**The values are stored twice on purpose.** The sidecar sits beside its image so
the pair survives being moved as a unit, and exiftool merges it straight into
tags (`exiftool -json=IMG.jpg.json IMG.jpg`). `index.json` is the one file to
read to know what the archive holds without walking it.

`index.json` carries provenance — which images directory and which photosheet it
was built from, the app, the template's full field list, and the join counts —
so a later reader can tell a complete import from a partial one.

## Filenames are preserved verbatim

Including the parentheses and doubled underscores. They look like junk and are
not: Timemark tags exist **only** in the filename, and renaming destroys them.
The generated `README.md` says this too, so the constraint travels with the
archive.

## Check the counts before shipping it

`index.json` → `counts`, same block the join produces. Anything non-zero in
`images_without_a_row` or `conflicting_values` is written into the generated
README as a caveat, so the archive is honest about its own gaps rather than
looking complete. Read them; a caveat means someone should decide whether to
re-export while the photos are still on the phone.

## Verifying an archive later

```bash
python3 - <<'PY'
import json, hashlib
d = json.load(open("index.json"))
for r in d["records"]:
    h = hashlib.sha256(open(r["image"], "rb").read()).hexdigest()
    print("OK " if h == r["sha256"] else "BAD", r["image"])
PY
```

## Combining with burn-in

Pass `--embed-xmp` and the archive's images get the values written into them too,
so they stay self-describing even if separated from the index:

```bash
python3 scripts/timemark_archive.py photos/ \
  --photosheet Photosheet_*.xlsx --out inventory-2026-09-01 --embed-xmp
```

This writes only to the archive's **copies** — the originals are never touched —
and it happens **before hashing**, so the recorded digests stay valid. Doing it
the other way round (build, then run burn-in over `images/`) bakes stale hashes
into the index that fail verification for no real reason. Use the flag rather
than running the two steps by hand.

See [timemark-burn-in](../timemark-burn-in/SKILL.md) for what lands where and the
exiftool trap involved.
