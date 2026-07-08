import { defineStore } from 'pinia';

export interface Block {
  id: number;
  title: string;
  description: string;
  metrics: string[];
}

export interface Memo {
  id: number;
  title: string;
  blocks: Block[];
  generated: Record<string, string>; // normalizedTitle -> markdown paragraph
}

export interface Metric {
  metric: string;
  description: string;
}

let uid = 100;
const nextId = () => ++uid;

function emptyBlock(): Block {
  return { id: nextId(), title: '', description: '', metrics: [] };
}

function seedMemo(title: string, blocks: Array<Partial<Block>>): Memo {
  return {
    id: nextId(),
    title,
    blocks: blocks.map((b) => ({
      id: nextId(),
      title: b.title || '',
      description: b.description || '',
      metrics: b.metrics || [],
    })),
    generated: {},
  };
}

// A mock "agent" that fabricates an on-topic paragraph for a block.
// Demonstrates the rich renderer: Markdown, KaTeX math, LaTeX tables, <python>.
function mockParagraph(block: Block): string {
  const intro =
    `## ${block.title}\n\n` +
    `${block.description || 'This section summarises the relevant findings for the memo.'} ` +
    `Based on the available data, the analysis indicates a **stable** outlook.`;

  const metricsLine = block.metrics.length
    ? `\n\nKey metrics considered: **${block.metrics.join('**, **')}**.`
    : '';

  // On a "financial" section, showcase a formula + a LaTeX table + a chart snippet.
  if (/financ|analysis|leverage/i.test(block.title)) {
    return intro + metricsLine +
      `\n\nThe leverage ratio is $\\frac{\\text{Net debt}}{\\text{EBITDA}} = 2.4$, within covenant limits.\n\n` +
      `\\begin{table}[h!]\n\\centering\n\\begin{tabular}{|c|c|c|}\n\\hline\n` +
      `\\textbf{Year} & \\textbf{Revenue (\\$m)} & \\textbf{EBITDA margin (\\%)} \\\\ \\hline\n` +
      `2022 & 120 & 20.73 \\\\ \\hline\n2023 & 134 & 20.14 \\\\ \\hline\n2024 & 151 & 19.13 \\\\ \\hline\n` +
      `\\end{tabular}\n\\caption{Revenue and EBITDA margin trend}\n\\end{table}\n\n` +
      `<python>\nimport matplotlib.pyplot as plt\nyears = ['2022', '2023', '2024']\nmargins = [20.73, 20.14, 19.13]\nplt.plot(years, margins, marker='o')\nplt.title('EBITDA Margin Trend (%)')\nplt.show()\n</python>`;
  }
  return intro +
    ` A few areas warrant close monitoring over the next reporting period.${metricsLine}`;
}

export const useMemoStore = defineStore('memo', {
  state: () => ({
    metrics: [
      { metric: 'Net debt / EBITDA', description: 'Leverage ratio of the counterparty.' },
      { metric: 'Interest coverage', description: 'EBIT divided by interest expense.' },
      { metric: 'Current ratio', description: 'Current assets over current liabilities.' },
      { metric: 'Debt / Equity', description: 'Total debt relative to shareholder equity.' },
      { metric: 'Revenue growth', description: 'Year-over-year revenue change.' },
      { metric: 'Free cash flow', description: 'Operating cash flow minus capex.' },
    ] as Metric[],
    memos: [
      seedMemo('Acme Corp — 2026 annual credit review', [
        { title: 'Counterparty overview', description: 'Business profile, ownership and sector.', metrics: [] },
        { title: 'Financial analysis', description: 'Leverage, liquidity and profitability.', metrics: ['Net debt / EBITDA', 'Interest coverage'] },
        { title: 'Risks & mitigants', description: 'Main risks and how they are mitigated.', metrics: [] },
      ]),
      seedMemo('Globex Ltd — facility renewal', [
        { title: 'Purpose of the request', description: 'Renewal of the revolving facility.', metrics: [] },
        { title: 'Financial analysis', description: 'Trend over the last three years.', metrics: ['Revenue growth', 'Free cash flow'] },
      ]),
    ] as Memo[],
    currentMemoId: null as number | null,
  }),

  getters: {
    currentMemo(state): Memo | null {
      return state.memos.find((m) => m.id === state.currentMemoId) || null;
    },
    metricNames(state): string[] {
      return state.metrics.map((m) => m.metric);
    },
  },

  actions: {
    ensureSelection() {
      if (this.currentMemoId == null && this.memos.length) {
        this.currentMemoId = this.memos[0].id;
      }
    },
    selectMemo(id: number) {
      this.currentMemoId = id;
    },
    newMemo() {
      const memo: Memo = { id: nextId(), title: '', blocks: [emptyBlock()], generated: {} };
      this.memos.unshift(memo);
      this.currentMemoId = memo.id;
      return memo;
    },
    addBlock() {
      this.currentMemo?.blocks.push(emptyBlock());
    },
    removeBlock(blockId: number) {
      const memo = this.currentMemo;
      if (!memo) return;
      memo.blocks = memo.blocks.filter((b) => b.id !== blockId);
      if (!memo.blocks.length) memo.blocks.push(emptyBlock());
    },
    moveBlock(from: number, to: number) {
      const memo = this.currentMemo;
      if (!memo || to < 0 || to >= memo.blocks.length) return;
      const [moved] = memo.blocks.splice(from, 1);
      memo.blocks.splice(to, 0, moved);
    },
    toggleMetric(blockId: number, metric: string) {
      const block = this.currentMemo?.blocks.find((b) => b.id === blockId);
      if (!block) return;
      const i = block.metrics.indexOf(metric);
      if (i === -1) block.metrics.push(metric);
      else block.metrics.splice(i, 1);
    },
    runAgent() {
      const memo = this.currentMemo;
      if (!memo) return 0;
      memo.generated = {};
      memo.blocks.forEach((b) => {
        if (b.title.trim()) memo.generated[b.title.trim().toLowerCase()] = mockParagraph(b);
      });
      return Object.keys(memo.generated).length;
    },
    clearGenerated() {
      if (this.currentMemo) this.currentMemo.generated = {};
    },
    deleteGenerated(title: string) {
      const memo = this.currentMemo;
      if (memo) delete memo.generated[title.trim().toLowerCase()];
    },
    deleteMemo(id: number) {
      this.memos = this.memos.filter((m) => m.id !== id);
      if (this.currentMemoId === id) this.currentMemoId = this.memos[0]?.id ?? null;
    },
    addMetrics(fileNames: string[]) {
      // Mock extraction: derive one metric per uploaded document.
      fileNames.forEach((name, i) => {
        const base = name.replace(/\.[^.]+$/, '');
        const metric = `Metric from ${base}`;
        if (!this.metrics.some((m) => m.metric.toLowerCase() === metric.toLowerCase())) {
          this.metrics.push({ metric, description: `Extracted from ${name}.` });
        }
        void i;
      });
    },
    importMemo(fileName: string) {
      const base = fileName.replace(/\.[^.]+$/, '');
      const memo = seedMemo(base, [
        { title: 'Executive summary', description: 'Auto-extracted from the imported document.' },
        { title: 'Financial analysis', description: 'Auto-extracted from the imported document.', metrics: ['Net debt / EBITDA'] },
        { title: 'Conclusion', description: 'Auto-extracted from the imported document.' },
      ]);
      this.memos.unshift(memo);
      this.currentMemoId = memo.id;
      return memo;
    },
  },
});
