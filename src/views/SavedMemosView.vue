<script setup lang="ts">
  import { onMounted } from 'vue';
  import { useRouter } from 'vue-router';
  import { storeToRefs } from 'pinia';
  import { toast } from 'vue-sonner';
  import { Trash2 } from 'lucide-vue-next';
  import { Card, CardContent } from '@/components/ui/card';
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
  <div class="max-w-5xl mx-auto px-8 py-10">
    <h1 class="text-2xl font-semibold mb-1">Saved memos</h1>
    <p class="text-muted-foreground mb-8">Open a saved memo to edit its structure, or delete it.</p>

    <div class="grid gap-3 sm:grid-cols-2">
      <Card v-for="title in memos" :key="title" class="group cursor-pointer" @click="open(title)">
        <CardContent class="flex items-start justify-between gap-3 pt-5">
          <div class="min-w-0">
            <div class="font-medium truncate">{{ title || 'Untitled memo' }}</div>
            <div class="text-sm text-muted-foreground">{{ count(title) }}</div>
          </div>
          <Button variant="ghost" size="icon" class="h-8 w-8 shrink-0 text-destructive opacity-0 group-hover:opacity-100"
            @click.stop="remove(title)"><Trash2 class="h-4 w-4" /></Button>
        </CardContent>
      </Card>
    </div>

    <Card v-if="!memos.length"><CardContent class="py-10 text-center text-muted-foreground">
      No saved memo yet.
    </CardContent></Card>
  </div>
</template>
