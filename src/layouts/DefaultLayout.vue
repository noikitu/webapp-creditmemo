<script setup lang="ts">
  import AppSidebar from '@/components/layout/AppSidebar.vue';
  import { SidebarProvider } from '@/components/ui/sidebar';
</script>

<template>
  <div class="h-screen bg-background text-foreground flex">
    <SidebarProvider>
      <AppSidebar />
      <div class="flex-1 flex flex-col overflow-auto">
        <main class="flex-1 overflow-auto"><router-view /></main>
      </div>
    </SidebarProvider>
  </div>
</template>
