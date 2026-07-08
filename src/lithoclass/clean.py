"""Cleaning: censored-value parsing, unit harmonisation, pivot, lookup.

All rules here are logged in DECISIONS.md. Nothing is silently coerced or
dropped: every parse failure and excluded row carries a flag or a count.
"""

import pandas as pd

# Censor flags attached per (sample, element) measurement
FLAG_OK = "ok"
FLAG_BELOW = "below"  # "<x": substituted at DL/2
FLAG_ABOVE = "above"  # ">x": kept at face value
FLAG_NEGATIVE = "negative"  # negative raw value: treated as missing
FLAG_UNPARSED = "unparsed"  # unrecognisable string: treated as missing

UNIT_TO_PPM = {
    "ppm": 1.0,
    "%": 10_000.0,
    "ppb": 0.001,
    "g/T": 1.0,  # grams per tonne is ppm by definition
}


def parse_censored(values: pd.Series) -> tuple[pd.Series, pd.Series]:
    """Parse raw assay value strings into numbers plus a censor flag.

    ``"<x"`` becomes ``x / 2`` (DL/2 substitution) flagged ``below``;
    ``">x"`` becomes ``x`` flagged ``above``; negatives become NaN flagged
    ``negative``; anything unparseable becomes NaN flagged ``unparsed``.
    """
    s = values.astype("str").str.strip()
    below = s.str.startswith("<")
    above = s.str.startswith(">")

    stripped = s.mask(below | above, s.str[1:])
    numeric = pd.to_numeric(stripped, errors="coerce")
    numeric = numeric.mask(below, numeric / 2)

    negative = numeric < 0
    unparsed = numeric.isna() & values.notna()
    numeric = numeric.mask(negative)

    flag = pd.Series(FLAG_OK, index=values.index, dtype="str")
    flag = flag.mask(below, FLAG_BELOW).mask(above, FLAG_ABOVE)
    flag = flag.mask(negative, FLAG_NEGATIVE).mask(unparsed, FLAG_UNPARSED)
    return numeric, flag


def to_ppm(values: pd.Series, units: pd.Series) -> pd.Series:
    """Convert parsed values to ppm; unconvertible units become NaN."""
    factors = units.map(UNIT_TO_PPM)
    return values * factors


def pivot_samples(long_df: pd.DataFrame, elements: list[str]) -> pd.DataFrame:
    """Pivot the long parsed table to one row per sample.

    Expects columns ``SAMPLE_NO, CHEM_CODE, value_ppm, censor_flag`` plus
    sample-level metadata. Duplicate (sample, element) analyses resolve to
    the **median**; uncensored measurements are preferred over censored ones
    when both exist for the same sample and element.
    """
    df = long_df[long_df["CHEM_CODE"].isin(elements)].copy()
    df = df[df["value_ppm"].notna()]

    # prefer uncensored: drop censored rows where an "ok" row exists
    has_ok = df[df["censor_flag"] == FLAG_OK][["SAMPLE_NO", "CHEM_CODE"]]
    ok_pairs = set(zip(has_ok["SAMPLE_NO"], has_ok["CHEM_CODE"], strict=True))
    keep = [
        (flag == FLAG_OK) or ((sample, elem) not in ok_pairs)
        for sample, elem, flag in zip(
            df["SAMPLE_NO"], df["CHEM_CODE"], df["censor_flag"], strict=True
        )
    ]
    df = df[keep]

    values = df.pivot_table(
        index="SAMPLE_NO", columns="CHEM_CODE", values="value_ppm", aggfunc="median"
    )
    values = values.reindex(columns=elements)
    values.columns = [f"{c}_ppm" for c in values.columns]

    flags = (
        df.sort_values("censor_flag")  # "below" sorts before "ok"
        .drop_duplicates(["SAMPLE_NO", "CHEM_CODE"])
        .pivot(index="SAMPLE_NO", columns="CHEM_CODE", values="censor_flag")
        .reindex(columns=elements)
    )
    flags.columns = [f"{c}_censor" for c in flags.columns]

    meta_cols = [
        c
        for c in long_df.columns
        if c not in {"CHEM_CODE", "VALUE", "UNIT", "value_ppm", "censor_flag",
                     "SAMPLE_ANALYSIS_NO", "CHEM_METHOD_CODE"}
    ]
    meta = long_df[meta_cols].drop_duplicates("SAMPLE_NO").set_index("SAMPLE_NO")

    return meta.join(values).join(flags).reset_index()


def apply_lookup(df: pd.DataFrame, lookup: pd.DataFrame) -> pd.DataFrame:
    """Join the Hugh-approved lithology lookup; fail loudly on unmapped codes.

    ``lookup`` needs columns ``litho_code, tier, lith_class``.
    """
    merged = df.merge(
        lookup[["litho_code", "tier", "lith_class"]],
        left_on="LITHO_CODE",
        right_on="litho_code",
        how="left",
    ).drop(columns="litho_code")
    unmapped = merged.loc[merged["lith_class"].isna(), "LITHO_CODE"].unique()
    if len(unmapped) > 0:
        raise ValueError(f"Unmapped lithology codes: {sorted(unmapped)[:20]}")
    return merged
