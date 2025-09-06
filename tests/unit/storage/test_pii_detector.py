"""
Advanced test suite for PII Detector - achieving 95%+ coverage

Tests all PII detection patterns, edge cases, and compliance requirements.
"""

import pytest
import time
import re
from unittest.mock import Mock, patch

from devdocai.storage.pii_detector import (
    PIIDetector, PIIType, PIIMatch, MaskingStrategy
)


class TestPIIDetectorAdvanced:
    """Advanced tests for PII detection accuracy and edge cases."""
    
    @pytest.fixture
    def detector_high(self):
        """High sensitivity detector."""
        return PIIDetector(sensitivity="high")
    
    @pytest.fixture
    def detector_low(self):
        """Low sensitivity detector."""
        return PIIDetector(sensitivity="low")
    
    @pytest.fixture
    def detector_medium(self):
        """Medium sensitivity detector."""
        return PIIDetector(sensitivity="medium")
    
    def test_email_variations(self, detector_high):
        """Test various email format variations."""
        emails = [
            "simple@example.com",
            "user.name@example.com",
            "user+tag@example.co.uk",
            "user_name@sub.example.org",
            "123@example.com",
            "a@b.co",
            "test.email-with-dash@example.com"
        ]
        
        for email in emails:
            text = f"Contact: {email}"
            matches = detector_high.detect(text, [PIIType.EMAIL])
            assert len(matches) == 1, f"Failed to detect {email}"
            assert matches[0].value == email
    
    def test_phone_international_formats(self, detector_high):
        """Test international phone number formats."""
        phones = [
            "+1-555-123-4567",      # US with country code
            "+44 20 7123 4567",     # UK
            "+33 1 42 86 82 00",    # France
            "+49 30 12345678",      # Germany
            "+81 3-1234-5678",      # Japan
            "+86 10 1234 5678",     # China
            "555-123-4567",         # US without country code
            "(555) 123-4567",       # US with parentheses
            "555.123.4567",         # US with dots
        ]
        
        for phone in phones:
            text = f"Phone: {phone}"
            matches = detector_high.detect(text, [PIIType.PHONE])
            assert len(matches) >= 1, f"Failed to detect {phone}"
    
    def test_ssn_invalid_patterns(self, detector_high):
        """Test SSN detection excludes invalid patterns."""
        invalid_ssns = [
            "000-12-3456",  # Starts with 000
            "666-12-3456",  # Starts with 666
            "900-12-3456",  # Starts with 9xx
            "123-00-4567",  # Middle is 00
            "123-45-0000",  # Ends with 0000
        ]
        
        for ssn in invalid_ssns:
            text = f"Invalid SSN: {ssn}"
            matches = detector_high.detect(text, [PIIType.SSN])
            # Should not detect invalid SSNs or have low confidence
            if matches:
                assert matches[0].confidence < 0.5
    
    def test_credit_card_luhn_validation(self, detector_high):
        """Test credit card detection with Luhn algorithm validation."""
        # Valid test credit cards (pass Luhn check)
        valid_cards = [
            "4111111111111111",      # Visa
            "5555555555554444",      # MasterCard
            "378282246310005",       # Amex
            "6011111111111117",      # Discover
            "3530111333300000",      # JCB
        ]
        
        # Invalid cards (fail Luhn check)
        invalid_cards = [
            "4111111111111112",      # Invalid Visa
            "5555555555554445",      # Invalid MasterCard
        ]
        
        for card in valid_cards:
            text = f"Card: {card}"
            matches = detector_high.detect(text, [PIIType.CREDIT_CARD])
            assert len(matches) == 1
            assert matches[0].confidence >= 0.6
        
        for card in invalid_cards:
            text = f"Card: {card}"
            matches = detector_high.detect(text, [PIIType.CREDIT_CARD])
            if matches:
                # Should have lower confidence for invalid cards
                assert matches[0].confidence < 0.5
    
    def test_ip_address_ipv4_ipv6(self, detector_high):
        """Test both IPv4 and IPv6 address detection."""
        ips = [
            # IPv4
            "192.168.1.1",
            "10.0.0.1",
            "172.16.0.1",
            "8.8.8.8",
            "255.255.255.255",
            # IPv6
            "2001:0db8:85a3:0000:0000:8a2e:0370:7334",
            "2001:db8:85a3::8a2e:370:7334",
            "::1",
            "fe80::1",
        ]
        
        for ip in ips:
            text = f"IP: {ip}"
            matches = detector_high.detect(text, [PIIType.IP_ADDRESS])
            assert len(matches) >= 1, f"Failed to detect {ip}"
    
    def test_mac_address_formats(self, detector_high):
        """Test MAC address detection with different formats."""
        macs = [
            "00:11:22:33:44:55",
            "00-11-22-33-44-55",
            "AA:BB:CC:DD:EE:FF",
            "aa:bb:cc:dd:ee:ff",
        ]
        
        for mac in macs:
            text = f"MAC: {mac}"
            matches = detector_high.detect(text, [PIIType.MAC_ADDRESS])
            assert len(matches) == 1, f"Failed to detect {mac}"
            assert matches[0].value.upper() == mac.upper()
    
    def test_iban_detection(self, detector_high):
        """Test IBAN (International Bank Account Number) detection."""
        ibans = [
            "GB82WEST12345698765432",  # UK
            "DE89370400440532013000",  # Germany
            "FR1420041010050500013M02606",  # France
        ]
        
        for iban in ibans:
            text = f"IBAN: {iban}"
            matches = detector_high.detect(text, [PIIType.IBAN])
            assert len(matches) == 1, f"Failed to detect {iban}"
    
    def test_date_of_birth_formats(self, detector_high):
        """Test various date of birth formats."""
        dates = [
            "01/15/1990",
            "15-01-1990",
            "1990-01-15",
            "January 15, 1990",
            "Jan 15, 1990",
            "15 Jan 1990",
        ]
        
        for date in dates:
            text = f"Born on {date}"
            matches = detector_high.detect(text, [PIIType.DATE_OF_BIRTH])
            assert len(matches) >= 1, f"Failed to detect {date}"
    
    def test_api_key_patterns(self, detector_high):
        """Test API key detection patterns."""
        api_keys = [
            'api_key="sk-proj-1234567890abcdefghijklmnop"',
            'apikey: "1234567890abcdefghijklmnopqrstuvwxyz"',
            'api-token="tok_1234567890abcdef"',
            'API_SECRET="secret_1234567890"',
        ]
        
        for key_text in api_keys:
            matches = detector_high.detect(key_text, [PIIType.API_KEY])
            assert len(matches) >= 1, f"Failed to detect API key in: {key_text}"
    
    def test_aws_key_detection(self, detector_high):
        """Test AWS access key detection."""
        aws_keys = [
            "AKIAIOSFODNN7EXAMPLE",
            'aws_access_key_id="AKIAIOSFODNN7EXAMPLE"',
            'aws_secret_access_key="wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"',
        ]
        
        for key in aws_keys:
            text = f"AWS: {key}"
            matches = detector_high.detect(text, [PIIType.AWS_KEY])
            assert len(matches) >= 1, f"Failed to detect AWS key: {key}"
    
    def test_medical_record_patterns(self, detector_high):
        """Test medical record number detection."""
        medical_records = [
            "MRN: 123456789",
            "Medical Record #987654321",
            "medical_record: 555666777",
            "MRN#111222333",
        ]
        
        for record in medical_records:
            matches = detector_high.detect(record, [PIIType.MEDICAL_RECORD])
            assert len(matches) >= 1, f"Failed to detect: {record}"
    
    def test_health_insurance_detection(self, detector_high):
        """Test health insurance ID detection."""
        insurance_ids = [
            "ABC123456789",  # Medicare format
            "XYZ987654321",
        ]
        
        for id_text in insurance_ids:
            text = f"Insurance ID: {id_text}"
            matches = detector_high.detect(text, [PIIType.HEALTH_INSURANCE])
            assert len(matches) >= 1, f"Failed to detect: {id_text}"
    
    def test_context_validation_accuracy(self, detector_high):
        """Test context-based validation improves accuracy."""
        # Test SSN with and without context
        with_context = "My social security number is 123-45-6789"
        without_context = "Random: 123-45-6789"
        
        matches_with = detector_high.detect(with_context, [PIIType.SSN])
        matches_without = detector_high.detect(without_context, [PIIType.SSN])
        
        assert matches_with[0].confidence > matches_without[0].confidence
        
        # Test credit card with context
        with_context = "Payment card number: 4111111111111111"
        without_context = "Data: 4111111111111111"
        
        matches_with = detector_high.detect(with_context, [PIIType.CREDIT_CARD])
        matches_without = detector_high.detect(without_context, [PIIType.CREDIT_CARD])
        
        assert matches_with[0].confidence > matches_without[0].confidence
    
    def test_name_detection_advanced(self, detector_high):
        """Test advanced name detection with various patterns."""
        texts = [
            "CEO John Smith announced",
            "Dr. Sarah Johnson will attend",
            "From: Michael O'Brien",
            "Dear Ms. Emily Chen",
            "Professor James Wilson Jr.",
            "By: Mary Anne Thompson",
        ]
        
        for text in texts:
            matches = detector_high.detect(text, [PIIType.NAME])
            assert len(matches) >= 1, f"Failed to detect name in: {text}"
    
    def test_false_positive_reduction(self, detector_high):
        """Test false positive reduction for common patterns."""
        false_positives = [
            "Version 1.2.3.4",  # Not an IP
            "Test SSN: 000-00-0000",  # Invalid SSN
            "Example: test@example.com",  # Test email
            "Localhost: 127.0.0.1",  # Local IP
            "MAC: 00:00:00:00:00:00",  # Invalid MAC
        ]
        
        for text in false_positives:
            matches = detector_high.detect(text)
            # Should have low confidence for known false positives
            for match in matches:
                if match.value in ["000-00-0000", "test@example.com", "127.0.0.1", "00:00:00:00:00:00"]:
                    assert match.confidence < 0.5
    
    def test_sensitivity_levels_impact(self):
        """Test impact of different sensitivity levels."""
        text = "Possible email: maybe.email@test.com"
        
        detector_high = PIIDetector(sensitivity="high")
        detector_medium = PIIDetector(sensitivity="medium")
        detector_low = PIIDetector(sensitivity="low")
        
        matches_high = detector_high.detect(text)
        matches_medium = detector_medium.detect(text)
        matches_low = detector_low.detect(text)
        
        # High sensitivity should detect more or with higher confidence
        if matches_high and matches_low:
            assert matches_high[0].confidence >= matches_low[0].confidence
    
    def test_masking_all_strategies(self, detector_high):
        """Test all masking strategies comprehensively."""
        text = "John Doe, john@example.com, 555-123-4567, SSN: 123-45-6789"
        matches = detector_high.detect(text)
        
        # Test each strategy
        strategies = [
            MaskingStrategy.REDACT,
            MaskingStrategy.PARTIAL,
            MaskingStrategy.HASH,
            MaskingStrategy.TOKENIZE,
            MaskingStrategy.ENCRYPT
        ]
        
        for strategy in strategies:
            masked = detector_high.mask(text, matches, strategy)
            # Original PII should not be in masked text
            assert "john@example.com" not in masked
            assert "555-123-4567" not in masked
            assert "123-45-6789" not in masked
    
    def test_masking_preserves_structure(self, detector_high):
        """Test that masking preserves document structure."""
        text = """
        Name: John Doe
        Email: john@example.com
        Phone: 555-123-4567
        """
        
        matches = detector_high.detect(text)
        masked = detector_high.mask(text, matches, MaskingStrategy.PARTIAL)
        
        # Structure should be preserved
        assert "Name:" in masked
        assert "Email:" in masked
        assert "Phone:" in masked
        assert "\n" in masked
    
    def test_report_generation_comprehensive(self, detector_high):
        """Test comprehensive report generation."""
        text = """
        Customer: John Smith
        Email: john.smith@company.com
        Phone: +1-555-123-4567
        SSN: 123-45-6789
        Credit Card: 4111-1111-1111-1111
        DOB: 01/15/1980
        Address: 123 Main St, Anytown, USA
        Medical Record: MRN123456789
        API Key: sk-proj-1234567890abcdef
        """
        
        report = detector_high.generate_report(text)
        
        # Verify report completeness
        assert report['total_pii_found'] >= 8
        assert report['risk_score'] > 60  # High risk due to sensitive data
        assert report['risk_level'] in ["HIGH", "CRITICAL"]
        assert len(report['recommendations']) > 0
        assert report['unique_pii_types'] >= 5
        
        # Verify specific PII types detected
        pii_types = report['pii_by_type'].keys()
        assert 'ssn' in pii_types
        assert 'credit_card' in pii_types
        assert 'email' in pii_types
    
    def test_risk_score_calculation(self, detector_high):
        """Test risk score calculation logic."""
        # Low risk - just email
        text_low = "Contact: user@example.com"
        report_low = detector_high.generate_report(text_low)
        
        # Medium risk - email and phone
        text_medium = "Contact: user@example.com, 555-123-4567"
        report_medium = detector_high.generate_report(text_medium)
        
        # High risk - SSN and credit card
        text_high = "SSN: 123-45-6789, Card: 4111111111111111"
        report_high = detector_high.generate_report(text_high)
        
        # Risk scores should increase with sensitivity
        assert report_low['risk_score'] < report_medium['risk_score']
        assert report_medium['risk_score'] < report_high['risk_score']
    
    def test_recommendations_contextual(self, detector_high):
        """Test that recommendations are contextual."""
        # Financial PII
        text_financial = "Credit Card: 4111111111111111, SSN: 123-45-6789"
        report_financial = detector_high.generate_report(text_financial)
        assert any("PCI DSS" in rec for rec in report_financial['recommendations'])
        
        # Medical PII
        text_medical = "Medical Record: MRN123456789, Insurance: ABC123456789"
        report_medical = detector_high.generate_report(text_medical)
        assert any("HIPAA" in rec for rec in report_medical['recommendations'])
        
        # API Keys
        text_api = "API Key: sk-1234567890, AWS: AKIAIOSFODNN7EXAMPLE"
        report_api = detector_high.generate_report(text_api)
        assert any("rotate" in rec.lower() for rec in report_api['recommendations'])
    
    def test_performance_large_text(self, detector_high):
        """Test performance with large text documents."""
        # Generate large text with various PII
        large_text = """
        Lorem ipsum dolor sit amet, consectetur adipiscing elit.
        Contact: user@example.com, Phone: 555-123-4567
        """ * 1000  # ~100KB of text
        
        start_time = time.time()
        matches = detector_high.detect(large_text)
        detection_time = time.time() - start_time
        
        # Should complete within reasonable time (< 1 second for 100KB)
        assert detection_time < 1.0
        assert len(matches) > 0
    
    def test_cache_effectiveness(self, detector_high):
        """Test caching improves performance."""
        text = "Email: test@example.com " * 50
        
        # First call - not cached
        start1 = time.time()
        matches1 = detector_high.detect(text)
        time1 = time.time() - start1
        
        # Second call - should be cached
        start2 = time.time()
        matches2 = detector_high.detect(text)
        time2 = time.time() - start2
        
        # Cached should be significantly faster
        assert time2 < time1 * 0.5  # At least 50% faster
        assert matches1 == matches2
    
    def test_empty_and_none_handling(self, detector_high):
        """Test handling of empty and None inputs."""
        # Empty string
        matches = detector_high.detect("")
        assert matches == []
        
        # None input
        matches = detector_high.detect(None)
        assert matches == []
        
        # Whitespace only
        matches = detector_high.detect("   \n\t  ")
        assert matches == []
    
    def test_unicode_and_special_chars(self, detector_high):
        """Test handling of Unicode and special characters."""
        texts = [
            "Email: user@domäin.com",  # Unicode domain
            "Name: José García",  # Spanish names
            "Name: François Müller",  # European names
            "Email: 用户@example.com",  # Chinese characters
            "Phone: +81-3-1234-5678",  # Japanese format
        ]
        
        for text in texts:
            # Should not crash on Unicode
            matches = detector_high.detect(text)
            # Basic functionality should work
            assert isinstance(matches, list)
    
    def test_overlapping_matches(self, detector_high):
        """Test handling of overlapping PII matches."""
        # Text with potential overlapping patterns
        text = "Contact 555-123-4567 or email 5551234567@sms.carrier.com"
        
        matches = detector_high.detect(text)
        
        # Verify no overlapping positions
        for i, match1 in enumerate(matches):
            for match2 in matches[i+1:]:
                # Matches should not overlap
                assert not (match1.start_pos < match2.end_pos and 
                          match2.start_pos < match1.end_pos)
    
    def test_match_position_accuracy(self, detector_high):
        """Test that match positions are accurate."""
        text = "Email: john@example.com and phone: 555-123-4567"
        matches = detector_high.detect(text)
        
        for match in matches:
            # Extract text at match position
            extracted = text[match.start_pos:match.end_pos]
            assert extracted == match.value
    
    def test_confidence_thresholds(self, detector_high, detector_low):
        """Test confidence threshold handling."""
        text = "Possible SSN: 123-45-6789"
        
        # High sensitivity - lower threshold
        matches_high = detector_high.detect(text, [PIIType.SSN])
        
        # Low sensitivity - higher threshold
        matches_low = detector_low.detect(text, [PIIType.SSN])
        
        # Both should detect but with different confidences
        if matches_high and matches_low:
            assert len(matches_high) >= len(matches_low)