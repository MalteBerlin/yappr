from __future__ import annotations

from yappr.checks.base import CheckResult
from yappr.peec.models import PeecData


def run(data: PeecData) -> CheckResult:
    if data.total_chats == 0:
        return CheckResult(
            id="coverage",
            name="Citation Coverage",
            score=0,
            weight=0.30,
            summary="No Peec chat data yet for this window.",
            raw={},
        )

    visibility = data.own_brand.visibility
    score = round(visibility * 100)
    competitor = max(data.competitors, key=lambda brand: brand.visibility, default=None)
    competitor_name = competitor.name if competitor else None
    competitor_pct = round((competitor.visibility if competitor else 0.0) * 100)
    if competitor_name and competitor_pct > 0:
        summary = (
            f"Cited in {score}% of {data.total_chats} AI responses. "
            f"Top competitor ({competitor_name}) is cited in {competitor_pct}%."
        )
    elif data.gap_sources:
        summary = (
            f"Cited in {score}% of {data.total_chats} AI responses. "
            f"Competitors still appear on {len(data.gap_sources)} sources where you're absent."
        )
    else:
        summary = f"Cited in {score}% of {data.total_chats} AI responses."
    return CheckResult(
        id="coverage",
        name="Citation Coverage",
        score=score,
        weight=0.30,
        summary=summary,
        raw={
            "visibility": visibility,
            "total_chats": data.total_chats,
            "top_competitor": competitor_name,
            "top_competitor_visibility": competitor_pct,
        },
    )
