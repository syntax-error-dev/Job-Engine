# 🕵️ JobEngine

AI-powered job aggregator that scrapes vacancies from **Djinni**, **DOU**, and **LinkedIn**, then analyzes each one against your skill profile using **Google Gemini** — and gives every vacancy a match score.

![Python](https://img.shields.io/badge/Python-3.12-blue?logo=python)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115-green?logo=fastapi)
![Gemini](https://img.shields.io/badge/Google%20Gemini-AI-orange?logo=google)
![License](https://img.shields.io/badge/license-MIT-lightgrey)

---

## ✨ Features

- **Multi-source scraping** — Djinni, DOU, LinkedIn in one click
- **AI match scoring** — Gemini analyzes each vacancy against your profile (0–100%)
- **Real-time updates** — results stream to the UI via SSE as they arrive
- **Smart filters** — by score, technology stack, date scraped, work format (remote/office/city)
- **Export to CSV** — take your filtered results anywhere
- **Docker support** — one command to run

---

## 🖥️ Screenshot

> Run the app and open `http://localhost:8080`

---

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python 3.12, FastAPI, SQLAlchemy (async) |
| Database | SQLite + Aiosqlite, Alembic migrations |
| Scraping | Playwright (Djinni, LinkedIn), HTTPX + BeautifulSoup (DOU) |
| AI | Google Gemini API (structured output via Pydantic schema) |
| Frontend | Jinja2 templates, Bootstrap 5, SSE |
| DevOps | Docker, Docker Compose |

---

## 🚀 Quick Start

### Local

```bash
# 1. Clone
git clone https://github.com/your-username/jobengine.git
cd jobengine

# 2. Install dependencies
pip install -r requirements.txt
playwright install chromium

# 3. Configure
cp .env.example .env
# Edit .env and add your GEMINI_API_KEY

# 4. Run migrations
alembic upgrade head

# 5. Start
python run.py
```

Open `http://localhost:8080`

### Docker

```bash
cp .env.example .env
# Edit .env and add your GEMINI_API_KEY

mkdir data
docker compose up --build
```

---

## ⚙️ Configuration

Copy `.env.example` to `.env` and fill in:

```env
GEMINI_API_KEY=your_key_here
```

Get a free Gemini API key at [aistudio.google.com](https://aistudio.google.com/apikey).

---

## 📁 Project Structure

```
jobengine/
├── app/
│   ├── core/           # Database connection
│   ├── models/         # SQLAlchemy models
│   ├── schemas/        # Pydantic schemas
│   ├── services/       # VacancyService, AIService
│   ├── templates/      # Jinja2 HTML templates
│   └── main.py         # FastAPI app & routes
├── scrapers/
│   ├── base.py
│   ├── djinni.py       # Playwright scraper
│   ├── dou.py          # HTTPX + BeautifulSoup scraper
│   └── linkedin.py     # Playwright scraper
├── alembic/            # DB migrations
├── tests/
│   └── test_jobengine.py
├── analyze_jobs.py     # AI analysis pipeline
├── test_parser.py      # Scraper orchestrator
├── run.py
├── Dockerfile
├── docker-compose.yml
└── requirements.txt
```

---

## 🧪 Running Tests

```bash
pip install pytest pytest-asyncio httpx
pytest tests/ -v
```

---

## 📝 Notes

- Free Gemini API tier: ~15 req/min. The app handles rate limits automatically with exponential backoff and model fallback.
- LinkedIn scraping works without auth but may be blocked — results vary.
- The app uses SQLite by default. For production, swap to PostgreSQL in `database.py`.