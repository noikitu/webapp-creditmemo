<script setup lang="ts">
  import { ref, computed, watch } from 'vue';
  import type { ExcelSheet } from '@/api';

  const props = defineProps<{ sheets: ExcelSheet[]; highlight?: string }>();
  const active = ref(0);

  watch(() => props.sheets, () => { active.value = 0; });

  const current = computed(() => props.sheets[active.value] || null);

  // A cell is highlighted when the extracted quote contains its (non-trivial) value.
  const needle = computed(() => (props.highlight || '').trim().toLowerCase());
  function isHit(value: string): boolean {
    const v = (value || '').trim().toLowerCase();
    if (!v || v.length < 2 || !needle.value) return false;
    return needle.value.includes(v) || v.includes(needle.value);
  }
</script>

<template>
  <div class="excel-viewer">
    <div v-if="sheets.length > 1" class="excel-tabs">
      <button v-for="(s, i) in sheets" :key="s.name" type="button"
        :class="['excel-tab', { 'excel-tab-active': i === active }]"
        @click="active = i">{{ s.name }}</button>
    </div>

    <div v-if="current" class="excel-scroll">
      <table class="excel-table">
        <thead>
          <tr>
            <th class="excel-corner"></th>
            <th v-for="(c, ci) in current.columns" :key="ci">{{ c }}</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="(row, ri) in current.rows" :key="ri">
            <td class="excel-rownum">{{ ri + 1 }}</td>
            <td v-for="(cell, ci) in row" :key="ci" :class="{ 'excel-hit': isHit(cell) }">{{ cell }}</td>
          </tr>
        </tbody>
      </table>
    </div>

    <div v-if="current?.truncated" class="excel-note">
      Preview limited to the first {{ current.rows.length }} of {{ current.total_rows }} rows.
    </div>
    <div v-if="!sheets.length" class="excel-note">No sheet to display.</div>
  </div>
</template>

<style scoped>
  .excel-viewer { display: flex; flex-direction: column; gap: .5rem; }
  .excel-tabs { display: flex; flex-wrap: wrap; gap: .25rem; }
  .excel-tab {
    padding: .25rem .7rem; font-size: .8rem; border-radius: var(--radius-md);
    border: 1px solid var(--border); background: var(--card); color: var(--muted-foreground);
    cursor: pointer; transition: background .12s, color .12s;
  }
  .excel-tab:hover { background: var(--accent); }
  .excel-tab-active {
    background: color-mix(in oklab, var(--primary) 12%, transparent);
    color: var(--primary); border-color: color-mix(in oklab, var(--primary) 30%, transparent);
    font-weight: 600;
  }
  .excel-scroll { max-height: 70vh; overflow: auto; border: 1px solid var(--border); border-radius: var(--radius-md); }
  .excel-table { border-collapse: separate; border-spacing: 0; font-size: .8rem; width: max-content; min-width: 100%; }
  .excel-table th, .excel-table td {
    border-right: 1px solid var(--border); border-bottom: 1px solid var(--border);
    padding: .3rem .6rem; text-align: left; white-space: nowrap; vertical-align: top;
  }
  .excel-table thead th {
    position: sticky; top: 0; z-index: 2;
    background: color-mix(in oklab, var(--primary) 8%, var(--card));
    color: var(--foreground); font-weight: 600;
  }
  .excel-rownum, .excel-corner {
    position: sticky; left: 0; z-index: 1;
    background: var(--muted); color: var(--muted-foreground);
    text-align: right; font-variant-numeric: tabular-nums;
  }
  .excel-corner { z-index: 3; }
  .excel-hit {
    background: color-mix(in oklab, var(--primary) 22%, transparent);
    font-weight: 600;
  }
  .excel-note { font-size: .75rem; color: var(--muted-foreground); }
</style>
