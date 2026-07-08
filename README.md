# Credit Memo — DSS webapp (WEBAIKU)

A Dataiku **STANDARD project webapp** built as a Vue 3 SPA + Flask backend,
versioned in Git and served through the project library with **WEBAIKU** (the
"thin webapp" pattern). Package name (library folder): **`credit_memo`**.

## Architecture

- **Frontend** — Vue 3 + Vite + Tailwind v4 + shadcn-vue on the Dataiku design
  system. Renders UI and calls the backend over HTTP (`src/api.ts`). Built to
  `dist/` (committed).
- **Backend** — a Flask **Blueprint** (`backend/api/memo_api.py`, `url_prefix="/api"`)
  that reads/writes DSS datasets, folders and the agent, returning JSON.
- They meet at `/api`: locally via a Vite proxy, in DSS via `getWebAppBackendUrl()`.

```
backend/            Flask blueprint + DSS entry points (wsgi_dss / wsgi_local)
  config.py         dataset names, folder ids, agent name  ← verify per project
  api/memo_api.py   all endpoints (/metrics /memos /memo /structure /run_agent …)
src/                Vue SPA (views, components, stores, api.ts, lib/markdown.ts)
dist/               BUILT SPA — committed (DSS serves it, never builds)
webapp/             thin-webapp instance snippets (JS + Python tab)
config/             external-libraries.json snippet (pythonPath)
requirements.txt    code env (webaiku, pandas, matplotlib, …)
```

## Local development

```bash
pnpm install
pnpm dev        # http://127.0.0.1:5175 — /api proxied to the Flask dev backend

# backend (needs webaiku + a DSS connection):
VITE_API_PORT=5000 python -m credit_memo.backend.wsgi_local
```
Without a backend, the SPA falls back to **mock data** so the UI still runs.

## Build & commit

```bash
pnpm build      # → dist/ (commit it: DSS pulls the repo and serves dist/)
git commit -am "…" && git push
```

## Deploy to DSS

1. **Library ← Git.** Project → Library editor (`</>`) → **GIT** → add reference:
   repo URL, branch `main`, **target path `webapps/credit_memo`**.
2. **Python path.** In `lib/external-libraries.json` add the **parent** `webapps`
   to `pythonPath` (see `config/external-libraries.snippet.json`).
3. **Code env** with `webaiku` installed (`requirements.txt`), or reuse one.
4. **Thin webapp** (STANDARD, backend enabled + autostart):
   - HTML tab: empty · CSS tab: empty
   - JS tab: `webapp/js-bootstrap.js`
   - Python tab: `webapp/python-tab.py`
     (`from credit_memo.backend.wsgi_dss import init_dss_app; init_dss_app(app)`)
   - Then **Restart backend**.

## Features

Builder (title + sections with metric chips, reorder, run agent, delete),
Saved memos, Metrics (+ add via drag & drop → `BUILD_METRICS`), Import (drag &
drop → clears the Previous Memos PDF folder + rebuilds `structure_memo`).

Agent paragraphs render **Markdown + LaTeX tables + KaTeX math + `<python>` charts**.
`<python>` snippets are executed server-side by `/run_python` (matplotlib → PNG);
in the local mock they are shown as code.

> Config is per-project: verify dataset names / folder ids in `backend/config.py`
> against the target (`dku dataset list`, `dku managed-folder list`) before deploying.
