# Auditing Brand and Product Visibility in AI Shopping Recommendations

## A Methodological Framework with an Illustrative Application

Manuscript ID: `jtaer-4673189`  
Repository documentation: second revision

This repository supports a methodological framework for measuring brand and product representation in AI-assisted shopping responses. It distinguishes inclusion, prominence, evidential presentation, and recurrence across repeated conditions. The framework does not measure consumer purchases, trust, market outcomes, or generative engine optimization (GEO) effectiveness.

## Second-revision materials

The second revision introduces a prospective coding protocol and a fully disclosed constructed demonstration. The new demonstration is the main illustrative application; the earlier processed archive is retained separately for historical computational inspection. The two datasets are not pooled.

The following paths describe the intended repository layout for the second-revision deposit. Existing repository files should be retained.

| Path | Contents |
| --- | --- |
| `Data-and-analysis/` | Earlier processed archive and associated analysis materials |
| `revision_supplement/` | First-revision analytical codebook, pinned query-level input, sensitivity checks and results |
| `round2_supplement/prospective_protocol.pdf` | Prospective acquisition and coding protocol (S3) |
| `round2_supplement/prospective_protocol.tex` | Protocol source |
| `round2_supplement/protocol_summary.json` | Machine-readable protocol summary |
| `round2_supplement/demo/` | Complete executable constructed demonstration, inputs, outputs and verification records |
| `query_appendix.pdf` | Full historical query instrument (S1) |
| `revision_supplement/analytical_codebook.pdf` | Historical analytical codebook (S2) |
| `constructed_demonstration.pdf` | Constructed demonstration and worked examples (S4) |
| `legacy_archive.pdf` | Earlier archive methods, results and worked comparison (S5) |

## New constructed demonstration (S3–S4)

All 32 answers, product identities, attributes, source documents and scenario differences are deliberately constructed. No commercial AI platform was queried and no external website was retrieved for this example. No human coder produced the demonstration labels.

The design crosses two shopping needs, two wording variants, two constructed scenarios (X and Y), two ordered snapshot positions and two repetitions. Scenario labels do not identify real platforms, and snapshot positions do not represent dates. The construction is deterministic, with no random seed required.

The prospective protocol defines entity resolution at brand, strict-product and product-family levels; display and recommendation order; the five recommendation-strength levels (0–4); decision roles; evidence classification; ambiguity handling; and procedures for future independent coding and disagreement resolution. These are new rules for prospective use, not recovered historical coding instructions.

### Reproduce the demonstration

Python 3.10 or later is required. The demonstration was tested with CPython 3.12.14 and uses only the Python standard library. No credentials, API access or internet connection are required.

From the repository root:

```sh
cd round2_supplement/demo
python run_all.py
python verify_reproducibility.py
```

The first command regenerates the constructed inputs, codes the retained texts and recomputes the results and LaTeX fragments. The second checks deterministic reproduction across two runs. These commands do not read or modify the historical archive.

| File or directory (relative to `round2_supplement/demo/`) | Purpose |
| --- | --- |
| `README.md` | Detailed construction rules, coding logic, denominators and audit instructions |
| `fixture_spec.json` | Complete deterministic construction specification |
| `build_inputs.py` | Generates fictional answers and evidence documents |
| `run_demo.py` | Parses the constructed texts, applies coding rules and calculates indicators |
| `run_all.py` | Runs the complete pipeline |
| `verify_reproducibility.py` | Compares deterministic outputs across runs |
| `inputs/` | Exact prompts, 32 complete answers, entity dictionary, source index and 12 available fictional source documents |
| `results/` | Coded responses, annotation traces, claim bundles and atoms, paired comparisons, agreement and summary tables |
| `main_results.tex`, `overview.tex` | Generated LaTeX fragments |
| `manifest.json`, `runtime.json`, `reproducibility.json` | File hashes, runtime details and reproduction checks |

The evidence frame consists of 32 designated citation-linked claim bundles, including 10 deliberately inaccessible links. The 22 assessable bundles contain 44 assessable atomic claims. Support is evaluated against the supplied fictional documents, not external web pages or real product facts.

Two explicitly defined coding procedures demonstrate how different rules affect agreement statistics. Their agreement and kappa values are algorithmic examples, not evidence of human inter-rater reliability. The parser is designed for the published finite grammar, not unrestricted natural-language coding.

The packaged verification records report 52 fixed-value and boundary checks and byte-identical results for 62 generated files across two complete runs. These checks establish computational consistency for the constructed example; they do not establish external validity or operational performance.

## Earlier processed archive (S1–S2 and S5)

The historical archive contains 2,400 processed response records: 40 base queries across wireless headphones, robot vacuum cleaners, laptops and sunscreen, with two wording variants, two coded configurations (A and B), five ordered archive snapshots and three repetitions per condition.

The original platform outputs, provider and model identities, acquisition timestamps, raw-to-processed mappings, original source URLs and historical coding procedures are unavailable. A and B identify archived record groups rather than identified providers. Archive snapshots are not verified acquisition dates. Source identifiers are pseudonymous codes, and support classifications refer only to retained excerpts. Agreement between stored label streams is not validated human coder reliability.

The archive is not relabelled as synthetic because its original production history has not been established. Reproducing calculations from its processed files does not authenticate its origin. It is retained separately from the new constructed demonstration and is not evidence of the behavior of operational AI systems.

The original query instrument contains 40 base queries and 80 wording variants. Relevant files under `Data-and-analysis/data/` include `base_queries.csv`, `queries.csv`, `prompt_instructions.txt`, `response_texts.jsonl`, `responses.csv`, `items.csv`, `entity_dictionary.csv`, `sources.csv`, `source_documents.jsonl`, `claim_frame.csv`, `claim_validation.csv` and the paired-label files.

### First-revision sensitivity calculations

The existing-data supplement uses the query-level export `Data-and-analysis/results/query_means.csv` at the pinned commit `8d70a5dcf3ecb4409d1fdcd0b9861a170822d87e`.

- Git blob SHA-1: `0948c9267bfc87f8fa7ccb0b64ab1210964dbbae`
- Input SHA-256: `d2e8c202dd29d35af007a4020221b8717a915e6c19a8d9f8144acd2685b33a78`

From the repository root, use the environment specified in the supplement (tested with Python 3.13.5):

```sh
cd revision_supplement
python -m pip install -r requirements.txt
python revision_checks.py
```

The script checks the input hash before running the category-level sensitivity calculations. Bootstrap settings are 5,000 replicates and seed 20261114. It does not regenerate the original platform responses or replace the original primary analyses. See `revision_supplement/README.md` for the exact output definitions and interpretation limits.

## Interpretation and reuse

The framework specifies a measurement procedure. The new constructed example demonstrates its application and arithmetic under known conditions; the historical archive permits inspection of earlier computations. Neither establishes external operational validity, population-wide generalizability, causal effects of wording, consumer behavior or GEO effectiveness. A future operational study requires traceable acquisition, independent coding where appropriate, and verifiable source context.

## Archiving and citation

Repository: https://github.com/onurdogannet/GEO-Research-Data

Use the version-specific DOI of the Zenodo release containing the files used in your analysis, and record the corresponding GitHub release or commit. The second-revision DOI and release identifier should be added here once the updated archive has been published. Earlier versions should remain available for reproducibility.
