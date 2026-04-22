from __future__ import annotations

from html import escape

from yappr.peec.models import AuditReport


def render_report(report: AuditReport) -> str:
    checks = "".join(
        f"""
        <section class="check">
          <div class="check-head">
            <strong>{escape(check.name)}</strong>
            <span>{check.score} / 100</span>
          </div>
          <p>{escape(check.summary)}</p>
        </section>
        """
        for check in report.checks
    )
    opportunities = "".join(
        f"""
        <li>
          <strong>[{escape(item.category)}]</strong> {escape(item.label)}
          <span>+{item.impact} pts</span>
        </li>
        """
        for item in report.opportunities
    )
    models = ", ".join(report.models) if report.models else "No active models reported"
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>yappr report · {escape(report.domain)}</title>
  <style>
    :root {{
      --bg: #f6f1e8;
      --ink: #16110d;
      --muted: #6f645c;
      --accent: #0f766e;
      --card: #fffdf8;
      --line: #d9cfc2;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: Georgia, "Iowan Old Style", serif;
      background:
        radial-gradient(circle at top left, rgba(15,118,110,.12), transparent 30%),
        linear-gradient(180deg, #fbf8f2, var(--bg));
      color: var(--ink);
    }}
    main {{ max-width: 900px; margin: 0 auto; padding: 48px 24px 64px; }}
    .hero {{ display: grid; gap: 12px; margin-bottom: 32px; }}
    .score {{
      width: 180px;
      border: 2px solid var(--ink);
      border-radius: 18px;
      padding: 28px 0;
      text-align: center;
      background: var(--card);
      font-size: 48px;
      font-weight: 700;
    }}
    .meta {{ color: var(--muted); }}
    .checks, .opportunities {{
      background: rgba(255,255,255,.78);
      border: 1px solid var(--line);
      border-radius: 20px;
      padding: 24px;
      backdrop-filter: blur(8px);
    }}
    .checks {{ display: grid; gap: 18px; margin-bottom: 24px; }}
    .check-head {{
      display: flex;
      justify-content: space-between;
      gap: 16px;
    }}
    .opportunities ul {{ margin: 0; padding-left: 20px; display: grid; gap: 12px; }}
    .opportunities span {{ color: var(--accent); font-weight: 700; }}
  </style>
</head>
<body>
  <main>
    <section class="hero">
      <h1>yappr · AI Visibility Audit · {escape(report.domain)}</h1>
      <div class="score">{report.score}<div style="font-size:18px">/ 100</div></div>
      <div><strong>{escape(report.label)}</strong></div>
      <div class="meta">Models: {escape(models)}</div>
      <div class="meta">
        Window: {escape(report.date_range[0])} to {escape(report.date_range[1])}
      </div>
    </section>
    <section class="checks">
      {checks}
    </section>
    <section class="opportunities">
      <h2>Top Opportunities</h2>
      <ul>{opportunities}</ul>
    </section>
  </main>
</body>
</html>
"""
