TradingView ↔ MEXC ↔ GPT Bridge on Koyeb

Endpoints:
  GET /health
  GET /scan/mexc?limit=6&min_vol=20000000&usdt_only=1
  GET /feed/latest
  POST /tv/webhook  (JSON must include {"token": "...", "symbol": "..."} )
