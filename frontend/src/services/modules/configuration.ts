// M001: Configuration Manager Service

import { apiClient } from '@/services/api';
import type {
  ApiResponse,
  ConfigurationSettings,
  PaginationParams,
} from '@/types/api';

export class ConfigurationService {
  private readonly basePath = '/configuration';

  // Get current configuration
  async getConfiguration(): Promise<ApiResponse<ConfigurationSettings>> {
    return apiClient.get(`${this.basePath}`);
  }

  // Update configuration
  async updateConfiguration(
    settings: Partial<ConfigurationSettings>
  ): Promise<ApiResponse<ConfigurationSettings>> {
    return apiClient.put(`${this.basePath}`, settings);
  }

  // Reset to defaults
  async resetToDefaults(): Promise<ApiResponse<ConfigurationSettings>> {
    return apiClient.post(`${this.basePath}/reset`);
  }

  // Validate configuration
  async validateConfiguration(
    settings: ConfigurationSettings
  ): Promise<ApiResponse<{ valid: boolean; errors: string[] }>> {
    return apiClient.post(`${this.basePath}/validate`, settings);
  }

  // Get available memory modes
  async getMemoryModes(): Promise<ApiResponse<Array<{
    mode: string;
    description: string;
    ram_requirement_gb: number;
    performance_profile: string;
  }>>> {
    return apiClient.get(`${this.basePath}/memory-modes`);
  }

  // Get available AI providers
  async getAIProviders(): Promise<ApiResponse<Array<{
    name: string;
    display_name: string;
    available: boolean;
    cost_per_1k_tokens: number;
    features: string[];
  }>>> {
    return apiClient.get(`${this.basePath}/ai-providers`);
  }

  // Test AI provider connection
  async testAIProvider(provider: string): Promise<ApiResponse<{
    success: boolean;
    response_time_ms: number;
    error?: string;
  }>> {
    return apiClient.post(`${this.basePath}/test-provider`, { provider });
  }

  // Get encryption status
  async getEncryptionStatus(): Promise<ApiResponse<{
    enabled: boolean;
    algorithm: string;
    key_location: string;
    key_exists: boolean;
  }>> {
    return apiClient.get(`${this.basePath}/encryption-status`);
  }

  // Generate new encryption key
  async generateEncryptionKey(): Promise<ApiResponse<{
    key_generated: boolean;
    backup_location: string;
  }>> {
    return apiClient.post(`${this.basePath}/generate-key`);
  }

  // Export configuration
  async exportConfiguration(): Promise<ApiResponse<{
    configuration: ConfigurationSettings;
    exported_at: string;
    format: string;
  }>> {
    return apiClient.get(`${this.basePath}/export`);
  }

  // Import configuration
  async importConfiguration(
    configData: ConfigurationSettings
  ): Promise<ApiResponse<{
    imported: boolean;
    conflicts: string[];
    applied_settings: string[];
  }>> {
    return apiClient.post(`${this.basePath}/import`, configData);
  }

  // Get system requirements
  async getSystemRequirements(): Promise<ApiResponse<{
    current_system: {
      os: string;
      python_version: string;
      memory_gb: number;
      disk_space_gb: number;
    };
    requirements: {
      min_memory_gb: number;
      recommended_memory_gb: number;
      min_disk_space_gb: number;
      supported_os: string[];
    };
    compatibility: {
      meets_minimum: boolean;
      meets_recommended: boolean;
      warnings: string[];
    };
  }>> {
    return apiClient.get(`${this.basePath}/system-requirements`);
  }
}

export const configurationService = new ConfigurationService();