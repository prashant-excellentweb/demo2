# Buddy Chat

An AI chat assistant: **FastAPI** backend, **React + TypeScript** frontend, streaming
replies over Server-Sent Events.

Previously the UI was rendered with Jinja2 templates and driven by a single
vanilla-JS file, with each conversation stored as one JSON blob. The frontend is
now a real single-page app and the backend is layered into routes → services →
repositories, with each message stored as its own row.

---

## Requirements

- Python 3.11+
- Node.js 20+
- An API key for OpenAI or Groq

## Setup

```bash
python -m venv .venv
.venv\Scripts\activate          # macOS/Linux: source .venv/bin/activate
pip install -r requirements-dev.txt

cd frontend && npm install && cd ..

copy .env.example .env          # macOS/Linux: cp .env.example .env
```

Edit `.env` and set at least a `SECRET_KEY` and one provider key:

```bash
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

Then apply the schema:

```bash
python -m alembic upgrade head
```

## Running in development

Two processes. Vite owns the UI and proxies `/api` to FastAPI, so edits to either
side hot-reload.

On Windows, one command starts both:

```powershell
.\scripts\dev.ps1
```

Or run them yourself:

```bash
# terminal 1 - API on :8000
python -m uvicorn app.main:app --reload

# terminal 2 - UI on :5173
cd frontend && npm run dev
```

Open <http://localhost:5173>. API docs are at <http://localhost:8000/docs>
(disabled when `ENVIRONMENT=production`).

## Running as a single service

Build the frontend and FastAPI serves it directly — no Node process, no proxy:

```bash
cd frontend && npm run build && cd ..
python -m uvicorn app.main:app --port 8000
```

Everything is then on <http://localhost:8000>. `app/main.py` mounts
`frontend/dist` and falls back to `index.html` for client-side routes, so
deep links like `/login` survive a refresh. Requests under `/api` that match no
route still return JSON 404s rather than the HTML shell.

---

## Architecture

```
app/
  api/routes/     HTTP only: parse, authorize, delegate, serialize
  services/       business logic (chat orchestration, auth, uploads, search)
  repositories/   all database queries
  models/         SQLAlchemy tables
  schemas/        Pydantic request/response contracts
  core/           config, security, logging, exceptions
frontend/src/
  pages/          route-level screens
  components/     chat UI, layout, reusable primitives
  hooks/          data fetching (React Query) and streaming state
  lib/            API client, SSE parser, helpers
```

Routes never touch the ORM and services never touch HTTP, which is what keeps
the streaming path testable without a live provider.

### Streaming

`POST /api/chats/{id}/messages` returns `text/event-stream`. The server persists
the user turn, emits `start` (with the chat id and any web-search sources), then
`delta` events as tokens arrive, then `done` with final token counts. The
assistant turn is written once the stream finishes; if the provider fails
mid-way an `error` event is sent and no partial assistant row is saved.

### Notable behaviour

- **Auth** is a JWT in an `httpOnly` cookie, so page scripts cannot read it.
- **Quota** is server-side. The old client sent `total_tokens` and `locked_until`
  in the request body, meaning a user could edit their own limits; usage now
  lives in `usage_counters` keyed by `(user_id, date)`.
- **History** is server-owned. The old client posted the entire transcript back,
  so it could rewrite what the model had said; the server now reads history
  from the database and ignores any client-supplied messages.
- **Attachments** are rows plus files under `var/uploads`. Base64 images used to
  be embedded in the transcript JSON, which is what made the database grow to
  megabytes for a handful of chats.
- **Chat list vs. detail** are separate endpoints, so opening the sidebar no
  longer downloads every message of every conversation.

---

## Configuration

All settings live in `.env`; see `.env.example` for the full annotated list. The
ones worth knowing:

| Variable | Default | Purpose |
| --- | --- | --- |
| `ENVIRONMENT` | `development` | `production` enables extra safety checks and hides `/docs` |
| `SECRET_KEY` | insecure placeholder | JWT signing key; required in production |
| `DATABASE_URL` | local SQLite | Point at PostgreSQL for production |
| `AI_PROVIDER` | `groq` | `openai` or `groq` |
| `CHAT_CONTEXT_WINDOW` | `20` | Recent messages replayed to the model |
| `DAILY_TOKEN_BUDGET` | `200000` | Per-user daily cap; `0` disables |

With `ENVIRONMENT=production` the app refuses to start on a weak `SECRET_KEY` or
a SQLite database, since SQLite serialises writes and will stall under
concurrent users.

### Switching provider

If OpenAI reports `insufficient_quota` the account is out of credits, not rate
limited, and retrying will not help. Either add credits or switch to Groq's free
tier in `.env`:

```env
AI_PROVIDER=groq
GROQ_API_KEY=your_key_here
GROQ_MODEL=llama-3.3-70b-versatile
```

---

## Tests

```bash
python -m pytest
```

The suite stubs the AI and search services, so it runs offline and costs
nothing. It covers auth and session handling, per-user isolation, upload
validation, quota accounting, and the streaming path — including that a client
cannot inject its own history.

Frontend checks:

```bash
cd frontend
npm run typecheck
npm run build
```

## Maintenance

```bash
python -m scripts.maintenance stats                 # row counts, storage health
python -m scripts.maintenance purge-uploads --hours 24
python -m scripts.maintenance purge-cache
python -m scripts.maintenance vacuum                # reclaim space (SQLite)
```

Schedule `purge-uploads` and `purge-cache`; without them, files from abandoned
uploads and expired cache rows accumulate indefinitely.

## Deployment notes

1. Set `ENVIRONMENT=production`, a strong `SECRET_KEY`, and a PostgreSQL
   `DATABASE_URL`.
2. Run `python -m alembic upgrade head`.
3. Build the frontend (`npm run build`) so FastAPI can serve it.
4. Serve behind HTTPS — the session cookie is marked `secure` in production and
   browsers will drop it over plain HTTP.
5. Run under a process manager, e.g.
   `uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4`.
6. Put `var/uploads` on a persistent volume, or shared storage if you run more
   than one instance.
