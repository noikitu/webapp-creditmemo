<template>
  <div class="antialiased font-sans">
    <router-view />
    <Toaster rich-colors />
  </div>
</template>

<script setup lang="ts">
  import { Toaster } from '@/components/ui/sonner';
</script>
