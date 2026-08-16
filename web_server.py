import asyncio
import json
import time
import numpy as np
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, PlainTextResponse, Response

app = FastAPI(title="Quant Squeeze Terminal")

connected_sockets = set()
paper_positions = []
pos_counter = 1

spot_prices = {"BTCUSDT": 65000.0, "ETHUSDT": 3450.0, "XAUTUSDT": 2380.0}

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

@app.get("/")
async def get_dashboard():
    with open("templates/terminal.html", "r") as f:
        return HTMLResponse(content=f.read())

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
                qty = int(data.get("contracts", 1))
                spot = spot_prices[sym]
                paper_positions.append({
                    "id": f"SQZ_{pos_counter}",
                    "symbol": sym,
                    "strike": f"{round(spot * 1.015, 1)}C",
                    "contracts": qty,
                    "entry_spot": spot,
                    "entry_prem": round(spot * 0.00065, 3),
                    "entry_time": time.time(),
                    "status": "OPEN"
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
            pnl_inr = (curr_prem - p["entry_prem"]) * p["contracts"] * 100 * 85.0
            hold_time = round(time.time() - p["entry_time"], 1)

            pos_payloads.append({
                "id": p["id"],
                "symbol": p["symbol"],
                "strike": p["strike"],
                "contracts": p["contracts"],
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