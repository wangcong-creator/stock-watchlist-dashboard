#!/usr/bin/env python3
"""
generate_dashboard.py  —  Stock Watchlist Dashboard Generator
Usage  : python generate_dashboard.py
Output : dashboard.html  (open in any browser, no server needed)
"""

import json
import re
import sys
import time
import os
from datetime import datetime, timezone
from pathlib import Path

# ══════════════════════════════════════════════════════════════════════════════
# 1  CONSTANTS
# ══════════════════════════════════════════════════════════════════════════════
STOCK_LIST_FILE   = "stock list.txt"
CACHE_FILE        = "stock_cache.json"
OUTPUT_FILE       = "dashboard.html"
CACHE_MAX_AGE_HRS = 24
CHART_PERIOD      = "max"   # "max" = from IPO; also "10y", "5y", "1y"
RATE_LIMIT_DELAY  = 0.4     # seconds between API calls

# ══════════════════════════════════════════════════════════════════════════════
# 2  SECTOR CLASSIFICATION
# ══════════════════════════════════════════════════════════════════════════════
SECTOR_MAP = {
    # Chip Designers
    "NVDA": "chip_designer", "AMD": "chip_designer", "INTC": "chip_designer",
    "QCOM": "chip_designer", "TXN": "chip_designer", "ON": "chip_designer",
    "STM": "chip_designer", "MU": "chip_designer", "AVGO": "chip_designer",
    "ARM": "chip_designer", "MRVL": "chip_designer", "NXPI": "chip_designer",
    "MPWR": "chip_designer", "ADI": "chip_designer", "MCHP": "chip_designer",
    "WOLF": "chip_designer",
    # Chip Equipment
    "LRCX": "chip_equipment", "KLAC": "chip_equipment", "AMAT": "chip_equipment",
    "ASML": "chip_equipment", "TER": "chip_equipment", "AEHR": "chip_equipment",
    "FORM": "chip_equipment", "MKSI": "chip_equipment", "UCTT": "chip_equipment",
    "ONTO": "chip_equipment", "ATEYY": "chip_equipment", "KEYS": "chip_equipment",
    # Foundries & Fab
    "TSM": "foundry", "GFS": "foundry", "UMC": "foundry",
    "TSEM": "foundry", "SKYT": "foundry",
    # Packaging / EMS
    "ASX": "packaging_ems", "AMKR": "packaging_ems", "SANM": "packaging_ems",
    "CLS": "packaging_ems", "TTMI": "packaging_ems", "FN": "packaging_ems",
    "FLEX": "packaging_ems",
    # Memory & Storage
    "STX": "memory_storage", "SNDK": "memory_storage", "WDC": "memory_storage",
    "MRAM": "memory_storage",
    # Optical & Photonics
    "LITE": "optical_photonics", "COHR": "optical_photonics", "CIEN": "optical_photonics",
    "AAOI": "optical_photonics", "VIAV": "optical_photonics", "AXTI": "optical_photonics",
    "POET": "optical_photonics", "GLW": "optical_photonics",
    # AI & Data Center
    "ALAB": "ai_datacenter", "CRWV": "ai_datacenter", "NBIS": "ai_datacenter",
    "APLD": "ai_datacenter", "IREN": "ai_datacenter", "VRT": "ai_datacenter",
    "ANET": "ai_datacenter",
    # Networking & Comms
    "NET": "networking", "ERIC": "networking", "NOK": "networking", "GSAT": "networking",
    # Energy & Power
    "GEV": "energy_power", "BE": "energy_power", "VST": "energy_power",
    "ETN": "energy_power", "CMI": "energy_power", "FLNC": "energy_power",
    "UUUU": "energy_power", "LEU": "energy_power",
    # Space & Aerospace
    "RKLB": "space_aerospace", "PL": "space_aerospace", "ASTS": "space_aerospace",
    "LUNR": "space_aerospace", "HWM": "space_aerospace",
    # Crypto & Blockchain
    "COIN": "crypto", "IBIT": "crypto", "MSTR": "crypto", "ETHA": "crypto",
    "BMNR": "crypto", "CRCL": "crypto", "SATS": "crypto",
    # Semiconductor ETFs
    "SOXX": "etf_semi", "SOXL": "etf_semi", "CHPS": "etf_semi",
    "SMH": "etf_semi", "DRAM": "etf_semi",
    # Space / Other ETFs
    "UFO": "etf_other", "NASA": "etf_other", "EUV": "etf_other",
    # Leveraged ETFs (2x)
    "GGLL": "leveraged_etf", "ARMG": "leveraged_etf", "MRVU": "leveraged_etf",
    "NVDL": "leveraged_etf", "AMDL": "leveraged_etf", "AVL": "leveraged_etf",
    "INTW": "leveraged_etf", "QCMU": "leveraged_etf", "TXNU": "leveraged_etf",
    "ONX": "leveraged_etf", "SNXX": "leveraged_etf", "MULL": "leveraged_etf",
    "TSMX": "leveraged_etf", "ASMU": "leveraged_etf", "LRCU": "leveraged_etf",
    "KLAG": "leveraged_etf", "AMAU": "leveraged_etf", "DLLL": "leveraged_etf",
    "LNOK": "leveraged_etf",
    # Hardware & Other
    "DELL": "hardware_other", "HPE": "hardware_other", "HOOD": "hardware_other",
    "CAT": "hardware_other", "FIX": "hardware_other", "P": "hardware_other",
    "CDE": "hardware_other", "APH": "hardware_other", "VSH": "hardware_other",
    "MRAAY": "hardware_other", "CBRS": "hardware_other",
}

SECTOR_META = {
    "chip_designer":    {"label": "Chip Designers",       "color": "#3b82f6"},
    "chip_equipment":   {"label": "Chip Equipment",       "color": "#6366f1"},
    "foundry":          {"label": "Foundries & Fab",      "color": "#8b5cf6"},
    "packaging_ems":    {"label": "Packaging / EMS",      "color": "#a855f7"},
    "memory_storage":   {"label": "Memory & Storage",     "color": "#0891b2"},
    "optical_photonics":{"label": "Optical & Photonics",  "color": "#06b6d4"},
    "ai_datacenter":    {"label": "AI & Data Center",     "color": "#f97316"},
    "networking":       {"label": "Networking & Comms",   "color": "#0ea5e9"},
    "energy_power":     {"label": "Energy & Power",       "color": "#16a34a"},
    "space_aerospace":  {"label": "Space & Aerospace",    "color": "#64748b"},
    "crypto":           {"label": "Crypto & Blockchain",  "color": "#eab308"},
    "etf_semi":         {"label": "Semiconductor ETFs",   "color": "#6b7280"},
    "etf_other":        {"label": "Space / Other ETFs",   "color": "#9ca3af"},
    "leveraged_etf":    {"label": "Leveraged ETFs (2×)",  "color": "#ef4444"},
    "hardware_other":   {"label": "Hardware & Other",     "color": "#78716c"},
}

# Full exchange display names
EXCHANGE_NAMES = {
    "NMS": "NASDAQ",  "NGM": "NASDAQ",  "NCM": "NASDAQ",
    "NYQ": "NYSE",    "ASE": "NYSE American",  "PCX": "NYSE Arca",
    "AMS": "Euronext Amsterdam",  "LSE": "London SE",
    "TSE": "Tokyo SE",  "STO": "Nasdaq Stockholm",
    "HEL": "Nasdaq Helsinki",  "OTC": "OTC Markets",
    "BATS": "CBOE/BATS",
}

# Exchange codes used by Google Finance URLs
GF_EXCHANGE = {
    "NMS": "NASDAQ",  "NGM": "NASDAQ",  "NCM": "NASDAQ",
    "NYQ": "NYSE",    "ASE": "NYSEAMERICAN",  "PCX": "NYSEARCA",
    "AMS": "AMS",     "LSE": "LON",
    "TSE": "TYO",     "STO": "STO",
    "HEL": "HEL",     "OTC": "OTCMKTS",
}

# ══════════════════════════════════════════════════════════════════════════════
# 3  STOCK LIST PARSER
# ══════════════════════════════════════════════════════════════════════════════
def parse_stock_list(filepath: str) -> list:
    tickers = []
    seen = set()
    with open(filepath, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            # Try parenthesised ticker first: 英伟达 (NVDA)
            m = re.search(r'\(([A-Z]{1,5})\)', line)
            if m:
                t = m.group(1)
            else:
                # First standalone ALL-CAPS word of 1-5 chars after a digit+dot prefix
                # Skip leading number and dot: "10.  AMD - ..."
                stripped = re.sub(r'^\d+[\.\s]+', '', line)
                m = re.search(r'\b([A-Z]{1,5})\b', stripped)
                t = m.group(1) if m else None
            if t and t not in seen:
                tickers.append(t)
                seen.add(t)
    return tickers

# ══════════════════════════════════════════════════════════════════════════════
# 4  CACHE MANAGER
# ══════════════════════════════════════════════════════════════════════════════
def load_cache(path: str) -> dict:
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except Exception:
        return {}

def save_cache(path: str, data: dict) -> None:
    tmp = path + ".tmp"
    Path(tmp).write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    os.replace(tmp, path)

def is_cache_fresh(entry: dict, max_age_hours: int) -> bool:
    ts = entry.get("fetched_at")
    if not ts:
        return False
    try:
        fetched = datetime.fromisoformat(ts).replace(tzinfo=timezone.utc)
        age_hours = (datetime.now(timezone.utc) - fetched).total_seconds() / 3600
        return age_hours < max_age_hours
    except Exception:
        return False

# ══════════════════════════════════════════════════════════════════════════════
# 5  DATA FETCHER
# ══════════════════════════════════════════════════════════════════════════════
def fetch_stock_data(ticker: str) -> dict:
    import yfinance as yf
    import pandas as pd

    result = {
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "error": False,
    }

    try:
        t = yf.Ticker(ticker)
        info = t.info or {}

        # Company metadata — use .get() with safe defaults throughout
        result["name"]     = info.get("longName") or info.get("shortName") or ticker
        result["exchange"] = info.get("exchange") or ""
        result["currency"] = info.get("currency") or "USD"
        result["country"]  = info.get("country") or ""
        result["website"]  = info.get("website") or ""
        result["about"]    = (info.get("longBusinessSummary") or "")[:400]
        result["cap_raw"]  = info.get("marketCap") or 0
        result["px"]       = info.get("currentPrice") or info.get("regularMarketPrice") or info.get("navPrice") or 0
        result["h52"]      = info.get("fiftyTwoWeekHigh") or 0
        result["l52"]      = info.get("fiftyTwoWeekLow") or 0
        result["pe"]       = info.get("trailingPE") or None
        result["fpe"]      = info.get("forwardPE") or None
        result["eps"]      = info.get("trailingEps") or None
        result["dy"]       = info.get("dividendYield") or None
        result["beta"]     = info.get("beta") or None
        result["volume"]   = info.get("volume") or info.get("regularMarketVolume") or 0
        result["avg_vol"]  = info.get("averageVolume") or 0

        # Price history (monthly resampled from daily)
        hist = t.history(period=CHART_PERIOD, auto_adjust=True)
        if hist.empty:
            hist = t.history(period="10y", auto_adjust=True)

        if not hist.empty:
            monthly = hist["Close"].resample("ME").last().dropna()
            result["hist_dates"] = [d.strftime("%Y-%m") for d in monthly.index]
            result["hist_px"]    = [round(float(p), 4) for p in monthly.values]
            result["ipo"]        = monthly.index[0].strftime("%Y-%m") if len(monthly) > 0 else ""

            # % changes from history
            px_vals = result["hist_px"]
            if len(px_vals) >= 2:
                result["chg1d"] = round((px_vals[-1] - px_vals[-2]) / px_vals[-2] * 100, 2) if px_vals[-2] else None
            else:
                result["chg1d"] = None

            if len(px_vals) >= 2:
                one_month_ago = px_vals[-2]
                result["chg1m"] = round((px_vals[-1] - one_month_ago) / one_month_ago * 100, 2) if one_month_ago else None
            else:
                result["chg1m"] = None

            if len(px_vals) >= 13:
                one_year_ago = px_vals[-13]
                result["chg1y"] = round((px_vals[-1] - one_year_ago) / one_year_ago * 100, 2) if one_year_ago else None
            else:
                result["chg1y"] = None
        else:
            result["hist_dates"] = []
            result["hist_px"]    = []
            result["ipo"]        = ""
            result["chg1d"]      = None
            result["chg1m"]      = None
            result["chg1y"]      = None

        # If we still have no current price but have history, use last hist value
        if not result["px"] and result["hist_px"]:
            result["px"] = result["hist_px"][-1]

    except Exception as e:
        result["error"] = True
        result["error_msg"] = str(e)
        for key in ["name", "exchange", "currency", "country", "website", "about",
                    "cap_raw", "px", "h52", "l52", "pe", "fpe", "eps", "dy", "beta",
                    "volume", "avg_vol", "hist_dates", "hist_px", "ipo",
                    "chg1d", "chg1m", "chg1y"]:
            result.setdefault(key, None if key not in ("hist_dates", "hist_px") else [])

    return result

# ══════════════════════════════════════════════════════════════════════════════
# 6  BATCH FETCH WITH PROGRESS
# ══════════════════════════════════════════════════════════════════════════════
def fetch_all_stocks(tickers: list, cache: dict) -> dict:
    total = len(tickers)
    for i, ticker in enumerate(tickers, 1):
        entry = cache.get(ticker)
        if entry and is_cache_fresh(entry, CACHE_MAX_AGE_HRS):
            px = entry.get("px") or 0
            print(f"[{i:3}/{total}] {ticker:<6}  cached  (${px:.2f})" if px else f"[{i:3}/{total}] {ticker:<6}  cached")
            continue

        print(f"[{i:3}/{total}] {ticker:<6}  fetching...", end="", flush=True)
        data = fetch_stock_data(ticker)
        cache[ticker] = data

        if data.get("error"):
            print(f"  ERROR: {data.get('error_msg', 'unknown')[:60]}")
        else:
            px  = data.get("px") or 0
            ipo = data.get("ipo") or ""
            print(f"  OK  (${px:.2f}, IPO: ~{ipo})")

        save_cache(CACHE_FILE, cache)
        time.sleep(RATE_LIMIT_DELAY)

    return cache

# ══════════════════════════════════════════════════════════════════════════════
# 7  DATA TRANSFORMATION
# ══════════════════════════════════════════════════════════════════════════════
def fmt_cap(n):
    if not n:
        return ""
    n = float(n)
    if n >= 1e12:
        return f"${n/1e12:.2f}T"
    if n >= 1e9:
        return f"${n/1e9:.2f}B"
    if n >= 1e6:
        return f"${n/1e6:.2f}M"
    return f"${n:,.0f}"

def build_records(tickers: list, cache: dict) -> list:
    records = []
    for ticker in tickers:
        d = cache.get(ticker, {})
        sector = SECTOR_MAP.get(ticker, "hardware_other")
        ex_code = d.get("exchange") or ""
        ex_name = EXCHANGE_NAMES.get(ex_code, ex_code)
        gf_ex   = GF_EXCHANGE.get(ex_code, "NASDAQ")
        rec = {
            "t":        ticker,
            "n":        d.get("name") or ticker,
            "s":        sector,
            "ex":       ex_code,
            "ex_name":  ex_name,
            "cur":      d.get("currency") or "USD",
            "country":  d.get("country") or "",
            "web":      d.get("website") or "",
            "about":    d.get("about") or "",
            "link_yf":   f"https://finance.yahoo.com/quote/{ticker}/",
            "link_gf":   f"https://www.google.com/finance/quote/{ticker}:{gf_ex}",
            "link_ibkr": f"https://www.interactivebrokers.com/en/trading/product-search.php#/?query={ticker}",
            "px":       round(float(d["px"]), 4) if d.get("px") else None,
            "cap_raw":  int(d["cap_raw"]) if d.get("cap_raw") else 0,
            "cap":      fmt_cap(d.get("cap_raw")),
            "h52":      round(float(d["h52"]), 4) if d.get("h52") else None,
            "l52":      round(float(d["l52"]), 4) if d.get("l52") else None,
            "pe":       round(float(d["pe"]), 2) if d.get("pe") else None,
            "fpe":      round(float(d["fpe"]), 2) if d.get("fpe") else None,
            "eps":      round(float(d["eps"]), 4) if d.get("eps") else None,
            "dy":       round(float(d["dy"]) * 100, 2) if d.get("dy") and 0 < float(d["dy"]) < 0.3 else None,
            "beta":     round(float(d["beta"]), 2) if d.get("beta") else None,
            "chg1d":    d.get("chg1d"),
            "chg1m":    d.get("chg1m"),
            "chg1y":    d.get("chg1y"),
            "ipo":      d.get("ipo") or "",
            "hist_dates": d.get("hist_dates") or [],
            "hist_px":    d.get("hist_px") or [],
            "err":      bool(d.get("error")),
        }
        records.append(rec)
    return records

def build_stats(records: list) -> dict:
    sector_counts = {}
    for r in records:
        s = r["s"]
        sector_counts[s] = sector_counts.get(s, 0) + 1
    with_data = sum(1 for r in records if not r["err"])
    return {
        "total":        len(records),
        "with_data":    with_data,
        "sectors":      sector_counts,
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
    }

# ══════════════════════════════════════════════════════════════════════════════
# 8  HTML TEMPLATE
# ══════════════════════════════════════════════════════════════════════════════
HTML_TEMPLATE = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Stock Watchlist Dashboard</title>
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;background:#0f172a;color:#e2e8f0;min-height:100vh}
a{color:#60a5fa;text-decoration:none}a:hover{text-decoration:underline}

/* Header */
.header{background:linear-gradient(135deg,#1e293b,#0f172a);border-bottom:1px solid #1e3a5f;padding:18px 24px;display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:8px}
.header h1{font-size:1.4rem;font-weight:700;color:#f1f5f9;letter-spacing:-0.3px}
.header .meta{font-size:.78rem;color:#64748b}

/* KPI strip */
.kpi-strip{display:flex;gap:12px;padding:16px 24px;flex-wrap:wrap;background:#111827;border-bottom:1px solid #1e293b}
.kpi{background:#1e293b;border-radius:10px;padding:12px 16px;min-width:110px;text-align:center}
.kpi .val{font-size:1.3rem;font-weight:700;color:#f1f5f9}
.kpi .lbl{font-size:.7rem;color:#94a3b8;text-transform:uppercase;letter-spacing:.5px;margin-top:2px}

/* Sector pills */
.sector-bar{padding:12px 24px;display:flex;flex-wrap:wrap;gap:7px;background:#0f172a;border-bottom:1px solid #1e293b}
.pill{cursor:pointer;border:1px solid transparent;border-radius:20px;padding:4px 12px;font-size:.75rem;font-weight:600;transition:all .15s;user-select:none;white-space:nowrap}
.pill:hover{filter:brightness(1.2)}
.pill.active{border-color:white!important;color:#fff!important}
.pill-all{background:#1e293b;color:#94a3b8;border-color:#334155}
.pill-all.active{background:#334155;border-color:#94a3b8;color:#e2e8f0}

/* Filter bar */
.filter-bar{position:sticky;top:0;z-index:50;background:#111827;border-bottom:1px solid #1e293b;padding:10px 24px;display:flex;flex-wrap:wrap;gap:8px;align-items:center}
.search-wrap{position:relative;flex:1;min-width:160px}
.search-wrap input{width:100%;background:#1e293b;border:1px solid #334155;color:#e2e8f0;border-radius:8px;padding:7px 10px 7px 32px;font-size:.85rem;outline:none}
.search-wrap input:focus{border-color:#3b82f6}
.search-icon{position:absolute;left:9px;top:50%;transform:translateY(-50%);color:#64748b;font-size:.9rem}
select{background:#1e293b;border:1px solid #334155;color:#e2e8f0;border-radius:8px;padding:7px 10px;font-size:.82rem;cursor:pointer;outline:none}
select:focus{border-color:#3b82f6}
.btn-group{display:flex;gap:2px}
.btn{background:#1e293b;border:1px solid #334155;color:#94a3b8;border-radius:7px;padding:6px 11px;font-size:.78rem;cursor:pointer;transition:all .12s;white-space:nowrap}
.btn:hover{background:#334155;color:#e2e8f0}
.btn.active{background:#3b82f6;border-color:#3b82f6;color:#fff}
.result-info{padding:8px 24px;font-size:.78rem;color:#64748b;background:#0f172a}

/* Card grid */
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(220px,1fr));gap:14px;padding:16px 24px 40px}

/* Stock card */
.card{background:#1e293b;border:1px solid #334155;border-radius:12px;padding:14px;cursor:pointer;transition:all .15s;position:relative;overflow:hidden}
.card:hover{border-color:#3b82f6;transform:translateY(-1px);box-shadow:0 4px 20px rgba(59,130,246,.15)}
.card-top{display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:6px}
.ticker{font-size:1.1rem;font-weight:800;color:#f1f5f9;letter-spacing:-.3px}
.sector-badge{font-size:.62rem;font-weight:600;border-radius:4px;padding:2px 6px;white-space:nowrap;max-width:100px;overflow:hidden;text-overflow:ellipsis}
.company{font-size:.75rem;color:#94a3b8;margin-bottom:8px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.price-row{display:flex;align-items:baseline;gap:8px;margin-bottom:4px}
.price{font-size:1.15rem;font-weight:700;color:#f1f5f9}
.chg{font-size:.8rem;font-weight:600}
.chg.pos{color:#22c55e}.chg.neg{color:#ef4444}.chg.neu{color:#94a3b8}
.sparkline-wrap{margin:6px 0;height:40px;width:100%}
canvas.sparkline{width:100%;height:40px;display:block}
.card-metrics{display:grid;grid-template-columns:1fr 1fr;gap:3px 8px;margin-top:6px}
.metric{font-size:.71rem;color:#94a3b8}
.metric span{color:#cbd5e1;font-weight:500}
.metric span.pos{color:#22c55e}.metric span.neg{color:#ef4444}
.detail-btn{display:block;width:100%;margin-top:10px;background:#0f172a;border:1px solid #334155;color:#94a3b8;border-radius:7px;padding:5px;font-size:.75rem;cursor:pointer;text-align:center;transition:all .12s}
.detail-btn:hover{border-color:#3b82f6;color:#60a5fa}
.no-data-overlay{position:absolute;inset:0;background:rgba(15,23,42,.6);display:flex;align-items:center;justify-content:center;border-radius:12px;font-size:.75rem;color:#64748b}
.ex-ipo{font-size:.67rem;color:#475569;margin-bottom:6px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
/* External links */
.ext-links{display:flex;gap:7px;flex-wrap:wrap;padding:4px 22px 14px}
.ext-link{display:inline-flex;align-items:center;gap:4px;padding:5px 11px;border-radius:7px;font-size:.76rem;font-weight:600;text-decoration:none;transition:all .15s;border:1px solid}
.ext-link-yf  {background:#4b00821a;border-color:#7c3aed44;color:#a78bfa}
.ext-link-yf:hover  {background:#4b008244;border-color:#7c3aed;color:#c4b5fd}
.ext-link-gf  {background:#0622101a;border-color:#16a34a44;color:#4ade80}
.ext-link-gf:hover  {background:#06221044;border-color:#16a34a;color:#86efac}
.ext-link-ibkr{background:#051e2e1a;border-color:#0ea5e944;color:#38bdf8}
.ext-link-ibkr:hover{background:#051e2e44;border-color:#0ea5e9;color:#7dd3fc}

/* Modal */
.modal-bg{display:none;position:fixed;inset:0;background:rgba(0,0,0,.7);z-index:1000;align-items:center;justify-content:center;padding:16px}
.modal-bg.open{display:flex}
.modal{background:#1e293b;border:1px solid #334155;border-radius:16px;width:100%;max-width:820px;max-height:92vh;overflow-y:auto}
.modal-header{display:flex;justify-content:space-between;align-items:flex-start;padding:20px 22px 0}
.modal-title{font-size:1.3rem;font-weight:800;color:#f1f5f9}
.modal-sub{font-size:.8rem;color:#94a3b8;margin-top:2px}
.close-btn{background:none;border:none;color:#94a3b8;font-size:1.4rem;cursor:pointer;padding:0 4px;line-height:1}
.close-btn:hover{color:#e2e8f0}
.chart-wrap{padding:16px 22px 0}
canvas#mainChart{width:100%;height:260px;display:block;border-radius:8px;background:#0f172a}
.modal-metrics{display:grid;grid-template-columns:repeat(auto-fill,minmax(150px,1fr));gap:10px;padding:16px 22px}
.mcard{background:#0f172a;border-radius:8px;padding:10px 14px}
.mcard .ml{font-size:.68rem;color:#64748b;text-transform:uppercase;letter-spacing:.5px}
.mcard .mv{font-size:1rem;font-weight:700;color:#f1f5f9;margin-top:2px}
.mcard .mv.pos{color:#22c55e}.mcard .mv.neg{color:#ef4444}
.about-section{padding:0 22px 20px}
.about-section h3{font-size:.78rem;color:#64748b;text-transform:uppercase;letter-spacing:.5px;margin-bottom:6px}
.about-section p{font-size:.82rem;color:#94a3b8;line-height:1.55}
.about-section .website{margin-top:8px;font-size:.8rem}

/* Empty state */
.empty{text-align:center;padding:60px;color:#475569}
.empty svg{width:48px;height:48px;margin:0 auto 12px;display:block;opacity:.4}

/* Scrollbar */
::-webkit-scrollbar{width:6px;height:6px}
::-webkit-scrollbar-track{background:#0f172a}
::-webkit-scrollbar-thumb{background:#334155;border-radius:3px}

/* Responsive */
@media(max-width:600px){
  .grid{grid-template-columns:repeat(auto-fill,minmax(160px,1fr))}
  .kpi-strip{gap:8px}.kpi{min-width:80px;padding:8px 10px}.kpi .val{font-size:1.1rem}
}
</style>
</head>
<body>

<div class="header">
  <h1>📈 Stock Watchlist Dashboard</h1>
  <div class="meta" id="genDate"></div>
</div>

<div class="kpi-strip" id="kpiStrip"></div>
<div class="sector-bar" id="sectorBar"></div>

<div class="filter-bar">
  <div class="search-wrap">
    <span class="search-icon">🔍</span>
    <input type="text" id="search" placeholder="Search ticker or company…" oninput="onFilter()">
  </div>
  <select id="selExchange" onchange="onFilter()"><option value="">All Exchanges</option></select>
  <select id="selCountry" onchange="onFilter()"><option value="">All Countries</option></select>
  <select id="selSort" onchange="onFilter()">
    <option value="ticker">Ticker</option>
    <option value="name">Name</option>
    <option value="px">Price</option>
    <option value="cap">Market Cap</option>
    <option value="pe">P/E</option>
    <option value="fpe">Fwd P/E</option>
    <option value="chg1d">1D %</option>
    <option value="chg1y">1Y %</option>
    <option value="beta">Beta</option>
  </select>
  <div class="btn-group">
    <button class="btn active" id="sortDir" onclick="toggleSortDir()">▲</button>
  </div>
  <div class="btn-group" id="typeGroup">
    <button class="btn active" onclick="setType('all',this)">All</button>
    <button class="btn" onclick="setType('stock',this)">Stocks</button>
    <button class="btn" onclick="setType('etf',this)">ETFs</button>
    <button class="btn" onclick="setType('leveraged',this)">2× ETF</button>
  </div>
  <div class="btn-group" id="specialGroup">
    <button class="btn active" onclick="setSpecial('all',this)">All</button>
    <button class="btn" onclick="setSpecial('gainers',this)">Gainers</button>
    <button class="btn" onclick="setSpecial('losers',this)">Losers</button>
    <button class="btn" onclick="setSpecial('nodata',this)">No Data</button>
  </div>
  <button class="btn" onclick="exportCSV()" style="margin-left:auto">⬇ Export CSV</button>
</div>

<div class="result-info" id="resultInfo"></div>
<div class="grid" id="grid"></div>

<!-- Detail Modal -->
<div class="modal-bg" id="modalBg" onclick="closeModal(event)">
  <div class="modal" id="modal">
    <div class="modal-header">
      <div>
        <div class="modal-title" id="mTitle"></div>
        <div class="modal-sub" id="mSub"></div>
      </div>
      <button class="close-btn" onclick="closeModal()">✕</button>
    </div>
    <div class="chart-wrap">
      <canvas id="mainChart"></canvas>
    </div>
    <div class="modal-metrics" id="mMetrics"></div>
    <div class="ext-links" id="mLinks"></div>
    <div class="about-section" id="mAbout"></div>
  </div>
</div>

<script>
// ─── Data ────────────────────────────────────────────────────────────────────
const DATA        = __DATA__;
const STATS       = __STATS__;
const SECTOR_META = __SECTOR_META__;

// ─── State ───────────────────────────────────────────────────────────────────
const state = {
  search:  "",
  sector:  "",
  exchange:"",
  country: "",
  sort:    "ticker",
  sortDir: 1,      // 1=asc, -1=desc
  type:    "all",  // all|stock|etf|leveraged
  special: "all",  // all|gainers|losers|nodata
};

// ─── Init ─────────────────────────────────────────────────────────────────────
document.getElementById("genDate").textContent = "Generated: " + STATS.generated_at;

// KPI strip
(function buildKPIs(){
  const withData  = STATS.with_data;
  const total     = STATS.total;
  const sectors   = Object.keys(STATS.sectors).length;
  const withPrice = DATA.filter(d=>d.px).length;
  const caps      = DATA.filter(d=>d.cap_raw>0).map(d=>d.cap_raw);
  const totalCap  = caps.reduce((a,b)=>a+b,0);
  const kpis = [
    {val: total,    lbl: "Stocks"},
    {val: withData, lbl: "With Data"},
    {val: sectors,  lbl: "Sectors"},
    {val: fmtCap(totalCap), lbl: "Total MCap"},
  ];
  const el = document.getElementById("kpiStrip");
  el.innerHTML = kpis.map(k=>`<div class="kpi"><div class="val">${k.val}</div><div class="lbl">${k.lbl}</div></div>`).join("");
})();

// Sector pills
(function buildPills(){
  const bar = document.getElementById("sectorBar");
  const counts = STATS.sectors;
  let html = `<span class="pill pill-all active" onclick="setSector('',this)">All (${STATS.total})</span>`;
  for(const [key, meta] of Object.entries(SECTOR_META)){
    const cnt = counts[key] || 0;
    if(!cnt) continue;
    const bg    = meta.color + "22";
    const color = meta.color;
    html += `<span class="pill" style="background:${bg};color:${color};border-color:${color}44"
              onclick="setSector('${key}',this)">${meta.label} (${cnt})</span>`;
  }
  bar.innerHTML = html;
})();

// Populate exchange dropdown
(function buildExchanges(){
  const seen = new Map();
  DATA.forEach(d=>{ if(d.ex && !seen.has(d.ex)) seen.set(d.ex, d.ex_name||d.ex); });
  const sel = document.getElementById("selExchange");
  [...seen.entries()].sort((a,b)=>a[1].localeCompare(b[1])).forEach(([code,name])=>{
    const opt = document.createElement("option");
    opt.value = code; opt.textContent = name;
    sel.appendChild(opt);
  });
})();

// Populate country dropdown
(function buildCountries(){
  const countries = [...new Set(DATA.map(d=>d.country).filter(Boolean))].sort();
  const sel = document.getElementById("selCountry");
  countries.forEach(c=>{
    const opt = document.createElement("option");
    opt.value = c; opt.textContent = c;
    sel.appendChild(opt);
  });
})();

// ─── Filters ─────────────────────────────────────────────────────────────────
function applyFilters(){
  let res = [...DATA];

  if(state.search){
    const q = state.search.toLowerCase();
    res = res.filter(d=>
      d.t.toLowerCase().includes(q) ||
      d.n.toLowerCase().includes(q) ||
      (d.about||"").toLowerCase().includes(q)
    );
  }
  if(state.sector)   res = res.filter(d=>d.s === state.sector);
  if(state.exchange) res = res.filter(d=>d.ex === state.exchange);
  if(state.country)  res = res.filter(d=>d.country === state.country);

  if(state.type === "leveraged") res = res.filter(d=>d.s === "leveraged_etf");
  else if(state.type === "etf")  res = res.filter(d=>["etf_semi","etf_other","leveraged_etf"].includes(d.s));
  else if(state.type === "stock")res = res.filter(d=>!["etf_semi","etf_other","leveraged_etf"].includes(d.s));

  if(state.special === "gainers") res = res.filter(d=>d.chg1d !== null && d.chg1d > 0);
  else if(state.special === "losers") res = res.filter(d=>d.chg1d !== null && d.chg1d < 0);
  else if(state.special === "nodata") res = res.filter(d=>d.err);

  // Sort
  res.sort((a,b)=>{
    let va, vb;
    if(state.sort==="ticker")      { va=a.t;        vb=b.t; }
    else if(state.sort==="name")   { va=a.n;        vb=b.n; }
    else if(state.sort==="px")     { va=a.px||0;    vb=b.px||0; }
    else if(state.sort==="cap")    { va=a.cap_raw||0;vb=b.cap_raw||0; }
    else if(state.sort==="pe")     { va=a.pe||0;    vb=b.pe||0; }
    else if(state.sort==="fpe")    { va=a.fpe||0;   vb=b.fpe||0; }
    else if(state.sort==="chg1d")  { va=a.chg1d??-Infinity;vb=b.chg1d??-Infinity; }
    else if(state.sort==="chg1y")  { va=a.chg1y??-Infinity;vb=b.chg1y??-Infinity; }
    else if(state.sort==="beta")   { va=a.beta||0;  vb=b.beta||0; }
    else { va=a.t; vb=b.t; }
    if(va < vb) return -1 * state.sortDir;
    if(va > vb) return  1 * state.sortDir;
    return 0;
  });
  return res;
}

function onFilter(){
  state.search   = document.getElementById("search").value;
  state.exchange = document.getElementById("selExchange").value;
  state.country  = document.getElementById("selCountry").value;
  state.sort     = document.getElementById("selSort").value;
  render();
}

function setSector(key, el){
  state.sector = key;
  document.querySelectorAll(".pill").forEach(p=>p.classList.remove("active"));
  el.classList.add("active");
  render();
}

function setType(val, el){
  state.type = val;
  document.querySelectorAll("#typeGroup .btn").forEach(b=>b.classList.remove("active"));
  el.classList.add("active");
  render();
}

function setSpecial(val, el){
  state.special = val;
  document.querySelectorAll("#specialGroup .btn").forEach(b=>b.classList.remove("active"));
  el.classList.add("active");
  render();
}

function toggleSortDir(){
  state.sortDir *= -1;
  document.getElementById("sortDir").textContent = state.sortDir===1 ? "▲" : "▼";
  render();
}

// ─── Render Cards ─────────────────────────────────────────────────────────────
function render(){
  const filtered = applyFilters();
  document.getElementById("resultInfo").textContent =
    `Showing ${filtered.length} of ${DATA.length} stocks`;

  const grid = document.getElementById("grid");

  if(!filtered.length){
    grid.innerHTML = `<div class="empty" style="grid-column:1/-1">
      <div style="font-size:2rem;margin-bottom:8px">🔍</div>
      <div style="font-size:.9rem">No stocks match your filters</div>
    </div>`;
    return;
  }

  grid.innerHTML = filtered.map(d=>{
    const meta  = SECTOR_META[d.s] || {label:d.s, color:"#6b7280"};
    const bgCol = meta.color + "22";
    const fgCol = meta.color;
    const px    = d.px !== null ? "$"+fmtNum(d.px) : "—";
    const chgHtml = fmtChgBadge(d.chg1d);
    const capStr  = d.cap || "—";
    const peStr   = d.pe  ? d.pe.toFixed(1) : "—";
    const fpeStr  = d.fpe ? d.fpe.toFixed(1) : "—";
    const betaStr = d.beta ? d.beta.toFixed(2) : "—";
    const exIpo   = [d.ex_name||d.ex, d.country, d.ipo ? "IPO "+d.ipo : ""].filter(Boolean).join(" · ");
    const sparkId = "spark-"+d.t;

    return `<div class="card" onclick="openDetail('${d.t}')">
      <div class="card-top">
        <div class="ticker">${d.t}</div>
        <span class="sector-badge" style="background:${bgCol};color:${fgCol}">${meta.label}</span>
      </div>
      <div class="company" title="${d.n}">${d.n}</div>
      ${exIpo ? `<div class="ex-ipo">${exIpo}</div>` : ""}
      <div class="price-row">
        <span class="price">${px}</span>
        ${chgHtml}
      </div>
      <div class="sparkline-wrap">
        <canvas class="sparkline" id="${sparkId}"></canvas>
      </div>
      <div class="card-metrics">
        <div class="metric">MCap <span>${capStr}</span></div>
        <div class="metric">P/E <span>${peStr}</span></div>
        <div class="metric">Fwd P/E <span>${fpeStr}</span></div>
        <div class="metric">Beta <span>${betaStr}</span></div>
        <div class="metric">1Y % <span class="${d.chg1y>0?'pos':d.chg1y<0?'neg':''}">${d.chg1y!==null?(d.chg1y>0?"+":"")+d.chg1y.toFixed(1)+"%":"—"}</span></div>
      </div>
      ${d.err ? '<div class="no-data-overlay">Data unavailable</div>' : ""}
    </div>`;
  }).join("");

  // Draw sparklines after DOM update
  requestAnimationFrame(()=>{
    filtered.forEach(d=>{
      const el = document.getElementById("spark-"+d.t);
      if(el && d.hist_px && d.hist_px.length>1){
        drawSparkline(el, d.hist_px, SECTOR_META[d.s]?.color||"#3b82f6");
      }
    });
  });
}

// ─── Charts (Canvas 2D) ───────────────────────────────────────────────────────
function drawSparkline(canvas, prices, color){
  const dpr = window.devicePixelRatio||1;
  canvas.width  = canvas.offsetWidth  * dpr;
  canvas.height = canvas.offsetHeight * dpr;
  const ctx = canvas.getContext("2d");
  ctx.scale(dpr, dpr);
  const W = canvas.offsetWidth, H = canvas.offsetHeight;
  const mn = Math.min(...prices), mx = Math.max(...prices);
  const range = mx - mn || 1;
  const toY = v => H - ((v-mn)/range)*(H-4) - 2;
  const toX = i => (i/(prices.length-1)) * W;

  ctx.beginPath();
  prices.forEach((p,i)=> i===0 ? ctx.moveTo(toX(i),toY(p)) : ctx.lineTo(toX(i),toY(p)));
  // fill
  ctx.lineTo(W, H); ctx.lineTo(0, H); ctx.closePath();
  const grad = ctx.createLinearGradient(0,0,0,H);
  grad.addColorStop(0, color+"66");
  grad.addColorStop(1, color+"00");
  ctx.fillStyle = grad; ctx.fill();
  // line
  ctx.beginPath();
  prices.forEach((p,i)=> i===0 ? ctx.moveTo(toX(i),toY(p)) : ctx.lineTo(toX(i),toY(p)));
  ctx.strokeStyle = color; ctx.lineWidth = 1.5; ctx.stroke();
}

function drawPriceChart(canvas, dates, prices, color){
  const dpr = window.devicePixelRatio||1;
  canvas.width  = canvas.offsetWidth  * dpr;
  canvas.height = canvas.offsetHeight * dpr;
  const ctx = canvas.getContext("2d");
  ctx.scale(dpr, dpr);
  const W = canvas.offsetWidth, H = canvas.offsetHeight;
  const PAD = {top:20, right:20, bottom:36, left:64};
  const cW = W - PAD.left - PAD.right;
  const cH = H - PAD.top  - PAD.bottom;

  const mn = Math.min(...prices), mx = Math.max(...prices);
  const range = mx - mn || 1;
  const toY = v => PAD.top + cH - ((v-mn)/range)*cH;
  const toX = i => PAD.left + (i/(prices.length-1||1)) * cW;

  // Background
  ctx.fillStyle = "#0f172a"; ctx.fillRect(0,0,W,H);

  // Horizontal gridlines
  ctx.strokeStyle = "#1e293b"; ctx.lineWidth = 1;
  for(let g=0;g<=4;g++){
    const y = PAD.top + (g/4)*cH;
    ctx.beginPath(); ctx.moveTo(PAD.left, y); ctx.lineTo(PAD.left+cW, y); ctx.stroke();
    const v = mx - (g/4)*range;
    ctx.fillStyle = "#64748b"; ctx.font = "10px sans-serif"; ctx.textAlign = "right";
    ctx.fillText(fmtPrice(v), PAD.left-6, y+3);
  }

  // X-axis year labels
  if(dates && dates.length > 1){
    const years = dates.map(d=>parseInt(d.slice(0,4)));
    const firstY = years[0], lastY = years[years.length-1];
    const span = lastY - firstY;
    const step = span > 20 ? 5 : span > 10 ? 2 : 1;
    ctx.fillStyle = "#64748b"; ctx.font = "10px sans-serif"; ctx.textAlign = "center";
    for(let y=Math.ceil(firstY/step)*step; y<=lastY; y+=step){
      const idx = years.findIndex(yr=>yr>=y);
      if(idx>=0){
        const x = toX(idx);
        ctx.beginPath(); ctx.strokeStyle = "#1e3a5f"; ctx.lineWidth = 1;
        ctx.moveTo(x, PAD.top); ctx.lineTo(x, PAD.top+cH); ctx.stroke();
        ctx.fillText(y, x, H-8);
      }
    }
  }

  // Filled area
  ctx.beginPath();
  prices.forEach((p,i)=> i===0 ? ctx.moveTo(toX(i),toY(p)) : ctx.lineTo(toX(i),toY(p)));
  ctx.lineTo(toX(prices.length-1), PAD.top+cH);
  ctx.lineTo(PAD.left, PAD.top+cH); ctx.closePath();
  const grad = ctx.createLinearGradient(0,PAD.top,0,PAD.top+cH);
  grad.addColorStop(0, color+"55");
  grad.addColorStop(1, color+"05");
  ctx.fillStyle = grad; ctx.fill();

  // Price line
  ctx.beginPath();
  prices.forEach((p,i)=> i===0 ? ctx.moveTo(toX(i),toY(p)) : ctx.lineTo(toX(i),toY(p)));
  ctx.strokeStyle = color; ctx.lineWidth = 2; ctx.stroke();

  // Current price dot
  const lx = toX(prices.length-1), ly = toY(prices[prices.length-1]);
  ctx.beginPath(); ctx.arc(lx, ly, 4, 0, 2*Math.PI);
  ctx.fillStyle = color; ctx.fill();

  // IPO annotation
  if(dates && dates.length){
    ctx.fillStyle = "#64748b66"; ctx.font = "9px sans-serif"; ctx.textAlign = "left";
    ctx.fillText("IPO ~"+dates[0], PAD.left+4, PAD.top+12);
  }
  // Data source watermark
  ctx.fillStyle = "#334155"; ctx.font = "9px sans-serif"; ctx.textAlign = "right";
  ctx.fillText("Source: Yahoo Finance (via yfinance)", W - PAD.right, H - 4);
}

// ─── Detail Modal ─────────────────────────────────────────────────────────────
function openDetail(ticker){
  const d = DATA.find(x=>x.t===ticker);
  if(!d) return;
  const meta = SECTOR_META[d.s] || {label:d.s, color:"#3b82f6"};

  document.getElementById("mTitle").textContent = `${d.t}  —  ${d.n}`;
  document.getElementById("mSub").textContent   =
    [d.ex_name||d.ex, d.cur, d.country, meta.label].filter(Boolean).join("  ·  ");

  // Metrics
  const metrics = [
    {l:"Price",    v: d.px!==null ? "$"+fmtNum(d.px) : "—", cls:""},
    {l:"52W High", v: d.h52 ? "$"+fmtNum(d.h52) : "—", cls:""},
    {l:"52W Low",  v: d.l52 ? "$"+fmtNum(d.l52) : "—", cls:""},
    {l:"Mkt Cap",  v: d.cap||"—", cls:""},
    {l:"Exchange", v: d.ex_name||(d.ex||"—"), cls:""},
    {l:"IPO Date", v: d.ipo ? d.ipo+" (est.)" : "—", cls:""},
    {l:"P/E",      v: d.pe  ? d.pe.toFixed(1)  : "—", cls:""},
    {l:"Fwd P/E",  v: d.fpe ? d.fpe.toFixed(1) : "—", cls:""},
    {l:"EPS",      v: d.eps ? "$"+d.eps.toFixed(2) : "—", cls:""},
    {l:"Div Yield",v: d.dy  ? d.dy.toFixed(2)+"%" : "—", cls:""},
    {l:"Beta",     v: d.beta ? d.beta.toFixed(2) : "—", cls:""},
    {l:"1D %",     v: d.chg1d!==null ? (d.chg1d>0?"+":"")+d.chg1d.toFixed(2)+"%" : "—",
                   cls: d.chg1d>0?"pos":d.chg1d<0?"neg":""},
    {l:"1M %",     v: d.chg1m!==null ? (d.chg1m>0?"+":"")+d.chg1m.toFixed(2)+"%" : "—",
                   cls: d.chg1m>0?"pos":d.chg1m<0?"neg":""},
    {l:"1Y %",     v: d.chg1y!==null ? (d.chg1y>0?"+":"")+d.chg1y.toFixed(2)+"%" : "—",
                   cls: d.chg1y>0?"pos":d.chg1y<0?"neg":""},
  ];
  document.getElementById("mMetrics").innerHTML = metrics.map(m=>
    `<div class="mcard"><div class="ml">${m.l}</div><div class="mv ${m.cls}">${m.v}</div></div>`
  ).join("");

  // External links
  document.getElementById("mLinks").innerHTML = `
    <a class="ext-link ext-link-yf"   href="${d.link_yf}"   target="_blank" rel="noopener">📊 Yahoo Finance</a>
    <a class="ext-link ext-link-gf"   href="${d.link_gf}"   target="_blank" rel="noopener">🔍 Google Finance</a>
    <a class="ext-link ext-link-ibkr" href="${d.link_ibkr}" target="_blank" rel="noopener">💹 IBKR</a>`;

  // About
  const aboutEl = document.getElementById("mAbout");
  aboutEl.innerHTML = "";
  if(d.about || d.web){
    const h = document.createElement("h3"); h.textContent = "About";
    const p = document.createElement("p");
    p.textContent = d.err ? "Data unavailable for this ticker." : (d.about || "No description available.");
    aboutEl.appendChild(h); aboutEl.appendChild(p);
    if(d.web){
      const wEl = document.createElement("div"); wEl.className = "website";
      wEl.innerHTML = `Website: <a href="${d.web}" target="_blank" rel="noopener">${d.web.replace(/^https?:\/\//,"")}</a>`;
      aboutEl.appendChild(wEl);
    }
  }

  document.getElementById("modalBg").classList.add("open");

  // Draw chart after modal is visible
  requestAnimationFrame(()=>{
    const canvas = document.getElementById("mainChart");
    if(d.hist_px && d.hist_px.length>1){
      drawPriceChart(canvas, d.hist_dates, d.hist_px, meta.color);
    } else {
      const ctx = canvas.getContext("2d");
      canvas.width = canvas.offsetWidth; canvas.height = canvas.offsetHeight;
      ctx.fillStyle = "#0f172a"; ctx.fillRect(0,0,canvas.width,canvas.height);
      ctx.fillStyle = "#475569"; ctx.font = "14px sans-serif"; ctx.textAlign = "center";
      ctx.fillText(d.err ? "Data unavailable" : "No price history available",
                   canvas.width/2, canvas.height/2);
    }
  });
}

function closeModal(e){
  if(e && e.target !== document.getElementById("modalBg")) return;
  document.getElementById("modalBg").classList.remove("open");
}

// ─── Export CSV ───────────────────────────────────────────────────────────────
function exportCSV(){
  const filtered = applyFilters();
  const hdr = ["Ticker","Name","Sector","Exchange","ExchangeName","Currency","Price","MktCap","PE","FwdPE","EPS","DivYield","Beta","1D%","1M%","1Y%","IPO","Country","Website","YahooFinance","GoogleFinance","IBKR"];
  const rows = filtered.map(d=>[
    d.t, d.n, (SECTOR_META[d.s]||{}).label||d.s, d.ex, d.ex_name||d.ex||'', d.cur,
    d.px??'', d.cap_raw||'', d.pe??'', d.fpe??'', d.eps??'', d.dy??'', d.beta??'',
    d.chg1d??'', d.chg1m??'', d.chg1y??'', d.ipo||'', d.country||'', d.web||'',
    d.link_yf||'', d.link_gf||'', d.link_ibkr||''
  ].map(v=>'"'+String(v).replace(/"/g,'""')+'"'));
  const csv = [hdr.join(","), ...rows.map(r=>r.join(","))].join("\n");
  const a = document.createElement("a");
  a.href = "data:text/csv;charset=utf-8,"+encodeURIComponent(csv);
  a.download = "stocks_"+new Date().toISOString().slice(0,10)+".csv";
  a.click();
}

// ─── Helpers ──────────────────────────────────────────────────────────────────
function fmtNum(n){
  if(n===null||n===undefined) return "—";
  if(n >= 1000) return n.toLocaleString("en-US",{minimumFractionDigits:2,maximumFractionDigits:2});
  if(n >= 10)   return n.toFixed(2);
  if(n >= 1)    return n.toFixed(3);
  return n.toFixed(4);
}
function fmtPrice(n){
  if(n>=1000) return "$"+(n/1000).toFixed(1)+"k";
  if(n>=1)    return "$"+n.toFixed(2);
  return "$"+n.toFixed(4);
}
function fmtCap(n){
  if(!n) return "—";
  if(n>=1e12) return "$"+(n/1e12).toFixed(2)+"T";
  if(n>=1e9)  return "$"+(n/1e9).toFixed(2)+"B";
  if(n>=1e6)  return "$"+(n/1e6).toFixed(2)+"M";
  return "$"+n;
}
function fmtChgBadge(v){
  if(v===null||v===undefined) return '<span class="chg neu">—</span>';
  const cls = v>0?"pos":v<0?"neg":"neu";
  const sign = v>0?"+":"";
  return `<span class="chg ${cls}">${sign}${v.toFixed(2)}%</span>`;
}

// ─── Boot ─────────────────────────────────────────────────────────────────────
render();
</script>
</body>
</html>
"""

# ══════════════════════════════════════════════════════════════════════════════
# 9  MAIN
# ══════════════════════════════════════════════════════════════════════════════
def main():
    try:
        import yfinance  # noqa: F401
        import pandas    # noqa: F401
    except ImportError as e:
        sys.exit(f"Missing dependency: {e}\nRun: pip install yfinance pandas")

    print("=== Stock Watchlist Dashboard Generator ===\n")

    # Parse stock list
    if not Path(STOCK_LIST_FILE).exists():
        sys.exit(f"Error: {STOCK_LIST_FILE!r} not found.")
    tickers = parse_stock_list(STOCK_LIST_FILE)
    print(f"Found {len(tickers)} tickers in {STOCK_LIST_FILE}\n")

    # Load cache
    cache = load_cache(CACHE_FILE)
    fresh = sum(1 for t in tickers if t in cache and is_cache_fresh(cache[t], CACHE_MAX_AGE_HRS))
    stale = len(tickers) - fresh
    print(f"Cache: {fresh} fresh, {stale} to fetch\n")

    # Fetch
    cache = fetch_all_stocks(tickers, cache)

    # Build records
    records = build_records(tickers, cache)
    stats   = build_stats(records)

    # Inject into HTML
    html = HTML_TEMPLATE
    html = html.replace("__DATA__",        json.dumps(records, ensure_ascii=False))
    html = html.replace("__STATS__",       json.dumps(stats,   ensure_ascii=False))
    html = html.replace("__SECTOR_META__", json.dumps(SECTOR_META, ensure_ascii=False))

    Path(OUTPUT_FILE).write_text(html, encoding="utf-8")

    print(f"\nDone! Dashboard written to: {OUTPUT_FILE}")
    print(f"  {stats['with_data']}/{stats['total']} stocks with data")
    print(f"  Open {OUTPUT_FILE} in your browser\n")

if __name__ == "__main__":
    main()
