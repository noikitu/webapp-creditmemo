<script setup lang="ts">
  import { Sidebar, SidebarHeader, SidebarContent, SidebarGroup, SidebarMenu, SidebarMenuItem, SidebarMenuButton, SidebarRail } from '@/components/ui/sidebar';
  import AppName from '@/components/layout/AppName.vue';
  import { useAppMenu } from '@/composables/useAppMenu';
  import { cn } from '@/lib/utils';
  const { menuItems } = useAppMenu();
</script>

<template>
  <Sidebar collapsible="icon">
    <SidebarHeader class="h-16 py-2 border-b"><AppName /></SidebarHeader>
    <SidebarContent>
      <SidebarGroup class="pt-3"><SidebarMenu>
        <SidebarMenuItem v-for="item in menuItems" :key="item.name">
          <router-link :to="{ name: item.name }">
            <SidebarMenuButton :tooltip="item.title" class="border border-transparent"
              :class="cn({ 'bg-white border-stone-200': item.isActive })">
              <component :is="item.icon" v-if="item.icon" />
              <span>{{ item.title }}</span>
            </SidebarMenuButton>
          </router-link>
        </SidebarMenuItem>
      </SidebarMenu></SidebarGroup>
    </SidebarContent>
    <SidebarRail />
  </Sidebar>
</template>
