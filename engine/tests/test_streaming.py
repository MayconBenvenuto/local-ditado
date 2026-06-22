"""Tests for the LocalAgreement-2 streaming stabiliser."""

from __future__ import annotations

from localditado.streaming import LocalAgreement, tokenize


def test_tokenize_handles_blank_and_spacing():
    assert tokenize("") == []
    assert tokenize("   ") == []
    assert tokenize("  ola   mundo ") == ["ola", "mundo"]


def test_commits_only_the_agreed_prefix():
    agg = LocalAgreement()
    # First pass: nothing was seen before, so nothing is confirmed yet.
    newly, preview = agg.update("o gato")
    assert newly == ""
    assert preview == "o gato"
    # Second pass agrees on "o gato" and extends with an unstable tail.
    newly, preview = agg.update("o gato subiu")
    assert newly == "o gato"
    assert preview == "subiu"
    assert agg.text == "o gato"


def test_revision_of_unstable_tail_does_not_corrupt_committed():
    agg = LocalAgreement()
    agg.update("eu acho")
    agg.update("eu acho que")          # commits "eu acho"
    # The tail gets revised: "que" -> "quero". Committed text must stay intact.
    newly, preview = agg.update("eu acho quero ir")
    assert agg.text == "eu acho"
    assert newly == ""
    assert preview == "quero ir"


def test_finalize_commits_remaining_tail():
    agg = LocalAgreement()
    agg.update("bom dia")
    agg.update("bom dia pessoal")      # commits "bom dia"
    newly = agg.finalize()             # commit the leftover "pessoal"
    assert newly == "pessoal"
    assert agg.text == "bom dia pessoal"


def test_finalize_never_drops_committed_words():
    agg = LocalAgreement()
    agg.update("um dois tres")
    agg.update("um dois tres")          # commits all three
    # A shorter final hypothesis must not erase confirmed words.
    newly = agg.finalize("um dois")
    assert newly == ""
    assert agg.text == "um dois tres"


def test_reset_clears_state():
    agg = LocalAgreement()
    agg.update("a b")
    agg.update("a b c")
    agg.reset()
    assert agg.text == ""
    newly, preview = agg.update("x y")
    assert newly == "" and preview == "x y"
