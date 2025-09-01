/**
 * Unified Webview Manager - DevDocAI Panel Management
 * 
 * Consolidates functionality from:
 * - Pass 1: Basic webview creation and lifecycle management
 * - Pass 2: Performance optimizations (caching, preloading, metrics)
 * - Pass 3: Security hardening (input validation, state protection)
 * 
 * Operation Modes:
 * - BASIC: Simple panel creation without caching
 * - PERFORMANCE: LRU caching, preloaded templates, metrics tracking
 * - SECURE: Input validation, secure state management, content sanitization
 * - ENTERPRISE: All features with maximum performance and security
 * 
 * @module M013-VSCodeExtension
 * @version 3.0.0
 */

import * as vscode from 'vscode';
import * as path from 'path';
import { Logger } from '../utils/Logger';
import * as crypto from 'crypto';

// Configuration interface
interface ExtensionConfig {
    operationMode: 'BASIC' | 'PERFORMANCE' | 'SECURE' | 'ENTERPRISE';
    features: {
        caching: boolean;
        preloading: boolean;
        inputValidation: boolean;
        stateEncryption: boolean;
        metricsTracking: boolean;
    };
}

// Performance features interfaces
interface WebviewCache {
    html: Map<string, string>;
    state: Map<string, any>;
    resources: Map<string, vscode.Uri>;
    lastAccess: Map<string, number>;
    maxSize: number;
}

interface WebviewMetrics {
    loadTimes: Map<string, number>;
    cacheHits: number;
    cacheMisses: number;
    averageLoadTime: number;
    panelsCreated: number;
    messagesHandled: number;
}

// Security interfaces
interface SecurityContext {
    inputValidator?: any;
    stateEncryption?: boolean;
    sessionId?: string;
    encryptionKey?: string;
}

// Panel configuration
interface PanelConfig {
    id: string;
    title: string;
    viewType: string;
    iconPath?: { light: vscode.Uri; dark: vscode.Uri };
    options?: vscode.WebviewPanelOptions;
}

/**
 * Unified Webview Manager with mode-based operation
 */
export class WebviewManager {
    private panels: Map<string, vscode.WebviewPanel> = new Map();
    private disposables: vscode.Disposable[] = [];
    
    // Performance features (PERFORMANCE/ENTERPRISE modes)
    private cache?: WebviewCache;
    private metrics?: WebviewMetrics;
    private templates: Map<string, string> = new Map();
    private templateLoadPromise?: Promise<void>;
    
    // Security context (SECURE/ENTERPRISE modes)
    private securityContext: SecurityContext = {};
    
    constructor(
        private context: vscode.ExtensionContext,
        private logger: Logger,
        private extensionConfig: ExtensionConfig
    ) {
        this.initializeFeatures();
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
        // Initialize cache
        this.cache = {
            html: new Map(),
            state: new Map(),
            resources: new Map(),
            lastAccess: new Map(),
            maxSize: this.extensionConfig.operationMode === 'ENTERPRISE' ? 10 : 5
        };
        
        // Initialize metrics
        this.metrics = {
            loadTimes: new Map(),
            cacheHits: 0,
            cacheMisses: 0,
            averageLoadTime: 0,
            panelsCreated: 0,
            messagesHandled: 0
        };
        
        // Load persisted state
        this.loadPersistedState();
        
        // Preload templates if enabled
        if (this.extensionConfig.features.preloading) {
            this.templateLoadPromise = this.preloadTemplates();
        }
        
        // Setup cache cleanup
        this.setupCacheCleanup();
    }
    
    /**
     * Initialize security features
     */
    private initializeSecurityFeatures(): void {
        this.securityContext = {
            sessionId: crypto.randomUUID(),
            stateEncryption: this.extensionConfig.features.stateEncryption,
            encryptionKey: this.generateEncryptionKey()
        };
    }
    
    /**
     * Shows the main dashboard webview
     */
    public async showDashboard(data?: any): Promise<void> {
        const startTime = Date.now();
        const panelId = 'dashboard';
        
        try {
            // Security validation
            if (data && this.shouldEnableSecurity()) {
                await this.validateInput('showDashboard', data);
            }
            
            let panel = this.panels.get(panelId);
            
            if (panel) {
                // Reveal existing panel
                panel.reveal();
                
                // Update with new data if provided
                if (data) {
                    await this.sendSecureMessage(panel, {
                        command: 'update',
                        data: await this.processSecureData(data)
                    });
                }
                
                // Record cache hit
                this.recordCacheHit();
            } else {
                // Create new panel
                panel = await this.createDashboardPanel(panelId, data);
                this.recordCacheMiss();
            }
            
            // Record performance metrics
            const loadTime = Date.now() - startTime;
            this.recordMetrics('dashboard', loadTime);
            
        } catch (error) {
            this.logger.error('Failed to show dashboard:', error);
            this.showErrorPanel('Failed to load dashboard', error.message);
        }
    }
    
    /**
     * Shows documentation viewer webview
     */
    public async showDocumentationViewer(documentPath: string, content?: string): Promise<void> {
        const panelId = `documentation-${path.basename(documentPath)}`;
        
        // Security validation
        if (this.shouldEnableSecurity()) {
            await this.validateInput('showDocumentationViewer', { documentPath });
        }
        
        let panel = this.panels.get(panelId);
        
        if (panel) {
            panel.reveal();
        } else {
            panel = await this.createDocumentationPanel(panelId, documentPath, content);
        }
    }
    
    /**
     * Shows quality metrics webview
     */
    public async showQualityMetrics(filePath: string, metrics: any): Promise<void> {
        const panelId = 'quality-metrics';
        
        // Security validation
        if (this.shouldEnableSecurity()) {
            await this.validateInput('showQualityMetrics', { filePath, metrics });
        }
        
        let panel = this.panels.get(panelId);
        
        if (panel) {
            panel.reveal();
            await this.sendSecureMessage(panel, {
                command: 'updateMetrics',
                data: { filePath, metrics: await this.processSecureData(metrics) }
            });
        } else {
            panel = await this.createQualityMetricsPanel(panelId, filePath, metrics);
        }
    }
    
    /**
     * Shows project statistics webview
     */
    public async showProjectStats(stats: any): Promise<void> {
        const panelId = 'project-stats';
        
        // Security validation
        if (this.shouldEnableSecurity()) {
            await this.validateInput('showProjectStats', { stats });
        }
        
        let panel = this.panels.get(panelId);
        
        if (panel) {
            panel.reveal();
            await this.sendSecureMessage(panel, {
                command: 'updateStats',
                data: await this.processSecureData(stats)
            });
        } else {
            panel = await this.createProjectStatsPanel(panelId, stats);
        }
    }
    
    /**
     * Shows configuration webview
     */
    public async showConfiguration(currentConfig?: any): Promise<void> {
        const panelId = 'configuration';
        
        let panel = this.panels.get(panelId);
        
        if (panel) {
            panel.reveal();
        } else {
            panel = await this.createConfigurationPanel(panelId, currentConfig);
        }
    }
    
    // ==================== Panel Creation Methods ====================
    
    /**
     * Create dashboard panel
     */
    private async createDashboardPanel(panelId: string, data?: any): Promise<vscode.WebviewPanel> {
        const config: PanelConfig = {
            id: panelId,
            title: 'DevDocAI Dashboard',
            viewType: 'devdocaiDashboard',
            iconPath: this.getIconPaths('dashboard'),
            options: {
                enableScripts: true,
                retainContextWhenHidden: true,
                localResourceRoots: this.getResourceRoots()
            }
        };
        
        const panel = await this.createPanel(config);
        
        // Set HTML content
        panel.webview.html = await this.getDashboardHtml(panel.webview, data);
        
        // Setup message handling
        this.setupPanelMessageHandling(panel, 'dashboard');
        
        return panel;
    }
    
    /**
     * Create documentation panel
     */
    private async createDocumentationPanel(panelId: string, documentPath: string, content?: string): Promise<vscode.WebviewPanel> {
        const config: PanelConfig = {
            id: panelId,
            title: `Documentation - ${path.basename(documentPath)}`,
            viewType: 'devdocaiDocumentation',
            iconPath: this.getIconPaths('document'),
            options: {
                enableScripts: true,
                retainContextWhenHidden: false,
                localResourceRoots: this.getResourceRoots()
            }
        };
        
        const panel = await this.createPanel(config);
        
        // Set HTML content
        panel.webview.html = await this.getDocumentationHtml(panel.webview, documentPath, content);
        
        // Setup message handling
        this.setupPanelMessageHandling(panel, 'documentation');
        
        return panel;
    }
    
    /**
     * Create quality metrics panel
     */
    private async createQualityMetricsPanel(panelId: string, filePath: string, metrics: any): Promise<vscode.WebviewPanel> {
        const config: PanelConfig = {
            id: panelId,
            title: 'Quality Metrics',
            viewType: 'devdocaiQualityMetrics',
            iconPath: this.getIconPaths('metrics'),
            options: {
                enableScripts: true,
                retainContextWhenHidden: true,
                localResourceRoots: this.getResourceRoots()
            }
        };
        
        const panel = await this.createPanel(config);
        
        // Set HTML content
        panel.webview.html = await this.getQualityMetricsHtml(panel.webview, filePath, metrics);
        
        // Setup message handling
        this.setupPanelMessageHandling(panel, 'quality');
        
        return panel;
    }
    
    /**
     * Create project stats panel
     */
    private async createProjectStatsPanel(panelId: string, stats: any): Promise<vscode.WebviewPanel> {
        const config: PanelConfig = {
            id: panelId,
            title: 'Project Statistics',
            viewType: 'devdocaiProjectStats',
            iconPath: this.getIconPaths('stats'),
            options: {
                enableScripts: true,
                retainContextWhenHidden: true,
                localResourceRoots: this.getResourceRoots()
            }
        };
        
        const panel = await this.createPanel(config);
        
        // Set HTML content
        panel.webview.html = await this.getProjectStatsHtml(panel.webview, stats);
        
        // Setup message handling
        this.setupPanelMessageHandling(panel, 'stats');
        
        return panel;
    }
    
    /**
     * Create configuration panel
     */
    private async createConfigurationPanel(panelId: string, currentConfig?: any): Promise<vscode.WebviewPanel> {
        const config: PanelConfig = {
            id: panelId,
            title: 'DevDocAI Configuration',
            viewType: 'devdocaiConfiguration',
            iconPath: this.getIconPaths('config'),
            options: {
                enableScripts: true,
                retainContextWhenHidden: false,
                localResourceRoots: this.getResourceRoots()
            }
        };
        
        const panel = await this.createPanel(config);
        
        // Set HTML content
        panel.webview.html = await this.getConfigurationHtml(panel.webview, currentConfig);
        
        // Setup message handling
        this.setupPanelMessageHandling(panel, 'configuration');
        
        return panel;
    }
    
    /**
     * Generic panel creation with caching support
     */
    private async createPanel(config: PanelConfig): Promise<vscode.WebviewPanel> {
        const panel = vscode.window.createWebviewPanel(
            config.viewType,
            config.title,
            vscode.ViewColumn.One,
            config.options
        );
        
        // Set icon if provided
        if (config.iconPath) {
            panel.iconPath = config.iconPath;
        }
        
        // Store panel
        this.panels.set(config.id, panel);
        
        // Handle disposal
        panel.onDidDispose(() => {
            this.panels.delete(config.id);
            this.cleanupPanelResources(config.id);
        }, undefined, this.disposables);
        
        // Update metrics
        if (this.metrics) {
            this.metrics.panelsCreated++;
        }
        
        return panel;
    }
    
    // ==================== HTML Generation Methods ====================
    
    /**
     * Generate dashboard HTML with caching
     */
    private async getDashboardHtml(webview: vscode.Webview, data?: any): Promise<string> {
        const cacheKey = `dashboard-${this.hashData(data)}`;
        
        // Check cache first
        if (this.cache && this.cache.html.has(cacheKey)) {
            this.updateCacheAccess(cacheKey);
            return this.cache.html.get(cacheKey)!;
        }
        
        // Ensure templates are loaded
        if (this.templateLoadPromise) {
            await this.templateLoadPromise;
        }
        
        // Generate HTML
        const template = this.templates.get('dashboard') || this.getDefaultDashboardTemplate();
        const html = this.renderTemplate(template, webview, data);
        
        // Cache if enabled
        if (this.cache) {
            this.cacheHtml(cacheKey, html);
        }
        
        return html;
    }
    
    /**
     * Generate documentation HTML
     */
    private async getDocumentationHtml(webview: vscode.Webview, documentPath: string, content?: string): Promise<string> {
        const template = this.templates.get('documentation') || this.getDefaultDocumentationTemplate();
        return this.renderTemplate(template, webview, { documentPath, content });
    }
    
    /**
     * Generate quality metrics HTML
     */
    private async getQualityMetricsHtml(webview: vscode.Webview, filePath: string, metrics: any): Promise<string> {
        const template = this.templates.get('quality') || this.getDefaultQualityTemplate();
        return this.renderTemplate(template, webview, { filePath, metrics });
    }
    
    /**
     * Generate project stats HTML
     */
    private async getProjectStatsHtml(webview: vscode.Webview, stats: any): Promise<string> {
        const template = this.templates.get('stats') || this.getDefaultStatsTemplate();
        return this.renderTemplate(template, webview, { stats });
    }
    
    /**
     * Generate configuration HTML
     */
    private async getConfigurationHtml(webview: vscode.Webview, currentConfig?: any): Promise<string> {
        const template = this.templates.get('configuration') || this.getDefaultConfigurationTemplate();
        return this.renderTemplate(template, webview, { currentConfig });
    }
    
    /**
     * Render template with data and webview context
     */
    private renderTemplate(template: string, webview: vscode.Webview, data?: any): string {
        // Get resource URIs
        const stylesUri = webview.asWebviewUri(
            vscode.Uri.file(path.join(this.context.extensionPath, 'resources', 'css', 'webview.css'))
        );
        const scriptUri = webview.asWebviewUri(
            vscode.Uri.file(path.join(this.context.extensionPath, 'resources', 'js', 'webview.js'))
        );
        
        // Security nonce for CSP
        const nonce = crypto.randomBytes(16).toString('base64');
        
        // Replace placeholders
        return template
            .replace(/\{\{stylesUri\}\}/g, stylesUri.toString())
            .replace(/\{\{scriptUri\}\}/g, scriptUri.toString())
            .replace(/\{\{nonce\}\}/g, nonce)
            .replace(/\{\{data\}\}/g, JSON.stringify(data || {}))
            .replace(/\{\{operationMode\}\}/g, this.extensionConfig.operationMode);
    }
    
    // ==================== Message Handling ====================
    
    /**
     * Setup message handling for a panel
     */
    private setupPanelMessageHandling(panel: vscode.WebviewPanel, panelType: string): void {
        panel.webview.onDidReceiveMessage(
            async message => {
                try {
                    // Security validation
                    if (this.shouldEnableSecurity()) {
                        await this.validateMessage(message);
                    }
                    
                    await this.handlePanelMessage(panelType, message, panel);
                    
                    // Update metrics
                    if (this.metrics) {
                        this.metrics.messagesHandled++;
                    }
                    
                } catch (error) {
                    this.logger.error(`Message handling error for ${panelType}:`, error);
                    
                    // Send error response
                    panel.webview.postMessage({
                        command: 'error',
                        message: error.message
                    });
                }
            },
            undefined,
            this.disposables
        );
    }
    
    /**
     * Handle messages from webview panels
     */
    private async handlePanelMessage(panelType: string, message: any, panel: vscode.WebviewPanel): Promise<void> {
        switch (panelType) {
            case 'dashboard':
                await this.handleDashboardMessage(message, panel);
                break;
            case 'documentation':
                await this.handleDocumentationMessage(message, panel);
                break;
            case 'quality':
                await this.handleQualityMessage(message, panel);
                break;
            case 'stats':
                await this.handleStatsMessage(message, panel);
                break;
            case 'configuration':
                await this.handleConfigurationMessage(message, panel);
                break;
            default:
                this.logger.warn(`Unknown panel type: ${panelType}`);
        }
    }
    
    /**
     * Handle dashboard-specific messages
     */
    private async handleDashboardMessage(message: any, panel: vscode.WebviewPanel): Promise<void> {
        switch (message.command) {
            case 'refresh':
                // Refresh dashboard data
                panel.webview.postMessage({
                    command: 'dataUpdated',
                    data: await this.getDashboardData()
                });
                break;
                
            case 'openFile':
                // Open file in editor
                if (message.filePath) {
                    await vscode.commands.executeCommand('vscode.open', vscode.Uri.file(message.filePath));
                }
                break;
                
            case 'generateDocs':
                // Trigger documentation generation
                await vscode.commands.executeCommand('devdocai.generateDocumentation', message.params);
                break;
                
            default:
                this.logger.warn(`Unknown dashboard command: ${message.command}`);
        }
    }
    
    /**
     * Handle documentation-specific messages
     */
    private async handleDocumentationMessage(message: any, panel: vscode.WebviewPanel): Promise<void> {
        switch (message.command) {
            case 'save':
                // Save documentation
                if (message.content && message.filePath) {
                    await this.saveDocumentation(message.filePath, message.content);
                    panel.webview.postMessage({ command: 'saved' });
                }
                break;
                
            case 'export':
                // Export documentation
                await this.exportDocumentation(message.format, message.content);
                break;
                
            default:
                this.logger.warn(`Unknown documentation command: ${message.command}`);
        }
    }
    
    /**
     * Handle quality metrics messages
     */
    private async handleQualityMessage(message: any, panel: vscode.WebviewPanel): Promise<void> {
        switch (message.command) {
            case 'analyzeFile':
                // Analyze specific file
                if (message.filePath) {
                    await vscode.commands.executeCommand('devdocai.analyzeQuality', message.filePath);
                }
                break;
                
            case 'showSuggestions':
                // Show improvement suggestions
                panel.webview.postMessage({
                    command: 'suggestionsLoaded',
                    data: await this.getQualitySuggestions(message.filePath)
                });
                break;
                
            default:
                this.logger.warn(`Unknown quality command: ${message.command}`);
        }
    }
    
    /**
     * Handle statistics messages
     */
    private async handleStatsMessage(message: any, panel: vscode.WebviewPanel): Promise<void> {
        switch (message.command) {
            case 'refresh':
                // Refresh statistics
                panel.webview.postMessage({
                    command: 'statsUpdated',
                    data: await this.getProjectStatistics()
                });
                break;
                
            case 'exportReport':
                // Export statistics report
                await this.exportStatisticsReport(message.format);
                break;
                
            default:
                this.logger.warn(`Unknown stats command: ${message.command}`);
        }
    }
    
    /**
     * Handle configuration messages
     */
    private async handleConfigurationMessage(message: any, panel: vscode.WebviewPanel): Promise<void> {
        switch (message.command) {
            case 'save':
                // Save configuration
                if (message.config) {
                    await this.saveConfiguration(message.config);
                    panel.webview.postMessage({ command: 'configSaved' });
                }
                break;
                
            case 'reset':
                // Reset to defaults
                await this.resetConfiguration();
                panel.webview.postMessage({
                    command: 'configReset',
                    data: await this.getDefaultConfiguration()
                });
                break;
                
            default:
                this.logger.warn(`Unknown configuration command: ${message.command}`);
        }
    }
    
    // ==================== Utility Methods ====================
    
    /**
     * Get icon paths for different panel types
     */
    private getIconPaths(type: string): { light: vscode.Uri; dark: vscode.Uri } {
        return {
            light: vscode.Uri.file(path.join(this.context.extensionPath, 'resources', 'icons', `${type}-light.svg`)),
            dark: vscode.Uri.file(path.join(this.context.extensionPath, 'resources', 'icons', `${type}-dark.svg`))
        };
    }
    
    /**
     * Get resource roots for webviews
     */
    private getResourceRoots(): vscode.Uri[] {
        return [
            vscode.Uri.file(path.join(this.context.extensionPath, 'resources')),
            vscode.Uri.file(path.join(this.context.extensionPath, 'dist')),
            vscode.Uri.file(path.join(this.context.extensionPath, 'node_modules'))
        ];
    }
    
    /**
     * Show error panel
     */
    private showErrorPanel(title: string, message: string): void {
        const panel = vscode.window.createWebviewPanel(
            'devdocaiError',
            title,
            vscode.ViewColumn.One,
            { enableScripts: false }
        );
        
        panel.webview.html = this.getErrorHtml(title, message);
    }
    
    /**
     * Generate error HTML
     */
    private getErrorHtml(title: string, message: string): string {
        return `
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="UTF-8">
                <title>${title}</title>
                <style>
                    body { font-family: var(--vscode-font-family); padding: 20px; }
                    .error { color: var(--vscode-errorForeground); }
                    .message { margin: 20px 0; }
                </style>
            </head>
            <body>
                <h1 class="error">${title}</h1>
                <div class="message">${message}</div>
            </body>
            </html>
        `;
    }
    
    // ==================== Performance Methods ====================
    
    /**
     * Preload templates for performance
     */
    private async preloadTemplates(): Promise<void> {
        const templatePath = path.join(this.context.extensionPath, 'resources', 'templates');
        const templateFiles = ['dashboard.html', 'documentation.html', 'quality.html', 'stats.html', 'configuration.html'];
        
        for (const templateFile of templateFiles) {
            try {
                const templatePath = path.join(templatePath, templateFile);
                const content = await vscode.workspace.fs.readFile(vscode.Uri.file(templatePath));
                const templateName = path.basename(templateFile, '.html');
                this.templates.set(templateName, content.toString());
            } catch (error) {
                this.logger.debug(`Template not found: ${templateFile}`);
            }
        }
        
        this.logger.info(`Preloaded ${this.templates.size} webview templates`);
    }
    
    /**
     * Cache HTML content
     */
    private cacheHtml(key: string, html: string): void {
        if (!this.cache) return;
        
        // Remove oldest entries if cache is full
        if (this.cache.html.size >= this.cache.maxSize) {
            const oldestKey = this.getOldestCacheKey();
            if (oldestKey) {
                this.cache.html.delete(oldestKey);
                this.cache.lastAccess.delete(oldestKey);
            }
        }
        
        this.cache.html.set(key, html);
        this.cache.lastAccess.set(key, Date.now());
    }
    
    /**
     * Update cache access time
     */
    private updateCacheAccess(key: string): void {
        if (this.cache) {
            this.cache.lastAccess.set(key, Date.now());
        }
    }
    
    /**
     * Get oldest cache key for LRU eviction
     */
    private getOldestCacheKey(): string | undefined {
        if (!this.cache) return undefined;
        
        let oldestKey: string | undefined;
        let oldestTime = Number.MAX_VALUE;
        
        this.cache.lastAccess.forEach((time, key) => {
            if (time < oldestTime) {
                oldestTime = time;
                oldestKey = key;
            }
        });
        
        return oldestKey;
    }
    
    /**
     * Setup cache cleanup interval
     */
    private setupCacheCleanup(): void {
        setInterval(() => {
            this.cleanupExpiredCache();
        }, 300000); // Cleanup every 5 minutes
    }
    
    /**
     * Clean up expired cache entries
     */
    private cleanupExpiredCache(): void {
        if (!this.cache) return;
        
        const now = Date.now();
        const maxAge = 1800000; // 30 minutes
        
        this.cache.lastAccess.forEach((time, key) => {
            if (now - time > maxAge) {
                this.cache!.html.delete(key);
                this.cache!.state.delete(key);
                this.cache!.lastAccess.delete(key);
            }
        });
    }
    
    /**
     * Record cache hit
     */
    private recordCacheHit(): void {
        if (this.metrics) {
            this.metrics.cacheHits++;
        }
    }
    
    /**
     * Record cache miss
     */
    private recordCacheMiss(): void {
        if (this.metrics) {
            this.metrics.cacheMisses++;
        }
    }
    
    /**
     * Record performance metrics
     */
    private recordMetrics(panelType: string, loadTime: number): void {
        if (!this.metrics) return;
        
        this.metrics.loadTimes.set(panelType, loadTime);
        
        // Update average load time
        const totalLoadTimes = Array.from(this.metrics.loadTimes.values());
        this.metrics.averageLoadTime = totalLoadTimes.reduce((a, b) => a + b, 0) / totalLoadTimes.length;
    }
    
    // ==================== Security Methods ====================
    
    /**
     * Validate input for security
     */
    private async validateInput(operation: string, data: any): Promise<void> {
        if (!this.shouldEnableSecurity()) return;
        
        // Basic validation
        if (typeof data !== 'object') {
            throw new Error('Invalid input data type');
        }
        
        // Check for dangerous content
        const dataStr = JSON.stringify(data);
        if (dataStr.includes('<script>') || dataStr.includes('javascript:') || dataStr.includes('eval(')) {
            throw new Error('Potentially dangerous content detected');
        }
    }
    
    /**
     * Validate messages from webviews
     */
    private async validateMessage(message: any): Promise<void> {
        if (!message || typeof message !== 'object') {
            throw new Error('Invalid message format');
        }
        
        if (!message.command) {
            throw new Error('Message missing command');
        }
        
        // Validate command whitelist
        const allowedCommands = [
            'refresh', 'save', 'export', 'openFile', 'generateDocs',
            'analyzeFile', 'showSuggestions', 'exportReport', 'reset'
        ];
        
        if (!allowedCommands.includes(message.command)) {
            throw new Error(`Unauthorized command: ${message.command}`);
        }
    }
    
    /**
     * Process data securely
     */
    private async processSecureData(data: any): Promise<any> {
        if (!this.shouldEnableSecurity()) {
            return data;
        }
        
        // Sanitize data
        const sanitized = this.sanitizeObject(data);
        
        // Encrypt if enabled
        if (this.securityContext.stateEncryption) {
            return this.encryptData(sanitized);
        }
        
        return sanitized;
    }
    
    /**
     * Send secure message to webview
     */
    private async sendSecureMessage(panel: vscode.WebviewPanel, message: any): Promise<void> {
        if (this.shouldEnableSecurity()) {
            message.sessionId = this.securityContext.sessionId;
            message.timestamp = Date.now();
        }
        
        panel.webview.postMessage(message);
    }
    
    /**
     * Sanitize object recursively
     */
    private sanitizeObject(obj: any): any {
        if (typeof obj !== 'object' || obj === null) {
            return obj;
        }
        
        if (Array.isArray(obj)) {
            return obj.map(item => this.sanitizeObject(item));
        }
        
        const sanitized: any = {};
        for (const [key, value] of Object.entries(obj)) {
            if (typeof value === 'string') {
                // Remove potentially dangerous content
                sanitized[key] = value
                    .replace(/<script[^>]*>.*?<\/script>/gi, '')
                    .replace(/javascript:/gi, '')
                    .replace(/on\w+\s*=/gi, '');
            } else {
                sanitized[key] = this.sanitizeObject(value);
            }
        }
        
        return sanitized;
    }
    
    /**
     * Generate encryption key
     */
    private generateEncryptionKey(): string {
        return crypto.randomBytes(32).toString('hex');
    }
    
    /**
     * Encrypt data (placeholder - would use real encryption in production)
     */
    private encryptData(data: any): string {
        // In production, use proper encryption like AES
        return Buffer.from(JSON.stringify(data)).toString('base64');
    }
    
    // ==================== State Management ====================
    
    /**
     * Load persisted state
     */
    private loadPersistedState(): void {
        if (!this.cache) return;
        
        try {
            const persistedState = this.context.globalState.get('webviewState');
            if (persistedState) {
                this.cache.state = new Map(Object.entries(persistedState));
            }
        } catch (error) {
            this.logger.error('Failed to load persisted state:', error);
        }
    }
    
    /**
     * Save state to persistence
     */
    private savePersistedState(): void {
        if (!this.cache) return;
        
        try {
            const stateObj = Object.fromEntries(this.cache.state.entries());
            this.context.globalState.update('webviewState', stateObj);
        } catch (error) {
            this.logger.error('Failed to save persisted state:', error);
        }
    }
    
    // ==================== Data Methods (Placeholders) ====================
    
    private async getDashboardData(): Promise<any> {
        // Implementation would fetch actual dashboard data
        return { placeholder: 'dashboard data' };
    }
    
    private async getQualitySuggestions(filePath: string): Promise<any> {
        // Implementation would fetch quality suggestions
        return { placeholder: 'quality suggestions' };
    }
    
    private async getProjectStatistics(): Promise<any> {
        // Implementation would calculate project statistics
        return { placeholder: 'project statistics' };
    }
    
    private async getDefaultConfiguration(): Promise<any> {
        // Implementation would return default configuration
        return { placeholder: 'default configuration' };
    }
    
    private async saveDocumentation(filePath: string, content: string): Promise<void> {
        // Implementation would save documentation
    }
    
    private async exportDocumentation(format: string, content: string): Promise<void> {
        // Implementation would export documentation
    }
    
    private async exportStatisticsReport(format: string): Promise<void> {
        // Implementation would export statistics report
    }
    
    private async saveConfiguration(config: any): Promise<void> {
        // Implementation would save configuration
    }
    
    private async resetConfiguration(): Promise<void> {
        // Implementation would reset configuration
    }
    
    // ==================== Template Defaults ====================
    
    private getDefaultDashboardTemplate(): string {
        return `
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="UTF-8">
                <title>DevDocAI Dashboard</title>
                <link href="{{stylesUri}}" rel="stylesheet">
                <meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src {{stylesUri}}; script-src 'nonce-{{nonce}}';">
            </head>
            <body>
                <div id="app">
                    <h1>DevDocAI Dashboard</h1>
                    <div id="content">Loading...</div>
                </div>
                <script nonce="{{nonce}}" src="{{scriptUri}}"></script>
                <script nonce="{{nonce}}">
                    window.initialData = {{data}};
                    window.operationMode = '{{operationMode}}';
                </script>
            </body>
            </html>
        `;
    }
    
    private getDefaultDocumentationTemplate(): string {
        return `
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="UTF-8">
                <title>Documentation Viewer</title>
                <link href="{{stylesUri}}" rel="stylesheet">
            </head>
            <body>
                <div id="app">
                    <h1>Documentation Viewer</h1>
                    <div id="content">{{data}}</div>
                </div>
                <script nonce="{{nonce}}" src="{{scriptUri}}"></script>
            </body>
            </html>
        `;
    }
    
    private getDefaultQualityTemplate(): string {
        return `
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="UTF-8">
                <title>Quality Metrics</title>
                <link href="{{stylesUri}}" rel="stylesheet">
            </head>
            <body>
                <div id="app">
                    <h1>Quality Metrics</h1>
                    <div id="metrics">{{data}}</div>
                </div>
                <script nonce="{{nonce}}" src="{{scriptUri}}"></script>
            </body>
            </html>
        `;
    }
    
    private getDefaultStatsTemplate(): string {
        return `
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="UTF-8">
                <title>Project Statistics</title>
                <link href="{{stylesUri}}" rel="stylesheet">
            </head>
            <body>
                <div id="app">
                    <h1>Project Statistics</h1>
                    <div id="stats">{{data}}</div>
                </div>
                <script nonce="{{nonce}}" src="{{scriptUri}}"></script>
            </body>
            </html>
        `;
    }
    
    private getDefaultConfigurationTemplate(): string {
        return `
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="UTF-8">
                <title>DevDocAI Configuration</title>
                <link href="{{stylesUri}}" rel="stylesheet">
            </head>
            <body>
                <div id="app">
                    <h1>DevDocAI Configuration</h1>
                    <div id="config">{{data}}</div>
                </div>
                <script nonce="{{nonce}}" src="{{scriptUri}}"></script>
            </body>
            </html>
        `;
    }
    
    // ==================== Utility Methods ====================
    
    /**
     * Hash data for cache keys
     */
    private hashData(data: any): string {
        return crypto.createHash('md5').update(JSON.stringify(data || {})).digest('hex');
    }
    
    /**
     * Check if performance features should be enabled
     */
    private shouldEnablePerformance(): boolean {
        return this.extensionConfig.operationMode === 'PERFORMANCE' || 
               this.extensionConfig.operationMode === 'ENTERPRISE';
    }
    
    /**
     * Check if security features should be enabled
     */
    private shouldEnableSecurity(): boolean {
        return this.extensionConfig.operationMode === 'SECURE' || 
               this.extensionConfig.operationMode === 'ENTERPRISE';
    }
    
    /**
     * Cleanup panel resources
     */
    private cleanupPanelResources(panelId: string): void {
        // Clean up cached data for this panel
        if (this.cache) {
            const keysToRemove: string[] = [];
            this.cache.html.forEach((_, key) => {
                if (key.startsWith(panelId)) {
                    keysToRemove.push(key);
                }
            });
            
            keysToRemove.forEach(key => {
                this.cache!.html.delete(key);
                this.cache!.state.delete(key);
                this.cache!.lastAccess.delete(key);
            });
        }
    }
    
    /**
     * Get performance metrics
     */
    public getMetrics(): any {
        return {
            ...this.metrics,
            panelCount: this.panels.size,
            cacheSize: this.cache?.html.size || 0,
            operationMode: this.extensionConfig.operationMode
        };
    }
    
    /**
     * Dispose all resources
     */
    public dispose(): void {
        // Close all panels
        this.panels.forEach(panel => {
            panel.dispose();
        });
        this.panels.clear();
        
        // Dispose disposables
        this.disposables.forEach(disposable => {
            disposable.dispose();
        });
        this.disposables = [];
        
        // Save persisted state
        this.savePersistedState();
        
        // Clear caches
        if (this.cache) {
            this.cache.html.clear();
            this.cache.state.clear();
            this.cache.resources.clear();
            this.cache.lastAccess.clear();
        }
    }
}

// Export types for external use
export type { ExtensionConfig, WebviewMetrics, PanelConfig };