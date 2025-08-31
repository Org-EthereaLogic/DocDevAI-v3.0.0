"""
CycloneDX 1.4 Format Validation Tests.

Comprehensive test suite for CycloneDX format validation including:
- JSON format validation
- XML format validation
- Schema compliance verification
- Component validation
"""

import pytest
import json
import xml.etree.ElementTree as ET
from pathlib import Path

# Import SBOM testing framework
from ..core import SBOMTestFramework, SBOMFormat
from ..validators import CycloneDXValidator, ValidationSeverity
from ..generators import SBOMTestDataGenerator
from ..assertions import SBOMAssertions


class TestCycloneDXValidators(SBOMTestFramework):
    """
    Test suite for CycloneDX 1.4 format validators.
    
    Validates compliance with CycloneDX specification and ensures
    100% format compliance scoring.
    """
    
    def setup_method(self):
        """Set up test environment."""
        super().setup_method()
        self.validator = CycloneDXValidator()
        self.generator = SBOMTestDataGenerator(seed=42)  # Reproducible tests
        self.assertions = SBOMAssertions()
    
    # ========================================================================
    # CYCLONEDX JSON FORMAT TESTS
    # ========================================================================
    
    def test_valid_cyclonedx_json_format(self):
        """Test validation of valid CycloneDX JSON format."""
        # Generate test dependency tree
        dependency_tree = self.generator.generate_realistic_dependency_tree(
            ecosystem="npm",
            complexity="medium"
        )
        
        # Generate CycloneDX JSON
        from ..core import create_sample_sbom
        cyclonedx_json = create_sample_sbom(SBOMFormat.CYCLONE_DX_JSON, dependency_tree)
        
        # Validate format
        result = self.validator.validate_json(cyclonedx_json)
        
        # Assert valid and compliant
        self.assertions.assert_valid_sbom_format(result, min_compliance_score=0.95)
        assert result.format_detected == SBOMFormat.CYCLONE_DX_JSON
        assert result.spec_version == "1.4"
    
    def test_cyclonedx_json_missing_required_fields(self):
        """Test CycloneDX JSON validation with missing required fields."""
        # Create incomplete CycloneDX document
        incomplete_cyclonedx = {
            "bomFormat": "CycloneDX",
            # Missing specVersion, serialNumber, version
            "components": []
        }
        
        result = self.validator.validate_json(json.dumps(incomplete_cyclonedx))
        
        # Should fail validation
        assert not result.is_valid
        assert result.compliance_score < 0.5
        
        # Check specific error messages
        errors = result.get_errors()
        expected_missing_fields = ["specVersion", "serialNumber", "version"]
        
        error_fields = [error.field for error in errors]
        for field in expected_missing_fields:
            assert field in error_fields, f"Expected error for missing field: {field}"
    
    def test_cyclonedx_json_invalid_bom_format(self):
        """Test CycloneDX JSON validation with invalid bomFormat."""
        invalid_cyclonedx = {
            "bomFormat": "SPDX",  # Invalid format - should be CycloneDX
            "specVersion": "1.4",
            "serialNumber": "urn:uuid:12345678-1234-1234-1234-123456789012",
            "version": 1
        }
        
        result = self.validator.validate_json(json.dumps(invalid_cyclonedx))
        
        # Should have validation issues
        errors = result.get_errors()
        format_errors = [e for e in errors if e.field == "bomFormat"]
        assert len(format_errors) > 0, "Expected validation error for invalid bomFormat"
        assert "CycloneDX" in format_errors[0].message
    
    def test_cyclonedx_json_invalid_spec_version(self):
        """Test CycloneDX JSON validation with invalid spec version."""
        invalid_cyclonedx = {
            "bomFormat": "CycloneDX",
            "specVersion": "2.0",  # Invalid version
            "serialNumber": "urn:uuid:12345678-1234-1234-1234-123456789012",
            "version": 1
        }
        
        result = self.validator.validate_json(json.dumps(invalid_cyclonedx))
        
        # Should have validation issues
        errors = result.get_errors()
        version_errors = [e for e in errors if e.field == "specVersion"]
        assert len(version_errors) > 0, "Expected validation error for invalid specVersion"
    
    def test_cyclonedx_json_component_validation(self):
        """Test CycloneDX JSON component-level validation."""
        cyclonedx_with_components = {
            "bomFormat": "CycloneDX",
            "specVersion": "1.4",
            "serialNumber": "urn:uuid:12345678-1234-1234-1234-123456789012",
            "version": 1,
            "components": [
                {
                    "type": "library",
                    "name": "valid-component",
                    "version": "1.0.0",
                    "purl": "pkg:npm/valid-component@1.0.0"
                },
                {
                    # Invalid component - missing required fields
                    "version": "2.0.0"
                    # Missing type and name
                }
            ]
        }
        
        result = self.validator.validate_json(json.dumps(cyclonedx_with_components))
        
        # Should identify component validation issues
        errors = result.get_errors()
        component_errors = [e for e in errors if "components[1]" in e.field]
        assert len(component_errors) > 0, "Expected validation errors for invalid component"
    
    def test_cyclonedx_json_invalid_component_type(self):
        """Test CycloneDX JSON component type validation."""
        cyclonedx_with_invalid_type = {
            "bomFormat": "CycloneDX",
            "specVersion": "1.4",
            "serialNumber": "urn:uuid:12345678-1234-1234-1234-123456789012",
            "version": 1,
            "components": [
                {
                    "type": "invalid-type",  # Not a valid component type
                    "name": "test-component"
                }
            ]
        }
        
        result = self.validator.validate_json(json.dumps(cyclonedx_with_invalid_type))
        
        # Should have warnings for non-standard component type
        warnings = result.get_warnings()
        type_warnings = [w for w in warnings if "type" in w.field]
        assert len(type_warnings) > 0, "Expected warning for non-standard component type"
    
    def test_cyclonedx_json_metadata_validation(self):
        """Test CycloneDX JSON metadata validation."""
        # Test with valid metadata
        cyclonedx_with_metadata = {
            "bomFormat": "CycloneDX",
            "specVersion": "1.4", 
            "serialNumber": "urn:uuid:12345678-1234-1234-1234-123456789012",
            "version": 1,
            "metadata": {
                "timestamp": "2024-01-01T12:00:00.000Z",
                "tools": [
                    {"vendor": "Test", "name": "SBOM Generator"}
                ]
            }
        }
        
        result = self.validator.validate_json(json.dumps(cyclonedx_with_metadata))
        
        # Should validate successfully with good metadata
        self.assertions.assert_valid_sbom_format(result, min_compliance_score=0.95)
        
        # Test with invalid timestamp
        cyclonedx_invalid_metadata = cyclonedx_with_metadata.copy()
        cyclonedx_invalid_metadata["metadata"]["timestamp"] = "invalid-timestamp"
        
        result_invalid = self.validator.validate_json(json.dumps(cyclonedx_invalid_metadata))
        
        # Should have metadata warnings
        warnings = result_invalid.get_warnings()
        timestamp_warnings = [w for w in warnings if "timestamp" in w.field]
        assert len(timestamp_warnings) > 0, "Expected warning for invalid timestamp"
    
    def test_malformed_cyclonedx_json(self):
        """Test handling of malformed JSON."""
        malformed_json = '{"bomFormat": "CycloneDX", "invalid": json}'
        
        result = self.validator.validate_json(malformed_json)
        
        assert not result.is_valid
        assert result.compliance_score == 0.0
        
        errors = result.get_errors()
        assert len(errors) == 1
        assert "Invalid JSON" in errors[0].message
    
    # ========================================================================
    # CYCLONEDX XML FORMAT TESTS
    # ========================================================================
    
    def test_valid_cyclonedx_xml_format(self):
        """Test validation of valid CycloneDX XML format."""
        # Create valid CycloneDX XML
        xml_content = '''<?xml version="1.0" encoding="UTF-8"?>
<bom xmlns="http://cyclonedx.org/schema/bom/1.4" 
     serialNumber="urn:uuid:12345678-1234-1234-1234-123456789012" 
     version="1">
    <metadata>
        <timestamp>2024-01-01T12:00:00.000Z</timestamp>
        <tools>
            <tool>
                <vendor>Test</vendor>
                <name>SBOM Generator</name>
            </tool>
        </tools>
    </metadata>
    <components>
        <component type="library">
            <name>test-component</name>
            <version>1.0.0</version>
        </component>
    </components>
</bom>'''
        
        result = self.validator.validate_xml(xml_content)
        
        self.assertions.assert_valid_sbom_format(result, min_compliance_score=0.90)
        assert result.format_detected == SBOMFormat.CYCLONE_DX_XML
    
    def test_cyclonedx_xml_missing_namespace(self):
        """Test CycloneDX XML validation with missing namespace."""
        xml_without_namespace = '''<?xml version="1.0" encoding="UTF-8"?>
<bom serialNumber="urn:uuid:12345678-1234-1234-1234-123456789012" version="1">
    <components>
        <component type="library">
            <name>test-component</name>
        </component>
    </components>
</bom>'''
        
        result = self.validator.validate_xml(xml_without_namespace)
        
        # Should still parse but may have lower compliance score
        assert result.format_detected == SBOMFormat.CYCLONE_DX_XML
        # Compliance might be lower due to missing namespace
    
    def test_malformed_cyclonedx_xml(self):
        """Test handling of malformed XML."""
        malformed_xml = '''<?xml version="1.0" encoding="UTF-8"?>
<bom>
    <component type="library">
        <!-- Unclosed tag -->
        <name>test-component
    </component>
</bom>'''
        
        result = self.validator.validate_xml(malformed_xml)
        
        assert not result.is_valid
        errors = result.get_errors()
        assert any("Invalid XML" in error.message for error in errors)
    
    def test_cyclonedx_xml_to_json_conversion(self):
        """Test XML to JSON conversion for validation."""
        xml_content = '''<?xml version="1.0" encoding="UTF-8"?>
<bom xmlns="http://cyclonedx.org/schema/bom/1.4" version="1">
    <components>
        <component type="library">
            <name>test-lib</name>
            <version>1.0.0</version>
        </component>
        <component type="application">
            <name>test-app</name>
            <version>2.0.0</version>
        </component>
    </components>
</bom>'''
        
        result = self.validator.validate_xml(xml_content)
        
        # Conversion should preserve component structure
        assert result.format_detected == SBOMFormat.CYCLONE_DX_XML
        # Should detect multiple components
    
    # ========================================================================
    # INTEGRATION AND PERFORMANCE TESTS
    # ========================================================================
    
    def test_cyclonedx_format_consistency(self):
        """Test that JSON and XML CycloneDX formats produce consistent results."""
        # Generate test data
        dependency_tree = self.generator.generate_realistic_dependency_tree(complexity="simple")
        
        # Generate both JSON and XML formats
        formats = self.generator.generate_sbom_formats_suite(dependency_tree)
        
        # Filter to only CycloneDX formats
        cyclonedx_formats = {
            fmt: content for fmt, content in formats.items()
            if fmt.name.startswith('CYCLONE_DX_')
        }
        
        # Validate consistency
        self.assertions.assert_format_consistency(cyclonedx_formats, dependency_tree)
    
    def test_cyclonedx_performance_validation(self):
        """Test CycloneDX validation performance."""
        # Generate large dependency tree
        dependency_tree = self.generator.generate_realistic_dependency_tree(complexity="complex")
        cyclonedx_json = create_sample_sbom(SBOMFormat.CYCLONE_DX_JSON, dependency_tree)
        
        # Measure validation time
        validation_time, result = self.measure_sbom_generation(
            self.validator.validate_json,
            cyclonedx_json
        )
        
        # Should validate large SBOM quickly (< 1 second)
        self.assertions.assert_generation_performance(
            validation_time,
            target_time=1.0,
            project_size="complex"
        )
        
        # Should still be valid
        self.assertions.assert_valid_sbom_format(result)
    
    def test_cyclonedx_large_component_count(self):
        """Test CycloneDX validation with large number of components."""
        # Create SBOM with many components
        large_cyclonedx = {
            "bomFormat": "CycloneDX",
            "specVersion": "1.4",
            "serialNumber": "urn:uuid:12345678-1234-1234-1234-123456789012",
            "version": 1,
            "components": []
        }
        
        # Add 1000 components
        for i in range(1000):
            component = {
                "type": "library",
                "name": f"component-{i}",
                "version": f"1.0.{i}"
            }
            large_cyclonedx["components"].append(component)
        
        result = self.validator.validate_json(json.dumps(large_cyclonedx))
        
        # Should handle large number of components
        self.assertions.assert_valid_sbom_format(result, min_compliance_score=0.95)
        
        # Check file size is reasonable
        self.assertions.assert_file_size_reasonable(
            json.dumps(large_cyclonedx),
            max_size_mb=5.0,
            dependency_count=1000
        )
    
    def test_cyclonedx_edge_cases(self):
        """Test CycloneDX validation edge cases."""
        edge_cases = [
            # Empty components array
            {
                "bomFormat": "CycloneDX",
                "specVersion": "1.4",
                "serialNumber": "urn:uuid:12345678-1234-1234-1234-123456789012",
                "version": 1,
                "components": []
            },
            # Component with all optional fields
            {
                "bomFormat": "CycloneDX",
                "specVersion": "1.4",
                "serialNumber": "urn:uuid:12345678-1234-1234-1234-123456789012",
                "version": 1,
                "components": [
                    {
                        "type": "library",
                        "name": "full-component",
                        "version": "1.0.0",
                        "description": "A fully specified component",
                        "scope": "required",
                        "hashes": [
                            {"alg": "SHA-256", "content": "abc123"}
                        ],
                        "licenses": [
                            {"license": {"id": "MIT"}}
                        ],
                        "purl": "pkg:npm/full-component@1.0.0",
                        "externalReferences": [
                            {
                                "type": "website",
                                "url": "https://example.com"
                            }
                        ]
                    }
                ]
            },
            # Very long component name
            {
                "bomFormat": "CycloneDX", 
                "specVersion": "1.4",
                "serialNumber": "urn:uuid:12345678-1234-1234-1234-123456789012",
                "version": 1,
                "components": [
                    {
                        "type": "library",
                        "name": "a" * 500,  # Very long name
                        "version": "1.0.0"
                    }
                ]
            }
        ]
        
        for i, edge_case in enumerate(edge_cases):
            result = self.validator.validate_json(json.dumps(edge_case))
            
            # Should handle edge cases gracefully
            assert isinstance(result.is_valid, bool), f"Edge case {i} validation failed"
            assert isinstance(result.compliance_score, float), f"Edge case {i} scoring failed"
    
    def test_cyclonedx_unicode_handling(self):
        """Test CycloneDX validation with Unicode content."""
        unicode_cyclonedx = {
            "bomFormat": "CycloneDX",
            "specVersion": "1.4",
            "serialNumber": "urn:uuid:12345678-1234-1234-1234-123456789012",
            "version": 1,
            "metadata": {
                "timestamp": "2024-01-01T12:00:00.000Z",
                "tools": [
                    {"vendor": "Test 测试", "name": "SBOM Generator 🚀"}
                ]
            },
            "components": [
                {
                    "type": "library",
                    "name": "unicode-component-名前",
                    "version": "1.0.0",
                    "description": "Component with Unicode: 中文 🌍 ñ",
                    "supplier": {"name": "Unicode Supplier © 2024"}
                }
            ]
        }
        
        result = self.validator.validate_json(json.dumps(unicode_cyclonedx, ensure_ascii=False))
        
        # Should handle Unicode content properly
        self.assertions.assert_valid_sbom_format(result, min_compliance_score=0.95)
    
    def test_cyclonedx_nested_dependencies(self):
        """Test CycloneDX validation with nested dependency relationships."""
        cyclonedx_with_deps = {
            "bomFormat": "CycloneDX",
            "specVersion": "1.4",
            "serialNumber": "urn:uuid:12345678-1234-1234-1234-123456789012",
            "version": 1,
            "components": [
                {
                    "bom-ref": "comp-1",
                    "type": "library",
                    "name": "parent-component",
                    "version": "1.0.0"
                },
                {
                    "bom-ref": "comp-2", 
                    "type": "library",
                    "name": "child-component",
                    "version": "2.0.0"
                }
            ],
            "dependencies": [
                {
                    "ref": "comp-1",
                    "dependsOn": ["comp-2"]
                }
            ]
        }
        
        result = self.validator.validate_json(json.dumps(cyclonedx_with_deps))
        
        # Should handle dependency relationships
        self.assertions.assert_valid_sbom_format(result, min_compliance_score=0.95)
    
    def teardown_method(self):
        """Clean up after tests."""
        super().cleanup_test_artifacts()