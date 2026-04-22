# yappr

`yappr` is a Lighthouse-style CLI for auditing AI search visibility with Peec.

```bash
uv run yappr audit example.com
```

Current scope:

- Day 1 scaffold with `uv`, Typer, typed config loading, and Peec REST auth.
- `audit <domain>` verifies connectivity and prints the selected Peec project.
- Scoring/check/render modules are scaffolded for the next implementation steps.
