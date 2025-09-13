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

  // M013 Marketplace features
  const marketplace = ref({
    featured: [],
    community: [],
    verified: [],
    userTemplates: [],
    downloadHistory: [],
    publishedTemplates: []
  });

  // Template publishing state
  const publishing = ref({
    isPublishing: false,
    uploadProgress: 0,
    validationErrors: [],
    publishingStep: 'idle' // 'idle', 'validating', 'uploading', 'signing', 'complete'
  });

  // Template security and verification
  const security = ref({
    signatureCache: new Map(),
    verificationResults: new Map(),
    trustedPublishers: [],
    securityScanResults: new Map()
  });

  // Local template management
  const localTemplates = ref([]);
  const customTemplates = ref([]);

  // Template ratings and reviews
  const ratings = ref(new Map());
  const reviews = ref(new Map());

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

  // M013 Marketplace computed properties
  const featuredTemplates = computed(() => marketplace.value.featured);
  const verifiedTemplates = computed(() => marketplace.value.verified);
  const communityTemplates = computed(() => marketplace.value.community);

  const myPublishedTemplates = computed(() => marketplace.value.publishedTemplates);
  const myDownloadedTemplates = computed(() => marketplace.value.downloadHistory);

  const isPublishing = computed(() => publishing.value.isPublishing);
  const publishingProgress = computed(() => publishing.value.uploadProgress);

  const totalLocalTemplates = computed(() =>
    localTemplates.value.length + customTemplates.value.length
  );

  const templatesByVerification = computed(() => ({
    verified: templates.value.filter(t => t.verified),
    community: templates.value.filter(t => !t.verified && t.published),
    local: [...localTemplates.value, ...customTemplates.value]
  }));

  const templateStats = computed(() => ({
    total: templates.value.length,
    verified: templates.value.filter(t => t.verified).length,
    community: templates.value.filter(t => !t.verified && t.published).length,
    local: totalLocalTemplates.value,
    downloaded: marketplace.value.downloadHistory.length,
    published: marketplace.value.publishedTemplates.length
  }));

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

  // M013 Marketplace Actions
  const fetchFeaturedTemplates = async () => {
    try {
      const response = await templateAPI.getFeatured();
      marketplace.value.featured = response.data || [];
      return response.data;
    } catch (err) {
      console.error('Error fetching featured templates:', err);
      throw err;
    }
  };

  const downloadTemplate = async (templateId) => {
    try {
      const response = await templateAPI.download(templateId);
      const template = response.data;

      // Add to local templates
      localTemplates.value.push(template);

      // Add to download history
      marketplace.value.downloadHistory.unshift({
        templateId,
        downloadedAt: new Date().toISOString(),
        template
      });

      // Limit download history
      if (marketplace.value.downloadHistory.length > 100) {
        marketplace.value.downloadHistory = marketplace.value.downloadHistory.slice(0, 100);
      }

      return template;
    } catch (err) {
      console.error('Error downloading template:', err);
      throw err;
    }
  };

  const publishTemplate = async (templateData) => {
    publishing.value.isPublishing = true;
    publishing.value.uploadProgress = 0;
    publishing.value.validationErrors = [];
    publishing.value.publishingStep = 'validating';

    try {
      // Step 1: Validate template
      publishing.value.uploadProgress = 20;
      const validationResult = await templateAPI.validateTemplate(templateData);

      if (!validationResult.isValid) {
        publishing.value.validationErrors = validationResult.errors;
        throw new Error('Template validation failed');
      }

      // Step 2: Upload template
      publishing.value.publishingStep = 'uploading';
      publishing.value.uploadProgress = 50;

      const uploadResponse = await templateAPI.uploadTemplate(templateData, {
        onProgress: (progress) => {
          publishing.value.uploadProgress = 50 + (progress * 0.3);
        }
      });

      // Step 3: Sign template (Ed25519 signature)
      publishing.value.publishingStep = 'signing';
      publishing.value.uploadProgress = 80;

      const signResponse = await templateAPI.signTemplate(uploadResponse.templateId);

      // Step 4: Complete publication
      publishing.value.publishingStep = 'complete';
      publishing.value.uploadProgress = 100;

      const publishedTemplate = {
        ...uploadResponse.template,
        signature: signResponse.signature,
        publishedAt: new Date().toISOString()
      };

      // Add to published templates
      marketplace.value.publishedTemplates.unshift(publishedTemplate);

      return publishedTemplate;

    } catch (err) {
      console.error('Error publishing template:', err);
      throw err;
    } finally {
      publishing.value.isPublishing = false;
      publishing.value.publishingStep = 'idle';
    }
  };

  const verifyTemplate = async (templateId) => {
    if (security.value.verificationResults.has(templateId)) {
      return security.value.verificationResults.get(templateId);
    }

    try {
      const response = await templateAPI.verifySignature(templateId);
      const result = {
        isValid: response.isValid,
        signature: response.signature,
        publisher: response.publisher,
        verifiedAt: new Date().toISOString()
      };

      security.value.verificationResults.set(templateId, result);
      return result;
    } catch (err) {
      console.error('Error verifying template:', err);
      throw err;
    }
  };

  const rateTemplate = async (templateId, rating, review = '') => {
    try {
      const response = await templateAPI.rateTemplate(templateId, rating, review);

      // Update local ratings cache
      ratings.value.set(templateId, {
        rating,
        review,
        ratedAt: new Date().toISOString()
      });

      return response;
    } catch (err) {
      console.error('Error rating template:', err);
      throw err;
    }
  };

  const getTemplateReviews = async (templateId) => {
    if (reviews.value.has(templateId)) {
      return reviews.value.get(templateId);
    }

    try {
      const response = await templateAPI.getReviews(templateId);
      reviews.value.set(templateId, response.data);
      return response.data;
    } catch (err) {
      console.error('Error fetching template reviews:', err);
      throw err;
    }
  };

  const installTemplate = async (templateId) => {
    try {
      // Download and verify template
      const template = await downloadTemplate(templateId);
      const verification = await verifyTemplate(templateId);

      if (!verification.isValid) {
        throw new Error('Template signature verification failed');
      }

      // Add to custom templates for immediate use
      customTemplates.value.push({
        ...template,
        installedAt: new Date().toISOString(),
        verified: verification.isValid
      });

      return template;
    } catch (err) {
      console.error('Error installing template:', err);
      throw err;
    }
  };

  const uninstallTemplate = (templateId) => {
    localTemplates.value = localTemplates.value.filter(t => t.id !== templateId);
    customTemplates.value = customTemplates.value.filter(t => t.id !== templateId);
  };

  const importLocalTemplate = (templateFile) => {
    try {
      const template = {
        id: `local_${Date.now()}`,
        name: templateFile.name.replace(/\.[^/.]+$/, ''),
        content: templateFile.content,
        category: 'custom',
        isLocal: true,
        createdAt: new Date().toISOString(),
        importedAt: new Date().toISOString()
      };

      localTemplates.value.push(template);
      return template;
    } catch (err) {
      console.error('Error importing local template:', err);
      throw err;
    }
  };

  const exportTemplate = (templateId) => {
    const template = [...localTemplates.value, ...customTemplates.value]
      .find(t => t.id === templateId);

    if (!template) {
      throw new Error('Template not found');
    }

    const exportData = {
      ...template,
      exportedAt: new Date().toISOString(),
      version: '1.0.0'
    };

    const blob = new Blob([JSON.stringify(exportData, null, 2)], {
      type: 'application/json'
    });

    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${template.name}-template.json`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  const syncWithMarketplace = async () => {
    try {
      // Fetch latest featured templates
      await fetchFeaturedTemplates();

      // Fetch community templates
      const communityResponse = await templateAPI.getCommunity();
      marketplace.value.community = communityResponse.data || [];

      // Fetch verified templates
      const verifiedResponse = await templateAPI.getVerified();
      marketplace.value.verified = verifiedResponse.data || [];

      // Sync user's published templates
      const publishedResponse = await templateAPI.getUserPublished();
      marketplace.value.publishedTemplates = publishedResponse.data || [];

      return true;
    } catch (err) {
      console.error('Error syncing with marketplace:', err);
      throw err;
    }
  };

  const searchMarketplace = async (query, filters = {}) => {
    try {
      const response = await templateAPI.searchMarketplace({
        query,
        ...filters
      });

      return response.data;
    } catch (err) {
      console.error('Error searching marketplace:', err);
      throw err;
    }
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

    // Reset marketplace data
    marketplace.value = {
      featured: [],
      community: [],
      verified: [],
      userTemplates: [],
      downloadHistory: [],
      publishedTemplates: []
    };

    // Reset publishing state
    publishing.value = {
      isPublishing: false,
      uploadProgress: 0,
      validationErrors: [],
      publishingStep: 'idle'
    };

    // Reset security data
    security.value.signatureCache.clear();
    security.value.verificationResults.clear();
    security.value.trustedPublishers = [];
    security.value.securityScanResults.clear();

    // Reset local templates
    localTemplates.value = [];
    customTemplates.value = [];

    // Reset ratings and reviews
    ratings.value.clear();
    reviews.value.clear();
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

    // M013 Marketplace State
    marketplace,
    publishing,
    security,
    localTemplates,
    customTemplates,
    ratings,
    reviews,

    // Computed
    filteredTemplates,
    popularTemplates,
    recentTemplates,
    hasError,
    isEmpty,

    // M013 Marketplace Computed
    featuredTemplates,
    verifiedTemplates,
    communityTemplates,
    myPublishedTemplates,
    myDownloadedTemplates,
    isPublishing,
    publishingProgress,
    totalLocalTemplates,
    templatesByVerification,
    templateStats,

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

    // M013 Marketplace Actions
    fetchFeaturedTemplates,
    downloadTemplate,
    publishTemplate,
    verifyTemplate,
    rateTemplate,
    getTemplateReviews,
    installTemplate,
    uninstallTemplate,
    importLocalTemplate,
    exportTemplate,
    syncWithMarketplace,
    searchMarketplace,

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
      },
      {
        key: 'template-marketplace',
        storage: localStorage,
        paths: [
          'marketplace.downloadHistory',
          'marketplace.publishedTemplates',
          'localTemplates',
          'customTemplates',
          'ratings',
          'reviews'
        ]
      }
    ]
  }
});
