<template>
  <div>
    <!-- Command Palette Modal -->
    <CommandPalette v-if="appStore.showCommandPalette" />

    <!-- Search Modal -->
    <SearchModal v-if="appStore.showSearch" />

    <!-- Settings Modal -->
    <SettingsModal v-if="appStore.showSettings" />

    <!-- Success/Error/Warning Modals -->
    <FeedbackModal
      v-if="appStore.feedbackModal.show"
      :type="appStore.feedbackModal.type"
      :title="appStore.feedbackModal.title"
      :message="appStore.feedbackModal.message"
      @close="appStore.closeFeedbackModal"
    />
  </div>
</template>

<script setup lang="ts">
import { useAppStore } from '@/stores/app';
import CommandPalette from './CommandPalette.vue';
import SearchModal from './SearchModal.vue';
import SettingsModal from './SettingsModal.vue';
import FeedbackModal from './FeedbackModal.vue';

const appStore = useAppStore();
</script>