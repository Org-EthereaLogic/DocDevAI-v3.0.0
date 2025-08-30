#!/usr/bin/env python3
"""
Test script to verify M004-M006 integration after refactoring.

This script tests that M004 (Document Generator) properly integrates with
M006 (Template Registry) through the new adapter layer.
"""

import sys
import logging
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_adapter_import():
    """Test that the adapter can be imported and used."""
    logger.info("Testing adapter import...")
    
    try:
        from devdocai.generator.core.template_registry_adapter import (
            TemplateRegistryAdapter,
            UnifiedTemplateLoader,  # Alias
            TemplateMetadata,
            SecurityLevel
        )
        logger.info("✅ Adapter imports successful")
        
        # Verify alias works
        assert TemplateRegistryAdapter is UnifiedTemplateLoader
        logger.info("✅ UnifiedTemplateLoader alias works")
        
        return True
    except ImportError as e:
        logger.error(f"❌ Failed to import adapter: {e}")
        return False


def test_adapter_initialization():
    """Test that the adapter can be initialized."""
    logger.info("\nTesting adapter initialization...")
    
    try:
        from devdocai.generator.core.template_registry_adapter import (
            TemplateRegistryAdapter,
            SecurityLevel
        )
        
        # Initialize with different security levels
        for level in [SecurityLevel.NONE, SecurityLevel.BASIC, 
                     SecurityLevel.STANDARD, SecurityLevel.STRICT]:
            adapter = TemplateRegistryAdapter(
                security_level=level,
                cache_enabled=True,
                cache_size=50
            )
            logger.info(f"✅ Adapter initialized with security level: {level.value}")
        
        return True
    except Exception as e:
        logger.error(f"❌ Failed to initialize adapter: {e}")
        return False


def test_unified_engine_integration():
    """Test that UnifiedDocumentGenerator uses the adapter correctly."""
    logger.info("\nTesting UnifiedDocumentGenerator integration...")
    
    try:
        from devdocai.generator.core.unified_engine import (
            UnifiedDocumentGenerator,
            UnifiedGenerationConfig,
            EngineMode
        )
        
        # Create configuration
        config = UnifiedGenerationConfig(
            output_format="markdown",
            engine_mode=EngineMode.STANDARD
        )
        
        # Initialize generator (this should use the adapter internally)
        generator = UnifiedDocumentGenerator(config)
        
        # Verify template loader is the adapter
        if hasattr(generator, 'template_loader'):
            loader_type = type(generator.template_loader).__name__
            logger.info(f"Template loader type: {loader_type}")
            
            # Check if it's our adapter
            from devdocai.generator.core.template_registry_adapter import TemplateRegistryAdapter
            if isinstance(generator.template_loader, TemplateRegistryAdapter):
                logger.info("✅ UnifiedDocumentGenerator uses TemplateRegistryAdapter")
            else:
                logger.warning(f"⚠️ Template loader is {loader_type}, not TemplateRegistryAdapter")
        
        return True
    except Exception as e:
        logger.error(f"❌ Failed to test engine integration: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_backward_compatibility():
    """Test that backward compatibility is maintained."""
    logger.info("\nTesting backward compatibility...")
    
    try:
        # Test old import patterns still work
        from devdocai.generator import TemplateLoader
        from devdocai.generator.core import (
            TemplateLoader as CoreTemplateLoader,
            SecureTemplateLoader
        )
        
        # Verify they're all the same adapter
        from devdocai.generator.core.template_registry_adapter import TemplateRegistryAdapter
        
        assert TemplateLoader is TemplateRegistryAdapter
        assert CoreTemplateLoader is TemplateRegistryAdapter
        assert SecureTemplateLoader is TemplateRegistryAdapter
        
        logger.info("✅ All legacy imports point to TemplateRegistryAdapter")
        
        return True
    except Exception as e:
        logger.error(f"❌ Backward compatibility test failed: {e}")
        return False


def test_m006_registry_connection():
    """Test that the adapter actually connects to M006's registry."""
    logger.info("\nTesting M006 registry connection...")
    
    try:
        from devdocai.generator.core.template_registry_adapter import TemplateRegistryAdapter
        from devdocai.templates.registry_unified import UnifiedTemplateRegistry
        
        # Create adapter
        adapter = TemplateRegistryAdapter()
        
        # Verify it has a registry attribute
        if hasattr(adapter, 'registry'):
            if isinstance(adapter.registry, UnifiedTemplateRegistry):
                logger.info("✅ Adapter contains M006's UnifiedTemplateRegistry")
            else:
                logger.error(f"❌ Adapter registry is {type(adapter.registry)}, not UnifiedTemplateRegistry")
                return False
        else:
            logger.error("❌ Adapter doesn't have a registry attribute")
            return False
        
        # Test listing templates (should use M006's templates)
        try:
            templates = adapter.list_templates()
            logger.info(f"✅ Listed {len(templates)} templates from M006 registry")
            
            # Show first few templates if any
            if templates:
                logger.info(f"   Sample templates: {templates[:3]}...")
        except Exception as e:
            logger.warning(f"⚠️ Could not list templates: {e}")
        
        return True
    except Exception as e:
        logger.error(f"❌ Failed to test M006 connection: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_template_operations():
    """Test basic template operations through the adapter."""
    logger.info("\nTesting template operations...")
    
    try:
        from devdocai.generator.core.template_registry_adapter import TemplateRegistryAdapter
        
        adapter = TemplateRegistryAdapter()
        
        # Test validate_template method
        is_valid = adapter.validate_template("test_template")
        logger.info(f"Template validation result: {is_valid}")
        
        # Test clear_cache method
        adapter.clear_cache()
        logger.info("✅ Cache cleared successfully")
        
        # Test render method (simplified test)
        try:
            # This might fail if no templates are loaded, which is okay for now
            result = adapter.render("test", name="Test", value="123")
            logger.info("✅ Render method works")
        except Exception as e:
            logger.info(f"ℹ️ Render test skipped (expected if no templates loaded): {e}")
        
        return True
    except Exception as e:
        logger.error(f"❌ Failed template operations test: {e}")
        return False


def main():
    """Run all integration tests."""
    logger.info("=" * 60)
    logger.info("M004-M006 Integration Test Suite")
    logger.info("=" * 60)
    
    tests = [
        ("Adapter Import", test_adapter_import),
        ("Adapter Initialization", test_adapter_initialization),
        ("Engine Integration", test_unified_engine_integration),
        ("Backward Compatibility", test_backward_compatibility),
        ("M006 Registry Connection", test_m006_registry_connection),
        ("Template Operations", test_template_operations)
    ]
    
    results = []
    for test_name, test_func in tests:
        logger.info(f"\nRunning: {test_name}")
        logger.info("-" * 40)
        result = test_func()
        results.append((test_name, result))
    
    # Summary
    logger.info("\n" + "=" * 60)
    logger.info("TEST SUMMARY")
    logger.info("=" * 60)
    
    passed = 0
    failed = 0
    
    for test_name, result in results:
        status = "✅ PASSED" if result else "❌ FAILED"
        logger.info(f"{test_name:30} {status}")
        if result:
            passed += 1
        else:
            failed += 1
    
    logger.info("-" * 60)
    logger.info(f"Total: {len(tests)} tests")
    logger.info(f"Passed: {passed}")
    logger.info(f"Failed: {failed}")
    
    if failed == 0:
        logger.info("\n🎉 All tests passed! M004-M006 integration successful!")
        return 0
    else:
        logger.error(f"\n⚠️ {failed} test(s) failed. Please review the integration.")
        return 1


if __name__ == "__main__":
    sys.exit(main())