// HTTP client for the Credit Memo backend (Flask blueprint under /api).
//
// In DSS the SPA runs inside a WEBAIKU-served iframe; getWebAppBackendUrl('')
// gives the backend base. Locally it is undefined and Vite proxies /api to the
// Flask dev server. Every backend route lives under the /api prefix.

interface WinWithBackend extends Window {
  getWebAppBackendUrl?: (arg: string) => string;
  parent: WinWithBackend;
}

function backendBase(): string {
  const w = window as unknown as WinWithBackend;
  const fn = w.getWebAppBackendUrl || (w.parent && w.parent.getWebAppBackendUrl);
  return typeof fn === 'function' ? fn('') : '';
}

const resolveUrl = (path: string): string => `${backendBase()}/api${path}`;

async function http<T>(path: string, opts?: RequestInit, timeout = 60000): Promise<T> {
  const ctrl = new AbortController();
  const timer = setTimeout(() => ctrl.abort(), timeout);
  try {
    const r = await fetch(resolveUrl(path), { signal: ctrl.signal, ...opts });
    if (!r.ok) throw new Error('HTTP ' + r.status);
    return (await r.json()) as T;
  } finally {
    clearTimeout(timer);
  }
}

const get = <T>(p: string, timeout?: number) => http<T>(p, undefined, timeout);
const postJson = <T>(p: string, body?: unknown) =>
  http<T>(p, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: body == null ? undefined : JSON.stringify(body),
  });
const postForm = <T>(p: string, form: FormData) =>
  http<T>(p, { method: 'POST', body: form });

// For <img>/<iframe> src or download links pointing at a backend route:
export const backendUrl = (path: string) => resolveUrl(path);

export interface Metric { metric: string; description: string }
export interface RawBlock { title: string; description: string; metrics: string }
export interface GeneratedItem { title: string; content: string }
export interface MemoPayload { memo_title: string; blocks: Array<{ title: string; description: string; metrics: string }> }

export const api = {
  metrics: () => get<{ items: Metric[] }>('/metrics'),
  memos: () => get<{ memos: string[] }>('/memos'),
  memo: (id: string) =>
    get<{ memo_title: string; blocks: RawBlock[]; generated: GeneratedItem[] }>(
      '/memo?memo_id=' + encodeURIComponent(id),
    ),
  saveStructure: (p: MemoPayload) =>
    postJson<{ status: string; count: number; memos: string[] }>('/structure', p),
  runAgent: (p: MemoPayload) =>
    postJson<{ status: string; items: GeneratedItem[]; memos: string[] }>('/run_agent', p),
  clearGenerated: (memo_title: string) =>
    postJson<{ status: string }>('/clear_generated', { memo_title }),
  deleteGenerated: (memo_title: string, title: string) =>
    postJson<{ status: string; items: GeneratedItem[] }>('/delete_generated', { memo_title, title }),
  deleteMemo: (memo_title: string) =>
    postJson<{ status: string; memos: string[] }>('/delete_memo', { memo_title }),
  importMemo: (file: File) => {
    const fd = new FormData();
    fd.append('file', file);
    return postForm<{ status: string; memos: string[]; new_ids: string[] }>('/import_memo', fd);
  },
  addMetrics: (files: File[]) => {
    const fd = new FormData();
    files.forEach((f) => fd.append('files', f));
    return postForm<{ status: string; items: Metric[] }>('/add_metrics', fd);
  },
  runPython: (code: string) =>
    postJson<{ status: string; image?: string; message?: string }>('/run_python', { code }),
  inputKpi: () => get<{ columns: string[]; rows: unknown[][] }>('/input_kpi'),
  documentUrl: (name: string) => backendUrl('/document?name=' + encodeURIComponent(name)),
};
