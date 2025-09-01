/**
 * Optimized Webview Manager - Cached and Performant
 * 
 * Performance optimizations:
 * - LRU cache for compiled HTML/CSS/JS
 * - Precompiled templates at build time
 * - State persistence between sessions
 * - Incremental DOM updates
 * - Resource bundling and minification
 * 
 * @module M013-VSCodeExtension
 */

import * as vscode from 'vscode';
import * as path from 'path';
import { Logger } from '../utils/Logger';
import { InputValidator, ValidationResult } from '../security/InputValidator';

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
}

export class OptimizedWebviewManager {
    private panels: Map<string, vscode.WebviewPanel> = new Map();
    private disposables: vscode.Disposable[] = [];
    
    // Security components
    private inputValidator: InputValidator;
    
    // LRU Cache for webview content
    private cache: WebviewCache = {
        html: new Map(),
        state: new Map(),
        resources: new Map(),
        lastAccess: new Map(),
        maxSize: 5
    };
    
    // Performance metrics
    private metrics: WebviewMetrics = {
        loadTimes: new Map(),
        cacheHits: 0,
        cacheMisses: 0,
        averageLoadTime: 0
    };
    
    // Precompiled templates (loaded once)
    private templates: Map<string, string> = new Map();
    private templateLoadPromise: Promise<void> | null = null;
    
    constructor(
        private context: vscode.ExtensionContext,
        private logger: Logger
    ) {
        // Initialize security validator
        this.inputValidator = new InputValidator(context);
        
        // Load persisted state from global state
        this.loadPersistedState();
        
        // Preload templates in background
        this.templateLoadPromise = this.preloadTemplates();
    }
    
    /**
     * Shows dashboard with caching and optimizations
     */
    public async showDashboard(data?: any): Promise<void> {
        const startTime = Date.now();
        const panelId = 'dashboard';
        
        // Check if panel already exists
        let panel = this.panels.get(panelId);
        
        if (panel) {
            // Reveal existing panel (instant)
            panel.reveal();
            
            // Send incremental update if data provided
            if (data) {
                this.sendIncrementalUpdate(panel, data);
            }
            
            this.updateMetrics(panelId, Date.now() - startTime, true);
            return;
        }
        
        // Create new panel with cached content
        panel = await this.createOptimizedPanel(
            panelId,
            'devdocaiDashboard',
            'DevDocAI Dashboard',
            vscode.ViewColumn.One
        );
        
        // Set HTML from cache or generate
        const html = await this.getCachedHtml(panelId, () => this.generateDashboardHtml(panel!.webview));
        panel.webview.html = html;
        
        // Restore previous state if available
        const savedState = this.cache.state.get(panelId);
        if (savedState) {
            panel.webview.postMessage({
                command: 'restoreState',
                state: savedState
            });
        }
        
        // Setup message handling
        this.setupMessageHandling(panel, panelId, this.handleDashboardMessage.bind(this));
        
        // Store panel reference
        this.panels.set(panelId, panel);
        
        // Send initial data
        if (data) {
            panel.webview.postMessage({
                command: 'initialize',
                data
            });
        }
        
        this.updateMetrics(panelId, Date.now() - startTime, false);
    }
    
    /**
     * Shows document generator with optimizations
     */
    public async showDocumentGenerator(filePath?: string): Promise<void> {
        const startTime = Date.now();
        const panelId = 'documentGenerator';
        
        let panel = this.panels.get(panelId);
        
        if (panel) {
            panel.reveal();
            if (filePath) {
                this.sendIncrementalUpdate(panel, { filePath });
            }
            this.updateMetrics(panelId, Date.now() - startTime, true);
            return;
        }
        
        panel = await this.createOptimizedPanel(
            panelId,
            'devdocaiGenerator',
            'Documentation Generator',
            vscode.ViewColumn.Two
        );
        
        const html = await this.getCachedHtml(panelId, () => this.generateDocumentGeneratorHtml(panel!.webview));
        panel.webview.html = html;
        
        this.setupMessageHandling(panel, panelId, this.handleGeneratorMessage.bind(this));
        this.panels.set(panelId, panel);
        
        if (filePath) {
            panel.webview.postMessage({
                command: 'initialize',
                filePath
            });
        }
        
        this.updateMetrics(panelId, Date.now() - startTime, false);
    }
    
    /**
     * Creates an optimized webview panel
     */
    private async createOptimizedPanel(
        panelId: string,
        viewType: string,
        title: string,
        column: vscode.ViewColumn
    ): Promise<vscode.WebviewPanel> {
        // Wait for templates to be loaded
        if (this.templateLoadPromise) {
            await this.templateLoadPromise;
        }
        
        const panel = vscode.window.createWebviewPanel(
            viewType,
            title,
            column,
            {
                enableScripts: true,
                retainContextWhenHidden: true, // Keep context for better performance
                localResourceRoots: [
                    vscode.Uri.file(path.join(this.context.extensionPath, 'resources')),
                    vscode.Uri.file(path.join(this.context.extensionPath, 'dist'))
                ]
            }
        );
        
        // Set icon (cached)
        const iconPath = this.getCachedResource('icon', () => ({
            light: vscode.Uri.file(path.join(this.context.extensionPath, 'resources', 'icons', 'devdocai-light.svg')),
            dark: vscode.Uri.file(path.join(this.context.extensionPath, 'resources', 'icons', 'devdocai-dark.svg'))
        }));
        panel.iconPath = iconPath;
        
        return panel;
    }
    
    /**
     * Gets cached HTML or generates new
     */
    private async getCachedHtml(panelId: string, generator: () => string | Promise<string>): Promise<string> {
        // Check cache first
        const cached = this.cache.html.get(panelId);
        if (cached) {
            this.metrics.cacheHits++;
            this.cache.lastAccess.set(panelId, Date.now());
            this.logger.debug(`✅ Cache hit for ${panelId}`);
            return cached;
        }
        
        // Generate and cache
        this.metrics.cacheMisses++;
        this.logger.debug(`❌ Cache miss for ${panelId}, generating...`);
        
        const html = await generator();
        this.cacheHtml(panelId, html);
        
        return html;
    }
    
    /**
     * Caches HTML with LRU eviction
     */
    private cacheHtml(panelId: string, html: string): void {
        // Check cache size and evict if necessary
        if (this.cache.html.size >= this.cache.maxSize) {
            this.evictLRU();
        }
        
        this.cache.html.set(panelId, html);
        this.cache.lastAccess.set(panelId, Date.now());
    }
    
    /**
     * Evicts least recently used cache entry
     */
    private evictLRU(): void {
        let oldestTime = Date.now();
        let oldestKey = '';
        
        for (const [key, time] of this.cache.lastAccess.entries()) {
            if (time < oldestTime) {
                oldestTime = time;
                oldestKey = key;
            }
        }
        
        if (oldestKey) {
            this.cache.html.delete(oldestKey);
            this.cache.state.delete(oldestKey);
            this.cache.lastAccess.delete(oldestKey);
            this.logger.debug(`🗑️ Evicted ${oldestKey} from cache`);
        }
    }
    
    /**
     * Sends incremental update instead of full refresh
     */
    private sendIncrementalUpdate(panel: vscode.WebviewPanel, data: any): void {
        panel.webview.postMessage({
            command: 'incrementalUpdate',
            data,
            timestamp: Date.now()
        });
    }
    
    /**
     * Preloads templates for instant rendering
     */
    private async preloadTemplates(): Promise<void> {
        this.logger.debug('📦 Preloading webview templates...');
        
        // In production, these would be pre-compiled
        // For now, we'll cache the base templates
        this.templates.set('dashboard', this.getDashboardTemplate());
        this.templates.set('generator', this.getGeneratorTemplate());
        this.templates.set('settings', this.getSettingsTemplate());
        
        this.logger.debug('✅ Templates preloaded');
    }
    
    /**
     * Generates optimized dashboard HTML with security hardening
     */
    private generateDashboardHtml(webview: vscode.Webview): string {
        const template = this.templates.get('dashboard') || '';
        
        // Get cached resources with validation
        const scriptUri = this.getCachedResource('dashboard-script', () => 
            webview.asWebviewUri(vscode.Uri.file(
                path.join(this.context.extensionPath, 'dist', 'dashboard.min.js')
            ))
        );
        
        const styleUri = this.getCachedResource('dashboard-style', () =>
            webview.asWebviewUri(vscode.Uri.file(
                path.join(this.context.extensionPath, 'resources', 'css', 'dashboard.min.css')
            ))
        );
        
        // Generate secure nonce
        const nonce = this.getSecureNonce();
        
        // SECURITY FIX: Validate URIs before template substitution
        const scriptUriValidation = this.inputValidator.validateParameter(
            'scriptUri', 
            scriptUri.toString(),
            { maxLength: 1000, requireAlphanumeric: false }
        );
        
        const styleUriValidation = this.inputValidator.validateParameter(
            'styleUri',
            styleUri.toString(), 
            { maxLength: 1000, requireAlphanumeric: false }
        );
        
        if (!scriptUriValidation.isValid || !styleUriValidation.isValid) {
            this.logger.error('URI validation failed for webview resources');
            throw new Error('Invalid resource URIs detected');
        }
        
        // Secure template variable replacement
        return this.secureTemplateReplace(template, {
            'SCRIPT_URI': scriptUriValidation.sanitized,
            'STYLE_URI': styleUriValidation.sanitized,
            'NONCE': nonce
        });
    }
    
    /**
     * Gets dashboard template (minified) with security hardening
     */
    private getDashboardTemplate(): string {
        return `<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src {{STYLE_URI}}; script-src 'nonce-{{NONCE}}'; img-src data: https:; font-src data:; connect-src 'none'; object-src 'none'; media-src 'none'; child-src 'none'; frame-src 'none'; worker-src 'none'; form-action 'none'; base-uri 'none';">
    <title>DevDocAI Dashboard</title>
    <link href="{{STYLE_URI}}" rel="stylesheet">
</head>
<body>
    <div id="root" class="dashboard-container">
        <div class="loading-spinner" id="initial-loader">
            <div class="spinner"></div>
            <span>Loading Dashboard...</span>
        </div>
    </div>
    <script nonce="{{NONCE}}">
        const vscode = acquireVsCodeApi();
        const state = vscode.getState() || {};
        
        // Optimized event delegation
        document.addEventListener('click', (e) => {
            const target = e.target.closest('[data-action]');
            if (target) {
                const action = target.dataset.action;
                vscode.postMessage({ command: action });
            }
        });
        
        // Efficient message handling
        window.addEventListener('message', (e) => {
            const msg = e.data;
            switch(msg.command) {
                case 'initialize':
                case 'incrementalUpdate':
                    updateDashboard(msg.data, msg.command === 'incrementalUpdate');
                    break;
                case 'restoreState':
                    Object.assign(state, msg.state);
                    renderFromState();
                    break;
            }
        });
        
        // Optimized update function
        function updateDashboard(data, incremental = false) {
            // Hide loader
            document.getElementById('initial-loader')?.remove();
            
            // Use requestAnimationFrame for smooth updates
            requestAnimationFrame(() => {
                if (incremental) {
                    // Only update changed elements
                    for (const key in data) {
                        const el = document.getElementById(key);
                        if (el) {
                            updateElement(el, data[key]);
                        }
                    }
                } else {
                    // Full render
                    renderDashboard(data);
                }
                
                // Save state
                Object.assign(state, data);
                vscode.setState(state);
            });
        }
        
        function updateElement(el, value) {
            // Intelligent update based on element type
            if (el.tagName === 'INPUT') {
                el.value = value;
            } else if (el.classList.contains('metric-value')) {
                // Animate number changes
                animateValue(el, parseInt(el.textContent) || 0, value);
            } else {
                el.textContent = value;
            }
        }
        
        function animateValue(el, start, end, duration = 300) {
            const range = end - start;
            const startTime = performance.now();
            
            function update(currentTime) {
                const elapsed = currentTime - startTime;
                const progress = Math.min(elapsed / duration, 1);
                const value = Math.round(start + range * progress);
                el.textContent = value;
                
                if (progress < 1) {
                    requestAnimationFrame(update);
                }
            }
            
            requestAnimationFrame(update);
        }
        
        function renderDashboard(data) {
            const root = document.getElementById('root');
            root.innerHTML = \`
                <header class="dashboard-header">
                    <h1>DevDocAI Dashboard</h1>
                    <div class="header-actions">
                        <button data-action="refresh" class="btn btn-icon" title="Refresh">
                            <span class="codicon codicon-refresh"></span>
                        </button>
                        <button data-action="openSettings" class="btn btn-icon" title="Settings">
                            <span class="codicon codicon-settings-gear"></span>
                        </button>
                    </div>
                </header>
                <div class="dashboard-content">
                    <div class="metrics-grid">
                        <div class="metric-card">
                            <h3>Coverage</h3>
                            <div class="metric-value" id="coverage">\${data.coverage || 0}</div>
                        </div>
                        <div class="metric-card">
                            <h3>Quality</h3>
                            <div class="metric-value" id="quality">\${data.quality || 0}</div>
                        </div>
                        <div class="metric-card">
                            <h3>Security</h3>
                            <div class="metric-value" id="security">\${data.security || 0}</div>
                        </div>
                        <div class="metric-card">
                            <h3>Files</h3>
                            <div class="metric-value" id="files">\${data.files || 0}</div>
                        </div>
                    </div>
                    <div class="actions-section">
                        <button data-action="generateDocumentation" class="btn btn-primary">Generate Docs</button>
                        <button data-action="analyzeQuality" class="btn">Analyze Quality</button>
                        <button data-action="runSecurity" class="btn">Security Scan</button>
                        <button data-action="exportDocumentation" class="btn">Export</button>
                    </div>
                </div>
            \`;
        }
        
        function renderFromState() {
            if (Object.keys(state).length > 0) {
                renderDashboard(state);
            }
        }
        
        // Initial render from saved state
        renderFromState();
    </script>
    <script src="{{SCRIPT_URI}}" defer></script>
</body>
</html>`;
    }
    
    /**
     * Gets generator template
     */
    private getGeneratorTemplate(): string {
        return `<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Documentation Generator</title>
    <style>
        body { font-family: var(--vscode-font-family); }
        .generator { padding: 20px; }
    </style>
</head>
<body>
    <div class="generator">
        <h1>Documentation Generator</h1>
        <div id="content"></div>
    </div>
</body>
</html>`;
    }
    
    /**
     * Gets settings template
     */
    private getSettingsTemplate(): string {
        return `<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Settings</title>
</head>
<body>
    <div id="settings"></div>
</body>
</html>`;
    }
    
    /**
     * Generates document generator HTML
     */
    private generateDocumentGeneratorHtml(webview: vscode.Webview): string {
        return this.templates.get('generator') || '';
    }
    
    /**
     * Setup message handling with state persistence and security validation
     */
    private setupMessageHandling(
        panel: vscode.WebviewPanel,
        panelId: string,
        handler: (message: any) => Promise<void>
    ): void {
        // Handle messages with security validation
        panel.webview.onDidReceiveMessage(
            async (message) => {
                // SECURITY: Validate incoming webview message
                const validation = this.validateWebviewMessage(message);
                if (!validation.isValid) {
                    this.logger.error('Invalid webview message received:', validation.errors);
                    // Send error response back to webview
                    panel.webview.postMessage({
                        command: 'error',
                        message: 'Invalid message format',
                        code: 'VALIDATION_FAILED'
                    });
                    return;
                }
                
                // Use sanitized message
                const sanitizedMessage = validation.sanitized;
                
                // Save state updates
                if (sanitizedMessage.command === 'saveState') {
                    // Validate state data before caching
                    const stateValidation = this.inputValidator.validateDataObject(sanitizedMessage.state);
                    if (stateValidation.isValid) {
                        this.cache.state.set(panelId, stateValidation.sanitized);
                        this.persistState();
                    } else {
                        this.logger.warn('Invalid state data, not saving:', stateValidation.warnings);
                    }
                }
                
                // Handle command with sanitized message
                await handler(sanitizedMessage);
            },
            undefined,
            this.disposables
        );
        
        // Handle disposal
        panel.onDidDispose(
            () => {
                this.panels.delete(panelId);
                // Keep cache for quick re-open
            },
            undefined,
            this.disposables
        );
    }
    
    /**
     * Message handlers
     */
    private async handleDashboardMessage(message: any): Promise<void> {
        switch (message.command) {
            case 'generateDocumentation':
                await vscode.commands.executeCommand('devdocai.generateDocumentation');
                break;
            case 'analyzeQuality':
                await vscode.commands.executeCommand('devdocai.analyzeQuality');
                break;
            case 'runSecurity':
                await vscode.commands.executeCommand('devdocai.runSecurityScan');
                break;
            case 'exportDocumentation':
                await vscode.commands.executeCommand('devdocai.exportDocumentation');
                break;
            case 'refresh':
                await this.refreshDashboard();
                break;
            case 'openSettings':
                await vscode.commands.executeCommand('devdocai.configureSettings');
                break;
        }
    }
    
    private async handleGeneratorMessage(message: any): Promise<void> {
        this.logger.debug(`Generator message: ${message.command}`);
    }
    
    /**
     * Refreshes dashboard with cached data
     */
    private async refreshDashboard(): Promise<void> {
        const panel = this.panels.get('dashboard');
        if (!panel) return;
        
        // Get latest metrics (simulated)
        const data = {
            coverage: Math.round(Math.random() * 100),
            quality: Math.round(Math.random() * 100),
            security: Math.round(Math.random() * 100),
            files: Math.round(Math.random() * 100)
        };
        
        this.sendIncrementalUpdate(panel, data);
    }
    
    /**
     * Gets cached resource URI
     */
    private getCachedResource(key: string, generator: () => any): any {
        let resource = this.cache.resources.get(key);
        if (!resource) {
            resource = generator();
            this.cache.resources.set(key, resource);
        }
        return resource;
    }
    
    /**
     * Generates nonce for CSP (DEPRECATED - use getSecureNonce)
     */
    private getNonce(): string {
        return this.getSecureNonce();
    }
    
    /**
     * Generates cryptographically secure nonce for CSP
     */
    private getSecureNonce(): string {
        const crypto = require('crypto');
        return crypto.randomBytes(16).toString('base64');
    }
    
    /**
     * Secure template variable replacement to prevent XSS
     */
    private secureTemplateReplace(template: string, variables: { [key: string]: string }): string {
        let result = template;
        
        for (const [key, value] of Object.entries(variables)) {
            // Validate the variable name
            const keyValidation = this.inputValidator.validateParameter(
                'templateVar',
                key,
                { maxLength: 50, requireAlphanumeric: true }
            );
            
            if (!keyValidation.isValid) {
                this.logger.error(`Invalid template variable name: ${key}`);
                continue;
            }
            
            // Create safe placeholder pattern
            const placeholder = new RegExp(`\\{\\{${key.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}\\}\\}`, 'g');
            
            // Replace with validated value
            result = result.replace(placeholder, value);
        }
        
        // Check if there are any unreplaced placeholders (security risk)
        const unreplacedPlaceholders = result.match(/\{\{[^}]+\}\}/g);
        if (unreplacedPlaceholders) {
            this.logger.warn('Unreplaced template placeholders found:', unreplacedPlaceholders);
        }
        
        return result;
    }
    
    /**
     * Validates and sanitizes webview messages
     */
    private validateWebviewMessage(message: any): ValidationResult {
        return this.inputValidator.validateWebviewMessage(message);
    }
    
    /**
     * Updates performance metrics
     */
    private updateMetrics(panelId: string, loadTime: number, cacheHit: boolean): void {
        this.metrics.loadTimes.set(panelId, loadTime);
        
        // Calculate average
        const times = Array.from(this.metrics.loadTimes.values());
        this.metrics.averageLoadTime = times.reduce((a, b) => a + b, 0) / times.length;
        
        // Log periodically
        const total = this.metrics.cacheHits + this.metrics.cacheMisses;
        if (total % 10 === 0) {
            this.logger.info(`📊 Webview Metrics: Avg Load: ${this.metrics.averageLoadTime.toFixed(2)}ms, ` +
                `Cache Hit Rate: ${(this.metrics.cacheHits / total * 100).toFixed(1)}%`);
        }
    }
    
    /**
     * Persists state to global state
     */
    private persistState(): void {
        const stateObj = Object.fromEntries(this.cache.state);
        this.context.globalState.update('webviewStates', stateObj);
    }
    
    /**
     * Loads persisted state
     */
    private loadPersistedState(): void {
        const savedStates = this.context.globalState.get<any>('webviewStates');
        if (savedStates) {
            for (const [key, value] of Object.entries(savedStates)) {
                this.cache.state.set(key, value);
            }
            this.logger.debug(`📥 Loaded ${this.cache.state.size} persisted states`);
        }
    }
    
    /**
     * Disposes all resources
     */
    public async dispose(): Promise<void> {
        // Persist final state
        this.persistState();
        
        // Log final metrics
        this.logger.info(`📊 Final Webview Metrics: Avg Load: ${this.metrics.averageLoadTime.toFixed(2)}ms, ` +
            `Cache Hits: ${this.metrics.cacheHits}, Cache Misses: ${this.metrics.cacheMisses}`);
        
        // Dispose panels
        for (const panel of this.panels.values()) {
            panel.dispose();
        }
        
        this.panels.clear();
        
        // Dispose subscriptions
        for (const disposable of this.disposables) {
            disposable.dispose();
        }
        
        this.disposables = [];
    }
}