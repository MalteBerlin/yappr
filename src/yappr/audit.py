from __future__ import annotations

from collections import Counter

from yappr.checks import coverage, diversity, gap, sentiment, topics
from yappr.checks.base import CheckResult
from yappr.peec.models import AuditReport, Opportunity, PeecData
from yappr.scoring import aggregate, status


def build_report(data: PeecData) -> AuditReport:
    results = [
        coverage.run(data),
        diversity.run(data),
        sentiment.run(data),
        topics.run(data),
        gap.run(data),
    ]
    score = aggregate(results)
    symbol, color, label = status(score)
    opportunities = derive_opportunities(data, results)
    return AuditReport(
        domain=data.domain,
        project_name=data.project_name,
        project_scope=data.project_scope,
        date_range=data.date_range,
        models=data.active_models,
        score=score,
        symbol=symbol,
        color=color,
        label=label,
        checks=results,
        opportunities=opportunities,
    )


def derive_opportunities(data: PeecData, results: list[CheckResult]) -> list[Opportunity]:
    opportunities: list[Opportunity] = []
    deficits = {result.id: 100 - result.score for result in results}

    if data.gap_url_sources:
        by_classification = Counter(
            source.classification or "OTHER"
            for source in data.gap_url_sources
            if source.classification
        )
        classification, count = by_classification.most_common(1)[0]
        opportunities.append(
            Opportunity(
                id="1",
                category="EDITORIAL",
                label=f"Get cited in more {classification.replace('_', ' ').title()} pages",
                impact=max(6, min(25, count * 2 + round(deficits["coverage"] * 0.1))),
            )
        )

    gap_domains = [
        source.domain
        for source in data.gap_sources
        if source.classification in {"UGC", "REFERENCE"}
        or source.domain in {"reddit.com", "youtube.com"}
    ]
    if gap_domains:
        domain, count = Counter(gap_domains).most_common(1)[0]
        ugc_domains = {"reddit.com", "youtube.com", "linkedin.com", "g2.com"}
        category = "UGC" if domain in ugc_domains else "REFERENCE"
        label = f"Build presence on {domain}"
        opportunities.append(
            Opportunity(
                id=str(len(opportunities) + 1),
                category=category,
                label=label,
                impact=max(5, min(18, count * 3 + round(deficits["diversity"] * 0.08))),
            )
        )

    own_domain = data.own_brand.domains[0] if data.own_brand.domains else data.domain
    opportunities.append(
        Opportunity(
            id=str(len(opportunities) + 1),
            category="OWNED",
            label=f"Strengthen owned pages on {own_domain}",
            impact=max(4, min(15, round((deficits["coverage"] + deficits["topics"]) * 0.08))),
        )
    )

    weak_topics = [
        topic for topic in data.topics if topic.competitor_max_visibility > topic.visibility
    ]
    if weak_topics:
        topic = max(weak_topics, key=lambda item: item.competitor_max_visibility - item.visibility)
        opportunities.append(
            Opportunity(
                id=str(len(opportunities) + 1),
                category="TOPIC",
                label=f"Publish content for '{topic.topic_name}'",
                impact=max(4, min(16, round(deficits["topics"] * 0.12))),
            )
        )

    ranked = sorted(opportunities, key=lambda item: item.impact, reverse=True)
    return [
        item.model_copy(update={"id": str(index)})
        for index, item in enumerate(ranked[:3], start=1)
    ]
