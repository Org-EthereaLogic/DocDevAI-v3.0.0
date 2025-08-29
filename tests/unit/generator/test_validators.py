"""
Tests for M004 Document Generator - Input Validators.

Tests the InputValidator class and validation functionality.
"""

import pytest

from devdocai.generator.utils.validators import (
    InputValidator, 
    ValidationError
)


class TestValidationError:
    """Test ValidationError exception."""
    
    def test_validation_error_creation(self):
        """Test creating ValidationError."""
        error = ValidationError("Test error message")
        
        assert str(error) == "Test error message"
        assert isinstance(error, Exception)


class TestInputValidator:
    """Test InputValidator class."""
    
    @pytest.fixture
    def validator(self):
        """Create InputValidator instance."""
        return InputValidator()
    
    def test_initialization(self, validator):
        """Test validator initialization."""
        assert validator.patterns is not None
        assert "email" in validator.patterns
        assert "url" in validator.patterns
        assert "version" in validator.patterns
        assert len(validator.xss_patterns) > 0
    
    def test_validate_template_inputs_success(self, validator):
        """Test successful template input validation."""
        inputs = {
            "title": "Test Document",
            "description": "This is a test document",
            "author": "Test Author"
        }
        required_variables = ["title", "description"]
        
        errors = validator.validate_template_inputs(inputs, required_variables)
        
        assert errors == []
    
    def test_validate_template_inputs_missing_required(self, validator):
        """Test validation with missing required variables."""
        inputs = {
            "title": "Test Document"
            # Missing 'description'
        }
        required_variables = ["title", "description"]
        
        errors = validator.validate_template_inputs(inputs, required_variables)
        
        assert len(errors) > 0
        assert any("description" in error and "missing" in error.lower() for error in errors)
    
    def test_validate_template_inputs_none_value(self, validator):
        """Test validation with None values for required variables."""
        inputs = {
            "title": "Test Document",
            "description": None
        }
        required_variables = ["title", "description"]
        
        errors = validator.validate_template_inputs(inputs, required_variables)
        
        assert len(errors) > 0
        assert any("description" in error and "none" in error.lower() for error in errors)
    
    def test_validate_template_inputs_empty_string(self, validator):
        """Test validation with empty string for required variables."""
        inputs = {
            "title": "Test Document",
            "description": "   "  # Empty/whitespace string
        }
        required_variables = ["title", "description"]
        
        errors = validator.validate_template_inputs(inputs, required_variables)
        
        assert len(errors) > 0
        assert any("description" in error and "empty" in error.lower() for error in errors)
    
    def test_validate_field_email(self, validator):
        """Test email field validation."""
        # Valid emails
        valid_errors = validator.validate_field("email", "test@example.com")
        assert valid_errors == []
        
        valid_errors = validator.validate_field("user_email", "user.name+tag@domain.co.uk")
        assert valid_errors == []
        
        # Invalid emails
        invalid_errors = validator.validate_field("email", "invalid-email")
        assert len(invalid_errors) > 0
        assert "invalid email format" in invalid_errors[0].lower()
        
        invalid_errors = validator.validate_field("email", "@example.com")
        assert len(invalid_errors) > 0
    
    def test_validate_field_url(self, validator):
        """Test URL field validation."""
        # Valid URLs
        valid_errors = validator.validate_field("url", "https://example.com")
        assert valid_errors == []
        
        valid_errors = validator.validate_field("website_url", "http://sub.domain.com/path?query=value")
        assert valid_errors == []
        
        # Invalid URLs
        invalid_errors = validator.validate_field("url", "not-a-url")
        assert len(invalid_errors) > 0
        assert "invalid url format" in invalid_errors[0].lower()
        
        invalid_errors = validator.validate_field("url", "ftp://example.com")
        assert len(invalid_errors) > 0
    
    def test_validate_field_version(self, validator):
        """Test version field validation."""
        # Valid versions
        valid_errors = validator.validate_field("version", "1.0.0")
        assert valid_errors == []
        
        valid_errors = validator.validate_field("api_version", "2.1.3-beta")
        assert valid_errors == []
        
        # Invalid versions
        invalid_errors = validator.validate_field("version", "1.0")
        assert len(invalid_errors) > 0
        assert "invalid version format" in invalid_errors[0].lower()
        
        invalid_errors = validator.validate_field("version", "v1.0.0")
        assert len(invalid_errors) > 0
    
    def test_validate_field_date(self, validator):
        """Test date field validation."""
        # Valid dates
        valid_errors = validator.validate_field("date", "2024-01-15")
        assert valid_errors == []
        
        valid_errors = validator.validate_field("created_date", "2024/01/15")
        assert valid_errors == []
        
        valid_errors = validator.validate_field("updated_date", "2024-01-15 10:30:00")
        assert valid_errors == []
        
        # Invalid dates
        invalid_errors = validator.validate_field("date", "not-a-date")
        assert len(invalid_errors) > 0
        assert "invalid date format" in invalid_errors[0].lower()
        
        invalid_errors = validator.validate_field("date", "2024-13-01")  # Invalid month
        assert len(invalid_errors) > 0
    
    def test_validate_field_phone(self, validator):
        """Test phone number field validation."""
        # Valid phones
        valid_errors = validator.validate_field("phone", "123-456-7890")
        assert valid_errors == []
        
        valid_errors = validator.validate_field("telephone", "+1 (555) 123-4567")
        assert valid_errors == []
        
        valid_errors = validator.validate_field("phone_number", "5551234567")
        assert valid_errors == []
        
        # Invalid phones
        invalid_errors = validator.validate_field("phone", "abc-def-ghij")
        assert len(invalid_errors) > 0
        assert "invalid phone number format" in invalid_errors[0].lower()
        
        invalid_errors = validator.validate_field("phone", "123")  # Too short
        assert len(invalid_errors) > 0
        assert "invalid phone number length" in invalid_errors[0].lower()
    
    def test_validate_content_safety_xss(self, validator):
        """Test XSS detection in content."""
        safe_errors = validator._validate_content_safety("Safe content here", "content")
        assert safe_errors == []
        
        # Detect script tags
        xss_errors = validator._validate_content_safety("<script>alert('xss')</script>", "content")
        assert len(xss_errors) > 0
        assert "unsafe content" in xss_errors[0].lower()
        
        # Detect javascript URLs
        js_errors = validator._validate_content_safety("javascript:alert('xss')", "url")
        assert len(js_errors) > 0
        
        # Detect event handlers
        event_errors = validator._validate_content_safety("onclick=alert('xss')", "content")
        assert len(event_errors) > 0
    
    def test_validate_content_safety_sql_injection(self, validator):
        """Test SQL injection detection in content."""
        safe_errors = validator._validate_content_safety("Safe database content", "query")
        assert safe_errors == []
        
        # Detect SQL injection patterns
        sql_errors = validator._validate_content_safety("DROP TABLE users", "query")
        assert len(sql_errors) > 0
        assert "unsafe sql content" in sql_errors[0].lower()
        
        sql_errors = validator._validate_content_safety("SELECT * FROM users; --", "query")
        assert len(sql_errors) > 0
    
    def test_validate_length_standard_fields(self, validator):
        """Test length validation for standard field types."""
        # Title field - should have limit
        long_title = "x" * 250  # Longer than typical title limit
        title_errors = validator._validate_length(long_title, "title")
        assert len(title_errors) > 0
        assert "exceeds maximum length" in title_errors[0].lower()
        
        # Normal length should pass
        normal_title = "Normal Title"
        title_errors = validator._validate_length(normal_title, "title")
        assert title_errors == []
    
    def test_validate_length_email_field(self, validator):
        """Test length validation for email field."""
        # Very long email (beyond RFC limit)
        long_email = "a" * 250 + "@example.com"
        email_errors = validator._validate_length(long_email, "email")
        assert len(email_errors) > 0
        
        # Normal email should pass
        normal_email = "user@example.com"
        email_errors = validator._validate_length(normal_email, "email")
        assert email_errors == []
    
    def test_validate_generation_config_valid(self, validator):
        """Test validation of valid generation config."""
        config = {
            "output_format": "markdown",
            "save_to_storage": True,
            "include_metadata": False,
            "version": "1.0.0",
            "project_name": "Test Project"
        }
        
        errors = validator.validate_generation_config(config)
        assert errors == []
    
    def test_validate_generation_config_invalid_format(self, validator):
        """Test validation with invalid output format."""
        config = {
            "output_format": "invalid_format"
        }
        
        errors = validator.validate_generation_config(config)
        assert len(errors) > 0
        assert any("invalid output format" in error.lower() for error in errors)
    
    def test_validate_generation_config_invalid_types(self, validator):
        """Test validation with invalid data types."""
        config = {
            "save_to_storage": "not_boolean",
            "include_metadata": "also_not_boolean"
        }
        
        errors = validator.validate_generation_config(config)
        assert len(errors) >= 2  # Should catch both boolean field errors
        assert any("must be boolean" in error for error in errors)
    
    def test_validate_generation_config_invalid_version(self, validator):
        """Test validation with invalid version format."""
        config = {
            "version": "invalid_version"
        }
        
        errors = validator.validate_generation_config(config)
        assert len(errors) > 0
        assert any("invalid version format" in error.lower() for error in errors)
    
    def test_validate_project_name(self, validator):
        """Test project name validation."""
        # Valid project names
        valid_errors = validator._validate_project_name("Valid Project Name")
        assert valid_errors == []
        
        valid_errors = validator._validate_project_name("project-with-hyphens")
        assert valid_errors == []
        
        valid_errors = validator._validate_project_name("project_with_underscores")
        assert valid_errors == []
        
        # Invalid project names
        empty_errors = validator._validate_project_name("")
        assert len(empty_errors) > 0
        assert "cannot be empty" in empty_errors[0].lower()
        
        long_errors = validator._validate_project_name("x" * 150)
        assert len(long_errors) > 0
        assert "cannot exceed 100 characters" in long_errors[0]
        
        invalid_char_errors = validator._validate_project_name("project@with#symbols")
        assert len(invalid_char_errors) > 0
        assert "invalid characters" in invalid_char_errors[0].lower()
    
    def test_sanitize_input_basic(self, validator):
        """Test basic input sanitization."""
        unsafe_input = "<script>alert('xss')</script>Hello World"
        
        sanitized = validator.sanitize_input(unsafe_input, allow_html=False)
        
        # Should escape HTML entities
        assert "&lt;script&gt;" in sanitized
        assert "alert('xss')" not in sanitized
        assert "Hello World" in sanitized
    
    def test_sanitize_input_allow_html(self, validator):
        """Test input sanitization with HTML allowed."""
        input_with_html = "<p>Safe paragraph</p><script>alert('xss')</script>"
        
        sanitized = validator.sanitize_input(input_with_html, allow_html=True)
        
        # Should keep basic HTML but remove dangerous scripts
        assert "<p>Safe paragraph</p>" in sanitized
        assert "<script>" not in sanitized
    
    def test_sanitize_input_whitespace_normalization(self, validator):
        """Test whitespace normalization in sanitization."""
        messy_input = "  Multiple   spaces    and\n\ntabs\t\there  "
        
        sanitized = validator.sanitize_input(messy_input)
        
        # Should normalize whitespace
        assert sanitized == "Multiple spaces and tabs here"
    
    def test_sanitize_input_non_string(self, validator):
        """Test sanitizing non-string input."""
        number_input = 12345
        
        sanitized = validator.sanitize_input(number_input)
        
        assert sanitized == "12345"
    
    def test_regex_patterns_compilation(self, validator):
        """Test that regex patterns compile correctly."""
        # Test email pattern
        email_pattern = validator.patterns['email']
        assert email_pattern.match("test@example.com")
        assert not email_pattern.match("invalid-email")
        
        # Test URL pattern
        url_pattern = validator.patterns['url']
        assert url_pattern.match("https://example.com")
        assert url_pattern.match("http://example.com/path")
        assert not url_pattern.match("ftp://example.com")
        
        # Test version pattern
        version_pattern = validator.patterns['version']
        assert version_pattern.match("1.0.0")
        assert version_pattern.match("2.1.3-beta")
        assert not version_pattern.match("1.0")
        assert not version_pattern.match("v1.0.0")
    
    def test_comprehensive_field_validation(self, validator):
        """Test comprehensive field validation with multiple field types."""
        inputs = {
            "title": "Valid Title",
            "email": "user@example.com",
            "website_url": "https://example.com",
            "version": "1.0.0",
            "created_date": "2024-01-15",
            "phone_number": "555-123-4567",
            "description": "A valid description with safe content."
        }
        
        all_errors = []
        for field_name, value in inputs.items():
            field_errors = validator.validate_field(field_name, value)
            all_errors.extend(field_errors)
        
        assert all_errors == []  # All fields should be valid
    
    def test_error_accumulation(self, validator):
        """Test that validation errors are properly accumulated."""
        inputs = {
            "email": "invalid-email",
            "url": "not-a-url", 
            "version": "invalid-version",
            "phone": "not-a-phone"
        }
        required_variables = ["title"]  # Missing required variable
        
        errors = validator.validate_template_inputs(inputs, required_variables)
        
        # Should accumulate multiple errors
        assert len(errors) >= 5  # At least one for each invalid field + missing required
        
        error_text = " ".join(errors).lower()
        assert "email" in error_text
        assert "url" in error_text
        assert "version" in error_text
        assert "phone" in error_text
        assert "title" in error_text