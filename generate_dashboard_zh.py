#!/usr/bin/env python3
"""
generate_dashboard_zh.py  —  股票观察列表仪表盘生成器（中文版）
用法  : python generate_dashboard_zh.py
输出  : dashboard_zh.html  （在浏览器中打开，无需服务器）
数据  : 复用 stock_cache.json 缓存，无需重新联网获取
"""

import json
import sys
from pathlib import Path
from datetime import datetime

# ── 复用原版的数据逻辑 ────────────────────────────────────────────────────────
sys.path.insert(0, str(Path(__file__).parent))
from generate_dashboard import (
    STOCK_LIST_FILE, CACHE_FILE, CACHE_MAX_AGE_HRS,
    load_cache, parse_stock_list, build_records, build_stats,
    fmt_cap,
)

OUTPUT_FILE = "dashboard_zh.html"

# ══════════════════════════════════════════════════════════════════════════════
# 板块分类（中文标签）
# ══════════════════════════════════════════════════════════════════════════════
SECTOR_META_ZH = {
    "chip_designer":    {"label": "芯片设计",     "color": "#3b82f6"},
    "chip_equipment":   {"label": "芯片设备",     "color": "#6366f1"},
    "foundry":          {"label": "晶圆代工",     "color": "#8b5cf6"},
    "packaging_ems":    {"label": "封装/代工",    "color": "#a855f7"},
    "memory_storage":   {"label": "存储器",       "color": "#0891b2"},
    "optical_photonics":{"label": "光电/光子",    "color": "#06b6d4"},
    "ai_datacenter":    {"label": "AI/数据中心",  "color": "#f97316"},
    "networking":       {"label": "网络通信",     "color": "#0ea5e9"},
    "energy_power":     {"label": "能源/电力",    "color": "#16a34a"},
    "space_aerospace":  {"label": "航天航空",     "color": "#64748b"},
    "crypto":           {"label": "加密/区块链",  "color": "#eab308"},
    "etf_semi":         {"label": "半导体ETF",    "color": "#6b7280"},
    "etf_other":        {"label": "航天/其他ETF", "color": "#9ca3af"},
    "leveraged_etf":    {"label": "2倍杠杆ETF",  "color": "#ef4444"},
    "hardware_other":   {"label": "硬件/其他",    "color": "#78716c"},
}

# ══════════════════════════════════════════════════════════════════════════════
# HTML 模板（中文版）
# ══════════════════════════════════════════════════════════════════════════════
HTML_TEMPLATE = r"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>股票观察列表仪表盘</title>
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:-apple-system,BlinkMacSystemFont,'PingFang SC','Microsoft YaHei','Segoe UI',sans-serif;background:#0f172a;color:#e2e8f0;min-height:100vh}
a{color:#60a5fa;text-decoration:none}a:hover{text-decoration:underline}

.header{background:linear-gradient(135deg,#1e293b,#0f172a);border-bottom:1px solid #1e3a5f;padding:18px 24px;display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:8px}
.header h1{font-size:1.4rem;font-weight:700;color:#f1f5f9;letter-spacing:-.3px}
.header .meta{font-size:.78rem;color:#64748b}

.kpi-strip{display:flex;gap:12px;padding:16px 24px;flex-wrap:wrap;background:#111827;border-bottom:1px solid #1e293b}
.kpi{background:#1e293b;border-radius:10px;padding:12px 16px;min-width:110px;text-align:center}
.kpi .val{font-size:1.3rem;font-weight:700;color:#f1f5f9}
.kpi .lbl{font-size:.7rem;color:#94a3b8;text-transform:uppercase;letter-spacing:.5px;margin-top:2px}

.sector-bar{padding:12px 24px;display:flex;flex-wrap:wrap;gap:7px;background:#0f172a;border-bottom:1px solid #1e293b}
.pill{cursor:pointer;border:1px solid transparent;border-radius:20px;padding:4px 12px;font-size:.75rem;font-weight:600;transition:all .15s;user-select:none;white-space:nowrap}
.pill:hover{filter:brightness(1.2)}
.pill.active{border-color:white!important;color:#fff!important}
.pill-all{background:#1e293b;color:#94a3b8;border-color:#334155}
.pill-all.active{background:#334155;border-color:#94a3b8;color:#e2e8f0}

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

.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(220px,1fr));gap:14px;padding:16px 24px 40px}

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
.detail-btn{display:block;width:100%;margin-top:10px;background:#0f172a;border:1px solid #334155;color:#94a3b8;border-radius:7px;padding:5px;font-size:.75rem;cursor:pointer;text-align:center;transition:all .12s}
.detail-btn:hover{border-color:#3b82f6;color:#60a5fa}
.no-data-overlay{position:absolute;inset:0;background:rgba(15,23,42,.6);display:flex;align-items:center;justify-content:center;border-radius:12px;font-size:.75rem;color:#64748b}

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

.empty{text-align:center;padding:60px;color:#475569}

::-webkit-scrollbar{width:6px;height:6px}
::-webkit-scrollbar-track{background:#0f172a}
::-webkit-scrollbar-thumb{background:#334155;border-radius:3px}

@media(max-width:600px){
  .grid{grid-template-columns:repeat(auto-fill,minmax(160px,1fr))}
  .kpi-strip{gap:8px}.kpi{min-width:80px;padding:8px 10px}.kpi .val{font-size:1.1rem}
}
</style>
</head>
<body>

<div class="header">
  <h1>📈 股票观察列表仪表盘</h1>
  <div class="meta" id="genDate"></div>
</div>

<div class="kpi-strip" id="kpiStrip"></div>
<div class="sector-bar" id="sectorBar"></div>

<div class="filter-bar">
  <div class="search-wrap">
    <span class="search-icon">🔍</span>
    <input type="text" id="search" placeholder="搜索股票代码或公司名称…" oninput="onFilter()">
  </div>
  <select id="selExchange" onchange="onFilter()"><option value="">全部交易所</option></select>
  <select id="selSort" onchange="onFilter()">
    <option value="ticker">代码</option>
    <option value="name">名称</option>
    <option value="px">现价</option>
    <option value="cap">市值</option>
    <option value="pe">市盈率</option>
    <option value="fpe">预期PE</option>
    <option value="chg1d">日涨跌</option>
    <option value="chg1y">年涨跌</option>
    <option value="beta">贝塔</option>
  </select>
  <div class="btn-group">
    <button class="btn active" id="sortDir" onclick="toggleSortDir()">▲</button>
  </div>
  <div class="btn-group" id="typeGroup">
    <button class="btn active" onclick="setType('all',this)">全部</button>
    <button class="btn" onclick="setType('stock',this)">股票</button>
    <button class="btn" onclick="setType('etf',this)">ETF</button>
    <button class="btn" onclick="setType('leveraged',this)">2倍ETF</button>
  </div>
  <div class="btn-group" id="specialGroup">
    <button class="btn active" onclick="setSpecial('all',this)">全部</button>
    <button class="btn" onclick="setSpecial('gainers',this)">上涨</button>
    <button class="btn" onclick="setSpecial('losers',this)">下跌</button>
    <button class="btn" onclick="setSpecial('nodata',this)">无数据</button>
  </div>
  <button class="btn" onclick="exportCSV()" style="margin-left:auto">⬇ 导出CSV</button>
</div>

<div class="result-info" id="resultInfo"></div>
<div class="grid" id="grid"></div>

<!-- 详情弹窗 -->
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
    <div class="about-section" id="mAbout"></div>
  </div>
</div>

<script>
const DATA        = __DATA__;
const STATS       = __STATS__;
const SECTOR_META = __SECTOR_META__;

const state = {
  search:  "",
  sector:  "",
  exchange:"",
  sort:    "ticker",
  sortDir: 1,
  type:    "all",
  special: "all",
};

document.getElementById("genDate").textContent = "生成时间：" + STATS.generated_at;

// KPI 卡片
(function buildKPIs(){
  const total    = STATS.total;
  const withData = STATS.with_data;
  const sectors  = Object.keys(STATS.sectors).length;
  const totalCap = DATA.filter(d=>d.cap_raw>0).reduce((a,d)=>a+d.cap_raw,0);
  const kpis = [
    {val: total,           lbl: "股票总数"},
    {val: withData,        lbl: "有数据"},
    {val: sectors,         lbl: "板块数"},
    {val: fmtCap(totalCap),lbl: "总市值"},
  ];
  document.getElementById("kpiStrip").innerHTML =
    kpis.map(k=>`<div class="kpi"><div class="val">${k.val}</div><div class="lbl">${k.lbl}</div></div>`).join("");
})();

// 板块标签
(function buildPills(){
  const bar = document.getElementById("sectorBar");
  const counts = STATS.sectors;
  let html = `<span class="pill pill-all active" onclick="setSector('',this)">全部 (${STATS.total})</span>`;
  for(const [key, meta] of Object.entries(SECTOR_META)){
    const cnt = counts[key] || 0;
    if(!cnt) continue;
    const bg = meta.color+"22", color = meta.color;
    html += `<span class="pill" style="background:${bg};color:${color};border-color:${color}44"
              onclick="setSector('${key}',this)">${meta.label} (${cnt})</span>`;
  }
  bar.innerHTML = html;
})();

// 交易所下拉
(function buildExchanges(){
  const exSet = new Set(DATA.map(d=>d.ex).filter(Boolean));
  const sel = document.getElementById("selExchange");
  [...exSet].sort().forEach(ex=>{
    const opt = document.createElement("option");
    opt.value = ex; opt.textContent = ex;
    sel.appendChild(opt);
  });
})();

// ── 筛选逻辑 ─────────────────────────────────────────────────────────────────
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
  if(state.sector)   res = res.filter(d=>d.s===state.sector);
  if(state.exchange) res = res.filter(d=>d.ex===state.exchange);

  if(state.type==="leveraged") res = res.filter(d=>d.s==="leveraged_etf");
  else if(state.type==="etf")  res = res.filter(d=>["etf_semi","etf_other","leveraged_etf"].includes(d.s));
  else if(state.type==="stock")res = res.filter(d=>!["etf_semi","etf_other","leveraged_etf"].includes(d.s));

  if(state.special==="gainers") res = res.filter(d=>d.chg1d!==null&&d.chg1d>0);
  else if(state.special==="losers")  res = res.filter(d=>d.chg1d!==null&&d.chg1d<0);
  else if(state.special==="nodata")  res = res.filter(d=>d.err);

  res.sort((a,b)=>{
    let va, vb;
    if(state.sort==="ticker")      {va=a.t;              vb=b.t;}
    else if(state.sort==="name")   {va=a.n;              vb=b.n;}
    else if(state.sort==="px")     {va=a.px||0;          vb=b.px||0;}
    else if(state.sort==="cap")    {va=a.cap_raw||0;     vb=b.cap_raw||0;}
    else if(state.sort==="pe")     {va=a.pe||0;          vb=b.pe||0;}
    else if(state.sort==="fpe")    {va=a.fpe||0;         vb=b.fpe||0;}
    else if(state.sort==="chg1d")  {va=a.chg1d??-Infinity;vb=b.chg1d??-Infinity;}
    else if(state.sort==="chg1y")  {va=a.chg1y??-Infinity;vb=b.chg1y??-Infinity;}
    else if(state.sort==="beta")   {va=a.beta||0;        vb=b.beta||0;}
    else {va=a.t; vb=b.t;}
    if(va<vb) return -1*state.sortDir;
    if(va>vb) return  1*state.sortDir;
    return 0;
  });
  return res;
}

function onFilter(){
  state.search   = document.getElementById("search").value;
  state.exchange = document.getElementById("selExchange").value;
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

// ── 渲染卡片 ─────────────────────────────────────────────────────────────────
function render(){
  const filtered = applyFilters();
  document.getElementById("resultInfo").textContent =
    `共显示 ${filtered.length} / ${DATA.length} 只`;

  const grid = document.getElementById("grid");
  if(!filtered.length){
    grid.innerHTML = `<div class="empty" style="grid-column:1/-1">
      <div style="font-size:2rem;margin-bottom:8px">🔍</div>
      <div style="font-size:.9rem">没有符合筛选条件的股票</div>
    </div>`;
    return;
  }

  grid.innerHTML = filtered.map(d=>{
    const meta    = SECTOR_META[d.s]||{label:d.s,color:"#6b7280"};
    const bgCol   = meta.color+"22", fgCol = meta.color;
    const px      = d.px!==null ? "$"+fmtNum(d.px) : "—";
    const chgHtml = fmtChgBadge(d.chg1d);
    const capStr  = d.cap||"—";
    const peStr   = d.pe  ? d.pe.toFixed(1)  : "—";
    const fpeStr  = d.fpe ? d.fpe.toFixed(1) : "—";
    const betaStr = d.beta ? d.beta.toFixed(2): "—";
    const sparkId = "spark-"+d.t;

    return `<div class="card" onclick="openDetail('${d.t}')">
      <div class="card-top">
        <div class="ticker">${d.t}</div>
        <span class="sector-badge" style="background:${bgCol};color:${fgCol}">${meta.label}</span>
      </div>
      <div class="company" title="${d.n}">${d.n}</div>
      <div class="price-row">
        <span class="price">${px}</span>
        ${chgHtml}
      </div>
      <div class="sparkline-wrap">
        <canvas class="sparkline" id="${sparkId}"></canvas>
      </div>
      <div class="card-metrics">
        <div class="metric">市值 <span>${capStr}</span></div>
        <div class="metric">市盈率 <span>${peStr}</span></div>
        <div class="metric">预期PE <span>${fpeStr}</span></div>
        <div class="metric">贝塔 <span>${betaStr}</span></div>
        <div class="metric">上市 <span>${d.ipo||"—"}</span></div>
      </div>
      ${d.err?'<div class="no-data-overlay">数据暂不可用</div>':""}
    </div>`;
  }).join("");

  requestAnimationFrame(()=>{
    filtered.forEach(d=>{
      const el = document.getElementById("spark-"+d.t);
      if(el && d.hist_px && d.hist_px.length>1)
        drawSparkline(el, d.hist_px, SECTOR_META[d.s]?.color||"#3b82f6");
    });
  });
}

// ── 价格图表（Canvas 2D）─────────────────────────────────────────────────────
function drawSparkline(canvas, prices, color){
  const dpr = window.devicePixelRatio||1;
  canvas.width  = canvas.offsetWidth  * dpr;
  canvas.height = canvas.offsetHeight * dpr;
  const ctx = canvas.getContext("2d");
  ctx.scale(dpr,dpr);
  const W=canvas.offsetWidth, H=canvas.offsetHeight;
  const mn=Math.min(...prices), mx=Math.max(...prices), range=mx-mn||1;
  const toY=v=>H-((v-mn)/range)*(H-4)-2;
  const toX=i=>(i/(prices.length-1))*W;
  ctx.beginPath();
  prices.forEach((p,i)=>i===0?ctx.moveTo(toX(i),toY(p)):ctx.lineTo(toX(i),toY(p)));
  ctx.lineTo(W,H);ctx.lineTo(0,H);ctx.closePath();
  const g=ctx.createLinearGradient(0,0,0,H);
  g.addColorStop(0,color+"66");g.addColorStop(1,color+"00");
  ctx.fillStyle=g;ctx.fill();
  ctx.beginPath();
  prices.forEach((p,i)=>i===0?ctx.moveTo(toX(i),toY(p)):ctx.lineTo(toX(i),toY(p)));
  ctx.strokeStyle=color;ctx.lineWidth=1.5;ctx.stroke();
}

function drawPriceChart(canvas, dates, prices, color){
  const dpr=window.devicePixelRatio||1;
  canvas.width=canvas.offsetWidth*dpr;canvas.height=canvas.offsetHeight*dpr;
  const ctx=canvas.getContext("2d");ctx.scale(dpr,dpr);
  const W=canvas.offsetWidth,H=canvas.offsetHeight;
  const PAD={top:20,right:20,bottom:36,left:64};
  const cW=W-PAD.left-PAD.right,cH=H-PAD.top-PAD.bottom;
  const mn=Math.min(...prices),mx=Math.max(...prices),range=mx-mn||1;
  const toY=v=>PAD.top+cH-((v-mn)/range)*cH;
  const toX=i=>PAD.left+(i/(prices.length-1||1))*cW;

  ctx.fillStyle="#0f172a";ctx.fillRect(0,0,W,H);

  ctx.strokeStyle="#1e293b";ctx.lineWidth=1;
  for(let g=0;g<=4;g++){
    const y=PAD.top+(g/4)*cH;
    ctx.beginPath();ctx.moveTo(PAD.left,y);ctx.lineTo(PAD.left+cW,y);ctx.stroke();
    ctx.fillStyle="#64748b";ctx.font="10px sans-serif";ctx.textAlign="right";
    ctx.fillText(fmtPrice(mx-(g/4)*range),PAD.left-6,y+3);
  }

  if(dates&&dates.length>1){
    const years=dates.map(d=>parseInt(d.slice(0,4)));
    const span=years[years.length-1]-years[0];
    const step=span>20?5:span>10?2:1;
    ctx.fillStyle="#64748b";ctx.font="10px sans-serif";ctx.textAlign="center";
    for(let y=Math.ceil(years[0]/step)*step;y<=years[years.length-1];y+=step){
      const idx=years.findIndex(yr=>yr>=y);
      if(idx>=0){
        const x=toX(idx);
        ctx.beginPath();ctx.strokeStyle="#1e3a5f";ctx.lineWidth=1;
        ctx.moveTo(x,PAD.top);ctx.lineTo(x,PAD.top+cH);ctx.stroke();
        ctx.fillText(y,x,H-8);
      }
    }
  }

  ctx.beginPath();
  prices.forEach((p,i)=>i===0?ctx.moveTo(toX(i),toY(p)):ctx.lineTo(toX(i),toY(p)));
  ctx.lineTo(toX(prices.length-1),PAD.top+cH);
  ctx.lineTo(PAD.left,PAD.top+cH);ctx.closePath();
  const grad=ctx.createLinearGradient(0,PAD.top,0,PAD.top+cH);
  grad.addColorStop(0,color+"55");grad.addColorStop(1,color+"05");
  ctx.fillStyle=grad;ctx.fill();

  ctx.beginPath();
  prices.forEach((p,i)=>i===0?ctx.moveTo(toX(i),toY(p)):ctx.lineTo(toX(i),toY(p)));
  ctx.strokeStyle=color;ctx.lineWidth=2;ctx.stroke();

  const lx=toX(prices.length-1),ly=toY(prices[prices.length-1]);
  ctx.beginPath();ctx.arc(lx,ly,4,0,2*Math.PI);ctx.fillStyle=color;ctx.fill();

  if(dates&&dates.length){
    ctx.fillStyle="#64748b66";ctx.font="9px sans-serif";ctx.textAlign="left";
    ctx.fillText("上市 ~"+dates[0],PAD.left+4,PAD.top+12);
  }
}

// ── 详情弹窗 ─────────────────────────────────────────────────────────────────
function openDetail(ticker){
  const d=DATA.find(x=>x.t===ticker);
  if(!d)return;
  const meta=SECTOR_META[d.s]||{label:d.s,color:"#3b82f6"};

  document.getElementById("mTitle").textContent=`${d.t}  —  ${d.n}`;
  document.getElementById("mSub").textContent=
    [d.ex,d.cur,d.country,meta.label].filter(Boolean).join("  ·  ");

  const metrics=[
    {l:"现价",      v:d.px!==null?"$"+fmtNum(d.px):"—",            cls:""},
    {l:"52周最高",  v:d.h52?"$"+fmtNum(d.h52):"—",                 cls:""},
    {l:"52周最低",  v:d.l52?"$"+fmtNum(d.l52):"—",                 cls:""},
    {l:"市值",      v:d.cap||"—",                                   cls:""},
    {l:"市盈率",    v:d.pe?d.pe.toFixed(1):"—",                     cls:""},
    {l:"预期PE",    v:d.fpe?d.fpe.toFixed(1):"—",                   cls:""},
    {l:"每股收益",  v:d.eps?"$"+d.eps.toFixed(2):"—",               cls:""},
    {l:"股息率",    v:d.dy?d.dy.toFixed(2)+"%":"—",                  cls:""},
    {l:"贝塔",      v:d.beta?d.beta.toFixed(2):"—",                 cls:""},
    {l:"日涨跌",    v:d.chg1d!==null?(d.chg1d>0?"+":"")+d.chg1d.toFixed(2)+"%":"—",
                    cls:d.chg1d>0?"pos":d.chg1d<0?"neg":""},
    {l:"月涨跌",    v:d.chg1m!==null?(d.chg1m>0?"+":"")+d.chg1m.toFixed(2)+"%":"—",
                    cls:d.chg1m>0?"pos":d.chg1m<0?"neg":""},
    {l:"年涨跌",    v:d.chg1y!==null?(d.chg1y>0?"+":"")+d.chg1y.toFixed(2)+"%":"—",
                    cls:d.chg1y>0?"pos":d.chg1y<0?"neg":""},
    {l:"上市约",    v:d.ipo||"—",                                   cls:""},
  ];
  document.getElementById("mMetrics").innerHTML=metrics.map(m=>
    `<div class="mcard"><div class="ml">${m.l}</div><div class="mv ${m.cls}">${m.v}</div></div>`
  ).join("");

  const aboutEl=document.getElementById("mAbout");
  aboutEl.innerHTML="";
  if(d.about||d.web){
    const h=document.createElement("h3");h.textContent="公司简介";
    const p=document.createElement("p");
    p.textContent=d.err?"该股票暂无可用数据。":(d.about||"暂无公司简介。");
    aboutEl.appendChild(h);aboutEl.appendChild(p);
    if(d.web){
      const w=document.createElement("div");w.className="website";
      w.innerHTML=`官网：<a href="${d.web}" target="_blank" rel="noopener">${d.web.replace(/^https?:\/\//,"")}</a>`;
      aboutEl.appendChild(w);
    }
  }

  document.getElementById("modalBg").classList.add("open");
  requestAnimationFrame(()=>{
    const canvas=document.getElementById("mainChart");
    if(d.hist_px&&d.hist_px.length>1){
      drawPriceChart(canvas,d.hist_dates,d.hist_px,meta.color);
    } else {
      const ctx=canvas.getContext("2d");
      canvas.width=canvas.offsetWidth;canvas.height=canvas.offsetHeight;
      ctx.fillStyle="#0f172a";ctx.fillRect(0,0,canvas.width,canvas.height);
      ctx.fillStyle="#475569";ctx.font="14px sans-serif";ctx.textAlign="center";
      ctx.fillText(d.err?"数据暂不可用":"暂无历史价格数据",canvas.width/2,canvas.height/2);
    }
  });
}

function closeModal(e){
  if(e&&e.target!==document.getElementById("modalBg"))return;
  document.getElementById("modalBg").classList.remove("open");
}

// ── 导出 CSV ─────────────────────────────────────────────────────────────────
function exportCSV(){
  const filtered=applyFilters();
  const hdr=["代码","名称","板块","交易所","货币","现价","市值","市盈率","预期PE","每股收益","股息率","贝塔","日涨跌%","月涨跌%","年涨跌%","上市约","国家","官网"];
  const rows=filtered.map(d=>[
    d.t,d.n,(SECTOR_META[d.s]||{}).label||d.s,d.ex,d.cur,
    d.px??"",d.cap_raw||"",d.pe??"",d.fpe??"",d.eps??"",d.dy??"",d.beta??"",
    d.chg1d??"",d.chg1m??"",d.chg1y??"",d.ipo,d.country,d.web
  ].map(v=>'"'+String(v).replace(/"/g,'""')+'"'));
  const csv=[hdr.join(","),...rows.map(r=>r.join(","))].join("\n");
  const a=document.createElement("a");
  a.href="data:text/csv;charset=utf-8,﻿"+encodeURIComponent(csv);
  a.download="股票列表_"+new Date().toISOString().slice(0,10)+".csv";
  a.click();
}

// ── 格式化工具 ────────────────────────────────────────────────────────────────
function fmtNum(n){
  if(n===null||n===undefined)return"—";
  if(n>=1000)return n.toLocaleString("zh-CN",{minimumFractionDigits:2,maximumFractionDigits:2});
  if(n>=10)  return n.toFixed(2);
  if(n>=1)   return n.toFixed(3);
  return n.toFixed(4);
}
function fmtPrice(n){
  if(n>=1000)return"$"+(n/1000).toFixed(1)+"k";
  if(n>=1)   return"$"+n.toFixed(2);
  return"$"+n.toFixed(4);
}
function fmtCap(n){
  if(!n)return"—";
  if(n>=1e12)return"$"+(n/1e12).toFixed(2)+"万亿";
  if(n>=1e9) return"$"+(n/1e9).toFixed(2)+"B";
  if(n>=1e6) return"$"+(n/1e6).toFixed(2)+"M";
  return"$"+n;
}
function fmtChgBadge(v){
  if(v===null||v===undefined)return'<span class="chg neu">—</span>';
  const cls=v>0?"pos":v<0?"neg":"neu";
  return`<span class="chg ${cls}">${v>0?"+":""}${v.toFixed(2)}%</span>`;
}

render();
</script>
</body>
</html>
"""

# ══════════════════════════════════════════════════════════════════════════════
# 主程序
# ══════════════════════════════════════════════════════════════════════════════
def main():
    print("=== 股票观察列表仪表盘生成器（中文版）===\n")

    if not Path(STOCK_LIST_FILE).exists():
        sys.exit(f"错误：未找到 {STOCK_LIST_FILE!r}")
    if not Path(CACHE_FILE).exists():
        sys.exit(f"错误：未找到缓存文件 {CACHE_FILE!r}\n请先运行 generate_dashboard.py 获取股票数据。")

    tickers = parse_stock_list(STOCK_LIST_FILE)
    cache   = load_cache(CACHE_FILE)

    print(f"从缓存加载 {len(tickers)} 只股票数据…")
    missing = [t for t in tickers if t not in cache]
    if missing:
        print(f"警告：{len(missing)} 只股票在缓存中未找到：{missing[:10]}")
        print("请先运行 generate_dashboard.py 补充缺失数据。")

    # 使用中文板块标签构建记录
    records = build_records(tickers, cache)
    stats   = build_stats(records)

    html = HTML_TEMPLATE
    html = html.replace("__DATA__",        json.dumps(records,        ensure_ascii=False))
    html = html.replace("__STATS__",       json.dumps(stats,          ensure_ascii=False))
    html = html.replace("__SECTOR_META__", json.dumps(SECTOR_META_ZH, ensure_ascii=False))

    Path(OUTPUT_FILE).write_text(html, encoding="utf-8")

    print(f"\n完成！仪表盘已生成：{OUTPUT_FILE}")
    print(f"  {stats['with_data']}/{stats['total']} 只股票有数据")
    print(f"  用浏览器打开 {OUTPUT_FILE} 即可查看\n")

if __name__ == "__main__":
    main()
