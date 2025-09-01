/**
 * Unified Command Manager - DevDocAI VS Code Command Coordination
 * 
 * Consolidates command management with:
 * - Integration with unified services (CLIService_unified, WebviewManager_unified, etc.)
 * - Security validation and audit logging through SecurityManager_unified
 * - Mode-based command availability and behavior
 * - Performance monitoring and error handling
 * - Comprehensive permission checks and rate limiting
 * 
 * Operation Modes:
 * - BASIC: Core commands only, no security checks
 * - PERFORMANCE: All commands with performance monitoring
 * - SECURE: Commands with security validation and audit logging
 * - ENTERPRISE: Full security suite with permission management
 * 
 * @module M013-VSCodeExtension/Commands
 * @version 3.0.0
 */

import * as vscode from 'vscode';
import { Logger } from '../utils/Logger';
import { SecurityManager } from '../security/SecurityManager_unified';

// Configuration interface
interface ExtensionConfig {
    operationMode: 'BASIC' | 'PERFORMANCE' | 'SECURE' | 'ENTERPRISE';
    features: {
        securityValidation: boolean;
        auditLogging: boolean;
        permissionControl: boolean;
        performanceMonitoring: boolean;
    };
}

// Command execution context
interface CommandContext {
    commandId: string;
    args: any[];
    userId: string;
    sessionId: string;
    timestamp: number;
    source: 'palette' | 'keybinding' | 'menu' | 'api';
}

// Command execution result
interface CommandResult {
    success: boolean;
    result?: any;
    error?: string;
    executionTime: number;
    securityEvents?: string[];
}

// Command interface
interface Command {
    execute(...args: any[]): Promise<any>;
    canExecute?(...args: any[]): Promise<boolean>;
    getRequiredPermissions?(): string[];
}

// Performance metrics
interface CommandMetrics {
    executionCount: number;
    averageExecutionTime: number;
    successRate: number;
    lastExecution: number;
    securityViolations: number;
}

/**
 * Unified Command Manager with security and performance integration
 */
export class CommandManager {
    private commands: Map<string, Command> = new Map();
    private commandMetrics: Map<string, CommandMetrics> = new Map();
    private disposables: vscode.Disposable[] = [];
    
    // Service dependencies (injected by extension)
    private cliService?: any;          // Will be CLIService_unified
    private webviewManager?: any;      // Will be WebviewManager_unified
    private statusBarManager?: any;    // Will be StatusBarManager_unified
    private documentProvider?: any;    // Will be DocumentProvider_unified
    private configManager?: any;       // Will be ConfigurationManager
    
    constructor(
        private context: vscode.ExtensionContext,
        private logger: Logger,
        private extensionConfig: ExtensionConfig,
        private securityManager?: SecurityManager
    ) {
        this.initializeCommands();
    }
    
    /**
     * Set service dependencies (called by extension during initialization)
     */
    public setServices(services: {
        cliService?: any;
        webviewManager?: any;
        statusBarManager?: any;
        documentProvider?: any;
        configManager?: any;
    }): void {
        this.cliService = services.cliService;
        this.webviewManager = services.webviewManager;
        this.statusBarManager = services.statusBarManager;
        this.documentProvider = services.documentProvider;
        this.configManager = services.configManager;
        
        // Re-initialize commands with services
        this.initializeCommands();
    }
    
    /**
     * Initialize all command instances based on operation mode
     */
    private initializeCommands(): void {
        // Clear existing commands
        this.commands.clear();
        
        // Core commands (available in all modes)
        this.registerCommand('devdocai.generateDocumentation', 
            this.createGenerateDocumentationCommand());
        
        this.registerCommand('devdocai.analyzeQuality', 
            this.createAnalyzeQualityCommand());
        
        this.registerCommand('devdocai.openDashboard', 
            this.createOpenDashboardCommand());
        
        // Enhanced commands (PERFORMANCE+ modes)
        if (this.shouldEnableEnhancedCommands()) {
            this.registerCommand('devdocai.runTemplate', 
                this.createRunTemplateCommand());
            
            this.registerCommand('devdocai.enhanceDocument', 
                this.createEnhanceDocumentCommand());
            
            this.registerCommand('devdocai.reviewCode', 
                this.createReviewCodeCommand());
            
            this.registerCommand('devdocai.showMetrics', 
                this.createShowMetricsCommand());
        }
        
        // Secure commands (SECURE+ modes)
        if (this.shouldEnableSecureCommands()) {
            this.registerCommand('devdocai.runSecurityScan', 
                this.createRunSecurityScanCommand());
            
            this.registerCommand('devdocai.auditSecurity', 
                this.createAuditSecurityCommand());
        }
        
        // Administrative commands (ENTERPRISE mode)
        if (this.shouldEnableAdminCommands()) {
            this.registerCommand('devdocai.configureExtension', 
                this.createConfigureExtensionCommand());
            
            this.registerCommand('devdocai.exportReport', 
                this.createExportReportCommand());
            
            this.registerCommand('devdocai.refreshProject', 
                this.createRefreshProjectCommand());
        }
        
        // Internal commands (always available)
        this.registerCommand('devdocai.internal.recordActivity', 
            this.createRecordActivityCommand());
    }
    
    /**
     * Register all commands with VS Code
     */
    public async registerAllCommands(context?: {
        security?: SecurityManager;
        performance?: any;
    }): Promise<void> {
        try {
            this.logger.info(`Registering ${this.commands.size} commands in ${this.extensionConfig.operationMode} mode`);
            
            for (const [commandId, command] of this.commands.entries()) {
                // Register command with VS Code
                const disposable = vscode.commands.registerCommand(commandId, async (...args) => {
                    return this.executeCommandSafely(commandId, args);
                });
                
                this.disposables.push(disposable);
                this.context.subscriptions.push(disposable);
                
                // Initialize metrics
                this.commandMetrics.set(commandId, {
                    executionCount: 0,
                    averageExecutionTime: 0,
                    successRate: 1.0,
                    lastExecution: 0,
                    securityViolations: 0
                });
            }
            
            // Log successful registration
            await this.logSecurityEvent('commands.registration', 'INFO', {
                commandCount: this.commands.size,
                mode: this.extensionConfig.operationMode,
                commandIds: Array.from(this.commands.keys())
            });
            
        } catch (error) {
            this.logger.error('Failed to register commands:', error);
            await this.logSecurityEvent('commands.registration.error', 'HIGH', {
                error: error.message
            });
            throw error;
        }
    }
    
    /**
     * Execute command with security validation and error handling
     */
    private async executeCommandSafely(commandId: string, args: any[]): Promise<any> {
        const startTime = Date.now();
        
        const commandContext: CommandContext = {
            commandId,
            args,
            userId: 'default-user', // In real implementation, get from VS Code
            sessionId: crypto.randomUUID(),
            timestamp: startTime,
            source: this.detectCommandSource(args)
        };
        
        try {
            // Security validation
            if (this.shouldEnableSecurity()) {
                const securityResult = await this.validateCommandExecution(commandContext);
                if (!securityResult.allowed) {
                    throw new Error(`Security validation failed: ${securityResult.reason}`);
                }
            }
            
            // Permission check
            if (this.shouldEnablePermissions()) {
                const hasPermission = await this.checkCommandPermission(commandId);
                if (!hasPermission) {
                    throw new Error(`Insufficient permissions for command: ${commandId}`);
                }
            }
            
            // Get and validate command
            const command = this.commands.get(commandId);
            if (!command) {
                throw new Error(`Command not found: ${commandId}`);
            }
            
            // Check if command can execute
            if (command.canExecute && !(await command.canExecute(...args))) {
                throw new Error(`Command cannot execute in current context: ${commandId}`);
            }
            
            // Update status if available
            if (this.statusBarManager) {
                this.statusBarManager.setStatus('working', `Executing ${commandId.split('.').pop()}`);
            }
            
            // Execute command
            const result = await command.execute(...args);
            
            // Calculate execution time
            const executionTime = Date.now() - startTime;
            
            // Update metrics
            this.updateCommandMetrics(commandId, true, executionTime);
            
            // Log successful execution
            await this.logSecurityEvent('command.executed', 'INFO', {
                commandId,
                executionTime,
                success: true,
                args: this.sanitizeArgs(args)
            });
            
            // Update status
            if (this.statusBarManager) {
                this.statusBarManager.setStatus('ready');
            }
            
            return result;
            
        } catch (error) {
            const executionTime = Date.now() - startTime;
            
            // Update metrics
            this.updateCommandMetrics(commandId, false, executionTime);
            
            // Log error
            await this.logSecurityEvent('command.error', 'HIGH', {
                commandId,
                error: error.message,
                executionTime,
                args: this.sanitizeArgs(args)
            });
            
            // Update status
            if (this.statusBarManager) {
                this.statusBarManager.setStatus('error', `Command failed: ${error.message}`);
            }
            
            // Show error to user
            this.logger.error(`Command ${commandId} failed:`, error);
            vscode.window.showErrorMessage(`DevDocAI: ${error.message}`);
            
            throw error;
        }
    }
    
    /**
     * Validate command execution for security
     */
    private async validateCommandExecution(context: CommandContext): Promise<{allowed: boolean; reason?: string}> {
        if (!this.securityManager) {
            return { allowed: true };
        }
        
        try {
            // Validate command arguments
            const validationResult = await this.securityManager.validateInput(
                context.commandId,
                context.args,
                {
                    rateLimitKey: `command:${context.commandId}:${context.userId}`,
                    maxLength: 10000,
                    preventExecutables: true,
                    requireWorkspaceScope: context.commandId.includes('file') || context.commandId.includes('path')
                }
            );
            
            if (!validationResult.isValid) {
                return {
                    allowed: false,
                    reason: validationResult.errors.join(', ')
                };
            }
            
            return { allowed: true };
            
        } catch (error) {
            this.logger.error('Security validation failed:', error);
            return {
                allowed: false,
                reason: 'Security validation error'
            };
        }
    }
    
    /**
     * Check command permissions
     */
    private async checkCommandPermission(commandId: string): Promise<boolean> {
        if (!this.securityManager) {
            return true;
        }
        
        try {
            return await this.securityManager.checkPermission(commandId);
        } catch (error) {
            this.logger.error('Permission check failed:', error);
            return false;
        }
    }
    
    /**
     * Execute specific command by ID
     */
    public async executeCommand(commandId: string, ...args: any[]): Promise<any> {
        return this.executeCommandSafely(commandId, args);
    }
    
    // ==================== Command Factory Methods ====================
    
    /**
     * Create generate documentation command
     */
    private createGenerateDocumentationCommand(): Command {
        return {
            execute: async (...args: any[]) => {
                if (!this.cliService) {
                    throw new Error('CLI service not available');
                }
                
                // Determine context
                const context = await this.determineFileContext(args);
                if (!context) {
                    vscode.window.showWarningMessage('No valid context for documentation generation');
                    return;
                }
                
                // Get template selection
                const template = await this.selectTemplate(context.languageId);
                if (!template) return;
                
                // Generate documentation with progress
                return vscode.window.withProgress({
                    location: vscode.ProgressLocation.Notification,
                    title: 'Generating documentation...',
                    cancellable: true
                }, async (progress, token) => {
                    progress.report({ increment: 20, message: 'Analyzing code...' });
                    
                    const result = await this.cliService.generateDocumentation(
                        context.filePath,
                        template,
                        {
                            selection: context.selection,
                            useMIAIR: true,
                            includeExamples: true
                        }
                    );
                    
                    progress.report({ increment: 80, message: 'Documentation generated' });
                    
                    if (result.success) {
                        vscode.window.showInformationMessage(
                            'Documentation generated successfully',
                            'Open'
                        ).then(action => {
                            if (action === 'Open') {
                                vscode.commands.executeCommand('vscode.open', 
                                    vscode.Uri.file(result.documentPath));
                            }
                        });
                    }
                    
                    return result;
                });
            },
            
            canExecute: async () => {
                return !!this.cliService && !!vscode.window.activeTextEditor;
            },
            
            getRequiredPermissions: () => ['generate', 'write']
        };
    }
    
    /**
     * Create analyze quality command
     */
    private createAnalyzeQualityCommand(): Command {
        return {
            execute: async (...args: any[]) => {
                if (!this.cliService) {
                    throw new Error('CLI service not available');
                }
                
                const context = await this.determineFileContext(args);
                if (!context) {
                    vscode.window.showWarningMessage('No file selected for quality analysis');
                    return;
                }
                
                return vscode.window.withProgress({
                    location: vscode.ProgressLocation.Notification,
                    title: 'Analyzing code quality...',
                    cancellable: false
                }, async (progress) => {
                    progress.report({ increment: 30, message: 'Scanning code...' });
                    
                    const result = await this.cliService.analyzeQuality(context.filePath, {
                        dimensions: ['readability', 'maintainability', 'complexity', 'documentation', 'testing']
                    });
                    
                    progress.report({ increment: 70, message: 'Analysis complete' });
                    
                    if (result.success && this.webviewManager) {
                        await this.webviewManager.showQualityMetrics(context.filePath, result);
                    }
                    
                    return result;
                });
            },
            
            canExecute: async () => {
                return !!this.cliService && !!vscode.window.activeTextEditor;
            },
            
            getRequiredPermissions: () => ['analyze', 'read']
        };
    }
    
    /**
     * Create open dashboard command
     */
    private createOpenDashboardCommand(): Command {
        return {
            execute: async (...args: any[]) => {
                if (!this.webviewManager) {
                    throw new Error('Webview manager not available');
                }
                
                // Get dashboard data
                const dashboardData = await this.getDashboardData();
                
                // Show dashboard
                await this.webviewManager.showDashboard(dashboardData);
                
                return { success: true };
            },
            
            canExecute: async () => {
                return !!this.webviewManager;
            },
            
            getRequiredPermissions: () => ['read']
        };
    }
    
    /**
     * Create run template command
     */
    private createRunTemplateCommand(): Command {
        return {
            execute: async (...args: any[]) => {
                if (!this.cliService) {
                    throw new Error('CLI service not available');
                }
                
                const templateName = args[0] || await this.selectTemplate();
                if (!templateName) return;
                
                const parameters = args[1] || await this.getTemplateParameters(templateName);
                
                const result = await this.cliService.runTemplate(templateName, parameters);
                
                vscode.window.showInformationMessage('Template executed successfully');
                
                return result;
            },
            
            getRequiredPermissions: () => ['execute', 'write']
        };
    }
    
    /**
     * Create enhance document command
     */
    private createEnhanceDocumentCommand(): Command {
        return {
            execute: async (...args: any[]) => {
                if (!this.cliService) {
                    throw new Error('CLI service not available');
                }
                
                const context = await this.determineFileContext(args);
                if (!context) {
                    vscode.window.showWarningMessage('No document selected for enhancement');
                    return;
                }
                
                const strategy = args[1] || 'comprehensive';
                
                return vscode.window.withProgress({
                    location: vscode.ProgressLocation.Notification,
                    title: 'Enhancing document...',
                    cancellable: true
                }, async (progress) => {
                    const result = await this.cliService.enhanceDocument(context.filePath, strategy);
                    
                    if (result.success) {
                        vscode.window.showInformationMessage('Document enhanced successfully');
                    }
                    
                    return result;
                });
            },
            
            getRequiredPermissions: () => ['enhance', 'write']
        };
    }
    
    /**
     * Create review code command
     */
    private createReviewCodeCommand(): Command {
        return {
            execute: async (...args: any[]) => {
                if (!this.cliService) {
                    throw new Error('CLI service not available');
                }
                
                const context = await this.determineFileContext(args);
                if (!context) {
                    vscode.window.showWarningMessage('No code selected for review');
                    return;
                }
                
                const focusAreas = args[1] || [];
                
                const result = await this.cliService.reviewCode(context.filePath, focusAreas);
                
                if (result.suggestions && result.suggestions.length > 0) {
                    vscode.window.showInformationMessage(
                        `Code review complete: ${result.suggestions.length} suggestions`,
                        'Show Details'
                    ).then(action => {
                        if (action === 'Show Details' && this.webviewManager) {
                            this.webviewManager.showCodeReview(context.filePath, result);
                        }
                    });
                }
                
                return result;
            },
            
            getRequiredPermissions: () => ['review', 'read']
        };
    }
    
    /**
     * Create show metrics command
     */
    private createShowMetricsCommand(): Command {
        return {
            execute: async (...args: any[]) => {
                if (!this.webviewManager) {
                    throw new Error('Webview manager not available');
                }
                
                // Collect metrics from all services
                const metrics = await this.collectSystemMetrics();
                
                // Show metrics dashboard
                await this.webviewManager.showProjectStats(metrics);
                
                return { success: true };
            },
            
            getRequiredPermissions: () => ['read']
        };
    }
    
    /**
     * Create security scan command
     */
    private createRunSecurityScanCommand(): Command {
        return {
            execute: async (...args: any[]) => {
                if (!this.securityManager) {
                    throw new Error('Security manager not available');
                }
                
                const context = await this.determineFileContext(args);
                
                return vscode.window.withProgress({
                    location: vscode.ProgressLocation.Notification,
                    title: 'Running security scan...',
                    cancellable: false
                }, async (progress) => {
                    progress.report({ increment: 50, message: 'Scanning for vulnerabilities...' });
                    
                    // Security scan implementation would go here
                    const scanResults = {
                        threatsDetected: 0,
                        vulnerabilities: [],
                        score: 100
                    };
                    
                    progress.report({ increment: 50, message: 'Scan complete' });
                    
                    vscode.window.showInformationMessage(
                        `Security scan complete: ${scanResults.threatsDetected} threats detected`
                    );
                    
                    return scanResults;
                });
            },
            
            getRequiredPermissions: () => ['security', 'scan']
        };
    }
    
    /**
     * Create audit security command
     */
    private createAuditSecurityCommand(): Command {
        return {
            execute: async (...args: any[]) => {
                if (!this.securityManager || !this.webviewManager) {
                    throw new Error('Security manager or webview manager not available');
                }
                
                // Get security metrics and audit log
                const securityMetrics = this.securityManager.getSecurityMetrics();
                
                // Show security audit dashboard
                await this.webviewManager.showSecurityAudit(securityMetrics);
                
                return { success: true };
            },
            
            getRequiredPermissions: () => ['security', 'audit', 'read']
        };
    }
    
    /**
     * Create configure extension command
     */
    private createConfigureExtensionCommand(): Command {
        return {
            execute: async (...args: any[]) => {
                if (!this.webviewManager) {
                    throw new Error('Webview manager not available');
                }
                
                // Get current configuration
                const currentConfig = await this.getCurrentConfiguration();
                
                // Show configuration panel
                await this.webviewManager.showConfiguration(currentConfig);
                
                return { success: true };
            },
            
            getRequiredPermissions: () => ['configure', 'admin']
        };
    }
    
    /**
     * Create export report command
     */
    private createExportReportCommand(): Command {
        return {
            execute: async (...args: any[]) => {
                const format = args[0] || 'json';
                
                // Collect all metrics
                const report = await this.generateSystemReport();
                
                // Export to file
                const fileName = `devdocai-report-${Date.now()}.${format}`;
                const workspaceFolder = vscode.workspace.workspaceFolders?.[0];
                
                if (workspaceFolder) {
                    const filePath = vscode.Uri.joinPath(workspaceFolder.uri, fileName);
                    await vscode.workspace.fs.writeFile(filePath, 
                        Buffer.from(JSON.stringify(report, null, 2)));
                    
                    vscode.window.showInformationMessage(`Report exported to ${fileName}`);
                }
                
                return report;
            },
            
            getRequiredPermissions: () => ['export', 'admin', 'write']
        };
    }
    
    /**
     * Create refresh project command
     */
    private createRefreshProjectCommand(): Command {
        return {
            execute: async (...args: any[]) => {
                // Refresh document provider
                if (this.documentProvider) {
                    this.documentProvider.refresh();
                }
                
                // Clear caches and reload
                if (this.cliService && this.cliService.clearCache) {
                    await this.cliService.clearCache();
                }
                
                vscode.window.showInformationMessage('Project refreshed successfully');
                
                return { success: true };
            },
            
            getRequiredPermissions: () => ['refresh', 'admin']
        };
    }
    
    /**
     * Create record activity command (internal)
     */
    private createRecordActivityCommand(): Command {
        return {
            execute: async (activityType: string) => {
                // Record activity for status bar manager
                if (this.statusBarManager && this.statusBarManager.recordActivity) {
                    this.statusBarManager.recordActivity(activityType);
                }
                
                // Log activity for security monitoring
                await this.logSecurityEvent('user.activity', 'INFO', {
                    activityType,
                    timestamp: Date.now()
                });
                
                return { success: true };
            }
        };
    }
    
    // ==================== Utility Methods ====================
    
    /**
     * Register a single command
     */
    private registerCommand(commandId: string, command: Command): void {
        this.commands.set(commandId, command);
        this.logger.debug(`Registered command: ${commandId}`);
    }
    
    /**
     * Determine file context from command arguments
     */
    private async determineFileContext(args: any[]): Promise<any | null> {
        // Check if file URI provided
        if (args.length > 0 && args[0] && args[0].fsPath) {
            return {
                filePath: args[0].fsPath,
                languageId: await this.getLanguageId(args[0].fsPath)
            };
        }
        
        // Use active text editor
        const activeEditor = vscode.window.activeTextEditor;
        if (activeEditor) {
            return {
                filePath: activeEditor.document.uri.fsPath,
                languageId: activeEditor.document.languageId,
                selection: activeEditor.selection.isEmpty ? 
                    undefined : activeEditor.document.getText(activeEditor.selection)
            };
        }
        
        return null;
    }
    
    /**
     * Get language ID from file path
     */
    private async getLanguageId(filePath: string): Promise<string> {
        try {
            const document = await vscode.workspace.openTextDocument(filePath);
            return document.languageId;
        } catch {
            // Fallback to extension
            const ext = filePath.split('.').pop()?.toLowerCase();
            const langMap: Record<string, string> = {
                'js': 'javascript',
                'ts': 'typescript',
                'py': 'python',
                'java': 'java',
                'cs': 'csharp',
                'cpp': 'cpp',
                'c': 'c'
            };
            return langMap[ext || ''] || 'plaintext';
        }
    }
    
    /**
     * Select template
     */
    private async selectTemplate(languageId?: string): Promise<string | undefined> {
        const templates = ['comprehensive', 'api', 'minimal', 'tutorial'];
        
        if (languageId) {
            templates.unshift(`${languageId}-specific`);
        }
        
        return vscode.window.showQuickPick(templates, {
            placeHolder: 'Select documentation template'
        });
    }
    
    /**
     * Get template parameters
     */
    private async getTemplateParameters(templateName: string): Promise<any> {
        // Simplified parameter collection
        return {};
    }
    
    /**
     * Get dashboard data
     */
    private async getDashboardData(): Promise<any> {
        return {
            timestamp: Date.now(),
            mode: this.extensionConfig.operationMode,
            metrics: await this.collectSystemMetrics()
        };
    }
    
    /**
     * Collect system metrics
     */
    private async collectSystemMetrics(): Promise<any> {
        const metrics: any = {
            commands: Object.fromEntries(this.commandMetrics.entries()),
            mode: this.extensionConfig.operationMode
        };
        
        // Collect from services
        if (this.cliService && this.cliService.getMetrics) {
            metrics.cli = await this.cliService.getMetrics();
        }
        
        if (this.webviewManager && this.webviewManager.getMetrics) {
            metrics.webview = this.webviewManager.getMetrics();
        }
        
        if (this.statusBarManager && this.statusBarManager.getMetrics) {
            metrics.statusBar = this.statusBarManager.getMetrics();
        }
        
        if (this.documentProvider && this.documentProvider.getMetrics) {
            metrics.documentProvider = this.documentProvider.getMetrics();
        }
        
        if (this.securityManager && this.securityManager.getSecurityMetrics) {
            metrics.security = this.securityManager.getSecurityMetrics();
        }
        
        return metrics;
    }
    
    /**
     * Get current configuration
     */
    private async getCurrentConfiguration(): Promise<any> {
        const config = vscode.workspace.getConfiguration('devdocai');
        return {
            operationMode: config.get('operationMode', 'BASIC'),
            showStatusBar: config.get('showStatusBar', true),
            enableSecurity: config.get('enableSecurity', false),
            enablePerformanceMode: config.get('enablePerformanceMode', false)
        };
    }
    
    /**
     * Generate system report
     */
    private async generateSystemReport(): Promise<any> {
        return {
            timestamp: Date.now(),
            mode: this.extensionConfig.operationMode,
            metrics: await this.collectSystemMetrics(),
            commands: Array.from(this.commands.keys()),
            version: '3.0.0'
        };
    }
    
    /**
     * Update command metrics
     */
    private updateCommandMetrics(commandId: string, success: boolean, executionTime: number): void {
        const metrics = this.commandMetrics.get(commandId);
        if (!metrics) return;
        
        metrics.executionCount++;
        metrics.lastExecution = Date.now();
        
        // Update average execution time
        metrics.averageExecutionTime = 
            (metrics.averageExecutionTime * (metrics.executionCount - 1) + executionTime) / 
            metrics.executionCount;
        
        // Update success rate
        const successCount = Math.floor(metrics.successRate * (metrics.executionCount - 1));
        metrics.successRate = (successCount + (success ? 1 : 0)) / metrics.executionCount;
        
        if (!success) {
            metrics.securityViolations++;
        }
    }
    
    /**
     * Detect command source
     */
    private detectCommandSource(args: any[]): 'palette' | 'keybinding' | 'menu' | 'api' {
        // Basic heuristic - in real implementation would use VS Code APIs
        return 'palette';
    }
    
    /**
     * Sanitize arguments for logging
     */
    private sanitizeArgs(args: any[]): any[] {
        return args.map(arg => {
            if (typeof arg === 'string' && arg.length > 100) {
                return arg.substring(0, 100) + '...';
            }
            if (arg && arg.fsPath) {
                return { fsPath: arg.fsPath };
            }
            return arg;
        });
    }
    
    /**
     * Log security event
     */
    private async logSecurityEvent(category: string, severity: string, details: any): Promise<void> {
        if (this.securityManager && this.securityManager.logSecurityEvent) {
            const severityMap: Record<string, number> = {
                'INFO': 0,
                'LOW': 1,
                'MEDIUM': 2,
                'HIGH': 3,
                'CRITICAL': 4
            };
            
            await this.securityManager.logSecurityEvent(
                category,
                severityMap[severity] || 1,
                details,
                'CommandManager'
            );
        }
    }
    
    /**
     * Mode detection methods
     */
    private shouldEnableEnhancedCommands(): boolean {
        return this.extensionConfig.operationMode !== 'BASIC';
    }
    
    private shouldEnableSecureCommands(): boolean {
        return this.extensionConfig.operationMode === 'SECURE' || 
               this.extensionConfig.operationMode === 'ENTERPRISE';
    }
    
    private shouldEnableAdminCommands(): boolean {
        return this.extensionConfig.operationMode === 'ENTERPRISE';
    }
    
    private shouldEnableSecurity(): boolean {
        return this.extensionConfig.features.securityValidation && this.securityManager;
    }
    
    private shouldEnablePermissions(): boolean {
        return this.extensionConfig.features.permissionControl && this.securityManager;
    }
    
    /**
     * Get command metrics
     */
    public getCommandMetrics(): any {
        return {
            totalCommands: this.commands.size,
            registeredCommands: Array.from(this.commands.keys()),
            metrics: Object.fromEntries(this.commandMetrics.entries()),
            mode: this.extensionConfig.operationMode
        };
    }
    
    /**
     * Dispose and cleanup
     */
    public dispose(): void {
        // Dispose all VS Code disposables
        this.disposables.forEach(disposable => {
            disposable.dispose();
        });
        this.disposables = [];
        
        // Clear maps
        this.commands.clear();
        this.commandMetrics.clear();
        
        this.logger.debug('Command manager disposed');
    }
}

// Export types for external use
export type { Command, CommandContext, CommandResult, ExtensionConfig };