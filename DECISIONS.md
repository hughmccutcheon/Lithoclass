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

**Status: pending Hugh's sign-off**

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

**Status: pending Hugh's sign-off (workability gate follows the profile)**
