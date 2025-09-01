/**
 * Analyze Quality Command
 * 
 * Analyzes documentation quality and provides improvement suggestions.
 */

import * as vscode from 'vscode';
import { CLIService } from '../services/CLIService';
import { Logger } from '../utils/Logger';
import { Command } from './CommandManager';

export class AnalyzeQualityCommand implements Command {
    constructor(
        private cliService: CLIService,
        private logger: Logger
    ) {}
    
    public async execute(...args: any[]): Promise<void> {
        try {
            // Determine target document
            const uri = this.getTargetUri(args);
            
            if (!uri) {
                vscode.window.showWarningMessage('No document selected for quality analysis');
                return;
            }
            
            // Check if it's a markdown file
            const document = await vscode.workspace.openTextDocument(uri);
            if (document.languageId !== 'markdown') {
                const action = await vscode.window.showWarningMessage(
                    'Quality analysis works best on markdown documentation files. Continue anyway?',
                    'Continue',
                    'Cancel'
                );
                
                if (action !== 'Continue') {
                    return;
                }
            }
            
            // Analyze with progress
            await vscode.window.withProgress({
                location: vscode.ProgressLocation.Notification,
                title: 'Analyzing documentation quality...',
                cancellable: false
            }, async (progress) => {
                progress.report({ increment: 0, message: 'Reading document...' });
                
                // Get quality analysis
                progress.report({ increment: 50, message: 'Running quality checks...' });
                const result = await this.cliService.analyzeQuality(uri.fsPath);
                
                progress.report({ increment: 50, message: 'Preparing results...' });
                
                // Show results
                await this.showQualityResults(document, result);
            });
            
        } catch (error) {
            this.logger.error('Quality analysis failed', error);
            vscode.window.showErrorMessage(
                `Quality analysis failed: ${error instanceof Error ? error.message : 'Unknown error'}`
            );
        }
    }
    
    /**
     * Gets target URI from arguments or active editor
     */
    private getTargetUri(args: any[]): vscode.Uri | undefined {
        // From arguments (context menu or command)
        if (args[0] instanceof vscode.Uri) {
            return args[0];
        }
        
        // From active editor
        const editor = vscode.window.activeTextEditor;
        if (editor) {
            return editor.document.uri;
        }
        
        return undefined;
    }
    
    /**
     * Shows quality analysis results
     */
    private async showQualityResults(document: vscode.TextDocument, result: any): Promise<void> {
        // Create quality report
        const report = this.createQualityReport(result);
        
        // Show in new document
        const reportDoc = await vscode.workspace.openTextDocument({
            language: 'markdown',
            content: report
        });
        
        await vscode.window.showTextDocument(reportDoc, vscode.ViewColumn.Beside);
        
        // Add diagnostics if there are issues
        if (result.issues && result.issues.length > 0) {
            this.addDiagnostics(document, result.issues);
        }
        
        // Show summary notification
        const scoreEmoji = this.getScoreEmoji(result.score);
        const message = `Documentation Quality: ${result.score}/100 ${scoreEmoji}`;
        
        if (result.score >= 80) {
            vscode.window.showInformationMessage(message);
        } else if (result.score >= 60) {
            const action = await vscode.window.showWarningMessage(
                message,
                'Show Suggestions',
                'Improve Now'
            );
            
            if (action === 'Show Suggestions') {
                this.showSuggestions(result.suggestions);
            } else if (action === 'Improve Now') {
                await vscode.commands.executeCommand(
                    'devdocai.generateDocumentation',
                    document.uri
                );
            }
        } else {
            const action = await vscode.window.showErrorMessage(
                message,
                'Generate New Documentation',
                'View Issues'
            );
            
            if (action === 'Generate New Documentation') {
                await vscode.commands.executeCommand(
                    'devdocai.generateDocumentation',
                    document.uri
                );
            } else if (action === 'View Issues') {
                vscode.commands.executeCommand('workbench.actions.view.problems');
            }
        }
    }
    
    /**
     * Creates quality report markdown
     */
    private createQualityReport(result: any): string {
        const lines: string[] = [
            '# Documentation Quality Report',
            '',
            `Generated: ${new Date().toLocaleString()}`,
            '',
            '## Overall Score',
            '',
            `### ${result.score}/100 ${this.getScoreEmoji(result.score)}`,
            '',
            '## Detailed Metrics',
            '',
            '| Metric | Score | Status |',
            '|--------|-------|--------|',
            `| Completeness | ${result.completeness}% | ${this.getStatusIcon(result.completeness)} |`,
            `| Clarity | ${result.clarity}% | ${this.getStatusIcon(result.clarity)} |`,
            `| Accuracy | ${result.accuracy}% | ${this.getStatusIcon(result.accuracy)} |`,
            `| Maintainability | ${result.maintainability}% | ${this.getStatusIcon(result.maintainability)} |`,
            ''
        ];
        
        // Add suggestions
        if (result.suggestions && result.suggestions.length > 0) {
            lines.push('## Improvement Suggestions', '');
            result.suggestions.forEach((suggestion: string, index: number) => {
                lines.push(`${index + 1}. ${suggestion}`);
            });
            lines.push('');
        }
        
        // Add issues
        if (result.issues && result.issues.length > 0) {
            lines.push('## Issues Found', '');
            
            // Group issues by severity
            const critical = result.issues.filter((i: any) => i.severity === 'error');
            const warnings = result.issues.filter((i: any) => i.severity === 'warning');
            const info = result.issues.filter((i: any) => i.severity === 'information');
            
            if (critical.length > 0) {
                lines.push('### Critical Issues', '');
                critical.forEach((issue: any) => {
                    lines.push(`- **Line ${issue.line}**: ${issue.message}`);
                });
                lines.push('');
            }
            
            if (warnings.length > 0) {
                lines.push('### Warnings', '');
                warnings.forEach((issue: any) => {
                    lines.push(`- **Line ${issue.line}**: ${issue.message}`);
                });
                lines.push('');
            }
            
            if (info.length > 0) {
                lines.push('### Information', '');
                info.forEach((issue: any) => {
                    lines.push(`- **Line ${issue.line}**: ${issue.message}`);
                });
                lines.push('');
            }
        }
        
        // Add recommendations
        lines.push('## Recommendations', '');
        
        if (result.score >= 80) {
            lines.push('✅ Your documentation meets quality standards!');
            lines.push('');
            lines.push('Consider:');
            lines.push('- Regular updates to keep documentation current');
            lines.push('- Adding more examples if applicable');
            lines.push('- Peer review for accuracy');
        } else if (result.score >= 60) {
            lines.push('⚠️ Your documentation needs some improvements.');
            lines.push('');
            lines.push('Priority actions:');
            lines.push('- Address critical issues first');
            lines.push('- Improve clarity and completeness');
            lines.push('- Add missing sections');
        } else {
            lines.push('❌ Your documentation requires significant improvements.');
            lines.push('');
            lines.push('Immediate actions:');
            lines.push('- Consider regenerating documentation');
            lines.push('- Address all critical issues');
            lines.push('- Review documentation structure');
            lines.push('- Add comprehensive examples');
        }
        
        return lines.join('\n');
    }
    
    /**
     * Adds diagnostics for issues
     */
    private addDiagnostics(document: vscode.TextDocument, issues: any[]): void {
        const diagnostics: vscode.Diagnostic[] = [];
        
        for (const issue of issues) {
            const line = issue.line ? issue.line - 1 : 0;
            const range = new vscode.Range(
                line, 0,
                line, document.lineAt(line).text.length
            );
            
            const severity = this.getSeverity(issue.severity);
            const diagnostic = new vscode.Diagnostic(
                range,
                issue.message,
                severity
            );
            
            diagnostic.source = 'DevDocAI';
            diagnostic.code = issue.code;
            
            diagnostics.push(diagnostic);
        }
        
        // Set diagnostics
        const collection = vscode.languages.createDiagnosticCollection('devdocai');
        collection.set(document.uri, diagnostics);
    }
    
    /**
     * Shows suggestions in a quick pick
     */
    private async showSuggestions(suggestions: string[]): Promise<void> {
        if (!suggestions || suggestions.length === 0) {
            vscode.window.showInformationMessage('No suggestions available');
            return;
        }
        
        const items = suggestions.map((suggestion, index) => ({
            label: `$(lightbulb) Suggestion ${index + 1}`,
            description: suggestion,
            detail: 'Click to copy to clipboard'
        }));
        
        const selected = await vscode.window.showQuickPick(items, {
            placeHolder: 'Select a suggestion to copy',
            title: 'Documentation Improvement Suggestions'
        });
        
        if (selected) {
            await vscode.env.clipboard.writeText(selected.description);
            vscode.window.showInformationMessage('Suggestion copied to clipboard');
        }
    }
    
    /**
     * Gets emoji for score
     */
    private getScoreEmoji(score: number): string {
        if (score >= 90) return '🌟';
        if (score >= 80) return '✅';
        if (score >= 70) return '👍';
        if (score >= 60) return '⚠️';
        if (score >= 50) return '⚡';
        return '❌';
    }
    
    /**
     * Gets status icon for metric
     */
    private getStatusIcon(value: number): string {
        if (value >= 80) return '✅';
        if (value >= 60) return '⚠️';
        return '❌';
    }
    
    /**
     * Converts severity string to VS Code diagnostic severity
     */
    private getSeverity(severity: string): vscode.DiagnosticSeverity {
        switch (severity) {
            case 'error':
                return vscode.DiagnosticSeverity.Error;
            case 'warning':
                return vscode.DiagnosticSeverity.Warning;
            case 'information':
                return vscode.DiagnosticSeverity.Information;
            case 'hint':
                return vscode.DiagnosticSeverity.Hint;
            default:
                return vscode.DiagnosticSeverity.Information;
        }
    }
}