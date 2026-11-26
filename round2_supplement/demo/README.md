# Constructed demonstration for the second revision

## What this package establishes

This is a **new, fully disclosed, author-constructed synthetic example**. All
shopping answers, product names, product attributes, sources, and scenario
differences were deliberately constructed. No commercial AI platform was queried,
no website was retrieved, and no human coder produced these labels. This example
does not rename, repair, or authenticate the original archive of 2400 records.

The package shows a complete path from a finite construction specification,
through retained plain-text answers and evidence documents, to auditable coding,
paired calculations, and manuscript tables. Its results verify the example's
arithmetic and demonstrate the procedure. They do not establish performance of
real systems, human inter-rater reliability, measurement validity, consumer
effects, temporal stability, or an optimization effect.

## Run

Use Python 3.10 or later. The package uses only the standard library and runs
offline. From this directory:

```sh
python run_all.py
```

This regenerates `inputs/`, recomputes `results/`, and rewrites the generated
LaTeX fragments and manifest. To verify two independent command invocations
produce identical deterministic files in the current runtime:

```sh
python verify_reproducibility.py
```

The verified interpreter is recorded in `runtime.json`; a successful two-run
check produces `reproducibility.json`. No installation of packages or credentials
is required. Inputs and outputs of the historical archive are never read or
modified by these commands.

## Explicit construction recipe

`fixture_spec.json` supplies the complete specification. There are two authored
shopping needs (`QD01`, everyday listening; `QD02`, commuting), two paraphrases,
two scenarios (`X`, `Y`), two ordered snapshot positions, and two replicates.
The full crossing produces 32 fictional answers. Snapshots are arbitrary
constructed positions, not recorded dates or simulated acquisition intervals.
Scenarios are authored conditions, not provider names or disguised platforms.

For zero-based indices `q,w,s,r` in `{0,1}` and `c=0` for X / `c=1` for Y:

| Construction decision | Exact rule |
| --- | --- |
| Display list | Pattern `(2*q+w+2*s+r) % 4` within the scenario's explicit four-list specification |
| Advice template | Level `(q+2*w+s+r+c) % 5` |
| Source case | `(q+w+s+r+c) % 4` |
| Positive recommendation order | Last displayed product, then first displayed product |
| Single overall choice | Level 4, or level at least 2 with query index 0 |
| Separate prioritization sentence | Odd display-pattern index |
| Surface form | Canonical name for wording 0; declared alias for wording 1 |

There is no randomness and therefore no random seed. The recipe deliberately
varies the properties needed for the calculations; it is not a fitted model of
any platform's behavior. All four display patterns occur four times per scenario.

`build_inputs.py` generates the answer text and source documents from these rules.
`run_demo.py` then reads the resulting files. It obtains the reported codes by
parsing the retained text, not by importing the construction indices as labels.
The fixed analytic expectations in `manual_checks()` are independently stated
fractions and counts rather than assertions comparing a result to itself.

## Entities and decision roles

`inputs/entities.json` includes canonical product, brand and family identifiers,
exact names and aliases. DemoAlpha One standard and DemoAlpha One extended are
two strict products within one declared family and brand. DemoBeta Solo and
DemoGamma Mini have separate brands and families. These are fictional entities.

The parser recognizes the finite published grammar only. It is not a general
natural-language coder. Unrecognized advice, conflicting categorical choices,
unresolved advice targets, and mismatched focal claim/source identities cause
an error. Unknown displayed products are flagged and are not silently given
strict-product IDs; an explicitly recognizable brand can still be retained.

Information requires a descriptive property, not a name-only list. Every core
answer has a battery/warranty description and an explicit numeric comparison.
Prioritization requires the separate criterion-specific advantage sentence and
is not inferred from the presence of a recommendation. Positive direct advice
and single-best selection have separate fields. Declared aliases are merged
within a response. Negative advice and tied recommendations are retained in the
boundary checks. Display order and positive recommendation order remain separate.

The new prospective strength rules are represented by these controlled templates:

| Level | Template cue | Direct recommendation |
| ---: | --- | ---: |
| 0 | No positive advice sentence | 0 |
| 1 | `You could choose ... if ...` | 1 |
| 2 | `I recommend ...` | 1 |
| 3 | `I strongly recommend ...` | 1 |
| 4 | `Choose ...; ... is clearly the best overall option for these needs.` | 1 |

These rules belong to the new demonstration and prospective protocol. They are
not claimed to reproduce undocumented thresholds in the original archive.

## Claim frame and evidence

The frame is a **census of the 32 designated citation-linked bundles**, exactly
one per answer. Each bundle asserts battery life and warranty for one product.
Other descriptive comparison statements are outside this explicitly restricted
frame. The reported support percentages therefore do not measure support for
every factual sentence in the answers.

Each product has four source locators. Three point to retained complete fictional
documents and one is deliberately unavailable. Thus there are 16 source
locators, 12 source files, and 32 response-specific claim-source links. The four
cases provide:

1. Exact battery and warranty values: `E+E`, full support.
2. Exact battery; warranty not stated: `E+N`, partial support.
3. A contradictory battery; exact warranty: `C+E`, unsupported.
4. No document: inaccessible, with no invented assessable atomic codes.

`E` means supported, `N` means not established, and `C` means contradicted.
Any material contradiction has priority at bundle level. All `N` would also
give unsupported under the declared rule. Complete source text is preserved;
the excerpt is the contiguous product/battery/warranty block, selected by a
deterministic rule. UTF-8-decoded Unicode character offsets are zero-based and
end-exclusive. Hashes refer to the original file bytes. No fictitious URL or
retrieval timestamp is presented as a real one.

There are 22 assessable bundles and 10 inaccessible bundles, giving 44 assessable
atomic records. The source type is read from declared fictional publisher-type
metadata, not inferred from a verified publisher. Missing document types remain
unavailable. The bundle denominator is 32, including inaccessible links;
assessable-only denominators are recorded separately.

## Two explicitly constructed procedures

Procedure A applies the declared prospective rules to the controlled grammar.
Procedure B is a deliberately coarser procedure using the same parsed input:

- It discards tentative level-1 advice and maps level 3 to level 2. The level
  mapping is exactly `{0:0, 1:0, 2:2, 3:2, 4:4}`; its direct-advice field is 1
  only when that mapped score is positive.
- Its evidence rule treats **any** supported atom as sufficient for full support,
  even when another material atom is unestablished or contradicted. This is an
  intentionally permissive alternative, not the recommended protocol.
- Both keep a missing source inaccessible.

The streams are algorithmically related and were never independent human coding.
Their raw agreement and kappa values demonstrate the effect of an explicit rule
difference. They cannot be used as evidence of coder reliability, validity, or
external truth. Stored labels include their construction origins. No adjudication
session is claimed. A future human coding study must use the prospective protocol's
independence, training, sampling and adjudication records.

Nominal Cohen kappa is used for direct advice and bundle support. Linear distance
weights `abs(a-b)/4` are used for the 0–4 strength scale. A zero expected
disagreement yields undefined kappa, not a value of one. No confidence intervals
or significance tests are computed for these authored finite records.

## Paired conditions and denominators

Each contrast changes only one stored index while holding query, scenario and
the other indices fixed. With two levels of the changed index, each scenario
has eight pairs for repetitions, eight for wording and eight for adjacent
snapshots. Product and brand Jaccard use canonical presence sets. A joint-empty
pair is undefined and a one-empty pair is zero. First-recommendation agreement
includes only pairs with a unique first positive recommendation in both answers;
its eligible count is reported. A tied first group does not acquire an arbitrary
winner. The optional finite-prefix order statistic uses decay 0.9 and the
shorter list length; it is not an extrapolated rank-biased-overlap estimator.

## Outputs and audit path

| File | Purpose |
| --- | --- |
| `inputs/record_index.csv` | Prompts, exact construction coordinates, raw-answer paths and origin |
| `inputs/responses/*.txt` | All 32 complete fictional answer texts |
| `inputs/source_index.csv` | All fictional source locators, local paths and availability |
| `inputs/sources/*.txt` | All 12 complete available fictional documents |
| `results/coded_responses.csv` | Canonical entities, five roles, strength, order, evidence class |
| `results/annotation_trace.jsonl` | Input hashes, response spans, source spans, atom values and decisions |
| `results/claim_bundles.csv` | All 32 source-linked bundles and excerpt offsets |
| `results/claim_atoms.csv` | 44 assessable atomic decisions with evidence spans |
| `results/constructed_label_streams.csv` | Explicit procedures A and B with origin fields |
| `results/condition_pairs.csv` | All 48 declared pairs and eligibility |
| `results/scenario_summary.csv` | Breadth, appearance distributions and support counts |
| `results/overlap_summary.csv` | Eight-pair summaries for each scenario and contrast |
| `results/algorithm_agreement.csv` | Raw agreement and appropriate kappa coefficients |
| `results/summary.json` | Machine-readable complete summary |
| `results/verification.json` | Named fixed-value and boundary checks |
| `main_results.tex` | Three generated manuscript tables, using the host's revision environment |
| `overview.tex` | Include-friendly explanatory supplement text |
| `manifest.json` | SHA-256 hashes for scripts, specification, inputs and deterministic outputs |

Two concrete examples are `D_QD01_W0_X_S0_R0` (two brands, two products, no
positive advice, full support) and `D_QD01_W0_X_S0_R1` (one brand, two strict
products, one family, tentative advice for the last-displayed product, partial
support). Their full text, fictional source, coded row and exact spans can be
followed directly through the output paths above.

The independent arithmetic checks include 68 brand appearances, 80 strict-product
appearances, brand means of `7/4` and `5/2`, brand HHI of `17/49` and `17/50`,
strict-product HHI `1/4` in each scenario, and kappas `11/19`, `3/4`, and `35/99`.
Those checks are software/construction checks, not scientific external validation.
