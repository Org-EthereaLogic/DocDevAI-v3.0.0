<template>
  <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
    <div class="mb-8">
      <h1 class="text-2xl font-bold text-gray-900">Settings</h1>
      <p class="mt-1 text-sm text-gray-600">Manage your DevDocAI preferences and configuration</p>
    </div>

    <div class="space-y-6">
      <!-- AI Configuration -->
      <div class="bg-white shadow rounded-lg">
        <div class="px-4 py-5 sm:p-6">
          <h3 class="text-lg leading-6 font-medium text-gray-900 mb-4">AI Configuration</h3>

          <div class="space-y-4">
            <div>
              <label class="block text-sm font-medium text-gray-700">Default AI Model</label>
              <select class="mt-1 block w-full border-gray-300 rounded-md shadow-sm focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm">
                <option>GPT-4 (High Quality)</option>
                <option>Claude 3 (Balanced)</option>
                <option>Local Model (Free)</option>
              </select>
            </div>

            <div>
              <label class="block text-sm font-medium text-gray-700">API Keys</label>
              <div class="mt-2 space-y-2">
                <div>
                  <label class="block text-xs font-medium text-gray-500">OpenAI API Key</label>
                  <input
                    type="password"
                    placeholder="sk-..."
                    class="mt-1 block w-full border-gray-300 rounded-md shadow-sm focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm"
                  />
                </div>
                <div>
                  <label class="block text-xs font-medium text-gray-500">Anthropic API Key</label>
                  <input
                    type="password"
                    placeholder="sk-ant-..."
                    class="mt-1 block w-full border-gray-300 rounded-md shadow-sm focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm"
                  />
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Privacy Settings -->
      <div class="bg-white shadow rounded-lg">
        <div class="px-4 py-5 sm:p-6">
          <h3 class="text-lg leading-6 font-medium text-gray-900 mb-4">Privacy & Data</h3>

          <div class="space-y-4">
            <div class="flex items-center justify-between">
              <div>
                <h4 class="text-sm font-medium text-gray-900">Local-only processing</h4>
                <p class="text-sm text-gray-500">Keep all data on your local machine</p>
              </div>
              <button class="relative inline-flex flex-shrink-0 h-6 w-11 border-2 border-transparent rounded-full cursor-pointer transition-colors ease-in-out duration-200 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 bg-indigo-600">
                <span class="translate-x-5 pointer-events-none inline-block h-5 w-5 rounded-full bg-white shadow transform ring-0 transition ease-in-out duration-200"></span>
              </button>
            </div>

            <div class="flex items-center justify-between">
              <div>
                <h4 class="text-sm font-medium text-gray-900">Anonymous usage analytics</h4>
                <p class="text-sm text-gray-500">Help improve DevDocAI with anonymous data</p>
              </div>
              <button class="relative inline-flex flex-shrink-0 h-6 w-11 border-2 border-transparent rounded-full cursor-pointer transition-colors ease-in-out duration-200 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 bg-gray-200">
                <span class="translate-x-0 pointer-events-none inline-block h-5 w-5 rounded-full bg-white shadow transform ring-0 transition ease-in-out duration-200"></span>
              </button>
            </div>
          </div>
        </div>
      </div>

      <!-- Actions -->
      <div class="flex justify-end space-x-3">
        <button class="bg-white py-2 px-4 border border-gray-300 rounded-md shadow-sm text-sm font-medium text-gray-700 hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500">
          Reset to Defaults
        </button>
        <button class="bg-indigo-600 py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500">
          Save Changes
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
// Settings placeholder
</script>
