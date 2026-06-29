#!/usr/bin/env python3
"""
generate_interactive_charts.py — Interactive ECharts decay comparison.

Embeds raw price data as JSON in the HTML; the browser does all slicing,
normalisation, and rendering via ECharts.  No server required.

Usage:
  .venv/bin/python3 generate_interactive_charts.py          # all ETFs
  .venv/bin/python3 generate_interactive_charts.py MULL     # one ETF (verify)
Output: index.html
"""
import json
import sys
import warnings
from pathlib import Path

import pandas as pd
import yfinance as yf

warnings.filterwarnings("ignore")

# ── Config ────────────────────────────────────────────────────────────────────
# Each entry:
#   etf2x           — real 2× ETF ticker (key of the map)
#   underlying      — 1× proxy (value)
#   etf3x           — real 3× ETF ticker (None for single-stock)
#   leverage_sim    — leverage multiple for the simulation chart
#   fee2x / fee3x   — annual expense ratio

ETF_CONFIG = {
    # ── Tier-1: original 22 ──────────────────────────────────────────────────
    "GGLL": {"und": "GOOG", "etf3x": None, "lev": 2, "fee2x": 0.0095, "fee3x": None},
    "ARMG": {"und": "ARM",  "etf3x": None, "lev": 2, "fee2x": 0.0115, "fee3x": None},
    "MRVU": {"und": "MRVL", "etf3x": None, "lev": 2, "fee2x": 0.0095, "fee3x": None},
    "NVDL": {"und": "NVDA", "etf3x": None, "lev": 2, "fee2x": 0.0115, "fee3x": None},
    "AMDL": {"und": "AMD",  "etf3x": None, "lev": 2, "fee2x": 0.0115, "fee3x": None},
    "AVL":  {"und": "AVGO", "etf3x": None, "lev": 2, "fee2x": 0.0095, "fee3x": None},
    "INTW": {"und": "INTC", "etf3x": None, "lev": 2, "fee2x": 0.0115, "fee3x": None},
    "QCMU": {"und": "QCOM", "etf3x": None, "lev": 2, "fee2x": 0.0095, "fee3x": None},
    "TXNU": {"und": "TXN",  "etf3x": None, "lev": 2, "fee2x": 0.0095, "fee3x": None},
    "ONX":  {"und": "ON",   "etf3x": None, "lev": 2, "fee2x": 0.0105, "fee3x": None},
    "SNXX": {"und": "SNDK", "etf3x": None, "lev": 2, "fee2x": 0.0105, "fee3x": None},
    "MULL": {"und": "MU",   "etf3x": None, "lev": 2, "fee2x": 0.0115, "fee3x": None},
    "TSMX": {"und": "TSM",  "etf3x": None, "lev": 2, "fee2x": 0.0095, "fee3x": None},
    "ASMU": {"und": "ASML", "etf3x": None, "lev": 2, "fee2x": 0.0095, "fee3x": None},
    "LRCU": {"und": "LRCX", "etf3x": None, "lev": 2, "fee2x": 0.0095, "fee3x": None},
    "KLAG": {"und": "KLAC", "etf3x": None, "lev": 2, "fee2x": 0.0115, "fee3x": None},
    "AMAU": {"und": "AMAT", "etf3x": None, "lev": 2, "fee2x": 0.0115, "fee3x": None},
    "DLLL": {"und": "DELL", "etf3x": None, "lev": 2, "fee2x": 0.0115, "fee3x": None},
    "LNOK": {"und": "NOK",  "etf3x": None, "lev": 2, "fee2x": 0.0090, "fee3x": None},
    # Index ETFs (2x + 3x available)
    "QLD":  {"und": "QQQ",  "etf3x": "TQQQ", "lev": 2, "fee2x": 0.0095, "fee3x": 0.0084},
    "SSO":  {"und": "SPY",  "etf3x": "UPRO", "lev": 2, "fee2x": 0.0089, "fee3x": 0.0091},
    "DDM":  {"und": "DIA",  "etf3x": "UDOW", "lev": 2, "fee2x": 0.0095, "fee3x": 0.0095},
    # ── Tier-2: 21 new additions ─────────────────────────────────────────────
    "TSLL": {"und": "TSLA", "etf3x": None, "lev": 2, "fee2x": 0.0106, "fee3x": None},
    "CRCG": {"und": "CRCL", "etf3x": None, "lev": 2, "fee2x": 0.0075, "fee3x": None},
    "SPAL": {"und": "SPCX", "etf3x": None, "lev": 2, "fee2x": 0.0150, "fee3x": None},
    "MSTU": {"und": "MSTR", "etf3x": None, "lev": 2, "fee2x": 0.0129, "fee3x": None},
    "CONL": {"und": "COIN", "etf3x": None, "lev": 2, "fee2x": 0.0115, "fee3x": None},
    "HOOX": {"und": "HOOD", "etf3x": None, "lev": 2, "fee2x": 0.0130, "fee3x": None},
    "NBIL": {"und": "NBIS", "etf3x": None, "lev": 2, "fee2x": 0.0115, "fee3x": None},
    "CRWG": {"und": "CRWV", "etf3x": None, "lev": 2, "fee2x": 0.0077, "fee3x": None},
    "ASUP": {"und": "ASTS", "etf3x": None, "lev": 2, "fee2x": 0.0105, "fee3x": None},
    "RKLX": {"und": "RKLB", "etf3x": None, "lev": 2, "fee2x": 0.0131, "fee3x": None},
    "CBRX": {"und": "CBRS", "etf3x": None, "lev": 2, "fee2x": 0.0105, "fee3x": None},
    "LABX": {"und": "ALAB", "etf3x": None, "lev": 2, "fee2x": 0.0105, "fee3x": None},
    "CSEX": {"und": "CLS",  "etf3x": None, "lev": 2, "fee2x": 0.0105, "fee3x": None},
    "COHX": {"und": "COHR", "etf3x": None, "lev": 2, "fee2x": 0.0105, "fee3x": None},
    "LITX": {"und": "LITE", "etf3x": None, "lev": 2, "fee2x": 0.0105, "fee3x": None},
    "NXPX": {"und": "NXPI", "etf3x": None, "lev": 2, "fee2x": 0.0105, "fee3x": None},
    "MCHU": {"und": "MCHP", "etf3x": None, "lev": 2, "fee2x": 0.0105, "fee3x": None},
    "STXX": {"und": "STX",  "etf3x": None, "lev": 2, "fee2x": 0.0105, "fee3x": None},
    "WDCX": {"und": "WDC",  "etf3x": None, "lev": 2, "fee2x": 0.0105, "fee3x": None},
    "IREX": {"und": "IREN", "etf3x": None, "lev": 2, "fee2x": 0.0105, "fee3x": None},
    "LEUX": {"und": "LEU",  "etf3x": None, "lev": 2, "fee2x": 0.0105, "fee3x": None},
    # ── Semiconductor sector (SOXL = 3× SOXX) ───────────────────────────────
    "SOXL": {"und": "SOXX", "etf3x": None, "lev": 3, "fee2x": 0.0075, "fee3x": None},
}

# Underlyings unavailable in yfinance
_UNAVAILABLE_UND = {"SPCX"}

# ── Sector mapping ────────────────────────────────────────────────────────────

SECTOR_MAP = {
    # 芯片设计
    "NVDL": "chip_design", "AMDL": "chip_design", "AVL":  "chip_design",
    "ARMG": "chip_design", "QCMU": "chip_design", "TXNU": "chip_design",
    "NXPX": "chip_design", "MCHU": "chip_design", "CBRX": "chip_design", "ONX": "chip_design",
    # 晶圆代工 / IDM
    "TSMX": "foundry",    "INTW": "foundry",
    # 制造设备
    "LRCU": "equipment",  "KLAG": "equipment",  "ASMU": "equipment",  "AMAU": "equipment",
    # 存储
    "MULL": "memory",     "SNXX": "memory",     "STXX": "memory",     "WDCX": "memory",
    # 光互连 / 光子
    "MRVU": "optical",    "COHX": "optical",    "LITX": "optical",
    "LABX": "optical",    "LNOK": "optical",
    # 服务器 / 系统
    "DLLL": "server",     "CSEX": "server",
    # 云 / 算力
    "GGLL": "cloud",      "NBIL": "cloud",      "CRWG": "cloud",
    # 航天 / 国防
    "SPAL": "space",      "ASUP": "space",      "RKLX": "space",      "LEUX": "space",
    # 加密 / 金融科技
    "MSTU": "crypto",     "CONL": "crypto",     "HOOX": "crypto",
    "CRCG": "crypto",     "IREX": "crypto",
    # 应用 / 终端
    "TSLL": "consumer",
    # 宽基指数
    "QLD":  "index",      "SSO":  "index",      "DDM":  "index",
    # 半导体板块指数
    "SOXL": "semi_index",
}

SECTOR_LABELS = [
    ("chip_design", "芯片设计"),
    ("foundry",     "晶圆代工·IDM"),
    ("equipment",   "制造设备"),
    ("memory",      "存储"),
    ("optical",     "光互连·光子"),
    ("server",      "服务器·系统"),
    ("cloud",       "云·算力"),
    ("space",       "航天·国防"),
    ("crypto",      "加密·金融科技"),
    ("consumer",    "应用·终端"),
    ("index",       "宽基指数"),
    ("semi_index",  "板块指数"),
]

# ── Data fetching ─────────────────────────────────────────────────────────────

def _extract_close(hist: pd.DataFrame, ticker: str) -> pd.Series:
    if hist.empty:
        return pd.Series(dtype=float)
    col = hist["Close"]
    if isinstance(col, pd.DataFrame):
        col = col[ticker] if ticker in col.columns else col.iloc[:, 0]
    return col.dropna()


def fetch_data(etf2x: str, cfg: dict):
    """Returns (data_dict, None) or (None, error_str).

    data_dict keys:
      dates        — common trading dates (ISO strings)
      und_prices   — underlying (1×) adjusted close, same length as dates
      etf2x_prices — real 2× ETF adjusted close, same length as dates
      etf3x_prices — real 3× ETF adjusted close (or None)
      und2_prices  — secondary 1× reference (SOXL page: SMH), or None
      ipo          — ETF inception date (first trading day)
      latest       — last date in dates
      fee2x / fee3x
      und / etf3x / und2
      lev          — leverage for simulation
    """
    underlying = cfg["und"]
    etf3x      = cfg.get("etf3x")
    und2       = cfg.get("und2")  # secondary reference (SOXL page only)
    lev        = cfg.get("lev", 2)
    fee2x      = cfg.get("fee2x", 0.0115)
    fee3x      = cfg.get("fee3x")

    if underlying in _UNAVAILABLE_UND:
        msg = f"{underlying} 数据不可得（yfinance 不支持私有/特殊载体）"
        print(f"\n  ⚠  {etf2x}: {msg}")
        return None, msg

    try:
        # ── 1. Download 2× ETF to get inception date + real prices ──────────
        h2x = yf.download(etf2x, period="max", auto_adjust=True, progress=False)
        c2x = _extract_close(h2x, etf2x)
        if len(c2x) < 30:
            return None, f"2× ETF 数据不足 ({len(c2x)} 天)"
        ipo_date = c2x.index[0]

        # ── 2. Download underlying (1×) from inception ───────────────────────
        h_und = yf.download(underlying, start=ipo_date, auto_adjust=True, progress=False)
        c_und = _extract_close(h_und, underlying)
        if len(c_und) < 30:
            return None, f"正股数据不足 ({len(c_und)} 天)"

        # ── 3. Optional: secondary 1× reference (SMH for SOXL) ──────────────
        c_und2 = None
        if und2:
            h_und2 = yf.download(und2, start=ipo_date, auto_adjust=True, progress=False)
            c_und2 = _extract_close(h_und2, und2)
            if len(c_und2) < 10:
                c_und2 = None

        # ── 4. Optional: 3× ETF ──────────────────────────────────────────────
        c3x = None
        if etf3x:
            h3x = yf.download(etf3x, period="max", auto_adjust=True, progress=False)
            c3x = _extract_close(h3x, etf3x)
            if len(c3x) < 30:
                c3x = None

        # ── 5. Align on common trading dates ─────────────────────────────────
        common = c2x.index.intersection(c_und.index)
        if c3x is not None:
            common = common.intersection(c3x.index)
        if len(common) < 30:
            return None, f"共同交易日不足 ({len(common)} 天)"

        dates_list = [d.strftime("%Y-%m-%d") for d in common]

        def _prices(series):
            return [round(float(v), 6) for v in series.loc[common].values]

        result = {
            "dates":        dates_list,
            "und_prices":   _prices(c_und),
            "etf2x_prices": _prices(c2x),
            "etf3x_prices": _prices(c3x) if c3x is not None else None,
            "und2_prices":  None,
            "ipo":          ipo_date.strftime("%Y-%m-%d"),
            "latest":       common[-1].strftime("%Y-%m-%d"),
            "fee2x":        fee2x,
            "fee3x":        fee3x,
            "und":          underlying,
            "etf3x":        etf3x,
            "und2":         und2,
            "lev":          lev,
        }

        # Secondary reference: align separately (may have different history)
        if c_und2 is not None:
            common2 = common.intersection(c_und2.index)
            if len(common2) >= 30:
                result["und2_prices"] = {
                    "dates":  [d.strftime("%Y-%m-%d") for d in common2],
                    "prices": [round(float(v), 6) for v in c_und2.loc[common2].values],
                    "label":  und2,
                }

        return result, None

    except Exception as exc:
        return None, str(exc)


def verify(etf: str, data: dict):
    """Cross-check simulation in Python."""
    prices = data["und_prices"]
    fee    = data["fee2x"]
    lev    = data["lev"]
    n      = len(prices)
    p0     = prices[0]
    one_x  = prices[-1] / p0
    naive  = 1 + lev * (prices[-1] / p0 - 1)
    dr, df = 1.0, fee / 252.0
    for i in range(1, n):
        r  = prices[i] / prices[i - 1] - 1
        dr *= (1 + lev * r - df)
    # Real ETF return
    e2x = data["etf2x_prices"]
    real2x = e2x[-1] / e2x[0] if e2x else None
    print(f"  {n} 交易日  ({data['ipo']} → {data['latest']})")
    print(f"  1× 正股:              {(one_x - 1) * 100:+.1f}%")
    print(f"  朴素 {lev}×:              {(naive - 1) * 100:+.1f}%")
    print(f"  模拟每日重置 {lev}×:    {(dr - 1) * 100:+.1f}%")
    if real2x is not None:
        print(f"  真实 {etf} ({lev}×):       {(real2x - 1) * 100:+.1f}%")


# ── HTML template ─────────────────────────────────────────────────────────────

_HTML = '''\
<!DOCTYPE html>
<html lang="zh">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>杠杆 ETF 衰减对比图（交互版）</title>
  <script src="https://cdn.jsdelivr.net/npm/echarts@5/dist/echarts.min.js"></script>
  <style>
    *{box-sizing:border-box;margin:0;padding:0}
    html,body{height:100%;background:#0d1117;color:#e5e7eb;
              font-family:-apple-system,"PingFang SC",sans-serif;overflow:hidden}
    .app{display:flex;flex-direction:column;height:100vh}

    /* ── Header ── */
    header{flex-shrink:0;padding:8px 16px 6px;border-bottom:1px solid #21262d;
           background:#161b22;display:flex;align-items:center;gap:12px;flex-wrap:wrap}
    header h1{font-size:.92rem;color:#f3f4f6;white-space:nowrap}
    .pills{display:flex;flex-wrap:wrap;gap:4px;flex:1}
    .pill{background:transparent;border:1px solid #30363d;color:#8b949e;
          padding:2px 10px;border-radius:12px;cursor:pointer;font-size:.75rem;
          transition:all .15s;white-space:nowrap;font-family:inherit}
    .pill:hover{border-color:#58a6ff;color:#58a6ff}
    .pill.active{background:#1c3452;border-color:#58a6ff;color:#79c0ff;font-weight:600}

    /* ── Controls ── */
    .controls{flex-shrink:0;display:flex;align-items:center;gap:10px;
              padding:5px 16px;border-bottom:1px solid #21262d;
              background:#161b22;flex-wrap:wrap}
    .controls label{color:#8b949e;font-size:.78rem;white-space:nowrap}
    #dateInput{background:#21262d;border:1px solid #30363d;color:#e5e7eb;
               padding:3px 8px;border-radius:5px;font-size:.8rem;font-family:inherit;
               cursor:pointer}
    #dateInput:focus{outline:none;border-color:#58a6ff}
    .presets{display:flex;gap:5px;flex-wrap:wrap}
    .preset-btn{background:transparent;border:1px solid #30363d;color:#8b949e;
                padding:2px 9px;border-radius:5px;cursor:pointer;font-size:.74rem;
                font-family:inherit;transition:all .15s}
    .preset-btn:hover{border-color:#2dd4bf;color:#2dd4bf}
    #clamp-note{color:#f59e0b;font-size:.73rem;display:none}

    /* ── Dual chart area ── */
    .charts-row{flex:1;min-height:0;display:flex;gap:0}
    #chart-left{flex:1;min-width:0}
    .chart-divider{width:1px;background:#21262d;flex-shrink:0}
    #chart-right{flex:1;min-width:0}

    /* ── Disclaimer ── */
    .disclaimer{flex-shrink:0;padding:3px 16px;font-size:.67rem;color:#4b5563;
                border-top:1px solid #21262d;white-space:nowrap;
                overflow:hidden;text-overflow:ellipsis}

    /* ── Nav bar ── */
    .nav-bar{flex-shrink:0;display:flex;align-items:center;gap:12px;
             padding:5px 16px;border-top:1px solid #21262d;
             background:#161b22;justify-content:center}
    .nav-btn{background:#21262d;border:1px solid #30363d;color:#c9d1d9;
             padding:4px 16px;border-radius:5px;cursor:pointer;font-size:.8rem;
             font-family:inherit;transition:background .15s}
    .nav-btn:hover{background:#2d333b}
    .counter{color:#8b949e;font-size:.8rem;min-width:50px;text-align:center;
             font-variant-numeric:tabular-nums}
    .hint{color:#484f58;font-size:.68rem}

    /* ── Sector filter bar ── */
    .sector-bar{flex-shrink:0;display:flex;gap:5px;flex-wrap:wrap;
                padding:4px 16px;border-bottom:1px solid #21262d;background:#0d1117}
    .sector-chip{background:transparent;border:1px solid #30363d;color:#8b949e;
                 padding:2px 10px;border-radius:12px;cursor:pointer;font-size:.72rem;
                 font-family:inherit;transition:all .15s;white-space:nowrap}
    .sector-chip:hover{border-color:#2dd4bf;color:#2dd4bf}
    .sector-chip.active{background:#0d2a2a;border-color:#2dd4bf;color:#2dd4bf;font-weight:600}

    @media(max-width:600px){
      header,.controls,.sector-bar,.nav-bar{padding-left:10px;padding-right:10px}
      .controls{gap:7px}
      .charts-row{flex-direction:column}
      .chart-divider{width:100%;height:1px}
    }
  </style>
</head>
<body>
<div class="app">

  <header>
    <h1>杠杆 ETF 衰减对比图</h1>
    <div class="pills" id="pills">
      __PILLS__
    </div>
  </header>

  <div class="sector-bar">
    __SECTOR_CHIPS__
  </div>

  <div class="controls">
    <label>起始日期：</label>
    <input type="date" id="dateInput">
    <div class="presets">
      <button class="preset-btn" data-p="ipo">发行日</button>
      <button class="preset-btn" data-p="2022">2022</button>
      <button class="preset-btn" data-p="2023">2023</button>
      <button class="preset-btn" data-p="2024">2024</button>
      <button class="preset-btn" data-p="2025">2025</button>
      <button class="preset-btn" data-p="1y">近一年</button>
    </div>
    <span id="clamp-note">⚠ 已夹到最早可得日期</span>
  </div>

  <div class="charts-row">
    <div id="chart-left"></div>
    <div class="chart-divider"></div>
    <div id="chart-right"></div>
  </div>
  <div class="disclaimer" id="disclaimer"></div>

  <div class="nav-bar">
    <button class="nav-btn" id="prev">&#8592; 上一个</button>
    <span class="counter" id="counter"></span>
    <button class="nav-btn" id="next">下一个 &#8594;</button>
    <span class="hint">&#9095; 方向键切换</span>
  </div>
</div>

<script>
// ── Embedded price data ───────────────────────────────────────────────────────
const DATA      = __DATA_JSON__;
const ETF_ORDER = __ETF_ORDER_JSON__;
const N         = ETF_ORDER.length;
const SECTORS   = __SECTORS_JSON__;

const STATE = {};
let cur = 0, chartL = null, chartR = null;
let visibleOrder = [...ETF_ORDER];

// ── Helpers ───────────────────────────────────────────────────────────────────
function fmtPct(v) {
  const p = (v * 100).toFixed(1);
  return (v >= 0 ? "+" : "") + p + "%";
}
function fmtMult(v) {
  if (v >= 100) return v.toFixed(0) + "×";
  if (v >= 10)  return v.toFixed(1) + "×";
  if (v >= 1)   return v.toFixed(2) + "×";
  return v.toFixed(3) + "×";
}
function lowerBound(arr, target) {
  let lo = 0, hi = arr.length - 1;
  while (lo < hi) { const m = (lo + hi) >> 1; arr[m] < target ? lo = m + 1 : hi = m; }
  return lo;
}

// ── Simulation (right chart) ──────────────────────────────────────────────────
function computeSim(undPrices, si, fee, lev) {
  const s = undPrices.slice(si), n = s.length, p0 = s[0], df = fee / 252;
  const oneX  = new Float64Array(n);
  const naive = new Float64Array(n);
  const dr    = new Float64Array(n);
  oneX[0] = naive[0] = dr[0] = 1.0;
  for (let i = 1; i < n; i++) {
    const net = s[i] / p0;
    oneX[i]   = net;
    naive[i]  = 1 + lev * (net - 1);
    const r   = s[i] / s[i - 1] - 1;
    dr[i]     = dr[i - 1] * (1 + lev * r - df);
  }
  return { oneX, naive, dr };
}

// ── 3× simulation (for index pages) ──────────────────────────────────────────
function computeSim3(undPrices, si, fee3x) {
  const s = undPrices.slice(si), n = s.length, p0 = s[0], df = fee3x / 252;
  const naive3 = new Float64Array(n);
  const dr3    = new Float64Array(n);
  naive3[0] = dr3[0] = 1.0;
  for (let i = 1; i < n; i++) {
    const net = s[i] / p0;
    naive3[i]  = 1 + 3 * (net - 1);
    const r    = s[i] / s[i - 1] - 1;
    dr3[i]     = dr3[i - 1] * (1 + 3 * r - df);
  }
  return { naive3, dr3 };
}

// ── Log-axis guard & bounds ───────────────────────────────────────────────────
function logBounds(arrays) {
  const allVals = arrays.flat().filter(v => v > 0);
  if (!allVals.length) return { useLog: false };
  const maxAll = Math.max(...allVals), minAll = Math.min(...allVals);
  const useLog = maxAll > 5 && minAll > 0.01;
  if (!useLog) return { useLog: false };
  const lMin = Math.log10(Math.max(minAll, 1e-9));
  const lMax = Math.log10(maxAll);
  const pad  = (lMax - lMin) * 0.12;
  return { useLog: true, yMin: Math.pow(10, lMin - pad), yMax: Math.pow(10, lMax + pad) };
}

// ── Rebase series to index 0 = 1.0 ───────────────────────────────────────────
function rebase(prices, si) {
  const s = prices.slice(si), p0 = s[0];
  return s.map(v => v / p0);
}

// ── Shared yAxis config builder ───────────────────────────────────────────────
function yAxisCfg(useLog, yMin, yMax, name) {
  return {
    type: useLog ? "log" : "value",
    logBase: 10,
    min: useLog ? yMin : undefined,
    max: useLog ? yMax : undefined,
    name,
    nameTextStyle: { color: "#4b5563", fontSize: 8.5, padding: [0,0,0,54] },
    axisLine:  { lineStyle: { color: "#30363d" } },
    axisTick:  { show: false },
    axisLabel: { color: "#6b7280", fontSize: 9, formatter: v => fmtMult(v) },
    splitLine: { lineStyle: { color: "#21262d", width: 0.8 } },
  };
}
function xAxisCfg(dates) {
  return {
    type: "category",
    data: dates,
    axisLine:  { lineStyle: { color: "#30363d" } },
    axisTick:  { show: false },
    axisLabel: { color: "#6b7280", fontSize: 9, interval: "auto", showMaxLabel: true },
    splitLine: { show: false },
  };
}
function tooltipCfg() {
  return {
    trigger: "axis",
    backgroundColor: "#1c2333",
    borderColor: "#30363d",
    textStyle: { color: "#e5e7eb", fontSize: 11 },
    axisPointer: { lineStyle: { color: "#444c56" } },
    formatter(params) {
      return "<b>" + params[0].axisValue + "</b><br>" + params.map(p =>
        `<span style="color:${p.color}">●</span>&nbsp;${p.seriesName}:&nbsp;<b>${fmtPct(p.value - 1)}</b>`
      ).join("<br>");
    },
  };
}

// ── Push end-labels apart if they overlap ─────────────────────────────────────
function fixEndLabels(ch, pts) {
  try {
    pts.forEach(p => { p.py = ch.convertToPixel({ yAxisIndex: 0 }, p.val); });
    pts.sort((a, b) => b.py - a.py);
    const minPx = 16;
    for (let pass = 0; pass < 4; pass++) {
      for (let i = 0; i < pts.length - 1; i++) {
        const gap = pts[i].py - pts[i + 1].py;
        if (gap < minPx) {
          const adj = (minPx - gap) / 2;
          pts[i].py     += adj;
          pts[i + 1].py -= adj;
        }
      }
    }
    const ordered = Array(pts.length).fill(null);
    pts.forEach(p => {
      ordered[p.idx] = { endLabel: { offset: [0, p.py - ch.convertToPixel({ yAxisIndex: 0 }, p.val)] } };
    });
    ch.setOption({ series: ordered });
  } catch (_) {}
}

// ── LEFT chart: real price comparison (rebase to window start = 1) ────────────
function drawLeft(d, etf, dates, si) {
  const lev = d.lev || 2;
  const undReb  = rebase(d.und_prices,  si);
  const e2xReb  = rebase(d.etf2x_prices, si);

  const series = [
    {
      name: `${d.und} 正股 (1×)`,
      type: "line", data: undReb, symbol: "none",
      lineStyle: { color: "#9ca3af", width: 1.5 },
      itemStyle: { color: "#9ca3af" },
      endLabel: { show: true, formatter: () => fmtPct(undReb[undReb.length-1]-1),
                  color: "#9ca3af", fontSize: 10, fontWeight: "bold" },
    },
    {
      name: `${etf} (真实${lev}×)`,
      type: "line", data: e2xReb, symbol: "none",
      lineStyle: { color: "#2dd4bf", width: 2.5 },
      itemStyle: { color: "#2dd4bf" },
      endLabel: { show: true, formatter: () => fmtPct(e2xReb[e2xReb.length-1]-1),
                  color: "#2dd4bf", fontSize: 10, fontWeight: "bold" },
    },
  ];
  const pts = [
    { idx: 0, val: undReb[undReb.length-1] },
    { idx: 1, val: e2xReb[e2xReb.length-1] },
  ];

  // 3× ETF line (index pages)
  if (d.etf3x && d.etf3x_prices) {
    const e3xReb = rebase(d.etf3x_prices, si);
    series.push({
      name: `${d.etf3x} (真实3×)`,
      type: "line", data: e3xReb, symbol: "none",
      lineStyle: { color: "#c084fc", width: 2.5 },
      itemStyle: { color: "#c084fc" },
      endLabel: { show: true, formatter: () => fmtPct(e3xReb[e3xReb.length-1]-1),
                  color: "#c084fc", fontSize: 10, fontWeight: "bold" },
    });
    pts.push({ idx: 2, val: e3xReb[e3xReb.length-1] });
  }

  // Secondary 1× reference (SMH for SOXL)
  if (d.und2_prices) {
    const und2Dates = d.und2_prices.dates;
    const und2Prices = d.und2_prices.prices;
    const si2 = lowerBound(und2Dates, dates[0]);
    if (si2 < und2Prices.length) {
      const und2Reb = rebase(und2Prices, si2);
      // Align to main dates — fill with null where missing
      const und2Map = {};
      for (let i = si2; i < und2Dates.length; i++) {
        und2Map[und2Dates[i]] = und2Reb[i - si2];
      }
      const und2Aligned = dates.map(dt => und2Map[dt] ?? null);
      const lastValid = und2Aligned.reduce((acc, v, i) => v !== null ? i : acc, 0);
      series.push({
        name: `${d.und2_prices.label} (1× 参考)`,
        type: "line", data: und2Aligned, symbol: "none",
        lineStyle: { color: "#6b7280", width: 1.2, type: "dashed" },
        itemStyle: { color: "#6b7280" },
        endLabel: { show: true,
                    formatter: () => und2Aligned[lastValid] != null ? fmtPct(und2Aligned[lastValid]-1) : "",
                    color: "#6b7280", fontSize: 10 },
        connectNulls: false,
      });
      if (und2Aligned[lastValid] != null)
        pts.push({ idx: series.length-1, val: und2Aligned[lastValid] });
    }
  }

  const allArrays = series.map(s => s.data.filter(v => v !== null));
  const { useLog, yMin, yMax } = logBounds(allArrays);
  const guard = useLog ? v => (v > 0 ? v : 1e-6) : v => v;
  series.forEach(s => { s.data = s.data.map(v => v === null ? null : guard(v)); });
  pts.forEach(p => { p.val = guard(p.val); });

  const narrow = window.innerWidth < 520;
  chartL.setOption({
    backgroundColor: "#0d1117",
    animation: false,
    title: [{ text: narrow ? `实际价格  ${dates[0]}` : `实际价格对比  ·  起点 = 100  ·  ${dates[0]} →`,
              textStyle: { color: "#e5e7eb", fontSize: 11, fontWeight: "bold" },
              top: 10, left: 12 }],
    grid:    { top: 44, right: 96, bottom: 46, left: 64 },
    xAxis:   xAxisCfg(dates),
    yAxis:   yAxisCfg(useLog, yMin, yMax, useLog ? "净值（对数，起点=1）" : "净值（起点=1）"),
    tooltip: tooltipCfg(),
    legend:  { bottom: 5, textStyle: { color: "#9ca3af", fontSize: 9 },
               icon: "roundRect", itemWidth: 18, itemHeight: 3 },
    series,
  }, { notMerge: true });

  setTimeout(() => fixEndLabels(chartL, pts), 30);
}

// ── RIGHT chart: decay simulation ────────────────────────────────────────────
function drawRight(d, etf, dates, si) {
  const lev  = d.lev || 2;
  const fee  = d.fee2x;
  const { oneX, naive, dr } = computeSim(d.und_prices, si, fee, lev);

  const last = dates.length - 1;
  const fO = oneX[last], fN = naive[last], fD = dr[last];

  const allArrs = [Array.from(oneX), Array.from(naive), Array.from(dr)];
  const series = [
    {
      name: `${d.und} 正股 (1×)`,
      type: "line", data: Array.from(oneX), symbol: "none",
      lineStyle: { color: "#9ca3af", width: 1.5 },
      itemStyle: { color: "#9ca3af" },
      endLabel: { show: true, formatter: () => fmtPct(fO-1),
                  color: "#9ca3af", fontSize: 10, fontWeight: "bold" },
    },
    {
      name: `朴素${lev}倍累计`,
      type: "line", data: Array.from(naive), symbol: "none",
      lineStyle: { color: "#f59e0b", width: 1.8, type: "dashed" },
      itemStyle: { color: "#f59e0b" },
      endLabel: { show: true, formatter: () => fmtPct(fN-1),
                  color: "#f59e0b", fontSize: 10, fontWeight: "bold" },
    },
    {
      name: `模拟每日重置${lev}× (${etf})`,
      type: "line", data: Array.from(dr), symbol: "none",
      lineStyle: { color: "#2dd4bf", width: 2.5 },
      itemStyle: { color: "#2dd4bf" },
      endLabel: { show: true, formatter: () => fmtPct(fD-1),
                  color: "#2dd4bf", fontSize: 10, fontWeight: "bold" },
    },
  ];
  const pts = [
    { idx: 0, val: fO },
    { idx: 1, val: fN },
    { idx: 2, val: fD },
  ];

  // Extra 3× simulation lines for index pages
  if (d.etf3x && d.fee3x != null) {
    const { naive3, dr3 } = computeSim3(d.und_prices, si, d.fee3x);
    const fN3 = naive3[last], fD3 = dr3[last];
    allArrs.push(Array.from(naive3), Array.from(dr3));
    series.push({
      name: "朴素3倍累计",
      type: "line", data: Array.from(naive3), symbol: "none",
      lineStyle: { color: "#fb923c", width: 1.8, type: "dashed" },
      itemStyle: { color: "#fb923c" },
      endLabel: { show: true, formatter: () => fmtPct(fN3-1),
                  color: "#fb923c", fontSize: 10, fontWeight: "bold" },
    });
    series.push({
      name: `模拟每日重置3× (${d.etf3x})`,
      type: "line", data: Array.from(dr3), symbol: "none",
      lineStyle: { color: "#c084fc", width: 2.5 },
      itemStyle: { color: "#c084fc" },
      endLabel: { show: true, formatter: () => fmtPct(fD3-1),
                  color: "#c084fc", fontSize: 10, fontWeight: "bold" },
    });
    pts.push({ idx: 3, val: fN3 }, { idx: 4, val: fD3 });
  }

  const { useLog, yMin, yMax } = logBounds(allArrs);
  const guard = useLog ? v => Math.max(v, 1e-6) : v => v;
  series.forEach(s => { s.data = s.data.map(guard); });
  pts.forEach(p => { p.val = guard(p.val); });

  chartR.setOption({
    backgroundColor: "#0d1117",
    animation: false,
    title: [{ text: `衰减模拟  ·  ${lev}× 每日重置  ·  ${dates[0]} →`,
              textStyle: { color: "#e5e7eb", fontSize: 11, fontWeight: "bold" },
              top: 10, left: 12 }],
    grid:    { top: 44, right: 96, bottom: 46, left: 64 },
    xAxis:   xAxisCfg(dates),
    yAxis:   yAxisCfg(useLog, yMin, yMax, useLog ? "净值（对数，起点=1）" : "净值（起点=1）"),
    tooltip: tooltipCfg(),
    legend:  { bottom: 5, textStyle: { color: "#9ca3af", fontSize: 9 },
               icon: "roundRect", itemWidth: 18, itemHeight: 3 },
    series,
  }, { notMerge: true });

  setTimeout(() => fixEndLabels(chartR, pts), 30);
}

// ── Redraw both charts ────────────────────────────────────────────────────────
function redraw() {
  const etf = visibleOrder[cur];
  const d   = DATA[etf];

  const errOpt = (msg) => ({
    backgroundColor: "#0d1117",
    graphic: [{ type: "text", left: "center", top: "middle",
      style: { text: msg, fill: "#f87171", fontSize: 16 } }]
  });

  if (!d || d.error) {
    chartL.clear(); chartL.setOption(errOpt(d ? d.error : "无数据"));
    chartR.clear(); chartR.setOption(errOpt(d ? d.error : "无数据"));
    document.getElementById("disclaimer").textContent = "";
    return;
  }

  // Resolve start date
  const input     = document.getElementById("dateInput");
  const clampNote = document.getElementById("clamp-note");
  const requested = input.value;
  const clamped   = !requested || requested < d.dates[0];
  const startDate = clamped ? d.dates[0] : requested;
  if (clamped) input.value = startDate;
  clampNote.style.display = clamped ? "inline" : "none";
  STATE[etf] = startDate;

  const si    = lowerBound(d.dates, startDate);
  const dates = d.dates.slice(si);

  drawLeft(d, etf, dates, si);
  drawRight(d, etf, dates, si);

  document.getElementById("disclaimer").textContent =
    `假设费率 ${(d.fee2x * 100).toFixed(2)}%/年  ·  ` +
    `数据: yfinance ${d.und} 日线复权收盘价 ${d.dates[0]} 至 ${d.latest} (${d.dates.length} 交易日)  ·  仅供学习参考，非投资建议。`;
}

// ── ETF switcher ──────────────────────────────────────────────────────────────
function show(i) {
  const n = visibleOrder.length;
  if (!n) return;
  const pills = document.querySelectorAll(".pill");
  pills.forEach(p => p.classList.remove("active"));
  cur = ((i % n) + n) % n;
  const etf = visibleOrder[cur];
  const pi  = ETF_ORDER.indexOf(etf);
  pills[pi].classList.add("active");
  pills[pi].scrollIntoView({ behavior: "smooth", block: "nearest", inline: "center" });
  document.getElementById("counter").innerHTML = (cur + 1) + "&nbsp;/&nbsp;" + n;

  const d = DATA[etf];
  const input = document.getElementById("dateInput");
  if (d && !d.error) {
    input.min   = d.dates[0];
    input.max   = d.latest;
    input.value = STATE[etf] || d.ipo;
  }
  document.getElementById("clamp-note").style.display = "none";
  redraw();
}

// ── Sector filter ─────────────────────────────────────────────────────────────
function setFilter(sectorKey) {
  visibleOrder = sectorKey
    ? ETF_ORDER.filter(e => SECTORS[e] === sectorKey)
    : [...ETF_ORDER];
  document.querySelectorAll(".pill").forEach((pill, i) => {
    pill.style.display = (!sectorKey || SECTORS[ETF_ORDER[i]] === sectorKey) ? "" : "none";
  });
  document.querySelectorAll(".sector-chip").forEach(chip => {
    chip.classList.toggle("active", chip.dataset.sector === sectorKey);
  });
  show(0);
}

// ── Preset buttons ────────────────────────────────────────────────────────────
document.querySelectorAll(".preset-btn").forEach(btn => {
  btn.addEventListener("click", () => {
    const d = DATA[visibleOrder[cur]];
    if (!d || d.error) return;
    const input = document.getElementById("dateInput");
    const p = btn.dataset.p;
    let t;
    if (p === "ipo") {
      t = d.ipo;
    } else if (p === "1y") {
      const dt = new Date(d.latest);
      dt.setFullYear(dt.getFullYear() - 1);
      t = dt.toISOString().slice(0, 10);
    } else {
      t = p + "-01-02";
    }
    if (t < d.dates[0]) t = d.dates[0];
    if (t > d.latest)   t = d.latest;
    input.value = t;
    redraw();
  });
});

// ── Wire-up ───────────────────────────────────────────────────────────────────
document.getElementById("dateInput").addEventListener("change", redraw);
document.querySelectorAll(".pill").forEach((p, i) => {
  const etf = ETF_ORDER[i];
  p.addEventListener("click", () => {
    const vi = visibleOrder.indexOf(etf);
    if (vi >= 0) show(vi);
  });
});
document.querySelectorAll(".sector-chip").forEach(chip => {
  chip.addEventListener("click", () => setFilter(chip.dataset.sector));
});
document.getElementById("prev").addEventListener("click", () => show(cur - 1));
document.getElementById("next").addEventListener("click", () => show(cur + 1));
document.addEventListener("keydown", e => {
  if (e.key === "ArrowRight" || e.key === "ArrowDown") show(cur + 1);
  if (e.key === "ArrowLeft"  || e.key === "ArrowUp")   show(cur - 1);
});
window.addEventListener("resize", () => {
  chartL && chartL.resize();
  chartR && chartR.resize();
});

// ── Boot ──────────────────────────────────────────────────────────────────────
chartL = echarts.init(document.getElementById("chart-left"),  null, { renderer: "canvas" });
chartR = echarts.init(document.getElementById("chart-right"), null, { renderer: "canvas" });
show(0);
</script>
</body>
</html>
'''

# ── Build helpers ─────────────────────────────────────────────────────────────

def build_pills(etf_order: list) -> str:
    parts = []
    for i, etf in enumerate(etf_order):
        cls = "pill active" if i == 0 else "pill"
        und = ETF_CONFIG[etf]["und"]
        parts.append(f'<button class="{cls}" title="{und}">{etf}</button>')
    return "\n      ".join(parts)


def build_sector_chips(etf_order: list) -> str:
    counts: dict = {}
    for etf in etf_order:
        s = SECTOR_MAP.get(etf, "")
        if s:
            counts[s] = counts.get(s, 0) + 1
    total = len(etf_order)
    parts = [f'<button class="sector-chip active" data-sector="">全部 ({total})</button>']
    for key, label in SECTOR_LABELS:
        n = counts.get(key, 0)
        if n:
            parts.append(f'<button class="sector-chip" data-sector="{key}">{label} ({n})</button>')
    return "\n    ".join(parts)


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    only = sys.argv[1].upper() if len(sys.argv) > 1 else None
    etf_order = list(ETF_CONFIG.keys())

    sep = "=" * 60
    print(sep)
    mode = f"单支验证: {only}" if only else f"全部 {len(etf_order)} 支"
    print(f"  交互版衰减图生成器 — {mode}")
    print(sep)

    all_data: dict = {}
    for etf, cfg in ETF_CONFIG.items():
        if only and etf != only:
            all_data[etf] = {"error": f"未在此次运行中加载 (仅运行 {only})", "und": cfg["und"]}
            continue

        und = cfg["und"]
        etf3x = cfg.get("etf3x", "")
        suffix = f" + {etf3x}" if etf3x else ""
        print(f"  [{etf} → {und}{suffix}] 下载中…", end=" ", flush=True)
        data, err = fetch_data(etf, cfg)
        if err:
            print(f"错误: {err}")
            all_data[etf] = {"error": err, "und": und}
        else:
            nd = len(data["dates"])
            print(f"{nd} 天  ({data['ipo']} → {data['latest']})")
            if data.get("etf3x_prices"):
                print(f"    3× {etf3x}: {nd} 天")
            all_data[etf] = data
            if only:
                print()
                verify(etf, data)

    # Assemble HTML
    pills_html        = build_pills(etf_order)
    sector_chips_html = build_sector_chips(etf_order)
    data_json         = json.dumps(all_data, ensure_ascii=False, separators=(",", ":"))
    etf_order_json    = json.dumps(etf_order)
    sectors_json      = json.dumps(SECTOR_MAP, ensure_ascii=False)

    html = (
        _HTML
        .replace("__PILLS__",          pills_html)
        .replace("__SECTOR_CHIPS__",   sector_chips_html)
        .replace("__DATA_JSON__",      data_json)
        .replace("__ETF_ORDER_JSON__", etf_order_json)
        .replace("__SECTORS_JSON__",   sectors_json)
    )

    out = str(Path(__file__).parent / "index.html")
    with open(out, "w", encoding="utf-8") as fh:
        fh.write(html)

    print()
    print(sep)
    print(f"  完成 → {out}  ({len(html) // 1024} KB)")
    print(f"  打开: open {out}")
    print(sep)


if __name__ == "__main__":
    main()
