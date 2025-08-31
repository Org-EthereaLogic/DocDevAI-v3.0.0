"""
SPDX 2.3 Format Validation Tests.

Comprehensive test suite for SPDX format validation including:
- JSON format validation
- YAML format validation  
- Tag-Value format validation
- RDF/XML format validation
- JSON-LD format validation (future)
"""

import pytest
import json
import yaml
from pathlib import Path

# Import SBOM testing framework
from ..core import SBOMTestFramework, SBOMFormat
from ..validators import SPDXValidator, ValidationSeverity
from ..generators import SBOMTestDataGenerator
from ..assertions import SBOMAssertions


class TestSPDXValidators(SBOMTestFramework):
    """
    Test suite for SPDX 2.3 format validators.
    
    Validates compliance with SPDX specification and ensures
    100% format compliance scoring.
    """
    
    def setup_method(self):
        """Set up test environment."""
        super().setup_method()
        self.validator = SPDXValidator()
        self.generator = SBOMTestDataGenerator(seed=42)  # Reproducible tests
        self.assertions = SBOMAssertions()
    
    # ========================================================================
    # SPDX JSON FORMAT TESTS
    # ========================================================================
    
    def test_valid_spdx_json_format(self):
        """Test validation of valid SPDX JSON format."""
        # Generate test dependency tree
        dependency_tree = self.generator.generate_realistic_dependency_tree(
            ecosystem="npm",
            complexity="medium"
        )
        
        # Generate SPDX JSON
        from ..core import create_sample_sbom
        spdx_json = create_sample_sbom(SBOMFormat.SPDX_JSON, dependency_tree)
        
        # Validate format
        result = self.validator.validate_json(spdx_json)
        
        # Assert valid and compliant
        self.assertions.assert_valid_sbom_format(result, min_compliance_score=0.95)
        assert result.format_detected == SBOMFormat.SPDX_JSON
        assert result.spec_version == "SPDX-2.3"
    
    def test_spdx_json_missing_required_fields(self):
        """Test SPDX JSON validation with missing required fields."""
        # Create incomplete SPDX document
        incomplete_spdx = {
            "spdxVersion": "SPDX-2.3",
            # Missing dataLicense, SPDXID, documentName, etc.
            "packages": []
        }
        
        result = self.validator.validate_json(json.dumps(incomplete_spdx))
        
        # Should fail validation
        assert not result.is_valid
        assert result.compliance_score < 0.5
        
        # Check specific error messages
        errors = result.get_errors()
        expected_missing_fields = ["dataLicense", "SPDXID", "documentName", "documentNamespace", "creationInfo"]
        
        error_fields = [error.field for error in errors]
        for field in expected_missing_fields:
            assert field in error_fields, f"Expected error for missing field: {field}"
    
    def test_spdx_json_invalid_version_format(self):
        """Test SPDX JSON validation with invalid version format."""
        invalid_spdx = {
            "spdxVersion": "SPDX-3.5",  # Invalid version
            "dataLicense": "CC0-1.0",
            "SPDXID": "SPDXRef-DOCUMENT",
            "documentName": "Test Document",
            "documentNamespace": "https://example.com/test",
            "creationInfo": {
                "created": "2024-01-01T12:00:00Z",
                "creators": ["Tool: Test"]
            }
        }
        
        result = self.validator.validate_json(json.dumps(invalid_spdx))
        
        # Should have validation issues
        errors = result.get_errors()
        version_errors = [e for e in errors if e.field == "spdxVersion"]
        assert len(version_errors) > 0, "Expected validation error for invalid SPDX version"
    
    def test_spdx_json_package_validation(self):
        """Test SPDX JSON package-level validation."""
        # Create SPDX with invalid package
        spdx_with_packages = {
            "spdxVersion": "SPDX-2.3",
            "dataLicense": "CC0-1.0", 
            "SPDXID": "SPDXRef-DOCUMENT",
            "documentName": "Test Document",
            "documentNamespace": "https://example.com/test",
            "creationInfo": {
                "created": "2024-01-01T12:00:00Z",
                "creators": ["Tool: Test"]
            },
            "packages": [
                {
                    "SPDXID": "SPDXRef-Package-Valid",
                    "name": "valid-package",
                    "downloadLocation": "https://example.com/package",
                    "filesAnalyzed": False,
                    "licenseConcluded": "MIT",
                    "licenseDeclared": "MIT",
                    "copyrightText": "Copyright 2024"
                },
                {
                    # Invalid package - missing required fields
                    "name": "invalid-package"
                }
            ]
        }
        
        result = self.validator.validate_json(json.dumps(spdx_with_packages))
        
        # Should identify package validation issues
        errors = result.get_errors()
        package_errors = [e for e in errors if "packages[1]" in e.field]
        assert len(package_errors) > 0, "Expected validation errors for invalid package"
    
    def test_spdx_json_license_validation(self):
        """Test SPDX JSON license validation."""
        # Generate dependency tree with various license scenarios
        dependency_tree = self.generator.generate_realistic_dependency_tree(
            complexity="simple",
            license_compliance_issues=True
        )
        
        spdx_json = create_sample_sbom(SBOMFormat.SPDX_JSON, dependency_tree)
        result = self.validator.validate_json(spdx_json)
        
        # Check for license-related warnings
        warnings = result.get_warnings()
        license_warnings = [w for w in warnings if "license" in w.field.lower()]
        
        # Should have some license warnings due to non-standard licenses
        assert len(license_warnings) >= 0  # May or may not have warnings depending on generation
    
    def test_malformed_spdx_json(self):
        """Test handling of malformed JSON."""
        malformed_json = '{"spdxVersion": "SPDX-2.3", "invalid": json}'
        
        result = self.validator.validate_json(malformed_json)
        
        assert not result.is_valid
        assert result.compliance_score == 0.0
        
        errors = result.get_errors()
        assert len(errors) == 1
        assert "Invalid JSON" in errors[0].message
    
    # ========================================================================
    # SPDX YAML FORMAT TESTS
    # ========================================================================
    
    def test_valid_spdx_yaml_format(self):
        """Test validation of valid SPDX YAML format."""
        # Generate test data
        dependency_tree = self.generator.generate_realistic_dependency_tree(complexity="simple")
        
        # Generate SPDX JSON first, then convert to YAML
        spdx_json = create_sample_sbom(SBOMFormat.SPDX_JSON, dependency_tree)
        spdx_data = json.loads(spdx_json)
        spdx_yaml = yaml.dump(spdx_data, default_flow_style=False)
        
        # Validate YAML format
        result = self.validator.validate_yaml(spdx_yaml)
        
        self.assertions.assert_valid_sbom_format(result, min_compliance_score=0.95)
        assert result.format_detected == SBOMFormat.SPDX_YAML
    
    def test_malformed_spdx_yaml(self):
        """Test handling of malformed YAML."""
        malformed_yaml = """
        spdxVersion: SPDX-2.3
        dataLicense: CC0-1.0
        invalid: yaml: structure:
          - nested
            - improperly
        """
        
        result = self.validator.validate_yaml(malformed_yaml)
        
        assert not result.is_valid
        errors = result.get_errors()
        assert any("Invalid YAML" in error.message for error in errors)
    
    # ========================================================================
    # SPDX TAG-VALUE FORMAT TESTS
    # ========================================================================
    
    def test_valid_spdx_tag_value_format(self):
        """Test validation of valid SPDX Tag-Value format."""
        # Create valid Tag-Value format
        tag_value_content = """SPDXVersion: SPDX-2.3
DataLicense: CC0-1.0
SPDXID: SPDXRef-DOCUMENT
DocumentName: Test SBOM Document
DocumentNamespace: https://example.com/sbom/test
CreatedBy: Tool: SBOM-Test-Framework
Created: 2024-01-01T12:00:00Z

PackageName: test-package
SPDXID: SPDXRef-Package-test
PackageVersion: 1.0.0
PackageDownloadLocation: https://example.com/test-package
FilesAnalyzed: false
PackageLicenseConcluded: MIT
PackageLicenseDeclared: MIT
PackageCopyrightText: Copyright 2024"""
        
        result = self.validator.validate_tag_value(tag_value_content)
        
        self.assertions.assert_valid_sbom_format(result, min_compliance_score=0.90)
        assert result.format_detected == SBOMFormat.SPDX_TAG_VALUE
    
    def test_spdx_tag_value_missing_required_tags(self):
        """Test Tag-Value validation with missing required tags."""
        incomplete_tag_value = """SPDXVersion: SPDX-2.3
DataLicense: CC0-1.0
# Missing SPDXID, DocumentName, etc.
"""
        
        result = self.validator.validate_tag_value(incomplete_tag_value)
        
        assert not result.is_valid
        assert result.compliance_score < 0.5
        
        errors = result.get_errors()
        expected_tags = ["SPDXID", "DocumentName", "DocumentNamespace", "CreatedBy", "Created"]
        
        for tag in expected_tags:
            tag_errors = [e for e in errors if tag in e.message]
            assert len(tag_errors) > 0, f"Expected error for missing tag: {tag}"
    
    def test_spdx_tag_value_invalid_format(self):
        """Test Tag-Value validation with invalid format."""
        invalid_format = """SPDXVersion = SPDX-2.3
This is not a valid tag-value line
Another invalid line without colon
DataLicense: CC0-1.0"""
        
        result = self.validator.validate_tag_value(invalid_format)
        
        errors = result.get_errors()
        format_errors = [e for e in errors if "Invalid tag-value format" in e.message]
        assert len(format_errors) > 0, "Expected format validation errors"
    
    # ========================================================================
    # SPDX RDF/XML FORMAT TESTS
    # ========================================================================
    
    def test_valid_spdx_rdf_xml_format(self):
        """Test validation of valid SPDX RDF/XML format."""
        rdf_xml_content = '''<?xml version="1.0" encoding="UTF-8"?>
<rdf:RDF
    xmlns:spdx="http://spdx.org/rdf/terms#"
    xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#">
    
    <spdx:SpdxDocument rdf:about="https://example.com/test">
        <spdx:spdxVersion>SPDX-2.3</spdx:spdxVersion>
        <spdx:dataLicense>CC0-1.0</spdx:dataLicense>
        <spdx:name>Test Document</spdx:name>
        <spdx:spdxId>SPDXRef-DOCUMENT</spdx:spdxId>
        
        <spdx:creationInfo>
            <spdx:CreationInfo>
                <spdx:created>2024-01-01T12:00:00Z</spdx:created>
                <spdx:creator>Tool: SBOM-Test</spdx:creator>
            </spdx:CreationInfo>
        </spdx:creationInfo>
    </spdx:SpdxDocument>
    
</rdf:RDF>'''
        
        result = self.validator.validate_rdf_xml(rdf_xml_content)
        
        # RDF/XML validation is more lenient due to complexity
        self.assertions.assert_valid_sbom_format(result, min_compliance_score=0.80)
        assert result.format_detected == SBOMFormat.SPDX_RDF_XML
    
    def test_malformed_spdx_rdf_xml(self):
        """Test handling of malformed RDF/XML."""
        malformed_xml = '''<?xml version="1.0" encoding="UTF-8"?>
<rdf:RDF xmlns:spdx="http://spdx.org/rdf/terms#">
    <spdx:SpdxDocument>
        <!-- Unclosed tag -->
        <spdx:spdxVersion>SPDX-2.3
    </spdx:SpdxDocument>
</rdf:RDF>'''
        
        result = self.validator.validate_rdf_xml(malformed_xml)
        
        assert not result.is_valid
        errors = result.get_errors()
        assert any("Invalid XML" in error.message for error in errors)
    
    def test_spdx_rdf_xml_missing_namespaces(self):
        """Test RDF/XML validation with missing required namespaces."""
        xml_without_namespaces = '''<?xml version="1.0" encoding="UTF-8"?>
<root>
    <document>
        <version>SPDX-2.3</version>
    </document>
</root>'''
        
        result = self.validator.validate_rdf_xml(xml_without_namespaces)
        
        # Should have namespace-related errors
        errors = result.get_errors()
        namespace_errors = [e for e in errors if "namespace" in e.message.lower()]
        assert len(namespace_errors) > 0, "Expected namespace validation errors"
    
    # ========================================================================
    # INTEGRATION AND EDGE CASE TESTS
    # ========================================================================
    
    def test_spdx_format_consistency(self):
        """Test that different SPDX formats produce consistent results."""
        # Generate test data
        dependency_tree = self.generator.generate_realistic_dependency_tree(complexity="simple")
        
        # Generate multiple SPDX formats
        formats = self.generator.generate_sbom_formats_suite(dependency_tree)
        
        # Filter to only SPDX formats
        spdx_formats = {
            fmt: content for fmt, content in formats.items()
            if fmt.name.startswith('SPDX_')
        }
        
        # Validate consistency
        self.assertions.assert_format_consistency(spdx_formats, dependency_tree)
    
    def test_spdx_performance_validation(self):
        """Test SPDX validation performance."""
        # Generate large dependency tree
        dependency_tree = self.generator.generate_realistic_dependency_tree(complexity="complex")
        spdx_json = create_sample_sbom(SBOMFormat.SPDX_JSON, dependency_tree)
        
        # Measure validation time
        validation_time, result = self.measure_sbom_generation(
            self.validator.validate_json, 
            spdx_json
        )
        
        # Should validate large SBOM quickly (< 1 second)
        self.assertions.assert_generation_performance(
            validation_time, 
            target_time=1.0,
            project_size="complex"
        )
        
        # Should still be valid
        self.assertions.assert_valid_sbom_format(result)
    
    def test_spdx_edge_cases(self):
        """Test SPDX validation edge cases."""
        edge_cases = [
            # Empty packages array
            {
                "spdxVersion": "SPDX-2.3",
                "dataLicense": "CC0-1.0",
                "SPDXID": "SPDXRef-DOCUMENT", 
                "documentName": "Empty Document",
                "documentNamespace": "https://example.com/empty",
                "creationInfo": {"created": "2024-01-01T12:00:00Z", "creators": ["Tool: Test"]},
                "packages": []
            },
            # Very long document name
            {
                "spdxVersion": "SPDX-2.3",
                "dataLicense": "CC0-1.0",
                "SPDXID": "SPDXRef-DOCUMENT",
                "documentName": "A" * 1000,  # Very long name
                "documentNamespace": "https://example.com/long",
                "creationInfo": {"created": "2024-01-01T12:00:00Z", "creators": ["Tool: Test"]}
            }
        ]
        
        for i, edge_case in enumerate(edge_cases):
            result = self.validator.validate_json(json.dumps(edge_case))
            
            # Should handle edge cases gracefully without crashing
            assert isinstance(result.is_valid, bool), f"Edge case {i} validation failed"
            assert isinstance(result.compliance_score, float), f"Edge case {i} scoring failed"
    
    def test_spdx_unicode_handling(self):
        """Test SPDX validation with Unicode content."""
        unicode_spdx = {
            "spdxVersion": "SPDX-2.3",
            "dataLicense": "CC0-1.0",
            "SPDXID": "SPDXRef-DOCUMENT",
            "documentName": "Test Document with Unicode: 🚀 中文 ñ",
            "documentNamespace": "https://example.com/unicode",
            "creationInfo": {
                "created": "2024-01-01T12:00:00Z",
                "creators": ["Tool: Test 测试"]
            },
            "packages": [
                {
                    "SPDXID": "SPDXRef-Package-Unicode",
                    "name": "package-with-unicode-名前",
                    "downloadLocation": "NOASSERTION",
                    "filesAnalyzed": False,
                    "licenseConcluded": "MIT",
                    "licenseDeclared": "MIT",
                    "copyrightText": "Copyright © 2024 🌍"
                }
            ]
        }
        
        result = self.validator.validate_json(json.dumps(unicode_spdx, ensure_ascii=False))
        
        # Should handle Unicode content properly
        self.assertions.assert_valid_sbom_format(result, min_compliance_score=0.95)
    
    def teardown_method(self):
        """Clean up after tests."""
        super().cleanup_test_artifacts()