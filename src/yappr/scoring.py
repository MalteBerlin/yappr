from __future__ import annotations

from yappr.checks.base import CheckResult


def aggregate(results: list[CheckResult]) -> int:
    """Weighted average of all check scores, returned as a 0-100 integer."""
    total = sum(result.score * result.weight for result in results)
    return round(total)


def status(score: int) -> tuple[str, str, str]:
    """Return the audit symbol, color, and label for a score range."""
    if score < 40:
        return "✗", "red", "Needs work"
    if score < 70:
        return "⚠", "yellow", "Room to grow"
    return "✓", "green", "Strong"
