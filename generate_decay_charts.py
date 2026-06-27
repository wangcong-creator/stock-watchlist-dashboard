#!/usr/bin/env python3
"""
generate_decay_charts.py — Leveraged ETF Volatility Decay Comparison Charts
Usage  : python generate_decay_charts.py
Output : decay_charts.html  (self-contained, open in any browser)

Each of the 19 leveraged 2× ETFs gets a dual-subplot dark chart:
  ① Full history from ETF IPO: underlying 1×, naive 2×, simulated daily-reset 2×
  ② Auto-detected choppy window in past year: worst-case volatility decay
"""

import base64
import warnings
from io import BytesIO
from datetime import datetime

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import matplotlib.font_manager as fm
import numpy as np
import pandas as pd
import yfinance as yf

warnings.filterwarnings("ignore")

# ── ETF → underlying mapping ──────────────────────────────────────────────────

ETF_MAP = {
    "GGLL": "GOOG",
    "ARMG": "ARM",
    "MRVU": "MRVL",
    "NVDL": "NVDA",
    "AMDL": "AMD",
    "AVL":  "AVGO",
    "INTW": "INTC",
    "QCMU": "QCOM",
    "TXNU": "TXN",
    "ONX":  "ON",
    "SNXX": "SNDK",
    "MULL": "MU",
    "TSMX": "TSM",
    "ASMU": "ASML",
    "LRCU": "LRCX",
    "KLAG": "KLAC",
    "AMAU": "AMAT",
    "DLLL": "DELL",
    "LNOK": "NOK",
    "QLD":  "QQQ",
    "SSO":  "SPY",
    "DDM":  "DIA",
}

# Annual expense-ratio approximations (decimal)
ETF_FEES = {
    # GraniteShares 2× (~1.15 %/yr)
    "NVDL": 0.0115, "AMDL": 0.0115, "MULL": 0.0115, "INTW": 0.0115,
    "KLAG": 0.0115, "AMAU": 0.0115, "DLLL": 0.0115,
    # Leverage Shares 2× (~1.15 %/yr)
    "ARMG": 0.0115,
    # Direxion Daily 2× (~0.95 %/yr)
    "GGLL": 0.0095, "MRVU": 0.0095, "AVL":  0.0095, "QCMU": 0.0095,
    "TXNU": 0.0095, "TSMX": 0.0095, "ASMU": 0.0095, "LRCU": 0.0095,
    # Tradr 2× (~1.05 %/yr)
    "ONX":  0.0105, "SNXX": 0.0105,
    # Defiance Daily Target 2× (~0.90 %/yr)
    "LNOK": 0.0090,
    # ProShares Ultra 2× index ETFs
    "QLD":  0.0095, "SSO":  0.0089, "DDM":  0.0095,
}

LEVERAGE  = 2.0
CHOPPY_WINDOW = 20  # trading days for the bottom subplot

# ── Chart colours ─────────────────────────────────────────────────────────────

BG          = "#0d1117"
GRID_COLOR  = "#21262d"
TEXT_COLOR  = "#e5e7eb"
COLOR_1X    = "#9ca3af"   # grey  — underlying 1×
COLOR_NAIVE = "#f59e0b"   # amber — naive 2×
COLOR_SIM   = "#2dd4bf"   # teal  — simulated daily-reset 2×

# ── CJK font detection ────────────────────────────────────────────────────────

def _setup_font() -> bool:
    for name in ["PingFang SC", "Heiti SC", "STHeiti",
                 "Noto Sans CJK SC", "Arial Unicode MS"]:
        if any(f.name == name for f in fm.fontManager.ttflist):
            matplotlib.rcParams["font.family"] = name
            return True
    return False

HAS_CJK = _setup_font()

# ── Helpers ───────────────────────────────────────────────────────────────────

def pct_str(v: float) -> str:
    sign = "+" if v >= 0 else ""
    return f"{sign}{v * 100:.1f}%"


def _extract_close(hist: pd.DataFrame, ticker: str) -> pd.Series:
    """Handle both single- and multi-index yfinance DataFrames."""
    if hist.empty:
        return pd.Series(dtype=float)
    col = hist["Close"]
    if isinstance(col, pd.DataFrame):
        col = col[ticker] if ticker in col.columns else col.iloc[:, 0]
    return col.dropna()

# ── Data fetching ─────────────────────────────────────────────────────────────

def fetch_pair(etf: str, underlying: str):
    """Return (etf_close, stock_close, ipo_date_str) aligned on common days."""
    try:
        etf_hist = yf.download(etf, period="max", auto_adjust=True, progress=False)
        etf_close = _extract_close(etf_hist, etf)
        if len(etf_close) < 30:
            print(f"  WARNING: insufficient ETF data ({len(etf_close)} rows)")
            return None, None, None

        ipo_date = etf_close.index[0]

        stock_hist = yf.download(
            underlying, start=ipo_date, auto_adjust=True, progress=False
        )
        stock_close = _extract_close(stock_hist, underlying)
        if len(stock_close) < 30:
            print(f"  WARNING: insufficient underlying data ({len(stock_close)} rows)")
            return None, None, None

        common = etf_close.index.intersection(stock_close.index)
        if len(common) < 30:
            print(f"  WARNING: only {len(common)} common trading days")
            return None, None, None

        return (
            etf_close.loc[common],
            stock_close.loc[common],
            ipo_date.strftime("%Y-%m-%d"),
        )
    except Exception as exc:
        print(f"  ERROR: {exc}")
        return None, None, None

# ── Simulation ────────────────────────────────────────────────────────────────

def simulate(stock: pd.Series, annual_fee: float):
    """Return (one_x, naive_2x, daily_reset_2x), each normalised to start at 1.0."""
    s = stock.values.astype(float)
    n = len(s)
    one_x = s / s[0]
    naive = 1.0 + LEVERAGE * (s / s[0] - 1.0)
    daily_fee = annual_fee / 252.0
    dr = np.ones(n)
    for i in range(1, n):
        r = s[i] / s[i - 1] - 1.0
        dr[i] = dr[i - 1] * (1.0 + LEVERAGE * r - daily_fee)
    idx = stock.index
    return pd.Series(one_x, index=idx), pd.Series(naive, index=idx), pd.Series(dr, index=idx)

# ── Choppy window detection ───────────────────────────────────────────────────

def find_choppy_window(stock: pd.Series, window: int = CHOPPY_WINDOW):
    """Identify the highest-volatility window relative to net return in the last year.
    Returns (start_pos, end_pos) as integer positions into the full series."""
    look_back = min(252, len(stock) - window - 2)
    if look_back < window:
        return max(0, len(stock) - window - 1), len(stock) - 1

    recent_start = len(stock) - look_back - window
    recent = stock.iloc[recent_start:]
    daily_ret = recent.pct_change().dropna()
    m = len(daily_ret)

    best_score, best_i = -1.0, 0
    for i in range(m - window):
        seg = daily_ret.iloc[i : i + window]
        total_abs = seg.abs().sum()
        net = abs((1.0 + seg).prod() - 1.0) + 0.001
        score = total_abs / net
        if score > best_score:
            best_score, best_i = score, i

    full_start = recent_start + best_i + 1
    full_end = min(full_start + window, len(stock) - 1)
    return full_start, full_end

# ── Smart right-edge annotation ───────────────────────────────────────────────

def _annotate_right(ax, n_pts: int, items: list, is_log: bool):
    """Place right-edge value labels with vertical collision avoidance.
    items: [(val, label_str, color), ...]  (any order)
    """
    items_sorted = sorted(items, key=lambda x: x[0])
    ylo, yhi = ax.get_ylim()

    if is_log:
        lo_l = np.log10(max(ylo, 1e-9))
        hi_l = np.log10(max(yhi, 1e-6))
        span = hi_l - lo_l or 1.0
        to_norm   = lambda v: (np.log10(max(v, 1e-9)) - lo_l) / span
        from_norm = lambda nn: 10 ** (lo_l + nn * span)
    else:
        span = (yhi - ylo) or 1.0
        to_norm   = lambda v: (v - ylo) / span
        from_norm = lambda nn: ylo + nn * span

    min_gap = 0.075  # 7.5 % of axis height per label
    norms = [max(0.02, to_norm(v)) for v, l, c in items_sorted]

    # Push neighbours apart (upward)
    adj = [norms[0]]
    for i in range(1, len(norms)):
        adj.append(max(norms[i], adj[-1] + min_gap))

    # If the top label is above 0.97, shift all downward
    if adj[-1] > 0.97:
        shift = adj[-1] - 0.97
        adj = [a - shift for a in adj]

    adj_y = [from_norm(a) for a in adj]

    # Offset text 2% of x-range to the right of the last data point
    x_text = n_pts - 1 + max(2, n_pts * 0.02)

    for (orig_v, label, color), ay in zip(items_sorted, adj_y):
        needs_arrow = abs(to_norm(ay) - to_norm(max(orig_v, 1e-9))) > 0.04
        kw: dict = {}
        if needs_arrow:
            kw["arrowprops"] = dict(
                arrowstyle="-", color=color, lw=0.8,
                connectionstyle="arc3,rad=0",
            )
        ax.annotate(
            label,
            xy=(n_pts - 1, orig_v),
            xytext=(x_text, ay),
            xycoords="data", textcoords="data",
            color=color, fontsize=9.5, fontweight="bold",
            va="center", ha="left",
            annotation_clip=False,
            **kw,
        )


def _annotate_right_linear(ax, n_pts: int, items: list):
    """Simplified right-edge annotations for the (linear-scale) bottom subplot."""
    items_sorted = sorted(items, key=lambda x: x[0])
    ylo, yhi = ax.get_ylim()
    span = (yhi - ylo) or 1.0
    to_norm   = lambda v: (v - ylo) / span
    from_norm = lambda nn: ylo + nn * span

    min_gap = 0.09
    norms = [max(0.02, to_norm(v)) for v, l, c in items_sorted]
    adj = [norms[0]]
    for i in range(1, len(norms)):
        adj.append(max(norms[i], adj[-1] + min_gap))
    if adj[-1] > 0.97:
        shift = adj[-1] - 0.97
        adj = [a - shift for a in adj]

    adj_y = [from_norm(a) for a in adj]
    x_text = n_pts - 1 + max(1, n_pts * 0.05)

    for (orig_v, label, color), ay in zip(items_sorted, adj_y):
        needs_arrow = abs(to_norm(ay) - to_norm(orig_v)) > 0.05
        kw: dict = {}
        if needs_arrow:
            kw["arrowprops"] = dict(
                arrowstyle="-", color=color, lw=0.7,
                connectionstyle="arc3,rad=0",
            )
        ax.annotate(
            label,
            xy=(n_pts - 1, orig_v),
            xytext=(x_text, ay),
            xycoords="data", textcoords="data",
            color=color, fontsize=9, fontweight="bold",
            va="center", ha="left",
            annotation_clip=False,
            **kw,
        )

# ── Chart rendering ───────────────────────────────────────────────────────────

def make_chart(
    etf: str, underlying: str,
    stock: pd.Series,
    one_x: pd.Series, naive: pd.Series, daily_reset: pd.Series,
    ipo_str: str, annual_fee: float,
) -> bytes:
    """Render dual-subplot dark chart and return PNG bytes."""

    fig = plt.figure(figsize=(14, 10), facecolor=BG)
    gs = gridspec.GridSpec(
        2, 1, height_ratios=[2, 1], hspace=0.52,
        left=0.07, right=0.91, top=0.85, bottom=0.10,
    )
    ax1 = fig.add_subplot(gs[0])
    ax2 = fig.add_subplot(gs[1])

    for ax in (ax1, ax2):
        ax.set_facecolor(BG)
        ax.tick_params(colors=TEXT_COLOR, labelsize=9)
        ax.grid(True, color=GRID_COLOR, linewidth=0.6, alpha=0.9)
        for sp in ax.spines.values():
            sp.set_color(GRID_COLOR)
            sp.set_linewidth(0.5)

    # ─────────────────────────── ① Full history ───────────────────────────────
    n = len(one_x)
    x = np.arange(n)

    use_log = naive.min() > 0.05 and daily_reset.min() > 0.01
    plot_fn = ax1.semilogy if use_log else ax1.plot

    plot_fn(x, one_x.values,      color=COLOR_1X,    linewidth=1.4,
            label=f"{underlying} 正股 (1×)")
    plot_fn(x, naive.values,       color=COLOR_NAIVE, linewidth=1.6,
            linestyle="--", label="naive 2倍累计 (区间涨幅×2)")
    plot_fn(x, daily_reset.values, color=COLOR_SIM,   linewidth=2.0,
            label=f"每日重置 2倍 (模拟 {etf})")

    # End-of-line dots
    for val, col in [(one_x.iloc[-1], COLOR_1X),
                     (naive.iloc[-1], COLOR_NAIVE),
                     (daily_reset.iloc[-1], COLOR_SIM)]:
        if val > 0.001:
            ax1.scatter([n - 1], [val], color=col, s=45, zorder=6, clip_on=False)

    # Smart collision-avoidant annotations at right edge
    _annotate_right(ax1, n, [
        (one_x.iloc[-1],      pct_str(one_x.iloc[-1] - 1),      COLOR_1X),
        (naive.iloc[-1],      pct_str(naive.iloc[-1] - 1),       COLOR_NAIVE),
        (daily_reset.iloc[-1], pct_str(daily_reset.iloc[-1] - 1), COLOR_SIM),
    ], use_log)

    # Legend: lower right — lines start clustered near 1.0 at left; lower-right is clear
    ax1.legend(loc="lower right", framealpha=0.0, labelcolor=TEXT_COLOR,
               fontsize=9, handlelength=2.2)

    # Trend insight box: upper LEFT (opposite corner from legend)
    ratio = daily_reset.iloc[-1] / max(naive.iloc[-1], 0.001)
    if ratio > 1:
        box_msg = f"强趋势 → 正向复利:\n每日重置 2倍达到 naive 2倍的 {ratio:.1f}×"
        box_fc = "#1a4a3a"
    else:
        box_msg = f"震荡衰减:\n每日重置 2倍 = naive 2倍 × {ratio:.2f}"
        box_fc = "#4a1a1a"

    ax1.text(
        0.02, 0.97, box_msg, transform=ax1.transAxes,
        color=TEXT_COLOR, fontsize=8.5, va="top", ha="left",
        bbox=dict(boxstyle="round,pad=0.4", facecolor=box_fc, alpha=0.80, edgecolor="none"),
        zorder=10,
    )

    ax1.set_title(
        f"① 从发行以来 — {ipo_str} 至今  ({n} 个交易日)",
        color="#93c5fd", fontsize=10, pad=8,
    )
    ax1.set_ylabel(
        "净值 (起点=1, 对数轴)" if use_log else "净值 (起点=1)",
        color=TEXT_COLOR, fontsize=9,
    )

    # ─────────────────── ② Auto-detected choppy window ────────────────────────
    wi0, wi1 = find_choppy_window(stock)
    w_stock = stock.iloc[wi0 : wi1 + 1]
    ws = w_stock.values.astype(float)
    m = len(ws)

    w_1x    = (ws / ws[0] - 1.0) * 100.0
    w_naive = LEVERAGE * (ws / ws[0] - 1.0) * 100.0

    daily_fee = annual_fee / 252.0
    w_dr = np.zeros(m)
    v = 1.0
    for i in range(1, m):
        r = ws[i] / ws[i - 1] - 1.0
        v = v * (1.0 + LEVERAGE * r - daily_fee)
        w_dr[i] = (v - 1.0) * 100.0

    xw = np.arange(m)
    d0 = w_stock.index[0].strftime("%Y-%m-%d")
    d1 = w_stock.index[-1].strftime("%Y-%m-%d")
    decay_gap = w_dr[-1] - w_naive[-1]

    ax2.plot(xw, w_1x,    color=COLOR_1X,    linewidth=1.4, label=f"{underlying} 正股")
    ax2.plot(xw, w_naive, color=COLOR_NAIVE, linewidth=1.6, linestyle="--", label="naive 2倍")
    ax2.plot(xw, w_dr,    color=COLOR_SIM,   linewidth=2.0, label="每日重置 2倍 (模拟)")
    ax2.axhline(0, color=GRID_COLOR, linewidth=0.8)

    # Smart annotations for bottom subplot
    _annotate_right_linear(ax2, m, [
        (w_1x[-1],    pct_str(w_1x[-1] / 100),    COLOR_1X),
        (w_naive[-1], pct_str(w_naive[-1] / 100),  COLOR_NAIVE),
        (w_dr[-1],    pct_str(w_dr[-1] / 100),     COLOR_SIM),
    ])

    decay_sign = "+" if decay_gap >= 0 else ""
    ax2.set_title(
        f"② 震荡窗口 {d0} → {d1}  |  每日重置 2倍偏离 naive 2倍: {decay_sign}{decay_gap:.1f} pct",
        color="#93c5fd", fontsize=9.5, pad=8,
    )
    ax2.set_ylabel("区间累计收益率 (%)", color=TEXT_COLOR, fontsize=9)
    ax2.set_xlabel(f"交易日 (第 0 至第 {m-1} 日)", color=TEXT_COLOR, fontsize=9)

    # Legend: upper left — lines start at 0% so they're all at the top on day-0;
    # lower-left is where lines dip (for V-shaped windows) — use 'best'
    ax2.legend(loc="best", framealpha=0.0, labelcolor=TEXT_COLOR, fontsize=8.5,
               handlelength=2.0)

    # ── Figure title (suptitle) ───────────────────────────────────────────────
    fig.suptitle(
        f"{etf}  衰减对比:每日重置 2倍杠杆 ETF  vs  「naive 2倍累计」\n"
        f"以 {underlying} 真实日线模拟  ·  假设费率 {annual_fee * 100:.2f}%/年  ·  未计入 swap 融资成本与买卖价差",
        color=TEXT_COLOR, fontsize=10, fontweight="bold", y=0.97,
    )

    # Footer
    fig.text(
        0.5, 0.013,
        f"数据: yfinance {underlying} 日线收盘价 {ipo_str} 至今 ({n} 交易日)。"
        "每日重置模拟不含 swap 融资成本及买卖价差,实际 ETF 衰减通常更大。仅供学习参考,非投资建议。",
        ha="center", color="#6b7280", fontsize=7.5,
    )

    buf = BytesIO()
    plt.savefig(buf, format="png", dpi=150, bbox_inches="tight", facecolor=BG)
    plt.close(fig)
    buf.seek(0)
    return buf.read()

# ── HTML templates ────────────────────────────────────────────────────────────

# Double braces {{ }} escape literal { } in Python format strings.
_HTML = """\
<!DOCTYPE html>
<html lang="zh">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>杠杆 ETF 衰减对比图</title>
  <style>
    *{{box-sizing:border-box;margin:0;padding:0}}
    html,body{{height:100%;overflow:hidden;background:#0d1117;color:#e5e7eb;
               font-family:-apple-system,'PingFang SC',sans-serif}}
    .app{{display:flex;flex-direction:column;height:100vh}}

    /* ── Header ── */
    header{{flex-shrink:0;padding:10px 20px 8px;border-bottom:1px solid #21262d;
            background:#161b22;display:flex;align-items:center;gap:14px;flex-wrap:wrap}}
    header h1{{font-size:1rem;color:#f3f4f6;white-space:nowrap}}
    .pills{{display:flex;flex-wrap:wrap;gap:5px;align-items:center;flex:1}}
    .pill{{background:transparent;border:1px solid #30363d;color:#8b949e;
           padding:3px 11px;border-radius:12px;cursor:pointer;font-size:.78rem;
           transition:all .15s;white-space:nowrap;font-family:inherit}}
    .pill:hover{{border-color:#58a6ff;color:#58a6ff}}
    .pill.active{{background:#1c3452;border-color:#58a6ff;color:#79c0ff;font-weight:600}}

    /* ── Chart viewer ── */
    .viewer{{flex:1;overflow:hidden;display:flex;align-items:center;
             justify-content:center;background:#0d1117;padding:6px 10px}}
    .panel{{display:none;flex-direction:column;align-items:center;
            justify-content:center;width:100%;height:100%}}
    .panel.active{{display:flex}}
    .panel img{{max-width:100%;max-height:100%;object-fit:contain;
                display:block;border-radius:6px}}
    .fail-msg{{color:#f87171;font-size:1.1rem;text-align:center;padding:40px 20px}}

    /* ── Navigation bar ── */
    .nav-bar{{flex-shrink:0;display:flex;align-items:center;gap:14px;
              padding:7px 20px;border-top:1px solid #21262d;background:#161b22;
              justify-content:center}}
    .nav-btn{{background:#21262d;border:1px solid #30363d;color:#c9d1d9;
              padding:5px 18px;border-radius:6px;cursor:pointer;font-size:.85rem;
              font-family:inherit;transition:background .15s}}
    .nav-btn:hover{{background:#2d333b}}
    .counter{{color:#8b949e;font-size:.85rem;min-width:55px;text-align:center;
              font-variant-numeric:tabular-nums}}
    .hint{{color:#484f58;font-size:.72rem}}
  </style>
</head>
<body>
<div class="app">
  <!-- Header with title + pill nav -->
  <header>
    <h1>杠杆 ETF 衰减对比图</h1>
    <div class="pills" id="pills">
{pills_html}
    </div>
  </header>

  <!-- Full-screen chart area -->
  <div class="viewer" id="viewer">
{panels_html}
  </div>

  <!-- Prev / counter / Next -->
  <div class="nav-bar">
    <button class="nav-btn" id="prev">&#8592; 上一个</button>
    <span class="counter" id="counter">1&nbsp;/&nbsp;{total}</span>
    <button class="nav-btn" id="next">下一个 &#8594;</button>
    <span class="hint">&#9095; 方向键切换</span>
  </div>
</div>

<script>
  const pills  = Array.from(document.querySelectorAll('.pill'));
  const panels = Array.from(document.querySelectorAll('.panel'));
  const ctr    = document.getElementById('counter');
  let cur = 0;
  const N = panels.length;

  function show(i) {{
    pills[cur].classList.remove('active');
    panels[cur].classList.remove('active');
    cur = ((i % N) + N) % N;
    pills[cur].classList.add('active');
    panels[cur].classList.add('active');
    ctr.innerHTML = (cur + 1) + '&nbsp;/&nbsp;' + N;
    pills[cur].scrollIntoView({{behavior:'smooth', block:'nearest', inline:'center'}});
  }}

  pills.forEach((p, i) => p.addEventListener('click', () => show(i)));
  document.getElementById('prev').addEventListener('click', () => show(cur - 1));
  document.getElementById('next').addEventListener('click', () => show(cur + 1));
  document.addEventListener('keydown', e => {{
    if (e.key === 'ArrowRight' || e.key === 'ArrowDown')  show(cur + 1);
    if (e.key === 'ArrowLeft'  || e.key === 'ArrowUp')    show(cur - 1);
  }});
</script>
</body>
</html>"""

_PILL = '      <button class="pill" title="{und}">{etf}</button>'

_PANEL = """\
    <div class="panel" id="p-{etf}">
      <img src="data:image/png;base64,{b64}" alt="{etf} decay chart">
    </div>"""

_PANEL_FAIL = """\
    <div class="panel" id="p-{etf}">
      <div class="fail-msg">
        &#9888;&nbsp; {etf} &rarr; {und}<br>
        <span style="font-size:.9rem;color:#9ca3af">{reason}</span>
      </div>
    </div>"""

# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    sep = "=" * 64
    print(sep)
    total_pairs = len(ETF_MAP)
    print(f"  Leveraged ETF Decay Chart Generator  ({total_pairs} pairs)")
    print(sep)
    print(f"  CJK font: {'enabled' if HAS_CJK else 'not found — using system default'}")
    print()

    pill_parts:  list[str] = []
    panel_parts: list[str] = []
    success_count = 0

    for idx, (etf, und) in enumerate(ETF_MAP.items(), 1):
        fee = ETF_FEES.get(etf, 0.0115)
        print(f"[{idx:2d}/{total_pairs}] {etf} → {und}  (fee {fee*100:.2f}%/yr)")

        etf_px, stock_px, ipo = fetch_pair(etf, und)

        pill_parts.append(_PILL.format(etf=etf, und=und))

        if etf_px is None:
            panel_parts.append(_PANEL_FAIL.format(
                etf=etf, und=und, reason="yfinance 数据不足 (<30 天)"
            ))
            continue

        one_x, naive, dr = simulate(stock_px, fee)
        days = len(stock_px)
        print(
            f"       {days} days  |  1×={pct_str(one_x.iloc[-1]-1)}"
            f"  naive={pct_str(naive.iloc[-1]-1)}"
            f"  sim={pct_str(dr.iloc[-1]-1)}"
        )

        png = make_chart(etf, und, stock_px, one_x, naive, dr, ipo, fee)
        b64 = base64.b64encode(png).decode()
        panel_parts.append(_PANEL.format(etf=etf, b64=b64))
        success_count += 1
        print(f"       chart rendered  ({len(png)//1024} KB PNG)")

    # Mark the first pill/panel as active
    if pill_parts:
        pill_parts[0] = pill_parts[0].replace('class="pill"', 'class="pill active"')
    if panel_parts:
        panel_parts[0] = panel_parts[0].replace('class="panel"', 'class="panel active"')

    html = _HTML.format(
        pills_html="\n".join(pill_parts),
        panels_html="\n".join(panel_parts),
        total=len(panel_parts),
    )

    out = "decay_charts.html"
    with open(out, "w", encoding="utf-8") as fh:
        fh.write(html)

    print()
    print(sep)
    print(f"  Done!  {success_count}/{total_pairs} charts generated  →  {out}")
    print(f"  Open:  open {out}")
    print(sep)


if __name__ == "__main__":
    main()
