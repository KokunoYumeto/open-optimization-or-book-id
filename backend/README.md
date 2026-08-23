# Modular backend v0 — complete R017/O018 Book 1 corpus

This directory is the locale-neutral machine layer for the complete Indonesian
edition of *Mathematical Programming and Operations Research, Book 1* (R017)
and its separately attributed free/open-solver laboratory (O018). The backend
is additive: it does not rewrite the pinned authority, silently change the
book’s mathematics, or represent unfinished Book 2 as advanced optimization
coverage.

## Authority and authored inputs

- `input/backend-input.json` is the original v0 authored record set.
- `input/full-corpus-supplement.json` adds the complete later-book topology,
  terminology, exact component bindings, and closure-digested O018 labs.
- `schema/backend-input-v0.schema.json` validates the merged v0 input contract.
- `schema/full-corpus-supplement-v0.schema.json` validates the additive input.
- `schema/modular-backend-v0.schema.json` validates the consolidated export.

R017 is source-bound to `open-optimization/open-optimization-or-book` commit
`1745df89b608899f66983834fa4ec8c8910d18ff`, tree
`209d5de696ebac4e5921b73d6b6b2f539fc23d1c`, and archive SHA-256
`4bee88ed3af700b16d5643a3c18b9846244d3467eec7f4fb1f009a782b9143fc`.
Every admitted source file is independently hash-checked against that frozen
authority. Every release target and locally authored O018 component is also
hash-bound; `--require-bound-targets` refuses any unbound or drifted target.

## Complete admitted scope

The export covers the title and front matter; Introduction; Chapters 1–15;
all localized manuals for Chapters 2–15; the integrated equations, systems,
matrices, and vectors appendices; software resources; checkpoint answers;
further reading; attribution/contributor material; bibliography; and generated
index. The final built Book 1 PDF is an exact artifact record, not an inferred
page-count claim.

O018 includes the earlier admitted laboratory surfaces and the complete
Chapter 5–15 sequence: graphical LP, formal mathematics, simplex Chapters 7–9,
sensitivity analysis, duality, Python workflow, multiobjective optimization,
graph algorithms, and integer programming. Each Chapter 10–15 lab directory is
closed by a deterministic path/byte/SHA-256 manifest. Its README and
attribution are translatable units; every exercise in `results.json` is a
stable unit; every code, data, result, test, verifier, receipt, and accessible
SVG is a component asset; and the results/receipt artifacts are verified again
from local bytes during export.

## Stable identity, segmentation, and relations

IDs derive from corpus topology, immutable labels, and stable ordinals—not
translated titles or rendered page numbers. Earlier R017 files retain strict
source/target block alignment with explicit reviewed overrides. Later files
whose Indonesian reflow merged or split physical paragraphs use the explicit
`target_projection` mode: each localized block and structural node is still
independently selectable, while its source relationship remains bound honestly
to the exact upstream file rather than an invented paragraph pairing.

The export preserves hierarchy/order, source and target locators and hashes,
concept and prerequisite mappings, approved Indonesian terminology, exercise
and manual-solution links, O018-to-R017 adaptation labels, asset/code/data
dependencies, rights components, corrections, upstream-report disposition,
typed QA/build evidence, and deterministic artifact identities. Component
rights distinguish CC BY-SA 4.0 text/data, MIT code, third-party appendix and
graph material, open runtimes, and proprietary dependencies that are recorded
but not redistributed.

Three bounded R017 image directories are independently closure-inventoried in
addition to per-segment asset references. O018 lab closure generation excludes
only recreatable Python bytecode/cache files.

## Deterministic build and verification

From the lane root, using any supported Python 3 interpreter:

```powershell
python .\scripts\export_backend.py --show-target-hashes
python .\scripts\export_backend.py --require-bound-targets
python .\scripts\export_backend.py --require-bound-targets --check
```

For an independent clean replay, write the same export in a new bounded
directory and compare its 32 files byte-for-byte with `backend/dist`:

```powershell
python .\scripts\export_backend.py --require-bound-targets --output-dir backend\replay-final
python .\scripts\export_backend.py --require-bound-targets --check --output-dir backend\replay-final
```

The exporter uses only the Python standard library. Before writing, it
validates all three schemas, source/target/rights/artifact hashes, global IDs,
referential integrity, topology, common JSONL fields, CSV widths, and every
local verified artifact. It serializes the complete result twice in memory and
fails on any byte difference. `--check` regenerates in a new process and
compares every declared byte with the selected output tree.

`dist/backend-v0.json` is the lossless consolidated view. `dist/jsonl/` has one
stream per entity class. `dist/csv/` has deterministic exchange projections,
including `exercise_links.csv`; nested values use canonical JSON strings.
`dist/manifest.json` records byte lengths and SHA-256 values for every generated
data file, and `dist/SHA256SUMS.txt` hashes the manifest without a
self-referential digest.

The backend records the reader’s actual accessibility evidence. The PDF has
localized metadata, searchable embedded Unicode fonts, valid navigation, and
alternative-text marked content, but remains truthfully `Tagged=no`; no PDF/UA
claim is made.
