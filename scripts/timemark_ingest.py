#!/usr/bin/env python3
"""Join a Timemark photo ZIP (full-resolution images) to a Timemark photosheet
XLSX (structured field values) and emit one JSON sidecar per image.

No single Timemark export carries both the pixels and the data:

    photo ZIP   full-res originals, byte-identical to the phone; values only
                as filename text
    XLSX        values as real columns, plus 720x960 thumbnails
    PDF         values as prose, 617x823 images, time truncated to the minute

So ingest is always a join. The join key is the capture timestamp to the second,
which the ZIP carries in the filename and the XLSX carries as Date + Time. The
PDF cannot participate: it drops the seconds.

Writes IMG.jpg.json beside IMG.jpg (the Google Takeout convention, which exiftool
can merge straight into tags) plus a manifest.
"""
import argparse
import json
import os
import subprocess
import tempfile
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from timemark_filename import parse as parse_filename          # noqa: E402
from timemark_photosheet import read as read_photosheet        # noqa: E402

IMG_EXT = (".jpg", ".jpeg", ".png")


def collect_images(path):
    if os.path.isfile(path):
        return [path]
    out = []
    for root, _dirs, files in os.walk(path):
        for f in sorted(files):
            if f.lower().endswith(IMG_EXT):
                out.append(os.path.join(root, f))
    return out


def build(photos, xlsx, namespace="timemark"):
    sheet = read_photosheet(xlsx) if xlsx else {"records": [], "template_fields": []}
    known = sheet["template_fields"] or None

    by_ts = {}
    for rec in sheet["records"]:
        if rec["date"] and rec["time"]:
            by_ts.setdefault("%s %s" % (rec["date"], rec["time"]), []).append(rec)

    records, unmatched_images = [], []
    matched_rows = set()

    for img in collect_images(photos):
        parsed = parse_filename(img, known)
        ts = parsed["timestamp"]
        hits = by_ts.get(ts, [])
        row = hits[0] if len(hits) == 1 else None

        fields = dict(parsed["fields"])
        conflicts = {}
        if row:
            matched_rows.add(row["row"])
            for k, v in row["fields"].items():
                if k in fields and fields[k] != v:
                    conflicts[k] = {"filename": fields[k], "photosheet": v}
                fields[k] = v          # photosheet wins: it is not truncated

        records.append({
            "image": os.path.abspath(img),
            "timestamp": ts,
            "fields": fields,
            "tags": parsed["tags"],
            "source": ("filename+photosheet" if row
                       else ("filename+ambiguous_timestamp" if len(hits) > 1
                             else "filename")),
            "photosheet_row": row["row"] if row else None,
            "conflicts": conflicts,
        })
        if not row:
            unmatched_images.append(os.path.basename(img))

    unmatched_rows = [r["row"] for r in sheet["records"] if r["row"] not in matched_rows]

    return {
        "namespace": namespace,
        "photos": os.path.abspath(photos),
        "photosheet": os.path.abspath(xlsx) if xlsx else None,
        "template_fields": sheet["template_fields"],
        "counts": {
            "images": len(records),
            "photosheet_rows": len(sheet["records"]),
            "joined": len(matched_rows),
            "images_without_a_row": len(unmatched_images),
            "rows_without_an_image": len(unmatched_rows),
            "conflicting_values": sum(1 for r in records if r["conflicts"]),
        },
        "images_without_a_row": unmatched_images,
        "rows_without_an_image": unmatched_rows,
        "records": records,
    }


def write_sidecars(manifest):
    written = []
    for rec in manifest["records"]:
        payload = {
            "timestamp": rec["timestamp"],
            "fields": rec["fields"],
            "tags": rec["tags"],
            "source": rec["source"],
        }
        dest = rec["image"] + ".json"
        with open(dest, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, indent=2, ensure_ascii=False)
        written.append(dest)
    return written


def _tag_name(field):
    return "".join(ch for ch in field.title().replace(" ", "") if ch.isalnum())


def write_exiftool_config(fields, dest, namespace="timemark",
                          uri="http://ns.danielrosehill.com/timemark/1.0/"):
    """Generate an ExifTool config declaring one XMP tag per template field.

    This step is not optional. exiftool silently refuses to write an XMP tag it
    has never heard of: `-XMP-xmp:ItemNo=1` exits 0, prints nothing, and stores
    nothing. Custom fields need a declared namespace, and since Timemark's field
    names are whatever the template says, the declaration has to be generated.
    """
    tags = "\n".join(
        "    %s => { Name => '%s' }," % (_tag_name(f), _tag_name(f))
        for f in sorted(fields))
    body = """%%Image::ExifTool::UserDefined = (
    'Image::ExifTool::XMP::Main' => {
        %(ns)s => {
            SubDirectory => {
                TagTable => 'Image::ExifTool::UserDefined::%(ns)s',
            },
        },
    },
);

%%Image::ExifTool::UserDefined::%(ns)s = (
    GROUPS    => { 0 => 'XMP', 1 => 'XMP-%(ns)s', 2 => 'Image' },
    NAMESPACE => { '%(ns)s' => '%(uri)s' },
    WRITABLE  => 'string',
%(tags)s
);

1;  #end
""" % {"ns": namespace, "uri": uri, "tags": tags}
    with open(dest, "w", encoding="utf-8") as fh:
        fh.write(body)
    return dest


def embed_xmp(manifest, dry_run=False):
    """Write field values into XMP under a custom namespace, via exiftool.

    XMP is the right target: it is XML and takes arbitrary namespaces, so a
    custom field name is legal rather than a hack. EXIF has nowhere to put one.
    Tags go to dc:Subject, which is standard and readable by anything.
    """
    ns = manifest["namespace"]
    all_fields = sorted({k for rec in manifest["records"] for k in rec["fields"]}
                        | set(manifest.get("template_fields") or []))
    if not all_fields:
        return {"skipped": "no fields to write"}

    cfg = os.path.join(tempfile.mkdtemp(prefix="timemark-"), "timemark.ExifTool_config")
    write_exiftool_config(all_fields, cfg, namespace=ns)

    results = []
    for rec in manifest["records"]:
        cmd = ["exiftool", "-config", cfg, "-overwrite_original"]
        for k, v in rec["fields"].items():
            cmd.append("-XMP-%s:%s=%s" % (ns, _tag_name(k), v))
        if rec["tags"]:
            cmd.append("-XMP-dc:Subject=%s" % ", ".join(rec["tags"]))
        cmd.append(rec["image"])
        if dry_run:
            results.append({"image": rec["image"], "command": cmd})
            continue
        proc = subprocess.run(cmd, capture_output=True, text=True)
        # exiftool exits 0 on "0 image files updated" too - verify by reading back.
        check = subprocess.run(
            ["exiftool", "-config", cfg, "-s", "-s", "-s",
             "-XMP-%s:all" % ns, rec["image"]],
            capture_output=True, text=True)
        written = [l for l in check.stdout.splitlines() if l.strip()]
        results.append({
            "image": rec["image"],
            "ok": proc.returncode == 0 and len(written) == len(rec["fields"]),
            "tags_written": len(written),
            "tags_expected": len(rec["fields"]),
            "stderr": proc.stderr.strip(),
        })
    return {"config": cfg, "namespace": ns, "results": results}


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("photos", help="directory of full-resolution images (unzipped photo ZIP)")
    ap.add_argument("--photosheet", help="Photosheet_*.xlsx from the same date range")
    ap.add_argument("--sidecars", action="store_true", help="write IMG.jpg.json beside each image")
    ap.add_argument("--embed-xmp", action="store_true", help="write fields into XMP with exiftool")
    ap.add_argument("--dry-run", action="store_true", help="with --embed-xmp, print commands only")
    ap.add_argument("--manifest", help="write the full manifest here")
    args = ap.parse_args()

    manifest = build(args.photos, args.photosheet)
    if args.sidecars:
        manifest["sidecars_written"] = write_sidecars(manifest)
    if args.embed_xmp:
        manifest["xmp"] = embed_xmp(manifest, args.dry_run)
    if args.manifest:
        with open(args.manifest, "w", encoding="utf-8") as fh:
            json.dump(manifest, fh, indent=2, ensure_ascii=False)
    json.dump(manifest, sys.stdout, indent=2, ensure_ascii=False)
    print()


if __name__ == "__main__":
    main()
