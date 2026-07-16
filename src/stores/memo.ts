import { defineStore } from 'pinia';
import { api, type KpiOption } from '@/api';

export interface Block { id: number; title: string; description: string; metrics: string[]; }
export interface Memo { title: string; blocks: Block[]; generated: Record<string, string>; }

let uid = 0;
const nextId = () => ++uid;
const emptyBlock = (): Block => ({ id: nextId(), title: '', description: '', metrics: [] });

// The metrics column of structure_memo stores a JSON list (e.g. ["Current Ratio"]).
// Older rows may still hold a comma-separated string — parse both.
function parseMetrics(raw: string): string[] {
  const s = String(raw || '').trim();
  if (!s) return [];
  try {
    const v = JSON.parse(s);
    if (Array.isArray(v)) return v.map(String).map((t) => t.trim()).filter(Boolean);
  } catch { /* legacy format */ }
  return s.split(',').map((t) => t.trim()).filter(Boolean);
}

function toBlocks(raw: { title: string; description: string; metrics: string }[]): Block[] {
  return raw.map((b) => ({
    id: nextId(),
    title: b.title || '',
    description: b.description || '',
    metrics: parseMetrics(b.metrics),
  }));
}

function genMap(items: { title: string; content: string }[]): Record<string, string> {
  const m: Record<string, string> = {};
  (items || []).forEach((it) => {
    const k = (it.title || '').trim().toLowerCase();
    if (k) m[k] = it.content || '';
  });
  return m;
}

function payload(memo: Memo) {
  return {
    memo_title: memo.title.trim(),
    blocks: memo.blocks.map((b) => ({
      title: b.title.trim(),
      description: b.description.trim(),
      metrics: JSON.stringify(b.metrics),   // JSON list — easy to parse downstream
    })),
  };
}

// Mock "agent": rich paragraph (Markdown + KaTeX + LaTeX table + <python>).
function mockParagraph(block: Block): string {
  const intro = `## ${block.title}\n\n${block.description || 'This section summarises the relevant findings.'} ` +
    `Based on the available data, the analysis indicates a **stable** outlook.`;
  const metricsLine = block.metrics.length ? `\n\nKPIs to include: **${block.metrics.join('**, **')}**.` : '';
  if (/financ|analysis|leverage/i.test(block.title)) {
    return intro + metricsLine +
      `\n\nThe leverage ratio is $\\frac{\\text{Net debt}}{\\text{EBITDA}} = 2.4$, within covenant limits.\n\n` +
      `\\begin{table}[h!]\n\\centering\n\\begin{tabular}{|c|c|c|}\n\\hline\n` +
      `\\textbf{Year} & \\textbf{Revenue (\\$m)} & \\textbf{EBITDA margin (\\%)} \\\\ \\hline\n` +
      `2022 & 120 & 20.73 \\\\ \\hline\n2023 & 134 & 20.14 \\\\ \\hline\n2024 & 151 & 19.13 \\\\ \\hline\n` +
      `\\end{tabular}\n\\caption{Revenue and EBITDA margin trend}\n\\end{table}\n\n` +
      `<python>\nimport matplotlib.pyplot as plt\nplt.plot(['2022','2023','2024'], [20.73, 20.14, 19.13], marker='o')\nplt.title('EBITDA Margin Trend (%)')\nplt.show()\n</python>`;
  }
  return intro + ` A few areas warrant close monitoring over the next reporting period.${metricsLine}`;
}

const MOCK_KPIS: KpiOption[] = [
  { kpi: 'Current Ratio', category: 'Liquidity' },
  { kpi: 'Debt / Equity', category: 'Leverage' },
  { kpi: 'Total Debt / EBITDA', category: 'Leverage' },
  { kpi: 'EBITDA Margin', category: 'Profitability' },
  { kpi: 'Net Profit Margin', category: 'Profitability' },
  { kpi: 'Return on Equity (ROE)', category: 'Profitability' },
  { kpi: 'EBITDA', category: 'Reported' },
  { kpi: 'Free cash flow', category: 'Reported' },
];

function mockSeed(): { memos: string[]; store: Record<string, Memo> } {
  const store: Record<string, Memo> = {
    'Acme Corp — 2026 annual credit review': {
      title: 'Acme Corp — 2026 annual credit review',
      blocks: toBlocks([
        { title: 'Counterparty overview', description: 'Business profile, ownership and sector.', metrics: '' },
        { title: 'Financial analysis', description: 'Leverage, liquidity and profitability.', metrics: '["Total Debt / EBITDA","EBITDA Margin"]' },
        { title: 'Risks & mitigants', description: 'Main risks and how they are mitigated.', metrics: '' },
      ]),
      generated: {},
    },
    'Globex Ltd — facility renewal': {
      title: 'Globex Ltd — facility renewal',
      blocks: toBlocks([
        { title: 'Purpose of the request', description: 'Renewal of the revolving facility.', metrics: '' },
        { title: 'Financial analysis', description: 'Trend over the last three years.', metrics: '["Free cash flow"]' },
      ]),
      generated: {},
    },
  };
  return { memos: Object.keys(store), store };
}

export const useMemoStore = defineStore('memo', {
  state: () => ({
    booted: false,
    backendReady: false,
    kpiOptions: [] as KpiOption[],         // selectable KPIs (all_KPI dataset)
    memos: [] as string[],                 // ordered memo titles (sidebar)
    store: {} as Record<string, Memo>,     // loaded memos, keyed by title
    current: null as Memo | null,
  }),

  getters: {
    blockCount: (s) => (title: string): number | null =>
      s.store[title] ? s.store[title].blocks.length : null,
  },

  actions: {
    async boot() {
      if (this.booted) return;
      this.booted = true;
      try {
        const [k, mm] = await Promise.all([api.kpiFull(), api.memos()]);
        // Only offer KPIs that actually have values (skip empty ones).
        this.kpiOptions = (k.items || [])
          .filter((it) => (it.values || []).some((v) => v.kpi_value != null && v.kpi_value !== ''))
          .map((it) => ({ kpi: it.kpi, category: it.category }));
        this.memos = mm.memos;
        this.backendReady = true;
        if (this.memos.length) await this.selectMemo(this.memos[0]);
        else this.newMemo();
      } catch {
        // No DSS backend (local dev): fall back to mock data.
        const s = mockSeed();
        this.kpiOptions = MOCK_KPIS;
        this.store = s.store; this.memos = s.memos;
        this.current = this.store[this.memos[0]] || null;
      }
    },

    async selectMemo(title: string) {
      if (this.store[title]) { this.current = this.store[title]; return; }
      if (this.backendReady) {
        try {
          const d = await api.memo(title);
          const memo: Memo = {
            title: d.memo_title || title,
            blocks: toBlocks(d.blocks),
            generated: genMap(d.generated),
          };
          if (!memo.blocks.length) memo.blocks = [emptyBlock()];
          this.store[title] = memo; this.current = memo; return;
        } catch { /* fall through */ }
      }
      this.current = { title, blocks: [emptyBlock()], generated: {} };
    },

    newMemo() { this.current = { title: '', blocks: [emptyBlock()], generated: {} }; },

    addBlock() { this.current?.blocks.push(emptyBlock()); },
    removeBlock(id: number) {
      const m = this.current; if (!m) return;
      m.blocks = m.blocks.filter((b) => b.id !== id);
      if (!m.blocks.length) m.blocks.push(emptyBlock());
    },
    moveBlock(from: number, to: number) {
      const m = this.current; if (!m || to < 0 || to >= m.blocks.length) return;
      const [x] = m.blocks.splice(from, 1); m.blocks.splice(to, 0, x);
    },
    toggleMetric(id: number, metric: string) {
      const b = this.current?.blocks.find((x) => x.id === id); if (!b) return;
      const i = b.metrics.indexOf(metric);
      if (i === -1) b.metrics.push(metric); else b.metrics.splice(i, 1);
    },

    registerCurrent() {
      const m = this.current; if (!m || !m.title.trim()) return;
      this.store[m.title] = m;
      if (!this.memos.some((t) => t.toLowerCase() === m.title.toLowerCase())) {
        this.memos = [...this.memos, m.title].sort((a, b) => a.toLowerCase().localeCompare(b.toLowerCase()));
      }
    },

    async saveStructure() {
      const m = this.current; if (!m) return;
      this.registerCurrent();
      if (this.backendReady) {
        try { const r = await api.saveStructure(payload(m)); this.memos = r.memos; } catch { /* keep local */ }
      }
    },

    async runAgent(): Promise<number> {
      const m = this.current; if (!m) return 0;
      this.registerCurrent();
      if (this.backendReady) {
        try {
          const r = await api.runAgent(payload(m));
          m.generated = genMap(r.items); this.memos = r.memos;
          return Object.keys(m.generated).length;
        } catch { /* fall through to mock */ }
      }
      m.generated = {};
      m.blocks.forEach((b) => { if (b.title.trim()) m.generated[b.title.trim().toLowerCase()] = mockParagraph(b); });
      return Object.keys(m.generated).length;
    },

    // Regenerate one section only, optionally with a revision instruction.
    // Returns true if the paragraph was (re)written.
    async runAgentSection(block: Block, instruction: string): Promise<boolean> {
      const m = this.current; if (!m || !block.title.trim()) return false;
      this.registerCurrent();
      const key = block.title.trim().toLowerCase();
      if (this.backendReady) {
        const r = await api.runAgentSection({
          memo_title: m.title.trim(),
          block: {
            title: block.title.trim(),
            description: block.description.trim(),
            metrics: JSON.stringify(block.metrics),
          },
          instruction: instruction.trim(),
          previous: m.generated[key] || '',
        });
        m.generated = genMap(r.items);
        if (r.status !== 'ok') throw new Error(r.message || 'Agent produced no output.');
        return true;
      }
      // Mock: rewrite the paragraph, noting the instruction if any.
      const base = mockParagraph(block);
      m.generated[key] = instruction.trim()
        ? base + `\n\n_Revised per instruction: “${instruction.trim()}”._`
        : base;
      return true;
    },

    async refreshGenerated() {
      const m = this.current;
      if (!m || !this.backendReady) return;
      try { const r = await api.generated(m.title); m.generated = genMap(r.items); } catch { /* ignore */ }
    },

    async clearGenerated() {
      const m = this.current; if (!m) return;
      m.generated = {};
      if (this.backendReady) { try { await api.clearGenerated(m.title); } catch { /* ignore */ } }
    },
    async deleteGenerated(title: string) {
      const m = this.current; if (!m) return;
      delete m.generated[title.trim().toLowerCase()];
      if (this.backendReady) { try { const r = await api.deleteGenerated(m.title, title); m.generated = genMap(r.items); } catch { /* ignore */ } }
    },

    async deleteMemo(title: string) {
      delete this.store[title];
      this.memos = this.memos.filter((t) => t.toLowerCase() !== title.toLowerCase());
      if (this.current && this.current.title.toLowerCase() === title.toLowerCase()) {
        if (this.memos.length) await this.selectMemo(this.memos[0]);
        else this.newMemo();
      }
      if (this.backendReady) { try { const r = await api.deleteMemo(title); this.memos = r.memos; } catch { /* ignore */ } }
    },

    async importMemo(file: File): Promise<string> {
      if (this.backendReady) {
        try {
          const r = await api.importMemo(file);
          this.memos = r.memos;
          const id = (r.new_ids && r.new_ids[0]) || r.memos[0];
          if (id) await this.selectMemo(id);
          return id || '';
        } catch { /* fall through */ }
      }
      const base = file.name.replace(/\.[^.]+$/, '');
      const memo: Memo = {
        title: base,
        blocks: toBlocks([
          { title: 'Executive summary', description: 'Auto-extracted from the imported document.', metrics: '' },
          { title: 'Financial analysis', description: 'Auto-extracted from the imported document.', metrics: '["Total Debt / EBITDA"]' },
          { title: 'Conclusion', description: 'Auto-extracted from the imported document.', metrics: '' },
        ]),
        generated: {},
      };
      this.store[base] = memo;
      if (!this.memos.includes(base)) this.memos = [base, ...this.memos];
      this.current = memo;
      return base;
    },
  },
});
