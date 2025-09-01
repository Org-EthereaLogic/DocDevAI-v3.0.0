/**
 * DevDocAI VS Code Extension - Main Entry Point
 * 
 * This extension integrates DevDocAI's AI-powered documentation generation
 * and analysis capabilities directly into the VS Code IDE.
 * 
 * @module M013-VSCodeExtension
 * @version 3.0.0
 */

import * as vscode from 'vscode';
import { CommandManager } from './commands/CommandManager';
import { CLIService } from './services/CLIService';
import { WebviewManager } from './webviews/WebviewManager';
import { StatusBarManager } from './services/StatusBarManager';
import { DocumentProvider } from './providers/DocumentProvider';
import { QualityProvider } from './providers/QualityProvider';
import { TemplateProvider } from './providers/TemplateProvider';
import { ConfigurationManager } from './services/ConfigurationManager';
import { LanguageService } from './services/LanguageService';
import { Logger } from './utils/Logger';
import { ExtensionContext } from './utils/ExtensionContext';

// Extension state
let extensionContext: ExtensionContext;
let commandManager: CommandManager;
let cliService: CLIService;
let webviewManager: WebviewManager;
let statusBarManager: StatusBarManager;
let configManager: ConfigurationManager;
let languageService: LanguageService;
let logger: Logger;

/**
 * Activates the DevDocAI extension
 * Called when the extension is activated by VS Code
 */
export async function activate(context: vscode.ExtensionContext): Promise<void> {
    // Initialize logger
    logger = new Logger('DevDocAI');
    logger.info('Activating DevDocAI extension v3.0.0');

    try {
        // Initialize extension context
        extensionContext = new ExtensionContext(context);
        
        // Initialize configuration manager
        configManager = new ConfigurationManager(context);
        await configManager.initialize();
        
        // Initialize CLI service
        cliService = new CLIService(configManager, logger);
        await cliService.initialize();
        
        // Initialize webview manager
        webviewManager = new WebviewManager(context, logger);
        
        // Initialize status bar
        statusBarManager = new StatusBarManager(context, cliService, logger);
        await statusBarManager.initialize();
        
        // Initialize language service
        languageService = new LanguageService(context, cliService, logger);
        await languageService.initialize();
        
        // Initialize command manager and register commands
        commandManager = new CommandManager(
            context,
            cliService,
            webviewManager,
            configManager,
            logger
        );
        commandManager.registerCommands();
        
        // Register providers
        registerProviders(context);
        
        // Register event listeners
        registerEventListeners(context);
        
        // Show welcome message if first activation
        if (extensionContext.isFirstActivation()) {
            showWelcomeMessage();
        }
        
        // Update status bar
        statusBarManager.setStatus('ready', 'DevDocAI Ready');
        
        logger.info('DevDocAI extension activated successfully');
        
        // Report activation telemetry (if enabled)
        reportActivation();
        
    } catch (error) {
        logger.error('Failed to activate DevDocAI extension', error);
        vscode.window.showErrorMessage(
            `Failed to activate DevDocAI: ${error instanceof Error ? error.message : 'Unknown error'}`
        );
        throw error;
    }
}

/**
 * Deactivates the DevDocAI extension
 * Called when the extension is deactivated
 */
export async function deactivate(): Promise<void> {
    logger?.info('Deactivating DevDocAI extension');
    
    try {
        // Cleanup services
        await cliService?.dispose();
        await webviewManager?.dispose();
        await statusBarManager?.dispose();
        await languageService?.dispose();
        
        // Save state
        await extensionContext?.saveState();
        
        logger?.info('DevDocAI extension deactivated successfully');
    } catch (error) {
        logger?.error('Error during deactivation', error);
    }
}

/**
 * Registers all tree data providers
 */
function registerProviders(context: vscode.ExtensionContext): void {
    // Register document tree provider
    const documentProvider = new DocumentProvider(cliService, logger);
    context.subscriptions.push(
        vscode.window.registerTreeDataProvider('devdocai.documents', documentProvider)
    );
    
    // Register quality metrics provider
    const qualityProvider = new QualityProvider(cliService, logger);
    context.subscriptions.push(
        vscode.window.registerTreeDataProvider('devdocai.quality', qualityProvider)
    );
    
    // Register template provider
    const templateProvider = new TemplateProvider(cliService, logger);
    context.subscriptions.push(
        vscode.window.registerTreeDataProvider('devdocai.templates', templateProvider)
    );
    
    // Register code lens provider for documentation hints
    const codeLensProvider = new DocumentationCodeLensProvider(cliService, logger);
    context.subscriptions.push(
        vscode.languages.registerCodeLensProvider(
            [
                { language: 'python' },
                { language: 'typescript' },
                { language: 'javascript' }
            ],
            codeLensProvider
        )
    );
    
    // Register hover provider for quality insights
    const hoverProvider = new QualityHoverProvider(cliService, logger);
    context.subscriptions.push(
        vscode.languages.registerHoverProvider(
            { pattern: '**/*.md' },
            hoverProvider
        )
    );
}

/**
 * Registers event listeners
 */
function registerEventListeners(context: vscode.ExtensionContext): void {
    // Listen for configuration changes
    context.subscriptions.push(
        vscode.workspace.onDidChangeConfiguration(async (e) => {
            if (e.affectsConfiguration('devdocai')) {
                logger.info('Configuration changed, reloading settings');
                await configManager.reload();
                await cliService.reload();
                statusBarManager.refresh();
            }
        })
    );
    
    // Listen for document saves (for auto-documentation)
    context.subscriptions.push(
        vscode.workspace.onDidSaveTextDocument(async (document) => {
            if (configManager.getConfig().autoDocumentation) {
                const languages = ['python', 'typescript', 'javascript'];
                if (languages.includes(document.languageId)) {
                    logger.info(`Auto-generating documentation for ${document.fileName}`);
                    await commandManager.executeCommand('devdocai.generateDocumentation', document.uri);
                }
            }
        })
    );
    
    // Listen for active editor changes
    context.subscriptions.push(
        vscode.window.onDidChangeActiveTextEditor((editor) => {
            if (editor) {
                statusBarManager.updateForDocument(editor.document);
            }
        })
    );
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
 * Reports activation telemetry (privacy-first, opt-in only)
 */
function reportActivation(): void {
    if (configManager.getConfig().telemetryEnabled === true) {
        // Only report if explicitly enabled
        logger.info('Telemetry enabled, reporting activation');
        // Implementation would go here if telemetry is implemented
    }
}

/**
 * Code lens provider for documentation hints
 */
class DocumentationCodeLensProvider implements vscode.CodeLensProvider {
    constructor(
        private cliService: CLIService,
        private logger: Logger
    ) {}
    
    async provideCodeLenses(
        document: vscode.TextDocument,
        token: vscode.CancellationToken
    ): Promise<vscode.CodeLens[]> {
        const codeLenses: vscode.CodeLens[] = [];
        
        // Find functions/classes that need documentation
        const text = document.getText();
        const functionRegex = /^(async\s+)?function\s+(\w+)|^class\s+(\w+)|^def\s+(\w+)/gm;
        
        let match;
        while ((match = functionRegex.exec(text)) !== null) {
            const line = document.positionAt(match.index).line;
            const range = new vscode.Range(line, 0, line, 0);
            
            // Check if documentation exists
            const hasDoc = await this.checkDocumentation(document, line);
            
            if (!hasDoc) {
                const lens = new vscode.CodeLens(range, {
                    title: '$(file-text) Generate Documentation',
                    command: 'devdocai.generateDocumentation',
                    arguments: [document.uri, range]
                });
                codeLenses.push(lens);
            }
        }
        
        return codeLenses;
    }
    
    private async checkDocumentation(document: vscode.TextDocument, line: number): Promise<boolean> {
        // Check if there's a docstring/comment above the function/class
        if (line > 0) {
            const prevLine = document.lineAt(line - 1).text.trim();
            return prevLine.startsWith('"""') || 
                   prevLine.startsWith('/**') || 
                   prevLine.startsWith('#');
        }
        return false;
    }
}

/**
 * Hover provider for quality insights
 */
class QualityHoverProvider implements vscode.HoverProvider {
    constructor(
        private cliService: CLIService,
        private logger: Logger
    ) {}
    
    async provideHover(
        document: vscode.TextDocument,
        position: vscode.Position,
        token: vscode.CancellationToken
    ): Promise<vscode.Hover | undefined> {
        try {
            // Get quality metrics for the document
            const metrics = await this.cliService.analyzeQuality(document.uri.fsPath);
            
            if (metrics) {
                const markdown = new vscode.MarkdownString();
                markdown.appendMarkdown('### Documentation Quality\n\n');
                markdown.appendMarkdown(`**Overall Score**: ${metrics.score}/100\n\n`);
                markdown.appendMarkdown(`**Completeness**: ${metrics.completeness}%\n`);
                markdown.appendMarkdown(`**Clarity**: ${metrics.clarity}%\n`);
                markdown.appendMarkdown(`**Accuracy**: ${metrics.accuracy}%\n`);
                markdown.appendMarkdown(`**Maintainability**: ${metrics.maintainability}%\n\n`);
                
                if (metrics.suggestions && metrics.suggestions.length > 0) {
                    markdown.appendMarkdown('**Suggestions**:\n');
                    metrics.suggestions.forEach((suggestion: string) => {
                        markdown.appendMarkdown(`- ${suggestion}\n`);
                    });
                }
                
                return new vscode.Hover(markdown);
            }
        } catch (error) {
            this.logger.error('Failed to provide hover', error);
        }
        
        return undefined;
    }
}