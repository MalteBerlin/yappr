from __future__ import annotations

from yappr.checks.base import CheckResult
from yappr.peec.models import PeecData


def run(data: PeecData) -> CheckResult:
    if not data.topics:
        return CheckResult(
            id="topics",
            name="Topic Coverage",
            score=0,
            weight=0.20,
            summary="No tracked topics are available yet.",
            raw={},
        )

    visible_topics = [topic for topic in data.topics if topic.visibility > 0.05]
    total_topics = len(data.topics)
    invisible_topics = total_topics - len(visible_topics)
    score = round(len(visible_topics) / total_topics * 100)

    weakest_topic = max(
        data.topics,
        key=lambda topic: topic.competitor_max_visibility - topic.visibility,
        default=None,
    )
    topic_name = weakest_topic.topic_name if weakest_topic else "n/a"
    summary = (
        f"Invisible on {invisible_topics} of {total_topics} tracked topics. "
        f"Biggest gap: '{topic_name}'."
    )
    return CheckResult(
        id="topics",
        name="Topic Coverage",
        score=score,
        weight=0.20,
        summary=summary,
        raw={
            "visible_topics": len(visible_topics),
            "total_topics": total_topics,
            "weakest_topic": topic_name,
        },
    )
