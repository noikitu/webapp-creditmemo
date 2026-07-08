<script setup lang="ts">
  import { ref, onMounted } from 'vue';
  import { useRouter } from 'vue-router';
  import { toast } from 'vue-sonner';
  import { UploadCloud, FileText } from 'lucide-vue-next';
  import { Card, CardContent } from '@/components/ui/card';
  import { Button } from '@/components/ui/button';
  import { useMemoStore } from '@/stores/memo';
  import { cn } from '@/lib/utils';

  const store = useMemoStore();
  const router = useRouter();

  onMounted(() => store.boot());

  const dragover = ref(false);
  const busy = ref(false);
  const fileInput = ref<HTMLInputElement | null>(null);

  function pick() { fileInput.value?.click(); }

  async function handle(file: File | null | undefined) {
    if (!file) return;
    busy.value = true;
    try {
      const title = await store.importMemo(file);
      toast.success(`Imported « ${title} ».`);
      router.push({ name: 'builder' });
    } catch (e) {
      toast.error('Import failed: ' + (e as Error).message);
    } finally {
      busy.value = false;
    }
  }
</script>

<template>
  <div class="max-w-5xl mx-auto px-8 py-10">
    <h1 class="text-2xl font-semibold mb-1">Import a memo</h1>
    <p class="text-muted-foreground mb-8">
      Drag &amp; drop an existing memo (Word, PDF, …). Its structure is extracted and
      appended as a new draft you can edit.
    </p>

    <Card>
      <CardContent class="pt-6">
        <div
          :class="cn(
            'flex flex-col items-center justify-center gap-3 rounded-lg border-2 border-dashed px-6 py-14 text-center transition-colors cursor-pointer',
            dragover ? 'border-primary bg-primary/5' : 'border-input hover:border-primary/50',
          )"
          @click="pick"
          @dragover.prevent="dragover = true"
          @dragleave.prevent="dragover = false"
          @drop.prevent="dragover = false; handle($event.dataTransfer?.files?.[0])">
          <span class="flex h-12 w-12 items-center justify-center rounded-full bg-primary/10 text-primary">
            <UploadCloud class="h-6 w-6" />
          </span>
          <p class="font-medium">{{ busy ? 'Extracting structure…' : 'Drop a memo here, or click to choose' }}</p>
          <p class="text-xs text-muted-foreground">.docx · .doc · .pdf · .txt · .md</p>
          <input ref="fileInput" type="file" class="hidden"
            accept=".docx,.doc,.pdf,.txt,.md"
            @change="handle(($event.target as HTMLInputElement).files?.[0])" />
        </div>

        <div class="mt-4 flex items-center gap-2 text-sm text-muted-foreground">
          <FileText class="h-4 w-4" />
          The document is added to the source folder, then the extraction pipeline runs.
        </div>

        <Button variant="outline" class="mt-4" :disabled="busy" @click="pick">Choose a file</Button>
      </CardContent>
    </Card>
  </div>
</template>
