"""Tests for lithoclass.clean against synthetic data (never real assays)."""

import numpy as np
import pandas as pd
import pytest

from lithoclass.clean import (
    FLAG_BELOW,
    FLAG_NEGATIVE,
    FLAG_OK,
    FLAG_UNPARSED,
    apply_lookup,
    parse_censored,
    pivot_samples,
    to_ppm,
)


def test_parse_censored_below_detection() -> None:
    values = pd.Series(["<5", "<0.2", "10"])
    numeric, flag = parse_censored(values)
    assert numeric.tolist() == [2.5, 0.1, 10.0]
    assert flag.tolist() == [FLAG_BELOW, FLAG_BELOW, FLAG_OK]


def test_parse_censored_above_negative_unparsed() -> None:
    values = pd.Series([">1000", "-1", "n.a.", "3.5", None])
    numeric, flag = parse_censored(values)
    assert numeric[0] == 1000.0  # face value, flagged
    assert np.isnan(numeric[1]) and flag[1] == FLAG_NEGATIVE
    assert np.isnan(numeric[2]) and flag[2] == FLAG_UNPARSED
    assert numeric[3] == 3.5 and flag[3] == FLAG_OK
    assert np.isnan(numeric[4])  # missing stays missing, not "unparsed"
    assert flag[4] == FLAG_OK


def test_to_ppm_conversions() -> None:
    values = pd.Series([2.0, 2.0, 500.0, 3.1, 7.0])
    units = pd.Series(["%", "ppm", "ppb", "g/T", "cps"])
    ppm = to_ppm(values, units)
    assert ppm[0] == 20_000.0
    assert ppm[1] == 2.0
    assert ppm[2] == 0.5
    assert ppm[3] == 3.1
    assert np.isnan(ppm[4])  # unconvertible unit


def _long_fixture() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "SAMPLE_NO": ["S1", "S1", "S1", "S1", "S2", "S2"],
            "DRILLHOLE_NUMBER": ["100"] * 4 + ["200"] * 2,
            "LITHO_CODE": ["GRNT"] * 4 + ["BSLT"] * 2,
            "LITHOLOGY_NAME": ["Granite"] * 4 + ["Basalt"] * 2,
            "CHEM_CODE": ["Cu", "Cu", "Cu", "Zn", "Cu", "Zn"],
            # S1/Cu: duplicate analyses 10, 20, and a censored <2 → median(10,20)
            "value_ppm": [10.0, 20.0, 1.0, 55.0, 7.0, np.nan],
            "censor_flag": [FLAG_OK, FLAG_OK, FLAG_BELOW, FLAG_OK, FLAG_OK, FLAG_OK],
        }
    )


def test_pivot_prefers_uncensored_and_takes_median() -> None:
    wide = pivot_samples(_long_fixture(), elements=["Cu", "Zn"])
    s1 = wide[wide["SAMPLE_NO"] == "S1"].iloc[0]
    assert s1["Cu_ppm"] == 15.0  # median of uncensored 10, 20; <2 ignored
    assert s1["Cu_censor"] == FLAG_OK
    assert s1["Zn_ppm"] == 55.0
    s2 = wide[wide["SAMPLE_NO"] == "S2"].iloc[0]
    assert s2["Cu_ppm"] == 7.0
    assert pd.isna(s2["Zn_ppm"])  # NaN value dropped, no Zn left for S2
    assert len(wide) == 2


def test_pivot_censored_only_keeps_substitution() -> None:
    df = _long_fixture()
    df.loc[df["SAMPLE_NO"] == "S1", "censor_flag"] = FLAG_BELOW
    wide = pivot_samples(df, elements=["Cu", "Zn"])
    s1 = wide[wide["SAMPLE_NO"] == "S1"].iloc[0]
    assert s1["Cu_censor"] == FLAG_BELOW  # no uncensored rows to prefer


def test_apply_lookup_joins_and_raises_on_unmapped() -> None:
    wide = pivot_samples(_long_fixture(), elements=["Cu", "Zn"])
    lookup = pd.DataFrame(
        {
            "litho_code": ["GRNT", "BSLT"],
            "tier": ["basement", "basement"],
            "lith_class": ["Granitoid", "Mafic"],
        }
    )
    out = apply_lookup(wide, lookup)
    assert out.loc[out["SAMPLE_NO"] == "S1", "lith_class"].item() == "Granitoid"

    with pytest.raises(ValueError, match="Unmapped"):
        apply_lookup(wide, lookup[lookup["litho_code"] != "BSLT"])
