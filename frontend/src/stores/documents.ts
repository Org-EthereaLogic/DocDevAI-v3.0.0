// Documents Store - M004 Integration

import { defineStore } from 'pinia';
import { ref, computed } from 'vue';
import { documentService } from '@/services';
import type {
  DocumentTemplate,
  GeneratedDocument,
  GenerationRequest,
  PaginatedResponse,
} from '@/types/api';

export const useDocumentsStore = defineStore('documents', () => {
  // State
  const templates = ref<DocumentTemplate[]>([]);
  const documents = ref<GeneratedDocument[]>([]);
  const currentDocument = ref<GeneratedDocument | null>(null);
  const selectedTemplate = ref<DocumentTemplate | null>(null);

  // Loading states
  const isLoadingTemplates = ref(false);
  const isLoadingDocuments = ref(false);
  const isGenerating = ref(false);
  const isLoadingDocument = ref(false);

  // Error states
  const templatesError = ref<string | null>(null);
  const documentsError = ref<string | null>(null);
  const generationError = ref<string | null>(null);
  const documentError = ref<string | null>(null);

  // Pagination and filters
  const templatesPagination = ref({
    page: 1,
    limit: 20,
    total: 0,
    totalPages: 0,
  });

  const documentsPagination = ref({
    page: 1,
    limit: 20,
    total: 0,
    totalPages: 0,
  });

  const templatesFilter = ref({
    category: '',
    search: '',
  });

  const documentsFilter = ref({
    search: '',
    format: '',
    healthScoreMin: 0,
  });

  // Getters
  const templatesCount = computed(() => templates.value.length);
  const documentsCount = computed(() => documents.value.length);

  const templateCategories = computed(() => {
    const categories = new Set(templates.value.map(t => t.category));
    return Array.from(categories).sort();
  });

  const documentFormats = computed(() => {
    const formats = new Set(documents.value.map(d => d.format));
    return Array.from(formats).sort();
  });

  const filteredTemplates = computed(() => {
    return templates.value.filter(template => {
      const matchesCategory = !templatesFilter.value.category ||
        template.category === templatesFilter.value.category;

      const matchesSearch = !templatesFilter.value.search ||
        template.name.toLowerCase().includes(templatesFilter.value.search.toLowerCase()) ||
        template.description.toLowerCase().includes(templatesFilter.value.search.toLowerCase());

      return matchesCategory && matchesSearch;
    });
  });

  const filteredDocuments = computed(() => {
    return documents.value.filter(document => {
      const matchesSearch = !documentsFilter.value.search ||
        document.title.toLowerCase().includes(documentsFilter.value.search.toLowerCase());

      const matchesFormat = !documentsFilter.value.format ||
        document.format === documentsFilter.value.format;

      const matchesHealthScore = document.health_score >= documentsFilter.value.healthScoreMin;

      return matchesSearch && matchesFormat && matchesHealthScore;
    });
  });

  const averageHealthScore = computed(() => {
    if (documents.value.length === 0) return 0;
    const sum = documents.value.reduce((acc, doc) => acc + doc.health_score, 0);
    return Math.round(sum / documents.value.length);
  });

  // Actions - Templates
  const fetchTemplates = async (page = 1, search?: string, category?: string) => {
    isLoadingTemplates.value = true;
    templatesError.value = null;

    try {
      const response = await documentService.getTemplates({
        page,
        limit: templatesPagination.value.limit,
        search,
        category,
      });

      const data = response.data as PaginatedResponse<DocumentTemplate>;
      templates.value = data.items;
      templatesPagination.value = {
        page: data.page,
        limit: data.limit,
        total: data.total,
        totalPages: data.total_pages,
      };
    } catch (err) {
      templatesError.value = err instanceof Error ? err.message : 'Failed to fetch templates';
      throw err;
    } finally {
      isLoadingTemplates.value = false;
    }
  };

  const fetchTemplate = async (templateId: string) => {
    try {
      const response = await documentService.getTemplate(templateId);
      selectedTemplate.value = response.data;
      return response.data;
    } catch (err) {
      templatesError.value = err instanceof Error ? err.message : 'Failed to fetch template';
      throw err;
    }
  };

  const createTemplate = async (template: Omit<DocumentTemplate, 'id'>) => {
    try {
      const response = await documentService.createTemplate(template);
      templates.value.unshift(response.data);
      return response.data;
    } catch (err) {
      templatesError.value = err instanceof Error ? err.message : 'Failed to create template';
      throw err;
    }
  };

  const updateTemplate = async (templateId: string, updates: Partial<DocumentTemplate>) => {
    try {
      const response = await documentService.updateTemplate(templateId, updates);
      const index = templates.value.findIndex(t => t.id === templateId);
      if (index !== -1) {
        templates.value[index] = response.data;
      }
      if (selectedTemplate.value?.id === templateId) {
        selectedTemplate.value = response.data;
      }
      return response.data;
    } catch (err) {
      templatesError.value = err instanceof Error ? err.message : 'Failed to update template';
      throw err;
    }
  };

  const deleteTemplate = async (templateId: string) => {
    try {
      await documentService.deleteTemplate(templateId);
      templates.value = templates.value.filter(t => t.id !== templateId);
      if (selectedTemplate.value?.id === templateId) {
        selectedTemplate.value = null;
      }
    } catch (err) {
      templatesError.value = err instanceof Error ? err.message : 'Failed to delete template';
      throw err;
    }
  };

  // Actions - Documents
  const fetchDocuments = async (page = 1, filters = documentsFilter.value) => {
    isLoadingDocuments.value = true;
    documentsError.value = null;

    try {
      const response = await documentService.getDocuments({
        page,
        limit: documentsPagination.value.limit,
        search: filters.search,
        format: filters.format,
        health_score_min: filters.healthScoreMin,
      });

      const data = response.data as PaginatedResponse<GeneratedDocument>;
      documents.value = data.items;
      documentsPagination.value = {
        page: data.page,
        limit: data.limit,
        total: data.total,
        totalPages: data.total_pages,
      };
    } catch (err) {
      documentsError.value = err instanceof Error ? err.message : 'Failed to fetch documents';
      throw err;
    } finally {
      isLoadingDocuments.value = false;
    }
  };

  const fetchDocument = async (documentId: string) => {
    isLoadingDocument.value = true;
    documentError.value = null;

    try {
      const response = await documentService.getDocument(documentId);
      currentDocument.value = response.data;
      return response.data;
    } catch (err) {
      documentError.value = err instanceof Error ? err.message : 'Failed to fetch document';
      throw err;
    } finally {
      isLoadingDocument.value = false;
    }
  };

  const generateDocument = async (request: GenerationRequest) => {
    isGenerating.value = true;
    generationError.value = null;

    try {
      const response = await documentService.generateDocument(request);
      documents.value.unshift(response.data);
      currentDocument.value = response.data;
      return response.data;
    } catch (err) {
      generationError.value = err instanceof Error ? err.message : 'Failed to generate document';
      throw err;
    } finally {
      isGenerating.value = false;
    }
  };

  const updateDocument = async (
    documentId: string,
    updates: Partial<Pick<GeneratedDocument, 'title' | 'content'>>
  ) => {
    try {
      const response = await documentService.updateDocument(documentId, updates);
      const index = documents.value.findIndex(d => d.id === documentId);
      if (index !== -1) {
        documents.value[index] = response.data;
      }
      if (currentDocument.value?.id === documentId) {
        currentDocument.value = response.data;
      }
      return response.data;
    } catch (err) {
      documentsError.value = err instanceof Error ? err.message : 'Failed to update document';
      throw err;
    }
  };

  const deleteDocument = async (documentId: string) => {
    try {
      await documentService.deleteDocument(documentId);
      documents.value = documents.value.filter(d => d.id !== documentId);
      if (currentDocument.value?.id === documentId) {
        currentDocument.value = null;
      }
    } catch (err) {
      documentsError.value = err instanceof Error ? err.message : 'Failed to delete document';
      throw err;
    }
  };

  const exportDocument = async (documentId: string, format: 'markdown' | 'html' | 'pdf' | 'docx') => {
    try {
      await documentService.exportDocument(documentId, format);
    } catch (err) {
      documentsError.value = err instanceof Error ? err.message : 'Failed to export document';
      throw err;
    }
  };

  const enhanceDocument = async (
    documentId: string,
    options?: {
      strategy?: 'miair_only' | 'llm_only' | 'combined' | 'weighted_consensus';
      focus_areas?: string[];
    }
  ) => {
    try {
      const response = await documentService.enhanceDocument(documentId, options);
      return response.data;
    } catch (err) {
      documentsError.value = err instanceof Error ? err.message : 'Failed to enhance document';
      throw err;
    }
  };

  // Utility Actions
  const setTemplatesFilter = (filter: Partial<typeof templatesFilter.value>) => {
    templatesFilter.value = { ...templatesFilter.value, ...filter };
  };

  const setDocumentsFilter = (filter: Partial<typeof documentsFilter.value>) => {
    documentsFilter.value = { ...documentsFilter.value, ...filter };
  };

  const clearErrors = () => {
    templatesError.value = null;
    documentsError.value = null;
    generationError.value = null;
    documentError.value = null;
  };

  const clearCurrentDocument = () => {
    currentDocument.value = null;
  };

  const clearSelectedTemplate = () => {
    selectedTemplate.value = null;
  };

  // Initialize store
  const initialize = async () => {
    await Promise.all([
      fetchTemplates(),
      fetchDocuments(),
    ]);
  };

  return {
    // State
    templates: readonly(templates),
    documents: readonly(documents),
    currentDocument: readonly(currentDocument),
    selectedTemplate: readonly(selectedTemplate),

    // Loading states
    isLoadingTemplates: readonly(isLoadingTemplates),
    isLoadingDocuments: readonly(isLoadingDocuments),
    isGenerating: readonly(isGenerating),
    isLoadingDocument: readonly(isLoadingDocument),

    // Error states
    templatesError: readonly(templatesError),
    documentsError: readonly(documentsError),
    generationError: readonly(generationError),
    documentError: readonly(documentError),

    // Pagination and filters
    templatesPagination: readonly(templatesPagination),
    documentsPagination: readonly(documentsPagination),
    templatesFilter: readonly(templatesFilter),
    documentsFilter: readonly(documentsFilter),

    // Getters
    templatesCount,
    documentsCount,
    templateCategories,
    documentFormats,
    filteredTemplates,
    filteredDocuments,
    averageHealthScore,

    // Actions
    fetchTemplates,
    fetchTemplate,
    createTemplate,
    updateTemplate,
    deleteTemplate,
    fetchDocuments,
    fetchDocument,
    generateDocument,
    updateDocument,
    deleteDocument,
    exportDocument,
    enhanceDocument,
    setTemplatesFilter,
    setDocumentsFilter,
    clearErrors,
    clearCurrentDocument,
    clearSelectedTemplate,
    initialize,
  };
});

// Readonly helper (if not imported from elsewhere)
function readonly<T>(ref: Ref<T>): Readonly<Ref<T>> {
  return ref as Readonly<Ref<T>>;
}

export type DocumentsStore = ReturnType<typeof useDocumentsStore>;