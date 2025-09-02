/**
 * Module Interface Definitions for DevDocAI v3.0.0
 * Provides typed interfaces for interacting with operational modules
 */

class ModuleInterface {
  constructor(moduleId, baseUrl = 'http://localhost:8000') {
    this.moduleId = moduleId;
    this.baseUrl = baseUrl;
    this.apiPath = `/api/${moduleId.toLowerCase().replace('-', '/')}`;
  }

  async getStatus() {
    const response = await fetch(`${this.baseUrl}${this.apiPath}/status`);
    return response.json();
  }

  async getHealth() {
    const response = await fetch(`${this.baseUrl}${this.apiPath}/health`);
    return response.json();
  }

  async getMetrics() {
    const response = await fetch(`${this.baseUrl}${this.apiPath}/metrics`);
    return response.json();
  }
}

class M001ConfigManagerInterface extends ModuleInterface {
  constructor() {
    super('M001-ConfigManager');
  }

  async loadConfiguration(configPath = '.devdocai.yml') {
    const response = await fetch(`${this.baseUrl}${this.apiPath}/load`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ configPath })
    });
    return response.json();
  }

  async validateConfiguration(config) {
    const response = await fetch(`${this.baseUrl}${this.apiPath}/validate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ config })
    });
    return response.json();
  }

  async encryptApiKey(apiKey, provider) {
    const response = await fetch(`${this.baseUrl}${this.apiPath}/encrypt`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ apiKey, provider })
    });
    return response.json();
  }

  async getPerformanceMetrics() {
    const response = await fetch(`${this.baseUrl}${this.apiPath}/performance`);
    return response.json();
  }
}

class M002LocalStorageInterface extends ModuleInterface {
  constructor() {
    super('M002-LocalStorage');
  }

  async storeDocument(document, options = {}) {
    const response = await fetch(`${this.baseUrl}${this.apiPath}/store`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ document, options })
    });
    return response.json();
  }

  async retrieveDocument(documentId) {
    const response = await fetch(`${this.baseUrl}${this.apiPath}/retrieve/${documentId}`);
    return response.json();
  }

  async searchDocuments(query, options = {}) {
    const response = await fetch(`${this.baseUrl}${this.apiPath}/search`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ query, options })
    });
    return response.json();
  }

  async getStorageStats() {
    const response = await fetch(`${this.baseUrl}${this.apiPath}/stats`);
    return response.json();
  }

  async testEncryption() {
    const response = await fetch(`${this.baseUrl}${this.apiPath}/test/encryption`);
    return response.json();
  }

  async detectPII(content) {
    const response = await fetch(`${this.baseUrl}${this.apiPath}/pii/detect`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ content })
    });
    return response.json();
  }
}

class M003MIAIREngineInterface extends ModuleInterface {
  constructor() {
    super('M003-MIAIREngine');
  }

  async optimizeDocuments(documents, options = {}) {
    const response = await fetch(`${this.baseUrl}${this.apiPath}/optimize`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ documents, options })
    });
    return response.json();
  }

  async calculateEntropy(content) {
    const response = await fetch(`${this.baseUrl}${this.apiPath}/entropy`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ content })
    });
    return response.json();
  }

  async getPerformanceMetrics() {
    const response = await fetch(`${this.baseUrl}${this.apiPath}/performance`);
    return response.json();
  }

  async benchmarkPerformance(testSize = 100) {
    const response = await fetch(`${this.baseUrl}${this.apiPath}/benchmark`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ testSize })
    });
    return response.json();
  }
}

class M004DocumentGeneratorInterface extends ModuleInterface {
  constructor() {
    super('M004-DocumentGenerator');
  }

  async generateDocument(projectData, templateId, options = {}) {
    const response = await fetch(`${this.baseUrl}${this.apiPath}/generate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ projectData, templateId, options })
    });
    return response.json();
  }

  async generateMultipleDocuments(projectData, templateIds, options = {}) {
    const response = await fetch(`${this.baseUrl}${this.apiPath}/generate/batch`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ projectData, templateIds, options })
    });
    return response.json();
  }

  async getAvailableTemplates() {
    const response = await fetch(`${this.baseUrl}${this.apiPath}/templates`);
    return response.json();
  }

  async exportDocument(documentId, format) {
    const response = await fetch(`${this.baseUrl}${this.apiPath}/export/${documentId}/${format}`);
    return response.json();
  }
}

class M005QualityEngineInterface extends ModuleInterface {
  constructor() {
    super('M005-QualityEngine');
  }

  async analyzeQuality(content, options = {}) {
    const response = await fetch(`${this.baseUrl}${this.apiPath}/analyze`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ content, options })
    });
    return response.json();
  }

  async getQualityReport(documentId) {
    const response = await fetch(`${this.baseUrl}${this.apiPath}/report/${documentId}`);
    return response.json();
  }

  async benchmarkQuality(testSize = 10) {
    const response = await fetch(`${this.baseUrl}${this.apiPath}/benchmark`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ testSize })
    });
    return response.json();
  }
}

class M006TemplateRegistryInterface extends ModuleInterface {
  constructor() {
    super('M006-TemplateRegistry');
  }

  async getTemplate(templateId) {
    const response = await fetch(`${this.baseUrl}${this.apiPath}/template/${templateId}`);
    return response.json();
  }

  async getAllTemplates() {
    const response = await fetch(`${this.baseUrl}${this.apiPath}/templates`);
    return response.json();
  }

  async renderTemplate(templateId, variables) {
    const response = await fetch(`${this.baseUrl}${this.apiPath}/render`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ templateId, variables })
    });
    return response.json();
  }

  async validateTemplate(templateContent) {
    const response = await fetch(`${this.baseUrl}${this.apiPath}/validate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ templateContent })
    });
    return response.json();
  }
}

class M007ReviewEngineInterface extends ModuleInterface {
  constructor() {
    super('M007-ReviewEngine');
  }

  async reviewDocument(documentId, options = {}) {
    const response = await fetch(`${this.baseUrl}${this.apiPath}/review`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ documentId, options })
    });
    return response.json();
  }

  async getReviewCriteria() {
    const response = await fetch(`${this.baseUrl}${this.apiPath}/criteria`);
    return response.json();
  }

  async generateReviewReport(reviewId) {
    const response = await fetch(`${this.baseUrl}${this.apiPath}/report/${reviewId}`);
    return response.json();
  }
}

class M008LLMAdapterInterface extends ModuleInterface {
  constructor() {
    super('M008-LLMAdapter');
  }

  async sendRequest(prompt, options = {}) {
    const response = await fetch(`${this.baseUrl}${this.apiPath}/request`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ prompt, options })
    });
    return response.json();
  }

  async getProviderStatus() {
    const response = await fetch(`${this.baseUrl}${this.apiPath}/providers/status`);
    return response.json();
  }

  async getCostMetrics() {
    const response = await fetch(`${this.baseUrl}${this.apiPath}/cost/metrics`);
    return response.json();
  }

  async testProvider(providerId) {
    const response = await fetch(`${this.baseUrl}${this.apiPath}/test/${providerId}`);
    return response.json();
  }
}

class M009EnhancementPipelineInterface extends ModuleInterface {
  constructor() {
    super('M009-EnhancementPipeline');
  }

  async enhanceDocument(documentId, strategies = []) {
    const response = await fetch(`${this.baseUrl}${this.apiPath}/enhance`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ documentId, strategies })
    });
    return response.json();
  }

  async getEnhancementStrategies() {
    const response = await fetch(`${this.baseUrl}${this.apiPath}/strategies`);
    return response.json();
  }

  async batchEnhance(documentIds, options = {}) {
    const response = await fetch(`${this.baseUrl}${this.apiPath}/enhance/batch`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ documentIds, options })
    });
    return response.json();
  }
}

class M010SecurityModuleInterface extends ModuleInterface {
  constructor() {
    super('M010-SecurityModule');
  }

  async scanDocument(content, scanTypes = ['pii', 'secrets']) {
    const response = await fetch(`${this.baseUrl}${this.apiPath}/scan`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ content, scanTypes })
    });
    return response.json();
  }

  async generateSBOM(projectPath) {
    const response = await fetch(`${this.baseUrl}${this.apiPath}/sbom/generate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ projectPath })
    });
    return response.json();
  }

  async getSecurityReport() {
    const response = await fetch(`${this.baseUrl}${this.apiPath}/report`);
    return response.json();
  }

  async detectThreats(data) {
    const response = await fetch(`${this.baseUrl}${this.apiPath}/threats/detect`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ data })
    });
    return response.json();
  }
}

class M011UIComponentsInterface extends ModuleInterface {
  constructor() {
    super('M011-UIComponents');
  }

  async getDashboardData() {
    const response = await fetch(`${this.baseUrl}${this.apiPath}/dashboard/data`);
    return response.json();
  }

  async getSystemMetrics() {
    const response = await fetch(`${this.baseUrl}${this.apiPath}/metrics/system`);
    return response.json();
  }

  async updateComponentConfig(componentId, config) {
    const response = await fetch(`${this.baseUrl}${this.apiPath}/component/${componentId}/config`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ config })
    });
    return response.json();
  }

  async testAccessibility(componentId) {
    const response = await fetch(`${this.baseUrl}${this.apiPath}/component/${componentId}/accessibility`);
    return response.json();
  }
}

// Interface factory for easy instantiation
class ModuleInterfaceFactory {
  static create(moduleId) {
    const interfaces = {
      'M001-ConfigManager': M001ConfigManagerInterface,
      'M002-LocalStorage': M002LocalStorageInterface,
      'M003-MIAIREngine': M003MIAIREngineInterface,
      'M004-DocumentGenerator': M004DocumentGeneratorInterface,
      'M005-QualityEngine': M005QualityEngineInterface,
      'M006-TemplateRegistry': M006TemplateRegistryInterface,
      'M007-ReviewEngine': M007ReviewEngineInterface,
      'M008-LLMAdapter': M008LLMAdapterInterface,
      'M009-EnhancementPipeline': M009EnhancementPipelineInterface,
      'M010-SecurityModule': M010SecurityModuleInterface,
      'M011-UIComponents': M011UIComponentsInterface
    };

    const InterfaceClass = interfaces[moduleId];
    if (!InterfaceClass) {
      throw new Error(`Unknown module interface: ${moduleId}`);
    }

    return new InterfaceClass();
  }

  static createAll() {
    const moduleIds = [
      'M001-ConfigManager',
      'M002-LocalStorage', 
      'M003-MIAIREngine',
      'M004-DocumentGenerator',
      'M005-QualityEngine',
      'M006-TemplateRegistry',
      'M007-ReviewEngine',
      'M008-LLMAdapter',
      'M009-EnhancementPipeline',
      'M010-SecurityModule',
      'M011-UIComponents'
    ];

    const interfaces = {};
    for (const moduleId of moduleIds) {
      try {
        interfaces[moduleId] = this.create(moduleId);
      } catch (error) {
        console.warn(`Could not create interface for ${moduleId}: ${error.message}`);
      }
    }

    return interfaces;
  }
}

module.exports = {
  ModuleInterface,
  M001ConfigManagerInterface,
  M002LocalStorageInterface,
  M003MIAIREngineInterface,
  M004DocumentGeneratorInterface,
  M005QualityEngineInterface,
  M006TemplateRegistryInterface,
  M007ReviewEngineInterface,
  M008LLMAdapterInterface,
  M009EnhancementPipelineInterface,
  M010SecurityModuleInterface,
  M011UIComponentsInterface,
  ModuleInterfaceFactory
};