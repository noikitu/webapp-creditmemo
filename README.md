# Credit Memo — standardized webapp

A standardized **Dataiku-style** UI for the Credit Memo structure builder, built
with the `dataiku-webapp` design system.

- **Stack:** Vue 3 (`<script setup>`) · vue-router · pinia · Vite · Tailwind CSS v4 · shadcn-vue · lucide icons · Inter font · KaTeX.
- **Scope:** frontend-only prototype. All data is **mocked** in `src/stores/memo.ts`
  (no Dataiku backend). The agent run, import, and metric extraction are simulated;
  wire them to the DSS endpoints later.

## Run

```bash
pnpm install
pnpm dev      # → http://127.0.0.1:5175
```

## Pages (`src/views`)

| Route | Page | What it does |
|---|---|---|
| `/` | **Builder** | Memo title + sections (title / description / metric pills), reorder, run agent (mock), generated paragraphs, delete memo. |
| `/saved` | **Saved memos** | Browse mock memos, open or delete. |
| `/metrics` | **Metrics** | Metric catalog + "Add Metrics" dialog with drag & drop (mock BUILD_METRICS). |
| `/import` | **Import** | Drag & drop a document to import a memo (mock BUILD_TEMPLATE). |

## Rich agent paragraphs

`src/lib/markdown.ts` (`renderRich`) renders the agent's text with:

- **Markdown** (headings, bold/italic, lists, inline code),
- **LaTeX tables** (`\begin{table}` / `\begin{tabular}`) → styled HTML tables,
- **LaTeX math** (`$…$`, `$$…$$`, `\(…\)`, `\[…\]`) → **KaTeX**,
- **`<python>…</python>`** snippets → shown as a code block.

> Note: in this frontend-only version, `<python>` charts are **displayed as code**,
> not executed. Chart execution needs the Dataiku Python backend (matplotlib →
> PNG), as in the DSS standard webapp.

## Structure

- `src/style.css` — Dataiku design tokens (indigo primary, light sidebar, radius). **No `tailwind.config.js`** (Tailwind v4).
- `src/components/ui/*` — shadcn-vue primitives.
- `src/components/layout/*`, `src/layouts/DefaultLayout.vue` — app shell (collapsible icon sidebar that builds itself from route `meta`).
- `src/components/MemoContent.vue` — renders `renderRich` output and typesets KaTeX.
- `src/stores/memo.ts` — in-memory mock state + actions.
- `src/lib/markdown.ts` — Markdown + LaTeX + math renderer.
