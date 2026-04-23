# CircularX Backend (Taiwan)

CircularX is a FastAPI backend for an autonomous waste-to-wealth marketplace.
It supports material classification, buyer matching, negotiation, escrow workflow,
TPQC verification, and DPP (Digital Product Passport) generation.

## Tech Stack

- FastAPI + Pydantic
- SQLModel ORM (SQLite by default, Supabase Postgres optional)
- ChromaDB for vector matching
- OpenAI for classification/matching support
- Pytest for tests

## Project Structure

- `main.py`: FastAPI app entrypoint and lifespan startup
- `app/config.py`: environment settings
- `app/database.py`: DB engine/session setup
- `app/models/`: SQLModel entities
- `app/routers/`: API route handlers
- `app/services/`: business logic (classifier, matcher, escrow, DPP, etc.)
- `tests/`: unit tests
- `storage/`: runtime artifacts (DPP PDFs, market prices)

## Prerequisites

- Python 3.11+ recommended
- A virtual environment
- OpenAI API key
- (Optional) Supabase credentials
- (Optional) ngrok account + authtoken for public tunneling

## Local Setup

1. Create and activate virtual environment.
2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Create `.env` from `.env.example` and fill required values.

Minimum required values:

- `OPENAI_API_KEY`
- `SECRET_KEY`

If using Supabase/Postgres, also fill:

- `SUPABASE_URL`
- `SUPABASE_KEY`
- `SUPABASE_DATABASE_URL`

## Run the Backend

```bash
python main.py
```

or with uvicorn directly:

```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

API docs:

- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`
- Health: `http://localhost:8000/health`

## ngrok Port Forwarding

Install dependency (already listed in `requirements.txt`):

```bash
pip install pyngrok
```

Set your ngrok authtoken once:

```bash
python -c "from pyngrok import ngrok; ngrok.set_auth_token('YOUR_NGROK_AUTHTOKEN')"
```

Start backend in one terminal:

```bash
python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

Start a tunnel in another terminal:

```bash
python -c "from pyngrok import ngrok; import threading; t=ngrok.connect(8000, 'http'); print(t.public_url, flush=True); threading.Event().wait()"
```

## Main API Groups

- `/auth`: OAuth/login and current user
- `/buyer-profiles`: buyer profile CRUD for matching
- `/listings`: listing lifecycle
- `/ai`: classify, match, market-price endpoints
- `/transactions`: transaction and escrow flow
- `/tpqc`: inspection and approval/rejection
- `/notifications`: user notifications

## Running Tests

```bash
pytest -q
```

## Notes

- Startup seeds buyer profiles for matching via app lifespan handler.
- Runtime-generated files (DB, DPP PDFs, local caches) are ignored in git.
- Default database is local SQLite (`circularx.db`).

## Documentation

Additional architecture and setup references:

- `BACKEND_ARCHITECTURE.md`
- `CODEBASE_SUMMARY.md`
- `SUPABASE_DB_SETUP_AND_REQUEST_FORMATS.md`
- `SUPABASE_OAUTH_SETUP.md`
- `REDESIGN_GAP_ANALYSIS.md`
