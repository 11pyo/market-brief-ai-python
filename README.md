# AI Morning Market Briefing | AI 모닝 마켓 브리핑

**증시흐름 (Market Brief AI)** - AI-powered daily morning market briefing platform

[![Live Demo](https://img.shields.io/badge/Live%20Demo-market--brief--ai-6366f1?style=for-the-badge)](https://market-brief-ai-python.onrender.com/)
[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=flat-square&logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688?style=flat-square&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![License](https://img.shields.io/badge/License-MIT-green?style=flat-square)](LICENSE)

> Free, AI-generated hedge fund-style morning market briefings with real-time global data.

---

## Live Demo

**https://market-brief-ai-python.onrender.com/**

---

## Features

### AI Market Briefing (6-Part Structure)
Every briefing follows a professional hedge fund morning note format:
1. **Key Overnight Events** - Major market-moving news with real data
2. **Market Direction Probability** - Up/Sideways/Down with percentage confidence
3. **Sector Leadership** - Top 3 & Bottom 2 sectors with ETF symbols
4. **Key Risks** - Critical risk factors to watch
5. **Trade Ideas** - Long/Short with entry, target, stop-loss, and R:R ratio
6. **10-Second Dashboard** - Quick macro snapshot

Optional **Part 7**: Portfolio-specific personalized advice based on your holdings.

### Real-Time Market Dashboard
- Live ticker: S&P 500, Nasdaq, DJI, VIX, BTC, ETH, EUR/USD, USD/JPY
- Sector ETF performance (XLK, XLE, XLF, XLV, XLI, XLY, XLP, XLU, XLRE, XLB, XLC)
- CNN Fear & Greed Index with visual gauge
- Economic calendar & earnings dates
- Interactive candlestick charts (TradingView Lightweight Charts)

### Multi-Language
Korean (default), English, Chinese, Japanese - switch instantly in the UI.

### Progressive Web App (PWA)
Install on your phone's home screen for an app-like experience. Works offline with service worker caching.

### Portfolio Management
Store your asset allocation, investment style, and watchlist. The AI tailors Part 7 of the briefing to your specific portfolio.

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | **FastAPI** + Uvicorn (async Python) |
| AI/LLM | OpenAI GPT-4o, Google Gemini, Anthropic Claude (multi-provider with fallback) |
| Market Data | Yahoo Finance (yfinance), Finnhub API, Reuters/CNN RSS |
| Frontend | Vanilla JS + TradingView Lightweight Charts |
| Scheduler | APScheduler (daily 7 AM KST auto-generation) |
| Deployment | Render.com |

---

## Quick Start

```bash
# Clone
git clone https://github.com/11pyo/market-brief-ai-python.git
cd market-brief-ai-python

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your API keys (at minimum: FINNHUB_API_KEY + one LLM key)

# Run
python main.py
# Open http://localhost:8000
```

### Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `FINNHUB_API_KEY` | Yes | Free at [finnhub.io](https://finnhub.io/) |
| `OPENAI_API_KEY` | One of three | OpenAI GPT models |
| `GEMINI_API_KEY` | One of three | Google Gemini models |
| `ANTHROPIC_API_KEY` | One of three | Anthropic Claude models |
| `LLM_PROVIDER` | No | `openai` (default), `gemini`, or `anthropic` |
| `LLM_MODEL` | No | Model name (default: `gpt-4o`) |
| `TZ` | No | Timezone (default: `Asia/Seoul`) |

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/briefing/latest` | Latest briefing |
| GET | `/api/briefing/generate/stream` | Generate new briefing (SSE) |
| GET | `/api/briefing/history` | Briefing history |
| GET | `/api/market/snapshot` | Real-time market data |
| GET | `/api/market/chart?name=^GSPC&period=1d` | OHLCV chart data |
| GET | `/api/market/fear-greed` | CNN Fear & Greed Index |
| GET | `/api/market/sectors` | Sector ETF performance |
| GET | `/api/calendar` | Economic & earnings calendar |
| GET | `/api/portfolio` | Load portfolio |
| POST | `/api/portfolio` | Save portfolio |

---

## Project Structure

```
market-brief-ai-python/
├── main.py                 # FastAPI app + routes
├── config.py               # Environment settings
├── scheduler.py            # Daily briefing pipeline
├── schemas.py              # Pydantic models
├── services/
│   ├── llm_engine.py       # Multi-provider LLM (OpenAI/Gemini/Claude)
│   ├── market_data.py      # Yahoo Finance + CNN Fear/Greed
│   ├── news_collector.py   # Finnhub + RSS aggregation
│   ├── news_filter.py      # Relevance scoring & filtering
│   ├── briefing_store.py   # JSON file persistence
│   ├── portfolio_manager.py
│   ├── calendar_service.py
│   └── stats_tracker.py
├── public/                 # Frontend SPA
│   ├── index.html
│   ├── js/app.js
│   ├── js/i18n.js
│   ├── css/style.css
│   ├── manifest.json
│   └── sw.js
└── data/                   # Runtime data (briefings, portfolio)
```

---

## Contributing

Issues and pull requests are welcome. Please open an issue first to discuss proposed changes.

---

## License

MIT
