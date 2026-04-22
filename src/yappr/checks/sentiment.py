from __future__ import annotations

from yappr.checks.base import CheckResult
from yappr.peec.models import PeecData


def run(data: PeecData) -> CheckResult:
    if data.own_brand.mention_count == 0:
        return CheckResult(
            id="sentiment",
            name="Sentiment",
            score=0,
            weight=0.15,
            summary="No sentiment data yet because your brand was not mentioned.",
            raw={},
        )

    score = round(data.own_brand.sentiment)
    if score >= 70:
        summary = "AI describes your brand positively when mentioned."
    elif score >= 40:
        summary = "AI describes your brand neutrally."
    else:
        summary = "AI describes your brand negatively. Investigate which sources are shaping this."

    return CheckResult(
        id="sentiment",
        name="Sentiment",
        score=score,
        weight=0.15,
        summary=summary,
        raw={"sentiment": data.own_brand.sentiment},
    )
