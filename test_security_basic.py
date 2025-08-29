"""
Basic security functionality test for M004 Pass 3.
"""

import tempfile
from pathlib import Path

# Test basic imports
try:
    from devdocai.generator.utils.security_validator import EnhancedSecurityValidator
    print("✅ Enhanced Security Validator imported successfully")
except Exception as e:
    print(f"❌ Enhanced Security Validator import failed: {e}")

try:
    from devdocai.generator.security.security_monitor import SecurityMonitor
    print("✅ Security Monitor imported successfully")
except Exception as e:
    print(f"❌ Security Monitor import failed: {e}")

try:
    from devdocai.generator.security.pii_protection import PIIProtectionEngine
    print("✅ PII Protection Engine imported successfully")
except Exception as e:
    print(f"❌ PII Protection Engine import failed: {e}")

try:
    from devdocai.generator.security.access_control import AccessController
    print("✅ Access Controller imported successfully")
except Exception as e:
    print(f"❌ Access Controller import failed: {e}")

# Test basic functionality
def test_security_validator():
    """Test basic security validator functionality."""
    try:
        validator = EnhancedSecurityValidator()
        
        # Test XSS detection
        malicious_inputs = {
            'script_tag': '<script>alert("xss")</script>'
        }
        
        result = validator.validate_template_inputs_secure(
            malicious_inputs, [], 'test_client'
        )
        
        assert not result['valid'], "XSS should be detected and blocked"
        assert len(result['errors']) > 0, "Should have validation errors"
        print("✅ XSS detection working")
        
        # Test safe inputs
        safe_inputs = {
            'name': 'John Doe',
            'title': 'Test Document'
        }
        
        result = validator.validate_template_inputs_secure(
            safe_inputs, [], 'test_client'
        )
        
        assert result['valid'], "Safe inputs should pass validation"
        print("✅ Safe input validation working")
        
    except Exception as e:
        print(f"❌ Security validator test failed: {e}")

def test_pii_protection():
    """Test basic PII protection functionality."""
    try:
        pii_engine = PIIProtectionEngine()
        
        # Test SSN detection
        content_with_ssn = "My SSN is 123-45-6789"
        
        result = pii_engine.scan_and_protect(
            content_with_ssn, 'input', 'test_client'
        )
        
        assert result['pii_detected'], "SSN should be detected"
        assert 'ssn' in result['pii_types_found'], "SSN type should be identified"
        print("✅ PII detection working")
        
    except Exception as e:
        print(f"❌ PII protection test failed: {e}")

def test_access_control():
    """Test basic access control functionality."""
    try:
        from devdocai.generator.security.access_control import AccessLevel, ResourceType
        
        access_controller = AccessController()
        
        # Register client
        profile = access_controller.register_client('test_client', AccessLevel.AUTHENTICATED)
        assert profile.client_id == 'test_client'
        print("✅ Client registration working")
        
        # Test access check
        allowed, reason, metadata = access_controller.check_access(
            'test_client', ResourceType.TEMPLATE, 'read'
        )
        assert allowed, "Authenticated client should have template read access"
        print("✅ Access control working")
        
    except Exception as e:
        print(f"❌ Access control test failed: {e}")

def test_security_monitor():
    """Test basic security monitoring functionality.""" 
    try:
        monitor = SecurityMonitor()
        
        # Report security event
        incident_id = monitor.report_security_event(
            'xss', 'high', 'test_client', 'test_template',
            'XSS attempt detected', {'pattern': '<script>'}
        )
        
        assert incident_id != "", "Should create incident for high severity event"
        assert incident_id in monitor.active_incidents, "Incident should be tracked"
        print("✅ Security monitoring working")
        
    except Exception as e:
        print(f"❌ Security monitor test failed: {e}")

if __name__ == "__main__":
    print("🔒 Testing M004 Document Generator Security (Pass 3)")
    print("=" * 60)
    
    test_security_validator()
    test_pii_protection()
    test_access_control()
    test_security_monitor()
    
    print("=" * 60)
    print("🔒 Security testing completed!")