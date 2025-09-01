/**
 * Generate Documentation Command
 * 
 * Handles documentation generation for selected code or entire files
 * using the DevDocAI backend modules.
 */

import * as vscode from 'vscode';
import { CLIService } from '../services/CLIService';
import { Logger } from '../utils/Logger';
import { Command } from './CommandManager';

export class GenerateDocumentationCommand implements Command {
    constructor(
        private cliService: CLIService,
        private logger: Logger
    ) {}
    
    public async execute(...args: any[]): Promise<void> {
        try {
            // Determine context (from command palette, context menu, or code lens)
            const context = this.determineContext(args);
            
            if (!context) {
                vscode.window.showWarningMessage('No valid context for documentation generation');
                return;
            }
            
            // Show template selection
            const template = await this.selectTemplate(context.languageId);
            if (!template) {
                return; // User cancelled
            }
            
            // Generate documentation with progress
            await vscode.window.withProgress({
                location: vscode.ProgressLocation.Notification,
                title: 'Generating documentation...',
                cancellable: true
            }, async (progress, token) => {
                try {
                    // Step 1: Analyze code
                    progress.report({ increment: 20, message: 'Analyzing code structure...' });
                    
                    if (token.isCancellationRequested) {
                        return;
                    }
                    
                    // Step 2: Generate documentation
                    progress.report({ increment: 40, message: 'Generating documentation...' });
                    
                    const result = await this.cliService.generateDocumentation(
                        context.filePath,
                        template,
                        {
                            selection: context.selection,
                            languageId: context.languageId,
                            includeExamples: true,
                            useMIAIR: true
                        }
                    );
                    
                    if (token.isCancellationRequested) {
                        return;
                    }
                    
                    // Step 3: Apply quality checks
                    progress.report({ increment: 20, message: 'Running quality checks...' });
                    
                    const qualityResult = await this.cliService.analyzeQuality(result.documentPath);
                    
                    // Step 4: Insert or update documentation
                    progress.report({ increment: 20, message: 'Updating file...' });
                    
                    await this.applyDocumentation(context, result, qualityResult);
                    
                    // Show success message with quality score
                    const message = qualityResult.score >= 70
                        ? `Documentation generated successfully (Quality: ${qualityResult.score}/100)`
                        : `Documentation generated with warnings (Quality: ${qualityResult.score}/100)`;
                    
                    const action = await vscode.window.showInformationMessage(
                        message,
                        'View Documentation',
                        'Improve Quality'
                    );
                    
                    if (action === 'View Documentation') {
                        await this.openDocumentation(result.documentPath);
                    } else if (action === 'Improve Quality') {
                        await vscode.commands.executeCommand(
                            'devdocai.analyzeQuality',
                            vscode.Uri.file(result.documentPath)
                        );
                    }
                    
                } catch (error) {
                    this.logger.error('Documentation generation failed', error);
                    vscode.window.showErrorMessage(
                        `Failed to generate documentation: ${error instanceof Error ? error.message : 'Unknown error'}`
                    );
                }
            });
            
        } catch (error) {
            this.logger.error('Generate documentation command failed', error);
            throw error;
        }
    }
    
    /**
     * Determines the context for documentation generation
     */
    private determineContext(args: any[]): DocumentationContext | null {
        // From code lens or context menu with URI
        if (args[0] instanceof vscode.Uri) {
            const uri = args[0];
            const document = vscode.workspace.textDocuments.find(d => d.uri.toString() === uri.toString());
            
            return {
                filePath: uri.fsPath,
                languageId: document?.languageId || this.getLanguageFromExtension(uri.fsPath),
                selection: args[1] instanceof vscode.Range ? document?.getText(args[1]) : undefined
            };
        }
        
        // From command palette or keybinding
        const editor = vscode.window.activeTextEditor;
        if (!editor) {
            return null;
        }
        
        const selection = !editor.selection.isEmpty
            ? editor.document.getText(editor.selection)
            : undefined;
        
        return {
            filePath: editor.document.uri.fsPath,
            languageId: editor.document.languageId,
            selection
        };
    }
    
    /**
     * Shows template selection quick pick
     */
    private async selectTemplate(languageId: string): Promise<string | undefined> {
        // Get available templates from CLI service
        const templates = await this.cliService.getTemplates(languageId);
        
        if (!templates || templates.length === 0) {
            vscode.window.showWarningMessage('No templates available for this language');
            return undefined;
        }
        
        const items: vscode.QuickPickItem[] = templates.map(template => ({
            label: template.name,
            description: template.description,
            detail: `Supports: ${template.languages.join(', ')}`
        }));
        
        const selected = await vscode.window.showQuickPick(items, {
            placeHolder: 'Select a documentation template',
            title: 'Documentation Template'
        });
        
        return selected?.label;
    }
    
    /**
     * Applies generated documentation to the file
     */
    private async applyDocumentation(
        context: DocumentationContext,
        result: any,
        qualityResult: any
    ): Promise<void> {
        const document = await vscode.workspace.openTextDocument(context.filePath);
        const edit = new vscode.WorkspaceEdit();
        
        if (context.selection) {
            // Replace selection with documented version
            const editor = vscode.window.activeTextEditor;
            if (editor && editor.document.uri.toString() === document.uri.toString()) {
                const documentedCode = await this.getDocumentedCode(result);
                edit.replace(document.uri, editor.selection, documentedCode);
            }
        } else {
            // Add documentation comment at the beginning of the file or before functions/classes
            const documentationComment = await this.formatDocumentationComment(
                result,
                context.languageId
            );
            
            // Find insertion point (before first function/class or at beginning)
            const insertPosition = this.findInsertionPosition(document, context.languageId);
            edit.insert(document.uri, insertPosition, documentationComment);
        }
        
        await vscode.workspace.applyEdit(edit);
    }
    
    /**
     * Formats documentation as a comment for the target language
     */
    private async formatDocumentationComment(result: any, languageId: string): Promise<string> {
        const content = result.content || '';
        
        switch (languageId) {
            case 'python':
                return `"""\n${content}\n"""\n\n`;
            
            case 'typescript':
            case 'javascript':
                return `/**\n${content.split('\n').map((line: string) => ` * ${line}`).join('\n')}\n */\n\n`;
            
            case 'java':
            case 'c':
            case 'cpp':
                return `/**\n${content.split('\n').map((line: string) => ` * ${line}`).join('\n')}\n */\n\n`;
            
            default:
                // Generic comment format
                return `/*\n${content}\n*/\n\n`;
        }
    }
    
    /**
     * Finds the best position to insert documentation
     */
    private findInsertionPosition(document: vscode.TextDocument, languageId: string): vscode.Position {
        const text = document.getText();
        
        // Language-specific patterns for finding functions/classes
        const patterns: { [key: string]: RegExp } = {
            python: /^(class\s+\w+|def\s+\w+)/m,
            typescript: /^(export\s+)?(class\s+\w+|function\s+\w+|const\s+\w+\s*=\s*\()/m,
            javascript: /^(export\s+)?(class\s+\w+|function\s+\w+|const\s+\w+\s*=\s*\()/m
        };
        
        const pattern = patterns[languageId];
        if (pattern) {
            const match = text.match(pattern);
            if (match && match.index !== undefined) {
                return document.positionAt(match.index);
            }
        }
        
        // Default to beginning of file
        return new vscode.Position(0, 0);
    }
    
    /**
     * Gets the documented version of the code
     */
    private async getDocumentedCode(result: any): Promise<string> {
        // This would integrate with the backend to get the documented version
        return result.documentedCode || result.content || '';
    }
    
    /**
     * Opens the generated documentation in a new editor
     */
    private async openDocumentation(documentPath: string): Promise<void> {
        const document = await vscode.workspace.openTextDocument(documentPath);
        await vscode.window.showTextDocument(document, vscode.ViewColumn.Beside);
    }
    
    /**
     * Determines language from file extension
     */
    private getLanguageFromExtension(filePath: string): string {
        const extension = filePath.split('.').pop()?.toLowerCase();
        
        const languageMap: { [key: string]: string } = {
            'py': 'python',
            'ts': 'typescript',
            'tsx': 'typescript',
            'js': 'javascript',
            'jsx': 'javascript',
            'java': 'java',
            'c': 'c',
            'cpp': 'cpp',
            'cs': 'csharp',
            'go': 'go',
            'rs': 'rust',
            'rb': 'ruby',
            'php': 'php'
        };
        
        return languageMap[extension || ''] || 'plaintext';
    }
}

/**
 * Context for documentation generation
 */
interface DocumentationContext {
    filePath: string;
    languageId: string;
    selection?: string;
}