from flask import Flask, request, jsonify
from datetime import datetime, timezone
import os, json, threading, requests

app = Flask(__name__)

# ENV
WEBHOOK_TOKEN = os.environ.get("WEBHOOK_TOKEN", "change_me")
ALLOWED_ORIGINS = os.environ.get("ALLOWED_ORIGINS", "*")
DATA_DIR = os.environ.get("DATA_DIR", "./data")
PORT = int(os.environ.get("PORT", "8080"))  # Koyeb defaults to 8080
ALERTS_FILE = os.path.join(DATA_DIR, "alerts.json")
os.makedirs(DATA_DIR, exist_ok=True)
_lock = threading.Lock()

def _read_alerts():
    if not os.path.exists(ALERTS_FILE):
        return []
    try:
        with open(ALERTS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []

def _write_alerts(alerts):
    with open(ALERTS_FILE, "w", encoding="utf-8") as f:
        json.dump(alerts[-500:], f, ensure_ascii=False, indent=2)

@app.after_request
def add_cors_headers(resp):
    resp.headers["Access-Control-Allow-Origin"] = ALLOWED_ORIGINS
    resp.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
    resp.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    return resp

@app.route("/", methods=["GET"])
def root():
    return jsonify({"ok": True, "routes": ["/health", "/scan/mexc", "/feed/latest", "/tv/webhook (POST)"]})

@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "time": datetime.now(timezone.utc).isoformat()})

@app.route("/tv/webhook", methods=["POST"])
def tv_webhook():
    try:
        payload = request.get_json(force=True, silent=False)
    except Exception as e:
        return jsonify({"ok": False, "error": f"Invalid JSON: {e}"}), 400
    if not isinstance(payload, dict):
        return jsonify({"ok": False, "error": "Payload must be a JSON object"}), 400
    if payload.get("token") != WEBHOOK_TOKEN:
        return jsonify({"ok": False, "error": "Unauthorized"}), 401

    def _to_float(v):
        try: return float(v)
        except Exception: return None

    alert = {
        "symbol": str(payload.get("symbol", "")).upper(),
        "exchange": payload.get("exchange", ""),
        "price": _to_float(payload.get("price")),
        "time": payload.get("time") or datetime.now(timezone.utc).isoformat(),
        "note": payload.get("note", ""),
        "received_at": datetime.now(timezone.utc).isoformat()
    }
    with _lock:
        alerts = _read_alerts()
        alerts.append(alert)
        _write_alerts(alerts)
    return jsonify({"ok": True})

@app.route("/feed/latest", methods=["GET"])
def feed_latest():
    limit = max(1, min(int(request.args.get("limit", 20)), 100))
    symbol = request.args.get("symbol", "").upper()
    alerts = _read_alerts()
    if symbol:
        alerts = [a for a in alerts if a.get("symbol") == symbol]
    return jsonify(alerts[-limit:])

_cache = {"ts": 0, "data": None}
@app.route("/scan/mexc", methods=["GET"])
def scan_mexc():
    import time
    now = time.time()
    if _cache["data"] and now - _cache["ts"] < 20:
        return jsonify(_cache["data"])

    try:
        min_vol = float(request.args.get("min_vol", "20000000"))
    except ValueError:
        min_vol = 20000000.0
    limit = max(1, min(int(request.args.get("limit", 6)), 20))
    usdt_only = request.args.get("usdt_only", "1") == "1"

    url = "https://api.mexc.com/api/v3/ticker/24hr"
    try:
        resp = requests.get(url, timeout=8)
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        return jsonify({"ok": False, "error": f"MEXC fetch failed: {e}"}), 502

    gainers = []
    if isinstance(data, list):
        for item in data:
            symbol = item.get("symbol", "")
            if usdt_only and not symbol.endswith("USDT"):
                continue
            def to_float(v, default=0.0):
                try: return float(v)
                except Exception: return default
            last_price = to_float(item.get("lastPrice") or item.get("last_price"))
            pct = to_float(item.get("priceChangePercent") or item.get("price_change_percent"))
            qvol = to_float(item.get("quoteVolume") or item.get("quote_volume"))
            if qvol >= min_vol:
                gainers.append({
                    "symbol": symbol,
                    "lastPrice": last_price,
                    "priceChangePercent": pct,
                    "quoteVolume": qvol
                })
    gainers.sort(key=lambda x: x["priceChangePercent"], reverse=True)
    payload = {"ok": True, "source": "MEXC", "min_vol": min_vol, "count": min(limit, len(gainers)), "items": gainers[:limit]}
    _cache["ts"], _cache["data"] = now, payload
    return jsonify(payload)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=PORT)
