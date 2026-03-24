---
name: okx-trade-history-analyzer
description: End-to-end OKX CEX trade history export + analysis + report/letter generation using OKX Agent Trade Kit credentials (~/.okx/config.toml). Use when user wants to export OKX CEX spot/swap/futures orders/fills/bills, analyze trading behavior/performance, generate an objective report and a friend-style letter (Markdown + fixed HTML template), and optionally publish results to a GitHub folder.
---

# OKX Trade History Analyzer (Agent Trade Kit)

## What this skill does

Runs a full pipeline:
1) Export OKX CEX trade history (contracts first: SWAP/FUTURES) into JSONL
2) Analyze and compute metrics (coverage + multi-dimensional stats)
3) Generate outputs:
   - REPORT.md (objective)
   - LETTER.md (friend letter)
   - result-pages/letter-version.html (fixed template, only text replaced)

All credentials are read from `~/.okx/config.toml` (Agent Trade Kit profile). No keys are ever requested in chat.

## Prerequisites (user)

- OKX Agent Trade Kit credentials already configured in:
  - Windows: `C:\Users\<you>\.okx\config.toml`
- Node.js >= 18
- Python 3.10+

## Run (local)

Use the PowerShell pipeline script (recommended):

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\run_pipeline.ps1 -Profile live -Days 90
```

Outputs are written under:

- `runs/<timestamp>/raw/` (exported JSONL)
- `runs/<timestamp>/analysis/` (analysis.json)
- `runs/<timestamp>/output/` (REPORT.md, LETTER.md, result-pages/letter-version.html)

## Notes / safety

- The pipeline clears `OKX_*` environment variables for the process so they cannot override `~/.okx/config.toml`.
- Default mode is read-only data export + analysis.
- If some endpoints return empty, the report includes a coverage section so results are not over-claimed.

## When to publish to GitHub

Publishing is optional. If enabled, it will copy the `output/` folder into a chosen repo folder and git commit/push.
See `scripts/publish_github.ps1`.
