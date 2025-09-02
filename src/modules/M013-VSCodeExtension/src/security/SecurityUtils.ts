/**
 * SecurityUtils.ts
 * 
 * Centralized security utilities for the VS Code Extension
 * Implements OWASP best practices for input validation and sanitization
 */

import * as DOMPurify from 'isomorphic-dompurify';

/**
 * Configuration for DOMPurify HTML sanitization
 */
const DOMPURIFY_CONFIG = {
    // Allowed HTML tags for basic formatting
    ALLOWED_TAGS: ['p', 'span', 'div', 'a', 'b', 'i', 'em', 'strong', 'code', 'pre', 'ul', 'ol', 'li', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6'],
    // Allowed attributes
    ALLOWED_ATTR: ['href', 'class', 'id', 'title', 'style'],
    // Only allow safe URI schemes
    ALLOWED_URI_REGEXP: /^(?:https?|mailto)$/i,
    // Remove dangerous elements completely
    FORBID_TAGS: ['script', 'iframe', 'object', 'embed', 'form', 'input', 'textarea', 'button'],
    // Remove dangerous attributes
    FORBID_ATTR: ['onerror', 'onload', 'onclick', 'onmouseover', 'onfocus', 'onblur'],
    // Keep content of removed tags
    KEEP_CONTENT: true,
    // Return DOM instead of string for additional processing
    RETURN_DOM: false,
    // Return DOM fragment instead of full document
    RETURN_DOM_FRAGMENT: false,
    // Use safe for template mode
    SAFE_FOR_TEMPLATES: true
};

/**
 * Strict configuration for webview content
 */
const WEBVIEW_DOMPURIFY_CONFIG = {
    ...DOMPURIFY_CONFIG,
    // Even more restrictive for webviews
    ALLOWED_TAGS: ['p', 'span', 'div', 'b', 'i', 'em', 'strong', 'code', 'pre'],
    ALLOWED_ATTR: ['class', 'id'],
    // No external links in webviews
    ALLOWED_URI_REGEXP: /^$/,
    // Strip all data attributes
    FORBID_ATTR: [...DOMPURIFY_CONFIG.FORBID_ATTR, 'data-*']
};

/**
 * SecurityUtils class providing secure sanitization methods
 */
export class SecurityUtils {
    /**
     * Sanitize HTML content using DOMPurify
     * @param html - HTML string to sanitize
     * @param strict - Use strict mode for webview content
     * @returns Sanitized HTML string
     */
    public static sanitizeHtml(html: string, strict: boolean = false): string {
        if (!html || typeof html !== 'string') {
            return '';
        }

        const config = strict ? WEBVIEW_DOMPURIFY_CONFIG : DOMPURIFY_CONFIG;
        
        // Add hooks for additional security
        DOMPurify.addHook('afterSanitizeAttributes', (node: any) => {
            // Remove any javascript: or data: URLs from href attributes
            if ('href' in node && node.hasAttribute('href')) {
                const href = node.getAttribute('href');
                if (href && !this.isValidUrl(href)) {
                    node.removeAttribute('href');
                }
            }
            
            // Remove any style attributes that could contain expressions
            if (node.hasAttribute('style')) {
                const style = node.getAttribute('style');
                if (style && this.containsDangerousCSS(style)) {
                    node.removeAttribute('style');
                }
            }
        });

        const sanitized = DOMPurify.sanitize(html, config);
        
        // Remove hooks after use
        DOMPurify.removeAllHooks();
        
        return sanitized;
    }

    /**
     * Sanitize an object recursively
     * @param obj - Object to sanitize
     * @param strict - Use strict mode
     * @returns Sanitized object
     */
    public static sanitizeObject(obj: any, strict: boolean = false): any {
        if (obj === null || obj === undefined) {
            return obj;
        }

        if (typeof obj === 'string') {
            return this.sanitizeString(obj);
        }

        if (Array.isArray(obj)) {
            return obj.map(item => this.sanitizeObject(item, strict));
        }

        if (typeof obj === 'object') {
            const sanitized: any = {};
            for (const [key, value] of Object.entries(obj)) {
                // Sanitize the key as well
                const sanitizedKey = this.sanitizeString(key);
                sanitized[sanitizedKey] = this.sanitizeObject(value, strict);
            }
            return sanitized;
        }

        return obj;
    }

    /**
     * Sanitize a string for safe display (not HTML)
     * @param str - String to sanitize
     * @returns Sanitized string
     */
    public static sanitizeString(str: string): string {
        if (!str || typeof str !== 'string') {
            return '';
        }

        // Remove null bytes
        str = str.replace(/\0/g, '');
        
        // Remove control characters except newlines and tabs
        str = str.replace(/[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]/g, '');
        
        // Escape HTML special characters if not using DOMPurify
        str = str
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#39;');
        
        return str;
    }

    /**
     * Validate URL for safety
     * @param url - URL to validate
     * @returns True if URL is safe
     */
    public static isValidUrl(url: string): boolean {
        if (!url || typeof url !== 'string') {
            return false;
        }

        // Allow relative URLs
        if (!url.includes(':')) {
            return !url.includes('..'); // Prevent directory traversal
        }

        try {
            const parsed = new URL(url);
            // Only allow safe protocols
            const safeProtocols = ['http:', 'https:', 'mailto:'];
            return safeProtocols.includes(parsed.protocol.toLowerCase());
        } catch {
            // If URL parsing fails, consider it unsafe
            return false;
        }
    }

    /**
     * Validate file path for safety
     * @param filePath - File path to validate
     * @returns True if path is safe
     */
    public static isValidFilePath(filePath: string): boolean {
        if (!filePath || typeof filePath !== 'string') {
            return false;
        }

        // Check for directory traversal attempts
        const traversalPatterns = [
            /\.\./,           // Parent directory
            /\.\.\\/, // Parent directory (Windows)
            /~\//,            // Home directory
            /^\/etc/,         // System directories
            /^\/proc/,
            /^\/sys/,
            /^c:\\windows/i,  // Windows system directories
            /^c:\\program/i
        ];

        for (const pattern of traversalPatterns) {
            if (pattern.test(filePath)) {
                return false;
            }
        }

        // Check for null bytes
        if (filePath.includes('\0')) {
            return false;
        }

        return true;
    }

    /**
     * Check if CSS contains dangerous expressions
     * @param css - CSS string to check
     * @returns True if CSS contains dangerous content
     */
    private static containsDangerousCSS(css: string): boolean {
        const dangerousPatterns = [
            /expression\s*\(/i,      // IE CSS expressions
            /javascript:/i,          // JavaScript protocol
            /behavior\s*:/i,         // IE behaviors
            /-moz-binding/i,         // Firefox XBL
            /import\s*\(/i,          // CSS imports
            /url\s*\(/i              // External resources
        ];

        for (const pattern of dangerousPatterns) {
            if (pattern.test(css)) {
                return true;
            }
        }

        return false;
    }

    /**
     * Generate Content Security Policy for webviews
     * @param webview - VS Code webview
     * @param nonce - Nonce for inline scripts
     * @returns CSP string
     */
    public static generateCSP(webview: any, nonce: string): string {
        return [
            `default-src 'none'`,
            `script-src ${webview.cspSource} 'nonce-${nonce}'`,
            `style-src ${webview.cspSource} 'unsafe-inline'`,
            `img-src ${webview.cspSource} https: data:`,
            `font-src ${webview.cspSource}`,
            `connect-src 'none'`,
            `frame-src 'none'`,
            `object-src 'none'`,
            `base-uri 'none'`,
            `form-action 'none'`,
            `frame-ancestors 'none'`
        ].join('; ');
    }

    /**
     * Generate a secure nonce for CSP
     * @returns Nonce string
     */
    public static generateNonce(): string {
        const array = new Uint8Array(32);
        // Use crypto.getRandomValues if available (browser/node)
        if (typeof crypto !== 'undefined' && crypto.getRandomValues) {
            crypto.getRandomValues(array);
        } else {
            // Fallback for older environments
            for (let i = 0; i < array.length; i++) {
                array[i] = Math.floor(Math.random() * 256);
            }
        }
        return Buffer.from(array).toString('base64');
    }

    /**
     * Detect potential XSS patterns in input
     * @param input - Input to check
     * @returns Array of detected patterns
     */
    public static detectXSSPatterns(input: string): string[] {
        if (!input || typeof input !== 'string') {
            return [];
        }

        const detectedPatterns: string[] = [];
        
        // Define XSS patterns to detect (for logging/monitoring, not sanitization)
        const xssPatterns = [
            { name: 'Script Tag', pattern: /<script[\s>]/i },
            { name: 'JavaScript Protocol', pattern: /javascript:/i },
            { name: 'Data Protocol', pattern: /data:text\/html/i },
            { name: 'VBScript Protocol', pattern: /vbscript:/i },
            { name: 'On-Event Handler', pattern: /on\w+\s*=/i },
            { name: 'Eval Function', pattern: /eval\s*\(/i },
            { name: 'Expression CSS', pattern: /expression\s*\(/i },
            { name: 'Import Statement', pattern: /import\s+['"]/i },
            { name: 'Document Write', pattern: /document\.(write|writeln)\s*\(/i },
            { name: 'Inner HTML', pattern: /innerHTML\s*=/i },
            { name: 'Src Attribute Injection', pattern: /src\s*=\s*["'](?!https?:\/\/|\/)/i },
            { name: 'Unicode Escape', pattern: /\\u00/i },
            { name: 'HTML Entity Abuse', pattern: /&#x?[0-9a-f]+;/i }
        ];

        for (const { name, pattern } of xssPatterns) {
            if (pattern.test(input)) {
                detectedPatterns.push(name);
            }
        }

        return detectedPatterns;
    }

    /**
     * Sanitize input for command execution
     * @param command - Command to sanitize
     * @returns Sanitized command
     */
    public static sanitizeCommand(command: string): string {
        if (!command || typeof command !== 'string') {
            return '';
        }

        // Remove dangerous command injection characters
        const dangerousChars = [';', '|', '&', '$', '`', '\\', '\n', '\r', '>', '<', '(', ')', '{', '}', '[', ']'];
        let sanitized = command;
        
        for (const char of dangerousChars) {
            sanitized = sanitized.replace(new RegExp('\\' + char, 'g'), '');
        }

        return sanitized;
    }

    /**
     * Validate JSON string safely
     * @param jsonString - JSON string to validate
     * @returns Parsed object or null if invalid
     */
    public static safeJSONParse(jsonString: string): any | null {
        if (!jsonString || typeof jsonString !== 'string') {
            return null;
        }

        try {
            // Remove BOM if present
            if (jsonString.charCodeAt(0) === 0xFEFF) {
                jsonString = jsonString.slice(1);
            }

            // Basic validation before parsing
            if (!/^[\s\n\r\t]*[\[\{]/.test(jsonString)) {
                return null;
            }

            return JSON.parse(jsonString);
        } catch {
            return null;
        }
    }
}

/**
 * Export patterns for external threat detection
 */
export const SECURITY_PATTERNS = {
    XSS: {
        SCRIPT_TAG: /<script[\s>]/gi,
        EVENT_HANDLER: /on\w+\s*=/gi,
        JAVASCRIPT_PROTOCOL: /javascript:/gi,
        DATA_PROTOCOL: /data:text\/html/gi,
        VBSCRIPT_PROTOCOL: /vbscript:/gi
    },
    SQL_INJECTION: {
        UNION_SELECT: /union.*select/gi,
        DROP_TABLE: /drop\s+table/gi,
        DELETE_FROM: /delete\s+from/gi,
        INSERT_INTO: /insert\s+into/gi,
        UPDATE_SET: /update.*set/gi
    },
    PATH_TRAVERSAL: {
        PARENT_DIR: /\.\.[\/\\]/g,
        ABSOLUTE_PATH: /^[\/\\]/,
        HOME_DIR: /~[\/\\]/,
        NULL_BYTE: /\0/
    },
    COMMAND_INJECTION: {
        SHELL_OPERATORS: /[;&|`$]/g,
        COMMAND_SUBSTITUTION: /\$\([^)]+\)/g,
        BACKTICKS: /`[^`]+`/g
    }
};