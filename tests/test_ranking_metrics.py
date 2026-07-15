import pytest

from wamprobe.metrics import candidate_ranking_correlation


def test_candidate_ranking_correlation_has_exact_oracle_and_reversed_bounds() -> None:
    truth = {"best": 3.0, "middle": 2.0, "worst": 1.0}

    oracle = candidate_ranking_correlation(truth, truth)
    reversed_result = candidate_ranking_correlation(
        {"best": 1.0, "middle": 2.0, "worst": 3.0},
        truth,
    )

    assert oracle.spearman == 1.0
    assert oracle.kendall_tau == 1.0
    assert oracle.ndcg == 1.0
    assert oracle.pairwise_preference_accuracy == 1.0
    assert reversed_result.spearman == -1.0
    assert reversed_result.kendall_tau == -1.0
    assert 0.0 <= reversed_result.ndcg < 1.0
    assert reversed_result.pairwise_preference_accuracy == 0.0


def test_candidate_ranking_correlation_handles_tied_predictions() -> None:
    result = candidate_ranking_correlation(
        {"best": 0.0, "middle": 0.0, "worst": 0.0},
        {"best": 3.0, "middle": 2.0, "worst": 1.0},
    )

    assert result.spearman == 0.0
    assert result.kendall_tau == 0.0
    assert result.pairwise_preference_accuracy == 0.5
    assert 0.0 <= result.ndcg <= 1.0


def test_candidate_ranking_correlation_rejects_unpaired_candidates() -> None:
    with pytest.raises(ValueError, match="candidate names"):
        candidate_ranking_correlation({"left": 1.0}, {"right": 1.0})
    with pytest.raises(ValueError, match="at least two"):
        candidate_ranking_correlation({"only": 1.0}, {"only": 1.0})
