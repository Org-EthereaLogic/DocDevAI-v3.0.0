<template>
  <div id="app" class="min-h-screen bg-gray-50">
    <router-view />
    <NotificationContainer />
  </div>
</template>

<script setup lang="ts">
import NotificationContainer from '@/components/NotificationContainer.vue'
</script>

<style scoped>
/* Component-specific styles can go here */
</style>
