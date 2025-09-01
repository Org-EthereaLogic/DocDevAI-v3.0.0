/**
 * Optimized Status Bar Manager - Smart Updates
 * 
 * Performance optimizations:
 * - Event-driven updates instead of polling
 * - Adaptive update intervals based on activity
 * - Cached status calculations
 * - Minimal DOM updates
 * - Dispose pattern for cleanup
 * 
 * @module M013-VSCodeExtension
 */

import * as vscode from 'vscode';
import { CLIService } from './CLIService';
import { Logger } from '../utils/Logger';

interface StatusMetrics {
    coverage: number;
    quality: number;
    files: number;
    lastUpdate: number;
}

export class OptimizedStatusBarManager implements vscode.Disposable {
    private statusBarItem: vscode.StatusBarItem;
    private disposables: vscode.Disposable[] = [];
    
    // Smart update management
    private updateTimer: NodeJS.Timeout | undefined;
    private isActive: boolean = false;
    private lastActivity: number = Date.now();
    
    // Update intervals based on activity
    private readonly ACTIVE_INTERVAL = 10000;    // 10 seconds when active
    private readonly IDLE_INTERVAL = 60000;      // 1 minute when idle
    private readonly INACTIVE_INTERVAL = 300000; // 5 minutes when inactive
    
    // Cache for metrics
    private metricsCache: StatusMetrics = {
        coverage: 0,
        quality: 0,
        files: 0,
        lastUpdate: 0
    };
    
    // Cache TTL (30 seconds)
    private readonly CACHE_TTL = 30000;
    
    constructor(
        private context: vscode.ExtensionContext,
        private cliService: CLIService,
        private logger: Logger
    ) {
        // Create status bar item
        this.statusBarItem = vscode.window.createStatusBarItem(
            vscode.StatusBarAlignment.Left,
            100
        );
        
        // Initial setup
        this.statusBarItem.command = 'devdocai.openDashboard';
        this.statusBarItem.show();
        
        context.subscriptions.push(this.statusBarItem);
    }
    
    /**
     * Initializes the status bar with smart updates
     */
    public async initialize(): Promise<void> {
        this.logger.debug('🚀 Initializing optimized status bar');
        
        // Set initial status
        this.setStatus('ready', 'DevDocAI Ready');
        
        // Setup event listeners for activity detection
        this.setupActivityListeners();
        
        // Start adaptive updates
        this.startAdaptiveUpdates();
        
        // Initial metrics load (non-blocking)
        this.updateMetricsAsync();
    }
    
    /**
     * Sets status with icon and text
     */
    public setStatus(status: 'ready' | 'busy' | 'error' | 'warning', text: string): void {
        const icons = {
            ready: '$(check)',
            busy: '$(sync~spin)',
            error: '$(error)',
            warning: '$(warning)'
        };
        
        // Only update if changed
        const newText = `${icons[status]} ${text}`;
        if (this.statusBarItem.text !== newText) {
            this.statusBarItem.text = newText;
        }
    }
    
    /**
     * Updates status for the current document
     */
    public updateForDocument(document: vscode.TextDocument): void {
        // Mark as active
        this.markActive();
        
        // Check if document has documentation (cached check)
        const hasDoc = this.checkDocumentationCached(document);
        
        if (hasDoc) {
            this.setStatus('ready', 'DevDocAI (Documented)');
        } else {
            this.setStatus('warning', 'DevDocAI (No Docs)');
        }
        
        // Update tooltip with metrics
        this.updateTooltip();
    }
    
    /**
     * Setup activity listeners for smart updates
     */
    private setupActivityListeners(): void {
        // Listen for user activity
        this.disposables.push(
            vscode.window.onDidChangeActiveTextEditor(() => {
                this.markActive();
            })
        );
        
        this.disposables.push(
            vscode.workspace.onDidSaveTextDocument(() => {
                this.markActive();
                // Trigger metrics update on save (important event)
                this.updateMetricsAsync();
            })
        );
        
        // Listen for commands (user interactions)
        this.disposables.push(
            vscode.commands.onDidExecuteCommand((command) => {
                if (command.startsWith('devdocai.')) {
                    this.markActive();
                }
            })
        );
        
        // Listen for terminal activity
        this.disposables.push(
            vscode.window.onDidChangeTerminalState(() => {
                this.markActive();
            })
        );
    }
    
    /**
     * Marks the extension as active
     */
    private markActive(): void {
        this.isActive = true;
        this.lastActivity = Date.now();
        
        // Adjust update interval if needed
        this.adjustUpdateInterval();
    }
    
    /**
     * Starts adaptive update timer
     */
    private startAdaptiveUpdates(): void {
        this.scheduleNextUpdate();
    }
    
    /**
     * Schedules the next update based on activity
     */
    private scheduleNextUpdate(): void {
        // Clear existing timer
        if (this.updateTimer) {
            clearTimeout(this.updateTimer);
        }
        
        // Determine interval based on activity
        const interval = this.getUpdateInterval();
        
        this.updateTimer = setTimeout(() => {
            this.updateMetricsAsync();
            this.scheduleNextUpdate(); // Reschedule
        }, interval);
    }
    
    /**
     * Gets update interval based on activity
     */
    private getUpdateInterval(): number {
        const timeSinceActivity = Date.now() - this.lastActivity;
        
        if (timeSinceActivity < 30000) { // Active in last 30 seconds
            return this.ACTIVE_INTERVAL;
        } else if (timeSinceActivity < 300000) { // Active in last 5 minutes
            return this.IDLE_INTERVAL;
        } else { // Inactive
            return this.INACTIVE_INTERVAL;
        }
    }
    
    /**
     * Adjusts update interval when activity changes
     */
    private adjustUpdateInterval(): void {
        // Reschedule with new interval
        this.scheduleNextUpdate();
    }
    
    /**
     * Updates metrics asynchronously (non-blocking)
     */
    private async updateMetricsAsync(): Promise<void> {
        // Check cache first
        if (this.isCacheValid()) {
            this.updateTooltip();
            return;
        }
        
        try {
            // Get metrics in background
            const metrics = await this.getMetricsLightweight();
            
            // Update cache
            this.metricsCache = {
                ...metrics,
                lastUpdate: Date.now()
            };
            
            // Update tooltip
            this.updateTooltip();
            
        } catch (error) {
            this.logger.debug('Failed to update metrics', error);
            // Don't show error to user, just use cached values
        }
    }
    
    /**
     * Gets lightweight metrics (fast)
     */
    private async getMetricsLightweight(): Promise<StatusMetrics> {
        // Quick file count
        const files = await this.countRelevantFiles();
        
        // Quick coverage estimate (based on .md files)
        const coverage = await this.estimateCoverage();
        
        // Use cached quality if available
        const quality = this.metricsCache.quality || 75;
        
        return {
            coverage,
            quality,
            files,
            lastUpdate: Date.now()
        };
    }
    
    /**
     * Counts relevant files quickly
     */
    private async countRelevantFiles(): Promise<number> {
        try {
            const files = await vscode.workspace.findFiles(
                '**/*.{py,js,ts,jsx,tsx}',
                '**/node_modules/**',
                100 // Limit for performance
            );
            return files.length;
        } catch {
            return this.metricsCache.files || 0;
        }
    }
    
    /**
     * Estimates coverage quickly
     */
    private async estimateCoverage(): Promise<number> {
        try {
            const codeFiles = await vscode.workspace.findFiles(
                '**/*.{py,js,ts}',
                '**/node_modules/**',
                50
            );
            
            const docFiles = await vscode.workspace.findFiles(
                '**/*.md',
                '**/node_modules/**',
                50
            );
            
            if (codeFiles.length === 0) return 0;
            
            const coverage = Math.round((docFiles.length / codeFiles.length) * 100);
            return Math.min(coverage, 100);
            
        } catch {
            return this.metricsCache.coverage || 0;
        }
    }
    
    /**
     * Checks if cache is still valid
     */
    private isCacheValid(): boolean {
        return Date.now() - this.metricsCache.lastUpdate < this.CACHE_TTL;
    }
    
    /**
     * Updates tooltip with metrics
     */
    private updateTooltip(): void {
        const tooltip = new vscode.MarkdownString();
        tooltip.appendMarkdown('### DevDocAI Metrics\n\n');
        tooltip.appendMarkdown(`📊 **Coverage**: ${this.metricsCache.coverage}%\n\n`);
        tooltip.appendMarkdown(`✨ **Quality**: ${this.metricsCache.quality}/100\n\n`);
        tooltip.appendMarkdown(`📁 **Files**: ${this.metricsCache.files}\n\n`);
        tooltip.appendMarkdown('*Click to open dashboard*');
        
        this.statusBarItem.tooltip = tooltip;
    }
    
    /**
     * Cached documentation check
     */
    private documentationCache = new Map<string, boolean>();
    
    private checkDocumentationCached(document: vscode.TextDocument): boolean {
        const cacheKey = document.uri.fsPath;
        
        // Check cache
        if (this.documentationCache.has(cacheKey)) {
            return this.documentationCache.get(cacheKey)!;
        }
        
        // Check if .md file exists (async, non-blocking)
        const docPath = document.uri.fsPath.replace(/\.[^.]+$/, '.md');
        
        vscode.workspace.fs.stat(vscode.Uri.file(docPath)).then(
            () => {
                this.documentationCache.set(cacheKey, true);
            },
            () => {
                this.documentationCache.set(cacheKey, false);
            }
        );
        
        // Return false for first check (will update on next check)
        return false;
    }
    
    /**
     * Refreshes the status bar
     */
    public refresh(): void {
        this.markActive();
        this.updateMetricsAsync();
    }
    
    /**
     * Disposes resources
     */
    public async dispose(): Promise<void> {
        this.logger.debug('♻️ Disposing status bar manager');
        
        // Clear timer
        if (this.updateTimer) {
            clearTimeout(this.updateTimer);
        }
        
        // Clear caches
        this.documentationCache.clear();
        
        // Dispose status bar item
        this.statusBarItem.dispose();
        
        // Dispose all subscriptions
        for (const disposable of this.disposables) {
            disposable.dispose();
        }
        
        this.disposables = [];
    }
}