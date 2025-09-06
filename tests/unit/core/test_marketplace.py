#!/usr/bin/env python3
"""
Unit tests for M013 - Template Marketplace Client.
Tests all core functionality including browsing, downloading, publishing,
signature verification, and caching.
"""

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

# Import the marketplace modules
from devdocai.marketplace import (
    TemplateMarketplaceClient,
    Ed25519Verifier,
    TemplateCache,
    CertificateManager,
    MarketplaceAPIClient,
    TemplatePublisher
)


class TestTemplateMarketplaceClient(unittest.TestCase):
    """Test the main TemplateMarketplaceClient class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.client = TemplateMarketplaceClient(
            marketplace_url="https://test.marketplace.devdocai.org",
            cache_dir=Path(self.temp_dir),
            offline_mode=True
        )
    
    def tearDown(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_initialization(self):
        """Test client initialization."""
        self.assertEqual(self.client.marketplace_url, "https://test.marketplace.devdocai.org")
        self.assertTrue(self.client.offline_mode)
        self.assertIsNotNone(self.client.api_client)
        self.assertIsNotNone(self.client.local_cache)
        self.assertIsNotNone(self.client.signature_verifier)
        self.assertIsNotNone(self.client.certificate_manager)
        self.assertIsNotNone(self.client.publisher)
    
    def test_browse_templates_offline(self):
        """Test browsing templates in offline mode."""
        result = self.client.browse_templates(category="api")
        
        self.assertIn("templates", result)
        self.assertIn("pagination", result)
        self.assertTrue(result.get("cached", False))
    
    def test_search_templates(self):
        """Test searching for templates."""
        result = self.client.search_templates("documentation")
        
        self.assertIn("templates", result)
        self.assertIn("pagination", result)
    
    def test_download_template_offline(self):
        """Test downloading template in offline mode."""
        # Should return empty in offline mode with no cache
        template_data, verified = self.client.download_template("test-template-id")
        
        self.assertIsInstance(template_data, dict)
        self.assertIsInstance(verified, bool)
    
    def test_publish_template_offline(self):
        """Test publishing template in offline mode."""
        template = {
            "name": "Test Template",
            "version": "1.0.0",
            "description": "A test template for unit testing",
            "category": "documentation",
            "content": {"template_text": "# Test\n\nThis is a test template."}
        }
        
        success, result = self.client.publish_template(template)
        
        # Should fail in offline mode
        self.assertFalse(success)
        self.assertEqual(result, "Offline mode enabled")
    
    def test_get_stats(self):
        """Test getting client statistics."""
        stats = self.client.get_stats()
        
        self.assertIn("templates_browsed", stats)
        self.assertIn("templates_downloaded", stats)
        self.assertIn("templates_published", stats)
        self.assertIn("cache_info", stats)
        self.assertIn("offline_mode", stats)
    
    def test_validate_template_structure(self):
        """Test template structure validation."""
        # Valid template
        valid_template = {
            "name": "Valid Template",
            "version": "1.0.0",
            "description": "A valid template for testing",
            "category": "api",
            "content": {"template_text": "# Template Content"}
        }
        self.assertTrue(self.client._validate_template_structure(valid_template))
        
        # Invalid template (missing required field)
        invalid_template = {
            "name": "Invalid Template",
            "version": "1.0.0"
            # Missing description, category, content
        }
        self.assertFalse(self.client._validate_template_structure(invalid_template))
    
    def test_semver_validation(self):
        """Test semantic version validation."""
        self.assertTrue(self.client._is_valid_semver("1.0.0"))
        self.assertTrue(self.client._is_valid_semver("2.1.3"))
        self.assertTrue(self.client._is_valid_semver("1.0.0-alpha"))
        self.assertTrue(self.client._is_valid_semver("1.0.0-beta+build"))
        
        self.assertFalse(self.client._is_valid_semver("1.0"))
        self.assertFalse(self.client._is_valid_semver("v1.0.0"))
        self.assertFalse(self.client._is_valid_semver("1.0.0.0"))


class TestEd25519Verifier(unittest.TestCase):
    """Test the Ed25519 signature verifier."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.verifier = Ed25519Verifier()
    
    def test_demo_mode(self):
        """Test demo mode functionality."""
        content = b"Test content for signing"
        signature = "demo_sig_test"
        public_key = "demo_public_key"
        
        # Demo signatures should verify
        result = self.verifier.verify(content, signature, public_key)
        self.assertTrue(result)
    
    def test_generate_keypair(self):
        """Test keypair generation."""
        private_key, public_key = self.verifier.generate_keypair()
        
        self.assertIsNotNone(private_key)
        self.assertIsNotNone(public_key)
        self.assertNotEqual(private_key, public_key)
    
    def test_sign_and_verify(self):
        """Test signing and verification in demo mode."""
        content = b"Test content"
        private_key, public_key = self.verifier.generate_keypair()
        
        signature = self.verifier.sign(content, private_key)
        self.assertIsNotNone(signature)
        
        # In demo mode, verification should work
        if self.verifier.demo_mode:
            result = self.verifier.verify(content, signature, public_key)
            self.assertTrue(result)
    
    def test_get_stats(self):
        """Test getting verifier statistics."""
        stats = self.verifier.get_stats()
        
        self.assertIn("verified_count", stats)
        self.assertIn("failed_count", stats)
        self.assertIn("total_verifications", stats)
        self.assertIn("success_rate", stats)
        self.assertIn("demo_mode", stats)


class TestTemplateCache(unittest.TestCase):
    """Test the template cache manager."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.cache = TemplateCache(cache_dir=Path(self.temp_dir))
    
    def tearDown(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_save_and_get_template(self):
        """Test saving and retrieving templates from cache."""
        template_id = "test-template-123"
        template_data = {
            "name": "Test Template",
            "version": "1.0.0",
            "content": "Template content"
        }
        
        # Save template
        success = self.cache.save_template(template_id, template_data)
        self.assertTrue(success)
        
        # Retrieve template
        retrieved = self.cache.get_template(template_id)
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved["name"], "Test Template")
    
    def test_cache_metadata(self):
        """Test caching template metadata."""
        metadata = {
            "id": "test-meta-123",
            "name": "Test Metadata",
            "category": "api"
        }
        
        success = self.cache.cache_template_metadata(metadata)
        self.assertTrue(success)
        
        retrieved = self.cache.get_template_metadata("test-meta-123")
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved["name"], "Test Metadata")
    
    def test_browse_cached_templates(self):
        """Test browsing cached templates."""
        # Add some metadata
        for i in range(3):
            metadata = {
                "id": f"template-{i}",
                "name": f"Template {i}",
                "category": "documentation",
                "version": f"1.0.{i}"
            }
            self.cache.cache_template_metadata(metadata)
        
        # Browse cached templates
        result = self.cache.browse_cached_templates()
        
        self.assertIn("templates", result)
        self.assertIn("pagination", result)
        self.assertTrue(result["cached"])
    
    def test_clear_cache(self):
        """Test clearing the cache."""
        # Add a template
        self.cache.save_template("test-id", {"name": "Test"})
        
        # Clear cache
        success = self.cache.clear()
        self.assertTrue(success)
        
        # Verify cache is empty
        self.assertEqual(len(self.cache), 0)
    
    def test_cache_info(self):
        """Test getting cache information."""
        info = self.cache.get_cache_info()
        
        self.assertIn("location", info)
        self.assertIn("template_count", info)
        self.assertIn("size_mb", info)
        self.assertIn("cache_hits", info)
        self.assertIn("hit_rate", info)


class TestCertificateManager(unittest.TestCase):
    """Test the certificate manager."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.cert_manager = CertificateManager()
    
    def test_check_certificate(self):
        """Test certificate validation."""
        # Valid certificate (demo)
        result = self.cert_manager.check_certificate("devdocai-cert-123")
        self.assertTrue(result)
        
        # Revoked certificate
        result = self.cert_manager.check_certificate("compromised-cert-001")
        self.assertFalse(result)
    
    def test_add_to_revocation_list(self):
        """Test adding certificate to revocation list."""
        cert_id = "bad-cert-456"
        
        success = self.cert_manager.add_to_revocation_list(cert_id, "Compromised")
        self.assertTrue(success)
        
        # Verify it's revoked
        self.assertTrue(self.cert_manager.is_revoked(cert_id))
    
    def test_trusted_roots(self):
        """Test trusted root certificate management."""
        # Get existing trusted roots
        roots = self.cert_manager.get_trusted_roots()
        self.assertIsInstance(roots, list)
        self.assertTrue(len(roots) > 0)
        
        # Add new trusted root
        success = self.cert_manager.add_trusted_root("new-root-ca-2024")
        self.assertTrue(success)
        
        # Verify it was added
        updated_roots = self.cert_manager.get_trusted_roots()
        self.assertIn("new-root-ca-2024", updated_roots)
    
    def test_get_stats(self):
        """Test getting certificate manager statistics."""
        stats = self.cert_manager.get_stats()
        
        self.assertIn("checks_performed", stats)
        self.assertIn("revoked_found", stats)
        self.assertIn("valid_found", stats)
        self.assertIn("revoked_count", stats)
        self.assertIn("trusted_roots", stats)


class TestMarketplaceAPIClient(unittest.TestCase):
    """Test the marketplace API client."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.api_client = MarketplaceAPIClient(
            base_url="https://test.marketplace.devdocai.org",
            offline_mode=True
        )
    
    def test_browse_templates_demo(self):
        """Test browsing templates in demo mode."""
        result = self.api_client.browse_templates(category="api")
        
        self.assertIn("templates", result)
        self.assertIn("pagination", result)
        self.assertIsInstance(result["templates"], list)
    
    def test_download_template_demo(self):
        """Test downloading template in demo mode."""
        result = self.api_client.download_template("api-docs-v1.0")
        
        if not result.get("error"):
            self.assertIn("content", result)
            self.assertIn("signature", result)
    
    def test_get_stats(self):
        """Test getting API client statistics."""
        stats = self.api_client.get_stats()
        
        self.assertIn("request_count", stats)
        self.assertIn("error_count", stats)
        self.assertIn("error_rate", stats)
        self.assertIn("offline_mode", stats)


class TestTemplatePublisher(unittest.TestCase):
    """Test the template publisher."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.api_client = MagicMock()
        self.signature_verifier = Ed25519Verifier()
        self.publisher = TemplatePublisher(self.api_client, self.signature_verifier)
    
    def test_validate_template(self):
        """Test template validation."""
        # Valid template
        valid_template = {
            "name": "Test Template",
            "version": "1.0.0",
            "description": "This is a test template for validation",
            "category": "documentation",
            "content": {"template_text": "# Template\n\nContent goes here"}
        }
        
        result = self.publisher._validate_template(valid_template)
        self.assertTrue(result[0])
        self.assertEqual(result[1], "Valid")
        
        # Invalid template (missing fields)
        invalid_template = {"name": "Bad"}
        result = self.publisher._validate_template(invalid_template)
        self.assertFalse(result[0])
    
    def test_add_metadata(self):
        """Test adding metadata to template."""
        template = {
            "name": "Test",
            "category": "api"
        }
        
        enhanced = self.publisher._add_metadata(template)
        
        self.assertIn("created_at", enhanced)
        self.assertIn("updated_at", enhanced)
        self.assertIn("author", enhanced)
        self.assertIn("tags", enhanced)
        self.assertIn("schema_version", enhanced)
    
    def test_is_valid_semver(self):
        """Test semantic version validation."""
        self.assertTrue(self.publisher._is_valid_semver("1.0.0"))
        self.assertTrue(self.publisher._is_valid_semver("2.1.3-alpha"))
        self.assertTrue(self.publisher._is_valid_semver("1.0.0+build123"))
        
        self.assertFalse(self.publisher._is_valid_semver("1.0"))
        self.assertFalse(self.publisher._is_valid_semver("v1.0.0"))


def run_tests():
    """Run all tests and return results."""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add all test classes
    suite.addTests(loader.loadTestsFromTestCase(TestTemplateMarketplaceClient))
    suite.addTests(loader.loadTestsFromTestCase(TestEd25519Verifier))
    suite.addTests(loader.loadTestsFromTestCase(TestTemplateCache))
    suite.addTests(loader.loadTestsFromTestCase(TestCertificateManager))
    suite.addTests(loader.loadTestsFromTestCase(TestMarketplaceAPIClient))
    suite.addTests(loader.loadTestsFromTestCase(TestTemplatePublisher))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result


if __name__ == "__main__":
    result = run_tests()
    
    # Print summary
    print("\n" + "=" * 60)
    print("M013 Template Marketplace Client - Test Summary")
    print("=" * 60)
    print(f"Tests Run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print(f"Success Rate: {((result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun * 100):.1f}%")
    
    # Exit with appropriate code
    exit(0 if result.wasSuccessful() else 1)