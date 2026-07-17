<script setup lang="ts">
  import { ref, watch, onMounted, nextTick } from 'vue';
  import { FileText, FileSpreadsheet } from 'lucide-vue-next';
  import { renderRich, typesetMath, extractSources, type SourceRef } from '@/lib/markdown';
  import { api, isExcelName } from '@/api';

  const props = defineProps<{ content: string }>();
  const emit = defineEmits<{ (e: 'open-source', file: string): void }>();
  const root = ref<HTMLElement | null>(null);
  const html = ref('');
  const sources = ref<SourceRef[]>([]);

  function showChartError(id: string, msg?: string) {
    const box = document.getElementById(id);
    if (!box) return;
    box.innerHTML = '';
    const span = document.createElement('span');
    span.className = 'py-error';
    span.textContent = '⚠︎ No chart could be generated from this code'
      + (msg ? ': ' + msg : '.');
    box.appendChild(span);
  }

  async function renderChart(id: string, code: string) {
    try {
      const res = await api.runPython(code);
      const box = document.getElementById(id);
      if (!box) return;
      if (res.status === 'ok' && res.image) {
        box.innerHTML = `<img class="py-chart-img" alt="Generated chart" src="data:image/png;base64,${res.image}">`;
      } else {
        showChartError(id, res.message);
      }
    } catch (e) {
      showChartError(id, (e as Error).message);
    }
  }

  async function update() {
    const { body, sources: srcs } = extractSources(props.content);
    sources.value = srcs;
    const { html: h, charts } = renderRich(body);
    html.value = h;
    await nextTick();
    if (root.value) {
      try { typesetMath(root.value); } catch { /* ignore KaTeX errors */ }
    }
    charts.forEach((c) => renderChart(c.id, c.code));
  }

  onMounted(update);
  watch(() => props.content, update);
</script>

<template>
  <div>
    <div ref="root" class="memo-content" v-html="html" />

    <!-- Clickable "Sources Used" footer -->
    <div v-if="sources.length" class="memo-sources">
      <span class="memo-sources-label">Sources</span>
      <button v-for="s in sources" :key="s.file" type="button"
        class="memo-source-chip" :title="s.label" @click="emit('open-source', s.file)">
        <FileSpreadsheet v-if="isExcelName(s.file)" class="memo-source-icon" />
        <FileText v-else class="memo-source-icon" />
        {{ s.file }}
      </button>
    </div>
  </div>
</template>

<style scoped>
  .memo-sources {
    display: flex; flex-wrap: wrap; align-items: center; gap: .4rem;
    margin-top: .75rem; padding-top: .6rem;
    border-top: 1px dashed color-mix(in oklab, var(--primary) 25%, transparent);
  }
  .memo-sources-label {
    font-size: .7rem; font-weight: 600; text-transform: uppercase; letter-spacing: .04em;
    color: var(--muted-foreground); margin-right: .15rem;
  }
  .memo-source-chip {
    display: inline-flex; align-items: center; gap: .35rem;
    padding: .2rem .6rem; font-size: .75rem; font-weight: 500;
    border-radius: 9999px; cursor: pointer;
    color: var(--primary);
    background: color-mix(in oklab, var(--primary) 10%, transparent);
    border: 1px solid color-mix(in oklab, var(--primary) 22%, transparent);
    transition: background .12s, border-color .12s;
    max-width: 100%; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
  }
  .memo-source-chip:hover {
    background: color-mix(in oklab, var(--primary) 18%, transparent);
    border-color: color-mix(in oklab, var(--primary) 40%, transparent);
  }
  .memo-source-icon { width: .85rem; height: .85rem; flex-shrink: 0; }
</style>
