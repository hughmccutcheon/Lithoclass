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
