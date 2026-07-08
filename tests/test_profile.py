"""Tests for lithoclass.profile aggregation against synthetic fixtures."""

from pathlib import Path

from lithoclass.profile import profile_chem, profile_litho_log, write_report

CHEM_CSV = """\
SAMPLE_NO,DRILLHOLE_NUMBER,DH_DEPTH_FROM,LITHO_CODE,LITHOLOGY_NAME,CHEM_CODE,VALUE,UNIT
S1,100,10.0,GRAN,Granite,Cu,150,ppm
S1,100,10.0,GRAN,Granite,Au,<5,ppb
S2,100,12.0,,,Cu,<10,ppm
S3,200,,BSLT,Basalt,Zn,-1,ppm
S4,,,SDST,Sandstone,Cu,90,ppm
"""

LITHO_CSV = """DRILLHOLE_NO,MAJOR_LITHOLOGY
100,Granite
100,Granite
300,Basalt
"""


def test_profile_chem_aggregates(tmp_path: Path) -> None:
    path = tmp_path / "chem.csv"
    path.write_text(CHEM_CSV)
    out = profile_chem(path, chunksize=2)  # multiple chunks on purpose

    assert out["n_rows"] == 5
    assert out["n_rows_dh"] == 4  # S4 has no drillhole
    assert out["n_samples_all"] == 4
    assert out["n_samples_dh"] == 3
    assert out["n_holes_dh"] == 2
    assert out["n_censored_lt"] == 2
    assert out["n_negative"] == 1
    assert out["n_dh_rows_with_depth"] == 3
    assert out["element_counter_dh"]["Cu"] == 2
    # lithology counted once per drillhole-linked sample
    assert out["litho_by_sample"]["Granite"] == 1
    assert out["litho_by_sample"]["<no lithology>"] == 1
    assert out["litho_by_sample"]["Basalt"] == 1
    assert "Sandstone" not in out["litho_by_sample"]


def test_profile_litho_log_and_report(tmp_path: Path) -> None:
    chem_path = tmp_path / "chem.csv"
    chem_path.write_text(CHEM_CSV)
    litho_path = tmp_path / "litho.csv"
    litho_path.write_text(LITHO_CSV)

    litho = profile_litho_log(litho_path, chunksize=2)
    assert litho["n_rows"] == 3
    assert litho["holes"] == {"100", "300"}
    assert litho["major_litho"]["Granite"] == 2

    chem = profile_chem(chem_path)
    details = {"n_holes_total": 10, "n_holes_both_flags": 2}
    report = tmp_path / "reports" / "data_profile.md"
    write_report(chem, litho, details, report)
    text = report.read_text(encoding="utf-8")
    # element table has no min-count threshold, so fixture elements appear
    assert "| Cu | 2 |" in text
    # small lithology counts fold into the tail row (display threshold)
    assert "more distinct values" in text
    # join check: chem holes {100, 200} ∩ litho holes {100, 300} = 1
    assert "1 of the 2 geochem holes" in text
