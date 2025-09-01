/**
 * Language Service for DevDocAI VS Code Extension
 * 
 * Provides language-specific features like code lens, hover providers,
 * and auto-completion for documentation generation.
 */

import * as vscode from 'vscode';
import { CLIService } from './CLIService';
import { Logger } from '../utils/Logger';

export class LanguageService {
    private codeLensProviders: vscode.Disposable[] = [];
    private hoverProviders: vscode.Disposable[] = [];
    private completionProviders: vscode.Disposable[] = [];
    private codeActionProviders: vscode.Disposable[] = [];
    
    constructor(
        private context: vscode.ExtensionContext,
        private cliService: CLIService,
        private logger: Logger
    ) {}
    
    /**
     * Initializes language service providers
     */
    public async initialize(): Promise<void> {
        this.logger.info('Initializing language service');
        
        // Register providers for supported languages
        const languages = ['python', 'typescript', 'javascript', 'java', 'csharp', 'go', 'rust'];
        
        for (const language of languages) {
            this.registerProvidersForLanguage(language);
        }
        
        this.logger.info('Language service initialized');
    }
    
    /**
     * Registers all providers for a specific language
     */
    private registerProvidersForLanguage(language: string): void {
        // Code lens provider
        const codeLensProvider = vscode.languages.registerCodeLensProvider(
            { language },
            new DocumentationCodeLensProvider(this.cliService, this.logger, language)
        );
        this.codeLensProviders.push(codeLensProvider);
        
        // Hover provider for inline documentation hints
        const hoverProvider = vscode.languages.registerHoverProvider(
            { language },
            new DocumentationHoverProvider(this.cliService, this.logger, language)
        );
        this.hoverProviders.push(hoverProvider);
        
        // Completion provider for documentation templates
        const completionProvider = vscode.languages.registerCompletionItemProvider(
            { language },
            new DocumentationCompletionProvider(this.cliService, this.logger, language),
            '/', '@', '#'
        );
        this.completionProviders.push(completionProvider);
        
        // Code action provider for quick fixes
        const codeActionProvider = vscode.languages.registerCodeActionsProvider(
            { language },
            new DocumentationCodeActionProvider(this.cliService, this.logger, language),
            {
                providedCodeActionKinds: [
                    vscode.CodeActionKind.QuickFix,
                    vscode.CodeActionKind.Refactor
                ]
            }
        );
        this.codeActionProviders.push(codeActionProvider);
    }
    
    /**
     * Disposes all language service providers
     */
    public async dispose(): Promise<void> {
        this.logger.info('Disposing language service');
        
        [...this.codeLensProviders, 
         ...this.hoverProviders,
         ...this.completionProviders,
         ...this.codeActionProviders].forEach(provider => provider.dispose());
        
        this.codeLensProviders = [];
        this.hoverProviders = [];
        this.completionProviders = [];
        this.codeActionProviders = [];
    }
}

/**
 * Code lens provider for documentation hints
 */
class DocumentationCodeLensProvider implements vscode.CodeLensProvider {
    constructor(
        private cliService: CLIService,
        private logger: Logger,
        private language: string
    ) {}
    
    public async provideCodeLenses(
        document: vscode.TextDocument,
        token: vscode.CancellationToken
    ): Promise<vscode.CodeLens[]> {
        const codeLenses: vscode.CodeLens[] = [];
        
        // Get language-specific patterns
        const patterns = this.getLanguagePatterns();
        
        for (const pattern of patterns) {
            const regex = new RegExp(pattern.regex, 'gm');
            const text = document.getText();
            
            let match;
            while ((match = regex.exec(text)) !== null) {
                if (token.isCancellationRequested) {
                    return codeLenses;
                }
                
                const line = document.positionAt(match.index).line;
                const range = new vscode.Range(line, 0, line, 0);
                
                // Check if documentation exists
                const hasDoc = this.checkForDocumentation(document, line);
                
                if (!hasDoc) {
                    const lens = new vscode.CodeLens(range, {
                        title: '$(file-text) Generate Documentation',
                        command: 'devdocai.generateDocumentation',
                        arguments: [document.uri, range]
                    });
                    codeLenses.push(lens);
                } else {
                    const lens = new vscode.CodeLens(range, {
                        title: '$(checklist) Check Quality',
                        command: 'devdocai.analyzeQuality',
                        arguments: [document.uri]
                    });
                    codeLenses.push(lens);
                }
            }
        }
        
        return codeLenses;
    }
    
    private getLanguagePatterns(): Array<{ regex: string, type: string }> {
        const patterns: { [key: string]: Array<{ regex: string, type: string }> } = {
            python: [
                { regex: '^class\\s+(\\w+)', type: 'class' },
                { regex: '^def\\s+(\\w+)', type: 'function' },
                { regex: '^async\\s+def\\s+(\\w+)', type: 'async_function' }
            ],
            typescript: [
                { regex: '^export\\s+class\\s+(\\w+)', type: 'class' },
                { regex: '^class\\s+(\\w+)', type: 'class' },
                { regex: '^(?:export\\s+)?(?:async\\s+)?function\\s+(\\w+)', type: 'function' },
                { regex: '^(?:export\\s+)?const\\s+(\\w+)\\s*=\\s*(?:async\\s*)?(?:\\([^)]*\\)|\\w+)\\s*=>', type: 'arrow_function' }
            ],
            javascript: [
                { regex: '^class\\s+(\\w+)', type: 'class' },
                { regex: '^(?:async\\s+)?function\\s+(\\w+)', type: 'function' },
                { regex: '^const\\s+(\\w+)\\s*=\\s*(?:async\\s*)?(?:\\([^)]*\\)|\\w+)\\s*=>', type: 'arrow_function' }
            ],
            java: [
                { regex: '(?:public|private|protected)\\s+class\\s+(\\w+)', type: 'class' },
                { regex: '(?:public|private|protected)\\s+(?:static\\s+)?\\w+\\s+(\\w+)\\s*\\(', type: 'method' }
            ]
        };
        
        return patterns[this.language] || [];
    }
    
    private checkForDocumentation(document: vscode.TextDocument, line: number): boolean {
        if (line === 0) return false;
        
        const prevLine = document.lineAt(line - 1).text.trim();
        
        const docPatterns: { [key: string]: RegExp[] } = {
            python: [/^"""/, /^'''/],
            typescript: [/^\*\//, /^\/\*\*/],
            javascript: [/^\*\//, /^\/\*\*/],
            java: [/^\*\//]
        };
        
        const patterns = docPatterns[this.language] || [];
        return patterns.some(pattern => pattern.test(prevLine));
    }
}

/**
 * Hover provider for documentation insights
 */
class DocumentationHoverProvider implements vscode.HoverProvider {
    constructor(
        private cliService: CLIService,
        private logger: Logger,
        private language: string
    ) {}
    
    public async provideHover(
        document: vscode.TextDocument,
        position: vscode.Position,
        token: vscode.CancellationToken
    ): Promise<vscode.Hover | undefined> {
        const wordRange = document.getWordRangeAtPosition(position);
        if (!wordRange) {
            return undefined;
        }
        
        const word = document.getText(wordRange);
        const line = document.lineAt(position.line);
        
        // Check if this is a function/class/method
        if (this.isDefinition(line.text, word)) {
            const markdown = new vscode.MarkdownString();
            
            // Check documentation status
            const hasDoc = this.checkForDocumentation(document, position.line);
            
            if (hasDoc) {
                markdown.appendMarkdown('### Documentation Status\n\n');
                markdown.appendMarkdown('✅ **Documented**\n\n');
                markdown.appendMarkdown('[Analyze Quality](command:devdocai.analyzeQuality) | ');
                markdown.appendMarkdown('[Refresh Documentation](command:devdocai.refreshDocumentation)\n');
            } else {
                markdown.appendMarkdown('### Documentation Status\n\n');
                markdown.appendMarkdown('❌ **Not Documented**\n\n');
                markdown.appendMarkdown('[Generate Documentation](command:devdocai.generateDocumentation) | ');
                markdown.appendMarkdown('[Select Template](command:devdocai.selectTemplate)\n');
            }
            
            // Add language-specific tips
            markdown.appendMarkdown('\n---\n');
            markdown.appendMarkdown(`**Tip**: ${this.getLanguageTip()}`);
            
            markdown.isTrusted = true;
            
            return new vscode.Hover(markdown, wordRange);
        }
        
        return undefined;
    }
    
    private isDefinition(lineText: string, word: string): boolean {
        const patterns: { [key: string]: RegExp[] } = {
            python: [
                new RegExp(`^\\s*class\\s+${word}`),
                new RegExp(`^\\s*def\\s+${word}`),
                new RegExp(`^\\s*async\\s+def\\s+${word}`)
            ],
            typescript: [
                new RegExp(`class\\s+${word}`),
                new RegExp(`function\\s+${word}`),
                new RegExp(`const\\s+${word}\\s*=`)
            ],
            javascript: [
                new RegExp(`class\\s+${word}`),
                new RegExp(`function\\s+${word}`),
                new RegExp(`const\\s+${word}\\s*=`)
            ]
        };
        
        const langPatterns = patterns[this.language] || [];
        return langPatterns.some(pattern => pattern.test(lineText));
    }
    
    private checkForDocumentation(document: vscode.TextDocument, line: number): boolean {
        if (line === 0) return false;
        
        const prevLine = document.lineAt(line - 1).text.trim();
        
        const docPatterns: { [key: string]: RegExp[] } = {
            python: [/^"""/, /^'''/],
            typescript: [/^\*\//, /^\/\*\*/],
            javascript: [/^\*\//, /^\/\*\*/]
        };
        
        const patterns = docPatterns[this.language] || [];
        return patterns.some(pattern => pattern.test(prevLine));
    }
    
    private getLanguageTip(): string {
        const tips: { [key: string]: string } = {
            python: 'Use docstrings with """ for best results',
            typescript: 'Use JSDoc comments /** */ for TypeScript documentation',
            javascript: 'Use JSDoc comments /** */ for JavaScript documentation',
            java: 'Use Javadoc comments /** */ for Java documentation'
        };
        
        return tips[this.language] || 'Add documentation comments above your code';
    }
}

/**
 * Completion provider for documentation snippets
 */
class DocumentationCompletionProvider implements vscode.CompletionItemProvider {
    constructor(
        private cliService: CLIService,
        private logger: Logger,
        private language: string
    ) {}
    
    public async provideCompletionItems(
        document: vscode.TextDocument,
        position: vscode.Position,
        token: vscode.CancellationToken,
        context: vscode.CompletionContext
    ): Promise<vscode.CompletionItem[]> {
        const items: vscode.CompletionItem[] = [];
        
        // Check if we're at the beginning of a comment
        const linePrefix = document.lineAt(position).text.substr(0, position.character);
        
        if (this.shouldProvideCompletions(linePrefix)) {
            // Add documentation snippets
            items.push(...this.getDocumentationSnippets());
            
            // Add template suggestions
            const templates = await this.cliService.getTemplates(this.language);
            templates.forEach(template => {
                const item = new vscode.CompletionItem(
                    template.name,
                    vscode.CompletionItemKind.Snippet
                );
                item.detail = template.description;
                item.documentation = new vscode.MarkdownString(
                    `Generate ${template.name} documentation`
                );
                item.command = {
                    command: 'devdocai.generateDocumentation',
                    title: 'Generate Documentation',
                    arguments: [document.uri, template.name]
                };
                items.push(item);
            });
        }
        
        return items;
    }
    
    private shouldProvideCompletions(linePrefix: string): boolean {
        const triggers: { [key: string]: RegExp[] } = {
            python: [/^#\s*$/, /^"""\s*$/],
            typescript: [/^\/\/\s*$/, /^\/\*\*\s*$/],
            javascript: [/^\/\/\s*$/, /^\/\*\*\s*$/]
        };
        
        const langTriggers = triggers[this.language] || [];
        return langTriggers.some(trigger => trigger.test(linePrefix));
    }
    
    private getDocumentationSnippets(): vscode.CompletionItem[] {
        const snippets: vscode.CompletionItem[] = [];
        
        // Language-specific documentation snippets
        const langSnippets: { [key: string]: Array<{ label: string, snippet: string }> } = {
            python: [
                {
                    label: 'docstring',
                    snippet: '"""\n${1:Brief description}\n\nArgs:\n    ${2:param}: ${3:description}\n\nReturns:\n    ${4:description}\n"""'
                },
                {
                    label: 'docstring-class',
                    snippet: '"""\n${1:Class description}\n\nAttributes:\n    ${2:attr}: ${3:description}\n"""'
                }
            ],
            typescript: [
                {
                    label: 'jsdoc',
                    snippet: '/**\n * ${1:Brief description}\n * @param {${2:type}} ${3:name} - ${4:description}\n * @returns {${5:type}} ${6:description}\n */'
                },
                {
                    label: 'jsdoc-class',
                    snippet: '/**\n * ${1:Class description}\n * @class ${2:ClassName}\n */'
                }
            ],
            javascript: [
                {
                    label: 'jsdoc',
                    snippet: '/**\n * ${1:Brief description}\n * @param {${2:type}} ${3:name} - ${4:description}\n * @returns {${5:type}} ${6:description}\n */'
                }
            ]
        };
        
        const snippetList = langSnippets[this.language] || [];
        
        snippetList.forEach(({ label, snippet }) => {
            const item = new vscode.CompletionItem(label, vscode.CompletionItemKind.Snippet);
            item.insertText = new vscode.SnippetString(snippet);
            item.documentation = new vscode.MarkdownString(`Insert ${label} template`);
            snippets.push(item);
        });
        
        return snippets;
    }
}

/**
 * Code action provider for documentation quick fixes
 */
class DocumentationCodeActionProvider implements vscode.CodeActionProvider {
    constructor(
        private cliService: CLIService,
        private logger: Logger,
        private language: string
    ) {}
    
    public async provideCodeActions(
        document: vscode.TextDocument,
        range: vscode.Range | vscode.Selection,
        context: vscode.CodeActionContext,
        token: vscode.CancellationToken
    ): Promise<vscode.CodeAction[]> {
        const actions: vscode.CodeAction[] = [];
        
        // Check if there's missing documentation
        const line = range.start.line;
        const lineText = document.lineAt(line).text;
        
        if (this.isUndocumentedCode(document, line, lineText)) {
            // Quick fix to generate documentation
            const generateAction = new vscode.CodeAction(
                'Generate missing documentation',
                vscode.CodeActionKind.QuickFix
            );
            generateAction.command = {
                command: 'devdocai.generateDocumentation',
                title: 'Generate Documentation',
                arguments: [document.uri, range]
            };
            actions.push(generateAction);
            
            // Refactor to improve existing documentation
            if (this.hasMinimalDocumentation(document, line)) {
                const improveAction = new vscode.CodeAction(
                    'Improve documentation quality',
                    vscode.CodeActionKind.Refactor
                );
                improveAction.command = {
                    command: 'devdocai.analyzeQuality',
                    title: 'Analyze Quality',
                    arguments: [document.uri]
                };
                actions.push(improveAction);
            }
        }
        
        return actions;
    }
    
    private isUndocumentedCode(document: vscode.TextDocument, line: number, lineText: string): boolean {
        // Check if this line contains a function/class definition
        const definitionPatterns: { [key: string]: RegExp[] } = {
            python: [/^class\s+\w+/, /^def\s+\w+/, /^async\s+def\s+\w+/],
            typescript: [/class\s+\w+/, /function\s+\w+/, /const\s+\w+\s*=/],
            javascript: [/class\s+\w+/, /function\s+\w+/, /const\s+\w+\s*=/]
        };
        
        const patterns = definitionPatterns[this.language] || [];
        const isDefinition = patterns.some(pattern => pattern.test(lineText.trim()));
        
        if (!isDefinition) {
            return false;
        }
        
        // Check if there's documentation above
        if (line > 0) {
            const prevLine = document.lineAt(line - 1).text.trim();
            const docPatterns: { [key: string]: RegExp[] } = {
                python: [/^"""/, /^'''/],
                typescript: [/\*\/$/],
                javascript: [/\*\/$/]
            };
            
            const docChecks = docPatterns[this.language] || [];
            return !docChecks.some(pattern => pattern.test(prevLine));
        }
        
        return true;
    }
    
    private hasMinimalDocumentation(document: vscode.TextDocument, line: number): boolean {
        if (line === 0) return false;
        
        const prevLine = document.lineAt(line - 1).text.trim();
        
        // Check for very basic documentation
        const minimalPatterns: { [key: string]: RegExp[] } = {
            python: [/^"""[^"]+"""$/, /^#\s*\w+/],
            typescript: [/^\/\/\s*\w+/, /^\/\*\s*\w+\s*\*\/$/],
            javascript: [/^\/\/\s*\w+/, /^\/\*\s*\w+\s*\*\/$/]
        };
        
        const patterns = minimalPatterns[this.language] || [];
        return patterns.some(pattern => pattern.test(prevLine));
    }
}