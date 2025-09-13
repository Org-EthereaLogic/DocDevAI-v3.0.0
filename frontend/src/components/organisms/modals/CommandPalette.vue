<template>
  <div class="fixed inset-0 z-50 overflow-y-auto" @keydown.esc="close">
    <!-- Backdrop -->
    <div class="fixed inset-0 bg-gray-500 bg-opacity-75" @click="close"></div>

    <!-- Command Palette -->
    <div class="flex items-start justify-center min-h-screen pt-16">
      <div class="bg-white dark:bg-gray-800 rounded-lg shadow-xl max-w-2xl w-full mx-4">
        <!-- Search Input -->
        <div class="border-b border-gray-200 dark:border-gray-700 p-4">
          <input
            ref="searchInput"
            v-model="query"
            type="text"
            class="w-full px-3 py-2 bg-gray-50 dark:bg-gray-900 rounded-md"
            placeholder="Type a command or search..."
            @keydown.enter="executeCommand"
          />
        </div>

        <!-- Commands List -->
        <div class="max-h-96 overflow-y-auto p-2">
          <div
            v-for="command in filteredCommands"
            :key="command.id"
            class="px-3 py-2 hover:bg-gray-100 dark:hover:bg-gray-700 rounded cursor-pointer"
            @click="executeCommand(command)"
          >
            <div class="flex items-center justify-between">
              <span class="text-sm text-gray-900 dark:text-white">{{ command.label }}</span>
              <kbd v-if="command.shortcut" class="text-xs bg-gray-100 dark:bg-gray-700 px-2 py-1 rounded">
                {{ command.shortcut }}
              </kbd>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue';
import { useRouter } from 'vue-router';
import { useAppStore } from '@/stores/app';

const router = useRouter();
const appStore = useAppStore();

const searchInput = ref<HTMLInputElement>();
const query = ref('');

const commands = [
  { id: 'dashboard', label: 'Go to Dashboard', action: () => router.push('/app/dashboard'), shortcut: 'G D' },
  { id: 'documents', label: 'Go to Documents', action: () => router.push('/app/documents'), shortcut: 'G O' },
  { id: 'generate', label: 'Generate Document', action: () => router.push('/app/documents/generate'), shortcut: '⌘ N' },
  { id: 'settings', label: 'Settings', action: () => router.push('/app/settings'), shortcut: 'G S' },
];

const filteredCommands = computed(() => {
  if (!query.value) return commands;
  return commands.filter(cmd =>
    cmd.label.toLowerCase().includes(query.value.toLowerCase())
  );
});

const close = () => {
  appStore.showCommandPalette = false;
};

const executeCommand = (command?: any) => {
  if (command || filteredCommands.value.length > 0) {
    const cmd = command || filteredCommands.value[0];
    cmd.action();
    close();
  }
};

onMounted(() => {
  searchInput.value?.focus();
});
</script>