import { defineStore } from 'pinia';
import { ref, computed } from 'vue';
import { templateAPI } from '@/services/api';

export const useTemplateStore = defineStore('template', () => {
  // State
  const templates = ref([]);
  const selectedTemplate = ref(null);
  const loading = ref(false);
  const error = ref(null);
  const searchQuery = ref('');
  const filters = ref({
    category: '',
    tags: [],
    sortBy: 'downloads', // 'downloads', 'name', 'rating', 'updated'
    sortOrder: 'desc'
  });
  const pagination = ref({
    currentPage: 1,
    totalPages: 1,
    perPage: 20,
    total: 0
  });

  // Categories and tags for filtering
  const categories = ref([
    { id: 'readme', name: 'README', icon: '📝' },
    { id: 'api', name: 'API Documentation', icon: '🔌' },
    { id: 'changelog', name: 'Changelog', icon: '📋' },
    { id: 'contributing', name: 'Contributing Guide', icon: '🤝' },
    { id: 'license', name: 'License', icon: '⚖️' },
    { id: 'security', name: 'Security Policy', icon: '🔒' },
    { id: 'deployment', name: 'Deployment Guide', icon: '🚀' },
    { id: 'troubleshooting', name: 'Troubleshooting', icon: '🔧' }
  ]);

  const availableTags = ref([
    'javascript', 'python', 'react', 'vue', 'nodejs', 'typescript',
    'backend', 'frontend', 'mobile', 'desktop', 'web', 'api',
    'microservices', 'database', 'docker', 'kubernetes', 'aws',
    'opensource', 'enterprise', 'startup', 'tutorial', 'beginner'
  ]);

  // Template cache for performance
  const templateCache = ref(new Map());
  const cacheExpiry = ref(5 * 60 * 1000); // 5 minutes

  // Computed
  const filteredTemplates = computed(() => {
    let filtered = templates.value;

    // Apply search filter
    if (searchQuery.value) {
      const query = searchQuery.value.toLowerCase();
      filtered = filtered.filter(template =>
        template.name.toLowerCase().includes(query) ||
        template.description.toLowerCase().includes(query) ||
        template.tags?.some(tag => tag.toLowerCase().includes(query))
      );
    }

    // Apply category filter
    if (filters.value.category) {
      filtered = filtered.filter(template => template.category === filters.value.category);
    }

    // Apply tag filters
    if (filters.value.tags.length > 0) {
      filtered = filtered.filter(template =>
        filters.value.tags.some(tag => template.tags?.includes(tag))
      );
    }

    // Apply sorting
    filtered.sort((a, b) => {
      const { sortBy, sortOrder } = filters.value;
      let aVal = a[sortBy];
      let bVal = b[sortBy];

      if (sortBy === 'name') {
        aVal = aVal.toLowerCase();
        bVal = bVal.toLowerCase();
      }

      if (sortOrder === 'asc') {
        return aVal > bVal ? 1 : -1;
      } else {
        return aVal < bVal ? 1 : -1;
      }
    });

    return filtered;
  });

  const popularTemplates = computed(() =>
    templates.value
      .filter(t => t.downloads > 50)
      .sort((a, b) => b.downloads - a.downloads)
      .slice(0, 6)
  );

  const recentTemplates = computed(() =>
    templates.value
      .sort((a, b) => new Date(b.updatedAt) - new Date(a.updatedAt))
      .slice(0, 6)
  );

  const hasError = computed(() => !!error.value);
  const isEmpty = computed(() => !loading.value && templates.value.length === 0);

  // Actions
  const fetchTemplates = async (params = {}) => {
    loading.value = true;
    error.value = null;

    try {
      const queryParams = {
        page: pagination.value.currentPage,
        per_page: pagination.value.perPage,
        search: searchQuery.value,
        category: filters.value.category,
        tags: filters.value.tags.join(','),
        sort_by: filters.value.sortBy,
        sort_order: filters.value.sortOrder,
        ...params
      };

      const response = await templateAPI.getTemplates(queryParams);

      templates.value = response.data.data || [];

      // Update pagination if provided
      if (response.data.pagination) {
        pagination.value = { ...pagination.value, ...response.data.pagination };
      }

      // Cache the results
      const cacheKey = JSON.stringify(queryParams);
      templateCache.value.set(cacheKey, {
        data: response.data,
        timestamp: Date.now()
      });

    } catch (err) {
      error.value = err.response?.data?.message || 'Failed to fetch templates';
      console.error('Error fetching templates:', err);
    } finally {
      loading.value = false;
    }
  };

  const fetchTemplate = async (id) => {
    // Check cache first
    const cacheKey = `template_${id}`;
    const cached = templateCache.value.get(cacheKey);

    if (cached && Date.now() - cached.timestamp < cacheExpiry.value) {
      selectedTemplate.value = cached.data;
      return cached.data;
    }

    loading.value = true;
    error.value = null;

    try {
      const response = await templateAPI.getTemplate(id);
      selectedTemplate.value = response.data;

      // Cache the template
      templateCache.value.set(cacheKey, {
        data: response.data,
        timestamp: Date.now()
      });

      return response.data;
    } catch (err) {
      error.value = err.response?.data?.message || 'Failed to fetch template';
      console.error('Error fetching template:', err);
      throw err;
    } finally {
      loading.value = false;
    }
  };

  const searchTemplates = async (query) => {
    searchQuery.value = query;
    pagination.value.currentPage = 1; // Reset to first page
    await fetchTemplates();
  };

  const applyFilters = async (newFilters) => {
    filters.value = { ...filters.value, ...newFilters };
    pagination.value.currentPage = 1; // Reset to first page
    await fetchTemplates();
  };

  const changePage = async (page) => {
    pagination.value.currentPage = page;
    await fetchTemplates();
  };

  const resetFilters = async () => {
    searchQuery.value = '';
    filters.value = {
      category: '',
      tags: [],
      sortBy: 'downloads',
      sortOrder: 'desc'
    };
    pagination.value.currentPage = 1;
    await fetchTemplates();
  };

  const selectTemplate = (template) => {
    selectedTemplate.value = template;
  };

  const clearSelection = () => {
    selectedTemplate.value = null;
  };

  const toggleTag = (tag) => {
    const index = filters.value.tags.indexOf(tag);
    if (index > -1) {
      filters.value.tags.splice(index, 1);
    } else {
      filters.value.tags.push(tag);
    }
  };

  const clearError = () => {
    error.value = null;
  };

  // Cache management
  const clearCache = () => {
    templateCache.value.clear();
  };

  const getCachedTemplate = (id) => {
    const cacheKey = `template_${id}`;
    const cached = templateCache.value.get(cacheKey);

    if (cached && Date.now() - cached.timestamp < cacheExpiry.value) {
      return cached.data;
    }

    return null;
  };

  // Template validation for custom templates
  const validateTemplate = (template) => {
    const errors = [];

    if (!template.name || template.name.trim().length === 0) {
      errors.push('Template name is required');
    }

    if (!template.description || template.description.trim().length === 0) {
      errors.push('Template description is required');
    }

    if (!template.content || template.content.trim().length === 0) {
      errors.push('Template content is required');
    }

    if (!template.category) {
      errors.push('Template category is required');
    }

    return {
      isValid: errors.length === 0,
      errors
    };
  };

  // Reset store
  const $reset = () => {
    templates.value = [];
    selectedTemplate.value = null;
    loading.value = false;
    error.value = null;
    searchQuery.value = '';
    filters.value = {
      category: '',
      tags: [],
      sortBy: 'downloads',
      sortOrder: 'desc'
    };
    pagination.value = {
      currentPage: 1,
      totalPages: 1,
      perPage: 20,
      total: 0
    };
    templateCache.value.clear();
  };

  return {
    // State
    templates,
    selectedTemplate,
    loading,
    error,
    searchQuery,
    filters,
    pagination,
    categories,
    availableTags,

    // Computed
    filteredTemplates,
    popularTemplates,
    recentTemplates,
    hasError,
    isEmpty,

    // Actions
    fetchTemplates,
    fetchTemplate,
    searchTemplates,
    applyFilters,
    changePage,
    resetFilters,
    selectTemplate,
    clearSelection,
    toggleTag,
    clearError,
    clearCache,
    getCachedTemplate,
    validateTemplate,
    $reset
  };
}, {
  persist: {
    enabled: true,
    strategies: [
      {
        key: 'template',
        storage: sessionStorage,
        paths: ['searchQuery', 'filters']
      }
    ]
  }
});
