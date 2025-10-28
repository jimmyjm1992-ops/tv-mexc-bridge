# TradingView ↔ MEXC ↔ GPT Bridge

Deploy this Flask app to safely connect TradingView alerts and MEXC data to your GPT.

Endpoints:
- /tv/webhook → TradingView webhook
- /feed/latest → Latest alerts feed
- /scan/mexc → Top MEXC gainers

Setup:
1. Set environment variables (WEBHOOK_TOKEN, DATA_DIR, ALLOWED_ORIGINS, PORT)
2. pip install -r requirements.txt
3. python app.py
