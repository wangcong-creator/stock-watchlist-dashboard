# ETF Decay Charts

## What This Project Does

Generates leveraged ETF volatility-decay comparison charts showing daily-reset 2× vs naive 2× performance from each ETF's IPO date.

**GitHub repo (deployment target):** `wangcong-creator/etf-decay-charts`  
**Live site:** https://wangcong-creator.github.io/etf-decay-charts/

> **IMPORTANT:** Do NOT push these files via `git push` — the local git remote points to `stock-watchlist-dashboard`. Deploy to `etf-decay-charts` via the GitHub API only (see Deployment section below).

## Prerequisites

```
pip install yfinance pandas matplotlib numpy
```

## Two Scripts

### 1. Interactive Charts (primary) — `generate_interactive_charts.py`

Browser-rendered with ECharts. Date selector for slicing time windows. Supports 2× and 3× ETFs.

```
.venv/bin/python3 etf-decay-charts/generate_interactive_charts.py          # all ETFs
.venv/bin/python3 etf-decay-charts/generate_interactive_charts.py MULL     # single ETF (quick verify)
```

Output: `etf-decay-charts/index.html` (~1 MB, self-contained)

### 2. Static Charts — `generate_decay_charts.py`

Matplotlib charts embedded as base64 PNGs. Larger file, no interactivity.

```
.venv/bin/python3 etf-decay-charts/generate_decay_charts.py
```

Output: `etf-decay-charts/decay_charts.html` (~8.5 MB, self-contained)

## Deployment

Both HTML files deploy to `wangcong-creator/etf-decay-charts` via the GitHub API.

### Deploy `index.html` (interactive charts)

```bash
# 1. Get current file SHA
gh api repos/wangcong-creator/etf-decay-charts/contents/index.html --jq '.sha'

# 2. Upload
base64 -i etf-decay-charts/index.html | gh api repos/wangcong-creator/etf-decay-charts/contents/index.html \
  --method PUT \
  --field message="Update interactive decay charts" \
  --field sha="<sha from step 1>" \
  --field content=@-
```

### Deploy `decay_charts.html` (static charts)

```bash
# 1. Get current file SHA
gh api repos/wangcong-creator/etf-decay-charts/contents/decay_charts.html --jq '.sha'

# 2. Upload
base64 -i etf-decay-charts/decay_charts.html | gh api repos/wangcong-creator/etf-decay-charts/contents/decay_charts.html \
  --method PUT \
  --field message="Update static decay charts" \
  --field sha="<sha from step 1>" \
  --field content=@-
```

## ETF Configuration

ETF pairs are defined in `ETF_CONFIG` (interactive script) and `ETF_MAP` (static script) at the top of each file. Each entry maps a 2× leveraged ETF to its 1× underlying and optionally a 3× counterpart.

To add a new ETF pair: add an entry to `ETF_CONFIG` / `ETF_MAP` and re-run.
