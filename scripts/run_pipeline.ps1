param(
  [string]$Profile = "live",
  [int]$Days = 90,
  [string]$Name = "澜"
)

$ErrorActionPreference = 'Stop'

# Ensure OKX_* env vars won't override ~/.okx/config.toml
$env:OKX_API_KEY=$null
$env:OKX_SECRET_KEY=$null
$env:OKX_PASSPHRASE=$null
$env:OKX_SITE=$null
$env:OKX_API_BASE_URL=$null

$root = Split-Path -Parent $MyInvocation.MyCommand.Definition | Split-Path -Parent
$ts = Get-Date -Format 'yyyyMMdd_HHmmss'
$run = Join-Path $root ("runs\\" + $ts)
$raw = Join-Path $run 'raw'
$analysis = Join-Path $run 'analysis'
$output = Join-Path $run 'output'

New-Item -ItemType Directory -Force -Path $raw,$analysis,$output | Out-Null

# 1) Export
node (Join-Path $root 'scripts\\export_contracts.js') --profile $Profile --days $Days --out $raw | Out-Null

# 2) Analyze
python (Join-Path $root 'scripts\\analyze_contracts.py') --raw $raw --out $analysis | Out-Null

# 3) Render report
python (Join-Path $root 'scripts\\render_report.py') --analysis (Join-Path $analysis 'analysis.json') --out $output | Out-Null

# 4) Render letter
if ($env:ANTHROPIC_API_KEY) {
  python (Join-Path $root 'scripts\\render_letter_ai.py') `
    --analysis (Join-Path $analysis 'analysis.json') `
    --report (Join-Path $output 'REPORT.md') `
    --out $output `
    --name $Name
  python (Join-Path $root 'scripts\\render_letter_html.py') `
    --analysis (Join-Path $analysis 'analysis.json') `
    --template (Join-Path $root 'assets\\letter-version.template.html') `
    --letter-md (Join-Path $output 'LETTER.md') `
    --out $output | Out-Null
} else {
  Write-Host "[WARN] 未设置 ANTHROPIC_API_KEY，回退到模板信。"
  python (Join-Path $root 'scripts\\render_letter_md.py') --analysis (Join-Path $analysis 'analysis.json') --out $output | Out-Null
  python (Join-Path $root 'scripts\\render_letter_html.py') --analysis (Join-Path $analysis 'analysis.json') --template (Join-Path $root 'assets\\letter-version.template.html') --out $output | Out-Null
}

Write-Host "DONE: $run"
Write-Host "- raw: $raw"
Write-Host "- analysis: $analysis"
Write-Host "- output: $output"
