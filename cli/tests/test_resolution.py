from __future__ import annotations

import pytest

from czm_cli.errors import ResolutionError
from czm_cli.resolution import resolve_single


def test_resolution_exact_then_case_insensitive_then_substring():
    items = [
        (1, ("Left elbow",)),
        (2, ("left wrist",)),
        (3, ("Neck",)),
    ]
    assert resolve_single("Left elbow", items, label="subject") == 1
    assert resolve_single("left ELBOW", items, label="subject") == 1
    assert resolve_single("wrist", items, label="subject") == 2


def test_resolution_numeric_id_precedence():
    items = [(7, ("Seven",)), (8, ("8",))]
    assert resolve_single("7", items, label="subject") == 7


def test_resolution_ambiguous_and_missing():
    items = [(1, ("alpha",)), (2, ("alphabet",))]
    with pytest.raises(ResolutionError):
        resolve_single("alp", items, label="subject")
    with pytest.raises(ResolutionError):
        resolve_single("missing", items, label="subject")

