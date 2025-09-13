<template>
  <div class="document-type-selection">
    <!-- Section Header -->
    <div class="mb-6">
      <Heading level="2" size="lg" weight="semibold" color="primary" class="mb-2">
        Select Document Type(s) - You can choose multiple!
      </Heading>
      <Text size="sm" color="muted">
        Choose the types of documents you want to generate for your project
      </Text>
    </div>

    <!-- Document Categories -->
    <div class="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
      <!-- Planning & Requirements -->
      <div class="category-section">
        <div class="category-header mb-4">
          <div class="flex items-center space-x-2">
            <DocumentTextIcon class="h-5 w-5 text-blue-600 dark:text-blue-400" />
            <Heading level="3" size="md" weight="semibold">
              Planning & Requirements
            </Heading>
          </div>
        </div>

        <div class="space-y-3">
          <DocumentOption
            v-for="doc in planningDocs"
            :key="doc.id"
            :document="doc"
            :selected="selectedTypes.includes(doc.id)"
            @toggle="toggleDocument"
          />
        </div>
      </div>

      <!-- Design & Architecture -->
      <div class="category-section">
        <div class="category-header mb-4">
          <div class="flex items-center space-x-2">
            <CubeIcon class="h-5 w-5 text-purple-600 dark:text-purple-400" />
            <Heading level="3" size="md" weight="semibold">
              Design & Architecture
            </Heading>
          </div>
        </div>

        <div class="space-y-3">
          <DocumentOption
            v-for="doc in designDocs"
            :key="doc.id"
            :document="doc"
            :selected="selectedTypes.includes(doc.id)"
            @toggle="toggleDocument"
          />
        </div>
      </div>
    </div>

    <!-- Help Text -->
    <div v-if="showHelpText" class="help-section bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg p-4 mb-6">
      <div class="flex">
        <InformationCircleIcon class="h-5 w-5 text-blue-600 dark:text-blue-400 mt-0.5 mr-3 flex-shrink-0" />
        <div>
          <Text size="sm" weight="medium" class="text-blue-900 dark:text-blue-100 mb-2">
            What's the difference between SRS and PRD?
          </Text>
          <div class="space-y-1">
            <Text size="sm" class="text-blue-800 dark:text-blue-200">
              • PRD: Business requirements (what to build and why)
            </Text>
            <Text size="sm" class="text-blue-800 dark:text-blue-200">
              • SRS: Technical requirements (how to build it)
            </Text>
          </div>
        </div>
      </div>
    </div>

    <!-- Generation Options -->
    <div class="options-section bg-gray-50 dark:bg-gray-800 rounded-lg p-6">
      <Heading level="3" size="md" weight="semibold" class="mb-4">
        Generation Options:
      </Heading>

      <div class="space-y-4">
        <!-- Generate Complete Suite -->
        <div class="flex items-start space-x-3">
          <input
            id="generate-suite"
            v-model="generateSuite"
            type="checkbox"
            class="mt-1 h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
          >
          <div class="flex-1">
            <label
              for="generate-suite"
              class="text-sm font-medium text-gray-900 dark:text-gray-100 cursor-pointer"
            >
              Generate Complete Suite
            </label>
            <Text size="xs" color="muted" class="mt-1 flex items-center">
              <InformationCircleIcon class="h-3 w-3 mr-1" />
              Creates all related documents at once
            </Text>
          </div>
        </div>

        <!-- Selected Documents Summary -->
        <div v-if="selectedTypes.length > 0" class="selected-summary">
          <Text size="sm" weight="medium" class="mb-2">
            Selected Documents ({{ selectedTypes.length }}):
          </Text>
          <div class="flex flex-wrap gap-2">
            <span
              v-for="docId in selectedTypes"
              :key="docId"
              class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200"
            >
              {{ getDocumentName(docId) }}
              <button
                @click="removeDocument(docId)"
                class="ml-1.5 h-3 w-3 text-blue-600 dark:text-blue-300 hover:text-blue-800 dark:hover:text-blue-100"
                :aria-label="`Remove ${getDocumentName(docId)}`"
              >
                <XMarkIcon class="h-3 w-3" />
              </button>
            </span>
          </div>
        </div>

        <!-- Empty State -->
        <div v-if="selectedTypes.length === 0" class="empty-state text-center py-8">
          <DocumentPlusIcon class="h-12 w-12 text-gray-400 mx-auto mb-3" />
          <Text size="sm" color="muted">
            Select document types above to get started
          </Text>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import {
  DocumentTextIcon,
  CubeIcon,
  InformationCircleIcon,
  XMarkIcon,
  DocumentPlusIcon
} from '@heroicons/vue/24/outline'

// Components
import Heading from '@/components/atoms/Heading.vue'
import Text from '@/components/atoms/Text.vue'
import DocumentOption from './DocumentOption.vue'

// Types
interface DocumentType {
  id: string
  name: string
  description: string
  category: 'planning' | 'design'
  popular?: boolean
  recommended?: boolean
}

// Props
interface Props {
  selectedTypes: string[]
  generateSuite: boolean
}

const props = withDefaults(defineProps<Props>(), {
  selectedTypes: () => [],
  generateSuite: false
})

// Emits
const emit = defineEmits<{
  'update:selectedTypes': [value: string[]]
  'update:generateSuite': [value: boolean]
}>()

// Document definitions based on v3.6.0 mockups
const documentTypes: DocumentType[] = [
  // Planning & Requirements
  {
    id: 'project-plan',
    name: 'Project Plan',
    description: 'Comprehensive project planning document with timelines and milestones',
    category: 'planning'
  },
  {
    id: 'work-breakdown',
    name: 'Work Breakdown (WBS)',
    description: 'Hierarchical decomposition of project work into manageable tasks',
    category: 'planning'
  },
  {
    id: 'software-requirements',
    name: 'Software Requirements (SRS)',
    description: 'Technical requirements specification for software implementation',
    category: 'planning',
    popular: true,
    recommended: true
  },
  {
    id: 'product-requirements',
    name: 'Product Requirements (PRD)',
    description: 'Business requirements defining what to build and why',
    category: 'planning',
    popular: true
  },
  {
    id: 'user-stories',
    name: 'User Stories',
    description: 'User-centered requirements written from the end user perspective',
    category: 'planning',
    recommended: true
  },

  // Design & Architecture
  {
    id: 'software-design',
    name: 'Software Design Doc',
    description: 'Detailed software design and architecture specification',
    category: 'design',
    popular: true
  },
  {
    id: 'architecture-blueprint',
    name: 'Architecture Blueprint',
    description: 'High-level system architecture and design patterns',
    category: 'design',
    recommended: true
  },
  {
    id: 'api-specifications',
    name: 'API Specifications',
    description: 'RESTful API documentation with endpoints and schemas',
    category: 'design',
    popular: true
  },
  {
    id: 'database-schema',
    name: 'Database Schema',
    description: 'Database design with tables, relationships, and constraints',
    category: 'design'
  },
  {
    id: 'uml-diagrams',
    name: 'UML Diagrams',
    description: 'Visual system modeling diagrams and documentation',
    category: 'design'
  },
  {
    id: 'mockups-wireframes',
    name: 'Mockups/Wireframes',
    description: 'User interface design mockups and wireframe documentation',
    category: 'design'
  }
]

// Computed properties
const planningDocs = computed(() =>
  documentTypes.filter(doc => doc.category === 'planning')
)

const designDocs = computed(() =>
  documentTypes.filter(doc => doc.category === 'design')
)

const showHelpText = computed(() =>
  props.selectedTypes.includes('software-requirements') ||
  props.selectedTypes.includes('product-requirements')
)

// Computed getters for v-model
const selectedTypes = computed({
  get: () => props.selectedTypes,
  set: (value) => emit('update:selectedTypes', value)
})

const generateSuite = computed({
  get: () => props.generateSuite,
  set: (value) => emit('update:generateSuite', value)
})

// Methods
const toggleDocument = (docId: string) => {
  const currentSelection = [...props.selectedTypes]
  const index = currentSelection.indexOf(docId)

  if (index > -1) {
    currentSelection.splice(index, 1)
  } else {
    currentSelection.push(docId)
  }

  emit('update:selectedTypes', currentSelection)
}

const removeDocument = (docId: string) => {
  const currentSelection = props.selectedTypes.filter(id => id !== docId)
  emit('update:selectedTypes', currentSelection)
}

const getDocumentName = (docId: string): string => {
  const doc = documentTypes.find(d => d.id === docId)
  return doc?.name || docId
}
</script>

<style scoped>
.category-section {
  @apply bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-4;
}

.category-header {
  @apply pb-3 border-b border-gray-200 dark:border-gray-700;
}

.selected-summary {
  @apply pt-4 border-t border-gray-200 dark:border-gray-700;
}

.empty-state {
  @apply border-2 border-dashed border-gray-300 dark:border-gray-600 rounded-lg;
}

/* Checkbox styling */
input[type="checkbox"]:focus {
  @apply ring-2 ring-blue-500 ring-offset-2 dark:ring-offset-gray-800;
}

/* Responsive adjustments */
@media (max-width: 768px) {
  .grid.grid-cols-1.md\\:grid-cols-2 {
    @apply grid-cols-1 gap-4;
  }

  .category-section {
    @apply p-3;
  }
}
</style>