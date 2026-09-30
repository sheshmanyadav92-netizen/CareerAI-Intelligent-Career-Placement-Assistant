# CareerAI

CareerAI is a job-seeker platform. This repository currently contains only the Phase 1 development skeleton: a Vite/React/TypeScript placeholder, a FastAPI health endpoint, and PostgreSQL for local development.

## Backend

From the repository root, create the virtual environment and install dependencies:

```powershell
python -m venv backend/.venv
backend/.venv/Scripts/python.exe -m pip install -r backend/requirements.txt
backend/.venv/Scripts/python.exe -m uvicorn main:app --app-dir backend --reload --port 8001
```

Open <http://127.0.0.1:8001/health> or <http://127.0.0.1:8001/docs>.

## Frontend

```powershell
```powershell
npm.cmd --prefix frontend install
npm.cmd --prefix frontend run dev -- --port 5173
```

Open <http://localhost:5173>.

## Database

Copy `.env.example` to `.env`, then start the PostgreSQL service:

```powershell
docker compose up -d --wait
```

PostgreSQL is exposed on `localhost:5433` to avoid colliding with other local projects. Check it with `docker compose ps`; stop it with `docker compose down`.
