# College Notice and Circular Summarisation Assistant

A Phase 1 foundation for a college dashboard that will help students and staff upload notices and circulars, extract their contents, and receive clear AI-generated summaries.

## Problem statement

College notices are often distributed as lengthy PDFs across multiple channels. Important dates, eligibility rules, and required actions can be missed. This project will provide one focused workspace for organising notices and making their key information easier to understand.

## Objectives

- Provide a clean, responsive dashboard for managing notices and circulars.
- Accept PDF documents for later text extraction with PyMuPDF.
- Use Google Gemini to generate clear summaries in a future phase.
- Store application data securely with Supabase.
- Keep frontend and backend independently deployable.

## Technology stack

| Layer | Technology |
| --- | --- |
| Frontend | React, Vite, Tailwind CSS |
| Backend | Python, Flask, Flask-CORS |
| Database | Supabase |
| AI | Google GenAI SDK (Gemini) |
| PDF processing | PyMuPDF |
| Deployment | Vercel |

## Folder structure

```text
college-notice-assistant/
├── frontend/                 # Vite + React dashboard
│   ├── src/components/       # Reusable UI components
│   ├── src/pages/            # Page-level components
│   └── src/services/         # API client
├── backend/                  # Flask API
│   ├── routes/               # API blueprints
│   ├── services/             # Future business services
│   └── utils/                # Future shared utilities
└── database/                 # Future Supabase schema and migrations
```

## Prerequisites

- Node.js 20 or later
- Python 3.12 (see `backend/.python-version`)

## Environment setup

Create local environment files from the examples. Never commit the resulting `.env` files.

```powershell
Copy-Item backend/.env.example backend/.env
Copy-Item frontend/.env.example frontend/.env
```

Backend variables:

| Variable | Purpose |
| --- | --- |
| `APP_ENV` | Use `development` locally and `production` in Vercel. |
| `GEMINI_API_KEY` | Server-only Google Gemini API credential; required for OCR and AI summaries. |
| `GEMINI_MODEL` | Optional Gemini model name; defaults to `gemini-3.8-flash`. |
| `SUPABASE_URL` | Supabase project URL; required when database features are added. |
| `SUPABASE_SECRET_KEY` | Server-only Supabase credential; do not expose it to the frontend. |
| `FRONTEND_URL` | Allowed CORS origin, such as `http://localhost:5173`. |

Frontend variables:

| Variable | Purpose |
| --- | --- |
| `VITE_API_BASE_URL` | Local Flask API base URL, such as `http://localhost:5000`. Leave unset in Vercel so the frontend uses same-origin `/api` routes. |

## Run locally

Start the backend in one terminal:

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python app.py
```

Start the frontend in another terminal:

```powershell
cd frontend
npm install
npm run dev
```

Open the Vite URL shown in the terminal (normally `http://localhost:5173`).

## Health check

With the Flask server running, request:

```powershell
Invoke-RestMethod http://localhost:5000/api/health
```

Expected response:

```json
{
  "success": true,
  "message": "College Notice Assistant API is running",
  "status": "healthy"
}
```

## Vercel deployment

This repository deploys as one Vercel project. The Vite frontend is built from `frontend/`, and Vercel runs the Flask WSGI application through the root `app.py` entry point as the backend function. The root `vercel.json` supplies the Vite build/output settings and function configuration; `pyproject.toml` identifies the Python dependencies.

1. Push this repository to GitHub, then choose **Add New → Project** in Vercel and import the repository.
2. Keep the Vercel project **Root Directory** set to the repository root. Do not set it to `frontend/` or `backend/`.
3. The checked-in `vercel.json` supplies the install command, build command, and output directory. No Gunicorn start command is used on Vercel.
4. In **Settings → Environment Variables**, add the following for Production (and Preview if you want previews to process documents):

   | Variable | Value |
   | --- | --- |
   | `APP_ENV` | `production` |
   | `GEMINI_API_KEY` | Your secret Gemini API key |
   | `GEMINI_MODEL` | Optional; defaults to `gemini-3.8-flash` |
   | `FRONTEND_URL` | The exact frontend origin, for example `https://your-project.vercel.app` |

   Do not set `VITE_API_BASE_URL` in Vercel. The production frontend uses the same-origin API paths `/api/health` and `/api/v1/summarize`, so the Gemini key is never shipped to the browser.
5. Deploy from the Vercel dashboard. Confirm `GET https://your-project.vercel.app/api/health` returns a healthy JSON response, then test a small PDF or image upload.

Vercel Functions use the configured Python 3.12 runtime and have a 500 MB uncompressed Python function-bundle limit. Tests and fixture files are excluded from the runtime bundle. PyMuPDF must install its Linux wheel during Vercel's build; verify the first deployment log because the final dependency bundle size cannot be confirmed locally.

### Vercel upload and execution limits

The local API supports files up to 10 MB, but Vercel Functions currently limit request and response bodies to 4.5 MB. Files larger than 4.5 MB will be rejected by Vercel before Flask can process them. This configuration deliberately preserves the local 10 MB validation and all supported formats rather than silently changing behavior. Scanned multi-page PDFs may also approach the configured 300-second function duration because each page can require a Gemini OCR request.

## Roadmap

1. Add secure PDF upload and storage.
2. Extract PDF text with PyMuPDF.
3. Add Gemini-based summaries, key dates, and action items.
4. Persist notices and summaries in Supabase.
5. Add authentication, search, and filtering.
6. Add tests, production monitoring, and refined deployment configuration.

## Document processing

The Phase 3 API accepts PDF, JPG, JPEG, and PNG notice files up to 10 MB at `POST /api/v1/summarize` using multipart form field `file`. It extracts native PDF text with PyMuPDF, uses Gemini vision OCR for scanned PDFs and images, then returns a structured Gemini summary. A server-only `GEMINI_API_KEY` is required. No Supabase integration, API authentication, or webhooks are included.

## Current scope

The dashboard supports document selection, upload progress, extraction, structured summaries, retry messages, and empty states. Supabase persistence, authentication, webhooks, and deployment configuration remain out of scope.
