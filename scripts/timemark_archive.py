#!/usr/bin/env python3
"""Build a self-describing archive from a Timemark export set.

Timemark's own exports each throw away half of what matters. This writes the
half-and-half back together into one directory that carries everything and
explains itself:

    <archive>/
    ├── index.json          the references: every image, its values, its hash
    ├── README.md           generated - what the format is, for whoever opens it
    └── images/
        ├── <original filename>.jpg        full resolution, untouched, unrenamed
        └── <original filename>.jpg.json   sidecar, Google Takeout convention

Two copies of the values on purpose. The sidecar sits beside its image so the
pair survives being moved as a unit and exiftool can merge it straight into
tags; index.json is the single file to read to know what the archive holds
without walking it.

Filenames are preserved verbatim, because Timemark tags exist ONLY in the
filename - the photosheet drops them.
"""
import argparse
import json
import os
import shutil
import sys
import zipfile
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from timemark_join import build, sha256, embed_xmp, DEFAULT_XMP_URI  # noqa: E402

FORMAT = "timemark-archive/1"

README = """# Timemark archive

Format `{fmt}`, written {when}.

Self-contained: full-resolution images with their capture-time field values,
recovered from a Timemark export set. Timemark ships no export that carries
both, so this was assembled by joining the original images to a Photosheet
XLSX on the capture timestamp.

## Layout

    index.json    every record: image path, values, tags, sha256
    images/       originals, filenames verbatim, each with a .json sidecar

## Reading it

Everything is in `index.json`. The per-image sidecars carry the same values in
the Google Takeout convention, so exiftool can merge them into tags directly:

    exiftool -json=images/IMG.jpg.json images/IMG.jpg

## Provenance

Source images: {photos}
Photosheet:    {sheet}
Images: {n}, joined to a photosheet row: {joined}, values from filename only: {fnonly}

{caveats}
## Do not rename the images

Timemark encodes tags only in the filename; the photosheet drops them. Renaming
destroys them irreversibly. Rename derived copies, never these.
"""


def build_archive(photos, xlsx, dest, zip_it=False, xmp=False,
                  xmp_uri=DEFAULT_XMP_URI):
    manifest = build(photos, xlsx)
    images_dir = os.path.join(dest, "images")
    os.makedirs(images_dir, exist_ok=True)

    records = []
    for rec in manifest["records"]:
        name = os.path.basename(rec["image"])
        target = os.path.join(images_dir, name)
        shutil.copy2(rec["image"], target)
        sidecar = {
            "timestamp": rec["timestamp"],
            "fields": rec["fields"],
            "tags": rec["tags"],
            "source": rec["source"],
        }
        with open(target + ".json", "w", encoding="utf-8") as fh:
            json.dump(sidecar, fh, indent=2, ensure_ascii=False)
        records.append({
            "image": "images/" + name,
            "sidecar": "images/" + name + ".json",
            "timestamp": rec["timestamp"],
            "fields": rec["fields"],
            "tags": rec["tags"],
            "source": rec["source"],
            "photosheet_row": rec["photosheet_row"],
            "conflicts": rec["conflicts"],
            "_path": target,
        })

    # XMP goes on the archive's copies, never the originals, and must happen
    # BEFORE hashing - writing XMP changes the file, so hashing first would bake
    # stale digests into the index that fail verification for no real reason.
    xmp_result = None
    if xmp:
        xmp_manifest = dict(manifest)
        xmp_manifest["records"] = [
            {"image": r["_path"], "fields": r["fields"], "tags": r["tags"]}
            for r in records]
        xmp_result = embed_xmp(xmp_manifest, uri=xmp_uri)

    for r in records:
        r["sha256"] = sha256(r["_path"])
        r["bytes"] = os.path.getsize(r["_path"])
        del r["_path"]

    index = {
        "format": FORMAT,
        "created": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "source": {
            "images": os.path.abspath(photos),
            "photosheet": manifest["photosheet"],
            "app": "Timemark (com.oceangalaxy.camera.new)",
        },
        "template_fields": manifest["template_fields"],
        "xmp_embedded": bool(xmp),
        "counts": manifest["counts"],
        "images_without_a_row": manifest["images_without_a_row"],
        "rows_without_an_image": manifest["rows_without_an_image"],
        "records": records,
    }
    with open(os.path.join(dest, "index.json"), "w", encoding="utf-8") as fh:
        json.dump(index, fh, indent=2, ensure_ascii=False)
        fh.write("\n")

    c = manifest["counts"]
    caveats = ""
    if c["images_without_a_row"]:
        caveats += ("**%d image(s) had no photosheet row.** Their values are whatever the\n"
                    "filename encoded, and any field left empty at capture is simply gone.\n\n"
                    % c["images_without_a_row"])
    if c["conflicting_values"]:
        caveats += ("**%d image(s) had a filename/photosheet disagreement.** The photosheet\n"
                    "value was used; see `conflicts` in index.json.\n\n"
                    % c["conflicting_values"])
    with open(os.path.join(dest, "README.md"), "w", encoding="utf-8") as fh:
        fh.write(README.format(
            fmt=FORMAT, when=index["created"],
            photos=os.path.basename(os.path.abspath(photos)),
            sheet=os.path.basename(manifest["photosheet"]) if manifest["photosheet"] else "none",
            n=c["images"], joined=c["joined"],
            fnonly=c["images"] - c["joined"], caveats=caveats))

    if zip_it:
        archive_path = dest.rstrip("/") + ".zip"
        with zipfile.ZipFile(archive_path, "w", zipfile.ZIP_DEFLATED) as z:
            for root, _d, files in os.walk(dest):
                for f in sorted(files):
                    full = os.path.join(root, f)
                    z.write(full, os.path.relpath(full, os.path.dirname(dest)))
        index["zip"] = archive_path
    return index


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("photos", help="directory of full-resolution originals")
    ap.add_argument("--photosheet", help="Photosheet_*.xlsx covering the same dates")
    ap.add_argument("--out", required=True, help="archive directory to create")
    ap.add_argument("--zip", action="store_true", help="also write <out>.zip")
    ap.add_argument("--embed-xmp", action="store_true",
                    help="also write values into the archive's images as XMP "
                         "(done before hashing, so the index stays valid)")
    ap.add_argument("--xmp-uri", default=DEFAULT_XMP_URI,
                    help="XMP namespace URI (default: %(default)s)")
    args = ap.parse_args()

    index = build_archive(args.photos, args.photosheet, args.out, args.zip,
                          args.embed_xmp, args.xmp_uri)
    json.dump({k: v for k, v in index.items() if k != "records"},
              sys.stdout, indent=2, ensure_ascii=False)
    print()


if __name__ == "__main__":
    main()
