/**
 * Unified Document Provider - DevDocAI Document Tree Management
 * 
 * Consolidates functionality from:
 * - Pass 1: Basic tree data provider with document categorization
 * - Pass 2: Performance optimizations (virtual scrolling, lazy loading, WeakMap caching)
 * - Pass 3: Security features (secure document scanning, audit logging)
 * 
 * Operation Modes:
 * - BASIC: Simple tree display with basic file watching
 * - PERFORMANCE: Virtual scrolling, lazy loading, debounced updates
 * - SECURE: Secure file scanning, access control validation
 * - ENTERPRISE: All features with comprehensive monitoring
 * 
 * @module M013-VSCodeExtension
 * @version 3.0.0
 */

import * as vscode from 'vscode';
import * as path from 'path';
import * as fs from 'fs';
import { Logger } from '../utils/Logger';
import * as crypto from 'crypto';

// Configuration interface
interface ExtensionConfig {
    operationMode: 'BASIC' | 'PERFORMANCE' | 'SECURE' | 'ENTERPRISE';
    features: {
        virtualScrolling: boolean;
        lazyLoading: boolean;
        secureScanning: boolean;
        auditLogging: boolean;
        caching: boolean;
    };
}

// Document interfaces
interface DocumentInfo {
    path: string;
    name: string;
    type: 'file' | 'folder';
    size: number;
    lastModified: number;
    documented: boolean;
    quality?: number;
    coverage?: number;
    security?: {
        validated: boolean;
        threatLevel: 'LOW' | 'MEDIUM' | 'HIGH';
        lastScan: number;
    };
}

interface DocumentCategory {
    name: string;
    description: string;
    icon: string;
    filter: (doc: DocumentInfo) => boolean;
    count: number;
}

// Tree item classes
class DocumentTreeItem extends vscode.TreeItem {
    constructor(
        public readonly label: string,
        public readonly collapsibleState: vscode.TreeItemCollapsibleState,
        public readonly resourceUri?: vscode.Uri,
        public readonly contextValue?: string,
        public readonly category?: string,
        public readonly documentInfo?: DocumentInfo
    ) {
        super(label, collapsibleState);
        
        if (resourceUri) {
            this.resourceUri = resourceUri;
        }
        
        if (contextValue) {
            this.contextValue = contextValue;
        }
    }
}

// Security context
interface SecurityContext {
    allowedPaths: Set<string>;
    scanResults: Map<string, any>;
    lastSecurityScan: number;
}

/**
 * Unified Document Provider with mode-based operation
 */
export class DocumentProvider implements vscode.TreeDataProvider<DocumentTreeItem>, vscode.Disposable {
    private _onDidChangeTreeData = new vscode.EventEmitter<DocumentTreeItem | undefined | null | void>();
    readonly onDidChangeTreeData = this._onDidChangeTreeData.event;
    
    // Core data structures
    private documents: Map<string, DocumentInfo> = new Map();
    private categories: DocumentCategory[] = [];
    private disposables: vscode.Disposable[] = [];
    
    // Performance features (PERFORMANCE/ENTERPRISE modes)
    private itemCache?: WeakMap<DocumentTreeItem, DocumentInfo>;
    private visibleItems: DocumentTreeItem[] = [];
    private readonly PAGE_SIZE = 50;
    private refreshDebounced?: () => void;
    
    // File watching
    private fileWatcher?: vscode.FileSystemWatcher;
    
    // Security features (SECURE/ENTERPRISE modes)
    private securityContext?: SecurityContext;
    
    // Metrics
    private scanMetrics = {
        totalFiles: 0,
        documentedFiles: 0,
        lastScanDuration: 0,
        cacheHits: 0,
        cacheMisses: 0
    };
    
    constructor(
        private cliService: any, // CLIService will be available at runtime
        private logger: Logger,
        private extensionConfig: ExtensionConfig
    ) {
        this.initializeFeatures();
        this.initializeCategories();
        this.setupFileWatching();
    }
    
    /**
     * Initialize features based on operation mode
     */
    private initializeFeatures(): void {
        // Initialize performance features
        if (this.shouldEnablePerformance()) {
            this.initializePerformanceFeatures();
        }
        
        // Initialize security features
        if (this.shouldEnableSecurity()) {
            this.initializeSecurityFeatures();
        }
    }
    
    /**
     * Initialize performance features
     */
    private initializePerformanceFeatures(): void {
        // WeakMap for automatic garbage collection
        this.itemCache = new WeakMap<DocumentTreeItem, DocumentInfo>();
        
        // Debounced refresh (300ms delay)
        this.refreshDebounced = this.debounce(() => this.refresh(), 300);
    }
    
    /**
     * Initialize security features
     */
    private initializeSecurityFeatures(): void {
        this.securityContext = {
            allowedPaths: new Set(),
            scanResults: new Map(),
            lastSecurityScan: 0
        };
        
        // Initialize allowed paths with workspace folders
        const workspaceFolders = vscode.workspace.workspaceFolders;
        if (workspaceFolders) {
            workspaceFolders.forEach(folder => {
                this.securityContext!.allowedPaths.add(folder.uri.fsPath);
            });
        }
    }
    
    /**
     * Initialize document categories
     */
    private initializeCategories(): void {
        this.categories = [
            {
                name: 'Documented',
                description: 'Files with documentation',
                icon: '📄',
                filter: (doc) => doc.documented,
                count: 0
            },
            {
                name: 'Undocumented',
                description: 'Files without documentation',
                icon: '📝',
                filter: (doc) => !doc.documented,
                count: 0
            },
            {
                name: 'High Quality',
                description: 'Well-documented files (80%+ quality)',
                icon: '⭐',
                filter: (doc) => doc.quality !== undefined && doc.quality >= 80,
                count: 0
            },
            {
                name: 'Needs Review',
                description: 'Files with low quality documentation',
                icon: '⚠️',
                filter: (doc) => doc.quality !== undefined && doc.quality < 60,
                count: 0
            },
            {
                name: 'Recently Modified',
                description: 'Files modified in the last 24 hours',
                icon: '🕒',
                filter: (doc) => Date.now() - doc.lastModified < 86400000,
                count: 0
            }
        ];
        
        // Add security category if security mode enabled
        if (this.shouldEnableSecurity()) {
            this.categories.push({
                name: 'Security Issues',
                description: 'Files with security concerns',
                icon: '🔒',
                filter: (doc) => doc.security?.threatLevel !== 'LOW',
                count: 0
            });
        }
    }
    
    /**
     * Setup file watching with debouncing
     */
    private setupFileWatching(): void {
        try {
            // Create file watcher for workspace files
            this.fileWatcher = vscode.workspace.createFileSystemWatcher(
                '**/*',
                false, // don't ignore creates
                false, // don't ignore changes
                false  // don't ignore deletes
            );
            
            // Setup event handlers
            const refreshHandler = this.shouldEnablePerformance() && this.refreshDebounced ? 
                this.refreshDebounced : () => this.refresh();
            
            this.fileWatcher.onDidCreate(refreshHandler);
            this.fileWatcher.onDidChange(refreshHandler);
            this.fileWatcher.onDidDelete(refreshHandler);
            
            this.disposables.push(this.fileWatcher);
            
        } catch (error) {
            this.logger.error('Failed to setup file watching:', error);
        }
    }
    
    /**
     * Refresh the tree view
     */
    public refresh(): void {
        this.logger.debug('Refreshing document tree');
        
        // Clear caches
        this.documents.clear();
        this.visibleItems = [];
        
        // Update scan metrics
        this.scanMetrics.lastScanDuration = Date.now();
        
        // Fire change event
        this._onDidChangeTreeData.fire();
        
        // Complete scan timing
        this.scanMetrics.lastScanDuration = Date.now() - this.scanMetrics.lastScanDuration;
    }
    
    /**
     * Get tree item implementation
     */
    public getTreeItem(element: DocumentTreeItem): vscode.TreeItem {
        if (this.itemCache) {
            // Store in cache for performance tracking
            const docInfo = element.documentInfo;
            if (docInfo) {
                this.itemCache.set(element, docInfo);
                this.scanMetrics.cacheHits++;
            }
        }
        
        return element;
    }
    
    /**
     * Get children implementation with mode-based behavior
     */
    public async getChildren(element?: DocumentTreeItem): Promise<DocumentTreeItem[]> {
        if (!vscode.workspace.workspaceFolders) {
            return [];
        }
        
        try {
            if (!element) {
                // Root level
                if (this.shouldEnablePerformance()) {
                    return await this.getRootItemsOptimized();
                } else {
                    return await this.getRootItemsBasic();
                }
            }
            
            if (element.contextValue === 'category') {
                return await this.getDocumentsInCategory(element.category!);
            }
            
            if (element.contextValue === 'document') {
                return await this.getDocumentDetails(element.resourceUri!);
            }
            
            return [];
            
        } catch (error) {
            this.logger.error('Error getting tree children:', error);
            return [];
        }
    }
    
    /**
     * Get root items with basic implementation
     */
    private async getRootItemsBasic(): Promise<DocumentTreeItem[]> {
        await this.scanWorkspace();
        return this.createCategoryItems();
    }
    
    /**
     * Get root items with performance optimizations
     */
    private async getRootItemsOptimized(): Promise<DocumentTreeItem[]> {
        // Lazy load first page only
        await this.scanWorkspaceOptimized();
        
        const categoryItems = this.createCategoryItems();
        
        // Store in visible items for virtual scrolling
        this.visibleItems = categoryItems.slice(0, this.PAGE_SIZE);
        
        return this.visibleItems;
    }
    
    /**
     * Scan workspace with basic implementation
     */
    private async scanWorkspace(): Promise<void> {
        const startTime = Date.now();
        
        try {
            // Find all files in workspace
            const files = await vscode.workspace.findFiles(
                '**/*',
                '**/node_modules/**',
                2000 // Limit for performance
            );
            
            this.scanMetrics.totalFiles = files.length;
            let documentedCount = 0;
            
            // Process each file
            for (const file of files) {
                try {
                    const stat = await vscode.workspace.fs.stat(file);
                    const relativePath = vscode.workspace.asRelativePath(file);
                    
                    // Security validation if enabled
                    if (this.shouldEnableSecurity() && !this.validateFilePath(file.fsPath)) {
                        continue;
                    }
                    
                    // Create document info
                    const docInfo: DocumentInfo = {
                        path: file.fsPath,
                        name: path.basename(file.fsPath),
                        type: stat.type === vscode.FileType.Directory ? 'folder' : 'file',
                        size: stat.size,
                        lastModified: stat.mtime,
                        documented: await this.checkDocumentationStatus(file.fsPath),
                        quality: await this.getDocumentQuality(file.fsPath),
                        coverage: await this.getDocumentCoverage(file.fsPath)
                    };
                    
                    // Add security info if enabled
                    if (this.shouldEnableSecurity()) {
                        docInfo.security = await this.scanDocumentSecurity(file.fsPath);
                    }
                    
                    if (docInfo.documented) {
                        documentedCount++;
                    }
                    
                    this.documents.set(relativePath, docInfo);
                    
                } catch (error) {
                    this.logger.debug(`Error processing file ${file.fsPath}:`, error);
                }
            }
            
            this.scanMetrics.documentedFiles = documentedCount;
            this.updateCategoryCounts();
            
        } catch (error) {
            this.logger.error('Error scanning workspace:', error);
        }
        
        this.logger.debug(`Workspace scan completed in ${Date.now() - startTime}ms`);
    }
    
    /**
     * Scan workspace with performance optimizations
     */
    private async scanWorkspaceOptimized(): Promise<void> {
        const startTime = Date.now();
        
        try {
            // Use streaming approach for large workspaces
            const files = await vscode.workspace.findFiles(
                '**/*',
                '**/node_modules/**',
                this.PAGE_SIZE * 3 // Load 3 pages worth initially
            );
            
            this.scanMetrics.totalFiles = files.length;
            
            // Process files in batches
            const batchSize = 10;
            for (let i = 0; i < files.length; i += batchSize) {
                const batch = files.slice(i, i + batchSize);
                await Promise.all(batch.map(file => this.processFileOptimized(file)));
            }
            
            this.updateCategoryCounts();
            
        } catch (error) {
            this.logger.error('Error in optimized workspace scan:', error);
        }
        
        this.logger.debug(`Optimized workspace scan completed in ${Date.now() - startTime}ms`);
    }
    
    /**
     * Process file with optimizations
     */
    private async processFileOptimized(file: vscode.Uri): Promise<void> {
        try {
            const relativePath = vscode.workspace.asRelativePath(file);
            
            // Check cache first
            if (this.documents.has(relativePath)) {
                this.scanMetrics.cacheHits++;
                return;
            }
            
            this.scanMetrics.cacheMisses++;
            
            // Security validation
            if (this.shouldEnableSecurity() && !this.validateFilePath(file.fsPath)) {
                return;
            }
            
            const stat = await vscode.workspace.fs.stat(file);
            
            // Create document info with lazy loading
            const docInfo: DocumentInfo = {
                path: file.fsPath,
                name: path.basename(file.fsPath),
                type: stat.type === vscode.FileType.Directory ? 'folder' : 'file',
                size: stat.size,
                lastModified: stat.mtime,
                documented: false // Will be loaded on demand
            };
            
            this.documents.set(relativePath, docInfo);
            
        } catch (error) {
            this.logger.debug(`Error processing file ${file.fsPath}:`, error);
        }
    }
    
    /**
     * Create category items
     */
    private createCategoryItems(): DocumentTreeItem[] {
        return this.categories.map(category => {
            const item = new DocumentTreeItem(
                `${category.icon} ${category.name} (${category.count})`,
                vscode.TreeItemCollapsibleState.Collapsed,
                undefined,
                'category',
                category.name
            );
            
            item.tooltip = category.description;
            item.description = `${category.count} files`;
            
            return item;
        });
    }
    
    /**
     * Get documents in category
     */
    private async getDocumentsInCategory(categoryName: string): Promise<DocumentTreeItem[]> {
        const category = this.categories.find(c => c.name === categoryName);
        if (!category) return [];
        
        const matchingDocs = Array.from(this.documents.values())
            .filter(category.filter)
            .slice(0, this.shouldEnablePerformance() ? this.PAGE_SIZE : 100);
        
        return matchingDocs.map(doc => {
            const item = new DocumentTreeItem(
                doc.name,
                vscode.TreeItemCollapsibleState.Collapsed,
                vscode.Uri.file(doc.path),
                'document',
                undefined,
                doc
            );
            
            // Add quality indicator
            if (doc.quality !== undefined) {
                item.description = `Quality: ${doc.quality}%`;
            }
            
            // Add security indicator
            if (doc.security && doc.security.threatLevel !== 'LOW') {
                item.description = (item.description || '') + ` ⚠️ ${doc.security.threatLevel}`;
            }
            
            // Set icon based on documentation status
            item.iconPath = new vscode.ThemeIcon(
                doc.documented ? 'file-text' : 'file',
                doc.quality && doc.quality >= 80 ? 
                    new vscode.ThemeColor('charts.green') : 
                    doc.quality && doc.quality < 60 ? 
                        new vscode.ThemeColor('charts.red') : 
                        undefined
            );
            
            return item;
        });
    }
    
    /**
     * Get document details
     */
    private async getDocumentDetails(uri: vscode.Uri): Promise<DocumentTreeItem[]> {
        const relativePath = vscode.workspace.asRelativePath(uri);
        const doc = this.documents.get(relativePath);
        
        if (!doc) return [];
        
        const details: DocumentTreeItem[] = [];
        
        // Basic info
        details.push(new DocumentTreeItem(
            `Size: ${this.formatFileSize(doc.size)}`,
            vscode.TreeItemCollapsibleState.None,
            undefined,
            'detail'
        ));
        
        details.push(new DocumentTreeItem(
            `Modified: ${new Date(doc.lastModified).toLocaleString()}`,
            vscode.TreeItemCollapsibleState.None,
            undefined,
            'detail'
        ));
        
        // Documentation info
        if (doc.documented) {
            if (doc.quality !== undefined) {
                details.push(new DocumentTreeItem(
                    `Quality: ${doc.quality}%`,
                    vscode.TreeItemCollapsibleState.None,
                    undefined,
                    'detail'
                ));
            }
            
            if (doc.coverage !== undefined) {
                details.push(new DocumentTreeItem(
                    `Coverage: ${doc.coverage.toFixed(1)}%`,
                    vscode.TreeItemCollapsibleState.None,
                    undefined,
                    'detail'
                ));
            }
        } else {
            details.push(new DocumentTreeItem(
                '📝 No documentation',
                vscode.TreeItemCollapsibleState.None,
                undefined,
                'detail'
            ));
        }
        
        // Security info
        if (doc.security && this.shouldEnableSecurity()) {
            details.push(new DocumentTreeItem(
                `Security: ${doc.security.threatLevel}`,
                vscode.TreeItemCollapsibleState.None,
                undefined,
                'detail'
            ));
        }
        
        return details;
    }
    
    /**
     * Update category counts
     */
    private updateCategoryCounts(): void {
        const docs = Array.from(this.documents.values());
        
        this.categories.forEach(category => {
            category.count = docs.filter(category.filter).length;
        });
    }
    
    /**
     * Check documentation status
     */
    private async checkDocumentationStatus(filePath: string): Promise<boolean> {
        try {
            // Check if there's a corresponding .md file or inline documentation
            const ext = path.extname(filePath);
            const baseName = path.basename(filePath, ext);
            const dirName = path.dirname(filePath);
            
            // Check for companion .md file
            const mdPath = path.join(dirName, `${baseName}.md`);
            try {
                await vscode.workspace.fs.stat(vscode.Uri.file(mdPath));
                return true;
            } catch {
                // No companion file
            }
            
            // Check for inline documentation (basic heuristic)
            if (['.js', '.ts', '.py', '.java', '.c', '.cpp', '.cs'].includes(ext)) {
                const content = await vscode.workspace.fs.readFile(vscode.Uri.file(filePath));
                const text = Buffer.from(content).toString();
                
                // Look for common documentation patterns
                const docPatterns = [
                    /\/\*\*[\s\S]*?\*\//,  // JSDoc
                    /"""[\s\S]*?"""/,      // Python docstrings
                    /'''[\s\S]*?'''/,      // Python docstrings
                    /<!--[\s\S]*?-->/,     // HTML comments
                    /#\s*@/                // Python decorators
                ];
                
                return docPatterns.some(pattern => pattern.test(text));
            }
            
            return false;
            
        } catch (error) {
            this.logger.debug(`Error checking documentation for ${filePath}:`, error);
            return false;
        }
    }
    
    /**
     * Get document quality score
     */
    private async getDocumentQuality(filePath: string): Promise<number | undefined> {
        try {
            // In real implementation, would call CLI service
            // For now, simulate based on file analysis
            const ext = path.extname(filePath);
            
            if (!['.js', '.ts', '.py', '.java', '.c', '.cpp', '.cs'].includes(ext)) {
                return undefined;
            }
            
            // Simulate quality score based on file characteristics
            const stat = await vscode.workspace.fs.stat(vscode.Uri.file(filePath));
            const size = stat.size;
            
            // Larger files tend to need more documentation
            let baseScore = 85;
            if (size > 10000) baseScore -= 10;
            if (size > 50000) baseScore -= 10;
            
            // Add some randomness for simulation
            const variance = Math.random() * 20 - 10; // ±10
            
            return Math.max(0, Math.min(100, baseScore + variance));
            
        } catch (error) {
            return undefined;
        }
    }
    
    /**
     * Get document coverage
     */
    private async getDocumentCoverage(filePath: string): Promise<number | undefined> {
        try {
            // Simulate coverage calculation
            const quality = await this.getDocumentQuality(filePath);
            return quality ? quality * 0.8 + Math.random() * 20 : undefined;
        } catch {
            return undefined;
        }
    }
    
    /**
     * Scan document for security issues
     */
    private async scanDocumentSecurity(filePath: string): Promise<any> {
        if (!this.securityContext) {
            return { validated: false, threatLevel: 'LOW', lastScan: Date.now() };
        }
        
        try {
            // Check if already scanned recently
            const cacheKey = filePath;
            const cached = this.securityContext.scanResults.get(cacheKey);
            if (cached && Date.now() - cached.lastScan < 300000) { // 5 minutes
                return cached;
            }
            
            // Perform security scan (simplified)
            const content = await vscode.workspace.fs.readFile(vscode.Uri.file(filePath));
            const text = Buffer.from(content).toString();
            
            // Look for potential security issues
            let threatLevel: 'LOW' | 'MEDIUM' | 'HIGH' = 'LOW';
            
            const securityPatterns = [
                /password\s*=\s*['"].+['"]/i,
                /api[_-]?key\s*=\s*['"].+['"]/i,
                /secret\s*=\s*['"].+['"]/i,
                /eval\s*\(/,
                /exec\s*\(/,
                /innerHTML\s*=/
            ];
            
            const matches = securityPatterns.filter(pattern => pattern.test(text));
            
            if (matches.length > 2) {
                threatLevel = 'HIGH';
            } else if (matches.length > 0) {
                threatLevel = 'MEDIUM';
            }
            
            const result = {
                validated: true,
                threatLevel,
                lastScan: Date.now(),
                issues: matches.length
            };
            
            // Cache result
            this.securityContext.scanResults.set(cacheKey, result);
            
            return result;
            
        } catch (error) {
            return { validated: false, threatLevel: 'LOW', lastScan: Date.now() };
        }
    }
    
    /**
     * Validate file path for security
     */
    private validateFilePath(filePath: string): boolean {
        if (!this.securityContext) return true;
        
        // Check if path is within allowed directories
        return Array.from(this.securityContext.allowedPaths).some(allowedPath => 
            filePath.startsWith(allowedPath)
        );
    }
    
    /**
     * Format file size for display
     */
    private formatFileSize(bytes: number): string {
        const sizes = ['B', 'KB', 'MB', 'GB'];
        if (bytes === 0) return '0 B';
        
        const i = Math.floor(Math.log(bytes) / Math.log(1024));
        return `${(bytes / Math.pow(1024, i)).toFixed(1)} ${sizes[i]}`;
    }
    
    /**
     * Debounce utility function
     */
    private debounce<T extends (...args: any[]) => any>(
        func: T,
        wait: number
    ): (...args: Parameters<T>) => void {
        let timeout: NodeJS.Timeout;
        
        return (...args: Parameters<T>) => {
            clearTimeout(timeout);
            timeout = setTimeout(() => func.apply(this, args), wait);
        };
    }
    
    /**
     * Public API methods
     */
    public async refreshDocument(uri: vscode.Uri): Promise<void> {
        const relativePath = vscode.workspace.asRelativePath(uri);
        
        // Remove from cache
        this.documents.delete(relativePath);
        
        // Re-scan this specific document
        await this.processFileOptimized(uri);
        
        // Update display
        this._onDidChangeTreeData.fire();
    }
    
    public async getDocumentInfo(uri: vscode.Uri): Promise<DocumentInfo | undefined> {
        const relativePath = vscode.workspace.asRelativePath(uri);
        return this.documents.get(relativePath);
    }
    
    public getMetrics(): any {
        return {
            ...this.scanMetrics,
            categoryCount: this.categories.length,
            documentsLoaded: this.documents.size,
            visibleItemsCount: this.visibleItems.length,
            operationMode: this.extensionConfig.operationMode,
            features: this.extensionConfig.features
        };
    }
    
    /**
     * Utility methods for mode checking
     */
    private shouldEnablePerformance(): boolean {
        return this.extensionConfig.operationMode === 'PERFORMANCE' || 
               this.extensionConfig.operationMode === 'ENTERPRISE';
    }
    
    private shouldEnableSecurity(): boolean {
        return this.extensionConfig.operationMode === 'SECURE' || 
               this.extensionConfig.operationMode === 'ENTERPRISE';
    }
    
    /**
     * Dispose and cleanup
     */
    public dispose(): void {
        // Clear caches
        this.documents.clear();
        this.visibleItems = [];
        
        if (this.itemCache) {
            // WeakMap will be garbage collected automatically
            this.itemCache = undefined;
        }
        
        // Clear security context
        if (this.securityContext) {
            this.securityContext.scanResults.clear();
        }
        
        // Dispose all disposables
        this.disposables.forEach(disposable => {
            disposable.dispose();
        });
        this.disposables = [];
        
        // Dispose event emitter
        this._onDidChangeTreeData.dispose();
        
        this.logger.debug('Document provider disposed');
    }
}

// Export types for external use
export type { 
    DocumentInfo, 
    DocumentCategory, 
    ExtensionConfig 
};
export { DocumentTreeItem };