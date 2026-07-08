<script setup lang="ts">
  import { ref } from 'vue';
  import { storeToRefs } from 'pinia';
  import { toast } from 'vue-sonner';
  import { Plus, UploadCloud, FileText, BarChart3 } from 'lucide-vue-next';
  import { Card, CardContent } from '@/components/ui/card';
  import { Button } from '@/components/ui/button';
  import { Badge } from '@/components/ui/badge';
  import {
    Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter,
  } from '@/components/ui/dialog';
  import { useMemoStore } from '@/stores/memo';
  import { cn } from '@/lib/utils';

  const store = useMemoStore();
  const { metrics } = storeToRefs(store);

  const open = ref(false);
  const dragover = ref(false);
  const pending = ref<File[]>([]);
  const busy = ref(false);
  const fileInput = ref<HTMLInputElement | null>(null);

  function openDialog() { pending.value = []; open.value = true; }
  function pick() { fileInput.value?.click(); }

  function addFiles(list: FileList | null) {
    if (list) pending.value.push(...Array.from(list));
  }
  function onDrop(e: DragEvent) {
    dragover.value = false;
    addFiles(e.dataTransfer?.files ?? null);
  }

  async function confirm() {
    if (!pending.value.length) return;
    busy.value = true;
    await new Promise((r) => setTimeout(r, 700)); // simulate BUILD_METRICS
    store.addMetrics(pending.value.map((f) => f.name));
    busy.value = false;
    open.value = false;
    toast.success(`Metrics updated from ${pending.value.length} document(s).`);
  }
</script>

<template>
  <div class="max-w-5xl mx-auto px-8 py-10">
    <div class="flex items-center justify-between mb-1">
      <div class="flex items-center gap-3">
        <h1 class="text-2xl font-semibold">Metrics</h1>
        <Badge>{{ metrics.length }}</Badge>
      </div>
      <Button @click="openDialog"><Plus class="h-4 w-4" /> Add Metrics</Button>
    </div>
    <p class="text-muted-foreground mb-8">
      Selectable metrics extracted from your documents. Add more to enrich the catalog.
    </p>

    <div class="grid gap-3 sm:grid-cols-2">
      <Card v-for="m in metrics" :key="m.metric">
        <CardContent class="flex items-start gap-3 pt-5">
          <span class="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-chart-2/15 text-chart-2">
            <BarChart3 class="h-4 w-4" />
          </span>
          <div class="min-w-0">
            <div class="font-medium">{{ m.metric }}</div>
            <div class="text-sm text-muted-foreground">{{ m.description || '—' }}</div>
          </div>
        </CardContent>
      </Card>
    </div>

    <Dialog v-model:open="open">
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Add metrics</DialogTitle>
          <DialogDescription>
            Drag &amp; drop your metric documents (Excel, PDF, …), then confirm.
          </DialogDescription>
        </DialogHeader>

        <div
          :class="cn(
            'flex flex-col items-center justify-center gap-2 rounded-lg border-2 border-dashed px-6 py-8 text-center transition-colors cursor-pointer',
            dragover ? 'border-primary bg-primary/5' : 'border-input hover:border-primary/50',
          )"
          @click="pick"
          @dragover.prevent="dragover = true"
          @dragleave.prevent="dragover = false"
          @drop.prevent="onDrop">
          <UploadCloud class="h-7 w-7 text-primary" />
          <p class="text-sm">Drag &amp; drop documents here, or click to choose</p>
          <p class="text-xs text-muted-foreground">.xlsx · .xls · .csv · .pdf · .docx · .doc · .txt</p>
          <input ref="fileInput" type="file" multiple class="hidden"
            accept=".xlsx,.xls,.csv,.pdf,.docx,.doc,.txt"
            @change="addFiles(($event.target as HTMLInputElement).files)" />
        </div>

        <ul v-if="pending.length" class="space-y-1">
          <li v-for="(f, i) in pending" :key="i" class="flex items-center gap-2 text-sm">
            <FileText class="h-4 w-4 text-primary" /> {{ f.name }}
          </li>
        </ul>

        <DialogFooter>
          <Button variant="outline" @click="open = false">Cancel</Button>
          <Button :disabled="!pending.length || busy" @click="confirm">
            {{ busy ? 'Extracting…' : 'Confirm' }}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  </div>
</template>
