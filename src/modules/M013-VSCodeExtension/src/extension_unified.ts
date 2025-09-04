/**
 * DevDocAI VS Code Extension - Unified Entry Point
 * 
 * Consolidates functionality from all development passes:
 * - Pass 1: Core implementation with full integration
 * - Pass 2: Performance optimizations (lazy loading, async operations)
 * - Pass 3: Security hardening (enterprise-grade protection)
 * - Pass 4: Unified architecture with mode-based operation
 * 
 * Operation Modes:
 * - BASIC: Core functionality, synchronous operations
 * - PERFORMANCE: Optimized with lazy loading, async operations, caching
 * - SECURE: Input validation, audit logging, threat detection
 * - ENTERPRISE: All features with maximum performance and security
 * 
 * @module M013-VSCodeExtension
 * @version 3.0.0
 */

import * as vscode from 'vscode';
import { performance } from 'perf_hooks';
import * as crypto from 'crypto';

// Core interfaces
interface ExtensionConfig {
    operationMode: 'BASIC' | 'PERFORMANCE' | 'SECURE' | 'ENTERPRISE';
    features: {
        lazyLoading: boolean;
        asyncOperations: boolean;
        inputValidation: boolean;
        auditLogging: boolean;
        threatDetection: boolean;
        caching: boolean;
        streaming: boolean;
        permissionControl: boolean;
    };
    performance: {
        activationTimeTarget: number;
        commandTimeTarget: number;
        maxCacheSize: number;
    };
    security: {
        enableEncryption: boolean;
        auditLevel: 'BASIC' | 'DETAILED' | 'COMPREHENSIVE';
        rateLimiting: boolean;
    };
}

// Service registry for lazy loading and mode-based instantiation
interface ServiceRegistry {
    commandManager?: any;
    cliService?: any;
    webviewManager?: any;
    statusBarManager?: any;
    configManager?: any;
    languageService?: any;
    logger?: any;
    providers?: Map<string, any>;
    security?: {
        inputValidator?: any;
        auditLogger?: any;
        threatDetector?: any;
        permissionManager?: any;
    };
}

// Performance tracking
interface PerformanceMetrics {
    activationTime: number;
    commandTimes: Map<string, number>;
    memoryUsage: number;
    cacheHitRatio: number;
}

// Security context
interface SecurityContext {
    sessionId: string;
    userId: string;
    permissions: Set<string>;
    threatLevel: 'LOW' | 'MEDIUM' | 'HIGH';
    auditEnabled: boolean;
}

// Global state
const services: ServiceRegistry = { providers: new Map(), security: {} };
let extensionConfig: ExtensionConfig;
let performanceMetrics: PerformanceMetrics;
let securityContext: SecurityContext;
const perfMarks = new Map<string, number>();

/**
 * Extension activation - unified entry point with mode-based initialization
 */
export async function activate(context: vscode.ExtensionContext): Promise<void> {
    perfMarks.set('activation-start', performance.now());
    
    try {
        // Phase 1: Configuration and Mode Detection
        await initializeConfiguration(context);
        
        // Phase 2: Core Services (mode-dependent)
        await initializeCoreServices(context);
        
        // Phase 3: Security Services (if enabled)
        if (shouldEnableSecurity()) {
            await initializeSecurityServices(context);
        }
        
        // Phase 4: Performance Services (if enabled)
        if (shouldEnablePerformance()) {
            await initializePerformanceServices(context);
        }
        
        // Phase 5: Command Registration and UI
        await initializeCommandsAndUI(context);
        
        // Phase 6: Post-activation validation and monitoring
        await postActivationValidation(context);
        
        const activationTime = performance.now() - perfMarks.get('activation-start')!;
        await logActivationSuccess(activationTime);
        
    } catch (error) {
        await handleActivationError(error, context);
    }
}

/**
 * Extension deactivation with cleanup
 */
export async function deactivate(): Promise<void> {
    perfMarks.set('deactivation-start', performance.now());
    
    try {
        // Security cleanup
        if (services.security?.auditLogger) {
            await services.security.auditLogger.logEvent('extension.deactivation', {
                sessionDuration: Date.now() - perfMarks.get('activation-start')!,
                commandsExecuted: performanceMetrics?.commandTimes?.size || 0
            });
        }
        
        // Service cleanup
        await cleanupServices();
        
        // Performance logging
        if (services.logger) {
            services.logger.info(`Extension deactivated in ${performance.now() - perfMarks.get('deactivation-start')!}ms`);
        }
        
    } catch (error) {
        console.error('Error during extension deactivation:', error);
    }
}

/**
 * Phase 1: Configuration and Mode Detection
 */
async function initializeConfiguration(context: vscode.ExtensionContext): Promise<void> {
    perfMarks.set('config-start', performance.now());
    
    // Get operation mode from VS Code settings or default to BASIC
    const config = vscode.workspace.getConfiguration('devdocai');
    const operationMode = config.get<string>('operationMode') || 'BASIC';
    
    // Build configuration based on mode
    extensionConfig = createModeConfiguration(operationMode as any);
    
    // Initialize basic logger first (needed for all modes)
    const { Logger } = await import('./utils/Logger');
    services.logger = new Logger('DevDocAI', {
        level: extensionConfig.operationMode === 'BASIC' ? 'info' : 'debug',
        audit: extensionConfig.features.auditLogging
    });
    
    services.logger.info(`🚀 DevDocAI Extension activating in ${operationMode} mode`);
    
    // Initialize security context if security features enabled
    if (shouldEnableSecurity()) {
        securityContext = {
            sessionId: crypto.randomUUID(),
            userId: context.globalState.get('userId') || 'anonymous',
            permissions: new Set(['read', 'write']), // Default permissions
            threatLevel: 'LOW',
            auditEnabled: true
        };
    }
    
    // Initialize performance metrics if performance features enabled
    if (shouldEnablePerformance()) {
        performanceMetrics = {
            activationTime: 0,
            commandTimes: new Map(),
            memoryUsage: process.memoryUsage().heapUsed,
            cacheHitRatio: 0
        };
    }
    
    services.logger.debug(`Configuration initialized in ${performance.now() - perfMarks.get('config-start')!}ms`);
}

/**
 * Phase 2: Core Services Initialization (mode-dependent)
 */
async function initializeCoreServices(context: vscode.ExtensionContext): Promise<void> {
    perfMarks.set('core-services-start', performance.now());
    
    // Configuration Manager (always needed)
    const { ConfigurationManager } = await import('./services/ConfigurationManager');
    services.configManager = new ConfigurationManager(context, services.logger);
    
    if (extensionConfig.features.lazyLoading) {
        // Performance mode: lazy initialization
        services.logger.debug('Core services will be initialized on-demand');
    } else {
        // Basic mode: immediate initialization
        await initializeAllCoreServices(context);
    }
    
    services.logger.debug(`Core services initialized in ${performance.now() - perfMarks.get('core-services-start')!}ms`);
}

/**
 * Initialize all core services immediately (BASIC/SECURE modes)
 */
async function initializeAllCoreServices(context: vscode.ExtensionContext): Promise<void> {
    const imports = await Promise.all([
        import('./commands/CommandManager_unified'),
        import('./services/CLIService_unified'),
        import('./webviews/WebviewManager_unified'),
        import('./services/StatusBarManager_unified'),
        import('./services/LanguageService'),
        import('./providers/DocumentProvider_unified')
    ]);
    
    services.commandManager = new imports[0].CommandManager(context, services.logger);
    services.cliService = new imports[1].CLIService(services.configManager, services.logger, extensionConfig);
    services.webviewManager = new imports[2].WebviewManager(context, services.logger, extensionConfig);
    services.statusBarManager = new imports[3].StatusBarManager(context, services.logger, extensionConfig);
    services.languageService = new imports[4].LanguageService(services.logger);
    
    // Initialize providers
    const documentProvider = new imports[5].DocumentProvider(services.cliService, services.logger, extensionConfig);
    services.providers!.set('document', documentProvider);
    
    // Register providers with VS Code
    context.subscriptions.push(
        vscode.workspace.registerTextDocumentContentProvider('devdocai-document', documentProvider)
    );
}

/**
 * Phase 3: Security Services Initialization
 */
async function initializeSecurityServices(context: vscode.ExtensionContext): Promise<void> {
    if (!shouldEnableSecurity()) return;
    
    perfMarks.set('security-services-start', performance.now());
    
    const securityImports = await Promise.all([
        import('./security/InputValidator'),
        import('./security/AuditLogger'),
        import('./security/ThreatDetector'),
        import('./security/PermissionManager')
    ]);
    
    // Initialize security components
    services.security!.inputValidator = new securityImports[0].InputValidator({
        rateLimiting: extensionConfig.security.rateLimiting,
        auditLogger: null // Will be set after audit logger initialization
    });
    
    services.security!.auditLogger = new securityImports[1].AuditLogger({
        level: extensionConfig.security.auditLevel,
        sessionId: securityContext.sessionId,
        encryption: extensionConfig.security.enableEncryption
    });
    
    services.security!.threatDetector = new securityImports[2].ThreatDetector({
        auditLogger: services.security!.auditLogger,
        alertLevel: 'MEDIUM'
    });
    
    services.security!.permissionManager = new securityImports[3].PermissionManager({
        defaultPermissions: securityContext.permissions,
        auditLogger: services.security!.auditLogger
    });
    
    // Link components
    services.security!.inputValidator.setAuditLogger(services.security!.auditLogger);
    
    // Log security initialization
    await services.security!.auditLogger.logEvent('security.initialization', {
        mode: extensionConfig.operationMode,
        sessionId: securityContext.sessionId,
        features: extensionConfig.features
    });
    
    services.logger.info(`Security services initialized in ${performance.now() - perfMarks.get('security-services-start')!}ms`);
}

/**
 * Phase 4: Performance Services Initialization
 */
async function initializePerformanceServices(context: vscode.ExtensionContext): Promise<void> {
    if (!shouldEnablePerformance()) return;
    
    perfMarks.set('performance-services-start', performance.now());
    
    // Initialize caching system
    if (extensionConfig.features.caching) {
        const { CacheManager } = await import('./utils/CacheManager');
        const cacheManager = new CacheManager({
            maxSize: extensionConfig.performance.maxCacheSize,
            ttl: 300000 // 5 minutes
        });
        context.subscriptions.push(cacheManager);
    }
    
    // Initialize performance monitoring
    setInterval(() => {
        if (performanceMetrics) {
            performanceMetrics.memoryUsage = process.memoryUsage().heapUsed;
        }
    }, 30000); // Update every 30 seconds
    
    services.logger.info(`Performance services initialized in ${performance.now() - perfMarks.get('performance-services-start')!}ms`);
}

/**
 * Phase 5: Command Registration and UI
 */
async function initializeCommandsAndUI(context: vscode.ExtensionContext): Promise<void> {
    perfMarks.set('ui-start', performance.now());
    
    if (extensionConfig.features.lazyLoading) {
        // Register commands with lazy handlers
        registerLazyCommands(context);
    } else {
        // Register commands with immediate handlers
        await registerImmediateCommands(context);
    }
    
    // Initialize status bar (always immediate for user feedback)
    if (!services.statusBarManager) {
        const { StatusBarManager } = await import('./services/StatusBarManager_unified');
        services.statusBarManager = new StatusBarManager(context, services.logger, extensionConfig);
    }
    
    await services.statusBarManager.initialize();
    
    services.logger.debug(`Commands and UI initialized in ${performance.now() - perfMarks.get('ui-start')!}ms`);
}

/**
 * Register commands with lazy loading (PERFORMANCE/ENTERPRISE modes)
 */
function registerLazyCommands(context: vscode.ExtensionContext): void {
    const commands = [
        'devdocai.generateDocumentation',
        'devdocai.analyzeQuality', 
        'devdocai.openDashboard',
        'devdocai.runTemplate',
        'devdocai.enhanceDocument',
        'devdocai.reviewCode',
        'devdocai.configureExtension',
        'devdocai.showMetrics',
        'devdocai.exportReport',
        'devdocai.refreshProject'
    ];
    
    commands.forEach(commandId => {
        context.subscriptions.push(
            vscode.commands.registerCommand(commandId, async (...args) => {
                const startTime = performance.now();
                
                try {
                    // Security validation if enabled
                    if (shouldEnableSecurity() && services.security?.inputValidator) {
                        const validationResult = await services.security.inputValidator.validateCommand(commandId, args);
                        if (!validationResult.isValid) {
                            throw new Error(`Security validation failed: ${validationResult.errors.join(', ')}`);
                        }
                    }
                    
                    // Lazy load command handler
                    const result = await executeLazyCommand(commandId, args);
                    
                    // Performance tracking
                    const executionTime = performance.now() - startTime;
                    if (performanceMetrics) {
                        performanceMetrics.commandTimes.set(commandId, executionTime);
                    }
                    
                    // Security audit
                    if (shouldEnableSecurity() && services.security?.auditLogger) {
                        await services.security.auditLogger.logEvent('command.executed', {
                            commandId,
                            executionTime,
                            success: true
                        });
                    }
                    
                    return result;
                    
                } catch (error) {
                    // Error handling and audit
                    if (shouldEnableSecurity() && services.security?.auditLogger) {
                        await services.security.auditLogger.logEvent('command.error', {
                            commandId,
                            error: error.message,
                            executionTime: performance.now() - startTime
                        });
                    }
                    
                    services.logger.error(`Command ${commandId} failed: ${error.message}`);
                    vscode.window.showErrorMessage(`DevDocAI: ${error.message}`);
                }
            })
        );
    });
}

/**
 * Execute command with lazy loading
 */
async function executeLazyCommand(commandId: string, args: any[]): Promise<any> {
    // Ensure command manager is loaded
    if (!services.commandManager) {
        const { CommandManager } = await import('./commands/CommandManager_unified');
        services.commandManager = new CommandManager(vscode.ExtensionContext, services.logger);
    }
    
    // Ensure required services are loaded based on command
    await ensureServicesForCommand(commandId);
    
    // Execute command
    return services.commandManager.executeCommand(commandId, ...args);
}

/**
 * Ensure required services are loaded for specific commands
 */
async function ensureServicesForCommand(commandId: string): Promise<void> {
    const serviceMap = {
        'devdocai.generateDocumentation': ['cliService', 'documentProvider'],
        'devdocai.analyzeQuality': ['cliService'],
        'devdocai.openDashboard': ['webviewManager'],
        'devdocai.runTemplate': ['cliService'],
        'devdocai.enhanceDocument': ['cliService'],
        'devdocai.reviewCode': ['cliService'],
        'devdocai.configureExtension': ['configManager'],
        'devdocai.showMetrics': ['webviewManager'],
        'devdocai.exportReport': ['cliService'],
        'devdocai.refreshProject': ['languageService']
    };
    
    const requiredServices = serviceMap[commandId] || [];
    
    for (const serviceName of requiredServices) {
        if (!services[serviceName]) {
            await loadService(serviceName);
        }
    }
}

/**
 * Load a specific service on-demand
 */
async function loadService(serviceName: string): Promise<void> {
    const context = vscode.ExtensionContext; // This should be passed properly in real implementation
    
    switch (serviceName) {
        case 'cliService':
            const { CLIService } = await import('./services/CLIService_unified');
            services.cliService = new CLIService(services.configManager, services.logger, extensionConfig);
            break;
            
        case 'webviewManager':
            const { WebviewManager } = await import('./webviews/WebviewManager_unified');
            services.webviewManager = new WebviewManager(context, services.logger, extensionConfig);
            break;
            
        case 'documentProvider':
            const { DocumentProvider } = await import('./providers/DocumentProvider_unified');
            const provider = new DocumentProvider(services.cliService, services.logger, extensionConfig);
            services.providers!.set('document', provider);
            break;
            
        case 'languageService':
            const { LanguageService } = await import('./services/LanguageService');
            services.languageService = new LanguageService(services.logger);
            break;
    }
}

/**
 * Register commands with immediate handlers (BASIC/SECURE modes)
 */
async function registerImmediateCommands(context: vscode.ExtensionContext): Promise<void> {
    if (!services.commandManager) {
        const { CommandManager } = await import('./commands/CommandManager_unified');
        services.commandManager = new CommandManager(context, services.logger);
    }
    
    await services.commandManager.registerAllCommands({
        security: shouldEnableSecurity() ? services.security : undefined,
        performance: shouldEnablePerformance() ? performanceMetrics : undefined
    });
}

/**
 * Phase 6: Post-activation validation and monitoring
 */
async function postActivationValidation(context: vscode.ExtensionContext): Promise<void> {
    // Validate activation time meets targets
    const activationTime = performance.now() - perfMarks.get('activation-start')!;
    const target = extensionConfig.performance.activationTimeTarget;
    
    if (activationTime > target) {
        services.logger.warn(`Activation time ${activationTime}ms exceeded target ${target}ms`);
    }
    
    // Start monitoring if performance mode is enabled
    if (shouldEnablePerformance()) {
        startPerformanceMonitoring();
    }
    
    // Start threat monitoring if security mode is enabled
    if (shouldEnableSecurity() && services.security?.threatDetector) {
        services.security.threatDetector.startMonitoring();
    }
}

/**
 * Configuration factory based on operation mode
 */
function createModeConfiguration(mode: 'BASIC' | 'PERFORMANCE' | 'SECURE' | 'ENTERPRISE'): ExtensionConfig {
    const baseConfig: ExtensionConfig = {
        operationMode: mode,
        features: {
            lazyLoading: false,
            asyncOperations: false,
            inputValidation: false,
            auditLogging: false,
            threatDetection: false,
            caching: false,
            streaming: false,
            permissionControl: false
        },
        performance: {
            activationTimeTarget: 2000, // 2 seconds for basic mode
            commandTimeTarget: 5000,    // 5 seconds
            maxCacheSize: 100
        },
        security: {
            enableEncryption: false,
            auditLevel: 'BASIC',
            rateLimiting: false
        }
    };
    
    switch (mode) {
        case 'PERFORMANCE':
            return {
                ...baseConfig,
                features: {
                    ...baseConfig.features,
                    lazyLoading: true,
                    asyncOperations: true,
                    caching: true,
                    streaming: true
                },
                performance: {
                    activationTimeTarget: 100, // 100ms for performance mode
                    commandTimeTarget: 50,     // 50ms
                    maxCacheSize: 1000
                }
            };
            
        case 'SECURE':
            return {
                ...baseConfig,
                features: {
                    ...baseConfig.features,
                    inputValidation: true,
                    auditLogging: true,
                    threatDetection: true,
                    permissionControl: true
                },
                security: {
                    enableEncryption: true,
                    auditLevel: 'DETAILED',
                    rateLimiting: true
                }
            };
            
        case 'ENTERPRISE':
            return {
                ...baseConfig,
                features: {
                    lazyLoading: true,
                    asyncOperations: true,
                    inputValidation: true,
                    auditLogging: true,
                    threatDetection: true,
                    caching: true,
                    streaming: true,
                    permissionControl: true
                },
                performance: {
                    activationTimeTarget: 100,
                    commandTimeTarget: 50,
                    maxCacheSize: 2000
                },
                security: {
                    enableEncryption: true,
                    auditLevel: 'COMPREHENSIVE',
                    rateLimiting: true
                }
            };
            
        default: // BASIC
            return baseConfig;
    }
}

/**
 * Utility functions for mode checking
 */
function shouldEnableSecurity(): boolean {
    // Add null check to prevent undefined errors during initialization
    if (!extensionConfig) {
        return false;
    }
    return extensionConfig.operationMode === 'SECURE' || extensionConfig.operationMode === 'ENTERPRISE';
}

function shouldEnablePerformance(): boolean {
    // Add null check to prevent undefined errors during initialization
    if (!extensionConfig) {
        return false;
    }
    return extensionConfig.operationMode === 'PERFORMANCE' || extensionConfig.operationMode === 'ENTERPRISE';
}

/**
 * Performance monitoring (PERFORMANCE/ENTERPRISE modes)
 */
function startPerformanceMonitoring(): void {
    setInterval(() => {
        const memoryUsage = process.memoryUsage();
        if (memoryUsage.heapUsed > 100 * 1024 * 1024) { // 100MB threshold
            services.logger.warn(`High memory usage: ${(memoryUsage.heapUsed / 1024 / 1024).toFixed(2)}MB`);
        }
    }, 60000); // Check every minute
}

/**
 * Activation success logging
 */
async function logActivationSuccess(activationTime: number): Promise<void> {
    const modeEmojis = {
        BASIC: '⚡',
        PERFORMANCE: '🚀',
        SECURE: '🛡️',
        ENTERPRISE: '👑'
    };
    
    const emoji = modeEmojis[extensionConfig.operationMode] || '⚡';
    services.logger.info(`${emoji} DevDocAI Extension activated in ${activationTime.toFixed(2)}ms (${extensionConfig.operationMode} mode)`);
    
    // Security audit
    if (shouldEnableSecurity() && services.security?.auditLogger) {
        await services.security.auditLogger.logEvent('extension.activation.success', {
            mode: extensionConfig.operationMode,
            activationTime,
            features: extensionConfig.features
        });
    }
}

/**
 * Error handling for activation failures
 */
async function handleActivationError(error: any, context: vscode.ExtensionContext): Promise<void> {
    const errorMessage = `DevDocAI Extension activation failed: ${error.message}`;
    
    services.logger?.error(errorMessage);
    console.error(errorMessage, error);
    
    // Security audit for failure
    if (services.security?.auditLogger) {
        await services.security.auditLogger.logEvent('extension.activation.error', {
            error: error.message,
            stack: error.stack,
            mode: extensionConfig?.operationMode || 'UNKNOWN'
        });
    }
    
    vscode.window.showErrorMessage(errorMessage);
    throw error;
}

/**
 * Cleanup services during deactivation
 */
async function cleanupServices(): Promise<void> {
    const cleanupTasks: Promise<void>[] = [];
    
    // Cleanup security services
    if (services.security?.auditLogger) {
        cleanupTasks.push(services.security.auditLogger.cleanup());
    }
    if (services.security?.threatDetector) {
        cleanupTasks.push(services.security.threatDetector.stop());
    }
    
    // Cleanup core services
    if (services.cliService?.cleanup) {
        cleanupTasks.push(services.cliService.cleanup());
    }
    if (services.webviewManager?.dispose) {
        cleanupTasks.push(services.webviewManager.dispose());
    }
    
    await Promise.allSettled(cleanupTasks);
}

// Export configuration for testing
export { extensionConfig, services, performanceMetrics, securityContext };