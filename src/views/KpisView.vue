<script setup lang="ts">
  import { ref, computed, onMounted } from 'vue';
  import { FileSearch, Sigma } from 'lucide-vue-next';
  import { Card, CardContent } from '@/components/ui/card';
  import { Button } from '@/components/ui/button';
  import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog';
  import PdfViewer from '@/components/PdfViewer.vue';
  import { api, type MergedKpi } from '@/api';
  import { cn } from '@/lib/utils';

  const kpis = ref<MergedKpi[]>([]);
  const loading = ref(true);
  const selected = ref<MergedKpi | null>(null);

  const open = ref(false);
  const activeDoc = ref('');
  const activeQuote = ref('');

  const categories = computed(() => {
    const seen: string[] = [];
    kpis.value.forEach((k) => { if (!seen.includes(k.category)) seen.push(k.category); });
    return seen;
  });
  function inCategory(c: string) { return kpis.value.filter((k) => k.category === c); }

  function openSource(source: string, quote: string) {
    activeDoc.value = source; activeQuote.value = quote; open.value = true;
  }
  function fmt(v: unknown): string {
    if (v == null || v === '') return '—';
    const n = Number(v);
    return Number.isFinite(n) ? n.toFixed(2) : String(v);
  }

  onMounted(async () => {
    try {
      const d = await api.kpiFull();
      kpis.value = d.items || [];
      selected.value = kpis.value[0] || null;
    } catch { /* backend unavailable */ }
    loading.value = false;
  });
</script>

<template>
  <div class="max-w-5xl mx-auto px-8 py-10">
    <h1 class="text-2xl font-semibold mb-1">KPIs</h1>
    <p class="text-muted-foreground mb-8">
      Every KPI from <code class="text-foreground">all_KPI</code>. Computed KPIs show their full
      lineage (formula, metrics, documents); extracted metrics show their source documents.
    </p>

    <div v-if="kpis.length" class="grid grid-cols-3 gap-6">
      <!-- Left: KPI list grouped by category -->
      <div class="col-span-1 space-y-4">
        <div v-for="c in categories" :key="c">
          <div class="text-xs font-medium uppercase tracking-wide text-muted-foreground mb-1.5">{{ c || 'Other' }}</div>
          <div class="space-y-1">
            <button v-for="k in inCategory(c)" :key="k.kpi" type="button"
              @click="selected = k"
              :class="cn('w-full flex items-center justify-between gap-2 text-left rounded-md px-3 py-2 text-sm transition-colors',
                selected && selected.kpi === k.kpi ? 'bg-primary/10 text-primary font-medium' : 'hover:bg-accent')">
              <span class="truncate">{{ k.kpi }}</span>
              <Sigma v-if="k.type === 'computed'" class="h-3.5 w-3.5 shrink-0 opacity-60" />
            </button>
          </div>
        </div>
      </div>

      <!-- Right: detail of the selected KPI -->
      <div class="col-span-2">
        <Card v-if="selected">
          <CardContent class="space-y-5">
            <div>
              <div class="flex items-center gap-2">
                <span class="text-lg font-semibold">{{ selected.kpi }}</span>
                <span class="rounded-full bg-muted px-2 py-0.5 text-[11px] font-medium text-muted-foreground">
                  {{ selected.type === 'computed' ? 'Computed' : 'Extracted' }}
                </span>
              </div>
              <div class="text-sm text-muted-foreground">{{ selected.category }}</div>
              <div v-if="selected.values.length" class="mt-2 flex flex-wrap gap-2">
                <span v-for="v in selected.values" :key="String(v.fiscal_year)"
                  class="rounded-md bg-muted px-2 py-1 text-xs">
                  {{ v.fiscal_year }} : <strong>{{ fmt(v.kpi_value) }}</strong>
                </span>
              </div>
            </div>

            <!-- Computed KPI: formula -> metrics -> documents -->
            <template v-if="selected.type === 'computed'">
              <div>
                <div class="flex items-center gap-1.5 text-xs font-medium text-muted-foreground mb-1.5">
                  <Sigma class="h-3.5 w-3.5" /> Formula
                </div>
                <pre class="kpi-formula">{{ selected.formula || 'Formula not found in the recipe.' }}</pre>
              </div>
              <div>
                <div class="text-xs font-medium text-muted-foreground mb-2">Metrics used</div>
                <div v-if="selected.metrics && selected.metrics.length" class="space-y-2">
                  <div v-for="m in selected.metrics" :key="m.metric" class="rounded-lg border p-3">
                    <div class="font-medium text-sm mb-1">{{ m.metric }}</div>
                    <div v-if="m.sources.length" class="flex flex-wrap gap-1.5">
                      <Button v-for="s in m.sources" :key="s.source"
                        variant="ghost" size="sm" class="h-7 gap-1.5 text-primary"
                        @click="openSource(s.source, s.quote)">
                        <FileSearch class="h-3.5 w-3.5" /> {{ s.source }}
                      </Button>
                    </div>
                    <div v-else class="text-xs text-muted-foreground">No source document found.</div>
                  </div>
                </div>
                <div v-else class="text-sm text-muted-foreground">No metric detected in the formula.</div>
              </div>
            </template>

            <!-- Extracted metric: just its source documents -->
            <template v-else>
              <div>
                <div class="text-xs font-medium text-muted-foreground mb-2">Source documents</div>
                <div v-if="selected.sources && selected.sources.length" class="flex flex-wrap gap-1.5">
                  <Button v-for="s in selected.sources" :key="s.source"
                    variant="ghost" size="sm" class="h-7 gap-1.5 text-primary"
                    @click="openSource(s.source, s.quote)">
                    <FileSearch class="h-3.5 w-3.5" /> {{ s.source }}
                  </Button>
                </div>
                <div v-else class="text-sm text-muted-foreground">No source document found.</div>
              </div>
            </template>
          </CardContent>
        </Card>
      </div>
    </div>

    <Card v-else><CardContent class="py-10 text-center text-muted-foreground">
      {{ loading ? 'Loading…' : 'No KPI available yet.' }}
    </CardContent></Card>

    <Dialog v-model:open="open">
      <DialogContent class="w-[96vw] max-w-[1800px]">
        <DialogHeader><DialogTitle class="truncate">{{ activeDoc || 'Source document' }}</DialogTitle></DialogHeader>
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
  .kpi-formula {
    margin: 0; white-space: pre-wrap; word-break: break-word;
    font-family: ui-monospace, "SFMono-Regular", Menlo, monospace;
    font-size: .78rem; line-height: 1.5; color: var(--foreground);
    background: color-mix(in oklab, var(--primary) 6%, transparent);
    border: 1px solid var(--border); border-radius: var(--radius-md); padding: .6rem .8rem;
  }
  .kpi-quote {
    margin: 0; max-height: 18vh; overflow: auto; white-space: pre-wrap; word-break: break-word;
    font-size: .75rem; line-height: 1.45; color: var(--foreground);
    background: var(--muted); border-radius: var(--radius-md); padding: .6rem .8rem;
  }
</style>
