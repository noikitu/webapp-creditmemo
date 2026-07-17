<script setup lang="ts">
  import { ref, watch } from 'vue';
  import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog';
  import PdfViewer from '@/components/PdfViewer.vue';
  import ExcelViewer from '@/components/ExcelViewer.vue';
  import { api, isExcelName, type ExcelSheet } from '@/api';

  const props = defineProps<{ open: boolean; name: string; quote?: string }>();
  const emit = defineEmits<{ (e: 'update:open', v: boolean): void }>();

  const sheets = ref<ExcelSheet[]>([]);
  const loading = ref(false);
  const error = ref('');

  const isExcel = () => isExcelName(props.name);

  async function load() {
    sheets.value = []; error.value = '';
    if (!props.name || !isExcel()) return;
    loading.value = true;
    try {
      const d = await api.excelPreview(props.name);
      if (d.error) error.value = d.error;
      else sheets.value = d.sheets || [];
    } catch (e) {
      error.value = (e as Error).message;
    } finally {
      loading.value = false;
    }
  }

  watch(() => [props.open, props.name], () => { if (props.open) load(); });
</script>

<template>
  <Dialog :open="open" @update:open="emit('update:open', $event)">
    <DialogContent class="!w-[96vw] !max-w-[1800px]">
      <DialogHeader><DialogTitle class="truncate">{{ name || 'Source document' }}</DialogTitle></DialogHeader>

      <template v-if="open && name">
        <!-- Excel source -->
        <template v-if="isExcel()">
          <div v-if="loading" class="py-10 text-center text-sm text-muted-foreground">Loading preview…</div>
          <div v-else-if="error" class="py-10 text-center text-sm text-destructive">{{ error }}</div>
          <ExcelViewer v-else :sheets="sheets" :highlight="quote" />
        </template>

        <!-- PDF (or other) source -->
        <PdfViewer v-else :url="api.documentUrl(name)" :highlight="quote || ''" />
      </template>

      <div v-if="quote" class="mt-1">
        <div class="text-xs font-medium text-muted-foreground mb-1">Extracted quote</div>
        <pre class="doc-quote">{{ quote }}</pre>
      </div>
    </DialogContent>
  </Dialog>
</template>

<style scoped>
  .doc-quote {
    margin: 0; max-height: 18vh; overflow: auto; white-space: pre-wrap; word-break: break-word;
    font-size: .75rem; line-height: 1.45; color: var(--foreground);
    background: var(--muted); border-radius: var(--radius-md); padding: .6rem .8rem;
  }
</style>
