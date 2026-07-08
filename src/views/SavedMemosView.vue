<script setup lang="ts">
  import { onMounted } from 'vue';
  import { useRouter } from 'vue-router';
  import { storeToRefs } from 'pinia';
  import { toast } from 'vue-sonner';
  import { FileText, Trash2, ChevronRight } from 'lucide-vue-next';
  import { Card, CardContent } from '@/components/ui/card';
  import { Button } from '@/components/ui/button';
  import { Badge } from '@/components/ui/badge';
  import { useMemoStore } from '@/stores/memo';

  const store = useMemoStore();
  const { memos } = storeToRefs(store);
  const router = useRouter();

  onMounted(() => store.boot());

  async function open(title: string) {
    await store.selectMemo(title);
    router.push({ name: 'builder' });
  }
  async function remove(title: string) {
    await store.deleteMemo(title);
    toast.success(`« ${title || '(untitled)'} » deleted.`);
  }
  function count(title: string): string {
    const n = store.blockCount(title);
    return n == null ? 'Open to view' : `${n} section${n > 1 ? 's' : ''}`;
  }
</script>

<template>
  <div class="max-w-5xl mx-auto px-8 py-10">
    <div class="flex items-center gap-3 mb-1">
      <h1 class="text-2xl font-semibold">Saved memos</h1>
      <Badge>{{ memos.length }}</Badge>
    </div>
    <p class="text-muted-foreground mb-8">Open a saved memo to edit its structure, or delete it.</p>

    <div class="grid gap-4 sm:grid-cols-2">
      <Card v-for="title in memos" :key="title" class="group">
        <CardContent class="pt-6">
          <div class="flex items-start justify-between gap-3">
            <button type="button" class="flex items-start gap-3 text-left min-w-0" @click="open(title)">
              <span class="mt-0.5 flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-primary">
                <FileText class="h-4.5 w-4.5" />
              </span>
              <span class="min-w-0">
                <span class="block font-medium truncate">{{ title || 'Untitled memo' }}</span>
                <span class="block text-sm text-muted-foreground">{{ count(title) }}</span>
              </span>
            </button>
            <Button variant="ghost" size="icon" class="h-8 w-8 text-destructive opacity-0 group-hover:opacity-100"
              @click="remove(title)"><Trash2 class="h-4 w-4" /></Button>
          </div>
          <Button variant="ghost" size="sm" class="mt-3 w-full justify-between" @click="open(title)">
            Open <ChevronRight class="h-4 w-4" />
          </Button>
        </CardContent>
      </Card>
    </div>

    <Card v-if="!memos.length"><CardContent class="py-10 text-center text-muted-foreground">
      No saved memo yet.
    </CardContent></Card>
  </div>
</template>
