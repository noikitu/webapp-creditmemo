<script setup lang="ts">
  import { ref, watch, onMounted, nextTick } from 'vue';
  import { renderRich, typesetMath } from '@/lib/markdown';
  import { api } from '@/api';

  const props = defineProps<{ content: string }>();
  const root = ref<HTMLElement | null>(null);
  const html = ref('');

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
    const { html: h, charts } = renderRich(props.content);
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
  <div ref="root" class="memo-content" v-html="html" />
</template>
