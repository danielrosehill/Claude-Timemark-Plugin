#!/usr/bin/env python3
"""Parse the Timemark filename encoding.

    2026-09-01 14.12.23__(Test! )_(Item No-2)_(Item Description-Flip flops).jpg
    <---- timestamp ---->  <tag>   <---------- fields ---------------->

The filename is the only machine-readable copy of the field values that travels
*with* the image, so it is the join key of last resort. Emits JSON.
"""
import argparse
import json
import os
import re
import sys

TS_RE = re.compile(r"^(\d{4}-\d{2}-\d{2}) (\d{2})\.(\d{2})\.(\d{2})")
GROUP_RE = re.compile(r"\(([^()]*)\)")


def parse(name, known_fields=None):
    """name -> dict. known_fields disambiguates tags from hyphen-free field names."""
    stem = os.path.splitext(os.path.basename(name))[0]
    out = {"filename": os.path.basename(name), "timestamp": None,
           "date": None, "time": None, "fields": {}, "tags": [], "unparsed": []}

    m = TS_RE.match(stem)
    if m:
        out["date"] = m.group(1)
        out["time"] = "%s:%s:%s" % (m.group(2), m.group(3), m.group(4))
        out["timestamp"] = "%s %s" % (out["date"], out["time"])
        rest = stem[m.end():]
    else:
        rest = stem

    for group in GROUP_RE.findall(rest):
        # A field renders as "Key-Value"; a tag renders as "Tag " (trailing space,
        # no hyphen). Split on the FIRST hyphen only - values contain hyphens far
        # more often than keys do.
        if known_fields is not None:
            hit = next((f for f in known_fields if group.startswith(f + "-")), None)
            if hit:
                out["fields"][hit] = group[len(hit) + 1:].strip()
                continue
            if group.strip() in (known_fields or []):
                out["fields"][group.strip()] = ""
                continue
            out["tags"].append(group.strip())
            continue
        if "-" in group:
            key, value = group.split("-", 1)
            out["fields"][key.strip()] = value.strip()
        elif group.strip():
            out["tags"].append(group.strip())
        else:
            out["unparsed"].append(group)
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("paths", nargs="+", help="image files or directories")
    ap.add_argument("--fields", help="comma-separated known template field names, "
                                     "normally the photosheet header row")
    args = ap.parse_args()

    known = [f.strip() for f in args.fields.split(",")] if args.fields else None
    known = sorted(known, key=len, reverse=True) if known else None

    files = []
    for p in args.paths:
        if os.path.isdir(p):
            files += [os.path.join(p, f) for f in sorted(os.listdir(p))
                      if f.lower().endswith((".jpg", ".jpeg", ".png"))]
        else:
            files.append(p)
    if not files:
        sys.exit("no image files found")
    json.dump([parse(f, known) for f in files], sys.stdout, indent=2, ensure_ascii=False)
    print()


if __name__ == "__main__":
    main()
