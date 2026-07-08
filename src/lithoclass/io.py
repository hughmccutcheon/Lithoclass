"""Raw data loading. Reads untouched SARIG CSVs from ``data/raw/``.

Everything is loaded as strings: censoring markers like ``"<5"`` must survive
untouched, and numeric parsing is deliberately deferred to the cleaning step
(Phase 1). No rows are dropped or coerced here.
"""

from pathlib import Path

import pandas as pd

ENCODINGS = ("utf-8", "cp1252")


def _read_csv_text(path: Path) -> pd.DataFrame:
    """Read a single CSV with all columns as strings, trying known encodings."""
    last_error: UnicodeDecodeError | None = None
    for encoding in ENCODINGS:
        try:
            return pd.read_csv(path, dtype=str, encoding=encoding, low_memory=False)
        except UnicodeDecodeError as exc:
            last_error = exc
    raise ValueError(f"Could not decode {path} with any of {ENCODINGS}") from last_error


def load_raw(path: str | Path, pattern: str = "*.csv") -> pd.DataFrame:
    """Load one raw CSV, or every CSV matching ``pattern`` under a directory.

    Parameters
    ----------
    path:
        A CSV file, or a directory searched recursively for ``pattern``.
    pattern:
        Glob used when ``path`` is a directory (e.g. ``"*geochem*.csv"``
        to load one SARIG table type across several map-sheet folders).

    Returns
    -------
    A DataFrame of strings (NaN for empty fields), with a ``source_file``
    column recording which file each row came from.
    """
    path = Path(path)
    if path.is_file():
        files = [path]
    elif path.is_dir():
        files = sorted(path.rglob(pattern))
        if not files:
            raise FileNotFoundError(f"No files matching {pattern!r} under {path}")
    else:
        raise FileNotFoundError(f"{path} does not exist")

    frames = []
    for file in files:
        frame = _read_csv_text(file)
        frame["source_file"] = file.name
        frames.append(frame)
    return pd.concat(frames, ignore_index=True)
