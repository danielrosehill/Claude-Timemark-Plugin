---
description: Ingest a Timemark export set into full-resolution images plus JSON sidecars
argument-hint: [directory containing the Timemark exports]
allowed-tools: Read, Write, Bash(python3 *), Bash(unzip *), Bash(exiftool *)
---

Ingest the Timemark export set in $1 (default: the current directory).

1. Inventory what is present: `Photos_from_Timemark_*.zip`, `Photosheet_*.xlsx`,
   `Work Report_*.pdf`, loose JPEGs.
2. Read the `timemark-export-triage` skill and say what the available routes can
   and cannot deliver. If either the photo ZIP or the photosheet is missing, say
   so up front — that is a gap only a re-export from the phone can close.
3. Unzip the photo ZIP, preserving filenames verbatim.
4. Run `scripts/timemark_ingest.py` with `--sidecars` and `--manifest`.
5. Report the `counts` block and explain any non-zero
   `images_without_a_row`, `rows_without_an_image` or `conflicting_values`.

Do not rename any image.
