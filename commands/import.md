---
description: Import a Timemark photo set - gate the inputs, join, then archive and/or burn in
argument-hint: [directory containing the Timemark photos and exports]
allowed-tools: Read, Write, Bash(python3 *), Bash(unzip *), Bash(exiftool *)
---

Import the Timemark photo set in $1 (default: the current directory).

1. Read the `timemark-import` skill and run its gate. Inventory what is present:
   original JPEGs or a `Photos_from_Timemark_*.zip`, a `Photosheet_*.xlsx`, a
   `Work Report_*.pdf`.
2. **If either the images or the photosheet is missing, stop and say so.** Name
   what is missing, say what it costs, and ask for it — the photos are usually
   still on the phone at this point and will not be later. Do not proceed with a
   partial set to be helpful.
3. If a photo ZIP is present, unzip it, preserving filenames verbatim.
4. Run `scripts/timemark_join.py` and report the `counts` block. Explain any
   non-zero `images_without_a_row`, `rows_without_an_image` or
   `conflicting_values` before going further.
5. Ask which output is wanted — archive, burn-in, or both — then follow
   `timemark-archive` and/or `timemark-burn-in`.

Never rename an image. Tags exist only in the filename.
