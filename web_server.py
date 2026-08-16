import asyncio
import json
import time
import os
import numpy as np
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, PlainTextResponse, Response

app = FastAPI(title="Quant Squeeze Terminal")

connected_sockets = set()
paper_positions = []
pos_counter = 1

spot_prices = {"BTCUSDT": 65000.0, "ETHUSDT": 3450.0, "XAUTUSDT": 2380.0}

HTML_CONTENT = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="google-site-verification" content="abcdef12345..." />
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Quant Store — Discover</title>
  <script src="https://cdn.tailwindcss.com"></script>
  <script src="https://cdn.plot.ly/plotly-2.32.0.min.js"></script>
  <style>
    body {
      font-family: -apple-system, BlinkMacSystemFont, "SF Pro Display", "SF Pro Text", system-ui, sans-serif;
      -webkit-font-smoothing: antialiased;
      background: linear-gradient(135deg, #c7d2fe 0%, #e0e7ff 40%, #f1f5f9 100%);
    }
    .mono { font-family: "SF Mono", Menlo, Monaco, monospace; }
    .appstore-window {
      background: #ffffff;
      box-shadow: 0 35px 70px -15px rgba(0, 0, 0, 0.25), 0 0 1px rgba(0, 0, 0, 0.2);
    }
    .appstore-sidebar {
      background: #f5f5f7;
      border-right: 1px solid #e5e5e7;
    }
    .card-banner {
      background: linear-gradient(135deg, #1e1b4b 0%, #312e81 35%, #ec4899 75%, #f43f5e 100%);
    }
  </style>
</head>
<body class="text-[#1d1d1f] h-screen p-5 flex items-center justify-center overflow-hidden select-none">
  <div class="w-full h-full max-w-6xl max-h-[92vh] appstore-window rounded-2xl flex overflow-hidden">
    <aside class="w-60 appstore-sidebar flex flex-col justify-between p-4 flex-shrink-0">
      <div class="space-y-4">
        <div class="flex items-center space-x-2 pt-1 pb-1 px-1">
          <div class="w-3 h-3 rounded-full bg-[#ff5f56] border border-[#e0443e]"></div>
          <div class="w-3 h-3 rounded-full bg-[#ffbd2e] border border-[#dea123]"></div>
          <div class="w-3 h-3 rounded-full bg-[#27c93f] border border-[#1aab29]"></div>
        </div>
        <div class="relative">
          <input type="text" placeholder="Search" class="w-full bg-[#e8e8ed] text-xs rounded-lg pl-3 pr-3 py-1.5 focus:outline-none placeholder-gray-500 font-medium">
        </div>
        <nav class="space-y-0.5 text-[13px] font-medium pt-1">
          <button onclick="switchTab('tab-discover')" id="nav-discover" class="w-full flex items-center space-x-3 px-3 py-1.5 rounded-lg bg-[#e8e8ed] text-[#007aff] font-semibold transition">
            <span>Discover</span>
          </button>
          <button onclick="switchTab('tab-gex')" id="nav-gex" class="w-full flex items-center space-x-3 px-3 py-1.5 rounded-lg text-gray-700 hover:bg-[#e8e8ed] transition">
            <span>3D GEX Mesh</span>
          </button>
          <button onclick="switchTab('tab-positions')" id="nav-positions" class="w-full flex items-center space-x-3 px-3 py-1.5 rounded-lg text-gray-700 hover:bg-[#e8e8ed] transition">
            <span>Live Positions</span>
          </button>
        </nav>
      </div>
      <div class="flex items-center space-x-2.5 px-2 py-2 pt-3 border-t border-gray-200">
        <div class="w-7 h-7 rounded-full bg-[#8e8e93] text-white text-[11px] font-bold flex items-center justify-center">AD</div>
        <div class="text-xs font-semibold text-gray-800">aarwin dalsro</div>
      </div>
    </aside>
    <main class="flex-1 p-8 overflow-y-auto bg-white space-y-6">
      <div id="tab-discover" class="space-y-6">
        <h1 class="text-3xl font-extrabold tracking-tight text-gray-900">Discover</h1>
        <div class="card-banner rounded-2xl p-7 text-white flex flex-col justify-between min-h-[240px] shadow-lg">
          <div>
            <div class="text-[11px] font-extrabold tracking-wider uppercase text-pink-200 mb-1">ESSENTIALS</div>
            <h2 class="text-2xl font-black leading-tight mb-2">3-SAC Squeeze Terminal</h2>
            <p class="text-xs text-indigo-100 max-w-md">Real-time dealer Gamma surface, order flow acceleration, and short-covering execution engine.</p>
          </div>
          <div class="flex items-center justify-between pt-4">
            <div class="text-xs font-medium text-pink-100">Live Engine Connected</div>
            <button onclick="switchTab('tab-gex')" class="px-5 py-2 rounded-full bg-white text-gray-900 font-bold text-xs shadow-md">Open 3D Mesh</button>
          </div>
        </div>
        <div class="grid grid-cols-1 md:grid-cols-3 gap-5">
          <div class="bg-[#f5f5f7] p-5 rounded-2xl flex flex-col justify-between space-y-4">
            <div>
              <div class="text-[10px] font-bold text-gray-400 uppercase">0.24Δ Squeeze</div>
              <div class="text-base font-bold text-gray-900 mt-0.5">Bitcoin Core</div>
              <div class="text-xs text-gray-500 mt-1 mono">Spot: <b id="d-btc" class="text-gray-900">--</b></div>
            </div>
            <button onclick="buySqueeze('BTCUSDT')" class="w-full py-1.5 bg-[#e8e8ed] hover:bg-[#007aff] hover:text-white text-[#007aff] font-bold text-xs rounded-full transition">GET CALL</button>
          </div>
          <div class="bg-[#f5f5f7] p-5 rounded-2xl flex flex-col justify-between space-y-4">
            <div>
              <div class="text-[10px] font-bold text-gray-400 uppercase">High-Beta Gamma</div>
              <div class="text-base font-bold text-gray-900 mt-0.5">Ethereum Call</div>
              <div class="text-xs text-gray-500 mt-1 mono">Spot: <b id="d-eth" class="text-gray-900">--</b></div>
            </div>
            <button onclick="buySqueeze('ETHUSDT')" class="w-full py-1.5 bg-[#e8e8ed] hover:bg-[#007aff] hover:text-white text-[#007aff] font-bold text-xs rounded-full transition">GET CALL</button>
          </div>
          <div class="bg-[#f5f5f7] p-5 rounded-2xl flex flex-col justify-between space-y-4">
            <div>
              <div class="text-[10px] font-bold text-gray-400 uppercase">Spring Flow</div>
              <div class="text-base font-bold text-gray-900 mt-0.5">Gold Squeeze</div>
              <div class="text-xs text-gray-500 mt-1 mono">Spot: <b id="d-xaut" class="text-gray-900">--</b></div>
            </div>
            <button onclick="buySqueeze('XAUTUSDT')" class="w-full py-1.5 bg-[#e8e8ed] hover:bg-[#007aff] hover:text-white text-[#007aff] font-bold text-xs rounded-full transition">GET CALL</button>
          </div>
        </div>
      </div>
      <div id="tab-gex" class="hidden space-y-4">
        <h1 class="text-2xl font-bold text-gray-900">3D Net Gamma Exposure</h1>
        <div class="bg-[#f5f5f7] p-4 rounded-2xl"><div id="plotly-3d" class="w-full h-[420px]"></div></div>
      </div>
      <div id="tab-positions" class="hidden space-y-4">
        <h1 class="text-2xl font-bold text-gray-900">Active Squeeze Positions</h1>
        <div class="bg-[#f5f5f7] rounded-2xl overflow-hidden">
          <table class="w-full text-left text-xs">
            <thead class="bg-[#ebebeb] text-gray-500 font-semibold">
              <tr>
                <th class="py-3 px-4">ID</th><th class="py-3 px-4">ASSET</th><th class="py-3 px-4">STRIKE</th>
                <th class="py-3 px-4 text-right">ENTRY</th><th class="py-3 px-4 text-right">MARK</th>
                <th class="py-3 px-4 text-right">ROI (%)</th><th class="py-3 px-4 text-right">PNL (INR)</th><th class="py-3 px-4 text-center">HOLD</th>
              </tr>
            </thead>
            <tbody id="pos-table" class="divide-y divide-gray-200 mono">
              <tr><td colspan="8" class="py-8 text-center text-gray-400">No open positions. Click GET CALL in Discover.</td></tr>
            </tbody>
          </table>
        </div>
      </div>
    </main>
  </div>
  <script>
    const ws = new WebSocket(`${window.location.protocol === 'https:' ? 'wss:' : 'ws:'}//${window.location.host}/ws/stream`);
    let plotlyInit = false;
    ws.onmessage = (e) => {
      const data = JSON.parse(e.data);
      document.getElementById('d-btc').textContent = `$${data.prices.BTCUSDT.toLocaleString()}`;
      document.getElementById('d-eth').textContent = `$${data.prices.ETHUSDT.toLocaleString()}`;
      document.getElementById('d-xaut').textContent = `$${data.prices.XAUTUSDT.toLocaleString()}`;
      const surfaceTrace = {
        z: data.gex_3d.matrix, x: data.gex_3d.strikes, y: data.gex_3d.expirations,
        type: 'surface', colorscale: [[0.0, '#f43f5e'], [0.5, '#e0e7ff'], [1.0, '#007aff']], showscale: false
      };
      const layout = {
        paper_bgcolor: 'rgba(0,0,0,0)', plot_bgcolor: 'rgba(0,0,0,0)', margin: { l: 0, r: 0, b: 0, t: 0 },
        scene: { xaxis: { title: 'Strike' }, yaxis: { title: 'DTE' }, zaxis: { title: 'Gamma' } }
      };
      if (!plotlyInit) { Plotly.newPlot('plotly-3d', [surfaceTrace], layout, { responsive: true }); plotlyInit = true; }
      else { Plotly.react('plotly-3d', [surfaceTrace], layout); }
      const tbody = document.getElementById('pos-table');
      if (!data.positions || data.positions.length === 0) {
        tbody.innerHTML = '<tr><td colspan="8" class="py-8 text-center text-gray-400">No open positions.</td></tr>';
      } else {
        tbody.innerHTML = '';
        data.positions.forEach(p => {
          const isProf = p.pnl_inr >= 0;
          const row = document.createElement('tr');
          row.innerHTML = `
            <td class="py-3 px-4 text-gray-400 font-bold">${p.id}</td>
            <td class="py-3 px-4 font-bold text-[#007aff]">${p.symbol}</td>
            <td class="py-3 px-4 text-gray-800">${p.strike}</td>
            <td class="py-3 px-4 text-right text-gray-500">$${p.entry_prem.toFixed(3)}</td>
            <td class="py-3 px-4 text-right font-bold text-gray-900">$${p.curr_prem.toFixed(3)}</td>
            <td class="py-3 px-4 text-right font-bold ${isProf ? 'text-emerald-600' : 'text-rose-600'}">${isProf ? '+' : ''}${p.roi_pct}%</td>
            <td class="py-3 px-4 text-right font-bold ${isProf ? 'text-emerald-600' : 'text-rose-600'}">₹${isProf ? '+' : ''}${p.pnl_inr.toLocaleString('en-IN')}</td>
            <td class="py-3 px-4 text-center text-gray-400">${p.hold_time}s</td>
          `;
          tbody.appendChild(row);
        });
      }
    };
    function buySqueeze(sym) { if (ws && ws.readyState === WebSocket.OPEN) ws.send(JSON.stringify({ action: 'SHORT_COVERING_ORDER', symbol: sym, contracts: 1 })); }
    function switchTab(tabId) {
      ['tab-discover', 'tab-gex', 'tab-positions'].forEach(t => document.getElementById(t).classList.add('hidden'));
      document.getElementById(tabId).classList.remove('hidden');
      ['nav-discover', 'nav-gex', 'nav-positions'].forEach(n => document.getElementById(n).className = 'w-full flex items-center space-x-3 px-3 py-1.5 rounded-lg text-gray-700 hover:bg-[#e8e8ed] transition');
      const activeNav = tabId === 'tab-discover' ? 'nav-discover' : (tabId === 'tab-gex' ? 'nav-gex' : 'nav-positions');
      document.getElementById(activeNav).className = 'w-full flex items-center space-x-3 px-3 py-1.5 rounded-lg bg-[#e8e8ed] text-[#007aff] font-semibold transition';
      if (tabId === 'tab-gex') window.dispatchEvent(new Event('resize'));
    }
  </script>
</body>
</html>
"""

def get_3d_gamma(spot):
    strikes = np.linspace(spot * 0.85, spot * 1.15, 15).tolist()
    expirations = ["0-DTE", "1-DTE", "3-DTE", "7-DTE"]
    z_matrix = []
    for exp in expirations:
        row = []
        for k in strikes:
            val = ((k - spot) / spot) * 1000
            row.append(round(val, 2))
        z_matrix.append(row)
    return {"strikes": [round(s, 1) for s in strikes], "expirations": expirations, "matrix": z_matrix}

@app.get("/google8123fcf904bd2735.html", response_class=PlainTextResponse)
async def get_dashboard():
    return HTMLResponse(content=HTML_CONTENT)

@app.get("/robots.txt", response_class=PlainTextResponse)
async def robots():
    return "User-agent: *\nAllow: /\nSitemap: /sitemap.xml"

@app.get("/sitemap.xml")
async def sitemap():
    xml_content = """<?xml version="1.0" encoding="UTF-8"?>
    <urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
      <url><loc>/</loc><changefreq>daily</changefreq><priority>1.0</priority></url>
    </urlset>"""
    return Response(content=xml_content, media_type="application/xml")

@app.websocket("/ws/stream")
async def websocket_endpoint(websocket: WebSocket):
    global pos_counter
    await websocket.accept()
    connected_sockets.add(websocket)
    try:
        while True:
            msg = await websocket.receive_text()
            data = json.loads(msg)
            if data.get("action") == "SHORT_COVERING_ORDER":
                sym = data.get("symbol", "BTCUSDT")
                spot = spot_prices[sym]
                paper_positions.append({
                    "id": f"SQZ_{pos_counter}",
                    "symbol": sym,
                    "strike": f"{round(spot * 1.015, 1)}C",
                    "entry_prem": round(spot * 0.00065, 3),
                    "entry_spot": spot,
                    "entry_time": time.time()
                })
                pos_counter += 1
    except WebSocketDisconnect:
        connected_sockets.remove(websocket)

async def market_loop():
    while True:
        for sym in spot_prices:
            spot_prices[sym] += np.random.normal(0, spot_prices[sym] * 0.0002)

        pos_payloads = []
        for p in list(paper_positions):
            spot = spot_prices[p["symbol"]]
            move_pct = (spot - p["entry_spot"]) / p["entry_spot"]
            curr_prem = max(p["entry_prem"] * (1.0 + (move_pct * 20.0)), 0.001)
            roi = ((curr_prem - p["entry_prem"]) / p["entry_prem"]) * 100.0
            pnl_inr = (curr_prem - p["entry_prem"]) * 100 * 85.0
            hold_time = round(time.time() - p["entry_time"], 1)

            pos_payloads.append({
                "id": p["id"],
                "symbol": p["symbol"],
                "strike": p["strike"],
                "entry_prem": p["entry_prem"],
                "curr_prem": round(curr_prem, 3),
                "roi_pct": round(roi, 2),
                "pnl_inr": round(pnl_inr, 2),
                "hold_time": hold_time
            })

        frame = json.dumps({
            "prices": {k: round(v, 2) for k, v in spot_prices.items()},
            "gex_3d": get_3d_gamma(spot_prices["BTCUSDT"]),
            "positions": pos_payloads
        })

        for ws in list(connected_sockets):
            try:
                await ws.send_text(frame)
            except Exception:
                pass
        await asyncio.sleep(0.5)

@app.on_event("startup")
async def start_feed():
    asyncio.create_task(market_loop())
