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
