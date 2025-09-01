/**
 * Document Provider for DevDocAI VS Code Extension
 * 
 * Provides tree view data for documents in the workspace
 * showing documentation status and quality metrics.
 */

import * as vscode from 'vscode';
import * as path from 'path';
import * as fs from 'fs';
import { CLIService } from '../services/CLIService';
import { Logger } from '../utils/Logger';

export class DocumentProvider implements vscode.TreeDataProvider<DocumentItem> {
    private _onDidChangeTreeData: vscode.EventEmitter<DocumentItem | undefined | null | void> = 
        new vscode.EventEmitter<DocumentItem | undefined | null | void>();
    readonly onDidChangeTreeData: vscode.Event<DocumentItem | undefined | null | void> = 
        this._onDidChangeTreeData.event;
    
    private documents: Map<string, DocumentInfo> = new Map();
    private watcher: vscode.FileSystemWatcher | null = null;
    
    constructor(
        private cliService: CLIService,
        private logger: Logger
    ) {
        this.initializeWatcher();
    }
    
    /**
     * Refreshes the tree view
     */
    public refresh(): void {
        this.documents.clear();
        this._onDidChangeTreeData.fire();
    }
    
    /**
     * Gets tree item for display
     */
    public getTreeItem(element: DocumentItem): vscode.TreeItem {
        return element;
    }
    
    /**
     * Gets children for a tree item
     */
    public async getChildren(element?: DocumentItem): Promise<DocumentItem[]> {
        if (!vscode.workspace.workspaceFolders) {
            return [];
        }
        
        if (!element) {
            // Root level - show categories
            return this.getCategories();
        }
        
        if (element.contextValue === 'category') {
            // Show documents in category
            return this.getDocumentsInCategory(element.category!);
        }
        
        if (element.contextValue === 'document') {
            // Show document details
            return this.getDocumentDetails(element.resourceUri!);
        }
        
        return [];
    }
    
    /**
     * Gets document categories
     */
    private async getCategories(): Promise<DocumentItem[]> {
        const categories: DocumentItem[] = [];
        
        // Scan workspace for documents
        await this.scanWorkspace();
        
        // Group documents by status
        const documented = Array.from(this.documents.values())
            .filter(doc => doc.hasDocumentation).length;
        
        const undocumented = Array.from(this.documents.values())
            .filter(doc => !doc.hasDocumentation).length;
        
        const needsUpdate = Array.from(this.documents.values())
            .filter(doc => doc.needsUpdate).length;
        
        // Create category items
        if (documented > 0) {
            categories.push(new DocumentItem(
                `Documented (${documented})`,
                vscode.TreeItemCollapsibleState.Collapsed,
                'category',
                undefined,
                'documented'
            ));
        }
        
        if (needsUpdate > 0) {
            categories.push(new DocumentItem(
                `Needs Update (${needsUpdate})`,
                vscode.TreeItemCollapsibleState.Collapsed,
                'category',
                undefined,
                'needs-update'
            ));
        }
        
        if (undocumented > 0) {
            categories.push(new DocumentItem(
                `Undocumented (${undocumented})`,
                vscode.TreeItemCollapsibleState.Collapsed,
                'category',
                undefined,
                'undocumented'
            ));
        }
        
        return categories;
    }
    
    /**
     * Gets documents in a specific category
     */
    private async getDocumentsInCategory(category: string): Promise<DocumentItem[]> {
        const items: DocumentItem[] = [];
        
        for (const [filePath, info] of this.documents) {
            let includeInCategory = false;
            
            switch (category) {
                case 'documented':
                    includeInCategory = info.hasDocumentation && !info.needsUpdate;
                    break;
                
                case 'needs-update':
                    includeInCategory = info.needsUpdate;
                    break;
                
                case 'undocumented':
                    includeInCategory = !info.hasDocumentation;
                    break;
            }
            
            if (includeInCategory) {
                const uri = vscode.Uri.file(filePath);
                const relativePath = vscode.workspace.asRelativePath(uri);
                const fileName = path.basename(filePath);
                
                const item = new DocumentItem(
                    fileName,
                    vscode.TreeItemCollapsibleState.Collapsed,
                    'document',
                    uri
                );
                
                // Set description
                item.description = relativePath;
                
                // Set tooltip
                item.tooltip = this.buildTooltip(info);
                
                // Set icon based on quality
                item.iconPath = this.getIconForQuality(info.quality);
                
                // Add context menu
                item.contextValue = 'document';
                
                // Add command to open file
                item.command = {
                    command: 'vscode.open',
                    title: 'Open',
                    arguments: [uri]
                };
                
                items.push(item);
            }
        }
        
        return items;
    }
    
    /**
     * Gets document details
     */
    private async getDocumentDetails(uri: vscode.Uri): Promise<DocumentItem[]> {
        const info = this.documents.get(uri.fsPath);
        if (!info) {
            return [];
        }
        
        const details: DocumentItem[] = [];
        
        // Quality score
        details.push(new DocumentItem(
            `Quality: ${info.quality}%`,
            vscode.TreeItemCollapsibleState.None,
            'detail'
        ));
        
        // Coverage
        details.push(new DocumentItem(
            `Coverage: ${info.coverage}%`,
            vscode.TreeItemCollapsibleState.None,
            'detail'
        ));
        
        // Language
        details.push(new DocumentItem(
            `Language: ${info.language}`,
            vscode.TreeItemCollapsibleState.None,
            'detail'
        ));
        
        // Lines
        details.push(new DocumentItem(
            `Lines: ${info.lines}`,
            vscode.TreeItemCollapsibleState.None,
            'detail'
        ));
        
        // Last updated
        if (info.lastUpdated) {
            details.push(new DocumentItem(
                `Updated: ${this.formatDate(info.lastUpdated)}`,
                vscode.TreeItemCollapsibleState.None,
                'detail'
            ));
        }
        
        return details;
    }
    
    /**
     * Scans workspace for documents
     */
    private async scanWorkspace(): Promise<void> {
        if (!vscode.workspace.workspaceFolders) {
            return;
        }
        
        const workspaceRoot = vscode.workspace.workspaceFolders[0].uri.fsPath;
        
        // Find all code files
        const pattern = '**/*.{py,ts,tsx,js,jsx,java,c,cpp,cs,go,rs}';
        const files = await vscode.workspace.findFiles(pattern, '**/node_modules/**');
        
        for (const file of files) {
            await this.analyzeFile(file);
        }
    }
    
    /**
     * Analyzes a single file
     */
    private async analyzeFile(uri: vscode.Uri): Promise<void> {
        try {
            const document = await vscode.workspace.openTextDocument(uri);
            const text = document.getText();
            
            // Check for documentation
            const hasDocumentation = this.checkForDocumentation(text, document.languageId);
            
            // Get quality score if documented
            let quality = 0;
            let coverage = 0;
            
            if (hasDocumentation) {
                // Check for corresponding .md file
                const mdPath = uri.fsPath.replace(/\.[^.]+$/, '.md');
                if (fs.existsSync(mdPath)) {
                    const result = await this.cliService.analyzeQuality(mdPath);
                    quality = result.score;
                    coverage = this.calculateCoverage(text, document.languageId);
                }
            }
            
            // Store document info
            this.documents.set(uri.fsPath, {
                uri: uri,
                hasDocumentation: hasDocumentation,
                quality: quality,
                coverage: coverage,
                needsUpdate: hasDocumentation && quality < 70,
                language: document.languageId,
                lines: document.lineCount,
                lastUpdated: hasDocumentation ? new Date() : undefined
            });
            
        } catch (error) {
            this.logger.error(`Failed to analyze file ${uri.fsPath}`, error);
        }
    }
    
    /**
     * Checks if code has documentation
     */
    private checkForDocumentation(text: string, languageId: string): boolean {
        const patterns: { [key: string]: RegExp } = {
            python: /"""|'''/,
            typescript: /\/\*\*|\*\s+@/,
            javascript: /\/\*\*|\*\s+@/,
            java: /\/\*\*|\*\s+@/,
            c: /\/\*\*|\*\s+@/,
            cpp: /\/\*\*|\*\s+@/,
            csharp: /\/\/\/ <summary>/,
            go: /\/\//,
            rust: /\/\/\/|\/\*!/
        };
        
        const pattern = patterns[languageId];
        return pattern ? pattern.test(text) : false;
    }
    
    /**
     * Calculates documentation coverage
     */
    private calculateCoverage(text: string, languageId: string): number {
        // Simplified coverage calculation
        // Real implementation would parse the AST
        
        const functionPatterns: { [key: string]: RegExp } = {
            python: /def\s+\w+/g,
            typescript: /function\s+\w+|(?:public|private|protected)?\s+\w+\s*\(/g,
            javascript: /function\s+\w+|const\s+\w+\s*=\s*(?:\(|async)/g,
            java: /(?:public|private|protected)\s+\w+\s+\w+\s*\(/g
        };
        
        const docPatterns: { [key: string]: RegExp } = {
            python: /def\s+\w+.*?\n\s*"""/g,
            typescript: /\/\*\*[\s\S]*?\*\/\s*\n\s*(?:function|class|(?:public|private|protected))/g,
            javascript: /\/\*\*[\s\S]*?\*\/\s*\n\s*(?:function|class|const)/g,
            java: /\/\*\*[\s\S]*?\*\/\s*\n\s*(?:public|private|protected)/g
        };
        
        const functionPattern = functionPatterns[languageId];
        const docPattern = docPatterns[languageId];
        
        if (!functionPattern || !docPattern) {
            return 0;
        }
        
        const functions = text.match(functionPattern) || [];
        const documented = text.match(docPattern) || [];
        
        if (functions.length === 0) {
            return 100;
        }
        
        return Math.round((documented.length / functions.length) * 100);
    }
    
    /**
     * Gets icon for quality score
     */
    private getIconForQuality(quality: number): vscode.ThemeIcon {
        if (quality >= 80) {
            return new vscode.ThemeIcon('pass', new vscode.ThemeColor('testing.iconPassed'));
        } else if (quality >= 60) {
            return new vscode.ThemeIcon('warning', new vscode.ThemeColor('list.warningForeground'));
        } else {
            return new vscode.ThemeIcon('error', new vscode.ThemeColor('testing.iconFailed'));
        }
    }
    
    /**
     * Builds tooltip for document
     */
    private buildTooltip(info: DocumentInfo): string {
        const lines = [];
        
        if (info.hasDocumentation) {
            lines.push(`✅ Documented`);
            lines.push(`Quality: ${info.quality}%`);
            lines.push(`Coverage: ${info.coverage}%`);
        } else {
            lines.push(`❌ No documentation`);
        }
        
        lines.push(`Language: ${info.language}`);
        lines.push(`Lines: ${info.lines}`);
        
        if (info.lastUpdated) {
            lines.push(`Updated: ${this.formatDate(info.lastUpdated)}`);
        }
        
        if (info.needsUpdate) {
            lines.push('');
            lines.push('⚠️ Documentation needs update');
        }
        
        return lines.join('\n');
    }
    
    /**
     * Formats date for display
     */
    private formatDate(date: Date): string {
        const now = new Date();
        const diff = now.getTime() - date.getTime();
        const hours = Math.floor(diff / (1000 * 60 * 60));
        
        if (hours < 1) {
            return 'Just now';
        } else if (hours < 24) {
            return `${hours} hour${hours > 1 ? 's' : ''} ago`;
        } else {
            const days = Math.floor(hours / 24);
            return `${days} day${days > 1 ? 's' : ''} ago`;
        }
    }
    
    /**
     * Initializes file system watcher
     */
    private initializeWatcher(): void {
        if (!vscode.workspace.workspaceFolders) {
            return;
        }
        
        // Watch for file changes
        this.watcher = vscode.workspace.createFileSystemWatcher('**/*.{py,ts,tsx,js,jsx,java,c,cpp,cs,go,rs,md}');
        
        this.watcher.onDidCreate((uri) => {
            this.analyzeFile(uri);
            this._onDidChangeTreeData.fire();
        });
        
        this.watcher.onDidChange((uri) => {
            this.analyzeFile(uri);
            this._onDidChangeTreeData.fire();
        });
        
        this.watcher.onDidDelete((uri) => {
            this.documents.delete(uri.fsPath);
            this._onDidChangeTreeData.fire();
        });
    }
    
    /**
     * Disposes the provider
     */
    public dispose(): void {
        if (this.watcher) {
            this.watcher.dispose();
        }
    }
}

/**
 * Tree item for document view
 */
export class DocumentItem extends vscode.TreeItem {
    constructor(
        public readonly label: string,
        public readonly collapsibleState: vscode.TreeItemCollapsibleState,
        public readonly contextValue: string,
        public readonly resourceUri?: vscode.Uri,
        public readonly category?: string
    ) {
        super(label, collapsibleState);
    }
}

/**
 * Document information
 */
interface DocumentInfo {
    uri: vscode.Uri;
    hasDocumentation: boolean;
    quality: number;
    coverage: number;
    needsUpdate: boolean;
    language: string;
    lines: number;
    lastUpdated?: Date;
}