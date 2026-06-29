# Stock / ETF Projects — Root

This repo contains two independent projects sharing a single git root and `.venv`.

| Sub-project | Folder | GitHub Repo | Purpose |
|---|---|---|---|
| Stock Watchlist Dashboard | `stock-dashboard/` | `wangcong-creator/stock-watchlist-dashboard` | 124-stock watchlist with sector filters, sparklines, price history |
| ETF Decay Charts | `etf-decay-charts/` | `wangcong-creator/etf-decay-charts` | Leveraged ETF volatility-decay analysis (interactive + static) |

## Shared Setup

```
pip install yfinance pandas matplotlib numpy
```

Virtual environment is at `.venv/` (repo root). Run scripts with:

```
.venv/bin/python3 stock-dashboard/generate_dashboard.py
.venv/bin/python3 etf-decay-charts/generate_interactive_charts.py
```

Or activate once: `source .venv/bin/activate`, then call scripts directly.

## Project Docs

- Stock dashboard details → [stock-dashboard/CLAUDE.md](stock-dashboard/CLAUDE.md)
- ETF decay charts details → [etf-decay-charts/CLAUDE.md](etf-decay-charts/CLAUDE.md)
