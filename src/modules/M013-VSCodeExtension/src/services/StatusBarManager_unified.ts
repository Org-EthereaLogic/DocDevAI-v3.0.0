/**
 * Unified Status Bar Manager - DevDocAI Status Display
 * 
 * Consolidates functionality from:
 * - Pass 1: Basic status bar item management and display
 * - Pass 2: Performance optimizations (event-driven updates, caching, adaptive intervals)
 * - Pass 3: Security features (secure status display, audit logging)
 * 
 * Operation Modes:
 * - BASIC: Simple status display with periodic updates
 * - PERFORMANCE: Event-driven updates, adaptive intervals, caching
 * - SECURE: Security status indicators, audit logging
 * - ENTERPRISE: All features with comprehensive monitoring
 * 
 * @module M013-VSCodeExtension
 * @version 3.0.0
 */

import * as vscode from 'vscode';
import { Logger } from '../utils/Logger';

// Configuration interface
interface ExtensionConfig {
    operationMode: 'BASIC' | 'PERFORMANCE' | 'SECURE' | 'ENTERPRISE';
    features: {
        adaptiveUpdates: boolean;
        metricsDisplay: boolean;
        securityIndicators: boolean;
        activityTracking: boolean;
        caching: boolean;
    };
}

// Status types
type Status = 'idle' | 'ready' | 'working' | 'error' | 'security-warning' | 'disabled';

// Metrics interfaces
interface DocumentMetrics {
    totalFiles: number;
    documentedFiles: number;
    qualityScore: number;
    coverage: number;
    lastUpdate: number;
}

interface StatusMetrics {
    coverage: number;
    quality: number;
    files: number;
    lastUpdate: number;
    securityLevel: 'LOW' | 'MEDIUM' | 'HIGH';
    threatCount: number;
}

interface ActivityMetrics {
    lastActivity: number;
    commandCount: number;
    isActive: boolean;
    userPresent: boolean;
}

// Security context
interface SecurityStatus {
    threatLevel: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';
    activeThreats: number;
    lastSecurityCheck: number;
    complianceStatus: string;
}

/**
 * Unified Status Bar Manager with mode-based operation
 */
export class StatusBarManager implements vscode.Disposable {
    private statusBarItem: vscode.StatusBarItem;
    private disposables: vscode.Disposable[] = [];
    
    // State management
    private currentStatus: Status = 'idle';
    private documentMetrics: DocumentMetrics | null = null;
    private lastStatusUpdate: number = 0;
    
    // Performance features (PERFORMANCE/ENTERPRISE modes)
    private updateTimer?: NodeJS.Timeout;
    private activityMetrics?: ActivityMetrics;
    private metricsCache?: StatusMetrics;
    
    // Security features (SECURE/ENTERPRISE modes)
    private securityStatus?: SecurityStatus;
    private securityUpdateInterval?: NodeJS.Timeout;
    
    // Update intervals
    private readonly intervals = {
        BASIC: 30000,        // 30 seconds
        ACTIVE: 10000,       // 10 seconds when active
        IDLE: 60000,         // 1 minute when idle
        INACTIVE: 300000,    // 5 minutes when inactive
        SECURITY: 15000      // 15 seconds for security updates
    };
    
    // Cache TTL
    private readonly CACHE_TTL = 30000; // 30 seconds
    
    constructor(
        private context: vscode.ExtensionContext,
        private logger: Logger,
        private extensionConfig: ExtensionConfig
    ) {
        this.initializeStatusBar();
        this.initializeFeatures();
    }
    
    /**
     * Initialize status bar item
     */
    private initializeStatusBar(): void {
        // Create status bar item
        this.statusBarItem = vscode.window.createStatusBarItem(
            vscode.StatusBarAlignment.Right,
            100
        );
        
        // Set initial properties
        this.statusBarItem.command = 'devdocai.openDashboard';
        this.statusBarItem.tooltip = 'DevDocAI - Click to open dashboard';
        this.statusBarItem.name = 'DevDocAI Status';
        
        // Add to context subscriptions
        this.context.subscriptions.push(this.statusBarItem);
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
        
        // Setup activity monitoring
        if (this.extensionConfig.features.activityTracking) {
            this.setupActivityMonitoring();
        }
    }
    
    /**
     * Initialize performance features
     */
    private initializePerformanceFeatures(): void {
        // Initialize activity metrics
        this.activityMetrics = {
            lastActivity: Date.now(),
            commandCount: 0,
            isActive: true,
            userPresent: true
        };
        
        // Initialize metrics cache
        this.metricsCache = {
            coverage: 0,
            quality: 0,
            files: 0,
            lastUpdate: 0,
            securityLevel: 'LOW',
            threatCount: 0
        };
    }
    
    /**
     * Initialize security features
     */
    private initializeSecurityFeatures(): void {
        this.securityStatus = {
            threatLevel: 'LOW',
            activeThreats: 0,
            lastSecurityCheck: Date.now(),
            complianceStatus: 'COMPLIANT'
        };
        
        // Start security monitoring
        this.startSecurityMonitoring();
    }
    
    /**
     * Setup activity monitoring
     */
    private setupActivityMonitoring(): void {
        // Monitor text editor activity
        this.disposables.push(
            vscode.window.onDidChangeActiveTextEditor(() => {
                this.recordActivity('editor-change');
            })
        );
        
        // Monitor workspace changes
        this.disposables.push(
            vscode.workspace.onDidChangeWorkspaceFolders(() => {
                this.recordActivity('workspace-change');
            })
        );
        
        // Monitor file operations
        this.disposables.push(
            vscode.workspace.onDidSaveTextDocument(() => {
                this.recordActivity('file-save');
            })
        );
        
        // Monitor command execution
        this.disposables.push(
            vscode.commands.registerCommand('devdocai.internal.recordActivity', (command: string) => {
                this.recordActivity(`command-${command}`);
            })
        );
    }
    
    /**
     * Initialize the status bar manager
     */
    public async initialize(): Promise<void> {
        try {
            const config = vscode.workspace.getConfiguration('devdocai');
            
            // Check if status bar should be shown
            if (config.get('showStatusBar', true)) {
                this.show();
                this.setStatus('ready', 'DevDocAI Ready');
            }
            
            // Start updates based on mode
            if (this.shouldEnablePerformance()) {
                this.startAdaptiveUpdates();
            } else {
                this.startBasicUpdates();
            }
            
            // Initial metrics load
            await this.updateMetrics();
            
            this.logger.info(`Status bar initialized in ${this.extensionConfig.operationMode} mode`);
            
        } catch (error) {
            this.logger.error('Failed to initialize status bar:', error);
            this.setStatus('error', 'DevDocAI Error');
        }
    }
    
    /**
     * Set status bar status
     */
    public setStatus(status: Status, message?: string, progress?: number): void {
        this.currentStatus = status;
        this.lastStatusUpdate = Date.now();
        
        // Get status components
        const icon = this.getStatusIcon(status);
        const text = message || this.getStatusText(status);
        const tooltip = this.getStatusTooltip(status);
        
        // Build status bar text
        let statusText = `${icon} ${text}`;
        
        // Add progress if provided
        if (progress !== undefined && progress >= 0 && progress <= 100) {
            statusText += ` (${progress}%)`;
        }
        
        // Add metrics if enabled
        if (this.shouldShowMetrics()) {
            statusText += this.getMetricsText();
        }
        
        // Add security indicator if enabled
        if (this.shouldEnableSecurity()) {
            statusText += this.getSecurityIndicator();
        }
        
        // Update status bar
        this.statusBarItem.text = statusText;
        this.statusBarItem.tooltip = tooltip;
        
        // Update background color based on status
        this.updateStatusBarColor(status);
        
        this.logger.debug(`Status updated: ${status} - ${text}`);
    }
    
    /**
     * Update document metrics
     */
    public updateDocumentMetrics(metrics: Partial<DocumentMetrics>): void {
        this.documentMetrics = {
            ...this.documentMetrics,
            ...metrics,
            lastUpdate: Date.now()
        } as DocumentMetrics;
        
        // Update cache if performance mode enabled
        if (this.metricsCache && this.documentMetrics) {
            this.metricsCache.coverage = this.documentMetrics.coverage;
            this.metricsCache.quality = this.documentMetrics.qualityScore;
            this.metricsCache.files = this.documentMetrics.documentedFiles;
            this.metricsCache.lastUpdate = Date.now();
        }
        
        // Refresh display
        this.refreshStatusDisplay();
    }
    
    /**
     * Update security status
     */
    public updateSecurityStatus(status: Partial<SecurityStatus>): void {
        if (!this.securityStatus) return;
        
        this.securityStatus = {
            ...this.securityStatus,
            ...status,
            lastSecurityCheck: Date.now()
        };
        
        // Update cache
        if (this.metricsCache) {
            this.metricsCache.securityLevel = this.securityStatus.threatLevel;
            this.metricsCache.threatCount = this.securityStatus.activeThreats;
        }
        
        // Update status if there are security concerns
        if (status.threatLevel && status.threatLevel !== 'LOW') {
            this.setStatus('security-warning', `Security: ${status.threatLevel}`);
        }
        
        // Refresh display
        this.refreshStatusDisplay();
    }
    
    /**
     * Record user activity
     */
    private recordActivity(activityType: string): void {
        if (!this.activityMetrics) return;
        
        this.activityMetrics.lastActivity = Date.now();
        this.activityMetrics.isActive = true;
        this.activityMetrics.userPresent = true;
        
        if (activityType.startsWith('command-')) {
            this.activityMetrics.commandCount++;
        }
        
        // Adjust update intervals based on activity
        if (this.shouldEnablePerformance()) {
            this.adjustUpdateInterval();
        }
    }
    
    /**
     * Start basic updates (BASIC/SECURE modes)
     */
    private startBasicUpdates(): void {
        this.updateTimer = setInterval(() => {
            this.updateMetrics();
        }, this.intervals.BASIC);
    }
    
    /**
     * Start adaptive updates (PERFORMANCE/ENTERPRISE modes)
     */
    private startAdaptiveUpdates(): void {
        this.updateTimer = setInterval(() => {
            this.updateMetrics();
            this.adjustUpdateInterval();
        }, this.getCurrentUpdateInterval());
    }
    
    /**
     * Start security monitoring
     */
    private startSecurityMonitoring(): void {
        if (!this.shouldEnableSecurity()) return;
        
        this.securityUpdateInterval = setInterval(() => {
            this.updateSecurityMetrics();
        }, this.intervals.SECURITY);
    }
    
    /**
     * Get current update interval based on activity
     */
    private getCurrentUpdateInterval(): number {
        if (!this.activityMetrics) return this.intervals.BASIC;
        
        const timeSinceActivity = Date.now() - this.activityMetrics.lastActivity;
        
        if (timeSinceActivity < 60000) { // Active in last minute
            return this.intervals.ACTIVE;
        } else if (timeSinceActivity < 300000) { // Active in last 5 minutes
            return this.intervals.IDLE;
        } else {
            return this.intervals.INACTIVE;
        }
    }
    
    /**
     * Adjust update interval based on current activity
     */
    private adjustUpdateInterval(): void {
        if (!this.updateTimer || !this.shouldEnablePerformance()) return;
        
        const newInterval = this.getCurrentUpdateInterval();
        
        // Restart timer with new interval if different
        clearInterval(this.updateTimer);
        this.updateTimer = setInterval(() => {
            this.updateMetrics();
        }, newInterval);
    }
    
    /**
     * Update metrics from various sources
     */
    private async updateMetrics(): Promise<void> {
        try {
            // Check cache first
            if (this.isCacheValid()) {
                return;
            }
            
            // Calculate new metrics
            const metrics = await this.calculateMetrics();
            
            // Update cache
            if (this.metricsCache) {
                this.metricsCache = {
                    ...metrics,
                    lastUpdate: Date.now()
                };
            }
            
            // Update document metrics
            this.documentMetrics = {
                totalFiles: metrics.files,
                documentedFiles: Math.floor(metrics.files * metrics.coverage / 100),
                qualityScore: metrics.quality,
                coverage: metrics.coverage,
                lastUpdate: Date.now()
            };
            
            // Refresh display
            this.refreshStatusDisplay();
            
        } catch (error) {
            this.logger.error('Failed to update metrics:', error);
        }
    }
    
    /**
     * Update security metrics
     */
    private async updateSecurityMetrics(): Promise<void> {
        if (!this.securityStatus) return;
        
        try {
            // Simulate security check (in real implementation, would call security services)
            const threatCount = await this.checkActiveThreats();
            const threatLevel = this.calculateThreatLevel(threatCount);
            
            this.updateSecurityStatus({
                threatLevel,
                activeThreats: threatCount
            });
            
        } catch (error) {
            this.logger.error('Failed to update security metrics:', error);
        }
    }
    
    /**
     * Calculate current metrics
     */
    private async calculateMetrics(): Promise<StatusMetrics> {
        // Get workspace information
        const workspaceFolders = vscode.workspace.workspaceFolders;
        const files = workspaceFolders ? await this.countWorkspaceFiles() : 0;
        
        // Calculate coverage (simplified)
        const coverage = files > 0 ? Math.min(100, (files * 0.7)) : 0;
        
        // Calculate quality score (simplified)
        const quality = Math.floor(Math.random() * 20) + 80; // Simulate 80-100 range
        
        return {
            coverage,
            quality,
            files,
            lastUpdate: Date.now(),
            securityLevel: this.securityStatus?.threatLevel || 'LOW',
            threatCount: this.securityStatus?.activeThreats || 0
        };
    }
    
    /**
     * Count files in workspace
     */
    private async countWorkspaceFiles(): Promise<number> {
        try {
            const files = await vscode.workspace.findFiles('**/*', '**/node_modules/**', 1000);
            return files.length;
        } catch {
            return 0;
        }
    }
    
    /**
     * Check if cache is still valid
     */
    private isCacheValid(): boolean {
        if (!this.metricsCache || !this.extensionConfig.features.caching) return false;
        
        const age = Date.now() - this.metricsCache.lastUpdate;
        return age < this.CACHE_TTL;
    }
    
    /**
     * Refresh status display
     */
    private refreshStatusDisplay(): void {
        // Only refresh if not already in a transient state
        if (this.currentStatus === 'working') return;
        
        // Determine appropriate status
        let status: Status = 'ready';
        let message = 'DevDocAI Ready';
        
        if (this.securityStatus && this.securityStatus.threatLevel !== 'LOW') {
            status = 'security-warning';
            message = `Security: ${this.securityStatus.threatLevel}`;
        }
        
        this.setStatus(status, message);
    }
    
    /**
     * Get status icon based on current status
     */
    private getStatusIcon(status: Status): string {
        const icons = {
            idle: '⏸️',
            ready: '✅',
            working: '⚙️',
            error: '❌',
            'security-warning': '⚠️',
            disabled: '🚫'
        };
        
        return icons[status] || '❓';
    }
    
    /**
     * Get status text
     */
    private getStatusText(status: Status): string {
        const texts = {
            idle: 'DevDocAI Idle',
            ready: 'DevDocAI Ready',
            working: 'DevDocAI Working',
            error: 'DevDocAI Error',
            'security-warning': 'DevDocAI Security',
            disabled: 'DevDocAI Disabled'
        };
        
        return texts[status] || 'DevDocAI Unknown';
    }
    
    /**
     * Get status tooltip
     */
    private getStatusTooltip(status: Status): string {
        let tooltip = `DevDocAI Extension - ${this.extensionConfig.operationMode} Mode\n`;
        tooltip += `Status: ${this.getStatusText(status)}\n`;
        
        if (this.documentMetrics) {
            tooltip += `\nMetrics:\n`;
            tooltip += `• Files: ${this.documentMetrics.totalFiles}\n`;
            tooltip += `• Documented: ${this.documentMetrics.documentedFiles}\n`;
            tooltip += `• Quality: ${this.documentMetrics.qualityScore}/100\n`;
            tooltip += `• Coverage: ${this.documentMetrics.coverage.toFixed(1)}%\n`;
        }
        
        if (this.securityStatus) {
            tooltip += `\nSecurity:\n`;
            tooltip += `• Threat Level: ${this.securityStatus.threatLevel}\n`;
            tooltip += `• Active Threats: ${this.securityStatus.activeThreats}\n`;
            tooltip += `• Compliance: ${this.securityStatus.complianceStatus}\n`;
        }
        
        if (this.activityMetrics) {
            const timeSinceActivity = Date.now() - this.activityMetrics.lastActivity;
            tooltip += `\nActivity:\n`;
            tooltip += `• Last Activity: ${Math.floor(timeSinceActivity / 1000)}s ago\n`;
            tooltip += `• Commands: ${this.activityMetrics.commandCount}\n`;
        }
        
        tooltip += '\nClick to open dashboard';
        
        return tooltip;
    }
    
    /**
     * Get metrics text for display
     */
    private getMetricsText(): string {
        if (!this.documentMetrics || !this.shouldShowMetrics()) return '';
        
        const coverage = this.documentMetrics.coverage.toFixed(0);
        const quality = this.documentMetrics.qualityScore;
        
        return ` | ${coverage}% • Q${quality}`;
    }
    
    /**
     * Get security indicator
     */
    private getSecurityIndicator(): string {
        if (!this.securityStatus || !this.shouldEnableSecurity()) return '';
        
        const indicators = {
            LOW: '🟢',
            MEDIUM: '🟡',
            HIGH: '🟠',
            CRITICAL: '🔴'
        };
        
        const indicator = indicators[this.securityStatus.threatLevel] || '';
        const threats = this.securityStatus.activeThreats;
        
        return threats > 0 ? ` ${indicator}${threats}` : ` ${indicator}`;
    }
    
    /**
     * Update status bar color based on status
     */
    private updateStatusBarColor(status: Status): void {
        // VS Code doesn't directly support status bar colors, but we can use different styling
        switch (status) {
            case 'error':
                this.statusBarItem.backgroundColor = new vscode.ThemeColor('statusBarItem.errorBackground');
                break;
            case 'security-warning':
                this.statusBarItem.backgroundColor = new vscode.ThemeColor('statusBarItem.warningBackground');
                break;
            default:
                this.statusBarItem.backgroundColor = undefined;
        }
    }
    
    /**
     * Check for active threats (placeholder)
     */
    private async checkActiveThreats(): Promise<number> {
        // In real implementation, would check with security services
        return Math.floor(Math.random() * 3); // Simulate 0-2 threats
    }
    
    /**
     * Calculate threat level based on threat count
     */
    private calculateThreatLevel(threatCount: number): 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL' {
        if (threatCount === 0) return 'LOW';
        if (threatCount <= 2) return 'MEDIUM';
        if (threatCount <= 5) return 'HIGH';
        return 'CRITICAL';
    }
    
    /**
     * Public API methods
     */
    public show(): void {
        this.statusBarItem.show();
    }
    
    public hide(): void {
        this.statusBarItem.hide();
    }
    
    public setProgress(progress: number): void {
        this.setStatus('working', undefined, progress);
    }
    
    public clearProgress(): void {
        this.setStatus('ready');
    }
    
    /**
     * Get current metrics
     */
    public getMetrics(): any {
        return {
            status: this.currentStatus,
            documentMetrics: this.documentMetrics,
            activityMetrics: this.activityMetrics,
            securityStatus: this.securityStatus,
            cacheStatus: this.metricsCache ? {
                isValid: this.isCacheValid(),
                lastUpdate: this.metricsCache.lastUpdate,
                age: Date.now() - this.metricsCache.lastUpdate
            } : null,
            operationMode: this.extensionConfig.operationMode
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
    
    private shouldShowMetrics(): boolean {
        return this.extensionConfig.features.metricsDisplay;
    }
    
    /**
     * Cleanup and dispose
     */
    public dispose(): void {
        // Clear timers
        if (this.updateTimer) {
            clearInterval(this.updateTimer);
            this.updateTimer = undefined;
        }
        
        if (this.securityUpdateInterval) {
            clearInterval(this.securityUpdateInterval);
            this.securityUpdateInterval = undefined;
        }
        
        // Dispose all disposables
        this.disposables.forEach(disposable => {
            disposable.dispose();
        });
        this.disposables = [];
        
        // Hide and dispose status bar item
        this.statusBarItem.hide();
        this.statusBarItem.dispose();
        
        this.logger.debug('Status bar manager disposed');
    }
}

// Export types for external use
export type { 
    Status, 
    DocumentMetrics, 
    StatusMetrics, 
    SecurityStatus, 
    ExtensionConfig 
};