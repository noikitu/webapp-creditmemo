// Rich renderer for agent paragraphs: Markdown + LaTeX tables + KaTeX math
// + <python> code blocks. Dependency-free except KaTeX (bundled).
import 'katex/dist/katex.min.css';
import renderMathInElement from 'katex/contrib/auto-render';

function escapeHtml(s: string): string {
  return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}

function inlineMd(t: string): string {
  return t
    .replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
    .replace(/__([^_]+)__/g, '<strong>$1</strong>')
    .replace(/(^|[^*])\*([^*]+)\*/g, '$1<em>$2</em>')
    .replace(/(^|[^_])_([^_]+)_/g, '$1<em>$2</em>')
    .replace(/`([^`]+)`/g, '<code>$1</code>');
}

function renderMarkdown(src: string): string {
  if (!src) return '';
  const lines = escapeHtml(src).split(/\r?\n/);
  const out: string[] = [];
  let para: string[] = [];
  let listType: 'ul' | 'ol' | null = null;

  const flushPara = () => {
    if (para.length) { out.push('<p>' + para.map(inlineMd).join('<br>') + '</p>'); para = []; }
  };
  const closeList = () => { if (listType) { out.push('</' + listType + '>'); listType = null; } };

  for (const line of lines) {
    const h = /^(#{1,6})\s+(.*)$/.exec(line);
    const ul = /^\s*[-*+]\s+(.*)$/.exec(line);
    const ol = /^\s*\d+\.\s+(.*)$/.exec(line);
    if (/^\s*$/.test(line)) { flushPara(); closeList(); continue; }
    if (h) { flushPara(); closeList(); out.push(`<h${h[1].length}>${inlineMd(h[2])}</h${h[1].length}>`); continue; }
    if (ul) { flushPara(); if (listType !== 'ul') { closeList(); out.push('<ul>'); listType = 'ul'; } out.push('<li>' + inlineMd(ul[1]) + '</li>'); continue; }
    if (ol) { flushPara(); if (listType !== 'ol') { closeList(); out.push('<ol>'); listType = 'ol'; } out.push('<li>' + inlineMd(ol[1]) + '</li>'); continue; }
    closeList(); para.push(line);
  }
  flushPara(); closeList();
  return out.join('');
}

// ---- LaTeX tabular/table -> HTML table -----------------------------------
function cleanLatexInline(s: string): string {
  return escapeHtml(s)
    .replace(/\\textbf\{([^}]*)\}/g, '<strong>$1</strong>')
    .replace(/\\textit\{([^}]*)\}/g, '<em>$1</em>')
    .replace(/\\%/g, '%').replace(/\\_/g, '_').replace(/\\\$/g, '$').replace(/\\#/g, '#')
    .replace(/\\&/g, '&amp;')
    .replace(/[{}]/g, '')
    .trim();
}

function tabularToHtml(body: string): string {
  body = body.replace(/\\(?:hline|centering|toprule|midrule|bottomrule)/g, '');
  const rows = body.split(/\\\\/).map((r) => r.trim()).filter((r) => r.length);
  let out = '<table class="memo-table">';
  rows.forEach((row, ri) => {
    const tag = ri === 0 ? 'th' : 'td';
    const cells = row.split('&').map((c) => cleanLatexInline(c.trim()));
    out += '<tr>' + cells.map((c) => `<${tag}>${c}</${tag}>`).join('') + '</tr>';
  });
  return out + '</table>';
}

function latexTableEnv(inner: string): string {
  let caption = '';
  const cm = /\\caption\{([^}]*)\}/.exec(inner);
  if (cm) caption = cleanLatexInline(cm[1]);
  const tm = /\\begin\{tabular\}\{[^}]*\}([\s\S]*?)\\end\{tabular\}/.exec(inner);
  const table = tm ? tabularToHtml(tm[1]) : '';
  return '<figure class="memo-figure">' + table +
    (caption ? '<figcaption>' + caption + '</figcaption>' : '') + '</figure>';
}

const MATH_RE = /\$\$[\s\S]+?\$\$|\\\[[\s\S]+?\\\]|\\\([\s\S]+?\\\)|\$[^$\n]+?\$/g;

let pyCounter = 0;

export interface PyChart { id: string; code: string; }
export interface RichResult { html: string; charts: PyChart[]; }

export function codeBlock(code: string): string {
  return '<pre class="memo-code"><code>' + escapeHtml(code.trim()) + '</code></pre>';
}

// ---- Full pipeline -------------------------------------------------------
export function renderRich(src: string): RichResult {
  if (!src) return { html: '', charts: [] };
  const blocks: string[] = [];
  const math: string[] = [];
  const charts: PyChart[] = [];
  let s = String(src);

  // <python> code blocks -> chart placeholder (filled by /run_python later)
  s = s.replace(/<python>([\s\S]*?)<\/python>/gi, (_m, code) => {
    const id = 'pychart-' + (++pyCounter);
    charts.push({ id, code: String(code).trim() });
    blocks.push('<div class="py-chart" id="' + id + '"><span class="py-loading">Generating chart…</span></div>');
    return '\n\n@@BLOCK' + (blocks.length - 1) + '@@\n\n';
  });
  // LaTeX tables -> HTML
  s = s.replace(/\\begin\{table\}(?:\[[^\]]*\])?([\s\S]*?)\\end\{table\}/g, (_m, inner) => {
    blocks.push(latexTableEnv(inner));
    return '\n\n@@BLOCK' + (blocks.length - 1) + '@@\n\n';
  });
  s = s.replace(/\\begin\{tabular\}\{[^}]*\}([\s\S]*?)\\end\{tabular\}/g, (_m, body) => {
    blocks.push(tabularToHtml(body));
    return '\n\n@@BLOCK' + (blocks.length - 1) + '@@\n\n';
  });
  // Math spans -> placeholders (Markdown must not mangle _ and *)
  s = s.replace(MATH_RE, (m) => { math.push(m); return '@@MATH' + (math.length - 1) + '@@'; });

  let html = renderMarkdown(s);
  html = html.replace(/@@MATH(\d+)@@/g, (_m, i) => escapeHtml(math[+i]));
  html = html
    .replace(/<p>\s*@@BLOCK(\d+)@@\s*<\/p>/g, (_m, i) => blocks[+i])
    .replace(/@@BLOCK(\d+)@@/g, (_m, i) => blocks[+i]);
  return { html, charts };
}

// ---- "Sources Used:" footer extraction -----------------------------------
export interface SourceRef { label: string; file: string; sheet: string; }
export interface ExtractResult { body: string; sources: SourceRef[]; }

const SOURCES_HEADER =
  /^\s*[*_#>\s]*sources?\s*(?:used|utilis[ée]s|consult[ée]s)?\s*[:：]/i;
// filename (+ optional trailing "(Sheet Name)" for Excel sources).
// Note: underscores are allowed (they're common in file names); only spaces,
// quotes, brackets, '*' and backticks are excluded.
const FILE_RE = /([^\s"'()<>*`]+\.(?:pdf|xlsx?|xlsm|docx?|csv|txt|pptx?))\s*(?:\(([^)]*)\))?/i;

function cleanSourceItem(s: string): string {
  return s
    .replace(/^\s*[-+•]\s+/, '')           // bullet (space-delimited; keep *emphasis*)
    .replace(/^\s*\d+[.)]\s*/, '')         // numbering
    .replace(/^[*_`~]+/, '')               // leading md emphasis wrapper (NOT inner _)
    .replace(/[*_`~]+$/, '')               // trailing md emphasis wrapper
    .replace(/^\s*["'“”[(]+|["'”\])]+\s*$/g, '')  // wrapping quotes/brackets
    .replace(/[.;,]+\s*$/, '')             // trailing punctuation
    .trim();
}

// Split off a trailing "Sources Used:" section into clickable document refs.
export function extractSources(src: string): ExtractResult {
  if (!src) return { body: '', sources: [] };
  const lines = src.split(/\r?\n/);
  let idx = -1;
  for (let i = 0; i < lines.length; i++) {
    if (SOURCES_HEADER.test(lines[i])) { idx = i; break; }
  }
  if (idx === -1) return { body: src, sources: [] };

  const afterColon = lines[idx].replace(SOURCES_HEADER, '');
  const rest = [afterColon, ...lines.slice(idx + 1)].join('\n');
  const items = rest.split(/[\n,;]+/).map((s) => s.trim()).filter(Boolean);

  const sources: SourceRef[] = [];
  const seen = new Set<string>();
  for (const raw of items) {
    const label = cleanSourceItem(raw);
    if (!label) continue;
    // Extract the file (and optional sheet) from the RAW item so markdown
    // wrappers (*, **, quotes) and the "(Sheet)" suffix stay intact.
    const m = FILE_RE.exec(raw);
    const file = m ? m[1] : label;
    const sheet = m && m[2] ? m[2].trim() : '';
    const key = (file + '|' + sheet).toLowerCase();
    if (seen.has(key)) continue;
    seen.add(key);
    sources.push({ label, file, sheet });
  }
  const body = lines.slice(0, idx).join('\n').replace(/\s+$/, '');
  return { body, sources };
}

export function typesetMath(el: HTMLElement): void {
  renderMathInElement(el, {
    delimiters: [
      { left: '$$', right: '$$', display: true },
      { left: '\\[', right: '\\]', display: true },
      { left: '\\(', right: '\\)', display: false },
      { left: '$', right: '$', display: false },
    ],
    throwOnError: false,
  });
}
