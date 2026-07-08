import { computed } from 'vue';
import { useRouter, useRoute } from 'vue-router';
import type { MenuItem } from '@/types/routes';

export function useAppMenu() {
  const router = useRouter();
  const route = useRoute();
  const menuItems = computed<MenuItem[]>(() =>
    router.getRoutes()
      .filter((r) => r.name && r.meta.title && !r.meta.hiddenInMenu)
      .sort((a, b) => (a.meta.order as number) - (b.meta.order as number))
      .map((r) => ({
        title: r.meta.title as string,
        name: r.name as string,
        icon: r.meta.icon as MenuItem['icon'],
        isActive: r.name === route.name,
      })),
  );
  return { menuItems };
}
