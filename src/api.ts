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
const postJson = <T>(p: string, body?: unknown, timeout?: number) =>
  http<T>(p, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: body == null ? undefined : JSON.stringify(body),
  }, timeout);
const postForm = <T>(p: string, form: FormData) =>
  http<T>(p, { method: 'POST', body: form });

// For <img>/<iframe> src or download links pointing at a backend route:
export const backendUrl = (path: string) => resolveUrl(path);

export interface KpiOption { kpi: string; category: string }
export interface RawBlock { title: string; description: string; metrics: string }
export interface GeneratedItem { title: string; content: string }
export interface MemoPayload { memo_title: string; blocks: Array<{ title: string; description: string; metrics: string }> }

export interface KpiSource { source: string; quote: string }
export interface KpiMetric { metric: string; sources: KpiSource[] }
export interface KpiValue { fiscal_year: number | string | null; kpi_value: number | string | null }
export interface MergedKpi {
  kpi: string;
  category: string;
  type: 'computed' | 'input';
  formula?: string;
  metrics?: KpiMetric[];
  sources?: KpiSource[];
  values: KpiValue[];
}

export const api = {
  allKpi: () => get<{ items: KpiOption[] }>('/all_kpi'),
  memos: () => get<{ memos: string[] }>('/memos'),
  memo: (id: string) =>
    get<{ memo_title: string; blocks: RawBlock[]; generated: GeneratedItem[] }>(
      '/memo?memo_id=' + encodeURIComponent(id),
    ),
  saveStructure: (p: MemoPayload) =>
    postJson<{ status: string; count: number; memos: string[] }>('/structure', p),
  runAgent: (p: MemoPayload) =>
    postJson<{ status: string; items: GeneratedItem[]; memos: string[] }>('/run_agent', p),
  runAgentSection: (p: {
    memo_title: string;
    block: { title: string; description: string; metrics: string };
    instruction?: string;
    previous?: string;
  }) =>
    postJson<{ status: string; message?: string; items: GeneratedItem[]; content?: string }>(
      '/run_agent_section', p,
    ),
  generated: (id: string) =>
    get<{ items: GeneratedItem[] }>('/generated?memo_id=' + encodeURIComponent(id)),
  saveGenerated: (p: { memo_title: string; title: string; content: string }) =>
    postJson<{ status: string; items: GeneratedItem[] }>('/save_generated', p),
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
  runPython: (code: string) =>
    postJson<{ status: string; image?: string; message?: string }>('/run_python', { code }),
  kpiFull: () => get<{ items: MergedKpi[] }>('/kpi_full'),
  inputKpi: () => get<{ columns: string[]; rows: unknown[][] }>('/input_kpi'),
  runKpiExtraction: () =>
    postJson<{ status: string; message?: string; columns: string[]; rows: unknown[][] }>(
      '/run_kpi_extraction', undefined, 600000,   // agent run: allow up to 10 min
    ),
  cleanInputKpi: () =>
    postJson<{ status: string; message?: string; columns: string[]; rows: unknown[][]; cleared: string[] }>(
      '/clean_input_kpi',
    ),
  documentUrl: (name: string) => backendUrl('/document?name=' + encodeURIComponent(name)),
  excelPreview: (name: string) =>
    get<{ sheets: ExcelSheet[]; error?: string }>('/excel_preview?name=' + encodeURIComponent(name)),
};

export interface ExcelSheet {
  name: string;
  columns: string[];
  rows: string[][];
  truncated: boolean;
  total_rows: number;
}

// Which source documents can be previewed as a spreadsheet vs a PDF.
export const isExcelName = (name: string): boolean => /\.(xlsx|xls|xlsm)$/i.test(name || '');

// Source names may carry a trailing sheet name in parentheses, e.g.
// "TerraNova_..._Aging.xlsx (Debt Schedule)" -> { file, sheet }.
export function parseSourceName(raw: string): { file: string; sheet: string } {
  const s = (raw || '').trim();
  const m = /^(.*\.(?:xlsx|xls|xlsm|pdf|docx?|csv|txt|pptx?))\s*(?:\(([^)]*)\))?\s*$/i.exec(s);
  return m ? { file: m[1].trim(), sheet: (m[2] || '').trim() } : { file: s, sheet: '' };
}
