<script setup lang="ts">
  import { ref, watch, onMounted, nextTick } from 'vue';
  import { renderRich, typesetMath } from '@/lib/markdown';

  const props = defineProps<{ content: string }>();
  const root = ref<HTMLElement | null>(null);
  const html = ref('');

  async function update() {
    html.value = renderRich(props.content);
    await nextTick();
    if (root.value) {
      try { typesetMath(root.value); } catch { /* ignore KaTeX errors */ }
    }
  }

  onMounted(update);
  watch(() => props.content, update);
</script>

<template>
  <div ref="root" class="memo-content" v-html="html" />
</template>
