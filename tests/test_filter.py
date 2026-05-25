"""Tests for the CLI attack-filter helper."""

from __future__ import annotations

import pytest

from rag_poison_lab.attacks import all_attacks
from rag_poison_lab.cli import _filter_attacks


def test_no_filters_returns_full_corpus():
    attacks = all_attacks()
    filtered = _filter_attacks(attacks, family=None, only=None, exclude=None)
    assert len(filtered) == len(attacks)


def test_family_filter_single():
    attacks = all_attacks()
    filtered = _filter_attacks(attacks, family="direct_override", only=None, exclude=None)
    assert filtered
    assert all(a.family == "direct_override" for a in filtered)


def test_family_filter_multiple_comma_separated():
    attacks = all_attacks()
    filtered = _filter_attacks(
        attacks, family="direct_override,markdown_exfil", only=None, exclude=None
    )
    assert filtered
    families = {a.family for a in filtered}
    assert families == {"direct_override", "markdown_exfil"}


def test_family_filter_unknown_family_raises():
    import typer
    attacks = all_attacks()
    with pytest.raises(typer.BadParameter):
        _filter_attacks(attacks, family="nonexistent_family", only=None, exclude=None)


def test_exclude_drops_specified_families():
    attacks = all_attacks()
    filtered = _filter_attacks(
        attacks, family=None, only=None, exclude="multilingual_bypass"
    )
    assert filtered
    assert all(a.family != "multilingual_bypass" for a in filtered)


def test_only_returns_single_attack():
    attacks = all_attacks()
    filtered = _filter_attacks(
        attacks, family=None, only="markdown_exfil/citation_image", exclude=None
    )
    assert len(filtered) == 1
    assert filtered[0].family == "markdown_exfil"
    assert filtered[0].payload_id == "citation_image"


def test_only_with_bad_format_raises():
    import typer
    attacks = all_attacks()
    with pytest.raises(typer.BadParameter):
        _filter_attacks(attacks, family=None, only="missing_slash", exclude=None)


def test_only_with_unknown_attack_raises():
    import typer
    attacks = all_attacks()
    with pytest.raises(typer.BadParameter):
        _filter_attacks(
            attacks, family=None, only="direct_override/does_not_exist", exclude=None
        )
