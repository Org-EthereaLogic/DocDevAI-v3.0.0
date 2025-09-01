/**
 * CLI Service - Integrates with M012 DevDocAI CLI
 * 
 * Manages communication with the Python-based DevDocAI backend
 * through the unified CLI interface (M012).
 */

import * as vscode from 'vscode';
import { spawn, ChildProcess } from 'child_process';
import * as path from 'path';
import { ConfigurationManager } from './ConfigurationManager';
import { Logger } from '../utils/Logger';
import { EventEmitter } from 'events';

export class CLIService extends EventEmitter {
    private cliProcess: ChildProcess | null = null;
    private pythonPath: string;
    private cliPath: string;
    private operationMode: string;
    private isInitialized: boolean = false;
    private commandQueue: CommandRequest[] = [];
    private isProcessing: boolean = false;
    
    constructor(
        private configManager: ConfigurationManager,
        private logger: Logger
    ) {
        super();
        this.pythonPath = this.configManager.getConfig().pythonPath || 'python';
        this.cliPath = this.resolveCLIPath();
        this.operationMode = this.configManager.getConfig().operationMode || 'BASIC';
    }
    
    /**
     * Initializes the CLI service
     */
    public async initialize(): Promise<void> {
        try {
            this.logger.info('Initializing CLI service');
            
            // Verify Python installation
            await this.verifyPython();
            
            // Verify CLI installation
            await this.verifyCLI();
            
            // Start CLI in daemon mode if performance mode
            if (this.operationMode === 'PERFORMANCE' || this.operationMode === 'ENTERPRISE') {
                await this.startDaemon();
            }
            
            this.isInitialized = true;
            this.logger.info('CLI service initialized successfully');
            
        } catch (error) {
            this.logger.error('Failed to initialize CLI service', error);
            throw error;
        }
    }
    
    /**
     * Generates documentation for a file or selection
     */
    public async generateDocumentation(
        filePath: string,
        template: string,
        options?: DocumentationOptions
    ): Promise<DocumentationResult> {
        this.ensureInitialized();
        
        const args = [
            'generate',
            filePath,
            '--template', template,
            '--mode', this.operationMode
        ];
        
        if (options?.selection) {
            args.push('--selection', options.selection);
        }
        
        if (options?.useMIAIR) {
            args.push('--miair');
        }
        
        if (options?.includeExamples) {
            args.push('--examples');
        }
        
        const result = await this.executeCommand(args);
        
        return {
            success: result.exitCode === 0,
            documentPath: result.output.documentPath || path.join(path.dirname(filePath), 'documentation.md'),
            content: result.output.content,
            metadata: result.output.metadata
        };
    }
    
    /**
     * Analyzes documentation quality
     */
    public async analyzeQuality(documentPath: string): Promise<QualityResult> {
        this.ensureInitialized();
        
        const args = [
            'analyze',
            documentPath,
            '--json',
            '--mode', this.operationMode
        ];
        
        const result = await this.executeCommand(args);
        
        return {
            score: result.output.score || 0,
            completeness: result.output.completeness || 0,
            clarity: result.output.clarity || 0,
            accuracy: result.output.accuracy || 0,
            maintainability: result.output.maintainability || 0,
            suggestions: result.output.suggestions || [],
            issues: result.output.issues || []
        };
    }
    
    /**
     * Gets available documentation templates
     */
    public async getTemplates(languageId?: string): Promise<Template[]> {
        this.ensureInitialized();
        
        const args = ['templates', '--list', '--json'];
        
        if (languageId) {
            args.push('--language', languageId);
        }
        
        const result = await this.executeCommand(args);
        
        return result.output.templates || [];
    }
    
    /**
     * Runs security scan on code
     */
    public async runSecurityScan(targetPath: string): Promise<SecurityScanResult> {
        this.ensureInitialized();
        
        const args = [
            'security',
            'scan',
            targetPath,
            '--json',
            '--mode', this.operationMode
        ];
        
        const result = await this.executeCommand(args);
        
        return {
            score: result.output.score || 0,
            vulnerabilities: result.output.vulnerabilities || [],
            piiDetected: result.output.piiDetected || [],
            recommendations: result.output.recommendations || [],
            sbom: result.output.sbom
        };
    }
    
    /**
     * Gets MIAIR optimization insights
     */
    public async getMIAIRInsights(filePath: string): Promise<MIAIRInsights> {
        this.ensureInitialized();
        
        const args = [
            'miair',
            'analyze',
            filePath,
            '--json'
        ];
        
        const result = await this.executeCommand(args);
        
        return {
            entropyScore: result.output.entropyScore || 0,
            complexityScore: result.output.complexityScore || 0,
            qualityScore: result.output.qualityScore || 0,
            optimizations: result.output.optimizations || [],
            metrics: result.output.metrics || {}
        };
    }
    
    /**
     * Exports documentation in various formats
     */
    public async exportDocumentation(
        sourcePath: string,
        outputPath: string,
        format: string
    ): Promise<ExportResult> {
        this.ensureInitialized();
        
        const args = [
            'export',
            sourcePath,
            '--output', outputPath,
            '--format', format,
            '--mode', this.operationMode
        ];
        
        const result = await this.executeCommand(args);
        
        return {
            success: result.exitCode === 0,
            outputPath: result.output.outputPath || outputPath,
            format: format,
            size: result.output.size
        };
    }
    
    /**
     * Deletes documentation for a file
     */
    public async deleteDocumentation(filePath: string): Promise<void> {
        this.ensureInitialized();
        
        const args = [
            'delete',
            filePath,
            '--confirm'
        ];
        
        await this.executeCommand(args);
    }
    
    /**
     * Executes a CLI command
     */
    private async executeCommand(args: string[]): Promise<CommandResult> {
        return new Promise((resolve, reject) => {
            const request: CommandRequest = {
                args,
                resolve,
                reject
            };
            
            this.commandQueue.push(request);
            this.processQueue();
        });
    }
    
    /**
     * Processes the command queue
     */
    private async processQueue(): Promise<void> {
        if (this.isProcessing || this.commandQueue.length === 0) {
            return;
        }
        
        this.isProcessing = true;
        const request = this.commandQueue.shift()!;
        
        try {
            const result = await this.runCommand(request.args);
            request.resolve(result);
        } catch (error) {
            request.reject(error);
        } finally {
            this.isProcessing = false;
            // Process next command in queue
            if (this.commandQueue.length > 0) {
                this.processQueue();
            }
        }
    }
    
    /**
     * Runs a single CLI command
     */
    private runCommand(args: string[]): Promise<CommandResult> {
        return new Promise((resolve, reject) => {
            const fullArgs = [this.cliPath, ...args];
            
            this.logger.debug(`Executing: ${this.pythonPath} ${fullArgs.join(' ')}`);
            
            const process = spawn(this.pythonPath, fullArgs, {
                cwd: vscode.workspace.workspaceFolders?.[0]?.uri.fsPath,
                env: {
                    ...process.env,
                    DEVDOCAI_MODE: this.operationMode
                }
            });
            
            let stdout = '';
            let stderr = '';
            
            process.stdout.on('data', (data) => {
                stdout += data.toString();
            });
            
            process.stderr.on('data', (data) => {
                stderr += data.toString();
            });
            
            process.on('close', (code) => {
                if (code === 0) {
                    try {
                        const output = stdout.trim() ? JSON.parse(stdout) : {};
                        resolve({
                            exitCode: code,
                            output,
                            stderr
                        });
                    } catch (error) {
                        // Non-JSON output
                        resolve({
                            exitCode: code,
                            output: { content: stdout },
                            stderr
                        });
                    }
                } else {
                    reject(new Error(`CLI command failed: ${stderr || stdout}`));
                }
            });
            
            process.on('error', (error) => {
                reject(error);
            });
        });
    }
    
    /**
     * Starts the CLI daemon for performance mode
     */
    private async startDaemon(): Promise<void> {
        // In performance mode, we could start a long-running process
        // For now, we'll use individual command execution
        this.logger.info('Performance mode enabled (daemon mode simulation)');
    }
    
    /**
     * Verifies Python installation
     */
    private async verifyPython(): Promise<void> {
        return new Promise((resolve, reject) => {
            const process = spawn(this.pythonPath, ['--version']);
            
            process.on('close', (code) => {
                if (code === 0) {
                    resolve();
                } else {
                    reject(new Error('Python not found. Please install Python 3.9 or later.'));
                }
            });
            
            process.on('error', () => {
                reject(new Error('Python not found. Please install Python 3.9 or later.'));
            });
        });
    }
    
    /**
     * Verifies CLI installation
     */
    private async verifyCLI(): Promise<void> {
        // Check if CLI exists at the resolved path
        const fs = require('fs');
        if (!fs.existsSync(this.cliPath)) {
            throw new Error(`DevDocAI CLI not found at ${this.cliPath}`);
        }
    }
    
    /**
     * Resolves the CLI path
     */
    private resolveCLIPath(): string {
        const customPath = this.configManager.getConfig().cliPath;
        if (customPath) {
            return customPath;
        }
        
        // Use the bundled CLI from the devdocai module
        const workspaceRoot = vscode.workspace.workspaceFolders?.[0]?.uri.fsPath;
        if (workspaceRoot) {
            return path.join(workspaceRoot, 'devdocai', 'cli', 'main_unified.py');
        }
        
        throw new Error('Unable to resolve CLI path');
    }
    
    /**
     * Ensures the service is initialized
     */
    private ensureInitialized(): void {
        if (!this.isInitialized) {
            throw new Error('CLI service not initialized');
        }
    }
    
    /**
     * Reloads the CLI service with new configuration
     */
    public async reload(): Promise<void> {
        this.logger.info('Reloading CLI service');
        
        // Dispose current process if running
        if (this.cliProcess) {
            this.cliProcess.kill();
            this.cliProcess = null;
        }
        
        // Update configuration
        this.pythonPath = this.configManager.getConfig().pythonPath || 'python';
        this.cliPath = this.resolveCLIPath();
        this.operationMode = this.configManager.getConfig().operationMode || 'BASIC';
        
        // Reinitialize
        await this.initialize();
    }
    
    /**
     * Disposes the CLI service
     */
    public async dispose(): Promise<void> {
        this.logger.info('Disposing CLI service');
        
        if (this.cliProcess) {
            this.cliProcess.kill();
            this.cliProcess = null;
        }
        
        this.isInitialized = false;
    }
}

// Type definitions

interface CommandRequest {
    args: string[];
    resolve: (result: CommandResult) => void;
    reject: (error: Error) => void;
}

interface CommandResult {
    exitCode: number;
    output: any;
    stderr: string;
}

interface DocumentationOptions {
    selection?: string;
    languageId?: string;
    includeExamples?: boolean;
    useMIAIR?: boolean;
}

interface DocumentationResult {
    success: boolean;
    documentPath: string;
    content?: string;
    metadata?: any;
}

interface QualityResult {
    score: number;
    completeness: number;
    clarity: number;
    accuracy: number;
    maintainability: number;
    suggestions: string[];
    issues: any[];
}

interface Template {
    name: string;
    description: string;
    languages: string[];
    category: string;
}

interface SecurityScanResult {
    score: number;
    vulnerabilities: any[];
    piiDetected: any[];
    recommendations: string[];
    sbom?: any;
}

interface MIAIRInsights {
    entropyScore: number;
    complexityScore: number;
    qualityScore: number;
    optimizations: string[];
    metrics: any;
}

interface ExportResult {
    success: boolean;
    outputPath: string;
    format: string;
    size?: number;
}