"""
Tests for the HTML sanitizer security fix.

This test file validates that the HTML sanitizer properly prevents XSS attacks
that were previously vulnerable due to regex-based filtering.
"""

import pytest
from bs4 import BeautifulSoup
from devdocai.common.html_sanitizer import (
    HtmlSanitizer,
    sanitize_html,
    strip_html_tags,
    get_sanitizer
)


class TestHtmlSanitizer:
    """Test the HTML sanitizer security functionality."""
    
    def test_basic_script_tag_removal(self):
        """Test that basic script tags are removed."""
        dangerous = '<p>Hello</p><script>alert("XSS")</script><p>World</p>'
        sanitized = sanitize_html(dangerous)
        
        assert '<script>' not in sanitized
        assert 'alert' not in sanitized
        assert 'Hello' in sanitized
        assert 'World' in sanitized
    
    def test_malformed_script_tag(self):
        """Test that malformed script tags are handled."""
        # Missing closing tag - browsers would still execute this
        dangerous = '<script>alert(1)'
        sanitized = sanitize_html(dangerous)
        
        assert '<script>' not in sanitized
        assert 'alert' not in sanitized
    
    def test_encoded_script_bypass_attempts(self):
        """Test that encoded script tags are handled."""
        test_cases = [
            # HTML entity encoding
            '&lt;script&gt;alert(1)&lt;/script&gt;',
            # Numeric entity encoding
            '&#60;script&#62;alert(1)&#60;/script&#62;',
            # Mixed case (already handled by browser)
            '<ScRiPt>alert(1)</ScRiPt>',
            # With attributes
            '<script src="evil.js"></script>',
            '<script type="text/javascript">alert(1)</script>',
        ]
        
        for dangerous in test_cases:
            sanitized = sanitize_html(dangerous)
            # The sanitizer should either escape or remove these
            assert 'alert(1)' not in sanitized or '&lt;' in sanitized
    
    def test_event_handler_removal(self):
        """Test that event handlers are removed."""
        test_cases = [
            '<img src=x onerror="alert(1)">',
            '<div onclick="alert(1)">Click me</div>',
            '<body onload="alert(1)">',
            '<input onfocus="alert(1)">',
            '<svg onload="alert(1)">',
        ]
        
        for dangerous in test_cases:
            sanitized = sanitize_html(dangerous)
            assert 'alert' not in sanitized
            assert 'onerror' not in sanitized
            assert 'onclick' not in sanitized
            assert 'onload' not in sanitized
            assert 'onfocus' not in sanitized
    
    def test_javascript_url_removal(self):
        """Test that javascript: URLs are removed."""
        test_cases = [
            '<a href="javascript:alert(1)">Click</a>',
            '<a href="JavaScript:alert(1)">Click</a>',
            '<a href="vbscript:alert(1)">Click</a>',
            '<a href="data:text/html,<script>alert(1)</script>">Click</a>',
        ]
        
        for dangerous in test_cases:
            sanitized = sanitize_html(dangerous)
            assert 'javascript:' not in sanitized.lower()
            assert 'vbscript:' not in sanitized.lower()
            assert 'data:' not in sanitized or 'text/html' not in sanitized
    
    def test_iframe_and_object_removal(self):
        """Test that dangerous embedding tags are removed."""
        test_cases = [
            '<iframe src="evil.com"></iframe>',
            '<object data="evil.swf"></object>',
            '<embed src="evil.swf">',
            '<applet code="Evil.class"></applet>',
        ]
        
        for dangerous in test_cases:
            sanitized = sanitize_html(dangerous)
            assert '<iframe' not in sanitized
            assert '<object' not in sanitized
            assert '<embed' not in sanitized
            assert '<applet' not in sanitized
    
    def test_css_injection_prevention(self):
        """Test that CSS injection is prevented."""
        test_cases = [
            '<style>@import url("evil.css")</style>',
            '<div style="background: url(javascript:alert(1))">',
            '<div style="expression(alert(1))">',
        ]
        
        for dangerous in test_cases:
            sanitized = sanitize_html(dangerous)
            assert 'javascript:' not in sanitized
            assert 'expression(' not in sanitized
            assert '@import' not in sanitized or '<style>' not in sanitized
    
    def test_safe_html_preservation(self):
        """Test that safe HTML is preserved."""
        safe_html = '''
        <div>
            <h1>Title</h1>
            <p>This is a <strong>paragraph</strong> with <em>emphasis</em>.</p>
            <ul>
                <li>Item 1</li>
                <li>Item 2</li>
            </ul>
            <a href="https://example.com">Safe link</a>
        </div>
        '''
        
        sanitized = sanitize_html(safe_html)
        
        # Safe tags should be preserved
        assert '<h1>' in sanitized or 'Title' in sanitized
        assert '<strong>' in sanitized or 'paragraph' in sanitized
        assert '<em>' in sanitized or 'emphasis' in sanitized
        assert '<ul>' in sanitized or 'Item 1' in sanitized
        
        # Safe links should work
        if 'href' in sanitized:
            soup = BeautifulSoup(sanitized, 'html.parser')
            a_tags = soup.find_all('a', href=True)
            expected_url = "https://example.com"
            assert any(a['href'] == expected_url for a in a_tags)
    
    def test_strip_all_tags(self):
        """Test that strip_html_tags removes all HTML."""
        html_content = '''
        <div>
            <script>alert(1)</script>
            <h1>Title</h1>
            <p>Paragraph with <a href="javascript:alert(1)">link</a></p>
        </div>
        '''
        
        stripped = strip_html_tags(html_content)
        
        # No HTML tags should remain
        assert '<' not in stripped
        assert '>' not in stripped
        
        # Text content should be preserved
        assert 'Title' in stripped
        assert 'Paragraph' in stripped
        assert 'link' in stripped
        
        # Dangerous content should be gone
        assert 'script' not in stripped
        assert 'alert' not in stripped
        assert 'javascript:' not in stripped
    
    def test_singleton_sanitizer(self):
        """Test that get_sanitizer returns a singleton."""
        sanitizer1 = get_sanitizer()
        sanitizer2 = get_sanitizer()
        
        assert sanitizer1 is sanitizer2
    
    def test_custom_allowed_tags(self):
        """Test custom allowed tags configuration."""
        # Create sanitizer that only allows paragraph tags
        sanitizer = HtmlSanitizer(allowed_tags={'p'})
        
        html = '<p>Keep this</p><div>Remove this</div><script>alert(1)</script>'
        result = sanitizer.sanitize(html)
        
        # Only <p> should remain
        if '<' in result:  # If any tags remain
            assert '<p>' in result
            assert '<div>' not in result
            assert '<script>' not in result
    
    def test_complex_nested_attack(self):
        """Test complex nested XSS attempts."""
        dangerous = '''
        <div>
            <p>Normal content</p>
            <<script>alert(1)</script>script>alert(2)<</script>/script>
            <img src="x" onerror="alert(3)" />
            <a href="javascript:void(0)" onclick="alert(4)">Click</a>
            <iframe src="data:text/html,<script>alert(5)</script>"></iframe>
        </div>
        '''
        
        sanitized = sanitize_html(dangerous)
        
        # None of the alerts should be present
        for i in range(1, 6):
            assert f'alert({i})' not in sanitized
        
        # Normal content should be preserved
        assert 'Normal content' in sanitized
    
    def test_performance_with_large_input(self):
        """Test that sanitizer handles large inputs efficiently."""
        # Create a large HTML document
        large_html = '<p>Safe content</p>' * 1000
        large_html += '<script>alert(1)</script>' * 100
        
        # Should complete without hanging
        import time
        start = time.time()
        sanitized = sanitize_html(large_html)
        duration = time.time() - start
        
        # Should complete in reasonable time (< 1 second for this size)
        assert duration < 1.0
        
        # Should remove all scripts
        assert '<script>' not in sanitized
        assert 'alert' not in sanitized
        
        # Should preserve safe content
        assert 'Safe content' in sanitized


class TestVulnerabilityPrevention:
    """Test that specific CodeQL vulnerabilities are prevented."""
    
    def test_codeql_script_tag_vulnerability(self):
        """Test the exact pattern that CodeQL flagged."""
        # This is the pattern that was vulnerable:
        # re.compile(r'<script[^>]*>.*?</script>', re.IGNORECASE | re.DOTALL)
        
        # These inputs would bypass the regex but should be caught by sanitizer
        bypass_attempts = [
            '<script',  # Incomplete tag
            '<script src=x',  # No closing bracket
            '<<script>>alert(1)<</script>>',  # Double brackets
            '<scr\x00ipt>alert(1)</script>',  # Null byte injection
            '<script\n>alert(1)</script>',  # Newline in tag
            '<script//src=x>',  # Comment in tag
            '<script<!--src=x-->>',  # HTML comment in tag
        ]
        
        for attempt in bypass_attempts:
            sanitized = sanitize_html(attempt)
            # Should not contain executable script
            assert not ('<script' in sanitized and '>' in sanitized)
            
    def test_no_regex_patterns_remain(self):
        """Verify that the vulnerable regex patterns are not used."""
        # This test ensures the refactoring was complete
        from devdocai.generator.utils import validators, security_validator
        from devdocai.generator.outputs import secure_html_output
        
        # Check that XSS_PATTERNS are empty or removed
        if hasattr(validators.InputValidator, 'xss_patterns'):
            validator = validators.InputValidator()
            assert len(validator.xss_patterns) == 0
        
        # Check security validator
        assert len(security_validator.SecurityValidator.XSS_PATTERNS) == 0
        
        # Check HTML output
        assert len(secure_html_output.SecureHtmlOutput.DANGEROUS_PATTERNS) == 0


if __name__ == '__main__':
    pytest.main([__file__, '-v'])