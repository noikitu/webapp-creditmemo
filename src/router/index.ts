import { createRouter, createWebHashHistory } from 'vue-router';
import { FileText, FolderOpen, Sigma, Wrench } from 'lucide-vue-next';
import DefaultLayout from '@/layouts/DefaultLayout.vue';
import BuilderView from '@/views/BuilderView.vue';
import SavedMemosView from '@/views/SavedMemosView.vue';
import KpisView from '@/views/KpisView.vue';
import DevToolsView from '@/views/DevToolsView.vue';

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
      { path: 'dev', name: 'dev', component: DevToolsView,
        meta: { title: 'Dev Tools', icon: Wrench, order: 4 } },
    ],
  }],
});
export default router;
