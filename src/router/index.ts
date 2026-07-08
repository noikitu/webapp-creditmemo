import { createRouter, createWebHashHistory } from 'vue-router';
import { FileText, FolderOpen, BarChart3, Upload } from 'lucide-vue-next';
import DefaultLayout from '@/layouts/DefaultLayout.vue';
import BuilderView from '@/views/BuilderView.vue';
import SavedMemosView from '@/views/SavedMemosView.vue';
import MetricsView from '@/views/MetricsView.vue';
import ImportView from '@/views/ImportView.vue';

const router = createRouter({
  history: createWebHashHistory(),
  routes: [{
    path: '/', component: DefaultLayout, children: [
      { path: '', name: 'builder', component: BuilderView,
        meta: { title: 'Builder', icon: FileText, order: 1 } },
      { path: 'saved', name: 'saved', component: SavedMemosView,
        meta: { title: 'Saved memos', icon: FolderOpen, order: 2 } },
      { path: 'metrics', name: 'metrics', component: MetricsView,
        meta: { title: 'Metrics', icon: BarChart3, order: 3 } },
      { path: 'import', name: 'import', component: ImportView,
        meta: { title: 'Import', icon: Upload, order: 4 } },
    ],
  }],
});
export default router;
