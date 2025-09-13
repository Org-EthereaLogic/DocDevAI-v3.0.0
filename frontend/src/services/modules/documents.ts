// M004: Document Generator Service

import { apiClient } from '@/services/api';
import type {
  ApiResponse,
  DocumentTemplate,
  GenerationRequest,
  GeneratedDocument,
  PaginationParams,
  PaginatedResponse,
} from '@/types/api';

export class DocumentService {
  private readonly basePath = '/documents';

  // Template Management
  async getTemplates(
    params?: Partial<PaginationParams & { category?: string; search?: string }>
  ): Promise<ApiResponse<PaginatedResponse<DocumentTemplate>>> {
    const queryParams = params ? `?${apiClient.buildPaginationParams(params as PaginationParams)}` : '';
    return apiClient.get(`${this.basePath}/templates${queryParams}`);
  }

  async getTemplate(templateId: string): Promise<ApiResponse<DocumentTemplate>> {
    return apiClient.get(`${this.basePath}/templates/${templateId}`);
  }

  async createTemplate(template: Omit<DocumentTemplate, 'id'>): Promise<ApiResponse<DocumentTemplate>> {
    return apiClient.post(`${this.basePath}/templates`, template);
  }

  async updateTemplate(
    templateId: string,
    template: Partial<DocumentTemplate>
  ): Promise<ApiResponse<DocumentTemplate>> {
    return apiClient.put(`${this.basePath}/templates/${templateId}`, template);
  }

  async deleteTemplate(templateId: string): Promise<ApiResponse<void>> {
    return apiClient.delete(`${this.basePath}/templates/${templateId}`);
  }

  // Document Generation
  async generateDocument(request: GenerationRequest): Promise<ApiResponse<GeneratedDocument>> {
    return apiClient.post(`${this.basePath}/generate`, request);
  }

  async generateDocumentAsync(request: GenerationRequest): Promise<ApiResponse<{ job_id: string }>> {
    return apiClient.post(`${this.basePath}/generate-async`, request);
  }

  async getGenerationStatus(jobId: string): Promise<ApiResponse<{
    status: 'queued' | 'processing' | 'completed' | 'failed';
    progress_percentage: number;
    estimated_completion?: string;
    result?: GeneratedDocument;
    error?: string;
  }>> {
    return apiClient.get(`${this.basePath}/generation-status/${jobId}`);
  }

  // Document Management
  async getDocuments(
    params?: Partial<PaginationParams & {
      search?: string;
      format?: string;
      health_score_min?: number;
      created_after?: string;
    }>
  ): Promise<ApiResponse<PaginatedResponse<GeneratedDocument>>> {
    const queryParams = params ? `?${apiClient.buildPaginationParams(params as PaginationParams)}` : '';
    return apiClient.get(`${this.basePath}${queryParams}`);
  }

  async getDocument(documentId: string): Promise<ApiResponse<GeneratedDocument>> {
    return apiClient.get(`${this.basePath}/${documentId}`);
  }

  async updateDocument(
    documentId: string,
    updates: Partial<Pick<GeneratedDocument, 'title' | 'content'>>
  ): Promise<ApiResponse<GeneratedDocument>> {
    return apiClient.put(`${this.basePath}/${documentId}`, updates);
  }

  async deleteDocument(documentId: string): Promise<ApiResponse<void>> {
    return apiClient.delete(`${this.basePath}/${documentId}`);
  }

  // Document Export
  async exportDocument(
    documentId: string,
    format: 'markdown' | 'html' | 'pdf' | 'docx'
  ): Promise<void> {
    await apiClient.downloadFile(
      `${this.basePath}/${documentId}/export?format=${format}`,
      `document.${format}`
    );
  }

  async bulkExport(
    documentIds: string[],
    format: 'zip' | 'pdf'
  ): Promise<void> {
    await apiClient.downloadFile(
      `${this.basePath}/bulk-export?format=${format}`,
      `documents.${format}`
    );
  }

  // Document Preview
  async previewDocument(request: GenerationRequest): Promise<ApiResponse<{
    preview: string;
    estimated_tokens: number;
    estimated_cost: number;
    estimated_time_seconds: number;
  }>> {
    return apiClient.post(`${this.basePath}/preview`, request);
  }

  // AI Enhancement
  async enhanceDocument(
    documentId: string,
    options?: {
      strategy?: 'miair_only' | 'llm_only' | 'combined' | 'weighted_consensus';
      focus_areas?: string[];
    }
  ): Promise<ApiResponse<{
    job_id: string;
    estimated_completion: string;
  }>> {
    return apiClient.post(`${this.basePath}/${documentId}/enhance`, options);
  }

  // Document History
  async getDocumentHistory(
    documentId: string
  ): Promise<ApiResponse<Array<{
    version: number;
    created_at: string;
    changes: string[];
    health_score_change: number;
  }>>> {
    return apiClient.get(`${this.basePath}/${documentId}/history`);
  }

  async revertToVersion(
    documentId: string,
    version: number
  ): Promise<ApiResponse<GeneratedDocument>> {
    return apiClient.post(`${this.basePath}/${documentId}/revert`, { version });
  }

  // Document Categories
  async getCategories(): Promise<ApiResponse<Array<{
    name: string;
    display_name: string;
    template_count: number;
    description: string;
  }>>> {
    return apiClient.get(`${this.basePath}/categories`);
  }

  // Document Statistics
  async getStatistics(): Promise<ApiResponse<{
    total_documents: number;
    total_templates: number;
    average_health_score: number;
    documents_by_format: Record<string, number>;
    generation_trends: Array<{
      date: string;
      count: number;
      average_health_score: number;
    }>;
  }>> {
    return apiClient.get(`${this.basePath}/statistics`);
  }
}

export const documentService = new DocumentService();