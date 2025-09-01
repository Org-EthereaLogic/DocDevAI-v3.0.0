/**
 * Input Validator Security Component - M013 VS Code Extension
 * 
 * Comprehensive input validation and sanitization to prevent:
 * - Command injection attacks
 * - XSS vulnerabilities 
 * - Path traversal attacks
 * - Parameter tampering
 * - Rate limiting abuse
 * 
 * Integrates with M010 Security Module patterns for enterprise-grade protection.
 * 
 * @module M013-VSCodeExtension/Security
 * @version 3.0.0
 */

import * as vscode from 'vscode';
import * as path from 'path';
import * as fs from 'fs';
import * as crypto from 'crypto';

// Rate limiting interface
interface RateLimitEntry {
    count: number;
    resetTime: number;
    blocked: boolean;
}

// Validation result interface
export interface ValidationResult {
    isValid: boolean;
    sanitized?: any;
    errors: string[];
    warnings: string[];
    securityScore: number;
}

// Validation options
export interface ValidationOptions {
    maxLength?: number;
    allowedCharacters?: RegExp;
    requireAlphanumeric?: boolean;
    preventExecutables?: boolean;
    requireWorkspaceScope?: boolean;
    htmlSanitize?: boolean;
    rateLimitKey?: string;
}

export class InputValidator {
    private rateLimits: Map<string, RateLimitEntry> = new Map();
    private blockedIPs: Set<string> = new Set();
    private suspiciousPatterns: RegExp[];
    private commandInjectionPatterns: RegExp[];
    private xssPatterns: RegExp[];
    private pathTraversalPatterns: RegExp[];
    private workspaceRoot: string;
    
    // Rate limiting configuration
    private readonly DEFAULT_RATE_LIMIT = 100; // requests per minute
    private readonly BURST_LIMIT = 20; // rapid requests
    private readonly BLOCK_DURATION = 15 * 60 * 1000; // 15 minutes
    
    constructor(private context: vscode.ExtensionContext) {
        this.workspaceRoot = vscode.workspace.workspaceFolders?.[0]?.uri.fsPath || '';
        this.initializeSecurityPatterns();
        this.startCleanupTimer();
    }
    
    /**
     * Validates CLI command arguments for injection attacks
     */
    public validateCliArguments(args: string[]): ValidationResult {
        const result: ValidationResult = {
            isValid: true,
            sanitized: [],
            errors: [],
            warnings: [],
            securityScore: 100
        };
        
        for (const arg of args) {
            // Check for command injection patterns
            const injectionCheck = this.checkCommandInjection(arg);
            if (!injectionCheck.isValid) {
                result.isValid = false;
                result.errors.push(`Command injection detected in argument: ${arg}`);
                result.securityScore -= 25;
                continue;
            }
            
            // Sanitize argument
            const sanitized = this.sanitizeCliArgument(arg);
            result.sanitized.push(sanitized);
            
            // Check for suspicious patterns
            if (this.containsSuspiciousPattern(arg)) {
                result.warnings.push(`Suspicious pattern in argument: ${arg}`);
                result.securityScore -= 5;
            }
        }
        
        return result;
    }
    
    /**
     * Validates file paths for traversal attacks and workspace boundaries
     */
    public validateFilePath(filePath: string, options: ValidationOptions = {}): ValidationResult {
        const result: ValidationResult = {
            isValid: true,
            sanitized: '',
            errors: [],
            warnings: [],
            securityScore: 100
        };
        
        // Check for path traversal patterns
        if (this.pathTraversalPatterns.some(pattern => pattern.test(filePath))) {
            result.isValid = false;
            result.errors.push('Path traversal attack detected');
            result.securityScore = 0;
            return result;
        }
        
        // Normalize and resolve path
        const normalizedPath = path.normalize(filePath);
        const resolvedPath = path.resolve(normalizedPath);
        
        // Check workspace boundary if required
        if (options.requireWorkspaceScope && this.workspaceRoot) {
            if (!resolvedPath.startsWith(path.resolve(this.workspaceRoot))) {
                result.isValid = false;
                result.errors.push('Path outside workspace boundaries');
                result.securityScore -= 30;
            }
        }
        
        // Check if path exists and is accessible
        try {
            fs.accessSync(resolvedPath, fs.constants.R_OK);
        } catch {
            result.warnings.push('Path may not be accessible');
            result.securityScore -= 10;
        }
        
        // Check for executable files if prevention is enabled
        if (options.preventExecutables) {
            const ext = path.extname(resolvedPath).toLowerCase();
            const executableExts = ['.exe', '.bat', '.sh', '.cmd', '.com', '.scr', '.vbs', '.ps1'];
            if (executableExts.includes(ext)) {
                result.isValid = false;
                result.errors.push('Executable file access denied');
                result.securityScore -= 20;
            }
        }
        
        result.sanitized = resolvedPath;
        return result;
    }
    
    /**
     * Validates and sanitizes HTML content for XSS prevention
     */
    public validateHtmlContent(content: string, options: ValidationOptions = {}): ValidationResult {
        const result: ValidationResult = {
            isValid: true,
            sanitized: content,
            errors: [],
            warnings: [],
            securityScore: 100
        };
        
        // Check for XSS patterns
        const xssDetected = this.xssPatterns.some(pattern => pattern.test(content));
        if (xssDetected) {
            result.isValid = false;
            result.errors.push('XSS attack pattern detected');
            result.securityScore = 0;
        }
        
        // Sanitize HTML content if requested
        if (options.htmlSanitize) {
            result.sanitized = this.sanitizeHtml(content);
        }
        
        // Check for suspicious JavaScript
        if (/<script|javascript:|on\w+\s*=|eval\(|Function\(/i.test(content)) {
            result.warnings.push('Suspicious JavaScript content detected');
            result.securityScore -= 15;
        }
        
        return result;
    }
    
    /**
     * Validates user input parameters
     */
    public validateParameter(
        name: string, 
        value: any, 
        options: ValidationOptions = {}
    ): ValidationResult {
        const result: ValidationResult = {
            isValid: true,
            sanitized: value,
            errors: [],
            warnings: [],
            securityScore: 100
        };
        
        // Type validation
        if (typeof value === 'string') {
            // Length validation
            if (options.maxLength && value.length > options.maxLength) {
                result.isValid = false;
                result.errors.push(`Parameter ${name} exceeds maximum length`);
                result.securityScore -= 20;
            }
            
            // Character validation
            if (options.allowedCharacters && !options.allowedCharacters.test(value)) {
                result.isValid = false;
                result.errors.push(`Parameter ${name} contains invalid characters`);
                result.securityScore -= 15;
            }
            
            // Alphanumeric requirement
            if (options.requireAlphanumeric && !/^[a-zA-Z0-9\s\-_\.]+$/.test(value)) {
                result.isValid = false;
                result.errors.push(`Parameter ${name} must be alphanumeric`);
                result.securityScore -= 10;
            }
            
            // Check for injection attempts
            const injectionCheck = this.checkCommandInjection(value);
            if (!injectionCheck.isValid) {
                result.isValid = false;
                result.errors.push(`Parameter ${name} contains injection attempt`);
                result.securityScore -= 25;
            }
            
            // Sanitize string value
            result.sanitized = this.sanitizeString(value);
        }
        
        return result;
    }
    
    /**
     * Rate limiting validation
     */
    public validateRateLimit(key: string, limit: number = this.DEFAULT_RATE_LIMIT): ValidationResult {
        const result: ValidationResult = {
            isValid: true,
            errors: [],
            warnings: [],
            securityScore: 100
        };
        
        const now = Date.now();
        const resetTime = now + 60000; // 1 minute window
        
        let entry = this.rateLimits.get(key);
        
        if (!entry) {
            entry = { count: 1, resetTime, blocked: false };
            this.rateLimits.set(key, entry);
            return result;
        }
        
        // Reset counter if window expired
        if (now > entry.resetTime) {
            entry.count = 1;
            entry.resetTime = resetTime;
            entry.blocked = false;
        } else {
            entry.count++;
        }
        
        // Check rate limit
        if (entry.count > limit) {
            result.isValid = false;
            result.errors.push('Rate limit exceeded');
            result.securityScore = 0;
            entry.blocked = true;
            
            // Add to blocked list if excessive
            if (entry.count > limit * 2) {
                this.blockedIPs.add(key);
                setTimeout(() => this.blockedIPs.delete(key), this.BLOCK_DURATION);
            }
        } else if (entry.count > limit * 0.8) {
            result.warnings.push('Approaching rate limit');
            result.securityScore -= 10;
        }
        
        return result;
    }
    
    /**
     * Comprehensive validation for webview messages
     */
    public validateWebviewMessage(message: any): ValidationResult {
        const result: ValidationResult = {
            isValid: true,
            sanitized: {},
            errors: [],
            warnings: [],
            securityScore: 100
        };
        
        if (!message || typeof message !== 'object') {
            result.isValid = false;
            result.errors.push('Invalid message format');
            result.securityScore = 0;
            return result;
        }
        
        // Validate command field
        if (message.command) {
            const commandValidation = this.validateParameter(
                'command',
                message.command,
                { maxLength: 100, requireAlphanumeric: true }
            );
            
            if (!commandValidation.isValid) {
                result.isValid = false;
                result.errors.push(...commandValidation.errors);
                result.securityScore = Math.min(result.securityScore, commandValidation.securityScore);
            }
            
            result.sanitized.command = commandValidation.sanitized;
        }
        
        // Validate data field
        if (message.data) {
            const dataValidation = this.validateDataObject(message.data);
            if (!dataValidation.isValid) {
                result.warnings.push(...dataValidation.warnings);
                result.securityScore = Math.min(result.securityScore, dataValidation.securityScore);
            }
            result.sanitized.data = dataValidation.sanitized;
        }
        
        return result;
    }
    
    /**
     * Validates data objects recursively
     */
    private validateDataObject(data: any, depth: number = 0): ValidationResult {
        const result: ValidationResult = {
            isValid: true,
            sanitized: data,
            errors: [],
            warnings: [],
            securityScore: 100
        };
        
        // Prevent deep recursion attacks
        if (depth > 10) {
            result.isValid = false;
            result.errors.push('Object depth limit exceeded');
            result.securityScore = 0;
            return result;
        }
        
        if (typeof data === 'string') {
            // Check for XSS in string values
            const htmlValidation = this.validateHtmlContent(data);
            result.sanitized = htmlValidation.sanitized;
            result.securityScore = Math.min(result.securityScore, htmlValidation.securityScore);
        } else if (Array.isArray(data)) {
            result.sanitized = data.map(item => 
                this.validateDataObject(item, depth + 1).sanitized
            );
        } else if (typeof data === 'object' && data !== null) {
            result.sanitized = {};
            for (const [key, value] of Object.entries(data)) {
                const keyValidation = this.validateParameter(
                    'key',
                    key,
                    { maxLength: 100, requireAlphanumeric: true }
                );
                
                if (keyValidation.isValid) {
                    const valueValidation = this.validateDataObject(value, depth + 1);
                    result.sanitized[keyValidation.sanitized] = valueValidation.sanitized;
                    result.securityScore = Math.min(result.securityScore, valueValidation.securityScore);
                }
            }
        }
        
        return result;
    }
    
    /**
     * Initialize security pattern detection
     */
    private initializeSecurityPatterns(): void {
        // Command injection patterns
        this.commandInjectionPatterns = [
            /[;&|`$(){}[\]<>]/,  // Shell metacharacters
            /\\\\/,               // Backslash escapes
            /\$\{.*\}/,          // Variable expansion
            /\$\(.*\)/,          // Command substitution
            /`.*`/,              // Backtick execution
            /\|\s*\w+/,          // Pipe commands
            /&&|\|\|/,           // Logical operators
            />\s*\/|<\s*\//      // File redirection
        ];
        
        // XSS patterns
        this.xssPatterns = [
            /<script[^>]*>.*?<\/script>/gi,
            /javascript:/gi,
            /on\w+\s*=\s*["'][^"']*["']/gi,
            /eval\s*\(/gi,
            /Function\s*\(/gi,
            /setTimeout\s*\(/gi,
            /setInterval\s*\(/gi,
            /<iframe[^>]*>.*?<\/iframe>/gi,
            /<object[^>]*>.*?<\/object>/gi,
            /<embed[^>]*>/gi,
            /expression\s*\(/gi,
            /url\s*\(\s*["']?javascript:/gi
        ];
        
        // Path traversal patterns
        this.pathTraversalPatterns = [
            /\.\.[\/\\]/,        // Directory traversal
            /^[\/\\]/,           // Absolute paths
            /~[\/\\]/,           // Home directory
            /\$[A-Z_]+/,         // Environment variables
            /%[0-9A-F]{2}/,      // URL encoding
            /\\x[0-9A-F]{2}/,    // Hex encoding
            /\\[0-7]{3}/         // Octal encoding
        ];
        
        // General suspicious patterns
        this.suspiciousPatterns = [
            /passwd|shadow|hosts|crontab|sudoers/i,
            /\.ssh|\.aws|\.env/i,
            /whoami|id|uname|ps\s|ls\s/i,
            /curl|wget|nc\s|netcat/i,
            /base64|hex|decode/i,
            /exec|system|spawn|fork/i
        ];
    }
    
    /**
     * Check for command injection patterns
     */
    private checkCommandInjection(input: string): ValidationResult {
        const result: ValidationResult = {
            isValid: true,
            errors: [],
            warnings: [],
            securityScore: 100
        };
        
        for (const pattern of this.commandInjectionPatterns) {
            if (pattern.test(input)) {
                result.isValid = false;
                result.errors.push(`Command injection pattern detected: ${pattern}`);
                result.securityScore = 0;
                break;
            }
        }
        
        return result;
    }
    
    /**
     * Check for suspicious patterns
     */
    private containsSuspiciousPattern(input: string): boolean {
        return this.suspiciousPatterns.some(pattern => pattern.test(input));
    }
    
    /**
     * Sanitize CLI arguments
     */
    private sanitizeCliArgument(arg: string): string {
        return arg
            .replace(/[;&|`$(){}[\]<>\\]/g, '') // Remove shell metacharacters
            .replace(/\s+/g, ' ')               // Normalize whitespace
            .trim()                             // Remove leading/trailing space
            .substring(0, 1000);                // Limit length
    }
    
    /**
     * Sanitize HTML content
     */
    private sanitizeHtml(html: string): string {
        return html
            .replace(/<script[^>]*>.*?<\/script>/gi, '')     // Remove scripts
            .replace(/on\w+\s*=\s*["'][^"']*["']/gi, '')     // Remove event handlers
            .replace(/javascript:/gi, '')                     // Remove javascript: URLs
            .replace(/eval\s*\(/gi, '')                       // Remove eval calls
            .replace(/expression\s*\(/gi, '')                 // Remove CSS expressions
            .replace(/<iframe[^>]*>.*?<\/iframe>/gi, '')      // Remove iframes
            .replace(/<object[^>]*>.*?<\/object>/gi, '')      // Remove objects
            .replace(/<embed[^>]*>/gi, '');                   // Remove embeds
    }
    
    /**
     * Sanitize string values
     */
    private sanitizeString(str: string): string {
        return str
            .replace(/[<>&"']/g, match => {
                const entities: { [key: string]: string } = {
                    '<': '&lt;',
                    '>': '&gt;',
                    '&': '&amp;',
                    '"': '&quot;',
                    "'": '&#39;'
                };
                return entities[match] || match;
            })
            .substring(0, 10000); // Reasonable length limit
    }
    
    /**
     * Start cleanup timer for rate limiting
     */
    private startCleanupTimer(): void {
        setInterval(() => {
            const now = Date.now();
            for (const [key, entry] of this.rateLimits.entries()) {
                if (now > entry.resetTime + 300000) { // 5 minutes after reset
                    this.rateLimits.delete(key);
                }
            }
        }, 60000); // Cleanup every minute
    }
    
    /**
     * Get security statistics
     */
    public getSecurityStats(): any {
        return {
            rateLimitEntries: this.rateLimits.size,
            blockedIPs: this.blockedIPs.size,
            patternsLoaded: {
                commandInjection: this.commandInjectionPatterns.length,
                xss: this.xssPatterns.length,
                pathTraversal: this.pathTraversalPatterns.length,
                suspicious: this.suspiciousPatterns.length
            }
        };
    }
    
    /**
     * Dispose resources
     */
    public dispose(): void {
        this.rateLimits.clear();
        this.blockedIPs.clear();
    }
}