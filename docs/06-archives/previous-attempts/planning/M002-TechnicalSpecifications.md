# M002 Local Storage System - Technical Specifications

## 1. TypeScript Interfaces

### 1.1 Core Storage Interfaces

```typescript
// IStorageManager.ts
export interface IStorageManager {
  initialize(config: IStorageConfig): Promise<void>;
  shutdown(): Promise<void>;
  
  // Document operations
  saveDocument(document: IDocument): Promise<string>;
  getDocument(id: string): Promise<IDocument | null>;
  updateDocument(id: string, updates: Partial<IDocument>): Promise<void>;
  deleteDocument(id: string): Promise<boolean>;
  
  // Query operations
  query(params: IQuery): Promise<IQueryResult>;
  count(params: IQuery): Promise<number>;
  exists(id: string): Promise<boolean>;
  
  // Transaction operations
  beginTransaction(): ITransaction;
  
  // Backup operations
  backup(path: string): Promise<void>;
  restore(path: string): Promise<void>;
  
  // Utility operations
  getStatistics(): Promise<IStorageStatistics>;
  vacuum(): Promise<void>;
  verify(): Promise<IVerificationResult>;
}

// IDocument.ts
export interface IDocument {
  id: string;                          // UUID v4
  type: DocumentType;                  // Document type enum
  title: string;                       // Document title (max 255 chars)
  content: string;                     // Document content (encrypted)
  metadata: IMetadata;                 // Associated metadata
  version: number;                     // Version number (starts at 1)
  checksum: string;                    // SHA-256 hash for integrity
  createdAt: Date;                     // Creation timestamp
  updatedAt: Date;                     // Last update timestamp
  createdBy: string;                   // User/system identifier
  tags: string[];                      // Searchable tags
  relationships: IRelationship[];      // Document relationships
  encrypted: boolean;                  // Encryption status
  compressionType?: CompressionType;   // Optional compression
  attachments?: IAttachment[];         // Optional attachments
}

// IMetadata.ts
export interface IMetadata {
  id: string;                          // Metadata UUID
  documentId: string;                  // Associated document ID
  category: string;                    // Document category
  priority: Priority;                  // Priority level
  status: DocumentStatus;              // Current status
  language: string;                    // ISO 639-1 language code
  encoding: string;                    // Character encoding
  mimeType: string;                    // MIME type
  size: number;                        // Size in bytes
  wordCount?: number;                  // Word count
  readTime?: number;                   // Estimated read time (minutes)
  complexity?: IComplexityScore;       // Complexity metrics
  qualityScore?: number;               // Quality score (0-100)
  customFields: Record<string, any>;   // Extensible fields
  searchableText?: string;             // Extracted searchable text
  keywords?: string[];                 // Extracted keywords
}

// IQuery.ts
export interface IQuery {
  // Filter criteria
  filters?: IFilterCriteria;
  
  // Sorting
  orderBy?: ISortCriteria[];
  
  // Pagination
  limit?: number;
  offset?: number;
  
  // Field selection
  select?: string[];
  
  // Relationships to include
  include?: string[];
  
  // Full-text search
  search?: string;
  
  // Aggregation
  groupBy?: string[];
  having?: IFilterCriteria;
}

export interface IFilterCriteria {
  // Logical operators
  and?: IFilterCriteria[];
  or?: IFilterCriteria[];
  not?: IFilterCriteria;
  
  // Field comparisons
  field?: string;
  operator?: FilterOperator;
  value?: any;
}

export interface ISortCriteria {
  field: string;
  direction: 'asc' | 'desc';
}

export interface IQueryResult {
  documents: IDocument[];
  total: number;
  offset: number;
  limit: number;
  executionTime: number;
}

// ITransaction.ts
export interface ITransaction {
  id: string;
  status: TransactionStatus;
  
  // Document operations within transaction
  saveDocument(document: IDocument): Promise<string>;
  updateDocument(id: string, updates: Partial<IDocument>): Promise<void>;
  deleteDocument(id: string): Promise<boolean>;
  
  // Transaction control
  commit(): Promise<void>;
  rollback(): Promise<void>;
  
  // Transaction info
  getOperations(): IOperation[];
  getDuration(): number;
}

// IRelationship.ts
export interface IRelationship {
  id: string;
  sourceId: string;
  targetId: string;
  type: RelationshipType;
  metadata?: Record<string, any>;
  bidirectional: boolean;
  createdAt: Date;
}

// IAttachment.ts
export interface IAttachment {
  id: string;
  documentId: string;
  filename: string;
  mimeType: string;
  size: number;
  checksum: string;
  data: Buffer | string;  // Binary data or base64
  encrypted: boolean;
  compressionType?: CompressionType;
}

// IStorageStatistics.ts
export interface IStorageStatistics {
  totalDocuments: number;
  totalSize: number;
  documentsByType: Record<DocumentType, number>;
  averageDocumentSize: number;
  oldestDocument: Date;
  newestDocument: Date;
  encryptedDocuments: number;
  compressionRatio?: number;
  indexSize: number;
  fragmentationLevel: number;
}

// IVerificationResult.ts
export interface IVerificationResult {
  valid: boolean;
  errors: IVerificationError[];
  warnings: IVerificationWarning[];
  statistics: {
    documentsChecked: number;
    metadataChecked: number;
    relationshipsChecked: number;
    corruptedDocuments: number;
    missingMetadata: number;
    orphanedRelationships: number;
  };
}
```

### 1.2 Enums and Types

```typescript
// Enums.ts
export enum DocumentType {
  REQUIREMENTS = 'requirements',
  ARCHITECTURE = 'architecture',
  API = 'api',
  TEST_PLAN = 'test_plan',
  USER_MANUAL = 'user_manual',
  RELEASE_NOTES = 'release_notes',
  README = 'readme',
  CONTRIBUTING = 'contributing',
  LICENSE = 'license',
  CHANGELOG = 'changelog',
  DESIGN = 'design',
  SPECIFICATION = 'specification',
  TUTORIAL = 'tutorial',
  REFERENCE = 'reference',
  REPORT = 'report',
  PRESENTATION = 'presentation',
  EMAIL = 'email',
  MEMO = 'memo',
  PROPOSAL = 'proposal',
  CONTRACT = 'contract',
  INVOICE = 'invoice',
  OTHER = 'other'
}

export enum Priority {
  CRITICAL = 'critical',
  HIGH = 'high',
  MEDIUM = 'medium',
  LOW = 'low',
  NONE = 'none'
}

export enum DocumentStatus {
  DRAFT = 'draft',
  IN_REVIEW = 'in_review',
  APPROVED = 'approved',
  PUBLISHED = 'published',
  ARCHIVED = 'archived',
  DELETED = 'deleted',
  PENDING = 'pending',
  REJECTED = 'rejected'
}

export enum RelationshipType {
  PARENT_CHILD = 'parent_child',
  REFERENCES = 'references',
  RELATED_TO = 'related_to',
  DEPENDS_ON = 'depends_on',
  CONFLICTS_WITH = 'conflicts_with',
  REPLACES = 'replaces',
  IMPLEMENTS = 'implements',
  VALIDATES = 'validates',
  DERIVED_FROM = 'derived_from'
}

export enum CompressionType {
  NONE = 'none',
  GZIP = 'gzip',
  BROTLI = 'brotli',
  LZ4 = 'lz4',
  ZSTD = 'zstd'
}

export enum FilterOperator {
  EQUALS = 'eq',
  NOT_EQUALS = 'ne',
  GREATER_THAN = 'gt',
  GREATER_THAN_OR_EQUAL = 'gte',
  LESS_THAN = 'lt',
  LESS_THAN_OR_EQUAL = 'lte',
  IN = 'in',
  NOT_IN = 'nin',
  CONTAINS = 'contains',
  NOT_CONTAINS = 'ncontains',
  STARTS_WITH = 'starts',
  ENDS_WITH = 'ends',
  REGEX = 'regex',
  IS_NULL = 'null',
  IS_NOT_NULL = 'nnull'
}

export enum TransactionStatus {
  PENDING = 'pending',
  IN_PROGRESS = 'in_progress',
  COMMITTED = 'committed',
  ROLLED_BACK = 'rolled_back',
  FAILED = 'failed'
}

export interface IComplexityScore {
  readability: number;      // 0-100
  technicalDepth: number;   // 0-100
  vocabularyLevel: number;  // 0-100
  structuralComplexity: number; // 0-100
  overall: number;          // 0-100
}

export interface IOperation {
  type: 'create' | 'update' | 'delete';
  target: 'document' | 'metadata' | 'relationship';
  id: string;
  timestamp: Date;
  data?: any;
}

export interface IVerificationError {
  type: 'corruption' | 'missing' | 'invalid';
  entity: string;
  id: string;
  message: string;
  severity: 'critical' | 'high' | 'medium';
}

export interface IVerificationWarning {
  type: string;
  entity: string;
  id: string;
  message: string;
}
```

---

## 2. Service Implementation Specifications

### 2.1 StorageManager Service

```typescript
// StorageManager.ts
import { IStorageManager, IDocument, IQuery, IQueryResult } from '../interfaces';
import { ConfigurationManager } from '../../M001-ConfigurationManager';
import { DatabaseConnection } from './DatabaseConnection';
import { DocumentService } from './DocumentService';
import { QueryService } from './QueryService';
import { TransactionManager } from './TransactionManager';
import { BackupService } from './BackupService';
import { StorageCache } from '../utils/StorageCache';
import { StorageMetrics } from '../utils/StorageMetrics';

export class StorageManager implements IStorageManager {
  private static instance: StorageManager;
  private config: IStorageConfig;
  private db: DatabaseConnection;
  private documentService: DocumentService;
  private queryService: QueryService;
  private transactionManager: TransactionManager;
  private backupService: BackupService;
  private cache: StorageCache;
  private metrics: StorageMetrics;
  private initialized: boolean = false;

  private constructor() {
    // Private constructor for singleton
  }

  public static getInstance(): StorageManager {
    if (!StorageManager.instance) {
      StorageManager.instance = new StorageManager();
    }
    return StorageManager.instance;
  }

  public async initialize(config: IStorageConfig): Promise<void> {
    if (this.initialized) {
      throw new Error('StorageManager already initialized');
    }

    this.config = config;
    
    // Initialize database connection
    this.db = new DatabaseConnection();
    await this.db.connect(config);
    
    // Initialize services
    this.documentService = new DocumentService(this.db);
    this.queryService = new QueryService(this.db);
    this.transactionManager = new TransactionManager(this.db);
    this.backupService = new BackupService(this.db);
    
    // Initialize utilities
    this.cache = new StorageCache(config.cacheEnabled, config.cacheSizeMB);
    this.metrics = new StorageMetrics();
    
    // Run migrations if needed
    await this.runMigrations();
    
    this.initialized = true;
  }

  // Implementation continues...
}
```

### 2.2 DatabaseConnection Service

```typescript
// DatabaseConnection.ts
import Database from 'better-sqlite3';
import { IStorageConfig } from '../../M001-ConfigurationManager/interfaces';
import { SecurityUtils } from '../../M001-ConfigurationManager/utils';

export class DatabaseConnection {
  private db: Database.Database | null = null;
  private config: IStorageConfig | null = null;
  private connectionPool: Database.Database[] = [];
  private maxConnections: number = 10;

  public async connect(config: IStorageConfig): Promise<void> {
    this.config = config;
    
    const dbPath = config.type === 'memory' ? ':memory:' : config.path;
    
    // Validate path if not memory database
    if (config.type !== 'memory' && dbPath) {
      SecurityUtils.validatePath(dbPath, process.cwd());
    }
    
    // Create main connection
    this.db = new Database(dbPath, {
      verbose: process.env.NODE_ENV === 'development' ? console.log : undefined,
      fileMustExist: false
    });
    
    // Enable SQLCipher if encryption is enabled
    if (config.encryptionEnabled) {
      await this.enableEncryption();
    }
    
    // Configure database settings
    this.configureDatabase();
    
    // Initialize connection pool
    this.initializeConnectionPool();
  }

  private async enableEncryption(): Promise<void> {
    if (!this.db) throw new Error('Database not connected');
    
    // Derive encryption key from configuration
    const masterKey = this.deriveMasterKey();
    
    // Set SQLCipher encryption
    this.db.pragma(`cipher = 'aes-256-gcm'`);
    this.db.pragma(`key = '${masterKey}'`);
    this.db.pragma(`cipher_integrity_check`);
  }

  private configureDatabase(): void {
    if (!this.db) throw new Error('Database not connected');
    
    // Performance optimizations
    this.db.pragma('journal_mode = WAL');
    this.db.pragma('synchronous = NORMAL');
    this.db.pragma('cache_size = -64000'); // 64MB cache
    this.db.pragma('temp_store = MEMORY');
    this.db.pragma('mmap_size = 30000000000'); // 30GB mmap
    
    // Security settings
    this.db.pragma('trusted_schema = OFF');
    this.db.pragma('cell_size_check = ON');
    
    // Enable foreign keys
    this.db.pragma('foreign_keys = ON');
  }

  // Implementation continues...
}
```

---

## 3. Storage Strategies

### 3.1 Data Storage Strategy

#### Document Storage
- **Primary Storage**: SQLite database with normalized schema
- **Binary Data**: Stored as BLOB columns for attachments
- **Large Documents**: Automatic chunking for documents >1MB
- **Compression**: Optional zstd compression for content
- **Versioning**: Copy-on-write for version history

#### Metadata Storage
- **Indexed Fields**: All searchable metadata fields indexed
- **JSON Fields**: Custom fields stored as JSON with indexing
- **Full-Text Search**: FTS5 virtual tables for content search
- **Calculated Fields**: Stored procedures for derived values

### 3.2 Encryption Strategy

#### Multi-Layer Encryption
```typescript
class StorageEncryption {
  // Layer 1: Database-level encryption (SQLCipher)
  private enableDatabaseEncryption(key: string): void {
    // SQLCipher configuration
  }
  
  // Layer 2: Field-level encryption for sensitive data
  public async encryptField(
    value: string, 
    fieldName: string
  ): Promise<EncryptedField> {
    const fieldKey = await this.deriveFieldKey(fieldName);
    const { encrypted, iv, tag } = SecurityUtils.encryptData(value, fieldKey);
    
    return {
      data: encrypted,
      iv: iv,
      tag: tag,
      algorithm: 'aes-256-gcm',
      keyId: this.currentKeyId
    };
  }
  
  // Layer 3: Attachment encryption
  public async encryptAttachment(
    data: Buffer
  ): Promise<EncryptedAttachment> {
    // Stream cipher for large files
    const cipher = crypto.createCipheriv('aes-256-gcm', this.attachmentKey, iv);
    // Process in chunks for memory efficiency
  }
}
```

#### Key Management
- **Master Key**: Derived from user password + salt using PBKDF2
- **Database Key**: Derived from master key for SQLCipher
- **Field Keys**: Unique keys per field type derived from master
- **Key Rotation**: Scheduled rotation with re-encryption
- **Key Storage**: OS keychain integration where available

### 3.3 Query Optimization Strategy

#### Index Strategy
```sql
-- Primary indexes
CREATE INDEX idx_documents_type_status ON documents(type, status);
CREATE INDEX idx_documents_created_updated ON documents(created_at, updated_at);
CREATE INDEX idx_metadata_priority_category ON metadata(priority, category);

-- Full-text search
CREATE VIRTUAL TABLE documents_fts USING fts5(
  title, content, tags,
  content=documents,
  content_rowid=id
);

-- JSON indexes for custom fields
CREATE INDEX idx_metadata_custom ON metadata(json_extract(custom_fields, '$.projectId'));
```

#### Query Optimization
- **Query Plans**: Analyze with EXPLAIN QUERY PLAN
- **Prepared Statements**: Cache and reuse for common queries
- **Query Batching**: Combine multiple queries when possible
- **Result Limiting**: Always use LIMIT for large result sets

---

## 4. Error Handling and Validation

### 4.1 Validation Strategy

```typescript
class StorageValidator {
  // Document validation
  public validateDocument(document: IDocument): ValidationResult {
    const errors: ValidationError[] = [];
    
    // Required fields
    if (!document.title?.trim()) {
      errors.push({
        field: 'title',
        message: 'Title is required',
        code: 'REQUIRED_FIELD'
      });
    }
    
    // Field length limits
    if (document.title?.length > 255) {
      errors.push({
        field: 'title',
        message: 'Title exceeds maximum length of 255',
        code: 'MAX_LENGTH'
      });
    }
    
    // Content size limits
    if (document.content?.length > 10 * 1024 * 1024) { // 10MB
      errors.push({
        field: 'content',
        message: 'Content exceeds maximum size of 10MB',
        code: 'MAX_SIZE'
      });
    }
    
    // Type validation
    if (!Object.values(DocumentType).includes(document.type)) {
      errors.push({
        field: 'type',
        message: 'Invalid document type',
        code: 'INVALID_ENUM'
      });
    }
    
    // Checksum validation
    if (document.checksum) {
      const calculated = this.calculateChecksum(document);
      if (calculated !== document.checksum) {
        errors.push({
          field: 'checksum',
          message: 'Checksum mismatch',
          code: 'INTEGRITY_ERROR'
        });
      }
    }
    
    return {
      valid: errors.length === 0,
      errors
    };
  }
  
  // Query validation
  public validateQuery(query: IQuery): ValidationResult {
    const errors: ValidationError[] = [];
    
    // Pagination limits
    if (query.limit && query.limit > 1000) {
      errors.push({
        field: 'limit',
        message: 'Limit exceeds maximum of 1000',
        code: 'MAX_LIMIT'
      });
    }
    
    // Valid field names
    if (query.select) {
      const validFields = this.getValidFields();
      const invalidFields = query.select.filter(f => !validFields.includes(f));
      if (invalidFields.length > 0) {
        errors.push({
          field: 'select',
          message: `Invalid fields: ${invalidFields.join(', ')}`,
          code: 'INVALID_FIELDS'
        });
      }
    }
    
    return {
      valid: errors.length === 0,
      errors
    };
  }
}
```

### 4.2 Error Handling

```typescript
// Custom error classes
export class StorageError extends Error {
  constructor(
    message: string,
    public code: string,
    public details?: any
  ) {
    super(message);
    this.name = 'StorageError';
  }
}

export class ValidationError extends StorageError {
  constructor(field: string, message: string) {
    super(message, 'VALIDATION_ERROR', { field });
    this.name = 'ValidationError';
  }
}

export class EncryptionError extends StorageError {
  constructor(message: string, details?: any) {
    super(message, 'ENCRYPTION_ERROR', details);
    this.name = 'EncryptionError';
  }
}

export class TransactionError extends StorageError {
  constructor(message: string, transactionId: string) {
    super(message, 'TRANSACTION_ERROR', { transactionId });
    this.name = 'TransactionError';
  }
}

// Error handler
export class StorageErrorHandler {
  public handle(error: unknown): StorageError {
    // SQLite errors
    if (error instanceof Database.SqliteError) {
      return this.handleSqliteError(error);
    }
    
    // Encryption errors
    if (error instanceof Error && error.message.includes('decrypt')) {
      return new EncryptionError('Decryption failed', { 
        originalError: error.message 
      });
    }
    
    // Validation errors
    if (error instanceof ValidationError) {
      return error;
    }
    
    // Generic errors
    if (error instanceof Error) {
      return new StorageError(
        'Storage operation failed',
        'UNKNOWN_ERROR',
        { originalError: error.message }
      );
    }
    
    return new StorageError(
      'Unknown error occurred',
      'UNKNOWN_ERROR'
    );
  }
  
  private handleSqliteError(error: Database.SqliteError): StorageError {
    // Map SQLite error codes to storage errors
    switch (error.code) {
      case 'SQLITE_CONSTRAINT_UNIQUE':
        return new StorageError('Document already exists', 'DUPLICATE_KEY');
      case 'SQLITE_CONSTRAINT_FOREIGNKEY':
        return new StorageError('Invalid reference', 'INVALID_REFERENCE');
      case 'SQLITE_FULL':
        return new StorageError('Storage full', 'STORAGE_FULL');
      case 'SQLITE_READONLY':
        return new StorageError('Database is read-only', 'READ_ONLY');
      case 'SQLITE_CORRUPT':
        return new StorageError('Database corruption detected', 'CORRUPTION');
      default:
        return new StorageError(
          'Database operation failed',
          'DATABASE_ERROR',
          { sqliteCode: error.code }
        );
    }
  }
}
```

---

## 5. Performance Specifications

### 5.1 Caching Implementation

```typescript
class StorageCache {
  private documentCache: LRUCache<string, IDocument>;
  private queryCache: LRUCache<string, IQueryResult>;
  private metadataCache: LRUCache<string, IMetadata>;
  
  constructor(
    private enabled: boolean,
    private maxSizeMB: number
  ) {
    const maxItems = this.calculateMaxItems(maxSizeMB);
    
    this.documentCache = new LRUCache({
      max: maxItems,
      ttl: 1000 * 60 * 5, // 5 minutes
      updateAgeOnGet: true,
      updateAgeOnHas: true
    });
    
    this.queryCache = new LRUCache({
      max: 100,
      ttl: 1000 * 60 * 2, // 2 minutes
      updateAgeOnGet: false
    });
    
    this.metadataCache = new LRUCache({
      max: maxItems * 2,
      ttl: 1000 * 60 * 10, // 10 minutes
      updateAgeOnGet: true
    });
  }
  
  public async getDocument(id: string): Promise<IDocument | undefined> {
    if (!this.enabled) return undefined;
    
    const cached = this.documentCache.get(id);
    if (cached) {
      this.metrics.recordCacheHit('document');
      return cached;
    }
    
    this.metrics.recordCacheMiss('document');
    return undefined;
  }
  
  public setDocument(id: string, document: IDocument): void {
    if (!this.enabled) return;
    
    this.documentCache.set(id, document);
    
    // Also cache metadata
    if (document.metadata) {
      this.metadataCache.set(document.metadata.id, document.metadata);
    }
  }
  
  public invalidateDocument(id: string): void {
    this.documentCache.delete(id);
    this.invalidateQueriesContaining(id);
  }
  
  private invalidateQueriesContaining(documentId: string): void {
    // Invalidate all cached queries that might contain this document
    for (const [key, result] of this.queryCache.entries()) {
      if (result.documents.some(doc => doc.id === documentId)) {
        this.queryCache.delete(key);
      }
    }
  }
}
```

### 5.2 Connection Pooling

```typescript
class ConnectionPool {
  private pool: Database.Database[] = [];
  private available: Database.Database[] = [];
  private inUse: Map<Database.Database, Date> = new Map();
  
  constructor(
    private config: IStorageConfig,
    private minConnections: number = 2,
    private maxConnections: number = 10
  ) {
    this.initialize();
  }
  
  private async initialize(): Promise<void> {
    // Create minimum connections
    for (let i = 0; i < this.minConnections; i++) {
      const conn = await this.createConnection();
      this.pool.push(conn);
      this.available.push(conn);
    }
  }
  
  public async acquire(): Promise<Database.Database> {
    // Return available connection
    if (this.available.length > 0) {
      const conn = this.available.pop()!;
      this.inUse.set(conn, new Date());
      return conn;
    }
    
    // Create new connection if under limit
    if (this.pool.length < this.maxConnections) {
      const conn = await this.createConnection();
      this.pool.push(conn);
      this.inUse.set(conn, new Date());
      return conn;
    }
    
    // Wait for connection to become available
    return this.waitForConnection();
  }
  
  public release(conn: Database.Database): void {
    if (this.inUse.has(conn)) {
      this.inUse.delete(conn);
      this.available.push(conn);
    }
  }
  
  private async waitForConnection(timeout: number = 5000): Promise<Database.Database> {
    const start = Date.now();
    
    while (Date.now() - start < timeout) {
      if (this.available.length > 0) {
        return this.acquire();
      }
      await new Promise(resolve => setTimeout(resolve, 100));
    }
    
    throw new Error('Connection pool timeout');
  }
}
```

### 5.3 Performance Metrics

```typescript
class StorageMetrics {
  private metrics: Map<string, IMetric> = new Map();
  
  public recordOperation(
    operation: string,
    duration: number,
    success: boolean
  ): void {
    const key = `operation.${operation}`;
    
    if (!this.metrics.has(key)) {
      this.metrics.set(key, {
        count: 0,
        totalDuration: 0,
        minDuration: Infinity,
        maxDuration: 0,
        avgDuration: 0,
        successCount: 0,
        errorCount: 0
      });
    }
    
    const metric = this.metrics.get(key)!;
    metric.count++;
    metric.totalDuration += duration;
    metric.minDuration = Math.min(metric.minDuration, duration);
    metric.maxDuration = Math.max(metric.maxDuration, duration);
    metric.avgDuration = metric.totalDuration / metric.count;
    
    if (success) {
      metric.successCount++;
    } else {
      metric.errorCount++;
    }
  }
  
  public getMetrics(): IMetricsReport {
    const report: IMetricsReport = {
      operations: {},
      cache: {
        hitRate: this.calculateCacheHitRate(),
        size: this.getCacheSize(),
        evictions: this.getCacheEvictions()
      },
      database: {
        connections: this.getConnectionStats(),
        queries: this.getQueryStats(),
        transactions: this.getTransactionStats()
      },
      performance: {
        avgResponseTime: this.getAvgResponseTime(),
        throughput: this.getThroughput(),
        errorRate: this.getErrorRate()
      }
    };
    
    for (const [key, metric] of this.metrics.entries()) {
      if (key.startsWith('operation.')) {
        const operation = key.substring(10);
        report.operations[operation] = metric;
      }
    }
    
    return report;
  }
}
```

---

## 6. Security Specifications

### 6.1 Access Control Implementation

```typescript
class StorageAccessControl {
  private permissions: Map<string, IPermission> = new Map();
  
  public async checkAccess(
    actor: string,
    resource: string,
    action: string
  ): Promise<boolean> {
    // Check direct permissions
    const key = `${actor}:${resource}:${action}`;
    if (this.permissions.has(key)) {
      return this.permissions.get(key)!.allowed;
    }
    
    // Check role-based permissions
    const roles = await this.getUserRoles(actor);
    for (const role of roles) {
      const roleKey = `role:${role}:${resource}:${action}`;
      if (this.permissions.has(roleKey)) {
        return this.permissions.get(roleKey)!.allowed;
      }
    }
    
    // Default deny
    return false;
  }
  
  public async audit(
    actor: string,
    action: string,
    resource: string,
    result: 'success' | 'failure',
    details?: any
  ): Promise<void> {
    const entry: IAuditEntry = {
      timestamp: new Date(),
      actor,
      action,
      resource,
      result,
      details,
      ipAddress: this.getClientIP(),
      userAgent: this.getUserAgent()
    };
    
    await this.auditRepository.create(entry);
  }
}
```

### 6.2 Input Sanitization

```typescript
class StorageSanitizer {
  // SQL injection prevention
  public sanitizeSQL(value: string): string {
    // Use parameterized queries instead of string concatenation
    // This is just for extra safety on dynamic column names
    return value.replace(/[^a-zA-Z0-9_]/g, '');
  }
  
  // Path traversal prevention
  public sanitizePath(path: string): string {
    // Remove dangerous characters
    let safe = path.replace(/\.\./g, '');
    safe = safe.replace(/[<>:"|?*]/g, '');
    safe = safe.replace(/\x00/g, ''); // Null bytes
    
    // Ensure path is within allowed directory
    const resolved = path.resolve(safe);
    const allowed = path.resolve(this.config.basePath);
    
    if (!resolved.startsWith(allowed)) {
      throw new SecurityError('Path traversal attempt detected');
    }
    
    return resolved;
  }
  
  // XSS prevention for stored content
  public sanitizeHTML(html: string): string {
    // Use DOMPurify or similar library
    return DOMPurify.sanitize(html, {
      ALLOWED_TAGS: ['b', 'i', 'em', 'strong', 'a', 'p', 'br'],
      ALLOWED_ATTR: ['href']
    });
  }
  
  // JSON injection prevention
  public sanitizeJSON(json: string): any {
    try {
      // Parse with size limit
      if (json.length > 1024 * 1024) { // 1MB limit
        throw new Error('JSON too large');
      }
      
      const parsed = JSON.parse(json);
      
      // Check depth
      if (this.getDepth(parsed) > 10) {
        throw new Error('JSON too deep');
      }
      
      return parsed;
    } catch (error) {
      throw new ValidationError('Invalid JSON');
    }
  }
}
```

---

## Document Metadata

**Created**: 2025-08-25  
**Author**: DevDocAI Implementation Team  
**Version**: 1.0.0  
**Status**: APPROVED  
**Review Date**: 2025-08-25  
**Next Review**: 2025-09-01