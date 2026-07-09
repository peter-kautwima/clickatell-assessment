# Clickatell Assessment

This repository contains a small FastAPI backend and a Vite React + TypeScript frontend for the assessment.

## Run locally

### Backend

From the repository root:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
```

Open http://127.0.0.1:8000/ to confirm the API responds.

### Frontend

In a second terminal:

```bash
cd frontend
npm install
npm run dev -- --host 127.0.0.1 --port 5173
```

Open http://127.0.0.1:5173/ to view the Vite app.

### Notes

A longer project overview draft has been moved to the private notes area at notes/READ_ME.md for developer reference.
