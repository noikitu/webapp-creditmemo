<script setup lang="ts">
  import { computed, onMounted, ref, nextTick } from 'vue';
  import { toast } from 'vue-sonner';
  import { ChevronUp, ChevronDown, Trash2, Plus, Sparkles, Check, X, Eraser, FilePlus2, UploadCloud } from 'lucide-vue-next';
  import { Card, CardContent } from '@/components/ui/card';
  import { Button } from '@/components/ui/button';
  import { Input } from '@/components/ui/input';
  import { Textarea } from '@/components/ui/textarea';
  import { Separator } from '@/components/ui/separator';
  import {
    Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter, DialogClose,
  } from '@/components/ui/dialog';
  import { useMemoStore, type Block } from '@/stores/memo';
  import MemoContent from '@/components/MemoContent.vue';
  import { cn } from '@/lib/utils';

  const store = useMemoStore();
  const memo = computed(() => store.current);
  const running = ref(false);
  const deleteOpen = ref(false);
  const confirmed = ref(false);   // triggers the green sweep on Save Memo

  // New-memo dialog (start from scratch or import)
  const newMemoOpen = ref(false);
  const importing = ref(false);
  const fileInput = ref<HTMLInputElement | null>(null);

  function startScratch() {
    store.newMemo();
    newMemoOpen.value = false;
    toast.success('New memo started.');
  }
  async function importFile(file: File | null | undefined) {
    if (!file) return;
    importing.value = true;
    try {
      const title = await store.importMemo(file);
      newMemoOpen.value = false;
      toast.success(`Imported « ${title} ».`);
    } catch (e) {
      toast.error('Import failed: ' + (e as Error).message);
    } finally {
      importing.value = false;
    }
  }

  // KPI picker (per block): + button opens the all_KPI catalog
  const pickerOpen = ref(false);
  const pickerBlock = ref<Block | null>(null);
  const pickerSearch = ref('');

  function openKpiPicker(block: Block) {
    pickerBlock.value = block;
    pickerSearch.value = '';
    pickerOpen.value = true;
  }
  const pickerGroups = computed(() => {
    const q = pickerSearch.value.trim().toLowerCase();
    const opts = store.kpiOptions.filter((o) => !q || o.kpi.toLowerCase().includes(q));
    const groups: { category: string; items: typeof opts }[] = [];
    for (const o of opts) {
      let g = groups.find((x) => x.category === (o.category || ''));
      if (!g) { g = { category: o.category || '', items: [] }; groups.push(g); }
      g.items.push(o);
    }
    return groups;
  });
  function isPicked(kpi: string): boolean {
    return !!pickerBlock.value && pickerBlock.value.metrics.includes(kpi);
  }
  function togglePicked(kpi: string) {
    if (pickerBlock.value) store.toggleMetric(pickerBlock.value.id, kpi);
  }

  onMounted(() => store.boot());

  const hasGenerated = computed(() => memo.value && Object.keys(memo.value.generated).length > 0);

  function generatedFor(title: string): string | undefined {
    return memo.value?.generated[title.trim().toLowerCase()];
  }

  function validate(): boolean {
    if (!memo.value) return false;
    if (!memo.value.title.trim()) { toast.error('Please set a memo title first.'); return false; }
    const empty = memo.value.blocks
      .map((b, i) => (b.title.trim() ? null : i + 1))
      .filter((x): x is number => x !== null);
    if (empty.length) { toast.error(`Each section needs a title. Missing: ${empty.join(', ')}.`); return false; }
    return true;
  }

  async function confirmStructure() {
    if (!validate()) return;
    await store.saveStructure();
    confirmed.value = false;      // restart the animation if clicked again
    await nextTick();
    confirmed.value = true;
    setTimeout(() => { confirmed.value = false; }, 1000);
    toast.success(`« ${memo.value!.title} » saved (${memo.value!.blocks.length} sections).`);
  }

  async function runAgent() {
    if (!validate()) return;
    running.value = true;
    // Reveal paragraphs as the agent writes them: poll credit_memo during the run.
    const poll = store.backendReady
      ? window.setInterval(() => { store.refreshGenerated(); }, 1500)
      : undefined;
    try {
      const n = await store.runAgent();
      toast.success(`Agent finished — ${n} paragraph(s) generated.`);
    } catch (e) {
      toast.error('Agent run failed: ' + (e as Error).message);
    } finally {
      if (poll) window.clearInterval(poll);
      running.value = false;
    }
  }

  async function doDelete() {
    if (memo.value) await store.deleteMemo(memo.value.title);
    deleteOpen.value = false;
    toast.success('Memo deleted.');
  }
</script>

<template>
  <div class="max-w-5xl mx-auto px-8 py-10">
    <div class="flex items-start justify-between gap-4 mb-8">
      <div>
        <h1 class="text-2xl font-semibold mb-1">Memo structure</h1>
        <p class="text-muted-foreground max-w-2xl">
          Give the memo a title, fill in each section, reorder them, then save the memo or run the agent.
        </p>
      </div>
      <Button variant="outline" class="shrink-0" @click="newMemoOpen = true">
        <Plus class="h-4 w-4" /> New Memo
      </Button>
    </div>

    <template v-if="memo">
      <!-- Memo title -->
      <div class="mb-8">
        <label class="text-sm mb-1.5 block" for="memo-title">Memo title</label>
        <Input id="memo-title" v-model="memo.title"
          placeholder="e.g. Acme Corp — 2026 annual credit review" class="max-w-xl" />
      </div>

      <!-- Sections -->
      <div class="space-y-4">
        <Card v-for="(block, i) in memo.blocks" :key="block.id">
          <CardContent>
            <div class="flex items-center justify-between mb-3">
              <span class="text-xs font-medium text-muted-foreground uppercase tracking-wide">
                Section {{ i + 1 }}
              </span>
              <div class="flex items-center gap-1">
                <Button variant="ghost" size="icon" class="h-8 w-8" :disabled="i === 0"
                  @click="store.moveBlock(i, i - 1)"><ChevronUp class="h-4 w-4" /></Button>
                <Button variant="ghost" size="icon" class="h-8 w-8" :disabled="i === memo.blocks.length - 1"
                  @click="store.moveBlock(i, i + 1)"><ChevronDown class="h-4 w-4" /></Button>
                <Button variant="ghost" size="icon" class="h-8 w-8 text-destructive"
                  @click="store.removeBlock(block.id)"><Trash2 class="h-4 w-4" /></Button>
              </div>
            </div>

            <Input v-model="block.title" placeholder="Title — e.g. Counterparty overview" class="mb-2 font-medium" />
            <Textarea v-model="block.description" :rows="3"
              placeholder="Description — expected content of this section…" class="mb-3" />

            <div class="mb-1">
              <span class="text-xs font-medium text-muted-foreground">KPIs to include</span>
              <TransitionGroup name="chip" tag="div" class="flex flex-wrap items-center gap-1.5 mt-1.5">
                <span v-for="m in block.metrics" :key="m"
                  class="inline-flex items-center gap-1 rounded-full bg-primary/10 text-primary px-3 py-1 text-xs font-medium">
                  {{ m }}
                  <button type="button" class="opacity-60 hover:opacity-100"
                    @click="store.toggleMetric(block.id, m)"><X class="h-3 w-3" /></button>
                </span>
                <Button key="__add" variant="outline" size="sm" class="h-7 rounded-full px-2.5"
                  @click="openKpiPicker(block)">
                  <Plus class="h-3.5 w-3.5" /> Add KPI
                </Button>
              </TransitionGroup>
            </div>

            <!-- Skeleton while the agent is writing this section -->
            <div v-if="running && !generatedFor(block.title)"
              class="mt-4 rounded-lg border border-primary/20 bg-primary/5 p-4">
              <div class="animate-pulse space-y-2">
                <div class="h-3 w-1/3 rounded bg-primary/25"></div>
                <div class="h-2.5 w-full rounded bg-muted-foreground/20"></div>
                <div class="h-2.5 w-11/12 rounded bg-muted-foreground/20"></div>
                <div class="h-2.5 w-4/5 rounded bg-muted-foreground/20"></div>
              </div>
            </div>

            <!-- Agent-generated paragraph (revealed when it arrives) -->
            <Transition name="reveal">
              <div v-if="generatedFor(block.title)"
                class="mt-4 rounded-lg border border-primary/20 bg-primary/5 p-4">
                <div class="flex items-center justify-between mb-1.5">
                  <span class="inline-flex items-center gap-1.5 text-xs font-medium text-primary">
                    <Sparkles class="h-3.5 w-3.5" /> Generated paragraph
                  </span>
                  <Button variant="ghost" size="icon" class="h-6 w-6"
                    @click="store.deleteGenerated(block.title)"><X class="h-3.5 w-3.5" /></Button>
                </div>
                <MemoContent class="prose-memo text-sm" :content="generatedFor(block.title)!" />
              </div>
            </Transition>
          </CardContent>
        </Card>
      </div>

      <Button variant="outline" class="w-full mt-4 border-dashed" @click="store.addBlock()">
        <Plus class="h-4 w-4" /> Add a section
      </Button>

      <Button v-if="hasGenerated" variant="ghost" class="w-full mt-2 text-muted-foreground"
        @click="store.clearGenerated()">
        <Eraser class="h-4 w-4" /> Clear agent paragraphs
      </Button>

      <Separator class="my-6" />

      <div class="flex items-center justify-end gap-2">
        <Button variant="ghost" class="text-destructive mr-auto" @click="deleteOpen = true">
          <Trash2 class="h-4 w-4" /> Delete this memo
        </Button>
        <Button variant="outline" :disabled="running" :class="cn({ 'run-sweep': running })" @click="runAgent">
          <Sparkles class="h-4 w-4" /> {{ running ? 'Running…' : 'Run agent' }}
        </Button>
        <Button :class="cn({ 'confirm-sweep': confirmed })" @click="confirmStructure">
          <Check class="h-4 w-4" /> Save Memo
        </Button>
      </div>
    </template>

    <Card v-else><CardContent class="py-10 text-center text-muted-foreground">
      No memo selected. Create one from <strong>Saved memos</strong> or <strong>Import</strong>.
    </CardContent></Card>

    <!-- New memo: start from scratch or import -->
    <Dialog v-model:open="newMemoOpen">
      <DialogContent>
        <DialogHeader>
          <DialogTitle>New memo</DialogTitle>
          <DialogDescription>Start from scratch, or import an existing memo to extract its structure.</DialogDescription>
        </DialogHeader>
        <div class="space-y-3">
          <Button variant="outline" class="w-full justify-start gap-2" @click="startScratch">
            <FilePlus2 class="h-4 w-4" /> Start from scratch
          </Button>

          <div class="text-xs font-medium uppercase tracking-wide text-muted-foreground text-center">or</div>

          <button type="button"
            class="flex w-full flex-col items-center justify-center gap-1.5 rounded-lg border border-dashed px-4 py-8 text-center transition-colors hover:border-primary hover:bg-accent"
            @click="fileInput?.click()"
            @dragover.prevent
            @drop.prevent="importFile($event.dataTransfer?.files?.[0])">
            <UploadCloud class="h-6 w-6 text-muted-foreground" />
            <span class="text-sm font-medium">{{ importing ? 'Importing…' : 'Import a memo' }}</span>
            <span class="text-xs text-muted-foreground">Drag &amp; drop or click — PDF, DOCX, TXT…</span>
            <input ref="fileInput" type="file" class="hidden"
              accept=".pdf,.docx,.doc,.txt,.md"
              @change="importFile(($event.target as HTMLInputElement).files?.[0])" />
          </button>
        </div>
      </DialogContent>
    </Dialog>

    <!-- KPI picker -->
    <Dialog v-model:open="pickerOpen">
      <DialogContent class="max-w-lg">
        <DialogHeader>
          <DialogTitle>Select KPIs</DialogTitle>
          <DialogDescription>KPIs from the <code class="text-foreground">all_KPI</code> catalog.</DialogDescription>
        </DialogHeader>
        <Input v-model="pickerSearch" placeholder="Search KPIs…" />
        <div class="max-h-[50vh] overflow-auto space-y-4 pr-1">
          <div v-for="g in pickerGroups" :key="g.category">
            <div class="text-xs font-medium uppercase tracking-wide text-muted-foreground mb-1">
              {{ g.category || 'Other' }}
            </div>
            <div class="space-y-0.5">
              <button v-for="o in g.items" :key="o.kpi" type="button"
                @click="togglePicked(o.kpi)"
                :class="cn('flex w-full items-center gap-2 rounded-md px-2.5 py-1.5 text-sm text-left transition-colors',
                  isPicked(o.kpi) ? 'bg-primary/10 text-primary font-medium' : 'hover:bg-accent')">
                <Check :class="cn('h-3.5 w-3.5 shrink-0', isPicked(o.kpi) ? 'opacity-100' : 'opacity-0')" />
                {{ o.kpi }}
              </button>
            </div>
          </div>
          <p v-if="!pickerGroups.length" class="text-sm text-muted-foreground text-center py-4">
            No KPI matches your search.
          </p>
        </div>
        <DialogFooter>
          <Button @click="pickerOpen = false">Done</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>

    <!-- Delete confirmation -->
    <Dialog v-model:open="deleteOpen">
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Delete this memo?</DialogTitle>
          <DialogDescription>
            This removes « {{ memo?.title || '(untitled)' }} » and its generated paragraphs.
            This action cannot be undone.
          </DialogDescription>
        </DialogHeader>
        <DialogFooter>
          <DialogClose as-child><Button variant="outline">Cancel</Button></DialogClose>
          <Button variant="destructive" @click="doDelete">Yes, delete</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  </div>
</template>

<style scoped>
  .prose-memo :deep(h2) { font-size: 1rem; font-weight: 600; margin: 0 0 .35rem; }
  .prose-memo :deep(p) { margin: 0 0 .6rem; line-height: 1.55; }
  .prose-memo :deep(p:last-child) { margin-bottom: 0; }
  .prose-memo :deep(strong) { font-weight: 600; }
  .prose-memo :deep(ul), .prose-memo :deep(ol) { margin: 0 0 .6rem; padding-left: 1.25rem; }

  /* LaTeX tables */
  .prose-memo :deep(.memo-figure) { margin: .6rem 0; overflow-x: auto; }
  .prose-memo :deep(.memo-table) {
    border-collapse: collapse; width: 100%; font-size: .8125rem;
    background: var(--card);
  }
  .prose-memo :deep(.memo-table th),
  .prose-memo :deep(.memo-table td) {
    border: 1px solid var(--border); padding: .4rem .7rem; text-align: left; vertical-align: top;
  }
  .prose-memo :deep(.memo-table th) {
    background: color-mix(in oklab, var(--primary) 10%, transparent);
    color: var(--primary); font-weight: 600;
  }
  .prose-memo :deep(.memo-table tr:nth-child(even) td) {
    background: color-mix(in oklab, var(--primary) 4%, transparent);
  }
  .prose-memo :deep(.memo-figure figcaption) {
    margin-top: .35rem; font-size: .75rem; color: var(--muted-foreground); font-style: italic;
  }

  /* <python> code blocks (prototype: displayed, not executed) */
  .prose-memo :deep(.memo-code) {
    margin: .6rem 0; padding: .7rem .85rem; overflow-x: auto;
    background: color-mix(in oklab, var(--primary) 6%, transparent);
    border: 1px solid var(--border); border-radius: var(--radius-md);
    font-size: .78rem; line-height: 1.5;
  }
  .prose-memo :deep(.memo-code code) { font-family: ui-monospace, "SFMono-Regular", Menlo, monospace; }

  /* Matplotlib chart rendered from a <python> block */
  .prose-memo :deep(.py-chart) { margin: .6rem 0; }
  .prose-memo :deep(.py-chart-img) {
    max-width: 100%; height: auto;
    border: 1px solid var(--border); border-radius: var(--radius-md); background: var(--card);
  }
  .prose-memo :deep(.py-loading) { font-size: .8125rem; color: var(--muted-foreground); }
  .prose-memo :deep(.py-error) {
    display: inline-block; font-size: .8125rem; color: var(--destructive);
    background: color-mix(in oklab, var(--destructive) 8%, transparent);
    border: 1px solid color-mix(in oklab, var(--destructive) 25%, transparent);
    border-radius: var(--radius-md); padding: .5rem .7rem;
  }

  /* KaTeX display spacing */
  .prose-memo :deep(.katex-display) { margin: .5rem 0; overflow-x: auto; overflow-y: hidden; }

  /* Green sweep across the Confirm button on success */
  .confirm-sweep { position: relative; overflow: hidden; }
  .confirm-sweep::after {
    content: ""; position: absolute; inset: 0; pointer-events: none;
    background: linear-gradient(90deg, transparent 0%, rgba(62, 218, 178, .9) 50%, transparent 100%);
    transform: translateX(-120%);
    animation: confirm-sweep-anim .9s ease-out;
  }
  @keyframes confirm-sweep-anim {
    from { transform: translateX(-120%); }
    to   { transform: translateX(120%); }
  }

  /* Looping blue sweep across the Run agent button while it runs */
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

  /* KPI chip pop in / out */
  .chip-enter-active, .chip-leave-active { transition: opacity .18s ease, transform .18s ease; }
  .chip-enter-from, .chip-leave-to { opacity: 0; transform: scale(.85); }

  /* Generated paragraph reveal (fade + slide up) */
  .reveal-enter-active { transition: opacity .35s ease, transform .35s ease; }
  .reveal-enter-from { opacity: 0; transform: translateY(8px); }

  @media (prefers-reduced-motion: reduce) {
    .chip-enter-active, .chip-leave-active,
    .reveal-enter-active { transition: none; }
    .confirm-sweep::after, .run-sweep::after { animation: none; }
  }
</style>
