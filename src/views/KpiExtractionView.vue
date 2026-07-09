<script setup lang="ts">
  import { ref, computed, onMounted } from 'vue';
  import { FileSearch } from 'lucide-vue-next';
  import { Card, CardContent } from '@/components/ui/card';
  import { Button } from '@/components/ui/button';
  import {
    Dialog, DialogContent, DialogHeader, DialogTitle,
  } from '@/components/ui/dialog';
  import PdfViewer from '@/components/PdfViewer.vue';
  import { api } from '@/api';

  const columns = ref<string[]>([]);
  const rows = ref<unknown[][]>([]);
  const loading = ref(true);

  const open = ref(false);
  const activeDoc = ref('');
  const activeQuote = ref('');

  const sourceIdx = computed(() => columns.value.indexOf('source'));
  const quoteIdx = computed(() => columns.value.indexOf('quote'));
  // Columns shown in the table (quote is long/noisy → seen in the reader instead).
  const displayCols = computed(() =>
    columns.value.map((c, i) => ({ name: c, i })).filter((c) => c.name !== 'quote'),
  );

  function cell(row: unknown[], i: number): string {
    const v = row[i];
    return v == null ? '' : String(v);
  }

  function openSource(row: unknown[]) {
    activeDoc.value = cell(row, sourceIdx.value);
    activeQuote.value = quoteIdx.value >= 0 ? cell(row, quoteIdx.value) : '';
    open.value = true;
  }

  onMounted(async () => {
    try {
      const d = await api.inputKpi();
      columns.value = d.columns || [];
      rows.value = d.rows || [];
    } catch { /* backend unavailable */ }
    loading.value = false;
  });
</script>

<template>
  <div class="max-w-5xl mx-auto px-8 py-10">
    <h1 class="text-2xl font-semibold mb-1">KPI Extraction</h1>
    <p class="text-muted-foreground mb-8">
      Metrics the agent extracted into <code class="text-foreground">input_KPI</code>.
      Click a source to see its quote highlighted in the document.
    </p>

    <Card>
      <CardContent class="p-0 overflow-x-auto">
        <table v-if="rows.length" class="kpi-table">
          <thead>
            <tr>
              <th v-for="c in displayCols" :key="c.i">{{ c.name }}</th>
              <th class="w-px"></th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(row, r) in rows" :key="r">
              <td v-for="c in displayCols" :key="c.i">{{ cell(row, c.i) }}</td>
              <td class="text-right whitespace-nowrap">
                <Button v-if="sourceIdx >= 0 && cell(row, sourceIdx)"
                  variant="ghost" size="sm" class="h-7 gap-1.5 text-primary"
                  @click="openSource(row)">
                  <FileSearch class="h-3.5 w-3.5" /> Source
                </Button>
              </td>
            </tr>
          </tbody>
        </table>
        <div v-else class="py-10 text-center text-muted-foreground">
          {{ loading ? 'Loading…' : 'No KPI extracted yet.' }}
        </div>
      </CardContent>
    </Card>

    <Dialog v-model:open="open">
      <DialogContent class="w-[92vw] max-w-[1100px]">
        <DialogHeader>
          <DialogTitle class="truncate">{{ activeDoc || 'Source document' }}</DialogTitle>
        </DialogHeader>
        <PdfViewer v-if="open && activeDoc" :url="api.documentUrl(activeDoc)" :highlight="activeQuote" />
        <div v-if="activeQuote" class="mt-1">
          <div class="text-xs font-medium text-muted-foreground mb-1">Extracted quote</div>
          <pre class="kpi-quote">{{ activeQuote }}</pre>
        </div>
      </DialogContent>
    </Dialog>
  </div>
</template>

<style scoped>
  .kpi-table { width: 100%; border-collapse: collapse; font-size: .8125rem; }
  .kpi-table th {
    text-align: left; font-weight: 600; color: var(--muted-foreground);
    padding: .55rem .85rem; border-bottom: 1px solid var(--border); white-space: nowrap;
    text-transform: capitalize;
  }
  .kpi-table td { padding: .5rem .85rem; border-bottom: 1px solid var(--border); vertical-align: top; }
  .kpi-table tbody tr:hover { background: var(--accent); }
  .kpi-quote {
    margin: 0; max-height: 22vh; overflow: auto; white-space: pre-wrap; word-break: break-word;
    font-size: .75rem; line-height: 1.45; color: var(--foreground);
    background: var(--muted); border-radius: var(--radius-md); padding: .6rem .8rem;
  }
</style>
