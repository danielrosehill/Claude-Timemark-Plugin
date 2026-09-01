# Reference fixtures

From a 3-frame Timemark export captured 2026-09-01 on a OnePlus CPH2493,
Timemark v10.0.210. Images themselves are not committed — the shapes are what
matters.

| File | What |
|---|---|
| `reference-manifest.json` | `timemark_ingest.py` output for the reference set: 3 images, 3 photosheet rows, 3 joined, 0 conflicts |
| `photosheet-anchors.xml` | the `drawing1.xml` fragment showing image→row anchors out of media-file order |

`reference-manifest.json` is the shape to expect from a clean join. Note
`template_fields` carries all five template fields while only two are ever
populated — that is the header row acting as a template definition.
