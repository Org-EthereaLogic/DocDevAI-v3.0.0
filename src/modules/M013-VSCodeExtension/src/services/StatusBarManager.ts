/**
 * Status Bar Manager for DevDocAI VS Code Extension
 * 
 * Manages the status bar item that shows DevDocAI status
 * and provides quick access to commands.
 */

import * as vscode from 'vscode';
import { CLIService } from './CLIService';
import { Logger } from '../utils/Logger';

export class StatusBarManager {
    private statusBarItem: vscode.StatusBarItem;
    private currentStatus: Status = 'idle';
    private documentMetrics: DocumentMetrics | null = null;
    private updateTimer: NodeJS.Timer | null = null;
    
    constructor(
        private context: vscode.ExtensionContext,
        private cliService: CLIService,
        private logger: Logger
    ) {
        // Create status bar item
        this.statusBarItem = vscode.window.createStatusBarItem(
            vscode.StatusBarAlignment.Right,
            100
        );
        
        // Set initial properties
        this.statusBarItem.command = 'devdocai.openDashboard';
        this.statusBarItem.tooltip = 'DevDocAI - Click to open dashboard';
        
        // Add to subscriptions
        context.subscriptions.push(this.statusBarItem);
    }
    
    /**
     * Initializes the status bar
     */
    public async initialize(): Promise<void> {
        const config = vscode.workspace.getConfiguration('devdocai');
        
        if (config.get('showStatusBar', true)) {
            this.show();
            this.setStatus('ready', 'DevDocAI Ready');
        }
        
        // Start periodic updates
        this.startPeriodicUpdates();
    }
    
    /**
     * Sets the status bar status
     */
    public setStatus(status: Status, message?: string): void {
        this.currentStatus = status;
        
        const icon = this.getStatusIcon(status);
        const text = message || this.getStatusText(status);
        
        this.statusBarItem.text = `${icon} ${text}`;
        
        // Update colors based on status
        switch (status) {
            case 'error':
                this.statusBarItem.backgroundColor = new vscode.ThemeColor('statusBarItem.errorBackground');
                break;
            
            case 'warning':
                this.statusBarItem.backgroundColor = new vscode.ThemeColor('statusBarItem.warningBackground');
                break;
            
            case 'working':
                this.statusBarItem.backgroundColor = new vscode.ThemeColor('statusBarItem.prominentBackground');
                break;
            
            default:
                this.statusBarItem.backgroundColor = undefined;
        }
    }
    
    /**
     * Updates status bar for a specific document
     */
    public async updateForDocument(document: vscode.TextDocument): Promise<void> {
        if (!this.isSupported(document)) {
            this.setStatus('idle', 'DevDocAI');
            return;
        }
        
        try {
            // Get document metrics
            const metrics = await this.getDocumentMetrics(document);
            this.documentMetrics = metrics;
            
            // Update status bar text
            const qualityIcon = this.getQualityIcon(metrics.quality);
            const coverageIcon = this.getCoverageIcon(metrics.coverage);
            
            this.statusBarItem.text = `$(book) DevDocAI ${qualityIcon} ${metrics.quality}% ${coverageIcon} ${metrics.coverage}%`;
            
            // Update tooltip
            this.statusBarItem.tooltip = this.buildTooltip(metrics);
            
        } catch (error) {
            this.logger.error('Failed to update document status', error);
            this.setStatus('error', 'DevDocAI Error');
        }
    }
    
    /**
     * Shows the status bar item
     */
    public show(): void {
        this.statusBarItem.show();
    }
    
    /**
     * Hides the status bar item
     */
    public hide(): void {
        this.statusBarItem.hide();
    }
    
    /**
     * Refreshes the status bar
     */
    public refresh(): void {
        const editor = vscode.window.activeTextEditor;
        if (editor) {
            this.updateForDocument(editor.document);
        } else {
            this.setStatus('idle', 'DevDocAI');
        }
    }
    
    /**
     * Gets the status icon
     */
    private getStatusIcon(status: Status): string {
        switch (status) {
            case 'ready':
                return '$(check)';
            
            case 'working':
                return '$(sync~spin)';
            
            case 'error':
                return '$(error)';
            
            case 'warning':
                return '$(warning)';
            
            case 'idle':
            default:
                return '$(book)';
        }
    }
    
    /**
     * Gets the status text
     */
    private getStatusText(status: Status): string {
        switch (status) {
            case 'ready':
                return 'DevDocAI Ready';
            
            case 'working':
                return 'DevDocAI Working...';
            
            case 'error':
                return 'DevDocAI Error';
            
            case 'warning':
                return 'DevDocAI Warning';
            
            case 'idle':
            default:
                return 'DevDocAI';
        }
    }
    
    /**
     * Gets quality icon based on score
     */
    private getQualityIcon(quality: number): string {
        if (quality >= 80) {
            return '$(pass)';
        } else if (quality >= 60) {
            return '$(warning)';
        } else {
            return '$(error)';
        }
    }
    
    /**
     * Gets coverage icon based on percentage
     */
    private getCoverageIcon(coverage: number): string {
        if (coverage >= 80) {
            return '$(symbol-class)';
        } else if (coverage >= 60) {
            return '$(symbol-interface)';
        } else {
            return '$(symbol-misc)';
        }
    }
    
    /**
     * Checks if document is supported
     */
    private isSupported(document: vscode.TextDocument): boolean {
        const supportedLanguages = [
            'python', 'typescript', 'javascript', 'java', 
            'c', 'cpp', 'csharp', 'go', 'rust', 'markdown'
        ];
        
        return supportedLanguages.includes(document.languageId);
    }
    
    /**
     * Gets document metrics
     */
    private async getDocumentMetrics(document: vscode.TextDocument): Promise<DocumentMetrics> {
        // Check if it's a markdown file (documentation)
        if (document.languageId === 'markdown') {
            // Analyze documentation quality
            const quality = await this.cliService.analyzeQuality(document.uri.fsPath);
            
            return {
                quality: quality.score,
                coverage: 100, // Documentation files have 100% coverage by definition
                hasDocumentation: true,
                lines: document.lineCount,
                language: document.languageId
            };
        }
        
        // For code files, check documentation coverage
        // This is a simplified version - real implementation would analyze the code
        const text = document.getText();
        const hasDocstrings = this.checkForDocumentation(text, document.languageId);
        
        return {
            quality: hasDocstrings ? 75 : 25,
            coverage: hasDocstrings ? 60 : 20,
            hasDocumentation: hasDocstrings,
            lines: document.lineCount,
            language: document.languageId
        };
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
     * Builds tooltip text
     */
    private buildTooltip(metrics: DocumentMetrics): string {
        const lines = [
            'DevDocAI Documentation Assistant',
            '',
            `Language: ${metrics.language}`,
            `Lines: ${metrics.lines}`,
            `Documentation Quality: ${metrics.quality}%`,
            `Coverage: ${metrics.coverage}%`,
            '',
            'Click to open dashboard',
            'Right-click for more options'
        ];
        
        if (metrics.quality < 70) {
            lines.push('', '⚠️ Documentation needs improvement');
        }
        
        return lines.join('\n');
    }
    
    /**
     * Starts periodic status updates
     */
    private startPeriodicUpdates(): void {
        // Update every 30 seconds
        this.updateTimer = setInterval(() => {
            this.refresh();
        }, 30000);
    }
    
    /**
     * Stops periodic updates
     */
    private stopPeriodicUpdates(): void {
        if (this.updateTimer) {
            clearInterval(this.updateTimer);
            this.updateTimer = null;
        }
    }
    
    /**
     * Disposes the status bar manager
     */
    public async dispose(): Promise<void> {
        this.stopPeriodicUpdates();
        this.statusBarItem.dispose();
    }
}

/**
 * Status types
 */
type Status = 'idle' | 'ready' | 'working' | 'error' | 'warning';

/**
 * Document metrics interface
 */
interface DocumentMetrics {
    quality: number;
    coverage: number;
    hasDocumentation: boolean;
    lines: number;
    language: string;
}