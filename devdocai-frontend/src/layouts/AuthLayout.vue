<template>
  <div class="min-h-screen bg-gradient-to-br from-indigo-50 to-blue-100 flex flex-col justify-center py-12 sm:px-6 lg:px-8">
    <div class="sm:mx-auto sm:w-full sm:max-w-md">
      <!-- Logo -->
      <div class="flex justify-center">
        <h1 class="text-3xl font-bold text-indigo-600">DevDocAI</h1>
      </div>

      <!-- Page Title (passed via slot) -->
      <div class="mt-6">
        <slot name="title" />
      </div>
    </div>

    <!-- Auth Form Container -->
    <div class="mt-8 sm:mx-auto sm:w-full sm:max-w-md">
      <div class="bg-white py-8 px-4 shadow-xl rounded-lg sm:px-10">
        <router-view />
      </div>

      <!-- Additional Links -->
      <div class="mt-6">
        <slot name="links" />
      </div>
    </div>
  </div>
</template>

<script setup>
// Auth layout for login/register pages
</script>
