# DECISIONS.md — dated log of every data and method decision

Every data decision (thresholds, drops, substitutions, groupings, imputation)
gets a dated entry with a one-line rationale. Hugh reviews and approves all
entries.

---

## 2026-07-08 — Environment: venv + pip with pinned requirements.txt

`uv` is not installed on this machine, so per CLAUDE.md the fallback applies:
`python -m venv .venv` + `requirements.txt` with exact pinned versions.
Python 3.14.0 (system). *Rationale: CLAUDE.md's documented fallback; keeps
fresh-clone reproducibility via pinned versions.*

**Status: approved by Hugh (Phase 0 gate, 2026-07-09)**

## 2026-07-08 — GSV (Victoria) statewide extract evaluated and rejected

Hugh downloaded the GSV borehole + geochemistry statewide collections instead
of SARIG. Profiling showed 5,090 borehole-assay samples across 183 holes, of
which only 11 holes have lithology logs (454 assayed samples within them) —
far below the ≥10,000-sample / ≥30-hole target; the surface geochem collection
is 86% soil / 13% stream sediment, unsuitable for bedrock lithology
classification. *Rationale: fails brief minimums on both routes; reverting to
the documented primary source (SARIG per-map-sheet packages). Files removed
from `data/raw/`.*

**Status: approved by Hugh (dataset call, 2026-07-08)**

## 2026-07-08 — Dataset selected: SARIG Data Package statewide export

Hugh downloaded the statewide SARIG Data Package (GSSA / SA Geodata CSV
export from dem-sdp.s3-ap-southeast-2.amazonaws.com; the per-map-sheet route
was too hard to locate). Key tables: `sarig_rs_chem_exp.csv` (long-format
geochemistry, 22 GB), `sarig_dh_litho_exp.csv` (interval lithology logs),
`sarig_dh_details_exp.csv`. 47,349 holes flagged with both geochemistry and
lithology logs. Licence: CC-BY 4.0 (`Disclaimer and CCBY.txt` in data/raw).
*Rationale: primary source per brief; statewide variant only affects file
size, not content. Dataset locked — no further shopping.*

**Status: approved by Hugh (Phase 0 gate, 2026-07-09)**

## 2026-07-09 — Phase 0 gate passed; label source = sample-level lithology

Hugh reviewed `reports/data_profile.md` and confirmed the dataset workable.
Target labels come from the sample-level `LITHO_CODE`/`LITHOLOGY_NAME` in
`sarig_rs_chem_exp.csv` (81,697 drillhole-linked labelled samples), not from
an interval-log join. *Rationale (Hugh): sample-scale label is more accurate;
avoids interval smearing. Claude to verify labelled-hole count ≥30 in
Phase 1.*

**Status: approved by Hugh (2026-07-09)**

## 2026-07-09 — Class-scheme direction for the Phase 1 lookup table

Hugh proposed categorising as overburden / interburden / basement. Three
classes conflicts with CLAUDE.md rule 4 (5–8 groups), so the agreed approach:
the lookup table carries Hugh's three-way **tier** column *plus* a final
class column with 5–8 groups (cover collapsed, basement split
lithologically). Claude drafts, Hugh edits and approves in Phase 1.
*Rationale: keeps the practical tiering without gutting the confusion-matrix
and interpretation artefacts.*

**Status: direction agreed; lookup table itself pending Hugh's approval**

## 2026-07-17 — Censored-value handling: DL/2 substitution with flags

`"<x"` → x/2 with flag `below`; `">x"` → face value with flag `above`;
negative raw values → missing with flag `negative`; unparseable strings →
missing with flag `unparsed`. Nothing coerced or dropped silently; flags are
carried per element into clean.parquet. *Rationale: DL/2 is the standard
simple substitution; the flag columns preserve censoring information for
the model and for the limitations section (formal censored-data methods are
a documented non-goal).*

**Status: approved by Hugh (2026-07-17)**

## 2026-07-17 — Unit harmonisation to ppm

% ×10,000; ppb ÷1,000; g/T ≡ ppm. Rows in non-mass-fraction units (cps,
us/cm, mg/L, ug/L, NOUNIT — ~0.01% of analyses) are unconvertible and
excluded from the pivot. *Rationale: single unit basis is required before
any compositional treatment; the excluded units measure properties, not
concentrations.*

**Status: approved by Hugh (2026-07-17)**

## 2026-07-17 — Duplicate analyses: median, preferring uncensored

Where a sample has multiple analyses of the same element (repeat/check
assays, multiple labs), the median is taken; censored measurements are
ignored when an uncensored one exists. *Rationale: median is robust to
single bad assays; a real measurement always beats a detection-limit
substitute.*

**Status: approved by Hugh (2026-07-17)**

## 2026-07-17 — Element suite F: Cu, Zn, Pb, Co, Ni, Fe, Mn

Deviation from the brief's default rule (drop elements >40% missing), which
would keep only Cu, Zn, Pb, Ag. Complete-case trade-off computed across
seven candidate suites; F chosen because (a) every element has <13%
censoring — Ag (59% below-DL) and Au (52%) were rejected as features that
are half detection-limit placeholders, and (b) it retains 20,024
complete-case samples across 3,424 holes with all seven classes ≥1,314
samples. *Rationale: more chemical dimensions than the 4-element default,
without the sample collapse of the 11-element suite (9,913) or the
censoring load of Ag/Au.*

**Status: approved by Hugh (2026-07-17, suite F chosen explicitly)**

## 2026-07-17 — Lithology lookup finalised: SARIG ROCK_GROUP aggregation

The 255 raw codes are consolidated to 7 classes by aggregating SARIG's own
ROCK_GROUP taxonomy (see `src/lithoclass/make_lookup.py`, which regenerates
`data/lith_lookup.csv` reproducibly), with three documented supplements:
(1) unconsolidated sediment names (sand, clay, silt, gravel, soil) are
transported cover, not basement clastics — SARIG groups sand with
sandstone; (2) metamorphosed rocks with known igneous protolith composition
class with that composition (metabasalt → mafic) since igneous chemistry
survives metamorphism, while metasediments and undifferentiated
metamorphics form the Metamorphic class; (3) codes whose chemistry reflects
process rather than protolith (alteration, mineralisation, ore, fault
rocks, undifferentiated breccia) are excluded (keep=N, 3,036 samples), as
are organics (coal/lignite) and iron formations (too few complete-case
samples). Per-code reasoning is in the `note` column. Classes:
Transported cover / In-situ regolith / Clastic sediment /
Carbonate-chemical sediment / Felsic-intermediate igneous /
Mafic-ultramafic igneous / Metamorphic. *Rationale: the survey's own
taxonomy is authoritative, auditable, and reproducible; manual judgement is
confined to the three stated supplements plus code-level notes (e.g.
undifferentiated clay → cover, the dominant case in SA drillholes).*

**Status: approved by Hugh (2026-07-17)**

## 2026-07-17 — CLR subcomposition and zero replacement (Phase 2)

Features are the CLR of the closed 7-element suite-F subcomposition
(Cu, Zn, Pb, Co, Ni, Fe, Mn). Reported zeros exist (e.g. Co: 3,879 of
20,024 — labs reporting undetected as plain 0 without a "<" marker) and are
handled by multiplicative replacement: zeros become 0.65 × the column's
smallest positive value, non-zero parts scaled down so closure is
preserved. A log10 feature set on zero-replaced ppm is retained strictly as
the comparison baseline. *Rationale: CLR requires strictly positive closed
compositions; 0.65 × min-positive is the standard multiplicative-replacement
heuristic and the reported zeros are best read as unflagged
below-detection values.*

**Status: approved by Hugh (2026-07-17)**

## 2026-07-17 — Phase 3 evaluation protocol

Metrics are computed on pooled out-of-fold predictions from GroupKFold(5)
by drillhole (macro-F1, balanced accuracy, per-class F1), with per-fold
macro-F1 spread reported. Both trained models use
``class_weight='balanced'`` (largest:smallest class ≈ 5:1). RF tuned over a
small grid (n_estimators 200/500 × max_depth None/10/20) on the same
grouped folds — a light-tuning shortcut per the brief, noted in results.md
as a source of minor selection optimism. One shuffled KFold(5) run of the
tuned RF exists solely to quantify the spatial-leakage gap. Seed 42
throughout. *Rationale: pooled OOF predictions give a single honest
confusion matrix for Phase 4; grouping by hole is the project's core
methodological claim.*

**Status: approved by Hugh (2026-07-17, delegated with logic recorded)**

## 2026-07-17 — Phase 3 finding: log10 baseline edges out CLR; CLR stays primary

Grouped-CV macro-F1: RF on CLR 0.448 vs RF on log10 ppm 0.478. The
comparison baseline outperforms the compositional features by 0.030. CLR
remains the primary feature set (rule 1: raw concentrations are modelled
only as a labelled baseline) and the result is reported, not buried.
*Rationale: absolute abundance carries real lithological signal here
(cover is dilute in most traces), and CLR on a 7-element trace-dominated
subcomposition — no Si/Al/Ca/Mg majors — normalises some of that away.
The gap and its interpretation go to Phase 4/limitations; switching
primary features post-hoc because the baseline won would be the kind of
result-chasing this repo exists to avoid.*

**Status: approved by Hugh (2026-07-17, delegated with logic recorded)**

## 2026-07-17 — Phase 4 figures: method and honesty choices

All four figures regenerate deterministically from
`python -m lithoclass.make_figures` (seed 42); nothing hand-edited.
- **F1 confusion / F4 strip log** use pooled out-of-fold predictions from
  the tuned RF under GroupKFold — the same honest predictions as the results
  table.
- **F3 permutation importance** is computed on a single held-out grouped
  fold (fit on train, permute on the held-out test), not on training data,
  so importances reflect generalisation, not memorisation. n_repeats=10.
- **F4 strip log** shows one best-case and one hard-case hole (highest and
  lowest per-hole agreement among holes with ≥3 classes and ≥80 samples),
  each labelled with its agreement %. *Rationale: showing the model's range
  — not two flattering holes — is the honest choice; the hard-case hole
  (systematic mafic→metamorphic flip) is itself a teachable confusion.*
  Predictions are drawn per-sample (no smoothing): the visible volatility in
  the predicted column is real.

**Status: approved by Hugh (2026-07-17, delegated with logic recorded)**

## 2026-07-17 — Minimum class support rule

Classes require ≥500 complete-case samples or are merged/dropped. All seven
classes clear it (smallest: Carbonate-chemical sediment, 1,314 samples
across 286 holes). *Rationale: enough support per class for stable
per-class F1 under 5-fold grouped CV.*

**Status: approved by Hugh (2026-07-17)**
