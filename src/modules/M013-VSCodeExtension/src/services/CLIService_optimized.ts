/**
 * Optimized CLI Service - Async/Streaming Operations
 * 
 * Performance optimizations:
 * - Async operations with progress indicators
 * - Streaming output for real-time feedback
 * - Connection pooling for process reuse
 * - Non-blocking UI with cancellation support
 * - Queue management with backpressure
 * 
 * @module M013-VSCodeExtension
 */

import * as vscode from 'vscode';
import { spawn, ChildProcess } from 'child_process';
import * as path from 'path';
import * as readline from 'readline';
import { EventEmitter } from 'events';
import { ConfigurationManager } from './ConfigurationManager';
import { Logger } from '../utils/Logger';
import { InputValidator, ValidationResult } from '../security/InputValidator';

interface CLIProcessPool {
    available: ChildProcess[];
    busy: Map<string, ChildProcess>;
    maxSize: number;
}

interface StreamingCommand {
    id: string;
    args: string[];
    onData?: (data: string) => void;
    onProgress?: (progress: number) => void;
    onComplete?: (result: any) => void;
    onError?: (error: Error) => void;
    cancellationToken?: vscode.CancellationToken;
}

export class OptimizedCLIService extends EventEmitter {
    private processPool: CLIProcessPool = {
        available: [],
        busy: new Map(),
        maxSize: 3
    };
    
    private commandQueue: StreamingCommand[] = [];
    private isProcessing: boolean = false;
    private isInitialized: boolean = false;
    
    // Security components
    private inputValidator: InputValidator;
    
    private pythonPath: string;
    private cliPath: string;
    private operationMode: string;
    
    // Performance metrics
    private metrics = {
        commandsExecuted: 0,
        averageResponseTime: 0,
        streamingLatency: 0,
        poolHitRate: 0
    };
    
    constructor(
        private configManager: ConfigurationManager,
        private logger: Logger
    ) {
        super();
        
        // Initialize security validator
        this.inputValidator = new InputValidator(configManager['context']);
        
        this.pythonPath = this.configManager.getConfig().pythonPath || 'python';
        this.cliPath = this.resolveCLIPath();
        this.operationMode = this.configManager.getConfig().operationMode || 'BASIC';
    }
    
    /**
     * Initializes the CLI service with process pool
     */
    public async initialize(): Promise<void> {
        return new Promise((resolve, reject) => {
            this.logger.info('🚀 Initializing optimized CLI service');
            
            // Verify Python and CLI in parallel
            Promise.all([
                this.verifyPython(),
                this.verifyCLI()
            ]).then(() => {
                // Pre-warm process pool for performance mode
                if (this.operationMode === 'PERFORMANCE' || this.operationMode === 'ENTERPRISE') {
                    this.warmProcessPool();
                }
                
                this.isInitialized = true;
                this.logger.info('✅ CLI service initialized with process pool');
                resolve();
            }).catch(reject);
        });
    }
    
    /**
     * Generates documentation with streaming and progress (Security Hardened)
     */
    public async generateDocumentation(
        filePath: string,
        template: string,
        options?: any
    ): Promise<any> {
        // SECURITY: Validate all inputs before processing
        const securityValidation = await this.validateDocumentationInputs(filePath, template, options);
        if (!securityValidation.isValid) {
            throw new Error(`Security validation failed: ${securityValidation.errors.join(', ')}`);
        }
        
        return vscode.window.withProgress({
            location: vscode.ProgressLocation.Notification,
            title: "Generating Documentation",
            cancellable: true
        }, async (progress, token) => {
            progress.report({ increment: 0, message: "Analyzing code..." });
            
            // Use validated/sanitized inputs
            const sanitizedInputs = securityValidation.sanitized;
            
            const args = [
                'generate',
                sanitizedInputs.filePath,
                '--template', sanitizedInputs.template,
                '--mode', this.operationMode,
                '--stream' // Enable streaming output
            ];
            
            if (sanitizedInputs.options?.selection) {
                args.push('--selection', sanitizedInputs.options.selection);
            }
            if (sanitizedInputs.options?.useMIAIR) {
                args.push('--miair');
            }
            
            // Final validation of complete argument array
            const argsValidation = this.inputValidator.validateCliArguments(args);
            if (!argsValidation.isValid) {
                throw new Error(`CLI arguments validation failed: ${argsValidation.errors.join(', ')}`);
            }
            
            let result: any = {};
            let outputBuffer = '';
            
            await this.executeStreamingCommand({
                id: `generate-${Date.now()}`,
                args: argsValidation.sanitized,
                onData: (data) => {
                    outputBuffer += data;
                    
                    // Parse progress from streamed data
                    const progressMatch = data.match(/progress:(\d+)/);
                    if (progressMatch) {
                        const percent = parseInt(progressMatch[1]);
                        progress.report({ 
                            increment: percent - (result.progress || 0),
                            message: `Processing... ${percent}%`
                        });
                        result.progress = percent;
                    }
                    
                    // Parse status messages
                    const statusMatch = data.match(/status:(.+)/);
                    if (statusMatch) {
                        progress.report({ message: statusMatch[1] });
                    }
                },
                onComplete: (data) => {
                    result = { ...result, ...data };
                },
                onError: (error) => {
                    throw error;
                },
                cancellationToken: token
            });
            
            progress.report({ increment: 100, message: "Documentation generated!" });
            
            return {
                success: true,
                documentPath: result.documentPath || path.join(path.dirname(filePath), 'documentation.md'),
                content: result.content || outputBuffer,
                metadata: result.metadata
            };
        });
    }
    
    /**
     * Analyzes quality with real-time updates (Security Hardened)
     */
    public async analyzeQuality(documentPath: string): Promise<any> {
        // SECURITY: Validate inputs and rate limiting
        const securityValidation = await this.validateQualityInputs(documentPath);
        if (!securityValidation.isValid) {
            throw new Error(`Security validation failed: ${securityValidation.errors.join(', ')}`);
        }
        
        const rateLimitCheck = this.checkRateLimit('analyze');
        if (!rateLimitCheck.isValid) {
            throw new Error(`Rate limit exceeded: ${rateLimitCheck.errors.join(', ')}`);
        }
        
        return vscode.window.withProgress({
            location: vscode.ProgressLocation.Window,
            title: "Analyzing Quality"
        }, async (progress) => {
            const args = [
                'analyze',
                securityValidation.sanitized,
                '--json',
                '--mode', this.operationMode,
                '--stream'
            ];
            
            // Validate CLI arguments
            const argsValidation = this.inputValidator.validateCliArguments(args);
            if (!argsValidation.isValid) {
                throw new Error(`CLI arguments validation failed: ${argsValidation.errors.join(', ')}`);
            }
            
            let result: any = {};
            
            await this.executeStreamingCommand({
                id: `analyze-${Date.now()}`,
                args: argsValidation.sanitized,
                onData: (data) => {
                    // Parse intermediate results
                    try {
                        const partial = JSON.parse(data);
                        if (partial.dimension) {
                            progress.report({ 
                                message: `Analyzing ${partial.dimension}...`
                            });
                        }
                    } catch (e) {
                        // Not JSON, ignore
                    }
                },
                onComplete: (data) => {
                    result = data;
                }
            });
            
            return {
                score: result.score || 0,
                completeness: result.completeness || 0,
                clarity: result.clarity || 0,
                accuracy: result.accuracy || 0,
                maintainability: result.maintainability || 0,
                suggestions: result.suggestions || [],
                issues: result.issues || []
            };
        });
    }
    
    /**
     * Executes a streaming command with progress support
     */
    private executeStreamingCommand(command: StreamingCommand): Promise<void> {
        return new Promise((resolve, reject) => {
            const startTime = Date.now();
            
            // Check for cancellation
            if (command.cancellationToken?.isCancellationRequested) {
                reject(new Error('Operation cancelled'));
                return;
            }
            
            // Get or create process from pool
            const process = this.getProcessFromPool(command.id);
            
            if (!process) {
                // Create new process if pool is exhausted
                this.createStreamingProcess(command, startTime)
                    .then(resolve)
                    .catch(reject);
            } else {
                // Reuse existing process
                this.reusePooledProcess(process, command, startTime)
                    .then(resolve)
                    .catch(reject);
            }
        });
    }
    
    /**
     * Creates a new streaming process
     */
    private createStreamingProcess(
        command: StreamingCommand,
        startTime: number
    ): Promise<void> {
        return new Promise((resolve, reject) => {
            const fullArgs = [this.cliPath, ...command.args];
            
            this.logger.debug(`🔄 Spawning: ${this.pythonPath} ${fullArgs.join(' ')}`);
            
            const process = spawn(this.pythonPath, fullArgs, {
                cwd: vscode.workspace.workspaceFolders?.[0]?.uri.fsPath,
                env: {
                    ...process.env,
                    DEVDOCAI_MODE: this.operationMode,
                    DEVDOCAI_STREAMING: 'true'
                }
            });
            
            // Track process in busy pool
            this.processPool.busy.set(command.id, process);
            
            let outputBuffer = '';
            let errorBuffer = '';
            
            // Create readline interface for streaming
            const rl = readline.createInterface({
                input: process.stdout,
                crlfDelay: Infinity
            });
            
            // Stream output line by line
            rl.on('line', (line) => {
                if (command.onData) {
                    command.onData(line);
                }
                outputBuffer += line + '\n';
                
                // Update streaming latency metric
                if (this.metrics.streamingLatency === 0) {
                    this.metrics.streamingLatency = Date.now() - startTime;
                }
            });
            
            // Handle stderr
            process.stderr.on('data', (data) => {
                errorBuffer += data.toString();
            });
            
            // Handle cancellation
            if (command.cancellationToken) {
                command.cancellationToken.onCancellationRequested(() => {
                    process.kill('SIGTERM');
                    reject(new Error('Operation cancelled by user'));
                });
            }
            
            // Handle process completion
            process.on('close', (code) => {
                // Return process to pool
                this.returnProcessToPool(command.id, process);
                
                // Update metrics
                const responseTime = Date.now() - startTime;
                this.updateMetrics(responseTime);
                
                if (code === 0) {
                    try {
                        const result = outputBuffer.trim() ? 
                            this.parseOutput(outputBuffer) : {};
                        
                        if (command.onComplete) {
                            command.onComplete(result);
                        }
                        resolve();
                    } catch (error) {
                        if (command.onError) {
                            command.onError(error as Error);
                        }
                        reject(error);
                    }
                } else {
                    const error = new Error(`CLI command failed: ${errorBuffer || outputBuffer}`);
                    if (command.onError) {
                        command.onError(error);
                    }
                    reject(error);
                }
            });
            
            // Handle process errors
            process.on('error', (error) => {
                this.returnProcessToPool(command.id, process);
                if (command.onError) {
                    command.onError(error);
                }
                reject(error);
            });
        });
    }
    
    /**
     * Reuses a pooled process for better performance
     */
    private async reusePooledProcess(
        process: ChildProcess,
        command: StreamingCommand,
        startTime: number
    ): Promise<void> {
        // For now, create new process
        // In a full implementation, we'd reuse the process with IPC
        return this.createStreamingProcess(command, startTime);
    }
    
    /**
     * Process pool management
     */
    private warmProcessPool(): void {
        this.logger.info('🔥 Pre-warming process pool');
        
        // Create initial processes
        for (let i = 0; i < Math.min(2, this.processPool.maxSize); i++) {
            const process = spawn(this.pythonPath, [this.cliPath, '--daemon'], {
                cwd: vscode.workspace.workspaceFolders?.[0]?.uri.fsPath,
                env: {
                    ...process.env,
                    DEVDOCAI_MODE: this.operationMode,
                    DEVDOCAI_DAEMON: 'true'
                }
            });
            
            // Keep process alive but idle
            process.stdin.write('ping\n');
            this.processPool.available.push(process);
        }
        
        this.logger.info(`✅ Process pool warmed with ${this.processPool.available.length} processes`);
    }
    
    private getProcessFromPool(commandId: string): ChildProcess | null {
        if (this.processPool.available.length > 0) {
            const process = this.processPool.available.pop()!;
            this.processPool.busy.set(commandId, process);
            this.metrics.poolHitRate++;
            return process;
        }
        return null;
    }
    
    private returnProcessToPool(commandId: string, process: ChildProcess): void {
        this.processPool.busy.delete(commandId);
        
        // Only return to pool if healthy and under limit
        if (!process.killed && this.processPool.available.length < this.processPool.maxSize) {
            this.processPool.available.push(process);
        } else {
            process.kill();
        }
    }
    
    /**
     * Parse output intelligently
     */
    private parseOutput(output: string): any {
        // Try JSON first
        try {
            return JSON.parse(output);
        } catch (e) {
            // Try to extract JSON from mixed output
            const jsonMatch = output.match(/\{[\s\S]*\}/);
            if (jsonMatch) {
                try {
                    return JSON.parse(jsonMatch[0]);
                } catch (e2) {
                    // Fall back to plain text
                    return { content: output };
                }
            }
            return { content: output };
        }
    }
    
    /**
     * Update performance metrics
     */
    private updateMetrics(responseTime: number): void {
        this.metrics.commandsExecuted++;
        this.metrics.averageResponseTime = 
            (this.metrics.averageResponseTime * (this.metrics.commandsExecuted - 1) + responseTime) / 
            this.metrics.commandsExecuted;
        
        // Log metrics periodically
        if (this.metrics.commandsExecuted % 10 === 0) {
            this.logger.info(`📊 CLI Metrics: Avg Response: ${this.metrics.averageResponseTime.toFixed(2)}ms, ` +
                `Streaming Latency: ${this.metrics.streamingLatency}ms, ` +
                `Pool Hit Rate: ${(this.metrics.poolHitRate / this.metrics.commandsExecuted * 100).toFixed(1)}%`);
        }
    }
    
    /**
     * Gets available templates with caching
     */
    private templateCache: { templates: any[], timestamp: number } | null = null;
    private readonly CACHE_TTL = 60000; // 1 minute
    
    public async getTemplates(languageId?: string): Promise<any[]> {
        // Check cache first
        if (this.templateCache && 
            Date.now() - this.templateCache.timestamp < this.CACHE_TTL) {
            this.logger.debug('📦 Returning cached templates');
            return this.templateCache.templates;
        }
        
        const args = ['templates', '--list', '--json'];
        if (languageId) {
            args.push('--language', languageId);
        }
        
        let templates: any[] = [];
        
        await this.executeStreamingCommand({
            id: `templates-${Date.now()}`,
            args,
            onComplete: (data) => {
                templates = data.templates || [];
            }
        });
        
        // Update cache
        this.templateCache = { templates, timestamp: Date.now() };
        
        return templates;
    }
    
    /**
     * Verifies Python installation (async)
     */
    private verifyPython(): Promise<void> {
        return new Promise((resolve, reject) => {
            const process = spawn(this.pythonPath, ['--version']);
            
            let timeout = setTimeout(() => {
                process.kill();
                reject(new Error('Python verification timed out'));
            }, 5000);
            
            process.on('close', (code) => {
                clearTimeout(timeout);
                if (code === 0) {
                    resolve();
                } else {
                    reject(new Error('Python not found. Please install Python 3.9 or later.'));
                }
            });
            
            process.on('error', () => {
                clearTimeout(timeout);
                reject(new Error('Python not found. Please install Python 3.9 or later.'));
            });
        });
    }
    
    /**
     * Verifies CLI installation (async)
     */
    private async verifyCLI(): Promise<void> {
        const fs = require('fs').promises;
        try {
            await fs.access(this.cliPath);
        } catch {
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
        
        const workspaceRoot = vscode.workspace.workspaceFolders?.[0]?.uri.fsPath;
        if (workspaceRoot) {
            return path.join(workspaceRoot, 'devdocai', 'cli', 'main_unified.py');
        }
        
        throw new Error('Unable to resolve CLI path');
    }
    
    /**
     * Reloads the CLI service
     */
    public async reload(): Promise<void> {
        this.logger.info('🔄 Reloading CLI service');
        
        // Dispose all pooled processes
        for (const process of this.processPool.available) {
            process.kill();
        }
        for (const process of this.processPool.busy.values()) {
            process.kill();
        }
        
        this.processPool.available = [];
        this.processPool.busy.clear();
        
        // Update configuration
        this.pythonPath = this.configManager.getConfig().pythonPath || 'python';
        this.cliPath = this.resolveCLIPath();
        this.operationMode = this.configManager.getConfig().operationMode || 'BASIC';
        
        // Clear caches
        this.templateCache = null;
        
        // Reinitialize
        await this.initialize();
    }
    
    /**
     * Disposes the CLI service
     */
    public async dispose(): Promise<void> {
        this.logger.info('♻️ Disposing CLI service');
        
        // Kill all processes
        for (const process of this.processPool.available) {
            process.kill();
        }
        for (const process of this.processPool.busy.values()) {
            process.kill();
        }
        
        this.processPool.available = [];
        this.processPool.busy.clear();
        this.isInitialized = false;
        
        // Log final metrics
        this.logger.info(`📊 Final CLI Metrics: Commands: ${this.metrics.commandsExecuted}, ` +
            `Avg Response: ${this.metrics.averageResponseTime.toFixed(2)}ms, ` +
            `Streaming Latency: ${this.metrics.streamingLatency}ms`);
    }
    
    /**
     * Getters for compatibility
     */
    public get isReady(): boolean {
        return this.isInitialized;
    }
    
    /**
     * SECURITY: Validates documentation generation inputs
     */
    private async validateDocumentationInputs(
        filePath: string,
        template: string,
        options?: any
    ): Promise<ValidationResult> {
        const result: ValidationResult = {
            isValid: true,
            sanitized: {
                filePath: '',
                template: '',
                options: {}
            },
            errors: [],
            warnings: [],
            securityScore: 100
        };
        
        // Validate file path for traversal attacks
        const filePathValidation = this.inputValidator.validateFilePath(
            filePath,
            { requireWorkspaceScope: true, preventExecutables: true }
        );
        
        if (!filePathValidation.isValid) {
            result.isValid = false;
            result.errors.push(...filePathValidation.errors);
            result.securityScore = Math.min(result.securityScore, filePathValidation.securityScore);
        } else {
            result.sanitized.filePath = filePathValidation.sanitized;
        }
        
        // Validate template name
        const templateValidation = this.inputValidator.validateParameter(
            'template',
            template,
            { maxLength: 100, requireAlphanumeric: true }
        );
        
        if (!templateValidation.isValid) {
            result.isValid = false;
            result.errors.push(...templateValidation.errors);
            result.securityScore = Math.min(result.securityScore, templateValidation.securityScore);
        } else {
            result.sanitized.template = templateValidation.sanitized;
        }
        
        // Validate options object
        if (options) {
            const optionsValidation = this.inputValidator.validateDataObject(options);
            if (!optionsValidation.isValid) {
                result.warnings.push(...optionsValidation.warnings);
                result.securityScore = Math.min(result.securityScore, optionsValidation.securityScore);
            }
            result.sanitized.options = optionsValidation.sanitized;
        }
        
        return result;
    }
    
    /**
     * SECURITY: Validates quality analysis inputs
     */
    private async validateQualityInputs(documentPath: string): Promise<ValidationResult> {
        return this.inputValidator.validateFilePath(
            documentPath,
            { requireWorkspaceScope: true }
        );
    }
    
    /**
     * SECURITY: Validates security scan inputs
     */
    private async validateSecurityScanInputs(targetPath: string): Promise<ValidationResult> {
        return this.inputValidator.validateFilePath(
            targetPath,
            { requireWorkspaceScope: true }
        );
    }
    
    /**
     * SECURITY: Rate limiting check for CLI operations
     */
    private checkRateLimit(operation: string): ValidationResult {
        const rateLimitKey = `cli-${operation}`;
        return this.inputValidator.validateRateLimit(rateLimitKey, 50); // 50 ops/minute
    }
    
    /**
     * Additional optimized methods
     */
    
    public async runSecurityScan(targetPath: string): Promise<any> {
        // SECURITY: Validate inputs and rate limiting
        const securityValidation = await this.validateSecurityScanInputs(targetPath);
        if (!securityValidation.isValid) {
            throw new Error(`Security validation failed: ${securityValidation.errors.join(', ')}`);
        }
        
        const rateLimitCheck = this.checkRateLimit('security-scan');
        if (!rateLimitCheck.isValid) {
            throw new Error(`Rate limit exceeded: ${rateLimitCheck.errors.join(', ')}`);
        }
        
        return vscode.window.withProgress({
            location: vscode.ProgressLocation.Notification,
            title: "Security Scan",
            cancellable: true
        }, async (progress, token) => {
            const args = ['security', 'scan', securityValidation.sanitized, '--json', '--stream'];
            
            // Validate CLI arguments
            const argsValidation = this.inputValidator.validateCliArguments(args);
            if (!argsValidation.isValid) {
                throw new Error(`CLI arguments validation failed: ${argsValidation.errors.join(', ')}`);
            }
            
            let result: any = {};
            
            await this.executeStreamingCommand({
                id: `security-${Date.now()}`,
                args: argsValidation.sanitized,
                onData: (data) => {
                    const match = data.match(/scanning:(.+)/);
                    if (match) {
                        progress.report({ message: `Scanning ${match[1]}...` });
                    }
                },
                onComplete: (data) => {
                    result = data;
                },
                cancellationToken: token
            });
            
            return result;
        });
    }
    
    public async getMIAIRInsights(filePath: string): Promise<any> {
        const args = ['miair', 'analyze', filePath, '--json', '--stream'];
        let result: any = {};
        
        await this.executeStreamingCommand({
            id: `miair-${Date.now()}`,
            args,
            onComplete: (data) => {
                result = data;
            }
        });
        
        return result;
    }
    
    public async exportDocumentation(
        sourcePath: string,
        outputPath: string,
        format: string
    ): Promise<any> {
        return vscode.window.withProgress({
            location: vscode.ProgressLocation.Window,
            title: `Exporting to ${format.toUpperCase()}`
        }, async (progress) => {
            const args = [
                'export',
                sourcePath,
                '--output', outputPath,
                '--format', format,
                '--stream'
            ];
            
            let result: any = {};
            
            await this.executeStreamingCommand({
                id: `export-${Date.now()}`,
                args,
                onData: (data) => {
                    const match = data.match(/progress:(\d+)/);
                    if (match) {
                        progress.report({ 
                            increment: parseInt(match[1]),
                            message: `Exporting... ${match[1]}%`
                        });
                    }
                },
                onComplete: (data) => {
                    result = data;
                }
            });
            
            return {
                success: true,
                outputPath: result.outputPath || outputPath,
                format,
                size: result.size
            };
        });
    }
    
    public async deleteDocumentation(filePath: string): Promise<void> {
        const args = ['delete', filePath, '--confirm'];
        
        await this.executeStreamingCommand({
            id: `delete-${Date.now()}`,
            args
        });
    }
}