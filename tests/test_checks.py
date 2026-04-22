from yappr.audit import build_report
from yappr.peec.models import Brand, DomainSource, PeecData, TopicCoverage, URLSource


def test_build_report_scores_and_opportunities() -> None:
    data = PeecData(
        project_id="project-scoped",
        project_name=None,
        project_scope="project",
        domain="example.com",
        own_brand=Brand(
            id="own",
            name="Example",
            domains=["example.com"],
            is_own=True,
            visibility=0.12,
            sentiment=76,
            mention_count=5,
            visibility_total=100,
        ),
        competitors=[
            Brand(id="comp-1", name="Acme", visibility=0.67),
            Brand(id="comp-2", name="Contoso", visibility=0.42),
        ],
        topics=[
            TopicCoverage(
                topic_id="t1",
                topic_name="Topic A",
                visibility=0.2,
                competitor_max_visibility=0.6,
            ),
            TopicCoverage(
                topic_id="t2",
                topic_name="Topic B",
                visibility=0.0,
                competitor_max_visibility=0.4,
            ),
        ],
        all_domain_sources=[
            DomainSource(domain="example.com", classification="OWN", mentioned_brand_ids=["own"]),
            DomainSource(domain="reddit.com", classification="UGC", mentioned_brand_ids=["comp-1"]),
            DomainSource(domain="g2.com", classification="UGC", mentioned_brand_ids=["comp-2"]),
            DomainSource(
                domain="listicle.com",
                classification="EDITORIAL",
                mentioned_brand_ids=["own", "comp-1"],
            ),
        ],
        domain_sources=[
            DomainSource(domain="example.com", classification="OWN", mentioned_brand_ids=["own"]),
            DomainSource(
                domain="listicle.com",
                classification="EDITORIAL",
                mentioned_brand_ids=["own", "comp-1"],
            ),
        ],
        gap_sources=[
            DomainSource(domain="reddit.com", classification="UGC", mentioned_brand_ids=["comp-1"]),
            DomainSource(domain="g2.com", classification="UGC", mentioned_brand_ids=["comp-2"]),
        ],
        gap_url_sources=[
            URLSource(
                url="https://listicle.com/best-tools",
                classification="LISTICLE",
                title="Best Tools",
                mentioned_brand_ids=["comp-1"],
            )
        ],
        active_models=["ChatGPT", "Gemini"],
        total_chats=100,
        date_range=("2026-03-23", "2026-04-22"),
    )

    report = build_report(data)

    assert report.score == 38
    assert report.label == "Needs work"
    assert report.checks[0].summary.startswith("Cited in 12%")
    assert report.opportunities[0].category == "EDITORIAL"
    assert report.opportunities[0].impact >= report.opportunities[-1].impact


def test_sentiment_returns_zero_when_brand_is_never_mentioned() -> None:
    data = PeecData(
        project_id="project-scoped",
        project_name=None,
        project_scope="project",
        domain="example.com",
        own_brand=Brand(id="own", name="Example", domains=["example.com"], is_own=True),
        competitors=[],
        total_chats=10,
        date_range=("2026-03-23", "2026-04-22"),
    )

    report = build_report(data)

    sentiment_check = next(check for check in report.checks if check.id == "sentiment")
    assert sentiment_check.score == 0
    assert "not mentioned" in sentiment_check.summary
