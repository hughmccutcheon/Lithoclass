"""Phase 0 profiling of the raw SARIG extract.

Streams the large long-format geochemistry table (``sarig_rs_chem_exp.csv``,
one row per element analysis) in chunks and writes a markdown profile to
``reports/data_profile.md`` for Hugh's workability review. Read-only: no
cleaning, no coercion, no dropping happens here.

Run: ``python -m lithoclass.profile``
"""

from collections import Counter
from pathlib import Path

import pandas as pd

RAW_DIR = Path("data/raw")
REPORT_PATH = Path("reports/data_profile.md")

CHEM_FILE = "sarig_rs_chem_exp.csv"
LITHO_LOG_FILE = "sarig_dh_litho_exp.csv"
DH_DETAILS_FILE = "sarig_dh_details_exp.csv"

CHEM_COLS = [
    "SAMPLE_NO",
    "DRILLHOLE_NUMBER",
    "DH_DEPTH_FROM",
    "LITHO_CODE",
    "LITHOLOGY_NAME",
    "CHEM_CODE",
    "VALUE",
    "UNIT",
]

CHUNKSIZE = 1_000_000


def profile_chem(path: Path, chunksize: int = CHUNKSIZE) -> dict:
    """Stream the long-format geochemistry table and aggregate profile stats.

    The "modelling population" tracked here is rows linked to a drillhole
    (``DRILLHOLE_NUMBER`` present); lithology coverage within it is counted
    once per sample (first row seen for that sample).
    """
    n_rows = 0
    n_rows_dh = 0
    n_censored_lt = 0
    n_censored_gt = 0
    n_negative = 0
    samples_all: set[str] = set()
    samples_dh: set[str] = set()
    holes_dh: set[str] = set()
    n_dh_rows_with_depth = 0
    element_counter_dh: Counter[str] = Counter()
    unit_counter: Counter[str] = Counter()
    litho_by_sample: Counter[str] = Counter()

    for chunk in pd.read_csv(
        path,
        usecols=CHEM_COLS,
        dtype=str,
        chunksize=chunksize,
        encoding="utf-8",
        encoding_errors="replace",
        low_memory=False,
    ):
        n_rows += len(chunk)
        value = chunk["VALUE"].str.strip()
        n_censored_lt += value.str.startswith("<").sum()
        n_censored_gt += value.str.startswith(">").sum()
        n_negative += value.str.startswith("-").sum()
        samples_all.update(chunk["SAMPLE_NO"].dropna())
        unit_counter.update(chunk["UNIT"].dropna())

        dh = chunk[chunk["DRILLHOLE_NUMBER"].notna()]
        n_rows_dh += len(dh)
        holes_dh.update(dh["DRILLHOLE_NUMBER"])
        n_dh_rows_with_depth += dh["DH_DEPTH_FROM"].notna().sum()
        element_counter_dh.update(dh["CHEM_CODE"].dropna())

        # lithology once per drillhole-linked sample (label else <no lithology>)
        first = dh.drop_duplicates("SAMPLE_NO")
        new = first[~first["SAMPLE_NO"].isin(samples_dh)]
        litho_by_sample.update(new["LITHOLOGY_NAME"].fillna("<no lithology>"))
        samples_dh.update(dh["SAMPLE_NO"])

    return {
        "n_rows": n_rows,
        "n_rows_dh": n_rows_dh,
        "n_censored_lt": int(n_censored_lt),
        "n_censored_gt": int(n_censored_gt),
        "n_negative": int(n_negative),
        "n_samples_all": len(samples_all),
        "n_samples_dh": len(samples_dh),
        "n_holes_dh": len(holes_dh),
        "holes_dh": holes_dh,
        "n_dh_rows_with_depth": int(n_dh_rows_with_depth),
        "element_counter_dh": element_counter_dh,
        "unit_counter": unit_counter,
        "litho_by_sample": litho_by_sample,
    }


def profile_litho_log(path: Path, chunksize: int = CHUNKSIZE) -> dict:
    """Aggregate the drillhole lithology-log table (interval logs)."""
    n_rows = 0
    holes: set[str] = set()
    major_litho: Counter[str] = Counter()
    for chunk in pd.read_csv(
        path,
        usecols=["DRILLHOLE_NO", "MAJOR_LITHOLOGY"],
        dtype=str,
        chunksize=chunksize,
        encoding="utf-8",
        encoding_errors="replace",
        low_memory=False,
    ):
        n_rows += len(chunk)
        holes.update(chunk["DRILLHOLE_NO"].dropna())
        major_litho.update(chunk["MAJOR_LITHOLOGY"].fillna("<no lithology>"))
    return {"n_rows": n_rows, "holes": holes, "major_litho": major_litho}


def profile_dh_details(path: Path) -> dict:
    """Count drillholes flagged as having both geochemistry and a litho log."""
    dh = pd.read_csv(
        path,
        usecols=["DRILLHOLE_NO", "GEOCHEMISTRY", "LITHO_LOG"],
        dtype=str,
        low_memory=False,
    )
    both = dh[(dh["GEOCHEMISTRY"] == "Y") & (dh["LITHO_LOG"] == "Y")]
    return {"n_holes_total": len(dh), "n_holes_both_flags": len(both)}


def _counter_table(counter: Counter, min_count: int = 0, top: int | None = None) -> str:
    """Render a Counter as a markdown table, most common first."""
    items = [(k, v) for k, v in counter.most_common(top) if v >= min_count]
    omitted = len(counter) - len(items)
    lines = ["| value | count |", "|---|---|"]
    lines += [f"| {k} | {v:,} |" for k, v in items]
    if omitted > 0:
        omitted_n = sum(counter.values()) - sum(v for _, v in items)
        lines.append(f"| *(…{omitted} more distinct values)* | {omitted_n:,} |")
    return "\n".join(lines)


def write_report(chem: dict, litho: dict, details: dict, out_path: Path) -> None:
    """Write the markdown data profile for Hugh's Phase 0 review."""
    overlap = len(chem["holes_dh"] & litho["holes"])
    pct_depth = 100 * chem["n_dh_rows_with_depth"] / max(chem["n_rows_dh"], 1)
    pct_lt = 100 * chem["n_censored_lt"] / max(chem["n_rows"], 1)
    lith_labelled = sum(
        v for k, v in chem["litho_by_sample"].items() if k != "<no lithology>"
    )

    md = f"""# Data profile — SARIG Data Package (raw)

Generated by `python -m lithoclass.profile` on {pd.Timestamp.now():%Y-%m-%d}.
Source: SARIG Data Package statewide export (GSSA / SA Geodata), CC-BY 4.0.
Profiled read-only from `data/raw/` — no cleaning applied.

## Geochemistry (`{CHEM_FILE}`, long format: one row per analysis)

- Analysis rows: **{chem["n_rows"]:,}** ({chem["n_samples_all"]:,} distinct samples)
- Drillhole-linked rows: **{chem["n_rows_dh"]:,}**
  ({chem["n_samples_dh"]:,} samples across {chem["n_holes_dh"]:,} holes)
- Drillhole rows with a FROM depth: {chem["n_dh_rows_with_depth"]:,} ({pct_depth:.1f}%)
- Censored values: {chem["n_censored_lt"]:,} below-detection "<x" ({pct_lt:.2f}% of rows),
  {chem["n_censored_gt"]:,} ">x", {chem["n_negative"]:,} negative
- Brief targets: ≥10,000 samples → **{chem["n_samples_dh"]:,}**; ≥30 holes →
  **{chem["n_holes_dh"]:,}** (drillhole-linked population)

### Elements by analysis count (drillhole-linked rows, top 40)

{_counter_table(chem["element_counter_dh"], top=40)}

### Units

{_counter_table(chem["unit_counter"], top=15)}

### Sample-level lithology (once per drillhole-linked sample)

Samples with a lithology label attached directly to the sample:
**{lith_labelled:,}** of {chem["n_samples_dh"]:,}.

{_counter_table(chem["litho_by_sample"], min_count=100)}

*(values with <100 samples folded into the tail row)*

## Drillhole lithology logs (`{LITHO_LOG_FILE}`)

- Interval rows: {litho["n_rows"]:,} across {len(litho["holes"]):,} holes
- **Join check:** {overlap:,} of the {chem["n_holes_dh"]:,} geochem holes also
  have interval lithology logs (join on drillhole number).

### Major lithology of intervals (values with ≥1,000 intervals)

{_counter_table(litho["major_litho"], min_count=1000)}

## Drillhole details (`{DH_DETAILS_FILE}`)

- {details["n_holes_total"]:,} drillholes state-wide;
  {details["n_holes_both_flags"]:,} flagged GEOCHEMISTRY=Y and LITHO_LOG=Y.

## For Hugh's review (Phase 0 gate)

1. Are the sample-level lithology labels (table above) usable as the target,
   or should labels come from the interval logs join?
2. Is the element coverage adequate for a sensible subcomposition?
3. Go/no-go: is this dataset workable?
"""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(md, encoding="utf-8")


def main() -> None:
    """Profile the raw SARIG tables and write ``reports/data_profile.md``."""
    chem = profile_chem(RAW_DIR / CHEM_FILE)
    litho = profile_litho_log(RAW_DIR / LITHO_LOG_FILE)
    details = profile_dh_details(RAW_DIR / DH_DETAILS_FILE)
    write_report(chem, litho, details, REPORT_PATH)
    print(f"Wrote {REPORT_PATH}")


if __name__ == "__main__":
    main()
