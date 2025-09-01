/**
 * Unified CLI Service - DevDocAI Backend Integration
 * 
 * Consolidates functionality from:
 * - Pass 1: Basic CLI communication and command execution
 * - Pass 2: Performance optimizations (async, streaming, pooling)
 * - Pass 3: Security hardening (validation, audit, threat detection)
 * 
 * Operation Modes:
 * - BASIC: Synchronous operations, single process
 * - PERFORMANCE: Process pooling, async operations, streaming
 * - SECURE: Input validation, audit logging, rate limiting
 * - ENTERPRISE: All features with maximum performance and security
 * 
 * @module M013-VSCodeExtension
 * @version 3.0.0
 */

import * as vscode from 'vscode';
import { spawn, ChildProcess } from 'child_process';
import * as path from 'path';
import * as readline from 'readline';
import { EventEmitter } from 'events';
import { ConfigurationManager } from './ConfigurationManager';
import { Logger } from '../utils/Logger';
import * as crypto from 'crypto';

// Interfaces for operation modes
interface ExtensionConfig {
    operationMode: 'BASIC' | 'PERFORMANCE' | 'SECURE' | 'ENTERPRISE';
    features: {
        asyncOperations: boolean;
        streaming: boolean;
        processPooling: boolean;
        inputValidation: boolean;
        auditLogging: boolean;
    };
}

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

interface CommandRequest {
    id: string;
    args: string[];
    resolve: (result: CommandResult) => void;
    reject: (error: Error) => void;
    timestamp: number;
}

interface CommandResult {
    success: boolean;
    exitCode: number;
    output: any;
    stderr?: string;
    executionTime: number;
}

interface DocumentationOptions {
    selection?: string;
    useMIAIR?: boolean;
    includeExamples?: boolean;
    template?: string;
    outputPath?: string;
}

interface DocumentationResult {
    success: boolean;
    documentPath: string;
    content?: string;
    metadata?: any;
}

interface QualityResult {
    success: boolean;
    score: number;
    dimensions: any;
    suggestions: string[];
}

interface SecurityContext {
    inputValidator?: any;
    auditLogger?: any;
    rateLimiter?: Map<string, { count: number; resetTime: number }>;
}

/**
 * Unified CLI Service with mode-based operation
 */
export class CLIService extends EventEmitter {
    // Core properties
    private pythonPath: string;
    private cliPath: string;
    private isInitialized: boolean = false;
    
    // Basic mode properties
    private cliProcess: ChildProcess | null = null;
    private commandQueue: CommandRequest[] = [];
    private isProcessing: boolean = false;
    
    // Performance mode properties
    private processPool?: CLIProcessPool;
    private streamingCommands: Map<string, StreamingCommand> = new Map();
    
    // Security context
    private securityContext: SecurityContext = {};
    
    // Performance metrics
    private metrics = {
        commandsExecuted: 0,
        averageResponseTime: 0,
        streamingLatency: 0,
        poolHitRate: 0,
        securityValidations: 0
    };
    
    constructor(
        private configManager: ConfigurationManager,
        private logger: Logger,
        private extensionConfig: ExtensionConfig
    ) {
        super();
        
        this.pythonPath = this.configManager.getConfig().pythonPath || 'python';
        this.cliPath = this.resolveCLIPath();
        
        // Initialize performance features
        if (this.shouldUseProcessPool()) {
            this.processPool = {
                available: [],
                busy: new Map(),
                maxSize: this.extensionConfig.operationMode === 'ENTERPRISE' ? 5 : 3
            };
        }
        
        // Initialize security features
        this.initializeSecurityFeatures();
    }
    
    /**
     * Initialize CLI service based on operation mode
     */
    public async initialize(): Promise<void> {
        const startTime = Date.now();
        
        try {
            this.logger.info(`🚀 Initializing CLI service (${this.extensionConfig.operationMode} mode)`);
            
            // Verify environment
            await this.verifyEnvironment();
            
            // Initialize based on mode
            if (this.shouldUseProcessPool()) {
                await this.initializePerformanceMode();
            } else {
                await this.initializeBasicMode();
            }
            
            this.isInitialized = true;
            
            const initTime = Date.now() - startTime;
            this.logger.info(`✅ CLI service initialized in ${initTime}ms`);
            
            // Security audit
            await this.auditSecurityEvent('service.initialization', {
                mode: this.extensionConfig.operationMode,
                initTime,
                features: this.extensionConfig.features
            });
            
        } catch (error) {
            this.logger.error('Failed to initialize CLI service', error);
            await this.auditSecurityEvent('service.initialization.error', { error: error.message });
            throw error;
        }
    }
    
    /**
     * Generate documentation for a file or selection
     */
    public async generateDocumentation(
        filePath: string,
        template: string,
        options: DocumentationOptions = {}
    ): Promise<DocumentationResult> {
        this.ensureInitialized();
        
        // Security validation
        const validationResult = await this.validateInput('generateDocumentation', {
            filePath,
            template,
            options
        });
        
        if (!validationResult.isValid) {
            throw new Error(`Security validation failed: ${validationResult.errors.join(', ')}`);
        }
        
        const args = this.buildDocumentationArgs(filePath, template, options);
        
        if (this.extensionConfig.features.streaming) {
            return this.executeStreamingDocumentationCommand(args);
        } else {
            return this.executeBasicDocumentationCommand(args);
        }
    }
    
    /**
     * Analyze code quality for a file
     */
    public async analyzeQuality(filePath: string, options: any = {}): Promise<QualityResult> {
        this.ensureInitialized();
        
        // Security validation
        await this.validateInput('analyzeQuality', { filePath, options });
        
        const args = [
            'analyze',
            filePath,
            '--mode', this.extensionConfig.operationMode.toLowerCase(),
            '--format', 'json'
        ];
        
        if (options.dimensions) {
            args.push('--dimensions', options.dimensions.join(','));
        }
        
        const result = await this.executeCommand(args);
        
        return {
            success: result.exitCode === 0,
            score: result.output?.score || 0,
            dimensions: result.output?.dimensions || {},
            suggestions: result.output?.suggestions || []
        };
    }
    
    /**
     * Run a template with specified parameters
     */
    public async runTemplate(templateName: string, parameters: any = {}): Promise<any> {
        this.ensureInitialized();
        
        await this.validateInput('runTemplate', { templateName, parameters });
        
        const args = [
            'template',
            templateName,
            '--mode', this.extensionConfig.operationMode.toLowerCase()
        ];
        
        // Add parameters
        for (const [key, value] of Object.entries(parameters)) {
            args.push('--param', `${key}=${value}`);
        }
        
        const result = await this.executeCommand(args);
        return result.output;
    }
    
    /**
     * Enhance a document using AI
     */
    public async enhanceDocument(documentPath: string, strategy: string = 'comprehensive'): Promise<any> {
        this.ensureInitialized();
        
        await this.validateInput('enhanceDocument', { documentPath, strategy });
        
        const args = [
            'enhance',
            documentPath,
            '--strategy', strategy,
            '--mode', this.extensionConfig.operationMode.toLowerCase()
        ];
        
        if (this.extensionConfig.features.streaming) {
            return this.executeStreamingCommand(args);
        } else {
            return this.executeCommand(args);
        }
    }
    
    /**
     * Review code and provide suggestions
     */
    public async reviewCode(filePath: string, focusAreas: string[] = []): Promise<any> {
        this.ensureInitialized();
        
        await this.validateInput('reviewCode', { filePath, focusAreas });
        
        const args = [
            'review',
            filePath,
            '--mode', this.extensionConfig.operationMode.toLowerCase()
        ];
        
        if (focusAreas.length > 0) {
            args.push('--focus', focusAreas.join(','));
        }
        
        const result = await this.executeCommand(args);
        return result.output;
    }
    
    /**
     * Get extension metrics and health status
     */
    public async getMetrics(): Promise<any> {
        return {
            ...this.metrics,
            isInitialized: this.isInitialized,
            operationMode: this.extensionConfig.operationMode,
            processPoolSize: this.processPool?.available.length || 0,
            activeCommands: this.streamingCommands.size,
            queueLength: this.commandQueue.length
        };
    }
    
    // ==================== Private Methods ====================
    
    /**
     * Initialize basic mode (synchronous operations)
     */
    private async initializeBasicMode(): Promise<void> {
        // Start a single daemon process if needed
        if (this.extensionConfig.operationMode === 'SECURE' || this.extensionConfig.operationMode === 'ENTERPRISE') {
            await this.startDaemonProcess();
        }
    }
    
    /**
     * Initialize performance mode (process pooling, async)
     */
    private async initializePerformanceMode(): Promise<void> {
        // Pre-warm process pool
        await this.warmProcessPool();
        
        // Start command processing loop
        this.startCommandProcessor();
    }
    
    /**
     * Initialize security features based on mode
     */
    private initializeSecurityFeatures(): void {
        if (!this.shouldEnableSecurity()) return;
        
        // Rate limiter
        this.securityContext.rateLimiter = new Map();
        
        // Clear rate limits periodically
        setInterval(() => {
            const now = Date.now();
            this.securityContext.rateLimiter!.forEach((limit, key) => {
                if (now > limit.resetTime) {
                    this.securityContext.rateLimiter!.delete(key);
                }
            });
        }, 60000); // Clear every minute
    }
    
    /**
     * Execute command based on operation mode
     */
    private async executeCommand(args: string[]): Promise<CommandResult> {
        const startTime = Date.now();
        const commandId = crypto.randomUUID();
        
        try {
            let result: CommandResult;
            
            if (this.shouldUseProcessPool()) {
                result = await this.executeWithProcessPool(commandId, args);
            } else {
                result = await this.executeBasicCommand(args);
            }
            
            // Update metrics
            const executionTime = Date.now() - startTime;
            this.updateMetrics(executionTime, result.success);
            
            // Security audit
            await this.auditSecurityEvent('command.executed', {
                args: args[0], // First arg is typically the command
                executionTime,
                success: result.success
            });
            
            return result;
            
        } catch (error) {
            await this.auditSecurityEvent('command.error', {
                args: args[0],
                error: error.message
            });
            throw error;
        }
    }
    
    /**
     * Execute command using process pool (PERFORMANCE/ENTERPRISE modes)
     */
    private async executeWithProcessPool(commandId: string, args: string[]): Promise<CommandResult> {
        return new Promise((resolve, reject) => {
            const command: CommandRequest = {
                id: commandId,
                args,
                resolve,
                reject,
                timestamp: Date.now()
            };
            
            this.commandQueue.push(command);
            this.processCommandQueue();
        });
    }
    
    /**
     * Execute basic command (BASIC/SECURE modes)
     */
    private async executeBasicCommand(args: string[]): Promise<CommandResult> {
        return new Promise((resolve, reject) => {
            const process = spawn(this.pythonPath, [this.cliPath, ...args]);
            let stdout = '';
            let stderr = '';
            const startTime = Date.now();
            
            process.stdout?.on('data', (data) => {
                stdout += data.toString();
            });
            
            process.stderr?.on('data', (data) => {
                stderr += data.toString();
            });
            
            process.on('close', (code) => {
                const result: CommandResult = {
                    success: code === 0,
                    exitCode: code || 0,
                    output: this.parseOutput(stdout),
                    stderr,
                    executionTime: Date.now() - startTime
                };
                
                resolve(result);
            });
            
            process.on('error', (error) => {
                reject(error);
            });
        });
    }
    
    /**
     * Execute streaming command (PERFORMANCE/ENTERPRISE modes)
     */
    private executeStreamingCommand(args: string[]): Promise<any> {
        return new Promise((resolve, reject) => {
            const commandId = crypto.randomUUID();
            
            const streamingCommand: StreamingCommand = {
                id: commandId,
                args,
                onComplete: resolve,
                onError: reject
            };
            
            this.streamingCommands.set(commandId, streamingCommand);
            this.executeStreamingCommandInternal(streamingCommand);
        });
    }
    
    /**
     * Execute streaming documentation command
     */
    private async executeStreamingDocumentationCommand(args: string[]): Promise<DocumentationResult> {
        return new Promise((resolve, reject) => {
            const process = spawn(this.pythonPath, [this.cliPath, ...args]);
            let output = '';
            let progress = 0;
            
            const rl = readline.createInterface({
                input: process.stdout!
            });
            
            rl.on('line', (line) => {
                try {
                    const data = JSON.parse(line);
                    
                    if (data.type === 'progress') {
                        progress = data.value;
                        this.emit('documentationProgress', progress);
                    } else if (data.type === 'output') {
                        output += data.content;
                    }
                } catch {
                    // Handle non-JSON output
                    output += line + '\n';
                }
            });
            
            process.on('close', (code) => {
                const result: DocumentationResult = {
                    success: code === 0,
                    documentPath: this.extractDocumentPath(output),
                    content: output,
                    metadata: this.extractMetadata(output)
                };
                
                resolve(result);
            });
            
            process.on('error', reject);
        });
    }
    
    /**
     * Build documentation command arguments
     */
    private buildDocumentationArgs(filePath: string, template: string, options: DocumentationOptions): string[] {
        const args = [
            'generate',
            filePath,
            '--template', template,
            '--mode', this.extensionConfig.operationMode.toLowerCase()
        ];
        
        if (options.selection) {
            args.push('--selection', options.selection);
        }
        
        if (options.useMIAIR) {
            args.push('--miair');
        }
        
        if (options.includeExamples) {
            args.push('--examples');
        }
        
        if (options.outputPath) {
            args.push('--output', options.outputPath);
        }
        
        return args;
    }
    
    /**
     * Warm up process pool for performance
     */
    private async warmProcessPool(): Promise<void> {
        if (!this.processPool) return;
        
        const promises: Promise<void>[] = [];
        
        for (let i = 0; i < this.processPool.maxSize; i++) {
            promises.push(this.createPoolProcess());
        }
        
        await Promise.allSettled(promises);
        this.logger.info(`Process pool warmed with ${this.processPool.available.length} processes`);
    }
    
    /**
     * Create a process for the pool
     */
    private async createPoolProcess(): Promise<void> {
        return new Promise((resolve, reject) => {
            const process = spawn(this.pythonPath, [this.cliPath, '--daemon']);
            
            process.on('spawn', () => {
                this.processPool?.available.push(process);
                resolve();
            });
            
            process.on('error', reject);
        });
    }
    
    /**
     * Process command queue
     */
    private processCommandQueue(): void {
        if (this.isProcessing || this.commandQueue.length === 0) return;
        if (!this.processPool || this.processPool.available.length === 0) return;
        
        this.isProcessing = true;
        const command = this.commandQueue.shift()!;
        const process = this.processPool.available.pop()!;
        
        this.processPool.busy.set(command.id, process);
        
        // Execute command with pooled process
        this.executeCommandWithPooledProcess(process, command)
            .then(() => {
                // Return process to pool
                this.processPool!.busy.delete(command.id);
                this.processPool!.available.push(process);
                this.isProcessing = false;
                
                // Process next command
                setImmediate(() => this.processCommandQueue());
            })
            .catch((error) => {
                this.processPool!.busy.delete(command.id);
                this.isProcessing = false;
                command.reject(error);
            });
    }
    
    /**
     * Execute command with pooled process
     */
    private executeCommandWithPooledProcess(process: ChildProcess, command: CommandRequest): Promise<void> {
        return new Promise((resolve, reject) => {
            let stdout = '';
            let stderr = '';
            
            // Send command to daemon process
            process.stdin?.write(JSON.stringify({
                id: command.id,
                args: command.args
            }) + '\n');
            
            const onData = (data: Buffer) => {
                const line = data.toString().trim();
                try {
                    const response = JSON.parse(line);
                    if (response.id === command.id) {
                        if (response.type === 'result') {
                            const result: CommandResult = {
                                success: response.success,
                                exitCode: response.exitCode,
                                output: response.output,
                                stderr: response.stderr,
                                executionTime: Date.now() - command.timestamp
                            };
                            
                            command.resolve(result);
                            process.stdout?.off('data', onData);
                            resolve();
                        }
                    }
                } catch {
                    // Handle non-JSON output
                    stdout += line + '\n';
                }
            };
            
            process.stdout?.on('data', onData);
            
            // Timeout handling
            setTimeout(() => {
                process.stdout?.off('data', onData);
                reject(new Error('Command timeout'));
            }, 30000); // 30 second timeout
        });
    }
    
    /**
     * Start command processor loop
     */
    private startCommandProcessor(): void {
        setInterval(() => {
            this.processCommandQueue();
        }, 100); // Check every 100ms
    }
    
    /**
     * Start daemon process for secure modes
     */
    private async startDaemonProcess(): Promise<void> {
        if (this.cliProcess) return;
        
        this.cliProcess = spawn(this.pythonPath, [this.cliPath, '--daemon', '--secure']);
        
        this.cliProcess.on('error', (error) => {
            this.logger.error('CLI daemon process error:', error);
        });
        
        this.cliProcess.on('exit', (code) => {
            this.logger.warn(`CLI daemon process exited with code ${code}`);
            this.cliProcess = null;
        });
    }
    
    /**
     * Verify Python and CLI environment
     */
    private async verifyEnvironment(): Promise<void> {
        await Promise.all([
            this.verifyPython(),
            this.verifyCLI()
        ]);
    }
    
    /**
     * Verify Python installation
     */
    private async verifyPython(): Promise<void> {
        return new Promise((resolve, reject) => {
            const process = spawn(this.pythonPath, ['--version']);
            
            process.on('close', (code) => {
                if (code === 0) {
                    resolve();
                } else {
                    reject(new Error(`Python not found at: ${this.pythonPath}`));
                }
            });
            
            process.on('error', () => {
                reject(new Error(`Failed to execute Python at: ${this.pythonPath}`));
            });
        });
    }
    
    /**
     * Verify CLI installation
     */
    private async verifyCLI(): Promise<void> {
        return new Promise((resolve, reject) => {
            const process = spawn(this.pythonPath, [this.cliPath, '--version']);
            
            process.on('close', (code) => {
                if (code === 0) {
                    resolve();
                } else {
                    reject(new Error(`DevDocAI CLI not found at: ${this.cliPath}`));
                }
            });
            
            process.on('error', () => {
                reject(new Error(`Failed to execute CLI at: ${this.cliPath}`));
            });
        });
    }
    
    /**
     * Resolve CLI path based on workspace
     */
    private resolveCLIPath(): string {
        const workspaceFolders = vscode.workspace.workspaceFolders;
        if (workspaceFolders && workspaceFolders.length > 0) {
            const workspaceRoot = workspaceFolders[0].uri.fsPath;
            return path.join(workspaceRoot, 'devdocai', 'cli.py');
        }
        
        // Fallback to global installation
        return 'devdocai-cli';
    }
    
    /**
     * Parse command output
     */
    private parseOutput(output: string): any {
        try {
            return JSON.parse(output);
        } catch {
            return { content: output };
        }
    }
    
    /**
     * Extract document path from output
     */
    private extractDocumentPath(output: string): string {
        const match = output.match(/Document saved to: (.+)/);
        return match ? match[1] : 'unknown';
    }
    
    /**
     * Extract metadata from output
     */
    private extractMetadata(output: string): any {
        try {
            const metadataMatch = output.match(/Metadata: ({.+})/);
            return metadataMatch ? JSON.parse(metadataMatch[1]) : {};
        } catch {
            return {};
        }
    }
    
    /**
     * Update performance metrics
     */
    private updateMetrics(executionTime: number, success: boolean): void {
        this.metrics.commandsExecuted++;
        
        // Update average response time
        this.metrics.averageResponseTime = 
            (this.metrics.averageResponseTime * (this.metrics.commandsExecuted - 1) + executionTime) / 
            this.metrics.commandsExecuted;
        
        // Update pool hit rate if using pool
        if (this.processPool) {
            const hits = this.processPool.available.length > 0 ? 1 : 0;
            this.metrics.poolHitRate = 
                (this.metrics.poolHitRate * (this.metrics.commandsExecuted - 1) + hits) / 
                this.metrics.commandsExecuted;
        }
    }
    
    /**
     * Input validation for security
     */
    private async validateInput(operation: string, params: any): Promise<{ isValid: boolean; errors: string[] }> {
        if (!this.shouldEnableSecurity()) {
            return { isValid: true, errors: [] };
        }
        
        this.metrics.securityValidations++;
        
        // Rate limiting
        const rateLimitKey = `${operation}:${Date.now()}`;
        const currentTime = Date.now();
        const windowSize = 60000; // 1 minute
        const maxRequests = 100;
        
        const rateLimit = this.securityContext.rateLimiter!.get(operation) || {
            count: 0,
            resetTime: currentTime + windowSize
        };
        
        if (currentTime > rateLimit.resetTime) {
            rateLimit.count = 1;
            rateLimit.resetTime = currentTime + windowSize;
        } else {
            rateLimit.count++;
        }
        
        this.securityContext.rateLimiter!.set(operation, rateLimit);
        
        if (rateLimit.count > maxRequests) {
            return {
                isValid: false,
                errors: [`Rate limit exceeded for operation: ${operation}`]
            };
        }
        
        // Basic input validation
        const errors: string[] = [];
        
        if (params.filePath && !this.isValidPath(params.filePath)) {
            errors.push('Invalid file path');
        }
        
        return { isValid: errors.length === 0, errors };
    }
    
    /**
     * Validate file path for security
     */
    private isValidPath(filePath: string): boolean {
        // Prevent path traversal
        if (filePath.includes('..') || filePath.includes('~')) {
            return false;
        }
        
        // Ensure it's within workspace
        const workspaceFolders = vscode.workspace.workspaceFolders;
        if (workspaceFolders) {
            const workspaceRoot = workspaceFolders[0].uri.fsPath;
            const normalizedPath = path.resolve(filePath);
            return normalizedPath.startsWith(workspaceRoot);
        }
        
        return true;
    }
    
    /**
     * Audit security events
     */
    private async auditSecurityEvent(event: string, data: any): Promise<void> {
        if (!this.shouldEnableSecurity() || !this.securityContext.auditLogger) return;
        
        try {
            await this.securityContext.auditLogger.logEvent(event, {
                timestamp: new Date().toISOString(),
                service: 'CLIService',
                ...data
            });
        } catch (error) {
            this.logger.error('Failed to audit security event:', error);
        }
    }
    
    /**
     * Execute streaming command internally
     */
    private executeStreamingCommandInternal(command: StreamingCommand): void {
        const process = spawn(this.pythonPath, [this.cliPath, ...command.args]);
        
        const rl = readline.createInterface({
            input: process.stdout!
        });
        
        rl.on('line', (line) => {
            if (command.onData) {
                command.onData(line);
            }
            
            try {
                const data = JSON.parse(line);
                if (data.type === 'progress' && command.onProgress) {
                    command.onProgress(data.value);
                }
            } catch {
                // Handle non-JSON output
            }
        });
        
        process.on('close', (code) => {
            this.streamingCommands.delete(command.id);
            if (command.onComplete) {
                command.onComplete({ success: code === 0, exitCode: code });
            }
        });
        
        process.on('error', (error) => {
            this.streamingCommands.delete(command.id);
            if (command.onError) {
                command.onError(error);
            }
        });
    }
    
    /**
     * Utility methods for mode checking
     */
    private shouldUseProcessPool(): boolean {
        return this.extensionConfig.operationMode === 'PERFORMANCE' || 
               this.extensionConfig.operationMode === 'ENTERPRISE';
    }
    
    private shouldEnableSecurity(): boolean {
        return this.extensionConfig.operationMode === 'SECURE' || 
               this.extensionConfig.operationMode === 'ENTERPRISE';
    }
    
    private ensureInitialized(): void {
        if (!this.isInitialized) {
            throw new Error('CLI service not initialized');
        }
    }
    
    /**
     * Cleanup resources
     */
    public async cleanup(): Promise<void> {
        // Stop daemon process
        if (this.cliProcess) {
            this.cliProcess.kill();
            this.cliProcess = null;
        }
        
        // Cleanup process pool
        if (this.processPool) {
            [...this.processPool.available, ...this.processPool.busy.values()].forEach(process => {
                process.kill();
            });
            this.processPool.available = [];
            this.processPool.busy.clear();
        }
        
        // Clear streaming commands
        this.streamingCommands.clear();
        
        // Audit cleanup
        await this.auditSecurityEvent('service.cleanup', {
            commandsExecuted: this.metrics.commandsExecuted,
            averageResponseTime: this.metrics.averageResponseTime
        });
    }
}

// Export types for external use
export type { 
    DocumentationOptions, 
    DocumentationResult, 
    QualityResult, 
    CommandResult,
    ExtensionConfig 
};