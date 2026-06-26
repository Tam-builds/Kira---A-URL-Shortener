# Kira ✦ — URL Shortener

A cute anime-styled URL shortener with **user authentication**, **click analytics**, and **per-user dashboards**.

## Features
- Register / Login / Logout (bcrypt password hashing)
- Shorten any URL to a 6-char code
- Per-user link isolation — you only see your own links
- Click tracking per link
- Delete links
- Stats lookup
- JSON API

## Tech Stack
| Layer    | Tech              |
|----------|-------------------|
| Backend  | Python + Flask    |
| Auth     | bcrypt + sessions |
| Database | SQLite            |
| Frontend | HTML + Vanilla JS |

## Run Locally

```bash
cd url-shortener-v2
python -m venv venv
source venv/bin/activate       # Windows: venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

Open `http://localhost:5000` — register an account and start shortening!

## Deploy to Render (Free)

1. Push to GitHub
2. New Web Service on render.com
3. Build command: `pip install -r requirements.txt`
4. Start command: `gunicorn app:app`
5. Add env var: `SECRET_KEY=your-random-secret-here`

## API Endpoints

| Method | Endpoint        | Auth | Description              |
|--------|-----------------|------|--------------------------|
| GET    | `/`             | ✅   | Dashboard                |
| POST   | `/shorten`      | ✅   | Shorten a URL (JSON)     |
| GET    | `/<code>`       | ❌   | Redirect to original URL |
| GET    | `/stats/<code>` | ✅   | Get stats for a code     |
| POST   | `/delete/<code>`| ✅   | Delete a link            |
| GET    | `/api/all`      | ✅   | List all your links      |
| GET    | `/login`        | ❌   | Login page               |
| GET    | `/register`     | ❌   | Register page            |
| GET    | `/logout`       | ❌   | Logout                   |

## Resume Bullet Point
> Built a full-stack URL shortener with user authentication (bcrypt), session management, SQLite persistence, per-user analytics dashboard, and REST API — deployed on Render.
