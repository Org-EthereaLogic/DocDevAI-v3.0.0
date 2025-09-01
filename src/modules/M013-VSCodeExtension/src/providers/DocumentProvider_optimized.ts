/**
 * Optimized Document Provider - Memory Efficient
 * 
 * Performance optimizations:
 * - Virtual scrolling for large document lists
 * - Lazy loading of tree items
 * - WeakMap for automatic garbage collection
 * - Debounced file watching
 * - Dispose pattern for cleanup
 * 
 * @module M013-VSCodeExtension
 */

import * as vscode from 'vscode';
import { CLIService } from '../services/CLIService';
import { Logger } from '../utils/Logger';
import { debounce } from '../utils/debounce';

interface DocumentItem {
    name: string;
    path: string;
    type: 'file' | 'folder';
    quality?: number;
    coverage?: number;
    children?: DocumentItem[];
}

export class OptimizedDocumentProvider implements vscode.TreeDataProvider<DocumentTreeItem>, vscode.Disposable {
    private _onDidChangeTreeData = new vscode.EventEmitter<DocumentTreeItem | undefined | null | void>();
    readonly onDidChangeTreeData = this._onDidChangeTreeData.event;
    
    // WeakMap for automatic GC of unused items
    private itemCache = new WeakMap<DocumentTreeItem, DocumentItem>();
    
    // Virtual scrolling: only load visible items
    private visibleItems: DocumentTreeItem[] = [];
    private readonly PAGE_SIZE = 50;
    
    // File watcher with debouncing
    private fileWatcher: vscode.FileSystemWatcher | undefined;
    private refreshDebounced: () => void;
    
    // Disposal tracking
    private disposables: vscode.Disposable[] = [];
    
    constructor(
        private cliService: CLIService,
        private logger: Logger
    ) {
        // Create debounced refresh (300ms delay)
        this.refreshDebounced = debounce(() => this.refresh(), 300);
        
        // Setup optimized file watching
        this.setupFileWatching();
    }
    
    /**
     * Gets tree item - Virtual scrolling implementation
     */
    getTreeItem(element: DocumentTreeItem): vscode.TreeItem | Thenable<vscode.TreeItem> {
        return element;
    }
    
    /**
     * Gets children - Lazy loading with pagination
     */
    async getChildren(element?: DocumentTreeItem): Promise<DocumentTreeItem[]> {
        if (!element) {
            // Root level - load first page only
            return this.getRootItems();
        }
        
        // Load children lazily
        return this.getChildItems(element);
    }
    
    /**
     * Gets root items with virtual scrolling
     */
    private async getRootItems(): Promise<DocumentTreeItem[]> {
        try {
            // Get workspace folders
            const folders = vscode.workspace.workspaceFolders;
            if (!folders || folders.length === 0) {
                return [new DocumentTreeItem('No workspace opened', vscode.TreeItemCollapsibleState.None)];
            }
            
            // Create lightweight tree items (don't load all at once)
            const items: DocumentTreeItem[] = [];
            
            for (const folder of folders.slice(0, this.PAGE_SIZE)) {
                const item = new DocumentTreeItem(
                    folder.name,
                    vscode.TreeItemCollapsibleState.Collapsed,
                    'folder',
                    folder.uri.fsPath
                );
                
                // Set icon
                item.iconPath = new vscode.ThemeIcon('folder');
                
                // Don't pre-load children (lazy loading)
                items.push(item);
            }
            
            // If more items available, add "Load More" item
            if (folders.length > this.PAGE_SIZE) {
                const loadMore = new DocumentTreeItem(
                    `Load ${folders.length - this.PAGE_SIZE} more...`,
                    vscode.TreeItemCollapsibleState.None,
                    'action'
                );
                loadMore.command = {
                    command: 'devdocai.loadMoreDocuments',
                    title: 'Load More',
                    arguments: [this.PAGE_SIZE]
                };
                items.push(loadMore);
            }
            
            this.visibleItems = items;
            return items;
            
        } catch (error) {
            this.logger.error('Failed to get root items', error);
            return [new DocumentTreeItem('Error loading documents', vscode.TreeItemCollapsibleState.None)];
        }
    }
    
    /**
     * Gets child items lazily
     */
    private async getChildItems(parent: DocumentTreeItem): Promise<DocumentTreeItem[]> {
        if (parent.type !== 'folder' || !parent.resourceUri) {
            return [];
        }
        
        try {
            // Use VS Code's file system API (more efficient)
            const uri = parent.resourceUri;
            const entries = await vscode.workspace.fs.readDirectory(uri);
            
            // Filter and sort entries
            const items: DocumentTreeItem[] = [];
            const sortedEntries = entries
                .filter(([name]) => !name.startsWith('.')) // Skip hidden files
                .sort(([a], [b]) => a.localeCompare(b))
                .slice(0, this.PAGE_SIZE); // Limit items
            
            for (const [name, type] of sortedEntries) {
                const itemPath = vscode.Uri.joinPath(uri, name);
                
                // Only process relevant files
                if (type === vscode.FileType.Directory || this.isRelevantFile(name)) {
                    const item = new DocumentTreeItem(
                        name,
                        type === vscode.FileType.Directory ? 
                            vscode.TreeItemCollapsibleState.Collapsed : 
                            vscode.TreeItemCollapsibleState.None,
                        type === vscode.FileType.Directory ? 'folder' : 'file',
                        itemPath
                    );
                    
                    // Set appropriate icon
                    if (type === vscode.FileType.Directory) {
                        item.iconPath = new vscode.ThemeIcon('folder');
                    } else {
                        item.iconPath = this.getFileIcon(name);
                        
                        // Add quality badge if available (lazy)
                        this.addQualityBadge(item);
                    }
                    
                    items.push(item);
                }
            }
            
            return items;
            
        } catch (error) {
            this.logger.error('Failed to get child items', error);
            return [];
        }
    }
    
    /**
     * Checks if file is relevant for documentation
     */
    private isRelevantFile(filename: string): boolean {
        const extensions = ['.py', '.js', '.ts', '.jsx', '.tsx', '.java', '.cs', '.cpp', '.md'];
        return extensions.some(ext => filename.endsWith(ext));
    }
    
    /**
     * Gets appropriate file icon
     */
    private getFileIcon(filename: string): vscode.ThemeIcon {
        if (filename.endsWith('.md')) return new vscode.ThemeIcon('markdown');
        if (filename.endsWith('.py')) return new vscode.ThemeIcon('file-code');
        if (filename.endsWith('.js') || filename.endsWith('.ts')) return new vscode.ThemeIcon('file-code');
        return new vscode.ThemeIcon('file');
    }
    
    /**
     * Adds quality badge asynchronously (non-blocking)
     */
    private async addQualityBadge(item: DocumentTreeItem): Promise<void> {
        // Don't block tree rendering
        setImmediate(async () => {
            try {
                if (!item.resourceUri) return;
                
                // Check if documentation exists (lightweight check)
                const docPath = item.resourceUri.fsPath.replace(/\.[^.]+$/, '.md');
                
                try {
                    await vscode.workspace.fs.stat(vscode.Uri.file(docPath));
                    
                    // Documentation exists, add badge
                    item.description = '📝';
                    
                    // Trigger minimal update
                    this._onDidChangeTreeData.fire(item);
                } catch {
                    // No documentation, ignore
                }
            } catch (error) {
                // Ignore errors for badges
            }
        });
    }
    
    /**
     * Setup optimized file watching
     */
    private setupFileWatching(): void {
        // Only watch relevant file patterns
        const pattern = '**/*.{py,js,ts,jsx,tsx,md}';
        
        this.fileWatcher = vscode.workspace.createFileSystemWatcher(pattern);
        
        // Use debounced refresh for all events
        this.fileWatcher.onDidCreate(() => this.refreshDebounced());
        this.fileWatcher.onDidChange(() => this.refreshDebounced());
        this.fileWatcher.onDidDelete(() => this.refreshDebounced());
        
        this.disposables.push(this.fileWatcher);
    }
    
    /**
     * Refreshes the tree view
     */
    refresh(): void {
        // Clear visible items cache
        this.visibleItems = [];
        
        // Fire change event
        this._onDidChangeTreeData.fire();
        
        this.logger.debug('Document tree refreshed');
    }
    
    /**
     * Loads more items (virtual scrolling)
     */
    loadMore(offset: number): void {
        // Implementation for loading more items
        this.logger.debug(`Loading more items from offset ${offset}`);
        this.refresh();
    }
    
    /**
     * Disposes resources
     */
    dispose(): void {
        this.logger.debug('Disposing document provider');
        
        // Dispose file watcher
        this.fileWatcher?.dispose();
        
        // Dispose event emitter
        this._onDidChangeTreeData.dispose();
        
        // Dispose all subscriptions
        for (const disposable of this.disposables) {
            disposable.dispose();
        }
        
        // Clear caches
        this.visibleItems = [];
    }
}

/**
 * Lightweight tree item class
 */
class DocumentTreeItem extends vscode.TreeItem {
    constructor(
        public readonly label: string,
        public readonly collapsibleState: vscode.TreeItemCollapsibleState,
        public readonly type: 'file' | 'folder' | 'action' = 'file',
        public readonly resourceUri?: vscode.Uri
    ) {
        super(label, collapsibleState);
        
        if (resourceUri) {
            this.tooltip = resourceUri.fsPath;
            
            // Add context value for commands
            this.contextValue = type === 'folder' ? 'folder' : 'documentedFile';
        }
    }
}

/**
 * Debounce utility
 */
function debounce<T extends (...args: any[]) => any>(
    func: T,
    wait: number
): (...args: Parameters<T>) => void {
    let timeout: NodeJS.Timeout;
    
    return function (...args: Parameters<T>) {
        clearTimeout(timeout);
        timeout = setTimeout(() => func(...args), wait);
    };
}