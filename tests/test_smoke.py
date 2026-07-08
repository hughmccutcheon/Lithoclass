"""Phase 0 smoke test: the package imports and pytest runs."""

import lithoclass


def test_package_imports() -> None:
    assert lithoclass.__doc__ is not None
