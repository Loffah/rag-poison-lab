"""Tests for the report renderer. No LLM calls."""

from __future__ import annotations

from rag_poison_lab.attacks import all_attacks
from rag_poison_lab.report import _PRODUCTION_IMPACT


def test_every_shipped_family_has_a_production_impact_blurb():
    """Each family that can appear in a landings report needs a production-impact
    paragraph, otherwise the report silently omits the callout for that family.
    Regression guard for the gap where hidden_text and format_spoofing shipped
    without one."""
    families = {a.family for a in all_attacks()}
    missing = families - set(_PRODUCTION_IMPACT)
    assert not missing, f"families with no production-impact blurb: {sorted(missing)}"
