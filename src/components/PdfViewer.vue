<script setup lang="ts">
  import { ref, watch, onMounted } from 'vue';
  import * as pdfjsLib from 'pdfjs-dist';
  import workerUrl from 'pdfjs-dist/build/pdf.worker.min.mjs?url';

  pdfjsLib.GlobalWorkerOptions.workerSrc = workerUrl;

  const props = defineProps<{ url: string; highlight?: string }>();
  const host = ref<HTMLElement | null>(null);
  const status = ref<'loading' | 'ready' | 'error'>('loading');
  const message = ref('');
  const matched = ref(false);

  function normalize(s: string): string {
    return (s || '').toLowerCase().replace(/\s+/g, ' ').trim();
  }

  async function render() {
    if (!host.value) return;
    host.value.innerHTML = '';
    status.value = 'loading';
    matched.value = false;
    const quote = normalize(props.highlight || '');
    let firstHl: HTMLElement | null = null;

    try {
      const doc = await pdfjsLib.getDocument({ url: props.url }).promise;
      // Fit pages to the container width (keeps highlights aligned since the
      // same scale is used for canvas and highlight boxes).
      const avail = Math.max(320, (host.value.clientWidth || 800) - 28);
      for (let i = 1; i <= doc.numPages; i++) {
        const page = await doc.getPage(i);
        const base = page.getViewport({ scale: 1 });
        const scale = Math.min(2, Math.max(0.5, avail / base.width));
        const viewport = page.getViewport({ scale });

        const wrap = document.createElement('div');
        wrap.className = 'pdf-page';
        wrap.style.width = viewport.width + 'px';
        wrap.style.height = viewport.height + 'px';

        const canvas = document.createElement('canvas');
        canvas.width = viewport.width;
        canvas.height = viewport.height;
        wrap.appendChild(canvas);
        host.value.appendChild(wrap);

        const ctx = canvas.getContext('2d')!;
        // pdfjs v6 RenderParameters shape varies across typings — cast to satisfy it.
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        await page.render({ canvas, canvasContext: ctx, viewport } as any).promise;

        // Best-effort highlight: mark text items whose text appears in the quote.
        if (quote) {
          const tc = await page.getTextContent();
          for (const item of tc.items as Array<Record<string, unknown>>) {
            const str = typeof item.str === 'string' ? item.str : '';
            const n = normalize(str);
            if (n.length < 3 || !quote.includes(n)) continue;
            const tr = item.transform as number[];
            const tx = pdfjsLib.Util.transform(viewport.transform, tr);
            const fontH = Math.hypot(tx[2], tx[3]);
            const w = (item.width as number) * scale;
            const hl = document.createElement('div');
            hl.className = 'pdf-hl';
            hl.style.left = tx[4] + 'px';
            hl.style.top = (tx[5] - fontH) + 'px';
            hl.style.width = w + 'px';
            hl.style.height = fontH + 'px';
            wrap.appendChild(hl);
            if (!firstHl) firstHl = hl;
          }
        }
      }
      status.value = 'ready';
      matched.value = !!firstHl;
      if (firstHl) firstHl.scrollIntoView({ block: 'center' });
    } catch (e) {
      status.value = 'error';
      message.value = (e as Error).message;
    }
  }

  onMounted(render);
  watch(() => [props.url, props.highlight], render);
</script>

<template>
  <div class="pdf-viewer">
    <p v-if="status === 'loading'" class="pdf-note">Loading document…</p>
    <p v-else-if="status === 'error'" class="pdf-note pdf-error">
      Could not load the document: {{ message }}
    </p>
    <p v-else-if="highlight && !matched" class="pdf-note">
      The exact quote was not located in the document — see it below the reader.
    </p>
    <div ref="host" class="pdf-host" />
  </div>
</template>

<style scoped>
  .pdf-viewer { display: flex; flex-direction: column; gap: 8px; }
  .pdf-note { font-size: .8125rem; color: var(--muted-foreground); margin: 0; }
  .pdf-error { color: var(--destructive); }
  .pdf-host { max-height: 72vh; overflow: auto; background: var(--muted); border-radius: var(--radius-md); padding: 12px; }
  .pdf-host :deep(.pdf-page) {
    position: relative; margin: 0 auto 12px; background: #fff;
    box-shadow: 0 1px 4px rgba(0,0,0,.15);
  }
  .pdf-host :deep(.pdf-hl) {
    position: absolute; background: rgba(255, 213, 0, .45);
    border-radius: 2px; pointer-events: none;
  }
</style>
