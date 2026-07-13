import { createRouter, createWebHashHistory } from 'vue-router';
import { FileText, FolderOpen, Upload, Sigma } from 'lucide-vue-next';
import DefaultLayout from '@/layouts/DefaultLayout.vue';
import BuilderView from '@/views/BuilderView.vue';
import SavedMemosView from '@/views/SavedMemosView.vue';
import ImportView from '@/views/ImportView.vue';
import KpisView from '@/views/KpisView.vue';

const router = createRouter({
  history: createWebHashHistory(),
  routes: [{
    path: '/', component: DefaultLayout, children: [
      { path: '', name: 'builder', component: BuilderView,
        meta: { title: 'Builder', icon: FileText, order: 1 } },
      { path: 'saved', name: 'saved', component: SavedMemosView,
        meta: { title: 'Saved memos', icon: FolderOpen, order: 2 } },
      { path: 'kpis', name: 'kpis', component: KpisView,
        meta: { title: 'KPIs', icon: Sigma, order: 3 } },
      { path: 'import', name: 'import', component: ImportView,
        meta: { title: 'Import', icon: Upload, order: 4 } },
    ],
  }],
});
export default router;
