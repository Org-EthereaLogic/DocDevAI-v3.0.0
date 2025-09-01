/**
 * Open Dashboard Command
 * 
 * Opens the DevDocAI dashboard in a webview panel.
 */

import * as vscode from 'vscode';
import { CLIService } from '../services/CLIService';
import { WebviewManager } from '../webviews/WebviewManager';
import { Logger } from '../utils/Logger';
import { Command } from './CommandManager';

export class OpenDashboardCommand implements Command {
    constructor(
        private webviewManager: WebviewManager,
        private cliService: CLIService,
        private logger: Logger
    ) {}
    
    public async execute(...args: any[]): Promise<void> {
        try {
            this.logger.info('Opening DevDocAI dashboard');
            
            // Gather metrics for dashboard
            const metrics = await this.gatherMetrics();
            
            // Show dashboard with metrics
            await this.webviewManager.showDashboard(metrics);
            
            this.logger.info('Dashboard opened successfully');
            
        } catch (error) {
            this.logger.error('Failed to open dashboard', error);
            vscode.window.showErrorMessage(
                `Failed to open dashboard: ${error instanceof Error ? error.message : 'Unknown error'}`
            );
        }
    }
    
    /**
     * Gathers metrics for the dashboard
     */
    private async gatherMetrics(): Promise<DashboardMetrics> {
        const metrics: DashboardMetrics = {
            coverage: 0,
            quality: 0,
            security: 0,
            files: 0,
            activity: []
        };
        
        try {
            // Get workspace information
            const workspaceFolder = vscode.workspace.workspaceFolders?.[0];
            if (!workspaceFolder) {
                return metrics;
            }
            
            // Count documented files
            const allFiles = await vscode.workspace.findFiles(
                '**/*.{py,ts,tsx,js,jsx,java,c,cpp,cs,go,rs}',
                '**/node_modules/**'
            );
            
            const docFiles = await vscode.workspace.findFiles(
                '**/*.{md,rst,txt}',
                '**/node_modules/**'
            );
            
            metrics.files = allFiles.length;
            
            // Calculate coverage (simplified)
            if (allFiles.length > 0) {
                metrics.coverage = Math.round((docFiles.length / allFiles.length) * 100);
            }
            
            // Get average quality score (mock for now, would aggregate from actual analysis)
            metrics.quality = await this.getAverageQuality(docFiles);
            
            // Get security score (mock for now)
            metrics.security = 85; // Would come from security scan
            
            // Get recent activity
            metrics.activity = await this.getRecentActivity();
            
        } catch (error) {
            this.logger.error('Failed to gather metrics', error);
        }
        
        return metrics;
    }
    
    /**
     * Gets average quality score for documentation
     */
    private async getAverageQuality(docFiles: vscode.Uri[]): Promise<number> {
        if (docFiles.length === 0) {
            return 0;
        }
        
        // In a real implementation, this would analyze each file
        // For now, return a mock value
        return 75;
    }
    
    /**
     * Gets recent activity
     */
    private async getRecentActivity(): Promise<ActivityItem[]> {
        const activities: ActivityItem[] = [];
        
        // Get recent file changes
        const recentFiles = await this.getRecentlyModifiedFiles();
        
        recentFiles.forEach(file => {
            activities.push({
                icon: 'file-text',
                text: `Modified ${file.name}`,
                time: this.formatTime(file.modified)
            });
        });
        
        // Add some mock activities for demonstration
        if (activities.length === 0) {
            activities.push(
                {
                    icon: 'file-text',
                    text: 'Documentation generated for api.py',
                    time: '2 hours ago'
                },
                {
                    icon: 'checklist',
                    text: 'Quality analysis completed',
                    time: '3 hours ago'
                },
                {
                    icon: 'shield',
                    text: 'Security scan passed',
                    time: 'Yesterday'
                }
            );
        }
        
        return activities.slice(0, 10); // Limit to 10 most recent
    }
    
    /**
     * Gets recently modified files
     */
    private async getRecentlyModifiedFiles(): Promise<Array<{ name: string, modified: Date }>> {
        const files: Array<{ name: string, modified: Date }> = [];
        
        // This would use file system watchers in a real implementation
        // For now, return empty array
        
        return files;
    }
    
    /**
     * Formats time for display
     */
    private formatTime(date: Date): string {
        const now = new Date();
        const diff = now.getTime() - date.getTime();
        const minutes = Math.floor(diff / 60000);
        const hours = Math.floor(diff / 3600000);
        const days = Math.floor(diff / 86400000);
        
        if (minutes < 1) {
            return 'Just now';
        } else if (minutes < 60) {
            return `${minutes} minute${minutes > 1 ? 's' : ''} ago`;
        } else if (hours < 24) {
            return `${hours} hour${hours > 1 ? 's' : ''} ago`;
        } else if (days < 7) {
            return `${days} day${days > 1 ? 's' : ''} ago`;
        } else {
            return date.toLocaleDateString();
        }
    }
}

/**
 * Dashboard metrics interface
 */
interface DashboardMetrics {
    coverage: number;
    quality: number;
    security: number;
    files: number;
    activity: ActivityItem[];
}

/**
 * Activity item interface
 */
interface ActivityItem {
    icon: string;
    text: string;
    time: string;
}