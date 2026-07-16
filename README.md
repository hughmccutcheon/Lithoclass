# lithoclass — lithology classification from drillhole geochemistry

**Work in progress** (data cleaning phase). Final write-up will replace this
README.

Supervised classification of logged lithology from open drillhole
geochemistry, built as a work sample in geoscience data science. The model
predicts a consolidated lithology class for each assayed sample from its
multi-element chemistry, evaluated with drillhole-grouped cross-validation
to avoid spatial leakage.

- **Data:** [SARIG Data Package](https://energymining.sa.gov.au/industry/geological-survey)
  — Geological Survey of South Australia / SA Geodata, licensed CC-BY 4.0.
  Raw extracts are not committed; see `data/raw/` notes in `.gitignore`.
- **Stack:** Python, pandas, scikit-learn, matplotlib, pytest.
- **Approach highlights:** explicit below-detection-limit handling, CLR
  compositional transform, geologist-approved lithology consolidation
  (`data/lith_lookup.csv`), GroupKFold by drillhole.
- **Process:** built with Claude Code under geologist review — every data
  decision is logged with rationale in [DECISIONS.md](DECISIONS.md).
