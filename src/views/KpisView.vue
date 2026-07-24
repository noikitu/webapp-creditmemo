<script setup lang="ts">
  import { ref, computed, onMounted, watch } from 'vue';
  import { toast } from 'vue-sonner';
  import { FileSearch, Sigma, FunctionSquare, Plus, Trash2 } from 'lucide-vue-next';
  import { Card, CardContent } from '@/components/ui/card';
  import { Button } from '@/components/ui/button';
  import { Input } from '@/components/ui/input';
  import {
    Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter,
  } from '@/components/ui/dialog';
  import DocumentDialog from '@/components/DocumentDialog.vue';
  import { api, type MergedKpi, type KpiValue } from '@/api';
  import { cn } from '@/lib/utils';

  const kpis = ref<MergedKpi[]>([]);
  const loading = ref(true);
  const selected = ref<MergedKpi | null>(null);

  const open = ref(false);
  const activeDoc = ref('');
  const activeQuote = ref('');

  // Keep custom KPIs visible even before they resolve to values.
  function hasValues(k: MergedKpi): boolean {
    return (k.values || []).some((v) => v.kpi_value != null && v.kpi_value !== '');
  }

  async function load(keepSelection = false) {
    try {
      const d = await api.kpiFull();
      const prev = selected.value?.kpi;
      kpis.value = (d.items || []).filter((k) => k.type === 'custom' || hasValues(k));
      selected.value = (keepSelection && prev ? kpis.value.find((k) => k.kpi === prev) : null)
        || kpis.value[0] || null;
    } catch { /* backend unavailable */ }
    loading.value = false;
  }

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
  function badge(t: MergedKpi['type']): string {
    return t === 'computed' ? 'Computed' : t === 'custom' ? 'Custom' : 'Extracted';
  }

  // ---- Custom KPI builder --------------------------------------------------
  const builderOpen = ref(false);
  const cName = ref('');
  const cCategory = ref('Custom');
  const cFormula = ref('');
  const preview = ref<KpiValue[]>([]);
  const previewMsg = ref('');
  const saving = ref(false);
  let previewTimer: number | undefined;

  // KPIs usable in a formula: everything with values, except other custom ones.
  const refKpis = computed(() => kpis.value.filter((k) => k.type !== 'custom' && hasValues(k)));

  function openBuilder() {
    cName.value = ''; cCategory.value = 'Custom'; cFormula.value = '';
    preview.value = []; previewMsg.value = '';
    builderOpen.value = true;
  }
  function insertKpi(name: string) {
    if (!name) return;
    cFormula.value += (cFormula.value && !/\s$/.test(cFormula.value) ? ' ' : '') + `[${name}]`;
  }
  function insertToken(tok: string) { cFormula.value += tok; }

  watch(cFormula, () => {
    window.clearTimeout(previewTimer);
    previewTimer = window.setTimeout(async () => {
      const f = cFormula.value.trim();
      if (!f) { preview.value = []; previewMsg.value = ''; return; }
      try {
        const d = await api.customKpiPreview(f);
        preview.value = d.values || [];
        previewMsg.value = d.values && d.values.length ? '' : 'No values — check the formula and referenced KPIs.';
      } catch (e) {
        preview.value = []; previewMsg.value = (e as Error).message;
      }
    }, 400);
  });

  async function saveCustom() {
    if (!cName.value.trim() || !cFormula.value.trim()) {
      toast.error('Give the KPI a name and a formula.'); return;
    }
    saving.value = true;
    try {
      const d = await api.addCustomKpi({
        kpi: cName.value.trim(), category: cCategory.value.trim() || 'Custom', formula: cFormula.value.trim(),
      });
      if (d.status !== 'ok') throw new Error(d.message || 'save failed');
      builderOpen.value = false;
      await load(true);
      selected.value = kpis.value.find((k) => k.kpi === cName.value.trim()) || selected.value;
      toast.success(`Custom KPI « ${cName.value.trim()} » added.`);
    } catch (e) {
      toast.error('Could not add KPI: ' + (e as Error).message);
    } finally {
      saving.value = false;
    }
  }

  async function deleteCustom(k: MergedKpi) {
    try {
      await api.deleteCustomKpi(k.kpi);
      await load();
      toast.success(`Custom KPI « ${k.kpi} » removed.`);
    } catch (e) {
      toast.error('Could not remove KPI: ' + (e as Error).message);
    }
  }

  onMounted(() => load());
</script>

<template>
  <div class="max-w-5xl mx-auto px-8 py-10">
    <div class="flex items-start justify-between gap-4 mb-8">
      <div>
        <h1 class="text-2xl font-semibold mb-1">KPIs</h1>
        <p class="text-muted-foreground max-w-2xl">
          Every KPI from <code class="text-foreground">all_KPI</code>. Computed KPIs show their lineage;
          extracted metrics show their source documents; custom KPIs are computed from a formula.
        </p>
      </div>
      <Button variant="outline" class="shrink-0" @click="openBuilder">
        <Plus class="h-4 w-4" /> Custom KPI
      </Button>
    </div>

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
              <FunctionSquare v-if="k.type === 'custom'" class="h-3.5 w-3.5 shrink-0 opacity-60" />
              <Sigma v-else-if="k.type === 'computed'" class="h-3.5 w-3.5 shrink-0 opacity-60" />
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
                  {{ badge(selected.type) }}
                </span>
                <Button v-if="selected.type === 'custom'" variant="ghost" size="sm"
                  class="ml-auto h-7 gap-1.5 text-destructive" @click="deleteCustom(selected)">
                  <Trash2 class="h-3.5 w-3.5" /> Delete
                </Button>
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

            <!-- Custom KPI: just its formula -->
            <template v-else-if="selected.type === 'custom'">
              <div>
                <div class="flex items-center gap-1.5 text-xs font-medium text-muted-foreground mb-1.5">
                  <FunctionSquare class="h-3.5 w-3.5" /> Formula
                </div>
                <pre class="kpi-formula">{{ selected.formula }}</pre>
                <p class="mt-2 text-xs text-muted-foreground">Computed from existing KPIs, per fiscal year.</p>
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

    <DocumentDialog v-model:open="open" :name="activeDoc" :quote="activeQuote" />

    <!-- Custom KPI builder -->
    <Dialog v-model:open="builderOpen">
      <DialogContent class="max-w-lg">
        <DialogHeader>
          <DialogTitle>New custom KPI</DialogTitle>
          <DialogDescription>Compute a new KPI from existing ones. Insert KPIs and operators to build the formula.</DialogDescription>
        </DialogHeader>

        <div class="space-y-3">
          <div class="grid grid-cols-2 gap-3">
            <div>
              <label class="text-xs mb-1 block text-muted-foreground">Name</label>
              <Input v-model="cName" placeholder="e.g. EBITDA margin (%)" />
            </div>
            <div>
              <label class="text-xs mb-1 block text-muted-foreground">Category</label>
              <Input v-model="cCategory" placeholder="Custom" />
            </div>
          </div>

          <div>
            <label class="text-xs mb-1 block text-muted-foreground">Formula</label>
            <Input v-model="cFormula" placeholder="e.g. [EBITDA] / [Net revenue] * 100"
              class="font-mono text-sm" />
            <div class="mt-2 flex flex-wrap items-center gap-1.5">
              <Button v-for="t in [' + ', ' - ', ' * ', ' / ', '( ', ' )']" :key="t"
                variant="outline" size="sm" class="h-7 w-9 px-0 font-mono" @click="insertToken(t)">
                {{ t.trim() }}
              </Button>
              <select
                class="h-7 rounded-md border bg-background px-2 text-xs"
                @change="insertKpi(($event.target as HTMLSelectElement).value); ($event.target as HTMLSelectElement).value = ''">
                <option value="">Insert KPI…</option>
                <option v-for="k in refKpis" :key="k.kpi" :value="k.kpi">{{ k.kpi }}</option>
              </select>
              <Button variant="ghost" size="sm" class="h-7 text-muted-foreground" @click="cFormula = ''">Clear</Button>
            </div>
          </div>

          <!-- Live preview -->
          <div class="rounded-lg border bg-muted/30 p-3">
            <div class="text-xs font-medium text-muted-foreground mb-1.5">Preview (per fiscal year)</div>
            <div v-if="preview.length" class="flex flex-wrap gap-2">
              <span v-for="v in preview" :key="String(v.fiscal_year)"
                class="rounded-md bg-primary/10 px-2 py-1 text-xs text-primary">
                {{ v.fiscal_year }} : <strong>{{ fmt(v.kpi_value) }}</strong>
              </span>
            </div>
            <div v-else class="text-xs text-muted-foreground">
              {{ cFormula.trim() ? (previewMsg || 'Computing…') : 'Build a formula to preview values.' }}
            </div>
          </div>
        </div>

        <DialogFooter>
          <Button variant="outline" @click="builderOpen = false">Cancel</Button>
          <Button :disabled="saving || !cName.trim() || !cFormula.trim()" @click="saveCustom">
            {{ saving ? 'Saving…' : 'Add KPI' }}
          </Button>
        </DialogFooter>
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
</style>
