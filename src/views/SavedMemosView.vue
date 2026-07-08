<script setup lang="ts">
  import { onMounted } from 'vue';
  import { useRouter } from 'vue-router';
  import { storeToRefs } from 'pinia';
  import { toast } from 'vue-sonner';
  import { Trash2 } from 'lucide-vue-next';
  import { Button } from '@/components/ui/button';
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
  <div class="max-w-3xl mx-auto px-8 py-10">
    <h1 class="text-2xl font-semibold mb-1">Saved memos</h1>
    <p class="text-muted-foreground mb-8">Open a saved memo to edit its structure, or delete it.</p>

    <div class="rounded-lg border divide-y">
      <div v-for="title in memos" :key="title"
        class="group flex items-center justify-between gap-3 px-4 py-3 cursor-pointer hover:bg-accent"
        @click="open(title)">
        <div class="min-w-0">
          <div class="font-medium truncate">{{ title || 'Untitled memo' }}</div>
          <div class="text-sm text-muted-foreground">{{ count(title) }}</div>
        </div>
        <Button variant="ghost" size="icon" class="h-8 w-8 shrink-0 text-destructive opacity-0 group-hover:opacity-100"
          @click.stop="remove(title)"><Trash2 class="h-4 w-4" /></Button>
      </div>
      <div v-if="!memos.length" class="px-4 py-10 text-center text-muted-foreground">
        No saved memo yet.
      </div>
    </div>
  </div>
</template>
