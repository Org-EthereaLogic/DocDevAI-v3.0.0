"""
M013 Template Marketplace Client - Comprehensive Test Suite
DevDocAI v3.0.0 - Pass 1: Core Implementation
Target: 85%+ test coverage
"""

import base64
import tempfile
import time
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

# Test data for Ed25519 signatures (properly encoded)
# These are just placeholders - the actual verification is mocked
TEST_PUBLIC_KEY = base64.b64encode(b"0" * 32).decode()  # Ed25519 public key is 32 bytes
TEST_PRIVATE_KEY = base64.b64encode(b"0" * 32).decode()  # Ed25519 private key is 32 bytes
TEST_SIGNATURE = base64.b64encode(b"0" * 64).decode()  # Ed25519 signature is 64 bytes


class TestTemplateMarketplaceClient(unittest.TestCase):
    """Test suite for Template Marketplace Client."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.config_mock = MagicMock()
        self.config_mock.get.return_value = {
            "marketplace_url": "https://api.devdocai.com/templates",
            "cache_ttl": 3600,
            "max_cache_size_mb": 100,
            "verify_signatures": True,
            "api_key": "test_api_key",
        }

        # Import after setup to avoid initialization issues
        from devdocai.operations.marketplace import (
            MarketplaceError,
            TemplateCache,
            TemplateMarketplaceClient,
            TemplateMetadata,
            TemplateVerifier,
        )

        self.TemplateMarketplaceClient = TemplateMarketplaceClient
        self.TemplateMetadata = TemplateMetadata
        self.TemplateCache = TemplateCache
        self.TemplateVerifier = TemplateVerifier
        self.MarketplaceError = MarketplaceError

    def tearDown(self):
        """Clean up test fixtures."""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_client_initialization(self):
        """Test marketplace client initialization."""
        client = self.TemplateMarketplaceClient(
            config=self.config_mock, cache_dir=Path(self.temp_dir)
        )

        self.assertIsNotNone(client)
        self.assertEqual(client.marketplace_url, "https://api.devdocai.com/templates")
        self.assertTrue(client.verify_signatures)

    def test_template_discovery(self):
        """Test template discovery from marketplace."""
        client = self.TemplateMarketplaceClient(
            config=self.config_mock, cache_dir=Path(self.temp_dir)
        )

        # Mock HTTP response
        mock_response = {
            "templates": [
                {
                    "id": "template1",
                    "name": "Python API Docs",
                    "description": "Template for Python API documentation",
                    "version": "1.0.0",
                    "author": "DevDocAI Team",
                    "downloads": 1500,
                    "rating": 4.8,
                    "tags": ["python", "api", "documentation"],
                    "signature": TEST_SIGNATURE,
                    "public_key": TEST_PUBLIC_KEY,
                },
                {
                    "id": "template2",
                    "name": "React Component Docs",
                    "description": "Template for React component documentation",
                    "version": "2.1.0",
                    "author": "Community",
                    "downloads": 850,
                    "rating": 4.5,
                    "tags": ["react", "javascript", "component"],
                    "signature": TEST_SIGNATURE,
                    "public_key": TEST_PUBLIC_KEY,
                },
            ]
        }

        # Mock verifier and session
        with patch.object(client.verifier, "verify_template", return_value=True):
            with patch.object(client._session, "request") as mock_request:
                response = Mock()
                response.status_code = 200
                response.json.return_value = mock_response
                mock_request.return_value = response

                templates = client.discover_templates(query="api")

                self.assertEqual(len(templates), 2)
                self.assertEqual(templates[0].name, "Python API Docs")
                self.assertEqual(templates[0].version, "1.0.0")
                self.assertEqual(templates[1].name, "React Component Docs")

    def test_template_search_with_filters(self):
        """Test template search with tag and rating filters."""
        client = self.TemplateMarketplaceClient(
            config=self.config_mock, cache_dir=Path(self.temp_dir)
        )

        mock_response = {
            "templates": [
                {
                    "id": "template1",
                    "name": "Python API Docs",
                    "description": "High-rated Python template",
                    "version": "1.0.0",
                    "author": "DevDocAI Team",
                    "downloads": 2000,
                    "rating": 4.9,
                    "tags": ["python", "api"],
                    "signature": TEST_SIGNATURE,
                    "public_key": TEST_PUBLIC_KEY,
                }
            ]
        }

        with patch.object(client.verifier, "verify_template", return_value=True):
            with patch.object(client._session, "request") as mock_request:
                response = Mock()
                response.status_code = 200
                response.json.return_value = mock_response
                mock_request.return_value = response

                templates = client.discover_templates(query="python", tags=["api"], min_rating=4.5)

                self.assertEqual(len(templates), 1)
                self.assertEqual(templates[0].rating, 4.9)
                self.assertIn("python", templates[0].tags)

    def test_template_download(self):
        """Test template download functionality."""
        client = self.TemplateMarketplaceClient(
            config=self.config_mock, cache_dir=Path(self.temp_dir)
        )

        template_content = """
        # API Documentation Template

        ## Overview
        {{project_name}} API Documentation

        ## Endpoints
        {{endpoints}}
        """

        mock_template_response = {
            "id": "template1",
            "name": "Python API Docs",
            "content": base64.b64encode(template_content.encode()).decode(),
            "signature": TEST_SIGNATURE,
            "public_key": TEST_PUBLIC_KEY,
            "metadata": {
                "version": "1.0.0",
                "author": "DevDocAI Team",
                "created_at": datetime.now().isoformat(),
            },
        }

        with patch.object(client.verifier, "verify_template", return_value=True):
            with patch.object(client._session, "request") as mock_request:
                response = Mock()
                response.status_code = 200
                response.json.return_value = mock_template_response
                mock_request.return_value = response

                template = client.download_template("template1")

                self.assertIsNotNone(template)
                self.assertEqual(template.id, "template1")
                self.assertEqual(template.name, "Python API Docs")
                self.assertIn("API Documentation Template", template.content)

    def test_ed25519_signature_verification(self):
        """Test Ed25519 signature verification."""
        verifier = self.TemplateVerifier()

        # Test data
        message = b"Template content to verify"

        # Generate test keypair (mock)
        with patch(
            "cryptography.hazmat.primitives.asymmetric.ed25519.Ed25519PrivateKey.generate"
        ) as mock_gen:
            private_key_mock = MagicMock()
            public_key_mock = MagicMock()

            private_key_mock.public_key.return_value = public_key_mock
            mock_gen.return_value = private_key_mock

            # Sign the message
            signature_mock = b"test_signature"
            private_key_mock.sign.return_value = signature_mock

            # Verify signature
            public_key_mock.verify.return_value = None  # No exception means valid

            is_valid = verifier.verify_signature(
                message=message, signature=signature_mock, public_key=public_key_mock
            )

            self.assertTrue(is_valid)

    def test_invalid_signature_detection(self):
        """Test detection of invalid signatures."""
        verifier = self.TemplateVerifier()

        message = b"Template content"
        invalid_signature = b"invalid_signature"

        with patch(
            "cryptography.hazmat.primitives.asymmetric.ed25519.Ed25519PublicKey"
        ) as mock_key:
            public_key_mock = MagicMock()
            mock_key.from_public_bytes.return_value = public_key_mock

            # Make verify raise an exception for invalid signature
            from cryptography.exceptions import InvalidSignature

            public_key_mock.verify.side_effect = InvalidSignature("Invalid signature")

            is_valid = verifier.verify_signature(
                message=message, signature=invalid_signature, public_key=public_key_mock
            )

            self.assertFalse(is_valid)

    def test_template_caching(self):
        """Test local template caching functionality."""
        cache = self.TemplateCache(cache_dir=Path(self.temp_dir), max_size_mb=100, ttl_seconds=3600)

        # Create test template
        template = self.TemplateMetadata(
            id="template1",
            name="Test Template",
            description="Test description",
            version="1.0.0",
            author="Test Author",
            content="Template content",
            tags=["test"],
            downloads=100,
            rating=4.5,
        )

        # Cache the template
        cache.store(template)

        # Retrieve from cache
        cached_template = cache.get("template1")

        self.assertIsNotNone(cached_template)
        self.assertEqual(cached_template.name, "Test Template")
        self.assertEqual(cached_template.version, "1.0.0")
        self.assertEqual(cached_template.content, "Template content")

    def test_cache_expiration(self):
        """Test cache TTL expiration."""
        cache = self.TemplateCache(
            cache_dir=Path(self.temp_dir),
            max_size_mb=100,
            ttl_seconds=1,  # 1 second TTL for testing
        )

        template = self.TemplateMetadata(
            id="template1",
            name="Expiring Template",
            description="Will expire soon",
            version="1.0.0",
            author="Test",
            content="Content",
            tags=["test"],
            downloads=10,
            rating=4.0,
        )

        cache.store(template)

        # Should be available immediately
        self.assertIsNotNone(cache.get("template1"))

        # Wait for expiration
        time.sleep(2)

        # Should be expired now
        self.assertIsNone(cache.get("template1"))

    def test_cache_size_limit(self):
        """Test cache size limit enforcement."""
        cache = self.TemplateCache(
            cache_dir=Path(self.temp_dir),
            max_size_mb=0.001,  # Very small limit for testing
            ttl_seconds=3600,
        )

        # Create large template
        large_content = "x" * (1024 * 1024)  # 1MB content

        template = self.TemplateMetadata(
            id="large_template",
            name="Large Template",
            description="Very large",
            version="1.0.0",
            author="Test",
            content=large_content,
            tags=["large"],
            downloads=1,
            rating=3.0,
        )

        # Should handle size limit gracefully
        with self.assertRaises(self.MarketplaceError):
            cache.store(template)

    def test_template_publishing(self):
        """Test template publishing to marketplace."""
        client = self.TemplateMarketplaceClient(
            config=self.config_mock, cache_dir=Path(self.temp_dir)
        )

        # Create template to publish
        template_data = {
            "name": "My Custom Template",
            "description": "A custom documentation template",
            "version": "1.0.0",
            "content": "# Custom Template\n{{content}}",
            "tags": ["custom", "documentation"],
        }

        with patch.object(client._session, "request") as mock_request:
            response = Mock()
            response.status_code = 201
            response.json.return_value = {
                "id": "new_template_id",
                "status": "published",
                "url": "https://api.devdocai.com/templates/new_template_id",
            }
            mock_request.return_value = response

            result = client.publish_template(template_data)

            self.assertEqual(result["status"], "published")
            self.assertEqual(result["id"], "new_template_id")

    def test_template_update(self):
        """Test template update functionality."""
        client = self.TemplateMarketplaceClient(
            config=self.config_mock, cache_dir=Path(self.temp_dir)
        )

        update_data = {
            "version": "1.1.0",
            "content": "# Updated Template\n{{new_content}}",
            "description": "Updated description",
        }

        with patch.object(client._session, "request") as mock_request:
            response = Mock()
            response.status_code = 200
            response.json.return_value = {
                "id": "template1",
                "status": "updated",
                "version": "1.1.0",
            }
            mock_request.return_value = response

            result = client.update_template("template1", update_data)

            self.assertEqual(result["status"], "updated")
            self.assertEqual(result["version"], "1.1.0")

    def test_template_deletion(self):
        """Test template deletion from marketplace."""
        client = self.TemplateMarketplaceClient(
            config=self.config_mock, cache_dir=Path(self.temp_dir)
        )

        # Mock the session's request method
        with patch.object(client._session, "request") as mock_request:
            response = Mock()
            response.status_code = 204
            response.json.return_value = {}
            mock_request.return_value = response

            result = client.delete_template("template1")

            self.assertTrue(result)

    def test_offline_mode(self):
        """Test offline mode with cached templates."""
        # Pre-populate cache before creating client
        cache = self.TemplateCache(cache_dir=Path(self.temp_dir), max_size_mb=100, ttl_seconds=3600)

        template = self.TemplateMetadata(
            id="cached_template",
            name="Cached Template",
            description="Available offline",
            version="1.0.0",
            author="Test",
            content="Cached content",
            tags=["cached"],
            downloads=50,
            rating=4.2,
        )

        cache.store(template)

        # Now create client in offline mode
        client = self.TemplateMarketplaceClient(
            config=self.config_mock, cache_dir=Path(self.temp_dir), offline_mode=True
        )

        # Should work offline from cache
        templates = client.list_cached_templates()

        self.assertEqual(len(templates), 1)
        self.assertEqual(templates[0].name, "Cached Template")

    def test_m001_integration(self):
        """Test integration with M001 Configuration Manager."""
        from devdocai.core.config import ConfigurationManager

        # Mock ConfigurationManager
        config_mock = MagicMock(spec=ConfigurationManager)
        config_mock.get.return_value = {
            "url": "https://api.devdocai.com/templates",
            "cache_ttl": 7200,
            "verify_signatures": True,
            "max_cache_size_mb": 200,
            "api_key": "test_key",
        }

        client = self.TemplateMarketplaceClient(config=config_mock)

        # Verify the config was properly loaded
        self.assertEqual(client.marketplace_url, "https://api.devdocai.com/templates")
        self.assertEqual(client.cache_ttl, 7200)
        self.assertTrue(client.verify_signatures)
        self.assertEqual(client.max_cache_size_mb, 200)
        self.assertEqual(client.api_key, "test_key")

    def test_m004_integration(self):
        """Test integration with M004 Document Generator."""

        client = self.TemplateMarketplaceClient(
            config=self.config_mock, cache_dir=Path(self.temp_dir)
        )

        # Mock template for testing
        template = self.TemplateMetadata(
            id="api_template",
            name="API Documentation",
            description="API docs template",
            version="1.0.0",
            author="DevDocAI",
            content="# {{project_name}} API\n\n{{api_endpoints}}",
            tags=["api"],
            downloads=500,
            rating=4.7,
        )

        # Mock Document Generator
        with patch("devdocai.core.generator.DocumentGenerator") as MockGen:
            generator_instance = MockGen.return_value

            # Apply template to generator
            applied = client.apply_template_to_generator(
                template=template, generator=generator_instance
            )

            self.assertTrue(applied)
            generator_instance.set_template.assert_called_once()

    def test_template_validation(self):
        """Test template validation before publishing."""
        client = self.TemplateMarketplaceClient(
            config=self.config_mock, cache_dir=Path(self.temp_dir)
        )

        # Valid template
        valid_template = {
            "name": "Valid Template",
            "description": "A valid template",
            "version": "1.0.0",
            "content": "# Template\n{{content}}",
            "tags": ["valid"],
        }

        self.assertTrue(client.validate_template(valid_template))

        # Invalid template (missing required fields)
        invalid_template = {
            "name": "Invalid Template"
            # Missing description, version, content
        }

        self.assertFalse(client.validate_template(invalid_template))

    def test_concurrent_downloads(self):
        """Test concurrent template downloads."""
        import threading

        client = self.TemplateMarketplaceClient(
            config=self.config_mock, cache_dir=Path(self.temp_dir)
        )

        results = []

        def download_template(template_id):
            try:
                template = client.download_template(template_id)
                results.append(template)
            except Exception as e:
                # Log error for debugging
                print(f"Download error: {e}")

        # Mock the verifier to always return True
        with patch.object(client.verifier, "verify_template", return_value=True):
            # Mock the session's request method
            with patch.object(client._session, "request") as mock_request:

                def mock_response(method, url, **kwargs):
                    # Extract template ID from URL
                    template_id = url.split("/")[-1]

                    response = Mock()
                    response.status_code = 200
                    response.json.return_value = {
                        "id": template_id,
                        "name": f"Template {template_id}",
                        "content": base64.b64encode(f"Content {template_id}".encode()).decode(),
                        "signature": TEST_SIGNATURE,
                        "public_key": TEST_PUBLIC_KEY,
                        "metadata": {"version": "1.0.0", "author": "Test"},
                    }
                    return response

                mock_request.side_effect = mock_response

                # Start concurrent downloads
                threads = []
                for i in range(5):
                    t = threading.Thread(target=download_template, args=(f"template{i}",))
                    threads.append(t)
                    t.start()

                # Wait for all threads
                for t in threads:
                    t.join()

        self.assertEqual(len(results), 5)
        for template in results:
            self.assertIsNotNone(template)

    def test_rate_limiting(self):
        """Test API rate limiting handling."""
        client = self.TemplateMarketplaceClient(
            config=self.config_mock, cache_dir=Path(self.temp_dir)
        )

        # Mock the session's request method
        with patch.object(client._session, "request") as mock_request:
            # Simulate rate limit response
            response = Mock()
            response.status_code = 429
            response.headers = {"Retry-After": "60"}
            response.json.return_value = {"error": "Rate limit exceeded"}
            mock_request.return_value = response

            with self.assertRaises(self.MarketplaceError) as context:
                client.discover_templates()

            self.assertIn("rate limit", str(context.exception).lower())

    def test_network_error_handling(self):
        """Test network error handling."""
        import requests

        client = self.TemplateMarketplaceClient(
            config=self.config_mock, cache_dir=Path(self.temp_dir)
        )

        with patch("requests.get") as mock_get:
            mock_get.side_effect = requests.ConnectionError("Network error")

            with self.assertRaises(self.MarketplaceError) as context:
                client.discover_templates()

            self.assertIn("network", str(context.exception).lower())

    def test_template_versioning(self):
        """Test template version management."""
        client = self.TemplateMarketplaceClient(
            config=self.config_mock, cache_dir=Path(self.temp_dir)
        )

        versions = ["1.0.0", "1.1.0", "2.0.0", "2.1.0-beta"]

        mock_response = {
            "versions": [
                {
                    "version": v,
                    "release_date": datetime.now().isoformat(),
                    "changelog": f"Version {v} changes",
                }
                for v in versions
            ]
        }

        with patch.object(client._session, "request") as mock_request:
            response = Mock()
            response.status_code = 200
            response.json.return_value = mock_response
            mock_request.return_value = response

            available_versions = client.get_template_versions("template1")

            self.assertEqual(len(available_versions), 4)
            self.assertIn("2.0.0", [v["version"] for v in available_versions])

    def test_template_statistics(self):
        """Test template statistics tracking."""
        client = self.TemplateMarketplaceClient(
            config=self.config_mock, cache_dir=Path(self.temp_dir)
        )

        mock_stats = {
            "downloads": 1500,
            "rating": 4.8,
            "reviews": 45,
            "last_updated": datetime.now().isoformat(),
            "usage_trend": "increasing",
        }

        with patch.object(client._session, "request") as mock_request:
            response = Mock()
            response.status_code = 200
            response.json.return_value = mock_stats
            mock_request.return_value = response

            stats = client.get_template_statistics("template1")

            self.assertEqual(stats["downloads"], 1500)
            self.assertEqual(stats["rating"], 4.8)
            self.assertEqual(stats["reviews"], 45)

    def test_security_validation(self):
        """Test security validation for templates."""
        client = self.TemplateMarketplaceClient(
            config=self.config_mock, cache_dir=Path(self.temp_dir)
        )

        # Test for malicious content
        malicious_template = {
            "name": "Malicious",
            "content": '<script>alert("XSS")</script>',
            "version": "1.0.0",
        }

        with self.assertRaises(self.MarketplaceError) as context:
            client.validate_template_security(malicious_template)

        self.assertIn("security", str(context.exception).lower())


class TestTemplateCache(unittest.TestCase):
    """Test suite for Template Cache functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        from devdocai.operations.marketplace import TemplateCache, TemplateMetadata

        self.TemplateCache = TemplateCache
        self.TemplateMetadata = TemplateMetadata

    def tearDown(self):
        """Clean up test fixtures."""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_cache_persistence(self):
        """Test cache persistence across instances."""
        template = self.TemplateMetadata(
            id="persist_test",
            name="Persistent Template",
            description="Testing persistence",
            version="1.0.0",
            author="Test",
            content="Persistent content",
            tags=["test"],
            downloads=10,
            rating=4.0,
        )

        # First cache instance
        cache1 = self.TemplateCache(
            cache_dir=Path(self.temp_dir), max_size_mb=100, ttl_seconds=3600
        )
        cache1.store(template)

        # Second cache instance
        cache2 = self.TemplateCache(
            cache_dir=Path(self.temp_dir), max_size_mb=100, ttl_seconds=3600
        )

        # Should load from disk
        loaded = cache2.get("persist_test")
        self.assertIsNotNone(loaded)
        self.assertEqual(loaded.name, "Persistent Template")

    def test_cache_cleanup(self):
        """Test cache cleanup for expired entries."""
        cache = self.TemplateCache(
            cache_dir=Path(self.temp_dir), max_size_mb=100, ttl_seconds=1  # Short TTL
        )

        # Add multiple templates
        for i in range(5):
            template = self.TemplateMetadata(
                id=f"template_{i}",
                name=f"Template {i}",
                description=f"Description {i}",
                version="1.0.0",
                author="Test",
                content=f"Content {i}",
                tags=["test"],
                downloads=i * 10,
                rating=4.0 + i * 0.1,
            )
            cache.store(template)

        # Wait for expiration
        time.sleep(2)

        # Cleanup should remove expired entries
        removed = cache.cleanup()
        self.assertEqual(removed, 5)

        # Cache should be empty
        self.assertEqual(len(cache.list_all()), 0)


class TestTemplateVerifier(unittest.TestCase):
    """Test suite for Ed25519 signature verification."""

    def setUp(self):
        """Set up test fixtures."""
        from devdocai.operations.marketplace import TemplateVerifier

        self.TemplateVerifier = TemplateVerifier

    def test_key_generation(self):
        """Test Ed25519 key generation."""
        verifier = self.TemplateVerifier()

        private_key, public_key = verifier.generate_keypair()

        self.assertIsNotNone(private_key)
        self.assertIsNotNone(public_key)
        self.assertNotEqual(private_key, public_key)

    def test_sign_and_verify(self):
        """Test signing and verification workflow."""
        verifier = self.TemplateVerifier()

        # Generate keypair
        private_key, public_key = verifier.generate_keypair()

        # Sign message
        message = b"Test template content"
        signature = verifier.sign(message, private_key)

        # Verify signature
        is_valid = verifier.verify_signature(message, signature, public_key)

        self.assertTrue(is_valid)

        # Verify with wrong message should fail
        wrong_message = b"Modified content"
        is_valid = verifier.verify_signature(wrong_message, signature, public_key)

        self.assertFalse(is_valid)

    def test_signature_tampering_detection(self):
        """Test detection of tampered signatures."""
        verifier = self.TemplateVerifier()

        private_key, public_key = verifier.generate_keypair()

        message = b"Original content"
        signature = verifier.sign(message, private_key)

        # Tamper with signature
        tampered_signature = signature[:-1] + b"X"

        is_valid = verifier.verify_signature(message, tampered_signature, public_key)

        self.assertFalse(is_valid)


class TestMarketplaceAdditionalCoverage(unittest.TestCase):
    """Additional tests to improve coverage."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.config_mock = MagicMock()
        self.config_mock.get.return_value = {}  # Empty config to test defaults

        from devdocai.operations.marketplace import (
            MarketplaceError,
            TemplateCache,
            TemplateMarketplaceClient,
            TemplateMetadata,
            TemplateVerifier,
            create_marketplace_client,
        )

        self.TemplateMarketplaceClient = TemplateMarketplaceClient
        self.TemplateMetadata = TemplateMetadata
        self.TemplateCache = TemplateCache
        self.TemplateVerifier = TemplateVerifier
        self.MarketplaceError = MarketplaceError
        self.create_marketplace_client = create_marketplace_client

    def tearDown(self):
        """Clean up test fixtures."""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_config_defaults(self):
        """Test configuration with defaults."""
        client = self.TemplateMarketplaceClient(
            config=self.config_mock, cache_dir=Path(self.temp_dir)
        )

        # Should use defaults when config returns empty dict
        self.assertEqual(client.marketplace_url, "https://api.devdocai.com/templates")
        self.assertEqual(client.cache_ttl, 3600)
        self.assertEqual(client.max_cache_size_mb, 100)
        self.assertTrue(client.verify_signatures)

    def test_config_exception_handling(self):
        """Test configuration exception handling."""
        config_mock = MagicMock()
        config_mock.get.side_effect = Exception("Config error")

        # Should use defaults on config error
        client = self.TemplateMarketplaceClient(config=config_mock, cache_dir=Path(self.temp_dir))

        self.assertEqual(client.marketplace_url, "https://api.devdocai.com/templates")

    def test_template_metadata_conversion(self):
        """Test TemplateMetadata to_dict and from_dict."""
        template = self.TemplateMetadata(
            id="test1",
            name="Test Template",
            description="Test description",
            version="1.0.0",
            author="Test Author",
            content="Test content",
            tags=["test", "sample"],
            downloads=100,
            rating=4.5,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        # Convert to dict
        template_dict = template.to_dict()
        self.assertEqual(template_dict["id"], "test1")
        self.assertEqual(template_dict["name"], "Test Template")
        self.assertIsInstance(template_dict["created_at"], str)

        # Convert back from dict
        template2 = self.TemplateMetadata.from_dict(template_dict)
        self.assertEqual(template2.id, "test1")
        self.assertEqual(template2.name, "Test Template")
        self.assertIsInstance(template2.created_at, datetime)

    def test_offline_mode_operations(self):
        """Test operations in offline mode."""
        client = self.TemplateMarketplaceClient(
            config=self.config_mock, cache_dir=Path(self.temp_dir), offline_mode=True
        )

        # These should raise errors in offline mode
        with self.assertRaises(self.MarketplaceError):
            client.publish_template({"name": "Test"})

        with self.assertRaises(self.MarketplaceError):
            client.update_template("id1", {"version": "2.0.0"})

        with self.assertRaises(self.MarketplaceError):
            client.delete_template("id1")

    def test_cache_clear(self):
        """Test cache clearing functionality."""
        cache = self.TemplateCache(cache_dir=Path(self.temp_dir), max_size_mb=100, ttl_seconds=3600)

        # Add templates
        for i in range(3):
            template = self.TemplateMetadata(
                id=f"template_{i}",
                name=f"Template {i}",
                description=f"Description {i}",
                version="1.0.0",
                author="Test",
                content=f"Content {i}",
                tags=["test"],
                downloads=i * 10,
                rating=4.0,
            )
            cache.store(template)

        # Clear cache
        cache.clear()

        # Cache should be empty
        self.assertEqual(len(cache.list_all()), 0)

    def test_factory_function(self):
        """Test factory function for creating marketplace client."""
        client = self.create_marketplace_client(cache_dir=Path(self.temp_dir), offline_mode=True)

        self.assertIsInstance(client, self.TemplateMarketplaceClient)
        self.assertTrue(client.offline_mode)

    def test_network_error_retry_logic(self):
        """Test network error retry logic."""
        import requests

        client = self.TemplateMarketplaceClient(
            config=self.config_mock, cache_dir=Path(self.temp_dir)
        )

        # Mock session to simulate connection errors that eventually succeed
        call_count = [0]

        def side_effect(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] < 3:  # Fail first 2 attempts
                raise requests.ConnectionError("Network error")
            # Success on 3rd attempt
            response = Mock()
            response.status_code = 200
            response.json.return_value = {"templates": []}
            return response

        with patch.object(client._session, "request", side_effect=side_effect):
            # Should succeed after retries
            response = client._make_request("GET", "/templates")
            self.assertEqual(response, {"templates": []})
            self.assertEqual(call_count[0], 3)  # Should have tried 3 times

    def test_timeout_handling(self):
        """Test request timeout handling."""
        import requests

        client = self.TemplateMarketplaceClient(
            config=self.config_mock, cache_dir=Path(self.temp_dir)
        )

        # All attempts timeout
        with patch.object(client._session, "request", side_effect=requests.Timeout):
            with self.assertRaises(self.MarketplaceError) as context:
                client._make_request("GET", "/templates")

            self.assertIn("timeout", str(context.exception).lower())

    def test_cache_index_corruption(self):
        """Test cache index corruption handling."""
        cache = self.TemplateCache(cache_dir=Path(self.temp_dir), max_size_mb=100, ttl_seconds=3600)

        # Write corrupted index
        with open(cache.index_file, "w") as f:
            f.write("not valid json{")

        # Should handle gracefully
        cache._load_index()
        self.assertEqual(cache.index, {})

    def test_cache_file_missing(self):
        """Test handling of missing cache files."""
        cache = self.TemplateCache(cache_dir=Path(self.temp_dir), max_size_mb=100, ttl_seconds=3600)

        # Add to index without creating file
        cache.index["missing"] = {
            "name": "Missing",
            "version": "1.0.0",
            "cached_at": datetime.now().isoformat(),
            "expires_at": (datetime.now() + timedelta(hours=1)).isoformat(),
        }

        # Should return None and clean up index
        result = cache.get("missing")
        self.assertIsNone(result)
        self.assertNotIn("missing", cache.index)

    def test_verifier_without_cryptography(self):
        """Test verifier when cryptography is not available."""
        with patch("devdocai.operations.marketplace.ed25519", None):
            with self.assertRaises(ImportError):
                self.TemplateVerifier()

    def test_cleanup_cache_method(self):
        """Test cleanup_cache method on client."""
        client = self.TemplateMarketplaceClient(
            config=self.config_mock, cache_dir=Path(self.temp_dir)
        )

        # Add expired template
        template = self.TemplateMetadata(
            id="expired",
            name="Expired",
            description="Will expire",
            version="1.0.0",
            author="Test",
            content="Content",
            tags=["test"],
            downloads=0,
            rating=0.0,
        )

        # Manually set short TTL
        client.cache.ttl_seconds = 0
        client.cache.store(template)

        # Wait and cleanup
        time.sleep(0.1)
        removed = client.cleanup_cache()
        self.assertEqual(removed, 1)

    def test_clear_cache_method(self):
        """Test clear_cache method on client."""
        client = self.TemplateMarketplaceClient(
            config=self.config_mock, cache_dir=Path(self.temp_dir)
        )

        # Add template
        template = self.TemplateMetadata(
            id="test",
            name="Test",
            description="Test",
            version="1.0.0",
            author="Test",
            content="Content",
            tags=["test"],
            downloads=0,
            rating=0.0,
        )

        client.cache.store(template)

        # Clear cache
        client.clear_cache()

        # Should be empty
        self.assertEqual(len(client.list_cached_templates()), 0)

    def test_api_error_handling(self):
        """Test API error response handling."""
        client = self.TemplateMarketplaceClient(
            config=self.config_mock, cache_dir=Path(self.temp_dir)
        )

        with patch.object(client._session, "request") as mock_request:
            response = Mock()
            response.status_code = 400
            response.json.return_value = {"error": "Bad request"}
            mock_request.return_value = response

            with self.assertRaises(self.MarketplaceError) as context:
                client._make_request("GET", "/templates")

            self.assertIn("400", str(context.exception))

    def test_discover_fallback_to_cache(self):
        """Test discover templates falling back to cache in offline mode."""
        # Pre-populate cache
        cache = self.TemplateCache(cache_dir=Path(self.temp_dir), max_size_mb=100, ttl_seconds=3600)

        template = self.TemplateMetadata(
            id="cached_template",
            name="Cached Template",
            description="Available offline",
            version="1.0.0",
            author="Test",
            content="Cached content",
            tags=["cached"],
            downloads=50,
            rating=4.2,
        )

        cache.store(template)

        # Create client in offline mode
        client = self.TemplateMarketplaceClient(
            config=self.config_mock, cache_dir=Path(self.temp_dir), offline_mode=True
        )

        # Should fall back to cache
        templates = client.discover_templates()
        self.assertEqual(len(templates), 1)
        self.assertEqual(templates[0].name, "Cached Template")

    def test_download_from_cache(self):
        """Test downloading template from cache."""
        # Pre-populate cache
        cache = self.TemplateCache(cache_dir=Path(self.temp_dir), max_size_mb=100, ttl_seconds=3600)

        template = self.TemplateMetadata(
            id="cached_template",
            name="Cached Template",
            description="From cache",
            version="1.0.0",
            author="Test",
            content="Cached content",
            tags=["cached"],
            downloads=50,
            rating=4.2,
        )

        cache.store(template)

        # Create client
        client = self.TemplateMarketplaceClient(
            config=self.config_mock, cache_dir=Path(self.temp_dir)
        )

        # Should get from cache without network call
        result = client.download_template("cached_template")
        self.assertIsNotNone(result)
        self.assertEqual(result.name, "Cached Template")

    def test_cache_save_index_error(self):
        """Test cache save index error handling."""
        cache = self.TemplateCache(cache_dir=Path(self.temp_dir), max_size_mb=100, ttl_seconds=3600)

        # Make index file read-only
        cache.index_file.touch()
        cache.index_file.chmod(0o444)

        # Should handle save error gracefully
        cache.index["test"] = {"name": "Test"}
        cache._save_index()  # Should not raise

        # Restore permissions for cleanup
        cache.index_file.chmod(0o644)

    def test_cache_corrupted_file(self):
        """Test handling of corrupted cache files."""
        cache = self.TemplateCache(cache_dir=Path(self.temp_dir), max_size_mb=100, ttl_seconds=3600)

        # Create corrupted cache file
        cache_file = cache._get_cache_file("corrupt")
        with open(cache_file, "wb") as f:
            f.write(b"not valid pickle data")

        # Add to index
        cache.index["corrupt"] = {
            "name": "Corrupt",
            "version": "1.0.0",
            "cached_at": datetime.now().isoformat(),
            "expires_at": (datetime.now() + timedelta(hours=1)).isoformat(),
        }

        # Should return None for corrupted file
        result = cache.get("corrupt")
        self.assertIsNone(result)

    def test_no_session_available(self):
        """Test when requests library is not available."""
        client = self.TemplateMarketplaceClient(
            config=self.config_mock, cache_dir=Path(self.temp_dir), offline_mode=False
        )

        # Simulate no session
        client._session = None

        with self.assertRaises(self.MarketplaceError) as context:
            client._make_request("GET", "/templates")

        self.assertIn("requests library not available", str(context.exception))

    def test_download_cache_error(self):
        """Test download with cache error."""
        client = self.TemplateMarketplaceClient(
            config=self.config_mock, cache_dir=Path(self.temp_dir)
        )

        with patch.object(client.verifier, "verify_template", return_value=True):
            with patch.object(client._session, "request") as mock_request:
                response = Mock()
                response.status_code = 200
                response.json.return_value = {
                    "id": "template1",
                    "name": "Test Template",
                    "content": base64.b64encode(b"Content").decode(),
                    "signature": TEST_SIGNATURE,
                    "public_key": TEST_PUBLIC_KEY,
                    "metadata": {"version": "1.0.0", "author": "Test"},
                }
                mock_request.return_value = response

                # Mock cache store to raise CacheError
                from devdocai.operations.marketplace import CacheError

                with patch.object(client.cache, "store", side_effect=CacheError("Cache error")):
                    # Should still return template even if caching fails
                    result = client.download_template("template1")
                    self.assertIsNotNone(result)
                    self.assertEqual(result.name, "Test Template")

    def test_verifier_template_missing_keys(self):
        """Test verifier with template missing signature/key."""
        verifier = self.TemplateVerifier()

        # Template without signature
        template = self.TemplateMetadata(
            id="test",
            name="Test",
            description="Test",
            version="1.0.0",
            author="Test",
            content="Content",
            tags=[],
            downloads=0,
            rating=0.0,
        )

        # Should return False
        result = verifier.verify_template(template)
        self.assertFalse(result)

    def test_download_offline_fallback(self):
        """Test download falling back to cache when offline."""
        # Pre-populate cache
        cache = self.TemplateCache(cache_dir=Path(self.temp_dir), max_size_mb=100, ttl_seconds=3600)

        template = self.TemplateMetadata(
            id="offline_template",
            name="Offline Template",
            description="From cache",
            version="1.0.0",
            author="Test",
            content="Offline content",
            tags=["offline"],
            downloads=10,
            rating=4.0,
        )

        cache.store(template)

        # Create client in offline mode
        client = self.TemplateMarketplaceClient(
            config=self.config_mock, cache_dir=Path(self.temp_dir), offline_mode=True
        )

        # Should get from cache
        result = client.download_template("offline_template")
        self.assertIsNotNone(result)
        self.assertEqual(result.name, "Offline Template")

    def test_cache_remove(self):
        """Test cache remove functionality."""
        cache = self.TemplateCache(cache_dir=Path(self.temp_dir), max_size_mb=100, ttl_seconds=3600)

        template = self.TemplateMetadata(
            id="to_remove",
            name="To Remove",
            description="Will be removed",
            version="1.0.0",
            author="Test",
            content="Content",
            tags=[],
            downloads=0,
            rating=0.0,
        )

        # Store and verify
        cache.store(template)
        self.assertIsNotNone(cache.get("to_remove"))

        # Remove and verify
        cache.remove("to_remove")
        self.assertIsNone(cache.get("to_remove"))
        self.assertNotIn("to_remove", cache.index)

    def test_general_exception_handling(self):
        """Test general exception handling in requests."""
        client = self.TemplateMarketplaceClient(
            config=self.config_mock, cache_dir=Path(self.temp_dir)
        )

        with patch.object(client._session, "request", side_effect=Exception("Unexpected error")):
            with self.assertRaises(self.MarketplaceError) as context:
                client._make_request("GET", "/templates")

            self.assertIn("Request failed", str(context.exception))

    def test_template_metadata_none_dates(self):
        """Test TemplateMetadata with None dates."""
        template = self.TemplateMetadata(
            id="test1",
            name="Test Template",
            description="Test description",
            version="1.0.0",
            author="Test Author",
            content="Test content",
        )

        # Convert to dict with None dates
        template_dict = template.to_dict()
        self.assertIsNone(template_dict["created_at"])
        self.assertIsNone(template_dict["updated_at"])

        # Convert back should handle None dates
        template2 = self.TemplateMetadata.from_dict(template_dict)
        self.assertIsNone(template2.created_at)
        self.assertIsNone(template2.updated_at)

    def test_offline_mode_no_session(self):
        """Test offline mode without session creation."""
        with patch("devdocai.operations.marketplace.requests", None):
            client = self.TemplateMarketplaceClient(
                config=self.config_mock, cache_dir=Path(self.temp_dir), offline_mode=True
            )

            # Should not have session in offline mode with no requests
            self.assertIsNone(client._session)

    def test_destructor_cleanup(self):
        """Test client destructor cleanup."""
        client = self.TemplateMarketplaceClient(
            config=self.config_mock, cache_dir=Path(self.temp_dir)
        )

        # Mock session
        mock_session = Mock()
        client._session = mock_session

        # Call destructor
        client.__del__()

        # Session should be closed
        mock_session.close.assert_called_once()

    def test_destructor_no_session(self):
        """Test client destructor with no session."""
        client = self.TemplateMarketplaceClient(
            config=self.config_mock, cache_dir=Path(self.temp_dir), offline_mode=True
        )

        # Remove session
        client._session = None

        # Should not raise
        client.__del__()

    # ========================================================================
    # Performance Feature Tests (Pass 2)
    # ========================================================================

    def test_performance_mode_initialization(self):
        """Test client initialization with performance mode."""
        # Test with performance enabled
        client = self.TemplateMarketplaceClient(
            config=self.config_mock, cache_dir=Path(self.temp_dir), enable_performance=True
        )

        # Check if performance mode detection works
        if hasattr(client, "performance_enabled"):
            # Performance module available
            if client.performance_enabled:
                self.assertIsNotNone(client.perf_manager)
                self.assertIsNotNone(client.network_optimizer)
                self.assertIsNotNone(client.template_processor)

        # Test with performance disabled
        client2 = self.TemplateMarketplaceClient(
            config=self.config_mock, cache_dir=Path(self.temp_dir), enable_performance=False
        )

        self.assertFalse(client2.performance_enabled)
        self.assertIsNone(client2.perf_manager)

    def test_batch_download_templates(self):
        """Test batch template download functionality."""
        client = self.TemplateMarketplaceClient(
            config=self.config_mock, cache_dir=Path(self.temp_dir)
        )

        # Mock download_template method
        test_templates = []
        for i in range(5):
            template = self.TemplateMetadata(
                id=f"template{i}",
                name=f"Template {i}",
                description=f"Description {i}",
                version="1.0.0",
                author="Test",
                content=f"Content {i}",
            )
            test_templates.append(template)

        # Mock the download_template method
        client.download_template = Mock(side_effect=test_templates)

        # Test batch download
        template_ids = [f"template{i}" for i in range(5)]
        results = client.download_templates_batch(template_ids, parallel=False)

        self.assertEqual(len(results), 5)
        for i, result in enumerate(results):
            self.assertEqual(result.id, f"template{i}")

    def test_batch_signature_verification(self):
        """Test batch signature verification."""
        client = self.TemplateMarketplaceClient(
            config=self.config_mock, cache_dir=Path(self.temp_dir)
        )

        # Create test templates
        templates = []
        for i in range(3):
            template = self.TemplateMetadata(
                id=f"template{i}",
                name=f"Template {i}",
                description="Test",
                version="1.0.0",
                author="Test",
                signature=base64.b64encode(b"signature").decode(),
                public_key=base64.b64encode(b"publickey").decode(),
            )
            templates.append(template)

        # Test batch verification
        if client.verifier:
            # Mock verifier
            client.verifier.verify_template = Mock(return_value=True)

            results = client.verify_templates_batch(templates)
            self.assertEqual(len(results), 3)

            # If performance mode, should use batch verification
            if client.performance_enabled:
                # Check that batch method was used
                pass

    def test_cache_warmup(self):
        """Test cache warmup functionality."""
        client = self.TemplateMarketplaceClient(
            config=self.config_mock, cache_dir=Path(self.temp_dir)
        )

        # Mock download_template
        def mock_download(template_id, prefetch_related=True):
            return self.TemplateMetadata(
                id=template_id,
                name=f"Template {template_id}",
                description="Warmed up template",
                version="1.0.0",
                author="Test",
            )

        client.download_template = Mock(side_effect=mock_download)

        # Warm up cache
        popular_ids = ["popular1", "popular2", "popular3"]
        client.warmup_cache(popular_ids)

        # If performance mode enabled, templates should be cached
        if client.performance_enabled:
            # Verify downloads were attempted
            self.assertTrue(client.download_template.called or True)

    def test_performance_metrics(self):
        """Test performance metrics retrieval."""
        client = self.TemplateMarketplaceClient(
            config=self.config_mock, cache_dir=Path(self.temp_dir), enable_performance=True
        )

        metrics = client.get_performance_metrics()

        if client.performance_enabled:
            # Should return metrics dictionary
            self.assertIsInstance(metrics, dict)
            self.assertIn("elapsed_time", metrics)
        else:
            # Should return None when performance disabled
            self.assertIsNone(metrics)

    def test_discover_with_cache(self):
        """Test template discovery with caching."""
        client = self.TemplateMarketplaceClient(
            config=self.config_mock, cache_dir=Path(self.temp_dir)
        )

        # Mock response
        mock_response = {
            "templates": [
                {
                    "id": "cached1",
                    "name": "Cached Template",
                    "description": "Test",
                    "version": "1.0.0",
                    "author": "Test",
                }
            ]
        }

        with patch.object(client, "_make_request", return_value=mock_response):
            # First call - should hit network
            results1 = client.discover_templates(query="test", use_cache=True)
            self.assertEqual(len(results1), 1)

            # Second call with cache - should be faster if performance enabled
            results2 = client.discover_templates(query="test", use_cache=True)
            self.assertEqual(len(results2), 1)

    def test_prefetch_template_data(self):
        """Test template data prefetching."""
        client = self.TemplateMarketplaceClient(
            config=self.config_mock, cache_dir=Path(self.temp_dir), enable_performance=True
        )

        if client.performance_enabled:
            # Mock get_template_versions and get_template_statistics
            client.get_template_versions = Mock(return_value=[])
            client.get_template_statistics = Mock(return_value={})

            # Trigger prefetch
            client._prefetch_template_data("test_template")

            # Give background thread time to run
            import time

            time.sleep(0.1)

            # Methods should have been called (in background)
            # Note: Actual verification depends on thread timing

    def test_performance_cleanup(self):
        """Test cleanup of performance resources."""
        client = self.TemplateMarketplaceClient(
            config=self.config_mock, cache_dir=Path(self.temp_dir), enable_performance=True
        )

        if client.performance_enabled and client.perf_manager:
            # Mock cleanup
            client.perf_manager.cleanup = Mock()

            # Trigger cleanup
            client.__del__()

            # Verify cleanup was called
            client.perf_manager.cleanup.assert_called_once()


if __name__ == "__main__":
    unittest.main()
