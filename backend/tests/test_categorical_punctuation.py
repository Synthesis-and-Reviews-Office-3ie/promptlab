"""Categorical values come from a closed taxonomy, so punctuation can't distinguish them.

Production bug this fixes: the taxonomy handed to the model says
"Agriculture fishing and forestry" while the ground truth says
"Agriculture, fishing, and forestry". Scoring required exact equality after
`_norm`, which keeps punctuation, so 22 of 100 sector_name records were
unwinnable -- models were marked wrong for obeying our own option list. The same divergence
also appears as "&" vs the word "and" (59 of 7,623 records); both fold.
"""
from __future__ import annotations

import pytest

from backend.app import scoring
from backend.app.analytics import compute_confusion, gate_metrics


class TestFoldCategory:
    @pytest.mark.parametrize("a,b", [
        ("Agriculture, fishing, and forestry", "Agriculture fishing and forestry"),
        ("Industry, trade, and services", "Industry trade and services"),
        ("Water, sanitation, and waste management", "Water sanitation and waste management"),
    ])
    def test_real_taxonomy_variants_collapse(self, a, b):
        assert scoring.fold_category(a) == scoring.fold_category(b)

    def test_ampersand_variant_folds_to_the_word_and(self):
        # REVERSED 2026-08-25; this previously asserted the opposite.
        #
        # Scope, measured rather than assumed: 59 of 7,623 sector_name ground-truth
        # records (0.8%) use the '&' spelling, but only 1 of the 208 records that
        # currently have model runs. So the old note calling it 'one record' was
        # right about today's evaluation set, and the fix is not worth much score.
        # It is here because an unwinnable comparison is a defect whatever its
        # frequency, and because the affected share of the master data is 75x the
        # extracted share -- it grows as the rollout grows.
        #
        # The old note preferred normalising the ground-truth value over folding.
        # Folding was chosen because the ground truth is the answer key and editing
        # it is human-gated by design, while an ampersand-vs-and divergence is a
        # spelling difference the comparison should absorb wherever it turns up.
        assert (scoring.fold_category("Information & communications technologies")
                == scoring.fold_category("Information and communications technologies"))

    def test_genuinely_different_categories_stay_different(self):
        assert scoring.fold_category("Health") != scoring.fold_category("Education")

    def test_case_and_whitespace_still_folded(self):
        assert scoring.fold_category("  HEALTH  ") == scoring.fold_category("health")


class TestCategoricalScoringUsesTheFold:
    def test_oxford_comma_variant_scores_as_exact_match(self):
        r = scoring.score_field(
            "sector_name", "Agriculture fishing and forestry", "Agriculture, fishing, and forestry")
        assert r.is_correct
        assert r.score == 1.0

    def test_confusion_treats_variants_as_one_class(self):
        rows = [
            {"predicted": "Agriculture fishing and forestry",
             "truth": "Agriculture, fishing, and forestry"},
            {"predicted": "Agriculture, fishing, and forestry",
             "truth": "Agriculture fishing and forestry"},
        ]
        conf = compute_confusion("sector_name", rows)
        assert conf["accuracy"] == pytest.approx(1.0)
        # One real class, not two spellings of it.
        assert len([c for c in conf["truth_labels"] if c != "(other)"]) == 1

    def test_kappa_not_deflated_by_spelling(self):
        rows = [{"predicted": "Agriculture fishing and forestry",
                 "truth": "Agriculture, fishing, and forestry"}] * 5 + \
               [{"predicted": "Health", "truth": "Health"}] * 5
        gm = gate_metrics("sector_name", rows)
        assert gm["accuracy"] == pytest.approx(1.0)


class TestListFieldsAreNotAffected:
    """The fold must never reach free-text list values: "Smith, John" is
    Last, First, and dropping that comma invites false author matches."""

    def test_author_comma_is_preserved_by_norm(self):
        assert "," in scoring._norm("Smith, John")

    def test_distinct_authors_do_not_collapse(self):
        # Without the comma these two would look far more similar than they are.
        r = scoring.score_field("authors", ["Smith, John"], ["Smith, Joan"])
        assert not r.is_correct

    def test_list_scoring_unchanged_for_exact_match(self):
        r = scoring.score_field("authors", ["Smith, John"], ["Smith, John"])
        assert r.is_correct
