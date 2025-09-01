/**
 * DevDocAI VS Code Extension - Optimized Entry Point
 * 
 * Performance optimizations:
 * - Lazy loading for <100ms activation
 * - Phased initialization
 * - Dynamic imports for heavy modules
 * - Service locator pattern
 * 
 * @module M013-VSCodeExtension
 * @version 3.0.0
 */

import * as vscode from 'vscode';
import { performance } from 'perf_hooks';

// Lightweight types only - no heavy imports
interface ServiceRegistry {
    commandManager?: any;
    cliService?: any;
    webviewManager?: any;
    statusBarManager?: any;
    configManager?: any;
    languageService?: any;
    logger?: any;
    providers?: Map<string, any>;
}

// Global service registry for lazy loading
const services: ServiceRegistry = {
    providers: new Map()
};

// Performance tracking
const perfMarks = new Map<string, number>();

/**
 * Phase 1: Critical activation (<50ms target)
 * Only register commands and essential UI
 */
export async function activate(context: vscode.ExtensionContext): Promise<void> {
    perfMarks.set('activation-start', performance.now());
    
    // Minimal logger initialization
    const { Logger } = await import('./utils/Logger');
    services.logger = new Logger('DevDocAI');
    services.logger.info('🚀 DevDocAI Extension - Phase 1 Activation');
    
    // Register commands with lazy handlers (no service initialization)
    registerLazyCommands(context);
    
    // Show status bar item immediately (visual feedback)
    const statusBarItem = vscode.window.createStatusBarItem(
        vscode.StatusBarAlignment.Left,
        100
    );
    statusBarItem.text = '$(loading~spin) DevDocAI';
    statusBarItem.tooltip = 'DevDocAI is initializing...';
    statusBarItem.show();
    context.subscriptions.push(statusBarItem);
    
    // Store context for later use
    context.globalState.update('extensionContext', context);
    
    const phase1Time = performance.now() - perfMarks.get('activation-start')!;
    services.logger.info(`✅ Phase 1 complete in ${phase1Time.toFixed(2)}ms`);
    
    // Schedule Phase 2 initialization (non-blocking)
    setImmediate(() => initializePhase2(context, statusBarItem));
    
    // Return immediately for fast activation
    return Promise.resolve();
}

/**
 * Phase 2: Deferred initialization (background)
 * Initialize services as needed
 */
async function initializePhase2(
    context: vscode.ExtensionContext,
    statusBarItem: vscode.StatusBarItem
): Promise<void> {
    perfMarks.set('phase2-start', performance.now());
    
    try {
        // Update status bar
        statusBarItem.text = '$(sync~spin) DevDocAI';
        
        // Initialize config manager (lightweight)
        const { ConfigurationManager } = await import('./services/ConfigurationManager');
        services.configManager = new ConfigurationManager(context);
        await services.configManager.initialize();
        
        // Update status bar to ready
        statusBarItem.text = '$(check) DevDocAI';
        statusBarItem.tooltip = 'DevDocAI Ready';
        statusBarItem.command = 'devdocai.openDashboard';
        
        // Register lightweight event listeners
        registerDeferredEventListeners(context);
        
        const phase2Time = performance.now() - perfMarks.get('phase2-start')!;
        services.logger.info(`✅ Phase 2 complete in ${phase2Time.toFixed(2)}ms`);
        
        // Show welcome message if first activation
        const { ExtensionContext } = await import('./utils/ExtensionContext');
        const extensionContext = new ExtensionContext(context);
        if (extensionContext.isFirstActivation()) {
            showWelcomeMessage();
        }
        
    } catch (error) {
        services.logger?.error('Phase 2 initialization failed', error);
        statusBarItem.text = '$(error) DevDocAI';
        statusBarItem.tooltip = 'DevDocAI initialization failed';
    }
}

/**
 * Register commands with lazy loading handlers
 */
function registerLazyCommands(context: vscode.ExtensionContext): void {
    const commands = [
        {
            id: 'devdocai.generateDocumentation',
            handler: async (...args: any[]) => {
                await ensureCommandManager();
                return services.commandManager.executeCommand('generateDocumentation', ...args);
            }
        },
        {
            id: 'devdocai.analyzeQuality',
            handler: async (...args: any[]) => {
                await ensureCommandManager();
                return services.commandManager.executeCommand('analyzeQuality', ...args);
            }
        },
        {
            id: 'devdocai.runSecurityScan',
            handler: async (...args: any[]) => {
                await ensureCommandManager();
                return services.commandManager.executeCommand('runSecurityScan', ...args);
            }
        },
        {
            id: 'devdocai.openDashboard',
            handler: async () => {
                await ensureWebviewManager();
                return services.webviewManager.showDashboard();
            }
        },
        {
            id: 'devdocai.showMIAIRInsights',
            handler: async (...args: any[]) => {
                await ensureCommandManager();
                return services.commandManager.executeCommand('showMIAIRInsights', ...args);
            }
        },
        {
            id: 'devdocai.configureSettings',
            handler: async () => {
                await ensureWebviewManager();
                return services.webviewManager.showSettings();
            }
        },
        {
            id: 'devdocai.exportDocumentation',
            handler: async (...args: any[]) => {
                await ensureCommandManager();
                return services.commandManager.executeCommand('exportDocumentation', ...args);
            }
        },
        {
            id: 'devdocai.deleteDocumentation',
            handler: async (...args: any[]) => {
                await ensureCommandManager();
                return services.commandManager.executeCommand('deleteDocumentation', ...args);
            }
        },
        {
            id: 'devdocai.refreshProviders',
            handler: async () => {
                // Refresh all loaded providers
                for (const provider of services.providers?.values() || []) {
                    if (provider.refresh) {
                        provider.refresh();
                    }
                }
            }
        },
        {
            id: 'devdocai.showDocumentationPanel',
            handler: async (...args: any[]) => {
                await ensureWebviewManager();
                return services.webviewManager.showDocumentGenerator(...args);
            }
        }
    ];
    
    // Register all commands with lazy handlers
    for (const cmd of commands) {
        context.subscriptions.push(
            vscode.commands.registerCommand(cmd.id, cmd.handler)
        );
    }
}

/**
 * Register deferred event listeners (Phase 2)
 */
function registerDeferredEventListeners(context: vscode.ExtensionContext): void {
    // Configuration changes (lightweight)
    context.subscriptions.push(
        vscode.workspace.onDidChangeConfiguration(async (e) => {
            if (e.affectsConfiguration('devdocai')) {
                services.logger?.info('Configuration changed');
                
                // Only reload if services are initialized
                if (services.configManager) {
                    await services.configManager.reload();
                }
                if (services.cliService) {
                    await services.cliService.reload();
                }
                if (services.statusBarManager) {
                    services.statusBarManager.refresh();
                }
            }
        })
    );
    
    // Auto-documentation on save (deferred and debounced)
    let saveTimeout: NodeJS.Timeout;
    context.subscriptions.push(
        vscode.workspace.onDidSaveTextDocument(async (document) => {
            if (!services.configManager?.getConfig().autoDocumentation) {
                return;
            }
            
            const languages = ['python', 'typescript', 'javascript'];
            if (!languages.includes(document.languageId)) {
                return;
            }
            
            // Debounce rapid saves
            clearTimeout(saveTimeout);
            saveTimeout = setTimeout(async () => {
                services.logger?.info(`Auto-documentation for ${document.fileName}`);
                await ensureCommandManager();
                await services.commandManager.executeCommand(
                    'generateDocumentation',
                    document.uri
                );
            }, 1000); // 1 second debounce
        })
    );
    
    // Active editor changes (lightweight)
    context.subscriptions.push(
        vscode.window.onDidChangeActiveTextEditor((editor) => {
            if (editor && services.statusBarManager) {
                services.statusBarManager.updateForDocument(editor.document);
            }
        })
    );
}

/**
 * Lazy initialization helpers - Load services on demand
 */

async function ensureCLIService(): Promise<any> {
    if (!services.cliService) {
        perfMarks.set('cli-init-start', performance.now());
        
        const { CLIService } = await import('./services/CLIService');
        services.cliService = new CLIService(services.configManager!, services.logger!);
        
        // Use async initialization without blocking
        services.cliService.initialize().catch((error: any) => {
            services.logger?.error('CLI service initialization failed', error);
            vscode.window.showErrorMessage('DevDocAI CLI initialization failed');
        });
        
        const initTime = performance.now() - perfMarks.get('cli-init-start')!;
        services.logger?.info(`CLI service loaded in ${initTime.toFixed(2)}ms`);
    }
    
    // Wait for initialization if needed
    while (!services.cliService.isInitialized) {
        await new Promise(resolve => setTimeout(resolve, 100));
    }
    
    return services.cliService;
}

async function ensureWebviewManager(): Promise<any> {
    if (!services.webviewManager) {
        perfMarks.set('webview-init-start', performance.now());
        
        const { WebviewManager } = await import('./webviews/WebviewManager');
        const context = await vscode.commands.executeCommand('getContext');
        services.webviewManager = new WebviewManager(context as any, services.logger!);
        
        const initTime = performance.now() - perfMarks.get('webview-init-start')!;
        services.logger?.info(`Webview manager loaded in ${initTime.toFixed(2)}ms`);
    }
    
    return services.webviewManager;
}

async function ensureCommandManager(): Promise<any> {
    if (!services.commandManager) {
        perfMarks.set('cmd-init-start', performance.now());
        
        // Ensure dependencies
        await ensureCLIService();
        await ensureWebviewManager();
        
        const { CommandManager } = await import('./commands/CommandManager');
        const context = await vscode.commands.executeCommand('getContext');
        
        services.commandManager = new CommandManager(
            context as any,
            services.cliService!,
            services.webviewManager!,
            services.configManager!,
            services.logger!
        );
        
        services.commandManager.registerCommands();
        
        const initTime = performance.now() - perfMarks.get('cmd-init-start')!;
        services.logger?.info(`Command manager loaded in ${initTime.toFixed(2)}ms`);
    }
    
    return services.commandManager;
}

async function ensureStatusBarManager(): Promise<any> {
    if (!services.statusBarManager) {
        await ensureCLIService();
        
        const { StatusBarManager } = await import('./services/StatusBarManager');
        const context = await vscode.commands.executeCommand('getContext');
        
        services.statusBarManager = new StatusBarManager(
            context as any,
            services.cliService!,
            services.logger!
        );
        
        await services.statusBarManager.initialize();
    }
    
    return services.statusBarManager;
}

async function ensureLanguageService(): Promise<any> {
    if (!services.languageService) {
        await ensureCLIService();
        
        const { LanguageService } = await import('./services/LanguageService');
        const context = await vscode.commands.executeCommand('getContext');
        
        services.languageService = new LanguageService(
            context as any,
            services.cliService!,
            services.logger!
        );
        
        await services.languageService.initialize();
    }
    
    return services.languageService;
}

/**
 * Lazy provider registration - Only when tree view is expanded
 */
async function registerProvider(providerId: string, context: vscode.ExtensionContext): Promise<void> {
    if (services.providers?.has(providerId)) {
        return; // Already registered
    }
    
    await ensureCLIService();
    
    switch (providerId) {
        case 'devdocai.documents': {
            const { DocumentProvider } = await import('./providers/DocumentProvider');
            const provider = new DocumentProvider(services.cliService!, services.logger!);
            context.subscriptions.push(
                vscode.window.registerTreeDataProvider(providerId, provider)
            );
            services.providers?.set(providerId, provider);
            break;
        }
        case 'devdocai.quality': {
            const { QualityProvider } = await import('./providers/QualityProvider');
            const provider = new QualityProvider(services.cliService!, services.logger!);
            context.subscriptions.push(
                vscode.window.registerTreeDataProvider(providerId, provider)
            );
            services.providers?.set(providerId, provider);
            break;
        }
        case 'devdocai.templates': {
            const { TemplateProvider } = await import('./providers/TemplateProvider');
            const provider = new TemplateProvider(services.cliService!, services.logger!);
            context.subscriptions.push(
                vscode.window.registerTreeDataProvider(providerId, provider)
            );
            services.providers?.set(providerId, provider);
            break;
        }
    }
}

/**
 * Shows welcome message for first-time users
 */
function showWelcomeMessage(): void {
    const actions = [
        'Open Dashboard',
        'View Documentation',
        'Configure Settings'
    ];
    
    vscode.window.showInformationMessage(
        'Welcome to DevDocAI! Your AI-powered documentation assistant is ready.',
        ...actions
    ).then((selection) => {
        switch (selection) {
            case 'Open Dashboard':
                vscode.commands.executeCommand('devdocai.openDashboard');
                break;
            case 'View Documentation':
                vscode.env.openExternal(
                    vscode.Uri.parse('https://github.com/Org-EthereaLogic/DocDevAI-v3.0.0/wiki')
                );
                break;
            case 'Configure Settings':
                vscode.commands.executeCommand('devdocai.configureSettings');
                break;
        }
    });
}

/**
 * Deactivate extension - Clean disposal
 */
export async function deactivate(): Promise<void> {
    services.logger?.info('Deactivating DevDocAI extension');
    
    const disposalPromises: Promise<void>[] = [];
    
    // Dispose services if initialized
    if (services.cliService?.dispose) {
        disposalPromises.push(services.cliService.dispose());
    }
    if (services.webviewManager?.dispose) {
        disposalPromises.push(services.webviewManager.dispose());
    }
    if (services.statusBarManager?.dispose) {
        disposalPromises.push(services.statusBarManager.dispose());
    }
    if (services.languageService?.dispose) {
        disposalPromises.push(services.languageService.dispose());
    }
    
    await Promise.all(disposalPromises);
    
    // Log performance summary
    const totalTime = performance.now() - (perfMarks.get('activation-start') || 0);
    services.logger?.info(`Total session time: ${(totalTime / 1000).toFixed(2)}s`);
    services.logger?.info('DevDocAI extension deactivated');
}

/**
 * Register view visibility listeners for lazy provider loading
 */
vscode.window.onDidChangeTreeViewVisibility(async (e) => {
    if (e.visible && e.viewId.startsWith('devdocai.')) {
        const context = await vscode.commands.executeCommand('getContext');
        await registerProvider(e.viewId, context as any);
    }
});