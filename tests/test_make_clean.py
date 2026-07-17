"""End-to-end test of the build_clean chain on synthetic data."""

import pandas as pd

from lithoclass.make_clean import build_clean


def _long() -> pd.DataFrame:
    rows = []
    # S1: granite, complete Cu+Zn incl. a censored Cu
    rows += [
        ("S1", "100", "GRNT", "Granite", "Cu", "<10", "ppm"),
        ("S1", "100", "GRNT", "Granite", "Zn", "80", "ppm"),
        # S2: basalt, missing Zn -> dropped by complete-case
        ("S2", "100", "BSLT", "Basalt", "Cu", "120", "ppm"),
        # S3: ore -> excluded class (keep=N)
        ("S3", "200", "ORE", "Ore", "Cu", "9999", "ppm"),
        ("S3", "200", "ORE", "Ore", "Zn", "5", "%"),
        # S4: basalt, complete, Zn in %
        ("S4", "200", "BSLT", "Basalt", "Cu", "300", "ppm"),
        ("S4", "200", "BSLT", "Basalt", "Zn", "0.02", "%"),
    ]
    return pd.DataFrame(
        rows,
        columns=["SAMPLE_NO", "DRILLHOLE_NUMBER", "LITHO_CODE",
                 "LITHOLOGY_NAME", "CHEM_CODE", "VALUE", "UNIT"],
    )


def _lookup() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "litho_code": ["GRNT", "BSLT", "ORE"],
            "tier": ["basement", "basement", "basement"],
            "lith_class": ["Felsic", "Mafic", "EXCLUDED"],
            "keep": ["Y", "Y", "N"],
        }
    )


def test_build_clean_end_to_end() -> None:
    clean, stats = build_clean(_long(), _lookup(), elements=["Cu", "Zn"])

    assert stats["n_samples_labelled"] == 4
    assert stats["n_excluded_class"] == 1  # S3 (ore)
    assert stats["n_incomplete_suite"] == 1  # S2 (no Zn)
    assert stats["n_final"] == 2
    assert stats["n_holes_final"] == 2

    s1 = clean[clean["SAMPLE_NO"] == "S1"].iloc[0]
    assert s1["Cu_ppm"] == 5.0  # <10 -> DL/2
    assert s1["Cu_censor"] == "below"
    assert s1["lith_class"] == "Felsic"

    s4 = clean[clean["SAMPLE_NO"] == "S4"].iloc[0]
    assert s4["Zn_ppm"] == 200.0  # 0.02% -> ppm
    assert set(clean["lith_class"]) == {"Felsic", "Mafic"}
