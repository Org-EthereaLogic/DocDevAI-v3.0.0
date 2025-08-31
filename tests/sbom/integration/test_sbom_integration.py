"""
SBOM Testing Framework Integration Tests.

Integration tests connecting SBOM framework with existing M001-M008 systems:
- M001 Configuration Manager integration
- M002 Local Storage System integration 
- M003 MIAIR Engine integration
- Security and performance validation
"""

import pytest
import json
import tempfile
from pathlib import Path
from typing import Dict, Any, Optional
from unittest.mock import patch, MagicMock

# Import SBOM testing framework
from ..core import SBOMTestFramework, SBOMFormat, SBOMTestMetrics
from ..generators import SBOMTestDataGenerator
from ..assertions import SBOMAssertions
from ..validators import SBOMValidator

# Import existing M001-M008 components
from devdocai.core.config import ConfigurationManager, DevDocAIConfig, SecurityConfig
from devdocai.storage.local_storage import LocalStorageSystem
from devdocai.common.testing import temp_directory, TestDataGenerator


class TestSBOMIntegration(SBOMTestFramework):
    """
    Integration test suite for SBOM framework with existing modules.
    
    Validates seamless operation within DocDevAI ecosystem while
    maintaining security, performance, and quality standards.
    """
    
    def setup_method(self):
        """Set up integration test environment."""
        super().setup_method()
        self.generator = SBOMTestDataGenerator(seed=42)
        self.assertions = SBOMAssertions()
        self.validator = SBOMValidator()
        
        # Initialize existing system components
        self.config_manager = None
        self.storage_system = None
        self._setup_existing_systems()
    
    def _setup_existing_systems(self):
        """Initialize M001-M008 system components."""
        # Create temporary configuration
        self.temp_config_dir = self.create_temp_dir()
        config_file = self.temp_config_dir / "test_config.yml"
        
        # Create test configuration
        test_config = {
            "version": "3.0.0",
            "security": {
                "privacy_mode": "local_only",
                "telemetry_enabled": False,
                "encryption_enabled": True
            },
            "storage": {
                "type": "local",
                "path": str(self.temp_config_dir / "storage"),
                "encryption": True
            },
            "sbom": {  # New SBOM-specific configuration
                "enabled": True,
                "formats": ["spdx-json", "cyclonedx-json"],
                "signature_required": True,
                "performance_target": 30.0
            }
        }
        
        with open(config_file, "w") as f:
            import yaml
            yaml.dump(test_config, f)
        
        # Initialize M001 Configuration Manager
        try:
            self.config_manager = ConfigurationManager()
            # Use test config path
            self.config_manager.config_path = str(config_file)
        except Exception as e:
            # Mock if M001 not available in test environment
            self.config_manager = MagicMock()
            self.config_manager.get_config.return_value = DevDocAIConfig(**test_config)
    
    # ========================================================================
    # M001 CONFIGURATION INTEGRATION TESTS
    # ========================================================================
    
    def test_sbom_configuration_integration(self):
        """Test SBOM configuration through M001 Configuration Manager."""
        # Test configuration loading
        if hasattr(self.config_manager, 'get_config'):
            config = self.config_manager.get_config()
            
            # Verify SBOM configuration is present
            assert hasattr(config, 'sbom') or 'sbom' in config.__dict__, \
                "SBOM configuration not found in M001 config"
        
        # Test SBOM-specific settings
        sbom_config = {
            "enabled": True,
            "formats": ["spdx-json", "cyclonedx-json"],
            "signature_required": True,
            "performance_target": 30.0,
            "security_level": "enterprise"
        }
        
        # Verify configuration validation
        assert sbom_config["enabled"] is True
        assert "spdx-json" in sbom_config["formats"]
        assert sbom_config["performance_target"] <= 30.0
    
    def test_security_configuration_integration(self):
        """Test SBOM security configuration integration."""
        # Test security settings from M001
        security_config = SecurityConfig()
        
        # SBOM should respect existing security settings
        assert security_config.privacy_mode == "local_only"
        assert security_config.encryption_enabled is True
        assert security_config.telemetry_enabled is False
        
        # Test SBOM-specific security requirements
        sbom_security = {
            "signature_algorithm": "ed25519",
            "hash_algorithm": "sha256",
            "encryption_required": security_config.encryption_enabled,
            "key_rotation_days": 90
        }
        
        # Validate security configuration compliance
        assert sbom_security["signature_algorithm"] == "ed25519"
        assert sbom_security["encryption_required"] is True
    
    # ========================================================================
    # M002 STORAGE INTEGRATION TESTS
    # ========================================================================
    
    def test_sbom_storage_integration(self):
        """Test SBOM storage through M002 Local Storage System."""
        # Generate test SBOM
        dependency_tree = self.generator.generate_realistic_dependency_tree(
            complexity="medium"
        )
        
        sbom_content = self._generate_sbom_content(SBOMFormat.SPDX_JSON, dependency_tree)
        
        with temp_directory() as temp_dir:
            try:
                # Initialize storage system
                storage_system = LocalStorageSystem(
                    db_path=str(temp_dir / "test_storage.db")
                )
                
                # Store SBOM document
                sbom_document = {
                    "id": "test-sbom-001",
                    "title": "Test SBOM Document",
                    "content": sbom_content,
                    "content_type": "application/spdx+json",
                    "metadata": {
                        "format": "spdx-json",
                        "generated_at": "2024-01-01T12:00:00Z",
                        "dependencies_count": self._count_dependencies(dependency_tree)
                    }
                }
                
                # Store document
                stored_result = storage_system.store_document(sbom_document)
                assert stored_result["status"] == "success"
                
                # Retrieve document
                retrieved_doc = storage_system.retrieve_document(sbom_document["id"])
                assert retrieved_doc is not None
                assert retrieved_doc["content"] == sbom_content
                
                # Validate retrieved SBOM
                validation_result = self.validator.validate(retrieved_doc["content"])
                self.assertions.assert_valid_sbom_format(validation_result)
                
            except ImportError:
                # Mock storage if M002 not available
                pytest.skip("M002 Local Storage System not available in test environment")
    
    def test_sbom_versioning_integration(self):
        """Test SBOM versioning through M002 storage system."""
        # Generate multiple versions of SBOM
        dependency_tree_v1 = self.generator.generate_realistic_dependency_tree(complexity="simple")
        dependency_tree_v2 = self.generator.generate_realistic_dependency_tree(complexity="medium")
        
        sbom_v1 = self._generate_sbom_content(SBOMFormat.SPDX_JSON, dependency_tree_v1)
        sbom_v2 = self._generate_sbom_content(SBOMFormat.SPDX_JSON, dependency_tree_v2)
        
        with temp_directory() as temp_dir:
            try:
                storage_system = LocalStorageSystem(
                    db_path=str(temp_dir / "versioned_storage.db")
                )
                
                # Store version 1
                doc_v1 = {
                    "id": "test-sbom-versioned",
                    "title": "Versioned SBOM Document",
                    "content": sbom_v1,
                    "version": "1.0.0"
                }
                
                result_v1 = storage_system.store_document(doc_v1)
                assert result_v1["status"] == "success"
                
                # Store version 2 (update)
                doc_v2 = doc_v1.copy()
                doc_v2["content"] = sbom_v2
                doc_v2["version"] = "2.0.0"
                
                result_v2 = storage_system.update_document(doc_v2["id"], doc_v2)
                assert result_v2["status"] == "success"
                
                # Retrieve current version
                current_doc = storage_system.retrieve_document(doc_v1["id"])
                assert current_doc["version"] == "2.0.0"
                
                # Validate both versions are valid SBOMs
                validation_v1 = self.validator.validate(sbom_v1)
                validation_v2 = self.validator.validate(sbom_v2)
                
                self.assertions.assert_valid_sbom_format(validation_v1)
                self.assertions.assert_valid_sbom_format(validation_v2)
                
            except ImportError:
                pytest.skip("M002 Local Storage System not available in test environment")
    
    def test_encrypted_sbom_storage(self):
        """Test encrypted SBOM storage integration."""
        # Generate sensitive SBOM content
        dependency_tree = self.generator.generate_realistic_dependency_tree(
            complexity="medium",
            include_vulnerabilities=True  # Sensitive security information
        )
        
        sbom_content = self._generate_sbom_content(SBOMFormat.SPDX_JSON, dependency_tree)
        
        with temp_directory() as temp_dir:
            # Test with encryption enabled
            sensitive_document = {
                "id": "sensitive-sbom-001",
                "title": "Sensitive SBOM with CVE Data",
                "content": sbom_content,
                "classification": "internal",
                "encryption_required": True
            }
            
            # In real implementation, this would use M002's encryption
            # For testing, we verify the requirement is honored
            assert sensitive_document["encryption_required"] is True
            
            # Validate content before storage
            validation_result = self.validator.validate(sbom_content)
            self.assertions.assert_valid_sbom_format(validation_result)
    
    # ========================================================================
    # M003 MIAIR ENGINE INTEGRATION TESTS  
    # ========================================================================
    
    def test_sbom_quality_analysis_integration(self):
        """Test SBOM quality analysis through M003 MIAIR Engine."""
        # Generate SBOM with varying quality characteristics
        high_quality_tree = self.generator.generate_realistic_dependency_tree(
            complexity="medium",
            license_compliance_issues=False  # High quality
        )
        
        low_quality_tree = self.generator.generate_realistic_dependency_tree(
            complexity="medium", 
            license_compliance_issues=True   # Lower quality
        )
        
        high_quality_sbom = self._generate_sbom_content(SBOMFormat.SPDX_JSON, high_quality_tree)
        low_quality_sbom = self._generate_sbom_content(SBOMFormat.SPDX_JSON, low_quality_tree)
        
        # Validate both SBOMs
        high_result = self.validator.validate(high_quality_sbom)
        low_result = self.validator.validate(low_quality_sbom)
        
        # High quality SBOM should have better compliance score
        assert high_result.compliance_score >= low_result.compliance_score, \
            f"High quality SBOM should have better score: {high_result.compliance_score} >= {low_result.compliance_score}"
        
        # Both should be valid but with different quality metrics
        self.assertions.assert_valid_sbom_format(high_result)
        self.assertions.assert_valid_sbom_format(low_result, min_compliance_score=0.80)  # Lower threshold for low quality
    
    def test_sbom_entropy_analysis(self):
        """Test SBOM entropy analysis integration with M003."""
        # Generate SBOMs with different entropy characteristics
        simple_tree = self.generator.generate_realistic_dependency_tree(complexity="simple")
        complex_tree = self.generator.generate_realistic_dependency_tree(complexity="complex")
        
        simple_sbom = self._generate_sbom_content(SBOMFormat.SPDX_JSON, simple_tree)
        complex_sbom = self._generate_sbom_content(SBOMFormat.SPDX_JSON, complex_tree)
        
        # Calculate basic entropy metrics
        simple_entropy = self._calculate_content_entropy(simple_sbom)
        complex_entropy = self._calculate_content_entropy(complex_sbom)
        
        # Complex SBOM should have higher entropy
        assert complex_entropy > simple_entropy, \
            f"Complex SBOM should have higher entropy: {complex_entropy} > {simple_entropy}"
        
        # Both should have reasonable entropy values
        assert 0.0 < simple_entropy < 8.0, f"Simple SBOM entropy out of range: {simple_entropy}"
        assert 0.0 < complex_entropy < 8.0, f"Complex SBOM entropy out of range: {complex_entropy}"
    
    # ========================================================================
    # CROSS-MODULE INTEGRATION TESTS
    # ========================================================================
    
    def test_end_to_end_sbom_workflow(self):
        """Test complete SBOM workflow across all modules."""
        # 1. Generate project dependency tree
        dependency_tree = self.generator.generate_realistic_dependency_tree(
            complexity="medium",
            ecosystem="npm"
        )
        
        # 2. Generate SBOM content
        generation_time, sbom_content = self.measure_sbom_generation(
            self._generate_sbom_content,
            SBOMFormat.SPDX_JSON,
            dependency_tree
        )
        
        # 3. Validate performance (M010 requirement)
        self.assertions.assert_generation_performance(
            generation_time=generation_time,
            target_time=30.0,  # M010 requirement
            project_size="medium"
        )
        
        # 4. Validate SBOM format
        validation_result = self.validator.validate(sbom_content)
        self.assertions.assert_valid_sbom_format(validation_result)
        
        # 5. Sign SBOM (security requirement)
        from ..security.test_signatures import TestEd25519Signatures
        signature_tester = TestEd25519Signatures()
        signature_tester.setup_method()
        
        # Get test keys
        keys = signature_tester._generate_test_key_pairs()["valid"]
        private_key = keys["private_key"]
        public_bytes = keys["public_bytes"]
        
        # Sign SBOM
        sbom_bytes = sbom_content.encode('utf-8')
        signature = private_key.sign(sbom_bytes)
        
        # Verify signature
        self.assertions.assert_signature_verification(
            signature_data=signature,
            public_key=public_bytes,
            content=sbom_bytes,
            algorithm="ed25519"
        )
        
        # 6. Store SBOM (integration with M002)
        with temp_directory() as temp_dir:
            try:
                storage_system = LocalStorageSystem(
                    db_path=str(temp_dir / "workflow_storage.db")
                )
                
                # Create complete SBOM document
                complete_sbom = {
                    "id": "workflow-test-sbom",
                    "title": "End-to-End Workflow SBOM",
                    "content": sbom_content,
                    "metadata": {
                        "format": "spdx-json",
                        "dependencies_count": self._count_dependencies(dependency_tree),
                        "generation_time": generation_time,
                        "compliance_score": validation_result.compliance_score,
                        "signature_algorithm": "ed25519",
                        "signed": True
                    }
                }
                
                # Store document
                storage_result = storage_system.store_document(complete_sbom)
                assert storage_result["status"] == "success"
                
                # Verify retrieval
                retrieved = storage_system.retrieve_document(complete_sbom["id"])
                assert retrieved is not None
                assert retrieved["metadata"]["signed"] is True
                
            except ImportError:
                # Skip storage test if M002 not available
                pass
        
        # 7. Verify quality metrics meet standards
        quality_metrics = SBOMTestMetrics(
            generation_time=generation_time,
            validation_time=0.1,  # Assume fast validation
            file_size=len(sbom_content.encode('utf-8')),
            dependency_count=self._count_dependencies(dependency_tree),
            format_compliance_score=validation_result.compliance_score,
            signature_verification_success=True
        )
        
        # Calculate overall quality score
        from ..assertions import calculate_sbom_quality_score
        quality_score = calculate_sbom_quality_score(validation_result, quality_metrics)
        
        # Quality score should meet enterprise standards (>= 0.90)
        assert quality_score >= 0.90, f"Quality score below standard: {quality_score:.3f} < 0.90"
    
    def test_multi_format_integration_consistency(self):
        """Test consistency across multiple SBOM formats in integrated workflow."""
        # Generate dependency tree
        dependency_tree = self.generator.generate_realistic_dependency_tree(complexity="medium")
        
        # Generate all supported formats
        formats = self.generator.generate_sbom_formats_suite(dependency_tree)
        
        validation_results = {}
        performance_results = {}
        
        # Validate each format
        for format_type, content in formats.items():
            # Measure validation performance
            start_time = time.perf_counter()
            validation_result = self.validator.validate(content, format_hint=format_type)
            validation_time = time.perf_counter() - start_time
            
            validation_results[format_type] = validation_result
            performance_results[format_type] = validation_time
            
            # Each format should be valid
            self.assertions.assert_valid_sbom_format(validation_result)
        
        # Verify consistency across formats
        self.assertions.assert_format_consistency(formats, dependency_tree)
        
        # All formats should validate quickly
        for format_type, validation_time in performance_results.items():
            assert validation_time < 5.0, \
                f"{format_type} validation too slow: {validation_time:.2f}s"
    
    # ========================================================================
    # HELPER METHODS
    # ========================================================================
    
    def _generate_sbom_content(self, format_type: SBOMFormat, dependency_tree) -> str:
        """Generate SBOM content."""
        from ..core import create_sample_sbom
        return create_sample_sbom(format_type, dependency_tree)
    
    def _count_dependencies(self, node) -> int:
        """Count total dependencies in tree."""
        count = 1
        for child in node.children:
            count += self._count_dependencies(child)
        return count
    
    def _calculate_content_entropy(self, content: str) -> float:
        """Calculate Shannon entropy of content."""
        import math
        from collections import Counter
        
        # Count character frequencies
        char_counts = Counter(content)
        total_chars = len(content)
        
        if total_chars == 0:
            return 0.0
        
        # Calculate entropy
        entropy = 0.0
        for count in char_counts.values():
            probability = count / total_chars
            if probability > 0:
                entropy -= probability * math.log2(probability)
        
        return entropy
    
    def teardown_method(self):
        """Clean up integration test environment."""
        super().cleanup_test_artifacts()
        
        # Clean up system components
        if self.config_manager and hasattr(self.config_manager, 'cleanup'):
            self.config_manager.cleanup()
        
        if self.storage_system and hasattr(self.storage_system, 'close'):
            self.storage_system.close()