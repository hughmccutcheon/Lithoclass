"""One-pass extraction of the labelled drillhole subset from the raw chem table.

Streams ``sarig_rs_chem_exp.csv`` (22 GB, long format) once and keeps only
rows that are drillhole-linked AND carry a sample-level lithology code — the
modelling population approved at the Phase 0 gate. Values stay as strings;
no cleaning happens here. Output: ``data/processed/labelled_long.parquet``.

Run: ``python -m lithoclass.extract``
"""

from pathlib import Path

import pandas as pd

from lithoclass.profile import CHEM_FILE, RAW_DIR

OUT_PATH = Path("data/processed/labelled_long.parquet")

EXTRACT_COLS = [
    "SAMPLE_NO",
    "DRILLHOLE_NUMBER",
    "DH_NAME",
    "DH_DEPTH_FROM",
    "DH_DEPTH_TO",
    "ROCK_GROUP_CODE",
    "ROCK_GROUP",
    "LITHO_CODE",
    "LITHO_CONF",
    "LITHOLOGY_NAME",
    "SAMPLE_ANALYSIS_NO",
    "CHEM_CODE",
    "VALUE",
    "UNIT",
    "CHEM_METHOD_CODE",
    "LONGITUDE_GDA2020",
    "LATITUDE_GDA2020",
]

MIN_HOLES = 30  # brief target; verified at extraction time

CHUNKSIZE = 1_000_000


def extract_labelled(
    chem_path: Path, out_path: Path, chunksize: int = CHUNKSIZE
) -> dict:
    """Stream the raw chem CSV and write the labelled drillhole subset.

    Keeps rows with both ``DRILLHOLE_NUMBER`` and ``LITHO_CODE`` present.
    Returns summary stats and raises if the hole count falls below the
    brief's minimum (sanity check, not expected to trigger).
    """
    frames: list[pd.DataFrame] = []
    for chunk in pd.read_csv(
        chem_path,
        usecols=EXTRACT_COLS,
        dtype=str,
        chunksize=chunksize,
        encoding="utf-8",
        encoding_errors="replace",
        low_memory=False,
    ):
        labelled = chunk[
            chunk["DRILLHOLE_NUMBER"].notna() & chunk["LITHO_CODE"].notna()
        ]
        if not labelled.empty:
            frames.append(labelled)

    df = pd.concat(frames, ignore_index=True)
    n_holes = df["DRILLHOLE_NUMBER"].nunique()
    if n_holes < MIN_HOLES:
        raise ValueError(f"Only {n_holes} labelled holes; brief requires >={MIN_HOLES}")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(out_path, index=False)
    return {
        "n_rows": len(df),
        "n_samples": df["SAMPLE_NO"].nunique(),
        "n_holes": n_holes,
    }


def main() -> None:
    """Extract the labelled subset and print summary stats."""
    stats = extract_labelled(RAW_DIR / CHEM_FILE, OUT_PATH)
    print(
        f"Wrote {OUT_PATH}: {stats['n_rows']:,} rows, "
        f"{stats['n_samples']:,} samples, {stats['n_holes']:,} holes"
    )


if __name__ == "__main__":
    main()
