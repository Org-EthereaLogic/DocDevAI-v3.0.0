/**
 * Configuration Manager for DevDocAI VS Code Extension
 * 
 * Manages extension settings and provides configuration access
 * to other services.
 */

import * as vscode from 'vscode';
import * as path from 'path';
import * as fs from 'fs';

export class ConfigurationManager {
    private config: DevDocAIConfig;
    private watchers: vscode.Disposable[] = [];
    
    constructor(private context: vscode.ExtensionContext) {
        this.config = this.loadConfiguration();
    }
    
    /**
     * Initializes the configuration manager
     */
    public async initialize(): Promise<void> {
        // Watch for configuration changes
        this.watchers.push(
            vscode.workspace.onDidChangeConfiguration((e) => {
                if (e.affectsConfiguration('devdocai')) {
                    this.config = this.loadConfiguration();
                }
            })
        );
        
        // Check for workspace-specific configuration
        await this.loadWorkspaceConfig();
    }
    
    /**
     * Gets the current configuration
     */
    public getConfig(): DevDocAIConfig {
        return { ...this.config };
    }
    
    /**
     * Updates a configuration value
     */
    public async updateConfig(key: string, value: any): Promise<void> {
        const config = vscode.workspace.getConfiguration('devdocai');
        await config.update(key, value, vscode.ConfigurationTarget.Global);
        
        // Update local cache
        (this.config as any)[key] = value;
    }
    
    /**
     * Gets a specific configuration value
     */
    public get<T>(key: keyof DevDocAIConfig): T {
        return this.config[key] as T;
    }
    
    /**
     * Reloads the configuration
     */
    public async reload(): Promise<void> {
        this.config = this.loadConfiguration();
        await this.loadWorkspaceConfig();
    }
    
    /**
     * Loads configuration from VS Code settings
     */
    private loadConfiguration(): DevDocAIConfig {
        const vsConfig = vscode.workspace.getConfiguration('devdocai');
        
        return {
            operationMode: vsConfig.get('operationMode', 'BASIC'),
            autoDocumentation: vsConfig.get('autoDocumentation', false),
            cliPath: vsConfig.get('cliPath', ''),
            pythonPath: vsConfig.get('pythonPath', 'python'),
            showStatusBar: vsConfig.get('showStatusBar', true),
            defaultTemplate: vsConfig.get('defaultTemplate', 'module'),
            qualityThreshold: vsConfig.get('qualityThreshold', 70),
            enableMIAIR: vsConfig.get('enableMIAIR', true),
            enableSecurity: vsConfig.get('enableSecurity', true),
            enableLLM: vsConfig.get('enableLLM', false),
            llmProvider: vsConfig.get('llmProvider', 'local'),
            debug: vsConfig.get('debug', false),
            telemetryEnabled: vsConfig.get('telemetryEnabled', false),
            
            // Additional settings not exposed in package.json
            maxConcurrentOperations: vsConfig.get('maxConcurrentOperations', 3),
            cacheEnabled: vsConfig.get('cacheEnabled', true),
            cacheDirectory: vsConfig.get('cacheDirectory', ''),
            exportFormats: vsConfig.get('exportFormats', ['markdown', 'html', 'pdf']),
            languageSupport: vsConfig.get('languageSupport', [
                'python', 'typescript', 'javascript', 'java', 'c', 'cpp', 'csharp', 'go', 'rust'
            ]),
            customTemplatesPath: vsConfig.get('customTemplatesPath', ''),
            analysisDepth: vsConfig.get('analysisDepth', 'standard'),
            securityRules: vsConfig.get('securityRules', []),
            ignorePaths: vsConfig.get('ignorePaths', [
                '**/node_modules/**',
                '**/.git/**',
                '**/dist/**',
                '**/build/**',
                '**/__pycache__/**',
                '**/*.pyc'
            ])
        };
    }
    
    /**
     * Loads workspace-specific configuration
     */
    private async loadWorkspaceConfig(): Promise<void> {
        const workspaceFolder = vscode.workspace.workspaceFolders?.[0];
        if (!workspaceFolder) {
            return;
        }
        
        // Check for .devdocai.yml in workspace
        const configPath = path.join(workspaceFolder.uri.fsPath, '.devdocai.yml');
        
        if (fs.existsSync(configPath)) {
            try {
                const yaml = require('js-yaml');
                const content = fs.readFileSync(configPath, 'utf8');
                const workspaceConfig = yaml.load(content);
                
                // Merge workspace config with VS Code settings
                this.mergeConfig(workspaceConfig);
                
            } catch (error) {
                vscode.window.showWarningMessage(
                    `Failed to load .devdocai.yml: ${error instanceof Error ? error.message : 'Unknown error'}`
                );
            }
        }
    }
    
    /**
     * Merges workspace configuration with current config
     */
    private mergeConfig(workspaceConfig: any): void {
        if (!workspaceConfig) {
            return;
        }
        
        // Only override specific settings from workspace config
        const allowedOverrides = [
            'defaultTemplate',
            'qualityThreshold',
            'enableMIAIR',
            'analysisDepth',
            'ignorePaths',
            'customTemplatesPath'
        ];
        
        for (const key of allowedOverrides) {
            if (workspaceConfig[key] !== undefined) {
                (this.config as any)[key] = workspaceConfig[key];
            }
        }
    }
    
    /**
     * Validates the configuration
     */
    public validateConfig(): ConfigValidationResult {
        const errors: string[] = [];
        const warnings: string[] = [];
        
        // Check Python path
        if (!this.config.pythonPath) {
            errors.push('Python path is not configured');
        }
        
        // Check CLI path if custom path is specified
        if (this.config.cliPath && !fs.existsSync(this.config.cliPath)) {
            errors.push(`CLI path does not exist: ${this.config.cliPath}`);
        }
        
        // Check quality threshold
        if (this.config.qualityThreshold < 0 || this.config.qualityThreshold > 100) {
            warnings.push('Quality threshold should be between 0 and 100');
        }
        
        // Check operation mode
        const validModes = ['BASIC', 'PERFORMANCE', 'SECURE', 'ENTERPRISE'];
        if (!validModes.includes(this.config.operationMode)) {
            errors.push(`Invalid operation mode: ${this.config.operationMode}`);
        }
        
        // Check LLM configuration
        if (this.config.enableLLM && !this.hasLLMCredentials()) {
            warnings.push('LLM is enabled but no API credentials are configured');
        }
        
        return {
            valid: errors.length === 0,
            errors,
            warnings
        };
    }
    
    /**
     * Checks if LLM credentials are configured
     */
    private hasLLMCredentials(): boolean {
        const secrets = this.context.secrets;
        
        switch (this.config.llmProvider) {
            case 'openai':
                return this.context.globalState.get('openai_api_key') !== undefined;
            
            case 'anthropic':
                return this.context.globalState.get('anthropic_api_key') !== undefined;
            
            case 'google':
                return this.context.globalState.get('google_api_key') !== undefined;
            
            case 'local':
                return true; // Local doesn't need credentials
            
            default:
                return false;
        }
    }
    
    /**
     * Exports configuration to file
     */
    public async exportConfig(outputPath: string): Promise<void> {
        const configToExport = {
            ...this.config,
            // Exclude sensitive information
            cliPath: this.config.cliPath ? '<configured>' : '',
            pythonPath: this.config.pythonPath || '<default>'
        };
        
        const yaml = require('js-yaml');
        const content = yaml.dump(configToExport);
        
        fs.writeFileSync(outputPath, content, 'utf8');
    }
    
    /**
     * Imports configuration from file
     */
    public async importConfig(inputPath: string): Promise<void> {
        try {
            const yaml = require('js-yaml');
            const content = fs.readFileSync(inputPath, 'utf8');
            const importedConfig = yaml.load(content);
            
            // Update VS Code settings
            const vsConfig = vscode.workspace.getConfiguration('devdocai');
            
            for (const key in importedConfig) {
                if (key !== 'cliPath' && key !== 'pythonPath') {
                    await vsConfig.update(key, importedConfig[key], vscode.ConfigurationTarget.Global);
                }
            }
            
            // Reload configuration
            await this.reload();
            
            vscode.window.showInformationMessage('Configuration imported successfully');
            
        } catch (error) {
            vscode.window.showErrorMessage(
                `Failed to import configuration: ${error instanceof Error ? error.message : 'Unknown error'}`
            );
        }
    }
    
    /**
     * Disposes the configuration manager
     */
    public dispose(): void {
        for (const watcher of this.watchers) {
            watcher.dispose();
        }
        this.watchers = [];
    }
}

/**
 * DevDocAI configuration interface
 */
export interface DevDocAIConfig {
    operationMode: 'BASIC' | 'PERFORMANCE' | 'SECURE' | 'ENTERPRISE';
    autoDocumentation: boolean;
    cliPath: string;
    pythonPath: string;
    showStatusBar: boolean;
    defaultTemplate: string;
    qualityThreshold: number;
    enableMIAIR: boolean;
    enableSecurity: boolean;
    enableLLM: boolean;
    llmProvider: string;
    debug: boolean;
    telemetryEnabled?: boolean;
    maxConcurrentOperations: number;
    cacheEnabled: boolean;
    cacheDirectory: string;
    exportFormats: string[];
    languageSupport: string[];
    customTemplatesPath: string;
    analysisDepth: string;
    securityRules: string[];
    ignorePaths: string[];
}

/**
 * Configuration validation result
 */
interface ConfigValidationResult {
    valid: boolean;
    errors: string[];
    warnings: string[];
}