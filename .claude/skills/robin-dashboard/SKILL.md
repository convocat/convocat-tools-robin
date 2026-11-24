---
name: robin-dashboard
description: "Launch Robin's Product Owner / Conversation logs dashboard (instructor/dashboard-kit/) for this repo: refreshes dashboard-data.json from Langfuse, builds the thread-view app if needed, and starts the local server. Triggers: '/robin-dashboard', 'start the dashboard', 'open the conversation log dashboard', 'launch robin dashboard'."
---

# robin-dashboard — start Robin's conversation/Product Owner dashboard

When invoked, get `instructor/dashboard-kit/` running against fresh data without Maaike touching the CLI herself.

## Step 1 — Verify prerequisites

1. Check Robin's venv exists: `.venv/Scripts/python.exe` (Windows) or `.venv/bin/python` (other OS). If missing, offer to create it and `pip install -r requirements.txt`.
2. Check `.env` exists at the repo root with `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY`, `LANGFUSE_BASE_URL`. Without these, `robin_adapter.py` fails — tell the user and stop rather than guessing values.
3. Check `instructor/dashboard-kit/thread-view/node_modules` exists. If not, run `npm install` in `instructor/dashboard-kit/thread-view/` first (needed before its first build).
4. Check `instructor/dashboard-kit/thread-view/dist/index.html` exists. If not, run `npm run build` in `instructor/dashboard-kit/thread-view/` (it's a vite-plugin-singlefile build — one HTML file with React + @assistant-ui/react inlined).

## Step 2 — Refresh the data

Run from the repo root:
```bash
.venv/Scripts/python.exe instructor/dashboard-kit/robin_adapter.py
```
This pulls fresh traces + feedback scores from Langfuse (environment `course`) and writes `instructor/dashboard-kit/dashboard-data.json`. Report how many conversations it built.

Then refresh the data for the RAG & Guardrails tab:
```bash
.venv/Scripts/python.exe instructor/dashboard-kit/guardrails_adapter.py
```
This writes `instructor/dashboard-kit/guardrails-data.json`: one record per chat turn (course chats and experiment runs), with each guardrail's result, the look-up matches and the evaluator scores. It uses Langfuse's newer endpoints, so it keeps working if the deprecated ones `robin_adapter.py` uses are removed. If it fails, the rest of the dashboard still works; only that tab shows "Nog geen data".

## Step 3 — Start the server

Check port 8080 isn't already serving the dashboard (`curl -s -m 3 http://localhost:8080/ -o /dev/null -w "%{http_code}"` — a 200 means it's already running, skip straight to Step 4). Otherwise start it in the background:
```bash
cd instructor/dashboard-kit && node server.js 8080
```
`server.js` is a plain static file server with no hot-reload: after any change to `dashboard.html`, `thread-view/`, or a re-run of `robin_adapter.py`, the browser just needs a refresh — no restart needed unless `server.js` itself changed.

## Step 4 — Confirm and hand off

Tell Maaike the dashboard is at **http://localhost:8080**, with tabs for Product Owner, Contentmanager, Technisch Beheer, RAG & Guardrails and Gesprekslogboek (conversation log — click any row to expand it inline with the assistant-ui thread view and the Bronnen/Beoordeling panel). She opens it herself; don't open the browser pane unless she asks to see it.

## Notes

- `instructor/dashboard-kit/robin_adapter.py` only pulls `environment: "course"` traces (real course chats), not the `experiment`/`sdk-experiment`/`ingestion` environments used by `experiments/run_experiment.py` or `ingestion/ingest_handbook.py`.
- The review panel (Beoordeling) in the conversation detail is UI-only — it doesn't persist anywhere. That's intentionally left to the separate `trace-annotation-dashboard` project.
- If `robin_adapter.py` raises a `RuntimeError` mentioning deprecated Langfuse endpoints, `/api/public/traces` or `/api/public/scores` have likely been removed — it needs migrating to `/api/public/v2/observations` and `/api/public/v3/scores`.
