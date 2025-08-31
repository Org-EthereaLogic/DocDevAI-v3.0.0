"""
Ed25519 Digital Signature Testing Framework.

Comprehensive test suite for SBOM digital signature verification including:
- Ed25519 key generation and management
- Digital signature creation and verification
- Signature validation in SBOM context
- Security attack simulation and edge cases
"""

import pytest
import json
import hashlib
import base64
from typing import Tuple, Dict, Any
from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.primitives import serialization
from cryptography.exceptions import InvalidSignature

# Import SBOM testing framework
from ..core import SBOMTestFramework, SBOMFormat
from ..generators import SBOMTestDataGenerator
from ..assertions import SBOMAssertions


class TestEd25519Signatures(SBOMTestFramework):
    """
    Test suite for Ed25519 digital signature verification.
    
    Validates 100% signature verification accuracy and security
    requirements for SBOM integrity protection.
    """
    
    def setup_method(self):
        """Set up test environment with key pairs."""
        super().setup_method()
        self.generator = SBOMTestDataGenerator(seed=42)
        self.assertions = SBOMAssertions()
        
        # Generate test key pairs
        self.test_keys = self._generate_test_key_pairs()
    
    def _generate_test_key_pairs(self) -> Dict[str, Dict[str, bytes]]:
        """Generate Ed25519 key pairs for testing."""
        key_pairs = {}
        
        # Generate multiple key pairs for different test scenarios
        scenarios = ["valid", "compromised", "expired", "revoked"]
        
        for scenario in scenarios:
            private_key = ed25519.Ed25519PrivateKey.generate()
            public_key = private_key.public_key()
            
            # Serialize keys
            private_bytes = private_key.private_bytes(
                encoding=serialization.Encoding.Raw,
                format=serialization.PrivateFormat.Raw,
                encryption_algorithm=serialization.NoEncryption()
            )
            
            public_bytes = public_key.public_bytes(
                encoding=serialization.Encoding.Raw,
                format=serialization.PublicFormat.Raw
            )
            
            key_pairs[scenario] = {
                "private_key": private_key,
                "public_key": public_key,
                "private_bytes": private_bytes,
                "public_bytes": public_bytes
            }
        
        return key_pairs
    
    # ========================================================================
    # BASIC SIGNATURE VERIFICATION TESTS
    # ========================================================================
    
    def test_valid_signature_verification(self):
        """Test successful Ed25519 signature verification."""
        # Get valid key pair
        keys = self.test_keys["valid"]
        private_key = keys["private_key"]
        public_bytes = keys["public_bytes"]
        
        # Create test content
        test_content = b"Test SBOM content for signature verification"
        
        # Sign the content
        signature = private_key.sign(test_content)
        
        # Verify signature using our assertion helper
        self.assertions.assert_signature_verification(
            signature_data=signature,
            public_key=public_bytes,
            content=test_content,
            algorithm="ed25519"
        )
        
        # Test should pass without raising AssertionError
    
    def test_invalid_signature_verification(self):
        """Test detection of invalid signatures."""
        # Get valid key pair
        keys = self.test_keys["valid"]
        private_key = keys["private_key"]
        public_bytes = keys["public_bytes"]
        
        # Create test content and sign it
        original_content = b"Original SBOM content"
        signature = private_key.sign(original_content)
        
        # Try to verify signature with modified content
        modified_content = b"Modified SBOM content"
        
        with pytest.raises(AssertionError, match="signature verification failed"):
            self.assertions.assert_signature_verification(
                signature_data=signature,
                public_key=public_bytes,
                content=modified_content,
                algorithm="ed25519"
            )
    
    def test_corrupted_signature_verification(self):
        """Test detection of corrupted signatures."""
        # Get valid key pair
        keys = self.test_keys["valid"]
        private_key = keys["private_key"]
        public_bytes = keys["public_bytes"]
        
        # Create test content and sign it
        test_content = b"Test SBOM content"
        signature = private_key.sign(test_content)
        
        # Corrupt the signature
        corrupted_signature = bytearray(signature)
        corrupted_signature[0] = (corrupted_signature[0] + 1) % 256  # Flip one bit
        
        with pytest.raises(AssertionError, match="signature verification failed"):
            self.assertions.assert_signature_verification(
                signature_data=bytes(corrupted_signature),
                public_key=public_bytes,
                content=test_content,
                algorithm="ed25519"
            )
    
    def test_wrong_public_key_verification(self):
        """Test detection of wrong public key usage."""
        # Get two different key pairs
        keys1 = self.test_keys["valid"]
        keys2 = self.test_keys["compromised"]
        
        private_key1 = keys1["private_key"]
        public_bytes2 = keys2["public_bytes"]  # Wrong public key
        
        # Sign with key1, verify with key2
        test_content = b"Test SBOM content"
        signature = private_key1.sign(test_content)
        
        with pytest.raises(AssertionError, match="signature verification failed"):
            self.assertions.assert_signature_verification(
                signature_data=signature,
                public_key=public_bytes2,
                content=test_content,
                algorithm="ed25519"
            )
    
    def test_invalid_public_key_format(self):
        """Test handling of invalid public key format."""
        # Get valid key pair
        keys = self.test_keys["valid"]
        private_key = keys["private_key"]
        
        # Create test content and sign it
        test_content = b"Test SBOM content"
        signature = private_key.sign(test_content)
        
        # Use invalid public key (wrong length)
        invalid_public_key = b"invalid_key_too_short"
        
        with pytest.raises(AssertionError, match="Invalid Ed25519 public key"):
            self.assertions.assert_signature_verification(
                signature_data=signature,
                public_key=invalid_public_key,
                content=test_content,
                algorithm="ed25519"
            )
    
    # ========================================================================
    # SBOM-SPECIFIC SIGNATURE TESTS
    # ========================================================================
    
    def test_sbom_content_signature(self):
        """Test signature verification for actual SBOM content."""
        # Generate realistic SBOM
        dependency_tree = self.generator.generate_realistic_dependency_tree(
            complexity="medium"
        )
        
        from ..core import create_sample_sbom
        sbom_content = create_sample_sbom(SBOMFormat.SPDX_JSON, dependency_tree)
        sbom_bytes = sbom_content.encode('utf-8')
        
        # Get valid key pair
        keys = self.test_keys["valid"]
        private_key = keys["private_key"]
        public_bytes = keys["public_bytes"]
        
        # Sign the SBOM content
        signature = private_key.sign(sbom_bytes)
        
        # Verify signature
        self.assertions.assert_signature_verification(
            signature_data=signature,
            public_key=public_bytes,
            content=sbom_bytes,
            algorithm="ed25519"
        )
    
    def test_sbom_hash_signature(self):
        """Test signature verification using SBOM content hash."""
        # Generate SBOM content
        dependency_tree = self.generator.generate_realistic_dependency_tree(
            complexity="large"
        )
        
        sbom_content = create_sample_sbom(SBOMFormat.CYCLONE_DX_JSON, dependency_tree)
        
        # Create hash of SBOM content
        sbom_hash = hashlib.sha256(sbom_content.encode('utf-8')).digest()
        
        # Get valid key pair
        keys = self.test_keys["valid"]
        private_key = keys["private_key"]
        public_bytes = keys["public_bytes"]
        
        # Sign the hash
        signature = private_key.sign(sbom_hash)
        
        # Verify signature
        self.assertions.assert_signature_verification(
            signature_data=signature,
            public_key=public_bytes,
            content=sbom_hash,
            algorithm="ed25519"
        )
    
    def test_multiple_sbom_signatures(self):
        """Test signature verification for multiple SBOM formats."""
        # Generate dependency tree
        dependency_tree = self.generator.generate_realistic_dependency_tree()
        
        # Generate multiple SBOM formats
        formats = self.generator.generate_sbom_formats_suite(dependency_tree)
        
        # Get valid key pair
        keys = self.test_keys["valid"]
        private_key = keys["private_key"]
        public_bytes = keys["public_bytes"]
        
        # Sign each format
        signatures = {}
        for format_type, content in formats.items():
            content_bytes = content.encode('utf-8')
            signature = private_key.sign(content_bytes)
            signatures[format_type] = signature
        
        # Verify all signatures
        for format_type, content in formats.items():
            content_bytes = content.encode('utf-8')
            signature = signatures[format_type]
            
            self.assertions.assert_signature_verification(
                signature_data=signature,
                public_key=public_bytes,
                content=content_bytes,
                algorithm="ed25519"
            )
    
    def test_sbom_signature_with_metadata(self):
        """Test signature verification including SBOM metadata."""
        # Generate SBOM with rich metadata
        dependency_tree = self.generator.generate_realistic_dependency_tree()
        sbom_content = create_sample_sbom(SBOMFormat.SPDX_JSON, dependency_tree)
        
        # Parse and add signature metadata
        sbom_data = json.loads(sbom_content)
        
        # Get valid key pair
        keys = self.test_keys["valid"]
        private_key = keys["private_key"]
        public_bytes = keys["public_bytes"]
        
        # Add signature metadata to SBOM
        signature_metadata = {
            "algorithm": "Ed25519",
            "keyId": "test-key-001",
            "timestamp": "2024-01-01T12:00:00Z",
            "signer": "SBOM-Test-Framework"
        }
        
        sbom_data["signatureInfo"] = signature_metadata
        
        # Create content to sign (SBOM without signature info)
        content_to_sign = json.dumps({
            k: v for k, v in sbom_data.items() 
            if k != "signatureInfo"
        }, sort_keys=True).encode('utf-8')
        
        # Sign the content
        signature = private_key.sign(content_to_sign)
        
        # Add signature to metadata
        sbom_data["signatureInfo"]["signature"] = base64.b64encode(signature).decode('ascii')
        sbom_data["signatureInfo"]["publicKey"] = base64.b64encode(public_bytes).decode('ascii')
        
        # Verify signature
        extracted_signature = base64.b64decode(sbom_data["signatureInfo"]["signature"])
        extracted_public_key = base64.b64decode(sbom_data["signatureInfo"]["publicKey"])
        
        self.assertions.assert_signature_verification(
            signature_data=extracted_signature,
            public_key=extracted_public_key,
            content=content_to_sign,
            algorithm="ed25519"
        )
    
    # ========================================================================
    # PERFORMANCE AND SCALABILITY TESTS
    # ========================================================================
    
    def test_signature_verification_performance(self):
        """Test signature verification performance."""
        # Generate large SBOM content
        dependency_tree = self.generator.generate_realistic_dependency_tree(
            complexity="enterprise"
        )
        
        sbom_content = create_sample_sbom(SBOMFormat.SPDX_JSON, dependency_tree)
        sbom_bytes = sbom_content.encode('utf-8')
        
        # Get valid key pair
        keys = self.test_keys["valid"]
        private_key = keys["private_key"]
        public_bytes = keys["public_bytes"]
        
        # Sign the content
        signature = private_key.sign(sbom_bytes)
        
        # Measure verification time
        import time
        start_time = time.perf_counter()
        
        # Verify signature
        self.assertions.assert_signature_verification(
            signature_data=signature,
            public_key=public_bytes,
            content=sbom_bytes,
            algorithm="ed25519"
        )
        
        verification_time = time.perf_counter() - start_time
        
        # Signature verification should be very fast (< 100ms)
        assert verification_time < 0.1, f"Signature verification too slow: {verification_time:.3f}s"
    
    def test_batch_signature_verification(self):
        """Test verification of multiple signatures in batch."""
        # Generate multiple SBOMs
        num_sboms = 50
        sboms = []
        signatures = []
        
        # Get valid key pair
        keys = self.test_keys["valid"]
        private_key = keys["private_key"]
        public_bytes = keys["public_bytes"]
        
        # Generate and sign multiple SBOMs
        for i in range(num_sboms):
            dependency_tree = self.generator.generate_realistic_dependency_tree(
                complexity="simple"
            )
            sbom_content = create_sample_sbom(SBOMFormat.SPDX_JSON, dependency_tree)
            sbom_bytes = sbom_content.encode('utf-8')
            
            signature = private_key.sign(sbom_bytes)
            
            sboms.append(sbom_bytes)
            signatures.append(signature)
        
        # Measure batch verification time
        start_time = time.perf_counter()
        
        # Verify all signatures
        for i in range(num_sboms):
            self.assertions.assert_signature_verification(
                signature_data=signatures[i],
                public_key=public_bytes,
                content=sboms[i],
                algorithm="ed25519"
            )
        
        total_time = time.perf_counter() - start_time
        avg_time = total_time / num_sboms
        
        # Average verification should be very fast
        assert avg_time < 0.01, f"Average signature verification too slow: {avg_time:.4f}s"
    
    # ========================================================================
    # SECURITY AND EDGE CASE TESTS
    # ========================================================================
    
    def test_signature_replay_attack_detection(self):
        """Test detection of signature replay attacks."""
        # Get valid key pair
        keys = self.test_keys["valid"]
        private_key = keys["private_key"]
        public_bytes = keys["public_bytes"]
        
        # Create original content and sign it
        original_content = b"Original SBOM v1.0"
        signature = private_key.sign(original_content)
        
        # Verify original signature works
        self.assertions.assert_signature_verification(
            signature_data=signature,
            public_key=public_bytes,
            content=original_content,
            algorithm="ed25519"
        )
        
        # Try to use same signature with different content (replay attack)
        malicious_content = b"Malicious SBOM v1.0"
        
        with pytest.raises(AssertionError, match="signature verification failed"):
            self.assertions.assert_signature_verification(
                signature_data=signature,
                public_key=public_bytes,
                content=malicious_content,
                algorithm="ed25519"
            )
    
    def test_signature_with_empty_content(self):
        """Test signature verification with empty content."""
        # Get valid key pair
        keys = self.test_keys["valid"]
        private_key = keys["private_key"]
        public_bytes = keys["public_bytes"]
        
        # Sign empty content
        empty_content = b""
        signature = private_key.sign(empty_content)
        
        # Verify empty content signature
        self.assertions.assert_signature_verification(
            signature_data=signature,
            public_key=public_bytes,
            content=empty_content,
            algorithm="ed25519"
        )
    
    def test_signature_with_large_content(self):
        """Test signature verification with very large content."""
        # Get valid key pair
        keys = self.test_keys["valid"]
        private_key = keys["private_key"]
        public_bytes = keys["public_bytes"]
        
        # Create large content (10MB)
        large_content = b"A" * (10 * 1024 * 1024)
        
        # Sign large content
        signature = private_key.sign(large_content)
        
        # Verify large content signature
        self.assertions.assert_signature_verification(
            signature_data=signature,
            public_key=public_bytes,
            content=large_content,
            algorithm="ed25519"
        )
    
    def test_signature_with_unicode_content(self):
        """Test signature verification with Unicode content."""
        # Get valid key pair
        keys = self.test_keys["valid"]
        private_key = keys["private_key"]
        public_bytes = keys["public_bytes"]
        
        # Create Unicode content
        unicode_content = "SBOM with Unicode: 🚀 中文 ñáéíóú çğşıöü"
        unicode_bytes = unicode_content.encode('utf-8')
        
        # Sign Unicode content
        signature = private_key.sign(unicode_bytes)
        
        # Verify Unicode content signature
        self.assertions.assert_signature_verification(
            signature_data=signature,
            public_key=public_bytes,
            content=unicode_bytes,
            algorithm="ed25519"
        )
    
    def test_unsupported_algorithm_handling(self):
        """Test handling of unsupported signature algorithms."""
        # Get valid key pair and content
        keys = self.test_keys["valid"]
        public_bytes = keys["public_bytes"]
        test_content = b"Test content"
        fake_signature = b"fake_signature"
        
        # Try to verify with unsupported algorithm
        with pytest.raises(AssertionError, match="Unsupported signature algorithm"):
            self.assertions.assert_signature_verification(
                signature_data=fake_signature,
                public_key=public_bytes,
                content=test_content,
                algorithm="rsa"  # Unsupported
            )
    
    def test_signature_key_rotation_scenario(self):
        """Test signature verification in key rotation scenarios."""
        # Get old and new key pairs
        old_keys = self.test_keys["valid"]
        new_keys = self.test_keys["expired"]  # Use as "new" keys
        
        test_content = b"SBOM content for key rotation test"
        
        # Sign with old key
        old_signature = old_keys["private_key"].sign(test_content)
        
        # Sign with new key
        new_signature = new_keys["private_key"].sign(test_content)
        
        # Verify old signature with old key (should work)
        self.assertions.assert_signature_verification(
            signature_data=old_signature,
            public_key=old_keys["public_bytes"],
            content=test_content,
            algorithm="ed25519"
        )
        
        # Verify new signature with new key (should work)
        self.assertions.assert_signature_verification(
            signature_data=new_signature,
            public_key=new_keys["public_bytes"],
            content=test_content,
            algorithm="ed25519"
        )
        
        # Verify old signature with new key (should fail)
        with pytest.raises(AssertionError, match="signature verification failed"):
            self.assertions.assert_signature_verification(
                signature_data=old_signature,
                public_key=new_keys["public_bytes"],
                content=test_content,
                algorithm="ed25519"
            )
    
    # ========================================================================
    # INTEGRATION TESTS
    # ========================================================================
    
    def test_end_to_end_sbom_signature_workflow(self):
        """Test complete SBOM signature workflow."""
        # 1. Generate SBOM
        dependency_tree = self.generator.generate_realistic_dependency_tree(
            complexity="medium"
        )
        
        sbom_content = create_sample_sbom(SBOMFormat.SPDX_JSON, dependency_tree)
        
        # 2. Parse SBOM and prepare for signing
        sbom_data = json.loads(sbom_content)
        
        # 3. Create canonical representation for signing
        canonical_content = json.dumps(sbom_data, sort_keys=True, separators=(',', ':')).encode('utf-8')
        
        # 4. Generate key pair
        keys = self.test_keys["valid"]
        private_key = keys["private_key"]
        public_bytes = keys["public_bytes"]
        
        # 5. Sign SBOM
        signature = private_key.sign(canonical_content)
        
        # 6. Add signature to SBOM
        sbom_data["signature"] = {
            "algorithm": "Ed25519",
            "signature": base64.b64encode(signature).decode('ascii'),
            "publicKey": base64.b64encode(public_bytes).decode('ascii'),
            "timestamp": "2024-01-01T12:00:00Z"
        }
        
        # 7. Serialize signed SBOM
        signed_sbom = json.dumps(sbom_data, indent=2)
        
        # 8. Verify signature from signed SBOM
        parsed_sbom = json.loads(signed_sbom)
        signature_info = parsed_sbom["signature"]
        
        # Extract signature components
        extracted_signature = base64.b64decode(signature_info["signature"])
        extracted_public_key = base64.b64decode(signature_info["publicKey"])
        
        # Remove signature for verification
        sbom_for_verification = {k: v for k, v in parsed_sbom.items() if k != "signature"}
        verification_content = json.dumps(sbom_for_verification, sort_keys=True, separators=(',', ':')).encode('utf-8')
        
        # 9. Verify signature
        self.assertions.assert_signature_verification(
            signature_data=extracted_signature,
            public_key=extracted_public_key,
            content=verification_content,
            algorithm="ed25519"
        )
        
        # 10. Ensure signed SBOM is still valid format
        from ..validators import SBOMValidator
        validator = SBOMValidator()
        
        # Remove signature for format validation
        validation_result = validator.validate(json.dumps(sbom_for_verification))
        self.assertions.assert_valid_sbom_format(validation_result)
    
    def teardown_method(self):
        """Clean up after tests."""
        super().cleanup_test_artifacts()
        
        # Clear sensitive key material
        self.test_keys.clear()