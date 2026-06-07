# Stock Watchlist Dashboard

## What This Project Does

Reads `stock list.txt` (124 tickers), fetches historical price data and company info from Yahoo Finance via `yfinance`, and generates a self-contained interactive `dashboard.html` file.

## Prerequisites

```
pip install yfinance pandas
```

## How to Run

```
python generate_dashboard.py
```

Then open `dashboard.html` in any browser. No server required — the file is fully self-contained.

## Dashboard Features

- **Sector pills**: Click to filter by industry (Chip Designers, Equipment, Foundries, Memory, Optical, AI/Data Center, Networking, Energy, Space, Crypto, ETFs, Leveraged ETFs, etc.)
- **Filter bar**: Search by name/ticker, filter by sector/exchange/type/currency, sort by any metric
- **Stock cards**: Ticker, name, sector badge, current price, 1D % change, sparkline chart, market cap, P/E, beta
- **Detail modal**: Full price history chart from IPO, all key metrics, company description, website link

## Stock List (`stock list.txt`)

One stock per line. Supported formats:
- `TICKER - Company Name`
- `Chinese Name (TICKER)`
- `TICKER公司`

To add/remove stocks: edit the file and re-run the script.

## Cache (`stock_cache.json`)

Auto-generated on first run. Data is reused for **24 hours** before re-fetching. To force a full refresh:

```
del stock_cache.json
python generate_dashboard.py
```

To refresh only specific tickers: delete their entries from `stock_cache.json` (it's plain JSON).

## Configuration

Edit constants at the top of `generate_dashboard.py`:

| Constant | Default | Description |
|---|---|---|
| `CACHE_MAX_AGE_HRS` | `24` | Hours before data is considered stale |
| `CHART_PERIOD` | `"max"` | yfinance period — `"max"` = from IPO; also `"10y"`, `"5y"`, `"1y"` |
| `RATE_LIMIT_DELAY` | `0.3` | Seconds between API calls (increase if getting throttled) |

## Sector Classifications

Defined in `SECTOR_MAP` dict at the top of `generate_dashboard.py`. Each ticker maps to one of these sector keys:

| Key | Label |
|---|---|
| `chip_designer` | Chip Designers |
| `chip_equipment` | Chip Equipment |
| `foundry` | Foundries & Fab |
| `packaging_ems` | Packaging / EMS |
| `memory_storage` | Memory & Storage |
| `optical_photonics` | Optical & Photonics |
| `ai_datacenter` | AI & Data Center |
| `networking` | Networking & Comms |
| `energy_power` | Energy & Power |
| `space_aerospace` | Space & Aerospace |
| `crypto` | Crypto & Blockchain |
| `etf_semi` | Semiconductor ETFs |
| `etf_other` | Space / Other ETFs |
| `leveraged_etf` | Leveraged ETFs (2×) |
| `hardware_other` | Hardware & Other |

To reclassify a ticker, change its value in `SECTOR_MAP` and re-run the script. No re-fetch is needed for sector changes — the dashboard is regenerated from cache.
