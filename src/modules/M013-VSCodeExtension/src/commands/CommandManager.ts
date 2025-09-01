/**
 * Command Manager - Handles all VS Code extension commands
 * 
 * Registers and manages execution of all DevDocAI commands
 * accessible through the command palette, context menus, and keybindings.
 */

import * as vscode from 'vscode';
import { CLIService } from '../services/CLIService';
import { WebviewManager } from '../webviews/WebviewManager';
import { ConfigurationManager } from '../services/ConfigurationManager';
import { Logger } from '../utils/Logger';
import { GenerateDocumentationCommand } from './GenerateDocumentationCommand';
import { AnalyzeQualityCommand } from './AnalyzeQualityCommand';
import { OpenDashboardCommand } from './OpenDashboardCommand';
import { SelectTemplateCommand } from './SelectTemplateCommand';
import { ConfigureSettingsCommand } from './ConfigureSettingsCommand';
import { RunSecurityScanCommand } from './RunSecurityScanCommand';
import { ShowMIAIRInsightsCommand } from './ShowMIAIRInsightsCommand';

export class CommandManager {
    private commands: Map<string, Command>;
    
    constructor(
        private context: vscode.ExtensionContext,
        private cliService: CLIService,
        private webviewManager: WebviewManager,
        private configManager: ConfigurationManager,
        private logger: Logger
    ) {
        this.commands = new Map();
        this.initializeCommands();
    }
    
    /**
     * Initializes all command instances
     */
    private initializeCommands(): void {
        // Core commands
        this.commands.set(
            'devdocai.generateDocumentation',
            new GenerateDocumentationCommand(this.cliService, this.logger)
        );
        
        this.commands.set(
            'devdocai.analyzeQuality',
            new AnalyzeQualityCommand(this.cliService, this.logger)
        );
        
        this.commands.set(
            'devdocai.openDashboard',
            new OpenDashboardCommand(this.webviewManager, this.cliService, this.logger)
        );
        
        this.commands.set(
            'devdocai.selectTemplate',
            new SelectTemplateCommand(this.cliService, this.logger)
        );
        
        this.commands.set(
            'devdocai.configureSettings',
            new ConfigureSettingsCommand(this.configManager, this.logger)
        );
        
        this.commands.set(
            'devdocai.runSecurityScan',
            new RunSecurityScanCommand(this.cliService, this.logger)
        );
        
        this.commands.set(
            'devdocai.showMIAIRInsights',
            new ShowMIAIRInsightsCommand(this.cliService, this.webviewManager, this.logger)
        );
        
        // Additional commands
        this.registerSimpleCommands();
    }
    
    /**
     * Registers all commands with VS Code
     */
    public registerCommands(): void {
        // Register complex commands
        for (const [commandId, command] of this.commands) {
            const disposable = vscode.commands.registerCommand(
                commandId,
                async (...args: any[]) => {
                    try {
                        this.logger.info(`Executing command: ${commandId}`);
                        await command.execute(...args);
                    } catch (error) {
                        this.logger.error(`Command ${commandId} failed`, error);
                        vscode.window.showErrorMessage(
                            `Command failed: ${error instanceof Error ? error.message : 'Unknown error'}`
                        );
                    }
                }
            );
            this.context.subscriptions.push(disposable);
        }
        
        this.logger.info(`Registered ${this.commands.size} commands`);
    }
    
    /**
     * Registers simple commands that don't need their own class
     */
    private registerSimpleCommands(): void {
        // Refresh documentation
        this.commands.set('devdocai.refreshDocumentation', {
            execute: async () => {
                const editor = vscode.window.activeTextEditor;
                if (!editor) {
                    vscode.window.showWarningMessage('No active editor');
                    return;
                }
                
                await vscode.window.withProgress({
                    location: vscode.ProgressLocation.Notification,
                    title: 'Refreshing documentation...',
                    cancellable: false
                }, async (progress) => {
                    progress.report({ increment: 0 });
                    
                    // Delete existing documentation
                    progress.report({ increment: 30, message: 'Removing old documentation...' });
                    await this.cliService.deleteDocumentation(editor.document.uri.fsPath);
                    
                    // Generate new documentation
                    progress.report({ increment: 60, message: 'Generating new documentation...' });
                    const result = await this.cliService.generateDocumentation(
                        editor.document.uri.fsPath,
                        this.configManager.getConfig().defaultTemplate
                    );
                    
                    progress.report({ increment: 100, message: 'Complete!' });
                    
                    if (result.success) {
                        vscode.window.showInformationMessage('Documentation refreshed successfully');
                    }
                });
            }
        });
        
        // Export documentation
        this.commands.set('devdocai.exportDocumentation', {
            execute: async () => {
                const formats = ['Markdown', 'HTML', 'PDF', 'JSON'];
                const format = await vscode.window.showQuickPick(formats, {
                    placeHolder: 'Select export format'
                });
                
                if (!format) {
                    return;
                }
                
                const uri = await vscode.window.showSaveDialog({
                    defaultUri: vscode.Uri.file(`documentation.${format.toLowerCase()}`),
                    filters: {
                        [format]: [format.toLowerCase()]
                    }
                });
                
                if (!uri) {
                    return;
                }
                
                await vscode.window.withProgress({
                    location: vscode.ProgressLocation.Notification,
                    title: `Exporting documentation as ${format}...`,
                    cancellable: false
                }, async () => {
                    const result = await this.cliService.exportDocumentation(
                        vscode.workspace.workspaceFolders?.[0]?.uri.fsPath || '.',
                        uri.fsPath,
                        format.toLowerCase()
                    );
                    
                    if (result.success) {
                        vscode.window.showInformationMessage(
                            `Documentation exported to ${uri.fsPath}`
                        );
                    }
                });
            }
        });
        
        // Toggle auto documentation
        this.commands.set('devdocai.toggleAutoDoc', {
            execute: async () => {
                const current = this.configManager.getConfig().autoDocumentation;
                await this.configManager.updateConfig('autoDocumentation', !current);
                
                const status = !current ? 'enabled' : 'disabled';
                vscode.window.showInformationMessage(
                    `Auto documentation ${status}`
                );
                
                // Update status bar
                vscode.commands.executeCommand('devdocai.refreshStatus');
            }
        });
    }
    
    /**
     * Executes a command by ID
     */
    public async executeCommand(commandId: string, ...args: any[]): Promise<void> {
        const command = this.commands.get(commandId);
        if (command) {
            await command.execute(...args);
        } else {
            throw new Error(`Unknown command: ${commandId}`);
        }
    }
}

/**
 * Base interface for commands
 */
export interface Command {
    execute(...args: any[]): Promise<void>;
}