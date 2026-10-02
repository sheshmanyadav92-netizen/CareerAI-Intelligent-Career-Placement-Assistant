# CareerAI

CareerAI is a job-seeker platform. The frontend includes an interactive dashboard preview for resumes, job applications, and a career profile. Dashboard sample data is held in browser memory; resume PDF analysis is handled by the backend and the configured AI provider.

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
npm.cmd --prefix frontend install
npm.cmd --prefix frontend run dev -- --port 5173
```

Open <http://localhost:5173>.

### Resume AI analysis

For local analysis without a cloud key, install Ollama and download a small model:

```powershell
winget install --id Ollama.Ollama --exact
ollama pull qwen2.5:3b
```

Then set these values in the project-root `.env`:

```dotenv
LLM_PROVIDER=ollama
LLM_MODEL=qwen2.5:3b
```

Ollama runs the model on your machine at `http://127.0.0.1:11434`; no API key is used. The backend warms the local model in the background on startup and keeps it loaded while the preview is in use to reduce first-analysis delay. The dashboard submits PDFs to the backend, which extracts their text and sends it to the selected provider for analysis. Displayed facts, summaries, and highlights must be verbatim excerpts from the resume; AI categorization can still be imperfect, so check the source context. For the OpenAI option instead, set `LLM_PROVIDER=openai`, `LLM_API_KEY`, and `LLM_MODEL=gpt-4o-mini` in the untracked project `.env` and keep the key out of frontend variables. Restart the backend after changing settings. Use a resume copy with information you do not want processed removed. Uploaded PDFs and analysis results are not persisted by this preview. Analysis is limited to 10 MB, 50 pages, and the configured text-length limit. Scanned PDFs without selectable text need OCR and are rejected.

The resume-analysis endpoint is an unauthenticated local-preview endpoint and is disabled when `ENVIRONMENT=production`. Add application authentication, authorization, and appropriate storage/privacy controls before exposing resume analysis in a deployed product. Dashboard sample data and edits are for demonstration only and are held in browser memory.

## Database

Copy `.env.example` to `.env`, then start the PostgreSQL service:

```powershell
docker compose up -d --wait
```

PostgreSQL is exposed on `localhost:5433` to avoid colliding with other local projects. Check it with `docker compose ps`; stop it with `docker compose down`.
