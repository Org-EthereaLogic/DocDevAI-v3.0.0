/**
 * Webview Manager - Manages all webview panels
 * 
 * Handles creation, lifecycle, and communication for webview panels
 * that display DevDocAI UI components from M011.
 */

import * as vscode from 'vscode';
import * as path from 'path';
import { Logger } from '../utils/Logger';

export class WebviewManager {
    private panels: Map<string, vscode.WebviewPanel> = new Map();
    private disposables: vscode.Disposable[] = [];
    
    constructor(
        private context: vscode.ExtensionContext,
        private logger: Logger
    ) {}
    
    /**
     * Creates or shows the dashboard webview
     */
    public async showDashboard(data?: any): Promise<void> {
        const panelId = 'dashboard';
        
        // Check if panel already exists
        let panel = this.panels.get(panelId);
        
        if (panel) {
            // Reveal existing panel
            panel.reveal();
            
            // Update with new data if provided
            if (data) {
                panel.webview.postMessage({
                    command: 'update',
                    data
                });
            }
        } else {
            // Create new panel
            panel = vscode.window.createWebviewPanel(
                'devdocaiDashboard',
                'DevDocAI Dashboard',
                vscode.ViewColumn.One,
                {
                    enableScripts: true,
                    retainContextWhenHidden: true,
                    localResourceRoots: [
                        vscode.Uri.file(path.join(this.context.extensionPath, 'resources')),
                        vscode.Uri.file(path.join(this.context.extensionPath, 'dist'))
                    ]
                }
            );
            
            // Set icon
            panel.iconPath = {
                light: vscode.Uri.file(path.join(this.context.extensionPath, 'resources', 'icons', 'devdocai-light.svg')),
                dark: vscode.Uri.file(path.join(this.context.extensionPath, 'resources', 'icons', 'devdocai-dark.svg'))
            };
            
            // Set HTML content
            panel.webview.html = this.getDashboardHtml(panel.webview);
            
            // Handle messages from webview
            panel.webview.onDidReceiveMessage(
                message => this.handleDashboardMessage(message),
                undefined,
                this.disposables
            );
            
            // Handle panel disposal
            panel.onDidDispose(
                () => {
                    this.panels.delete(panelId);
                },
                undefined,
                this.disposables
            );
            
            // Store panel reference
            this.panels.set(panelId, panel);
            
            // Send initial data
            if (data) {
                panel.webview.postMessage({
                    command: 'initialize',
                    data
                });
            }
        }
    }
    
    /**
     * Creates or shows the documentation generator panel
     */
    public async showDocumentGenerator(filePath?: string): Promise<void> {
        const panelId = 'documentGenerator';
        
        let panel = this.panels.get(panelId);
        
        if (panel) {
            panel.reveal();
            
            if (filePath) {
                panel.webview.postMessage({
                    command: 'loadFile',
                    filePath
                });
            }
        } else {
            panel = vscode.window.createWebviewPanel(
                'devdocaiGenerator',
                'Documentation Generator',
                vscode.ViewColumn.Two,
                {
                    enableScripts: true,
                    retainContextWhenHidden: true,
                    localResourceRoots: [
                        vscode.Uri.file(path.join(this.context.extensionPath, 'resources')),
                        vscode.Uri.file(path.join(this.context.extensionPath, 'dist'))
                    ]
                }
            );
            
            panel.webview.html = this.getDocumentGeneratorHtml(panel.webview);
            
            panel.webview.onDidReceiveMessage(
                message => this.handleGeneratorMessage(message),
                undefined,
                this.disposables
            );
            
            panel.onDidDispose(
                () => {
                    this.panels.delete(panelId);
                },
                undefined,
                this.disposables
            );
            
            this.panels.set(panelId, panel);
            
            if (filePath) {
                panel.webview.postMessage({
                    command: 'initialize',
                    filePath
                });
            }
        }
    }
    
    /**
     * Creates or shows the MIAIR insights panel
     */
    public async showMIAIRInsights(insights: any): Promise<void> {
        const panelId = 'miairInsights';
        
        let panel = this.panels.get(panelId);
        
        if (panel) {
            panel.reveal();
            panel.webview.postMessage({
                command: 'update',
                insights
            });
        } else {
            panel = vscode.window.createWebviewPanel(
                'devdocaiMIAIR',
                'MIAIR Optimization Insights',
                vscode.ViewColumn.Two,
                {
                    enableScripts: true,
                    localResourceRoots: [
                        vscode.Uri.file(path.join(this.context.extensionPath, 'resources')),
                        vscode.Uri.file(path.join(this.context.extensionPath, 'dist'))
                    ]
                }
            );
            
            panel.webview.html = this.getMIAIRInsightsHtml(panel.webview);
            
            panel.webview.onDidReceiveMessage(
                message => this.handleMIAIRMessage(message),
                undefined,
                this.disposables
            );
            
            panel.onDidDispose(
                () => {
                    this.panels.delete(panelId);
                },
                undefined,
                this.disposables
            );
            
            this.panels.set(panelId, panel);
            
            panel.webview.postMessage({
                command: 'initialize',
                insights
            });
        }
    }
    
    /**
     * Creates or shows the settings panel
     */
    public async showSettings(): Promise<void> {
        const panelId = 'settings';
        
        let panel = this.panels.get(panelId);
        
        if (panel) {
            panel.reveal();
        } else {
            panel = vscode.window.createWebviewPanel(
                'devdocaiSettings',
                'DevDocAI Settings',
                vscode.ViewColumn.Active,
                {
                    enableScripts: true,
                    localResourceRoots: [
                        vscode.Uri.file(path.join(this.context.extensionPath, 'resources'))
                    ]
                }
            );
            
            panel.webview.html = this.getSettingsHtml(panel.webview);
            
            panel.webview.onDidReceiveMessage(
                message => this.handleSettingsMessage(message),
                undefined,
                this.disposables
            );
            
            panel.onDidDispose(
                () => {
                    this.panels.delete(panelId);
                },
                undefined,
                this.disposables
            );
            
            this.panels.set(panelId, panel);
            
            // Load current settings
            const config = vscode.workspace.getConfiguration('devdocai');
            panel.webview.postMessage({
                command: 'loadSettings',
                settings: config
            });
        }
    }
    
    /**
     * Generates HTML for the dashboard
     */
    private getDashboardHtml(webview: vscode.Webview): string {
        const scriptUri = webview.asWebviewUri(
            vscode.Uri.file(path.join(this.context.extensionPath, 'dist', 'dashboard.js'))
        );
        const styleUri = webview.asWebviewUri(
            vscode.Uri.file(path.join(this.context.extensionPath, 'resources', 'css', 'dashboard.css'))
        );
        
        return `<!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>DevDocAI Dashboard</title>
            <link href="${styleUri}" rel="stylesheet">
        </head>
        <body>
            <div id="root">
                <div class="dashboard-container">
                    <header class="dashboard-header">
                        <h1>DevDocAI Dashboard</h1>
                        <div class="header-actions">
                            <button id="refresh-btn" class="btn btn-icon" title="Refresh">
                                <span class="codicon codicon-refresh"></span>
                            </button>
                            <button id="settings-btn" class="btn btn-icon" title="Settings">
                                <span class="codicon codicon-settings-gear"></span>
                            </button>
                        </div>
                    </header>
                    
                    <div class="dashboard-content">
                        <div class="metrics-grid">
                            <div class="metric-card">
                                <h3>Documentation Coverage</h3>
                                <div class="metric-value" id="coverage">--</div>
                                <div class="metric-chart" id="coverage-chart"></div>
                            </div>
                            
                            <div class="metric-card">
                                <h3>Quality Score</h3>
                                <div class="metric-value" id="quality">--</div>
                                <div class="metric-chart" id="quality-chart"></div>
                            </div>
                            
                            <div class="metric-card">
                                <h3>Security Score</h3>
                                <div class="metric-value" id="security">--</div>
                                <div class="metric-chart" id="security-chart"></div>
                            </div>
                            
                            <div class="metric-card">
                                <h3>Files Analyzed</h3>
                                <div class="metric-value" id="files">--</div>
                                <div class="metric-list" id="recent-files"></div>
                            </div>
                        </div>
                        
                        <div class="actions-section">
                            <h2>Quick Actions</h2>
                            <div class="action-buttons">
                                <button class="btn btn-primary" id="generate-doc">
                                    <span class="codicon codicon-file-text"></span>
                                    Generate Documentation
                                </button>
                                <button class="btn btn-secondary" id="analyze-quality">
                                    <span class="codicon codicon-checklist"></span>
                                    Analyze Quality
                                </button>
                                <button class="btn btn-secondary" id="run-security">
                                    <span class="codicon codicon-shield"></span>
                                    Security Scan
                                </button>
                                <button class="btn btn-secondary" id="export-docs">
                                    <span class="codicon codicon-export"></span>
                                    Export Documentation
                                </button>
                            </div>
                        </div>
                        
                        <div class="activity-section">
                            <h2>Recent Activity</h2>
                            <div class="activity-list" id="activity-list">
                                <div class="activity-item">
                                    <span class="activity-icon codicon codicon-loading"></span>
                                    <span>Loading recent activity...</span>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
            
            <script src="${scriptUri}"></script>
            <script>
                const vscode = acquireVsCodeApi();
                
                // Handle button clicks
                document.getElementById('generate-doc').addEventListener('click', () => {
                    vscode.postMessage({ command: 'generateDocumentation' });
                });
                
                document.getElementById('analyze-quality').addEventListener('click', () => {
                    vscode.postMessage({ command: 'analyzeQuality' });
                });
                
                document.getElementById('run-security').addEventListener('click', () => {
                    vscode.postMessage({ command: 'runSecurity' });
                });
                
                document.getElementById('export-docs').addEventListener('click', () => {
                    vscode.postMessage({ command: 'exportDocumentation' });
                });
                
                document.getElementById('refresh-btn').addEventListener('click', () => {
                    vscode.postMessage({ command: 'refresh' });
                });
                
                document.getElementById('settings-btn').addEventListener('click', () => {
                    vscode.postMessage({ command: 'openSettings' });
                });
                
                // Handle messages from extension
                window.addEventListener('message', event => {
                    const message = event.data;
                    
                    switch (message.command) {
                        case 'initialize':
                        case 'update':
                            updateDashboard(message.data);
                            break;
                    }
                });
                
                function updateDashboard(data) {
                    if (data.coverage !== undefined) {
                        document.getElementById('coverage').textContent = data.coverage + '%';
                    }
                    if (data.quality !== undefined) {
                        document.getElementById('quality').textContent = data.quality + '/100';
                    }
                    if (data.security !== undefined) {
                        document.getElementById('security').textContent = data.security + '/100';
                    }
                    if (data.files !== undefined) {
                        document.getElementById('files').textContent = data.files;
                    }
                    if (data.activity) {
                        updateActivityList(data.activity);
                    }
                }
                
                function updateActivityList(activities) {
                    const list = document.getElementById('activity-list');
                    list.innerHTML = '';
                    
                    activities.forEach(activity => {
                        const item = document.createElement('div');
                        item.className = 'activity-item';
                        item.innerHTML = \`
                            <span class="activity-icon codicon codicon-\${activity.icon}"></span>
                            <span class="activity-text">\${activity.text}</span>
                            <span class="activity-time">\${activity.time}</span>
                        \`;
                        list.appendChild(item);
                    });
                }
            </script>
        </body>
        </html>`;
    }
    
    /**
     * Generates HTML for the document generator
     */
    private getDocumentGeneratorHtml(webview: vscode.Webview): string {
        // Similar structure for document generator panel
        return `<!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Documentation Generator</title>
        </head>
        <body>
            <div id="root">
                <h1>Documentation Generator</h1>
                <div id="generator-content">
                    <!-- Generator UI will be rendered here -->
                </div>
            </div>
        </body>
        </html>`;
    }
    
    /**
     * Generates HTML for MIAIR insights
     */
    private getMIAIRInsightsHtml(webview: vscode.Webview): string {
        return `<!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>MIAIR Optimization Insights</title>
        </head>
        <body>
            <div id="root">
                <h1>MIAIR Optimization Insights</h1>
                <div id="insights-content">
                    <!-- MIAIR insights will be rendered here -->
                </div>
            </div>
        </body>
        </html>`;
    }
    
    /**
     * Generates HTML for settings
     */
    private getSettingsHtml(webview: vscode.Webview): string {
        return `<!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>DevDocAI Settings</title>
        </head>
        <body>
            <div id="root">
                <h1>DevDocAI Settings</h1>
                <div id="settings-content">
                    <!-- Settings UI will be rendered here -->
                </div>
            </div>
        </body>
        </html>`;
    }
    
    /**
     * Handles messages from dashboard webview
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
                // Refresh dashboard data
                await this.refreshDashboard();
                break;
            
            case 'openSettings':
                await vscode.commands.executeCommand('devdocai.configureSettings');
                break;
            
            default:
                this.logger.warn(`Unknown dashboard message: ${message.command}`);
        }
    }
    
    /**
     * Handles messages from generator webview
     */
    private async handleGeneratorMessage(message: any): Promise<void> {
        this.logger.debug(`Generator message: ${message.command}`);
    }
    
    /**
     * Handles messages from MIAIR webview
     */
    private async handleMIAIRMessage(message: any): Promise<void> {
        this.logger.debug(`MIAIR message: ${message.command}`);
    }
    
    /**
     * Handles messages from settings webview
     */
    private async handleSettingsMessage(message: any): Promise<void> {
        switch (message.command) {
            case 'saveSettings':
                await this.saveSettings(message.settings);
                break;
            
            case 'resetSettings':
                await this.resetSettings();
                break;
        }
    }
    
    /**
     * Refreshes the dashboard with latest data
     */
    private async refreshDashboard(): Promise<void> {
        // Get latest metrics from CLI service
        // This would be implemented with actual data fetching
        const data = {
            coverage: 85,
            quality: 78,
            security: 92,
            files: 42,
            activity: [
                { icon: 'file-text', text: 'Generated documentation for api.py', time: '2 min ago' },
                { icon: 'checklist', text: 'Quality analysis completed', time: '5 min ago' },
                { icon: 'shield', text: 'Security scan passed', time: '10 min ago' }
            ]
        };
        
        const panel = this.panels.get('dashboard');
        if (panel) {
            panel.webview.postMessage({
                command: 'update',
                data
            });
        }
    }
    
    /**
     * Saves settings from webview
     */
    private async saveSettings(settings: any): Promise<void> {
        const config = vscode.workspace.getConfiguration('devdocai');
        
        for (const key in settings) {
            await config.update(key, settings[key], vscode.ConfigurationTarget.Global);
        }
        
        vscode.window.showInformationMessage('Settings saved successfully');
    }
    
    /**
     * Resets settings to defaults
     */
    private async resetSettings(): Promise<void> {
        const config = vscode.workspace.getConfiguration('devdocai');
        
        // Get all configuration keys
        const keys = Object.keys(config);
        
        for (const key of keys) {
            await config.update(key, undefined, vscode.ConfigurationTarget.Global);
        }
        
        vscode.window.showInformationMessage('Settings reset to defaults');
    }
    
    /**
     * Disposes all webview panels
     */
    public async dispose(): Promise<void> {
        for (const panel of this.panels.values()) {
            panel.dispose();
        }
        
        this.panels.clear();
        
        for (const disposable of this.disposables) {
            disposable.dispose();
        }
        
        this.disposables = [];
    }
}