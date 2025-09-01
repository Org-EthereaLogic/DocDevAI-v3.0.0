/**
 * Extension Context utility for DevDocAI VS Code Extension
 * 
 * Manages extension state, persistence, and context information.
 */

import * as vscode from 'vscode';
import * as path from 'path';
import * as fs from 'fs';

export class ExtensionContext {
    private static readonly STATE_KEY_PREFIX = 'devdocai.';
    private static readonly FIRST_ACTIVATION_KEY = 'firstActivation';
    private static readonly LAST_VERSION_KEY = 'lastVersion';
    private static readonly USAGE_STATS_KEY = 'usageStats';
    
    constructor(private context: vscode.ExtensionContext) {}
    
    /**
     * Checks if this is the first activation
     */
    public isFirstActivation(): boolean {
        const firstActivation = this.context.globalState.get(
            `${ExtensionContext.STATE_KEY_PREFIX}${ExtensionContext.FIRST_ACTIVATION_KEY}`,
            true
        );
        
        if (firstActivation) {
            // Mark as not first activation anymore
            this.context.globalState.update(
                `${ExtensionContext.STATE_KEY_PREFIX}${ExtensionContext.FIRST_ACTIVATION_KEY}`,
                false
            );
        }
        
        return firstActivation;
    }
    
    /**
     * Checks if extension was updated
     */
    public isUpdated(): boolean {
        const extension = vscode.extensions.getExtension('devdocai.devdocai');
        if (!extension) {
            return false;
        }
        
        const currentVersion = extension.packageJSON.version;
        const lastVersion = this.context.globalState.get(
            `${ExtensionContext.STATE_KEY_PREFIX}${ExtensionContext.LAST_VERSION_KEY}`
        );
        
        if (currentVersion !== lastVersion) {
            // Update stored version
            this.context.globalState.update(
                `${ExtensionContext.STATE_KEY_PREFIX}${ExtensionContext.LAST_VERSION_KEY}`,
                currentVersion
            );
            return true;
        }
        
        return false;
    }
    
    /**
     * Gets extension version
     */
    public getVersion(): string {
        const extension = vscode.extensions.getExtension('devdocai.devdocai');
        return extension?.packageJSON.version || '0.0.0';
    }
    
    /**
     * Gets extension path
     */
    public getExtensionPath(): string {
        return this.context.extensionPath;
    }
    
    /**
     * Gets storage path for extension data
     */
    public getStoragePath(): string | undefined {
        return this.context.storagePath;
    }
    
    /**
     * Gets global storage path
     */
    public getGlobalStoragePath(): string | undefined {
        return this.context.globalStorageUri?.fsPath;
    }
    
    /**
     * Saves state value
     */
    public async saveState(key: string, value: any): Promise<void> {
        await this.context.globalState.update(
            `${ExtensionContext.STATE_KEY_PREFIX}${key}`,
            value
        );
    }
    
    /**
     * Gets state value
     */
    public getState<T>(key: string, defaultValue?: T): T | undefined {
        return this.context.globalState.get(
            `${ExtensionContext.STATE_KEY_PREFIX}${key}`,
            defaultValue
        );
    }
    
    /**
     * Clears state value
     */
    public async clearState(key: string): Promise<void> {
        await this.context.globalState.update(
            `${ExtensionContext.STATE_KEY_PREFIX}${key}`,
            undefined
        );
    }
    
    /**
     * Gets all state keys
     */
    public getStateKeys(): readonly string[] {
        return this.context.globalState.keys();
    }
    
    /**
     * Records usage statistics
     */
    public async recordUsage(action: string): Promise<void> {
        const stats = this.getUsageStats();
        
        if (!stats[action]) {
            stats[action] = {
                count: 0,
                lastUsed: null
            };
        }
        
        stats[action].count++;
        stats[action].lastUsed = new Date().toISOString();
        
        await this.saveState(ExtensionContext.USAGE_STATS_KEY, stats);
    }
    
    /**
     * Gets usage statistics
     */
    public getUsageStats(): UsageStats {
        return this.getState(ExtensionContext.USAGE_STATS_KEY, {}) as UsageStats;
    }
    
    /**
     * Clears usage statistics
     */
    public async clearUsageStats(): Promise<void> {
        await this.clearState(ExtensionContext.USAGE_STATS_KEY);
    }
    
    /**
     * Gets workspace state
     */
    public getWorkspaceState<T>(key: string, defaultValue?: T): T | undefined {
        return this.context.workspaceState.get(
            `${ExtensionContext.STATE_KEY_PREFIX}${key}`,
            defaultValue
        );
    }
    
    /**
     * Saves workspace state
     */
    public async saveWorkspaceState(key: string, value: any): Promise<void> {
        await this.context.workspaceState.update(
            `${ExtensionContext.STATE_KEY_PREFIX}${key}`,
            value
        );
    }
    
    /**
     * Stores a secret
     */
    public async storeSecret(key: string, value: string): Promise<void> {
        await this.context.secrets.store(
            `${ExtensionContext.STATE_KEY_PREFIX}${key}`,
            value
        );
    }
    
    /**
     * Gets a secret
     */
    public async getSecret(key: string): Promise<string | undefined> {
        return await this.context.secrets.get(
            `${ExtensionContext.STATE_KEY_PREFIX}${key}`
        );
    }
    
    /**
     * Deletes a secret
     */
    public async deleteSecret(key: string): Promise<void> {
        await this.context.secrets.delete(
            `${ExtensionContext.STATE_KEY_PREFIX}${key}`
        );
    }
    
    /**
     * Creates a cache directory
     */
    public async createCacheDirectory(): Promise<string> {
        const globalStoragePath = this.getGlobalStoragePath();
        if (!globalStoragePath) {
            throw new Error('No global storage path available');
        }
        
        const cachePath = path.join(globalStoragePath, 'cache');
        
        if (!fs.existsSync(cachePath)) {
            fs.mkdirSync(cachePath, { recursive: true });
        }
        
        return cachePath;
    }
    
    /**
     * Clears cache directory
     */
    public async clearCache(): Promise<void> {
        const globalStoragePath = this.getGlobalStoragePath();
        if (!globalStoragePath) {
            return;
        }
        
        const cachePath = path.join(globalStoragePath, 'cache');
        
        if (fs.existsSync(cachePath)) {
            // Remove all files in cache
            const files = fs.readdirSync(cachePath);
            for (const file of files) {
                fs.unlinkSync(path.join(cachePath, file));
            }
        }
    }
    
    /**
     * Gets cache file path
     */
    public getCacheFilePath(filename: string): string {
        const globalStoragePath = this.getGlobalStoragePath();
        if (!globalStoragePath) {
            throw new Error('No global storage path available');
        }
        
        return path.join(globalStoragePath, 'cache', filename);
    }
    
    /**
     * Checks if running in development mode
     */
    public isDevelopment(): boolean {
        return this.context.extensionMode === vscode.ExtensionMode.Development;
    }
    
    /**
     * Checks if running in test mode
     */
    public isTest(): boolean {
        return this.context.extensionMode === vscode.ExtensionMode.Test;
    }
    
    /**
     * Gets subscription array for disposables
     */
    public get subscriptions(): vscode.Disposable[] {
        return this.context.subscriptions;
    }
    
    /**
     * Shows release notes
     */
    public async showReleaseNotes(): Promise<void> {
        const releaseNotesPath = path.join(this.context.extensionPath, 'CHANGELOG.md');
        
        if (fs.existsSync(releaseNotesPath)) {
            const uri = vscode.Uri.file(releaseNotesPath);
            await vscode.commands.executeCommand('markdown.showPreview', uri);
        }
    }
    
    /**
     * Gets telemetry reporter (if enabled)
     */
    public getTelemetryReporter(): any | undefined {
        // Only return if telemetry is explicitly enabled
        const config = vscode.workspace.getConfiguration('devdocai');
        if (config.get('telemetryEnabled') === true) {
            // Telemetry implementation would go here
            return undefined;
        }
        return undefined;
    }
    
    /**
     * Logs extension activation
     */
    public async logActivation(): Promise<void> {
        await this.recordUsage('activation');
        
        // Log additional activation details
        const activationLog = {
            timestamp: new Date().toISOString(),
            version: this.getVersion(),
            mode: this.context.extensionMode,
            workspace: vscode.workspace.name || 'unknown'
        };
        
        await this.saveState('lastActivation', activationLog);
    }
    
    /**
     * Saves all state before deactivation
     */
    public async saveState(): Promise<void> {
        // Save current timestamp
        await this.saveState('lastDeactivation', new Date().toISOString());
        
        // Save workspace information
        if (vscode.workspace.workspaceFolders) {
            const workspaceInfo = {
                folders: vscode.workspace.workspaceFolders.map(f => f.uri.fsPath),
                name: vscode.workspace.name
            };
            await this.saveWorkspaceState('lastWorkspace', workspaceInfo);
        }
    }
}

/**
 * Usage statistics interface
 */
interface UsageStats {
    [action: string]: {
        count: number;
        lastUsed: string | null;
    };
}