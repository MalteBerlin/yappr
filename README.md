<p align="center">
  <img src="./assets/cover.png" alt="yappr cover" width="920" />
</p>

<h1 align="center">yappr</h1>

<p align="center">
  Lighthouse for AI search visibility.
</p>

<p align="center">
  <code>uv run yappr audit yoursite.com</code>
</p>

`yappr` is a CLI for auditing how your brand shows up across AI search engines using [Peec AI data](https://docs.peec.ai/api/introduction).

## What It Does

- Runs an AI visibility audit and produces a single score.
- Surfaces the domains and pages shaping your visibility.
- Shows competitor gaps and ranked next moves.
- Works well for terminal use, sharing, and CI.

## Commands

```bash
yappr key --set
yappr audit tryprism.com
yappr peek tryprism.com
yappr cite tryprism.com --gap
yappr diff tryprism.com --days 14
yappr next tryprism.com
```

## Quick Start

```bash
uv sync --dev
uv run yappr key --set
uv run yappr audit tryprism.com
```
