JTAER GEO – Processed Dataset and Reproduction Code
===================================================

CONTENTS
Data-and-analysis/data/      Retained processed data and linked coded text records
Data-and-analysis/code/      Analysis implementation
Data-and-analysis/tests/     Internal integrity and consistency tests
Data-and-analysis/results/   Recomputed results, tables, summary and input checksums
figures/                     Recomputed figures in PDF
 generated/                  Recomputed LaTeX table fragments and macros

HOW TO RUN (Python 3.10+)
python -m pip install -r requirements.txt
python Data-and-analysis/code/analyze.py
python -m unittest discover -s Data-and-analysis/tests -p 'test_*.py' -v

Start in the repository root. Analysis runs offline; no APIs or platform accounts are accessed. Output files are replaced by each analysis run. Bootstrap uses 5000 repetitions with seed 80426. The full observed process cannot be rerun with this archive.

IMPORTANT EVIDENCE BOUNDARY
The author reports that the study used real platform observations, but original raw platform responses, original URLs, platform/version identifiers and collection timestamps are not retained in the supplied archive. Platform labels A/B and the five waves cannot be independently tied to a named model or actual acquisition date. The dataset also contains highly standardized response wording and coded brand/product names. This repository cannot determine whether or how those records were transformed from original platform output.

The recorded source identifiers SRC_001...SRC_028 are coded values. They do NOT identify verifiable Internet domains, and independent website-level/source-independence claims cannot be checked. Stored evidence texts in source_documents.jsonl are retained processed records, NOT independently fetched web pages. Sampled support labels are reproduceable as counts, but their correctness against contemporaneous external sources cannot be independently checked.

The included tests assess structure, consistency and computational integrity. They do not verify external provenance, collection design, coding validity, originality of platform responses or truth of claimed evidence.

PUBLICATION CAUTION
Publish only after the author verifies that the archive is authorized for release, contains no confidential data, and the final manuscript describes this evidence boundary accurately. If DOI archiving, archive one tested release/tag rather than a moving GitHub branch. Do not describe this archive as original/raw platform responses. No unsupported provenance, real website addresses or acquisition dates have been reconstructed.

RESULTS
The results/summary.json records aggregate counts and computation parameters. The results/ CSVs, figures/ PDF plots and generated/ LaTeX values are recalculated from the preserved processed files. The script does not reconstruct original observations.
