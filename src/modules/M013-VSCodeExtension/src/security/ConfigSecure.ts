/**
 * Secure Configuration Manager - M013 VS Code Extension
 * 
 * Provides secure storage and management of sensitive configuration data:
 * - API keys encrypted with VS Code SecretStorage
 * - Configuration validation and sanitization
 * - Secure secret rotation and management
 * - Integration with InputValidator for security
 * 
 * Replaces plain text storage in ConfigurationManager with enterprise-grade security.
 * 
 * @module M013-VSCodeExtension/Security
 * @version 3.0.0
 */

import * as vscode from 'vscode';
import * as crypto from 'crypto';
import { InputValidator, ValidationResult } from './InputValidator';

// Secure configuration interface
export interface SecureDevDocAIConfig {
    // Public configuration (stored in VS Code settings)
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
    telemetryEnabled: boolean;
    maxConcurrentOperations: number;
    cacheEnabled: boolean;
    cacheDirectory: string;
    exportFormats: string[];
    languageSupport: string[];
    customTemplatesPath: string;
    analysisDepth: string;
    securityRules: string[];
    ignorePaths: string[];
    
    // Security configuration
    encryptionEnabled: boolean;
    auditLogging: boolean;
    rateLimitEnabled: boolean;
    threatDetectionEnabled: boolean;
}

// Secret keys that should be stored securely
interface SecretKeys {
    openai_api_key?: string;
    anthropic_api_key?: string;
    google_api_key?: string;
    custom_llm_key?: string;
    encryption_key?: string;
    webhook_secret?: string;
}

// Security metadata for secrets
interface SecretMetadata {
    created: number;
    lastRotated: number;
    rotationDays: number;
    keyStrength: number;
}

export class ConfigSecure {
    private config: SecureDevDocAIConfig;
    private inputValidator: InputValidator;
    private watchers: vscode.Disposable[] = [];
    private secretMetadata: Map<string, SecretMetadata> = new Map();
    
    // Security configuration
    private readonly ENCRYPTION_ALGORITHM = 'aes-256-gcm';
    private readonly KEY_ROTATION_DAYS = 90; // Rotate keys every 90 days
    private readonly MIN_KEY_STRENGTH = 32;   // Minimum key length in bytes
    
    constructor(
        private context: vscode.ExtensionContext,
        inputValidator?: InputValidator
    ) {
        this.inputValidator = inputValidator || new InputValidator(context);
        this.config = this.loadSecureConfiguration();
        this.loadSecretMetadata();
    }
    
    /**
     * Initializes secure configuration manager
     */
    public async initialize(): Promise<void> {
        // Migrate existing plain text API keys to secure storage
        await this.migrateInsecureSecrets();
        
        // Watch for configuration changes
        this.watchers.push(
            vscode.workspace.onDidChangeConfiguration(async (e) => {
                if (e.affectsConfiguration('devdocai')) {
                    await this.reloadConfiguration();
                }
            })
        );
        
        // Setup key rotation timer
        this.setupKeyRotationTimer();
        
        // Load workspace-specific secure configuration
        await this.loadWorkspaceSecureConfig();
    }
    
    /**
     * Gets the current secure configuration
     */
    public getConfig(): SecureDevDocAIConfig {
        return { ...this.config };
    }
    
    /**
     * Updates a public configuration value with validation
     */
    public async updateConfig(key: string, value: any): Promise<ValidationResult> {
        // Validate configuration key and value
        const keyValidation = this.inputValidator.validateParameter(
            'configKey',
            key,
            { maxLength: 50, requireAlphanumeric: true }
        );
        
        if (!keyValidation.isValid) {
            return keyValidation;
        }
        
        const valueValidation = this.inputValidator.validateParameter(
            key,
            value,
            { maxLength: 1000 }
        );
        
        if (!valueValidation.isValid) {
            return valueValidation;
        }
        
        // Update VS Code configuration
        const config = vscode.workspace.getConfiguration('devdocai');
        await config.update(key, valueValidation.sanitized, vscode.ConfigurationTarget.Global);
        
        // Update local cache
        (this.config as any)[key] = valueValidation.sanitized;
        
        return {
            isValid: true,
            sanitized: valueValidation.sanitized,
            errors: [],
            warnings: [],
            securityScore: 100
        };
    }
    
    /**
     * Securely stores an API key or secret
     */
    public async storeSecret(
        secretName: keyof SecretKeys, 
        secretValue: string,
        metadata?: Partial<SecretMetadata>
    ): Promise<ValidationResult> {
        // Validate secret name
        const nameValidation = this.inputValidator.validateParameter(
            'secretName',
            secretName,
            { maxLength: 50, requireAlphanumeric: true }
        );
        
        if (!nameValidation.isValid) {
            return nameValidation;
        }
        
        // Validate secret value strength
        const strengthValidation = this.validateSecretStrength(secretValue);
        if (!strengthValidation.isValid) {
            return strengthValidation;
        }
        
        try {
            // Encrypt secret before storage
            const encryptedSecret = this.config.encryptionEnabled 
                ? await this.encryptSecret(secretValue)
                : secretValue;
            
            // Store in VS Code SecretStorage
            await this.context.secrets.store(secretName, encryptedSecret);
            
            // Store metadata
            const secretMetadata: SecretMetadata = {
                created: Date.now(),
                lastRotated: Date.now(),
                rotationDays: metadata?.rotationDays || this.KEY_ROTATION_DAYS,
                keyStrength: secretValue.length,
                ...metadata
            };
            
            this.secretMetadata.set(secretName, secretMetadata);
            await this.saveSecretMetadata();
            
            return {
                isValid: true,
                errors: [],
                warnings: [],
                securityScore: 100
            };
            
        } catch (error) {
            return {
                isValid: false,
                errors: [`Failed to store secret: ${error instanceof Error ? error.message : 'Unknown error'}`],
                warnings: [],
                securityScore: 0
            };
        }
    }
    
    /**
     * Securely retrieves an API key or secret
     */
    public async getSecret(secretName: keyof SecretKeys): Promise<string | undefined> {
        try {
            const encryptedSecret = await this.context.secrets.get(secretName);
            if (!encryptedSecret) {
                return undefined;
            }
            
            // Decrypt if encryption is enabled
            if (this.config.encryptionEnabled) {
                return await this.decryptSecret(encryptedSecret);
            }
            
            return encryptedSecret;
            
        } catch (error) {
            console.error(`Failed to retrieve secret ${secretName}:`, error);
            return undefined;
        }
    }
    
    /**
     * Deletes a secret from secure storage
     */
    public async deleteSecret(secretName: keyof SecretKeys): Promise<ValidationResult> {
        try {
            await this.context.secrets.delete(secretName);
            this.secretMetadata.delete(secretName);
            await this.saveSecretMetadata();
            
            return {
                isValid: true,
                errors: [],
                warnings: [],
                securityScore: 100
            };
            
        } catch (error) {
            return {
                isValid: false,
                errors: [`Failed to delete secret: ${error instanceof Error ? error.message : 'Unknown error'}`],
                warnings: [],
                securityScore: 0
            };
        }
    }
    
    /**
     * Checks if LLM credentials are securely configured
     */
    public async hasSecureLLMCredentials(): Promise<boolean> {
        switch (this.config.llmProvider) {
            case 'openai':
                return (await this.getSecret('openai_api_key')) !== undefined;
            case 'anthropic':
                return (await this.getSecret('anthropic_api_key')) !== undefined;
            case 'google':
                return (await this.getSecret('google_api_key')) !== undefined;
            case 'local':
                return true; // Local doesn't need credentials
            default:
                return false;
        }
    }
    
    /**
     * Rotates API keys that are due for rotation
     */
    public async rotateExpiredKeys(): Promise<string[]> {
        const rotatedKeys: string[] = [];
        const now = Date.now();
        
        for (const [secretName, metadata] of this.secretMetadata.entries()) {
            const daysSinceRotation = (now - metadata.lastRotated) / (1000 * 60 * 60 * 24);
            
            if (daysSinceRotation >= metadata.rotationDays) {
                // For API keys, we can't automatically rotate them
                // Just notify the user
                const message = `API key '${secretName}' is due for rotation (${Math.floor(daysSinceRotation)} days old)`;
                vscode.window.showWarningMessage(
                    message,
                    'Rotate Now',
                    'Remind Later'
                ).then(selection => {
                    if (selection === 'Rotate Now') {
                        vscode.commands.executeCommand('devdocai.configureApiKeys');
                    }
                });
                
                rotatedKeys.push(secretName);
            }
        }
        
        return rotatedKeys;
    }
    
    /**
     * Validates secret strength
     */
    private validateSecretStrength(secret: string): ValidationResult {
        const result: ValidationResult = {
            isValid: true,
            errors: [],
            warnings: [],
            securityScore: 100
        };
        
        // Check minimum length
        if (secret.length < this.MIN_KEY_STRENGTH) {
            result.isValid = false;
            result.errors.push(`Secret must be at least ${this.MIN_KEY_STRENGTH} characters`);
            result.securityScore = 0;
        }
        
        // Check for common weak patterns
        const weakPatterns = [
            /^[a-z]+$/,           // All lowercase
            /^[A-Z]+$/,           // All uppercase
            /^[0-9]+$/,           // All numeric
            /^(.)\1+$/,           // Repeated character
            /password|secret|key|admin/i  // Common words
        ];
        
        for (const pattern of weakPatterns) {
            if (pattern.test(secret)) {
                result.warnings.push('Secret appears to be weak');
                result.securityScore -= 20;
                break;
            }
        }
        
        // Check entropy
        const entropy = this.calculateEntropy(secret);
        if (entropy < 4.0) {
            result.warnings.push('Secret has low entropy');
            result.securityScore -= 15;
        }
        
        return result;
    }
    
    /**
     * Calculates entropy of a string
     */
    private calculateEntropy(str: string): number {
        const frequencies = new Map<string, number>();
        
        for (const char of str) {
            frequencies.set(char, (frequencies.get(char) || 0) + 1);
        }
        
        let entropy = 0;
        for (const freq of frequencies.values()) {
            const probability = freq / str.length;
            entropy -= probability * Math.log2(probability);
        }
        
        return entropy;
    }
    
    /**
     * Encrypts a secret using AES-256-GCM
     */
    private async encryptSecret(secret: string): Promise<string> {
        const key = await this.getOrCreateEncryptionKey();
        const iv = crypto.randomBytes(12); // GCM requires 12-byte IV
        const cipher = crypto.createCipher(this.ENCRYPTION_ALGORITHM, key);
        
        let encrypted = cipher.update(secret, 'utf8', 'hex');
        encrypted += cipher.final('hex');
        
        const authTag = cipher.getAuthTag();
        
        // Return iv + authTag + encrypted data as hex string
        return iv.toString('hex') + authTag.toString('hex') + encrypted;
    }
    
    /**
     * Decrypts a secret using AES-256-GCM
     */
    private async decryptSecret(encryptedSecret: string): Promise<string> {
        const key = await this.getOrCreateEncryptionKey();
        
        // Extract IV (24 chars), auth tag (32 chars), and encrypted data
        const iv = Buffer.from(encryptedSecret.substring(0, 24), 'hex');
        const authTag = Buffer.from(encryptedSecret.substring(24, 56), 'hex');
        const encrypted = encryptedSecret.substring(56);
        
        const decipher = crypto.createDecipher(this.ENCRYPTION_ALGORITHM, key);
        decipher.setAuthTag(authTag);
        
        let decrypted = decipher.update(encrypted, 'hex', 'utf8');
        decrypted += decipher.final('utf8');
        
        return decrypted;
    }
    
    /**
     * Gets or creates the encryption key
     */
    private async getOrCreateEncryptionKey(): Promise<Buffer> {
        let encryptionKey = await this.getSecret('encryption_key');
        
        if (!encryptionKey) {
            // Generate new encryption key
            encryptionKey = crypto.randomBytes(32).toString('hex');
            await this.storeSecret('encryption_key', encryptionKey);
        }
        
        return Buffer.from(encryptionKey, 'hex');
    }
    
    /**
     * Migrates insecure secrets from globalState to SecretStorage
     */
    private async migrateInsecureSecrets(): Promise<void> {
        const secretKeys: (keyof SecretKeys)[] = [
            'openai_api_key',
            'anthropic_api_key',
            'google_api_key'
        ];
        
        let migratedCount = 0;
        
        for (const secretName of secretKeys) {
            // Check if secret exists in insecure globalState
            const insecureValue = this.context.globalState.get<string>(secretName);
            if (insecureValue) {
                // Move to secure storage
                const result = await this.storeSecret(secretName, insecureValue);
                if (result.isValid) {
                    // Remove from globalState
                    await this.context.globalState.update(secretName, undefined);
                    migratedCount++;
                }
            }
        }
        
        if (migratedCount > 0) {
            vscode.window.showInformationMessage(
                `Migrated ${migratedCount} API key(s) to secure storage`
            );
        }
    }
    
    /**
     * Loads secure configuration from VS Code settings
     */
    private loadSecureConfiguration(): SecureDevDocAIConfig {
        const vsConfig = vscode.workspace.getConfiguration('devdocai');
        
        return {
            // Original configuration
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
            ]),
            
            // Security configuration
            encryptionEnabled: vsConfig.get('encryptionEnabled', true),
            auditLogging: vsConfig.get('auditLogging', true),
            rateLimitEnabled: vsConfig.get('rateLimitEnabled', true),
            threatDetectionEnabled: vsConfig.get('threatDetectionEnabled', true)
        };
    }
    
    /**
     * Loads workspace-specific secure configuration
     */
    private async loadWorkspaceSecureConfig(): Promise<void> {
        const workspaceFolder = vscode.workspace.workspaceFolders?.[0];
        if (!workspaceFolder) {
            return;
        }
        
        // This implementation would load secure workspace configuration
        // For now, we'll use the standard configuration approach
    }
    
    /**
     * Reloads configuration
     */
    private async reloadConfiguration(): Promise<void> {
        this.config = this.loadSecureConfiguration();
        await this.loadWorkspaceSecureConfig();
    }
    
    /**
     * Sets up automatic key rotation timer
     */
    private setupKeyRotationTimer(): void {
        // Check for expired keys daily
        setInterval(async () => {
            await this.rotateExpiredKeys();
        }, 24 * 60 * 60 * 1000); // Daily
        
        // Initial check
        setTimeout(async () => {
            await this.rotateExpiredKeys();
        }, 5000); // Check after 5 seconds of initialization
    }
    
    /**
     * Loads secret metadata from context
     */
    private loadSecretMetadata(): void {
        const metadata = this.context.globalState.get<any>('secretMetadata', {});
        for (const [key, value] of Object.entries(metadata)) {
            this.secretMetadata.set(key, value as SecretMetadata);
        }
    }
    
    /**
     * Saves secret metadata to context
     */
    private async saveSecretMetadata(): Promise<void> {
        const metadata = Object.fromEntries(this.secretMetadata);
        await this.context.globalState.update('secretMetadata', metadata);
    }
    
    /**
     * Gets security configuration summary
     */
    public getSecuritySummary(): any {
        return {
            encryptionEnabled: this.config.encryptionEnabled,
            auditLogging: this.config.auditLogging,
            rateLimitEnabled: this.config.rateLimitEnabled,
            threatDetectionEnabled: this.config.threatDetectionEnabled,
            secretsStored: this.secretMetadata.size,
            keysNeedingRotation: Array.from(this.secretMetadata.entries())
                .filter(([_, metadata]) => {
                    const daysSince = (Date.now() - metadata.lastRotated) / (1000 * 60 * 60 * 24);
                    return daysSince >= metadata.rotationDays;
                }).length
        };
    }
    
    /**
     * Disposes secure configuration manager
     */
    public dispose(): void {
        for (const watcher of this.watchers) {
            watcher.dispose();
        }
        this.watchers = [];
        this.secretMetadata.clear();
    }
}