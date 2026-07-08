"""Tests for lithoclass.io.load_raw against synthetic fixtures (never real data)."""

from pathlib import Path

import pandas as pd
import pytest

from lithoclass.io import load_raw

FIXTURES = Path(__file__).parent / "fixtures"


def test_load_raw_single_file_preserves_strings() -> None:
    df = load_raw(FIXTURES / "geochem_tiny.csv")
    assert len(df) == 3
    # censoring markers must survive as-is — no numeric coercion
    assert df.loc[0, "Au_ppb"] == "<5"
    assert df.loc[1, "Cu_ppm"] == "<10"
    # empty fields become NaN, not empty strings or zeros
    assert pd.isna(df.loc[2, "Au_ppb"])
    assert (df["source_file"] == "geochem_tiny.csv").all()


def test_load_raw_directory_concatenates(tmp_path: Path) -> None:
    src = (FIXTURES / "geochem_tiny.csv").read_text()
    (tmp_path / "sheet_a").mkdir()
    (tmp_path / "sheet_b").mkdir()
    (tmp_path / "sheet_a" / "geochem_a.csv").write_text(src)
    (tmp_path / "sheet_b" / "geochem_b.csv").write_text(src)

    df = load_raw(tmp_path, pattern="*geochem*.csv")
    assert len(df) == 6
    assert set(df["source_file"]) == {"geochem_a.csv", "geochem_b.csv"}


def test_load_raw_missing_path_raises() -> None:
    with pytest.raises(FileNotFoundError):
        load_raw(FIXTURES / "does_not_exist.csv")


def test_load_raw_empty_directory_raises(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        load_raw(tmp_path)
