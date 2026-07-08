# CLAUDE.md — Drillhole Geochemistry Lithology Classifier

## What this project is

A portfolio work sample for Hugh's application to the Geo-Data Scientist role at
Datarock (IMDEX). Supervised classification of logged lithology from open
drillhole geochemistry. The audience is a hiring panel of geo-data scientists.
The repository must demonstrate four things:

1. Domain-aware handling of real geoscience data (censored values, compositional
   data, spatial structure, messy lithology logging)
2. Sound, honest ML methodology
3. Clean software habits (small typed functions, tests, reproducible figures)
4. Effective use of agentic coding tools under human expert oversight

## Roles

- **Hugh** — geologist, 14 years in Australian extractive industries. Domain
  expert and reviewer. All geological decisions (lithology groupings,
  interpretation of model confusions, data-quality judgement calls) are his.
- **Claude Code** — implementation partner. Write the code, propose options,
  flag anomalies. Stop and ask Hugh on any geological judgement call. Never
  make a geological decision silently.

## Non-negotiable domain rules

1. **Geochemistry is compositional data.** Never model raw concentrations
   directly. Apply zero-replacement then a CLR transform before modelling.
   A raw/log10 feature set may be kept only as a comparison baseline.
2. **Never randomly split samples across drillholes for evaluation.** All model
   evaluation uses GroupKFold (or leave-one-hole-out) grouped by `hole_id`.
   A naive random KFold is computed exactly once, deliberately, solely to
   quantify the spatial-leakage gap for the README.
3. **Below-detection-limit values are handled explicitly.** Parse censoring
   markers (e.g. "<5"), keep a censor-flag column, substitute at DL/2 as the
   default. Never silently coerce or drop. Log every choice in DECISIONS.md.
4. **Lithology classes are consolidated to 5–8 groups** via an explicit lookup
   table (`data/lith_lookup.csv`) that Hugh edits and approves. No silent
   relabelling, ever.
5. **Every data decision** (thresholds, drops, substitutions, groupings,
   imputation) gets a dated entry in DECISIONS.md with a one-line rationale.

## Scope guardrails

- The plan lives in PROJECT_BRIEF.md. Work **one phase at a time**. Do not
  start a phase early, and do not blend phases.
- **No** deep learning, dashboards, deployment, extra datasets, or features
  beyond the brief. If an idea seems valuable, append it to IDEAS_PARKED.md
  with one line of context and move on. Scope is deliberately fixed: if new
  scope comes up mid-phase, park the idea in IDEAS_PARKED.md and continue
  the phase.
- The stretch phase (NVCL hyperspectral) is **locked** until Phase 5 is
  complete AND Hugh confirms the job application has been submitted.

## Stack and conventions

- Python 3.11+. Libraries: pandas, numpy, scikit-learn, matplotlib, pytest.
  Nothing else without asking.
- Environment: `uv` if available, otherwise venv + `requirements.txt` with
  pinned versions.
- Logic lives in `src/lithoclass/` as small, typed, docstringed functions.
  The walkthrough notebook stays thin: it imports from `src` and narrates.
  No logic may exist only in the notebook.
- Figures regenerate from `python -m lithoclass.make_figures` into `figures/`.
  Nothing hand-edited.
- Lint with ruff. Tests must pass before a phase can be called done.
- Fixed random seeds everywhere results are reported.

## Repository layout

```
lithoclass/
├── CLAUDE.md
├── PROJECT_BRIEF.md
├── DECISIONS.md          # dated log of every data/method decision
├── IDEAS_PARKED.md       # parked out-of-scope ideas
├── README.md             # written in Phase 5, consulting-memo style
├── requirements.txt
├── data/
│   ├── raw/              # gitignored — untouched downloads
│   ├── processed/
│   └── lith_lookup.csv   # Hugh-approved lithology consolidation
├── src/lithoclass/
│   ├── io.py  clean.py  transform.py  model.py  evaluate.py
│   ├── plots.py  make_figures.py
├── notebooks/01_walkthrough.ipynb
├── tests/
├── figures/
└── reports/              # data_profile.md, results.md
```

## Workflow every session

1. Read this file and PROJECT_BRIEF.md.
2. Check DECISIONS.md and `git log`; state which phase we are in and what
   remains in it.
3. Plan before writing code (plan mode for anything non-trivial).
4. At the end of a phase: run tests, then give Hugh a review summary — what
   was done, what decisions need his sign-off — and **stop** until he
   approves.
5. Commit per phase or logical chunk with clear messages. Never commit
   `data/raw/`.

## Definition of done (whole project)

- All Phase 0–5 acceptance criteria in PROJECT_BRIEF.md met
- pytest green, ruff clean
- README reads as a consulting memo and includes the "Built with Claude Code"
  section
- `figures/` regenerates from a fresh clone + `data/raw/`
- Hugh has reviewed and approved every DECISIONS.md entry
