from __future__ import annotations

from yappr.checks.base import CheckResult
from yappr.peec.models import PeecData


def run(data: PeecData) -> CheckResult:
    if not data.all_domain_sources:
        return CheckResult(
            id="diversity",
            name="Source Diversity",
            score=0,
            weight=0.20,
            summary="No source citation data yet.",
            raw={},
        )

    own_types = {source.classification for source in data.domain_sources if source.classification}
    unique_types = len(own_types)
    score = min(round(unique_types / 8 * 100), 100)

    competitor_counts = []
    for competitor in data.competitors:
        source_types = {
            source.classification
            for source in data.all_domain_sources
            if competitor.id in source.mentioned_brand_ids and source.classification
        }
        competitor_counts.append(len(source_types))

    if competitor_counts:
        competitor_average = round(sum(competitor_counts) / len(competitor_counts), 1)
    else:
        competitor_average = 0.0
    summary = (
        f"Retrieved from {unique_types} distinct source types. "
        f"Competitors average {competitor_average}."
    )
    return CheckResult(
        id="diversity",
        name="Source Diversity",
        score=score,
        weight=0.20,
        summary=summary,
        raw={
            "unique_types": sorted(own_types),
            "competitor_average": competitor_average,
        },
    )
