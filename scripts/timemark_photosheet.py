#!/usr/bin/env python3
"""Read a Timemark "Photosheet" XLSX export.

The photosheet is the ONLY export that carries custom field values as structured
columns. Its embedded images are downscaled thumbnails - it is a data source, not
an image source.

The trap this exists to avoid: xl/media/imageN.jpg is NOT in row order. The
row a picture belongs to is declared in xl/drawings/drawing1.xml, and in a real
3-photo export the mapping was image1->row3, image2->row2, image3->row4. Zipping
media files to data rows by index silently attaches the wrong photo to every row.

Stdlib only - no openpyxl.
"""
import argparse
import json
import os
import re
import sys
import zipfile
import xml.etree.ElementTree as ET

MAIN = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
XDR = "{http://schemas.openxmlformats.org/drawingml/2006/spreadsheetDrawing}"
A = "{http://schemas.openxmlformats.org/drawingml/2006/main}"
REL = "{http://schemas.openxmlformats.org/package/2006/relationships}"
R = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"


def _shared_strings(z):
    try:
        root = ET.fromstring(z.read("xl/sharedStrings.xml"))
    except KeyError:
        return []
    out = []
    for si in root.findall(MAIN + "si"):
        out.append("".join(t.text or "" for t in si.iter(MAIN + "t")))
    return out


def _cell_text(c, strings):
    v = c.find(MAIN + "v")
    if v is None or v.text is None:
        if c.find(MAIN + "is") is not None:
            return "".join(t.text or "" for t in c.find(MAIN + "is").iter(MAIN + "t"))
        return ""
    if c.get("t") == "s":
        try:
            return strings[int(v.text)]
        except (ValueError, IndexError):
            return v.text
    return v.text


def _col_index(ref):
    letters = re.match(r"([A-Z]+)", ref).group(1)
    n = 0
    for ch in letters:
        n = n * 26 + (ord(ch) - 64)
    return n - 1


def read(path):
    with zipfile.ZipFile(path) as z:
        strings = _shared_strings(z)
        sheet = ET.fromstring(z.read("xl/worksheets/sheet1.xml"))

        rows = {}
        for row in sheet.iter(MAIN + "row"):
            idx = int(row.get("r"))
            cells = {}
            for c in row.findall(MAIN + "c"):
                cells[_col_index(c.get("r"))] = _cell_text(c, strings)
            rows[idx] = cells

        # Row 1 is the header. It enumerates the TEMPLATE's full field set, not
        # only the columns that happen to be populated - three of the eight
        # headers in the reference export had no data in any row. That makes the
        # header row the closest thing Timemark has to a template export.
        header_cells = rows.get(1, {})
        headers = [header_cells.get(i, "") for i in range(max(header_cells) + 1)] \
            if header_cells else []

        # Image anchors: authoritative row for each media file.
        anchors = {}
        try:
            relroot = ET.fromstring(z.read("xl/drawings/_rels/drawing1.xml.rels"))
            targets = {r.get("Id"): os.path.normpath(
                os.path.join("xl/drawings", r.get("Target")))
                for r in relroot.findall(REL + "Relationship")}
            draw = ET.fromstring(z.read("xl/drawings/drawing1.xml"))
            for anchor in draw.iter(XDR + "twoCellAnchor"):
                frm = anchor.find(XDR + "from")
                row0 = int(frm.find(XDR + "row").text)   # 0-based
                blip = anchor.find(".//" + A + "blip")
                if blip is None:
                    continue
                rid = blip.get(R + "embed")
                if rid in targets:
                    anchors[row0 + 1] = targets[rid].replace(os.sep, "/")
        except KeyError:
            pass

        records = []
        for idx in sorted(k for k in rows if k > 1):
            cells = rows[idx]
            fields = {}
            for col, name in enumerate(headers):
                if not name or name == "Photo":
                    continue
                val = cells.get(col, "")
                if val != "":
                    fields[name] = val
            records.append({
                "row": idx,
                "date": fields.pop("Date", None),
                "time": fields.pop("Time", None),
                "fields": fields,
                "thumbnail_part": anchors.get(idx),
            })

    return {
        "source": os.path.basename(path),
        "template_fields": [h for h in headers if h and h not in ("Photo", "Date", "Time")],
        "headers": headers,
        "records": records,
    }


def extract_thumbnails(path, outdir):
    """Write each thumbnail out named for the row it is actually anchored to."""
    data = read(path)
    os.makedirs(outdir, exist_ok=True)
    written = []
    with zipfile.ZipFile(path) as z:
        for rec in data["records"]:
            part = rec["thumbnail_part"]
            if not part:
                continue
            ext = os.path.splitext(part)[1] or ".jpg"
            dest = os.path.join(outdir, "row%02d%s" % (rec["row"], ext))
            with open(dest, "wb") as fh:
                fh.write(z.read(part))
            written.append(dest)
    return written


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("xlsx")
    ap.add_argument("--extract-thumbnails", metavar="DIR",
                    help="write anchored thumbnails to DIR as rowNN.jpg (low-res)")
    args = ap.parse_args()

    data = read(args.xlsx)
    if args.extract_thumbnails:
        data["thumbnails_written"] = extract_thumbnails(args.xlsx, args.extract_thumbnails)
    json.dump(data, sys.stdout, indent=2, ensure_ascii=False)
    print()


if __name__ == "__main__":
    main()
