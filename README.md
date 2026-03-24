# OKX Trade History Analyzer (Agent Trade Kit)

One-command pipeline to:
- Export OKX CEX trade history (contracts: SWAP/FUTURES)
- Analyze behavior/performance
- Generate outputs: REPORT.md / LETTER.md / result-pages/letter-version.html

## Quick start

1) Configure your OKX API credentials in `~/.okx/config.toml` (Agent Trade Kit profile format).

2) Run:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\run_pipeline.ps1 -Profile live -Days 90
```

Outputs will be written to `runs/<timestamp>/`.

## Notes

- This tool clears `OKX_*` environment variables for the process so they cannot override `~/.okx/config.toml`.
- Default is read-only export + analysis.

