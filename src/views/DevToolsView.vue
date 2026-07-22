<script setup lang="ts">
  import { ref, onMounted, onBeforeUnmount } from 'vue';
  import { toast } from 'vue-sonner';
  import { Eraser, RefreshCw, Database, AlertTriangle, Sparkles, X } from 'lucide-vue-next';
  import { Card, CardContent } from '@/components/ui/card';
  import { Button } from '@/components/ui/button';
  import {
    Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter, DialogClose,
  } from '@/components/ui/dialog';
  import { api } from '@/api';

  const MAX_ROWS = 100;
  const KEPT = ['metric', 'fiscal_year'];

  const columns = ref<string[]>([]);
  const rows = ref<unknown[][]>([]);
  const loading = ref(false);
  const cleaning = ref(false);
  const confirmOpen = ref(false);
  const extracting = ref(false);
  const extractError = ref('');
  let poll: number | undefined;

  function fmt(v: unknown): string {
    return v == null || v === '' ? '' : String(v);
  }
  function isKept(col: string): boolean {
    return KEPT.includes(col.toLowerCase());
  }

  async function refresh() {
    loading.value = true;
    try {
      const d = await api.inputKpi();
      columns.value = d.columns || [];
      rows.value = d.rows || [];
    } catch (e) {
      toast.error('Could not load input_KPI: ' + (e as Error).message);
    } finally {
      loading.value = false;
    }
  }

  async function runExtraction() {
    if (extracting.value) return;
    extracting.value = true;
    extractError.value = '';
    // Show rows appear live while the agent writes to input_KPI.
    poll = window.setInterval(async () => {
      try {
        const d = await api.inputKpi();
        columns.value = d.columns || [];
        rows.value = d.rows || [];
      } catch { /* ignore transient errors */ }
    }, 1500);
    try {
      const d = await api.runKpiExtraction();
      if (d.status !== 'ok') throw new Error(d.message || 'extraction failed');
      columns.value = d.columns || [];
      rows.value = d.rows || [];
      toast.success(`KPI Extraction finished — ${rows.value.length} row(s) in input_KPI.`);
    } catch (e) {
      extractError.value = (e as Error).message || 'Unknown error';
      toast.error('KPI Extraction failed.');
    } finally {
      if (poll) { window.clearInterval(poll); poll = undefined; }
      extracting.value = false;
    }
  }

  async function doClean() {
    cleaning.value = true;
    try {
      const d = await api.cleanInputKpi();
      if (d.status !== 'ok') throw new Error(d.message || 'clean failed');
      columns.value = d.columns || [];
      rows.value = d.rows || [];
      confirmOpen.value = false;
      toast.success(`input_KPI cleaned — cleared ${d.cleared.length} column(s), kept ${KEPT.join(' & ')}.`);
    } catch (e) {
      toast.error('Clean failed: ' + (e as Error).message);
    } finally {
      cleaning.value = false;
    }
  }

  onMounted(refresh);
  onBeforeUnmount(() => { if (poll) window.clearInterval(poll); });
</script>

<template>
  <div class="max-w-5xl mx-auto px-8 py-10">
    <h1 class="text-2xl font-semibold mb-1">Dev Tools</h1>
    <p class="text-muted-foreground mb-8">
      Maintenance utilities for the underlying datasets. Use with care — these write directly to DSS.
    </p>

    <Card>
      <CardContent class="space-y-4">
        <div class="flex items-start justify-between gap-4">
          <div>
            <div class="flex items-center gap-2 font-medium">
              <Database class="h-4 w-4 text-primary" /> Clean <code class="text-primary">input_KPI</code>
            </div>
            <p class="text-sm text-muted-foreground mt-1">
              Blanks every column <strong>except</strong>
              <code v-for="c in KEPT" :key="c" class="mx-0.5 rounded bg-muted px-1 py-0.5 text-xs">{{ c }}</code>,
              leaving the skeleton ready for a fresh KPI Filler run. Rows and schema are preserved.
            </p>
          </div>
          <div class="flex shrink-0 items-center gap-2">
            <Button variant="ghost" size="icon" class="h-8 w-8" :disabled="loading || extracting" @click="refresh">
              <RefreshCw :class="['h-4 w-4', { 'animate-spin': loading }]" />
            </Button>
            <Button :disabled="extracting || cleaning" :class="{ 'run-sweep': extracting }" @click="runExtraction">
              <Sparkles class="h-4 w-4" /> {{ extracting ? 'Extracting…' : 'Run KPI Extraction' }}
            </Button>
            <Button variant="destructive" :disabled="cleaning || loading || extracting" @click="confirmOpen = true">
              <Eraser class="h-4 w-4" /> Clean input_KPI
            </Button>
          </div>
        </div>

        <!-- Agent error (persistent, so it can be read/copied) -->
        <div v-if="extractError"
          class="rounded-lg border border-destructive/40 bg-destructive/5 p-3">
          <div class="flex items-center justify-between gap-2 mb-1">
            <span class="flex items-center gap-1.5 text-xs font-semibold text-destructive">
              <AlertTriangle class="h-3.5 w-3.5" /> KPI Extraction failed
            </span>
            <button type="button" class="text-destructive/70 hover:text-destructive" @click="extractError = ''">
              <X class="h-3.5 w-3.5" />
            </button>
          </div>
          <pre class="dev-error">{{ extractError }}</pre>
        </div>

        <!-- Preview -->
        <div class="rounded-lg border overflow-auto max-h-[60vh]">
          <table v-if="columns.length" class="w-max min-w-full text-xs">
            <thead>
              <tr>
                <th v-for="c in columns" :key="c"
                  :class="['sticky top-0 z-10 border-b px-3 py-2 text-left font-semibold whitespace-nowrap',
                    isKept(c) ? 'bg-primary/10 text-primary' : 'bg-muted text-foreground']">
                  {{ c }}<span v-if="isKept(c)" class="ml-1 opacity-60">(kept)</span>
                </th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(row, ri) in rows.slice(0, MAX_ROWS)" :key="ri" class="odd:bg-muted/30">
                <td v-for="(cell, ci) in row" :key="ci" class="border-b px-3 py-1.5 whitespace-nowrap">
                  {{ fmt(cell) }}
                </td>
              </tr>
            </tbody>
          </table>
          <div v-else class="py-10 text-center text-sm text-muted-foreground">
            {{ loading ? 'Loading…' : 'input_KPI is empty or unavailable.' }}
          </div>
        </div>
        <div v-if="rows.length" class="text-xs text-muted-foreground">
          {{ rows.length }} row(s){{ rows.length > MAX_ROWS ? ` — showing first ${MAX_ROWS}` : '' }}.
        </div>
      </CardContent>
    </Card>

    <!-- Confirm -->
    <Dialog v-model:open="confirmOpen">
      <DialogContent>
        <DialogHeader>
          <DialogTitle class="flex items-center gap-2">
            <AlertTriangle class="h-4 w-4 text-destructive" /> Clean input_KPI?
          </DialogTitle>
          <DialogDescription>
            This blanks all columns of <code>input_KPI</code> except
            <strong>{{ KEPT.join(' & ') }}</strong>. This action writes to DSS and cannot be undone.
          </DialogDescription>
        </DialogHeader>
        <DialogFooter>
          <DialogClose as-child><Button variant="outline">Cancel</Button></DialogClose>
          <Button variant="destructive" :disabled="cleaning" @click="doClean">
            <Eraser class="h-4 w-4" /> {{ cleaning ? 'Cleaning…' : 'Yes, clean' }}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  </div>
</template>

<style scoped>
  .dev-error {
    margin: 0; max-height: 30vh; overflow: auto; white-space: pre-wrap; word-break: break-word;
    font-family: ui-monospace, "SFMono-Regular", Menlo, monospace;
    font-size: .75rem; line-height: 1.45; color: var(--destructive);
  }

  /* Looping blue sweep while the KPI Extraction agent runs */
  .run-sweep { position: relative; overflow: hidden; }
  .run-sweep::after {
    content: ""; position: absolute; inset: 0; pointer-events: none;
    background: linear-gradient(90deg, transparent 0%, rgba(112, 146, 242, .85) 50%, transparent 100%);
    transform: translateX(-120%);
    animation: run-sweep-anim 1.1s linear infinite;
  }
  @keyframes run-sweep-anim {
    from { transform: translateX(-120%); }
    to   { transform: translateX(120%); }
  }
  @media (prefers-reduced-motion: reduce) {
    .run-sweep::after { animation: none; }
  }
</style>
