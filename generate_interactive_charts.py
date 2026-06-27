#!/usr/bin/env python3
"""
generate_interactive_charts.py — Interactive ECharts decay comparison.

Embeds raw price data as JSON in the HTML; the browser does all slicing,
normalisation, and rendering via ECharts.  No server required.

Usage:
  .venv/bin/python3 generate_interactive_charts.py          # all 22 ETFs
  .venv/bin/python3 generate_interactive_charts.py MULL     # one ETF (verify)
Output: index.html
"""
import json
import sys
import warnings

import pandas as pd
import yfinance as yf

warnings.filterwarnings("ignore")

# ── Config ────────────────────────────────────────────────────────────────────

ETF_MAP = {
    "GGLL": "GOOG", "ARMG": "ARM",  "MRVU": "MRVL", "NVDL": "NVDA",
    "AMDL": "AMD",  "AVL":  "AVGO", "INTW": "INTC",  "QCMU": "QCOM",
    "TXNU": "TXN",  "ONX":  "ON",   "SNXX": "SNDK",  "MULL": "MU",
    "TSMX": "TSM",  "ASMU": "ASML", "LRCU": "LRCX",  "KLAG": "KLAC",
    "AMAU": "AMAT", "DLLL": "DELL", "LNOK": "NOK",
    "QLD":  "QQQ",  "SSO":  "SPY",  "DDM":  "DIA",
}

ETF_FEES = {
    "NVDL": 0.0115, "AMDL": 0.0115, "MULL": 0.0115, "INTW": 0.0115,
    "KLAG": 0.0115, "AMAU": 0.0115, "DLLL": 0.0115, "ARMG": 0.0115,
    "GGLL": 0.0095, "MRVU": 0.0095, "AVL":  0.0095, "QCMU": 0.0095,
    "TXNU": 0.0095, "TSMX": 0.0095, "ASMU": 0.0095, "LRCU": 0.0095,
    "ONX":  0.0105, "SNXX": 0.0105, "LNOK": 0.0090,
    "QLD":  0.0095, "SSO":  0.0089, "DDM":  0.0095,
}

LEVERAGE = 2.0

# ── Data fetching ─────────────────────────────────────────────────────────────

def _extract_close(hist: pd.DataFrame, ticker: str) -> pd.Series:
    if hist.empty:
        return pd.Series(dtype=float)
    col = hist["Close"]
    if isinstance(col, pd.DataFrame):
        col = col[ticker] if ticker in col.columns else col.iloc[:, 0]
    return col.dropna()


def fetch_data(etf: str, underlying: str):
    """Returns (data_dict, None) or (None, error_str)."""
    try:
        etf_hist  = yf.download(etf, period="max", auto_adjust=True, progress=False)
        etf_close = _extract_close(etf_hist, etf)
        if len(etf_close) < 30:
            return None, f"ETF数据不足 ({len(etf_close)} 天)"

        ipo_date   = etf_close.index[0]
        stock_hist = yf.download(underlying, start=ipo_date,
                                 auto_adjust=True, progress=False)
        stock_close = _extract_close(stock_hist, underlying)
        if len(stock_close) < 30:
            return None, f"正股数据不足 ({len(stock_close)} 天)"

        common = etf_close.index.intersection(stock_close.index)
        if len(common) < 30:
            return None, f"共同交易日不足 ({len(common)} 天)"

        aligned = stock_close.loc[common]
        return {
            "dates":  [d.strftime("%Y-%m-%d") for d in aligned.index],
            "prices": [round(float(p), 6) for p in aligned.values],
            "ipo":    ipo_date.strftime("%Y-%m-%d"),
            "latest": common[-1].strftime("%Y-%m-%d"),
            "fee":    ETF_FEES.get(etf, 0.0115),
            "und":    underlying,
        }, None
    except Exception as exc:
        return None, str(exc)


def verify(etf: str, data: dict):
    """Compute IPO-to-latest returns in Python to cross-check against JS."""
    prices = data["prices"]
    fee    = data["fee"]
    n      = len(prices)
    p0     = prices[0]
    one_x  = prices[-1] / p0
    naive  = 1 + LEVERAGE * (prices[-1] / p0 - 1)
    dr, df = 1.0, fee / 252.0
    for i in range(1, n):
        r  = prices[i] / prices[i - 1] - 1
        dr *= (1 + LEVERAGE * r - df)
    print(f"  {n} 交易日  ({data['ipo']} → {data['latest']})")
    print(f"  1× 正股:       {(one_x - 1) * 100:+.1f}%")
    print(f"  朴素 2×:       {(naive - 1) * 100:+.1f}%")
    print(f"  每日重置 2×:   {(dr - 1) * 100:+.1f}%")

# ── HTML template ─────────────────────────────────────────────────────────────
# Placeholders (replaced with str.replace, not str.format):
#   __PILLS__          → pill button HTML
#   __DATA_JSON__      → JSON object keyed by ETF ticker
#   __ETF_ORDER_JSON__ → JSON array of tickers in display order

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

    /* ── Chart ── */
    #chart{flex:1;min-height:0}

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

    @media(max-width:600px){
      header,.controls,.nav-bar{padding-left:10px;padding-right:10px}
      .controls{gap:7px}
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

  <div id="chart"></div>
  <div class="disclaimer" id="disclaimer"></div>

  <div class="nav-bar">
    <button class="nav-btn" id="prev">&#8592; 上一个</button>
    <span class="counter" id="counter"></span>
    <button class="nav-btn" id="next">下一个 &#8594;</button>
    <span class="hint">&#9095; 方向键切换</span>
  </div>
</div>

<script>
// ── Embedded price data (Python-generated) ────────────────────────────────────
const DATA      = __DATA_JSON__;
const ETF_ORDER = __ETF_ORDER_JSON__;
const N         = ETF_ORDER.length;

// Per-ETF remembered start date (survives ETF switches)
const STATE = {};
let cur = 0, chart = null;

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
// First index where arr[i] >= target (binary search on sorted string array)
function lowerBound(arr, target) {
  let lo = 0, hi = arr.length - 1;
  while (lo < hi) { const m = (lo + hi) >> 1; arr[m] < target ? lo = m + 1 : hi = m; }
  return lo;
}

// ── Core maths (mirrors Python simulate()) ───────────────────────────────────
// net      = prices[i] / prices[startIdx]          (= one_x)
// naive    = 1 + 2*(net - 1)
// dr[i]    = dr[i-1] * (1 + 2*daily_return - fee/252)
function compute(prices, si, fee) {
  const s = prices.slice(si), n = s.length, p0 = s[0], df = fee / 252;
  const oneX = new Float64Array(n), naive = new Float64Array(n), dr = new Float64Array(n);
  oneX[0] = naive[0] = dr[0] = 1.0;
  for (let i = 1; i < n; i++) {
    const net = s[i] / p0;
    oneX[i]  = net;
    naive[i] = 1 + 2 * (net - 1);
    const r  = s[i] / s[i - 1] - 1;
    dr[i]    = dr[i - 1] * (1 + 2 * r - df);
  }
  return { oneX, naive, dr };
}

// ── Redraw ────────────────────────────────────────────────────────────────────
function redraw() {
  const etf = ETF_ORDER[cur];
  const d   = DATA[etf];

  // Error / placeholder panel
  if (!d || d.error) {
    chart.clear();
    chart.setOption({
      backgroundColor: "#0d1117",
      graphic: [{ type: "text", left: "center", top: "middle",
        style: { text: d ? d.error : "无数据", fill: "#f87171", fontSize: 16 } }]
    });
    document.getElementById("disclaimer").textContent = "";
    return;
  }

  // Resolve start date
  const input       = document.getElementById("dateInput");
  const clampNote   = document.getElementById("clamp-note");
  const requested   = input.value;
  const clamped     = !requested || requested < d.dates[0];
  const startDate   = clamped ? d.dates[0] : requested;
  if (clamped) input.value = startDate;
  clampNote.style.display = clamped ? "inline" : "none";
  STATE[etf] = startDate;

  const si    = lowerBound(d.dates, startDate);
  const dates = d.dates.slice(si);
  const { oneX, naive, dr } = compute(d.prices, si, d.fee);
  const last  = dates.length - 1;
  const fO = oneX[last], fN = naive[last], fD = dr[last];

  // Log-scale decision (same rule as Python)
  const naiveMin = Math.min(...naive), drMin = Math.min(...dr);
  const maxAll   = Math.max(...oneX, ...naive, ...dr);
  const useLog   = maxAll > 5 && naiveMin > 0.05 && drMin > 0.01;
  const guard    = useLog ? v => Math.max(v, 1e-6) : v => v;

  const o1 = Array.from(oneX,  guard);
  const o2 = Array.from(naive, guard);
  const o3 = Array.from(dr,    guard);

  // Log y-axis min: avoid extending down to 0.1× when data never dips below 0.3×
  let yAxisMin = undefined;
  if (useLog) {
    const allMin = Math.min(...o1, ...o2, ...o3);
    yAxisMin = allMin >= 0.3 ? 0.3 : allMin >= 0.03 ? 0.1 : 0.01;
  }

  // Adaptive title: shorten on narrow viewports
  const narrow = window.innerWidth < 520;
  const titleText = narrow
    ? `${etf}  ·  ${d.und}  ·  ${startDate}`
    : `${etf}  ·  正股 ${d.und}  ·  起点 ${startDate}  →  ${d.latest}  (${dates.length} 交易日)`;

  chart.setOption({
    backgroundColor: "#0d1117",
    animation: false,
    title: [{
      text: titleText,
      textStyle: { color: "#e5e7eb", fontSize: 12, fontWeight: "bold" },
      top: 10, left: 14,
    }],
    grid: { top: 44, right: 96, bottom: 46, left: 64 },
    xAxis: {
      type: "category",
      data: dates,
      axisLine:  { lineStyle: { color: "#30363d" } },
      axisTick:  { show: false },
      axisLabel: { color: "#6b7280", fontSize: 9, interval: "auto", showMaxLabel: true },
      splitLine: { show: false },
    },
    yAxis: {
      type: useLog ? "log" : "value",
      logBase: 10,
      min: yAxisMin,
      name: useLog ? "净值（对数轴，起点=1）" : "净值（起点=1）",
      nameTextStyle: { color: "#4b5563", fontSize: 8.5, padding: [0, 0, 0, 54] },
      axisLine:  { lineStyle: { color: "#30363d" } },
      axisTick:  { show: false },
      axisLabel: { color: "#6b7280", fontSize: 9, formatter: v => fmtMult(v) },
      splitLine: { lineStyle: { color: "#21262d", width: 0.8 } },
    },
    tooltip: {
      trigger: "axis",
      backgroundColor: "#1c2333",
      borderColor: "#30363d",
      textStyle: { color: "#e5e7eb", fontSize: 11 },
      axisPointer: { lineStyle: { color: "#444c56" } },
      formatter(params) {
        const date = params[0].axisValue;
        return "<b>" + date + "</b><br>" + params.map(p =>
          `<span style="color:${p.color}">●</span>&nbsp;${p.seriesName}:&nbsp;<b>${fmtPct(p.value - 1)}</b>`
        ).join("<br>");
      },
    },
    legend: {
      bottom: 5,
      textStyle: { color: "#9ca3af", fontSize: 9 },
      icon: "roundRect", itemWidth: 18, itemHeight: 3,
    },
    series: [
      {
        name: `${d.und} 正股 (1×)`,
        type: "line", data: o1, symbol: "none",
        lineStyle: { color: "#9ca3af", width: 1.5 },
        itemStyle: { color: "#9ca3af" },
        endLabel: { show: true, formatter: () => fmtPct(fO - 1),
                    color: "#9ca3af", fontSize: 10, fontWeight: "bold" },
      },
      {
        name: "朴素2倍累计",
        type: "line", data: o2, symbol: "none",
        lineStyle: { color: "#f59e0b", width: 1.8, type: "dashed" },
        itemStyle: { color: "#f59e0b" },
        endLabel: { show: true, formatter: () => fmtPct(fN - 1),
                    color: "#f59e0b", fontSize: 10, fontWeight: "bold" },
      },
      {
        name: `每日重置2倍 (${etf})`,
        type: "line", data: o3, symbol: "none",
        lineStyle: { color: "#2dd4bf", width: 2.5 },
        itemStyle: { color: "#2dd4bf" },
        endLabel: { show: true, formatter: () => fmtPct(fD - 1),
                    color: "#2dd4bf", fontSize: 10, fontWeight: "bold" },
      },
    ],
  }, { notMerge: true });

  // Post-render: collision-avoid the three end labels using pixel positions
  setTimeout(() => {
    try {
      const pts = [
        { idx: 0, val: guard(fO), color: "#9ca3af", text: fmtPct(fO - 1) },
        { idx: 1, val: guard(fN), color: "#f59e0b", text: fmtPct(fN - 1) },
        { idx: 2, val: guard(fD), color: "#2dd4bf", text: fmtPct(fD - 1) },
      ];
      pts.forEach(p => { p.py = chart.convertToPixel({ yAxisIndex: 0 }, p.val); });

      // Sort by pixel-y descending (bottom of screen first)
      pts.sort((a, b) => b.py - a.py);

      // Two passes: push upper labels up when gap < 16 px
      const minPx = 16;
      for (let pass = 0; pass < 3; pass++) {
        for (let i = 0; i < pts.length - 1; i++) {
          const gap = pts[i].py - pts[i + 1].py; // positive = i is lower
          if (gap < minPx) {
            const adj = (minPx - gap) / 2;
            pts[i].py     += adj;
            pts[i + 1].py -= adj;
          }
        }
      }

      // Apply dy offset = adjusted_py - original_py
      const seriesUpdates = pts.map(p => ({
        endLabel: {
          offset: [0, p.py - chart.convertToPixel({ yAxisIndex: 0 }, p.val)],
        },
      }));
      // Re-order by original series index
      const ordered = [null, null, null];
      pts.forEach(p => { ordered[p.idx] = seriesUpdates[pts.indexOf(p)]; });
      chart.setOption({ series: ordered });
    } catch (_) { /* ignore if chart disposed */ }
  }, 30);

  document.getElementById("disclaimer").textContent =
    `假设费率 ${(d.fee * 100).toFixed(2)}%/年（未计 swap 融资成本及买卖价差）  ·  ` +
    `数据: yfinance ${d.und} 日线收盘价 ${d.dates[0]} 至 ${d.latest}（${d.dates.length} 个交易日）  ·  仅供学习参考，非投资建议。`;
}

// ── ETF switcher ──────────────────────────────────────────────────────────────
function show(i) {
  const pills = document.querySelectorAll(".pill");
  pills[cur].classList.remove("active");
  cur = ((i % N) + N) % N;
  pills[cur].classList.add("active");
  pills[cur].scrollIntoView({ behavior: "smooth", block: "nearest", inline: "center" });
  document.getElementById("counter").innerHTML = (cur + 1) + "&nbsp;/&nbsp;" + N;

  const etf = ETF_ORDER[cur], d = DATA[etf];
  const input = document.getElementById("dateInput");
  if (d && !d.error) {
    input.min   = d.dates[0];
    input.max   = d.latest;
    input.value = STATE[etf] || d.ipo;
  }
  document.getElementById("clamp-note").style.display = "none";
  redraw();
}

// ── Preset buttons ────────────────────────────────────────────────────────────
document.querySelectorAll(".preset-btn").forEach(btn => {
  btn.addEventListener("click", () => {
    const d = DATA[ETF_ORDER[cur]];
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
      t = p + "-01-02"; // e.g. 2022-01-02
    }
    if (t < d.dates[0]) t = d.dates[0];
    if (t > d.latest)   t = d.latest;
    input.value = t;
    redraw();
  });
});

// ── Wire-up ───────────────────────────────────────────────────────────────────
document.getElementById("dateInput").addEventListener("change", redraw);
document.querySelectorAll(".pill").forEach((p, i) => p.addEventListener("click", () => show(i)));
document.getElementById("prev").addEventListener("click", () => show(cur - 1));
document.getElementById("next").addEventListener("click", () => show(cur + 1));
document.addEventListener("keydown", e => {
  if (e.key === "ArrowRight" || e.key === "ArrowDown") show(cur + 1);
  if (e.key === "ArrowLeft"  || e.key === "ArrowUp")   show(cur - 1);
});
window.addEventListener("resize", () => chart && chart.resize());

// ── Boot ──────────────────────────────────────────────────────────────────────
chart = echarts.init(document.getElementById("chart"), null, { renderer: "canvas" });
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
        und = ETF_MAP[etf]
        parts.append(f'<button class="{cls}" title="{und}">{etf}</button>')
    return "\n      ".join(parts)


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    only = sys.argv[1].upper() if len(sys.argv) > 1 else None
    etf_order = list(ETF_MAP.keys())

    sep = "=" * 60
    print(sep)
    mode = f"单支验证: {only}" if only else f"全部 {len(etf_order)} 支"
    print(f"  交互版衰减图生成器 — {mode}")
    print(sep)

    all_data: dict = {}
    for etf, und in ETF_MAP.items():
        if only and etf != only:
            all_data[etf] = {"error": f"未在此次运行中加载 (仅运行 {only})", "und": und}
            continue

        print(f"  [{etf} → {und}] 下载中…", end=" ", flush=True)
        data, err = fetch_data(etf, und)
        if err:
            print(f"错误: {err}")
            all_data[etf] = {"error": err, "und": und}
        else:
            print(f"{len(data['dates'])} 天  ({data['ipo']} → {data['latest']})")
            all_data[etf] = data
            if only:
                print()
                verify(etf, data)

    # Assemble HTML
    pills_html     = build_pills(etf_order)
    data_json      = json.dumps(all_data, ensure_ascii=False, separators=(",", ":"))
    etf_order_json = json.dumps(etf_order)

    html = (
        _HTML
        .replace("__PILLS__",          pills_html)
        .replace("__DATA_JSON__",      data_json)
        .replace("__ETF_ORDER_JSON__", etf_order_json)
    )

    out = "index.html"
    with open(out, "w", encoding="utf-8") as fh:
        fh.write(html)

    print()
    print(sep)
    print(f"  完成 → {out}  ({len(html) // 1024} KB)")
    print(f"  打开: open {out}")
    print(sep)


if __name__ == "__main__":
    main()
