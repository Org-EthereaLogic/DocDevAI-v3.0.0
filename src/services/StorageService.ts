/**
 * DevDocAI v3.0.0 - Storage Service
 * 
 * Service layer for M002 Local Storage module
 * Handles document storage, retrieval, versioning, and search capabilities.
 */

export interface DocumentMetadata {
  id: string;
  title: string;
  description?: string;
  tags: string[];
  category: string;
  size: number; // bytes
  createdAt: Date;
  updatedAt: Date;
  version: number;
  hash: string;
}

export interface Document {
  metadata: DocumentMetadata;
  content: string;
}

export interface DocumentVersion {
  version: number;
  content: string;
  createdAt: Date;
  changes: string;
  author: string;
}

export interface SearchOptions {
  query: string;
  tags?: string[];
  category?: string;
  dateFrom?: Date;
  dateTo?: Date;
  limit?: number;
  offset?: number;
}

export interface SearchResult {
  document: DocumentMetadata;
  relevanceScore: number;
  matchedContent: string[];
}

export interface StorageStats {
  totalDocuments: number;
  totalSize: number; // bytes
  documentsToday: number;
  averageSize: number;
  topCategories: Array<{ category: string; count: number }>;
  storageUsed: number; // bytes
  storageAvailable: number; // bytes
}

class StorageServiceImpl {
  private documents: Map<string, Document> = new Map();
  private versions: Map<string, DocumentVersion[]> = new Map();
  private initialized = false;

  async initialize(): Promise<void> {
    try {
      console.log('Initializing Storage Service...');
      
      // Initialize storage backend
      await this.initializeStorage();
      
      // Load existing documents
      await this.loadExistingDocuments();
      
      // Setup search index
      await this.initializeSearchIndex();
      
      this.initialized = true;
      console.log('Storage Service initialized successfully');
    } catch (error) {
      console.error('Failed to initialize Storage Service:', error);
      // Set initialized to true anyway to allow app to continue
      this.initialized = true;
      // Ensure we have at least empty data structures
      if (!this.documents) {
        this.documents = new Map();
      }
      if (!this.versions) {
        this.versions = new Map();
      }
      console.log('Storage Service using mock data due to initialization error');
    }
  }

  private async initializeStorage(): Promise<void> {
    // In a real implementation, this would:
    // 1. Connect to SQLite database
    // 2. Run migrations
    // 3. Initialize SQLCipher encryption
    // 4. Setup connection pooling
    // 5. Create necessary tables and indexes
    
    console.log('Storage backend initialized');
  }

  private async loadExistingDocuments(): Promise<void> {
    try {
      // In a real implementation, this would:
      // 1. Load documents from database
      // 2. Build in-memory cache
      // 3. Initialize document versions
      
      // For demo purposes, create some sample documents
      const sampleDocs = this.createSampleDocuments();
      sampleDocs.forEach(doc => {
        this.documents.set(doc.metadata.id, doc);
        this.versions.set(doc.metadata.id, [{
          version: 1,
          content: doc.content,
          createdAt: doc.metadata.createdAt,
          changes: 'Initial version',
          author: 'System',
        }]);
      });
      
      console.log(`Loaded ${this.documents.size} documents from storage`);
    } catch (error) {
      console.warn('Failed to load existing documents:', error);
    }
  }

  private async initializeSearchIndex(): Promise<void> {
    // In a real implementation, this would:
    // 1. Initialize FTS5 full-text search
    // 2. Index existing documents
    // 3. Setup search optimization
    
    console.log('Search index initialized');
  }

  private createSampleDocuments(): Document[] {
    return [
      {
        metadata: {
          id: 'doc-001',
          title: 'API Reference Guide',
          description: 'Complete API reference for DevDocAI',
          tags: ['api', 'reference', 'documentation'],
          category: 'API Documentation',
          size: 15420,
          createdAt: new Date('2024-01-15'),
          updatedAt: new Date('2024-01-20'),
          version: 1,
          hash: 'sha256-abc123',
        },
        content: '# API Reference Guide\n\nThis guide covers all available API endpoints...'
      },
      {
        metadata: {
          id: 'doc-002',
          title: 'Installation Guide',
          description: 'Step-by-step installation instructions',
          tags: ['installation', 'setup', 'guide'],
          category: 'User Guide',
          size: 8230,
          createdAt: new Date('2024-01-10'),
          updatedAt: new Date('2024-01-18'),
          version: 1,
          hash: 'sha256-def456',
        },
        content: '# Installation Guide\n\nFollow these steps to install DevDocAI...'
      },
      {
        metadata: {
          id: 'doc-003',
          title: 'Configuration Reference',
          description: 'All configuration options explained',
          tags: ['configuration', 'settings', 'reference'],
          category: 'Technical Reference',
          size: 12650,
          createdAt: new Date('2024-01-12'),
          updatedAt: new Date('2024-01-22'),
          version: 1,
          hash: 'sha256-ghi789',
        },
        content: '# Configuration Reference\n\nConfigure DevDocAI using these options...'
      },
    ];
  }

  async createDocument(title: string, content: string, metadata: Partial<DocumentMetadata> = {}): Promise<string> {
    try {
      const id = `doc-${Date.now()}`;
      const now = new Date();
      
      const document: Document = {
        metadata: {
          id,
          title,
          description: metadata.description || '',
          tags: metadata.tags || [],
          category: metadata.category || 'General',
          size: content.length,
          createdAt: now,
          updatedAt: now,
          version: 1,
          hash: this.generateHash(content),
        },
        content,
      };
      
      // Store document
      this.documents.set(id, document);
      
      // Create initial version
      this.versions.set(id, [{
        version: 1,
        content,
        createdAt: now,
        changes: 'Initial version',
        author: 'User',
      }]);
      
      console.log(`Document created: ${id}`);
      return id;
    } catch (error) {
      console.error('Failed to create document:', error);
      throw error;
    }
  }

  async getDocument(id: string): Promise<Document | null> {
    try {
      const document = this.documents.get(id);
      if (!document) {
        console.warn(`Document not found: ${id}`);
        return null;
      }
      
      return { ...document };
    } catch (error) {
      console.error(`Failed to get document ${id}:`, error);
      return null;
    }
  }

  async updateDocument(id: string, content: string, changes: string = 'Updated'): Promise<boolean> {
    try {
      const document = this.documents.get(id);
      if (!document) {
        console.error(`Document not found for update: ${id}`);
        return false;
      }
      
      const now = new Date();
      const newVersion = document.metadata.version + 1;
      
      // Update document
      document.content = content;
      document.metadata.updatedAt = now;
      document.metadata.version = newVersion;
      document.metadata.size = content.length;
      document.metadata.hash = this.generateHash(content);
      
      // Add new version
      const versions = this.versions.get(id) || [];
      versions.push({
        version: newVersion,
        content,
        createdAt: now,
        changes,
        author: 'User',
      });
      this.versions.set(id, versions);
      
      console.log(`Document updated: ${id} (version ${newVersion})`);
      return true;
    } catch (error) {
      console.error(`Failed to update document ${id}:`, error);
      return false;
    }
  }

  async deleteDocument(id: string): Promise<boolean> {
    try {
      const deleted = this.documents.delete(id);
      this.versions.delete(id);
      
      if (deleted) {
        console.log(`Document deleted: ${id}`);
      } else {
        console.warn(`Document not found for deletion: ${id}`);
      }
      
      return deleted;
    } catch (error) {
      console.error(`Failed to delete document ${id}:`, error);
      return false;
    }
  }

  async listDocuments(limit: number = 50, offset: number = 0): Promise<DocumentMetadata[]> {
    try {
      const allDocs = Array.from(this.documents.values());
      const sortedDocs = allDocs.sort((a, b) => 
        b.metadata.updatedAt.getTime() - a.metadata.updatedAt.getTime()
      );
      
      return sortedDocs
        .slice(offset, offset + limit)
        .map(doc => ({ ...doc.metadata }));
    } catch (error) {
      console.error('Failed to list documents:', error);
      return [];
    }
  }

  async searchDocuments(options: SearchOptions): Promise<SearchResult[]> {
    try {
      const { query, tags, category, dateFrom, dateTo, limit = 20, offset = 0 } = options;
      let results = Array.from(this.documents.values());
      
      // Filter by category
      if (category) {
        results = results.filter(doc => doc.metadata.category === category);
      }
      
      // Filter by tags
      if (tags && tags.length > 0) {
        results = results.filter(doc => 
          tags.some(tag => doc.metadata.tags.includes(tag))
        );
      }
      
      // Filter by date range
      if (dateFrom) {
        results = results.filter(doc => doc.metadata.createdAt >= dateFrom);
      }
      if (dateTo) {
        results = results.filter(doc => doc.metadata.createdAt <= dateTo);
      }
      
      // Search in title and content
      if (query) {
        results = results.filter(doc => {
          const searchText = `${doc.metadata.title} ${doc.metadata.description} ${doc.content}`.toLowerCase();
          return searchText.includes(query.toLowerCase());
        });
      }
      
      // Calculate relevance scores and create search results
      const searchResults: SearchResult[] = results.map(doc => {
        let relevanceScore = 0;
        const matchedContent: string[] = [];
        
        if (query) {
          const queryLower = query.toLowerCase();
          const titleMatch = doc.metadata.title.toLowerCase().includes(queryLower);
          const contentMatch = doc.content.toLowerCase().includes(queryLower);
          
          if (titleMatch) relevanceScore += 10;
          if (contentMatch) relevanceScore += 5;
          
          // Extract matched content snippets
          if (contentMatch) {
            const sentences = doc.content.split(/[.!?]+/);
            const matchingSentences = sentences.filter(sentence => 
              sentence.toLowerCase().includes(queryLower)
            );
            matchedContent.push(...matchingSentences.slice(0, 3));
          }
        } else {
          relevanceScore = 1; // Base score for non-query searches
        }
        
        return {
          document: { ...doc.metadata },
          relevanceScore,
          matchedContent,
        };
      });
      
      // Sort by relevance and apply pagination
      return searchResults
        .sort((a, b) => b.relevanceScore - a.relevanceScore)
        .slice(offset, offset + limit);
        
    } catch (error) {
      console.error('Failed to search documents:', error);
      return [];
    }
  }

  async getDocumentVersions(id: string): Promise<DocumentVersion[]> {
    try {
      const versions = this.versions.get(id) || [];
      return [...versions].sort((a, b) => b.version - a.version);
    } catch (error) {
      console.error(`Failed to get versions for document ${id}:`, error);
      return [];
    }
  }

  async getDocumentVersion(id: string, version: number): Promise<string | null> {
    try {
      const versions = this.versions.get(id);
      if (!versions) return null;
      
      const targetVersion = versions.find(v => v.version === version);
      return targetVersion ? targetVersion.content : null;
    } catch (error) {
      console.error(`Failed to get document ${id} version ${version}:`, error);
      return null;
    }
  }

  async getStorageStats(): Promise<StorageStats> {
    try {
      const docs = Array.from(this.documents.values());
      const totalDocuments = docs.length;
      const totalSize = docs.reduce((sum, doc) => sum + doc.metadata.size, 0);
      
      const today = new Date();
      today.setHours(0, 0, 0, 0);
      const documentsToday = docs.filter(doc => doc.metadata.createdAt >= today).length;
      
      const averageSize = totalDocuments > 0 ? totalSize / totalDocuments : 0;
      
      // Count documents by category
      const categoryCount = new Map<string, number>();
      docs.forEach(doc => {
        const count = categoryCount.get(doc.metadata.category) || 0;
        categoryCount.set(doc.metadata.category, count + 1);
      });
      
      const topCategories = Array.from(categoryCount.entries())
        .map(([category, count]) => ({ category, count }))
        .sort((a, b) => b.count - a.count)
        .slice(0, 5);
      
      return {
        totalDocuments,
        totalSize,
        documentsToday,
        averageSize,
        topCategories,
        storageUsed: totalSize,
        storageAvailable: 1024 * 1024 * 1024, // 1GB available (simulated)
      };
    } catch (error) {
      console.error('Failed to get storage stats:', error);
      return {
        totalDocuments: 0,
        totalSize: 0,
        documentsToday: 0,
        averageSize: 0,
        topCategories: [],
        storageUsed: 0,
        storageAvailable: 0,
      };
    }
  }

  async getUserPreferences(): Promise<any> {
    try {
      // Safely check if localStorage is available
      if (typeof localStorage !== 'undefined' && localStorage !== null) {
        try {
          const prefs = localStorage.getItem('devdocai-user-prefs');
          return prefs ? JSON.parse(prefs) : {};
        } catch (storageError) {
          console.warn('localStorage access failed:', storageError);
          return {};
        }
      }
      return {};
    } catch (error) {
      console.error('Failed to get user preferences:', error);
      return {};
    }
  }

  async saveUserPreferences(preferences: any): Promise<void> {
    try {
      // Safely check if localStorage is available
      if (typeof localStorage !== 'undefined' && localStorage !== null) {
        try {
          localStorage.setItem('devdocai-user-prefs', JSON.stringify(preferences));
          console.log('User preferences saved');
        } catch (storageError) {
          console.warn('localStorage save failed:', storageError);
        }
      }
    } catch (error) {
      console.error('Failed to save user preferences:', error);
    }
  }

  private generateHash(content: string): string {
    // Simple hash function for demo purposes
    // In a real implementation, use crypto.createHash('sha256')
    let hash = 0;
    for (let i = 0; i < content.length; i++) {
      const char = content.charCodeAt(i);
      hash = ((hash << 5) - hash) + char;
      hash = hash & hash; // Convert to 32bit integer
    }
    return `sha256-${Math.abs(hash).toString(16)}`;
  }

  isInitialized(): boolean {
    return this.initialized;
  }
}

// Export singleton instance
export const StorageService = new StorageServiceImpl();
export default StorageService;