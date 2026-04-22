from yappr.checks.base import CheckResult
from yappr.scoring import aggregate, status


def test_aggregate_returns_weighted_average() -> None:
    results = [
        CheckResult(id="coverage", name="Coverage", score=40, weight=0.30, summary=""),
        CheckResult(id="diversity", name="Diversity", score=50, weight=0.20, summary=""),
        CheckResult(id="sentiment", name="Sentiment", score=80, weight=0.15, summary=""),
        CheckResult(id="topics", name="Topics", score=30, weight=0.20, summary=""),
        CheckResult(id="gap", name="Gap", score=70, weight=0.15, summary=""),
    ]

    assert aggregate(results) == 50


def test_status_ranges() -> None:
    assert status(10) == ("✗", "red", "Needs work")
    assert status(55) == ("⚠", "yellow", "Room to grow")
    assert status(88) == ("✓", "green", "Strong")
