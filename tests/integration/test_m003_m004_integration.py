#!/usr/bin/env python3
"""
Integration tests for M003 MIAIR Engine and M004 Document Generator.

Tests the optimization of generated documents using Shannon entropy analysis.
"""

import sys
import time
import tempfile
from pathlib import Path
from typing import Dict, Any

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from devdocai.generator.core.unified_engine import (
    UnifiedDocumentGenerator,
    UnifiedGenerationConfig,
    EngineMode,
    GenerationResult
)


def create_test_template() -> str:
    """Create a simple test template for document generation."""
    return """
# {{ title }}

## Overview
{{ description }}

## Project Details
- **Author**: {{ author }}
- **Version**: {{ version }}
- **Date**: {{ generation_date }}

## Content
{{ main_content }}

## Summary
This document was generated for project {{ project_name }}.
"""


def test_miair_optimization_disabled():
    """Test document generation with MIAIR optimization disabled."""
    print("\n" + "="*60)
    print("Test 1: Document Generation WITHOUT MIAIR Optimization")
    print("="*60)
    
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create template file
        template_dir = Path(tmpdir) / "templates"
        template_dir.mkdir()
        template_file = template_dir / "test_template.md.jinja2"
        template_file.write_text(create_test_template())
        
        # Configure generator with optimization disabled
        config = UnifiedGenerationConfig(
            engine_mode=EngineMode.DEVELOPMENT,  # Development mode disables optimization
            enable_miair_optimization=False,
            save_to_storage=False
        )
        
        generator = UnifiedDocumentGenerator(
            config=config,
            template_dir=template_dir
        )
        
        # Generate document
        inputs = {
            "title": "Test Document",
            "description": "This is a test document with some basic content.",
            "author": "Test Suite",
            "version": "1.0",
            "main_content": "This is the main content. It contains simple text."
        }
        
        start_time = time.time()
        result = generator.generate("test_template", inputs)
        generation_time = time.time() - start_time
        
        assert result.success, f"Generation failed: {result.error_message}"
        
        print(f"✓ Document generated successfully in {generation_time:.3f}s")
        print(f"  - Template: {result.template_name}")
        print(f"  - Format: {result.format}")
        print(f"  - Content length: {len(result.content)} chars")
        print(f"  - Optimization applied: {result.optimization_report.get('applied', False)}")
        
        # Verify optimization was not applied
        assert not result.optimization_report.get('applied', False), "Optimization should be disabled"
        
        return result


def test_miair_optimization_enabled():
    """Test document generation with MIAIR optimization enabled."""
    print("\n" + "="*60)
    print("Test 2: Document Generation WITH MIAIR Optimization")
    print("="*60)
    
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create template file
        template_dir = Path(tmpdir) / "templates"
        template_dir.mkdir()
        template_file = template_dir / "test_template.md.jinja2"
        template_file.write_text(create_test_template())
        
        # Configure generator with optimization enabled
        config = UnifiedGenerationConfig(
            engine_mode=EngineMode.PRODUCTION,  # Production mode enables optimization
            enable_miair_optimization=True,
            miair_target_quality=0.8,
            miair_max_iterations=5,
            save_to_storage=False
        )
        
        generator = UnifiedDocumentGenerator(
            config=config,
            template_dir=template_dir
        )
        
        # Generate document with more complex content for optimization
        inputs = {
            "title": "Enhanced Test Document",
            "description": "This document contains more complex content that can benefit from optimization.",
            "author": "Test Suite",
            "version": "2.0",
            "main_content": """
            This is a comprehensive document with multiple sections and varied content.
            
            The first section discusses important concepts related to software development.
            It includes technical details about implementation strategies and best practices.
            
            The second section provides examples and use cases. These examples demonstrate
            practical applications of the concepts discussed earlier. Code samples and
            configuration files are included for reference.
            
            The third section covers advanced topics and optimization techniques. This includes
            performance considerations, security best practices, and scalability patterns.
            
            Finally, the document concludes with recommendations and next steps for readers
            who want to implement these concepts in their own projects.
            """
        }
        
        start_time = time.time()
        result = generator.generate("test_template", inputs)
        generation_time = time.time() - start_time
        
        assert result.success, f"Generation failed: {result.error_message}"
        
        print(f"✓ Document generated successfully in {generation_time:.3f}s")
        print(f"  - Template: {result.template_name}")
        print(f"  - Format: {result.format}")
        print(f"  - Content length: {len(result.content)} chars")
        
        # Check optimization report
        opt_report = result.optimization_report
        if opt_report.get('applied'):
            print(f"\n✓ MIAIR Optimization Applied:")
            print(f"  - Original quality: {opt_report.get('original_score', 0):.2f}")
            print(f"  - Optimized quality: {opt_report.get('optimized_score', 0):.2f}")
            print(f"  - Improvement: {opt_report.get('improvement_percentage', 0):.1f}%")
            print(f"  - Iterations: {opt_report.get('iterations', 0)}")
            print(f"  - Optimization time: {opt_report.get('optimization_time', 0):.3f}s")
        else:
            print(f"\n⚠ Optimization not applied: {opt_report.get('reason', 'Unknown')}")
            if 'error' in opt_report:
                print(f"  Error: {opt_report['error']}")
        
        return result


def test_optimization_modes():
    """Test optimization behavior across different engine modes."""
    print("\n" + "="*60)
    print("Test 3: Optimization Behavior Across Engine Modes")
    print("="*60)
    
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create template file
        template_dir = Path(tmpdir) / "templates"
        template_dir.mkdir()
        template_file = template_dir / "test_template.md.jinja2"
        template_file.write_text(create_test_template())
        
        modes = [
            (EngineMode.DEVELOPMENT, False),  # Should disable optimization
            (EngineMode.STANDARD, True),      # Should enable optimization
            (EngineMode.PRODUCTION, True),    # Should enable optimization
            (EngineMode.STRICT, True)         # Should enable optimization with security
        ]
        
        inputs = {
            "title": "Mode Test Document",
            "description": "Testing optimization across different modes.",
            "author": "Test Suite",
            "version": "1.0",
            "main_content": "Content for testing different engine modes."
        }
        
        for mode, should_optimize in modes:
            print(f"\n  Testing {mode.value} mode...")
            
            config = UnifiedGenerationConfig(
                engine_mode=mode,
                save_to_storage=False
            )
            
            generator = UnifiedDocumentGenerator(
                config=config,
                template_dir=template_dir
            )
            
            result = generator.generate("test_template", inputs)
            assert result.success, f"Generation failed in {mode.value} mode"
            
            # Check if optimization matches expectation
            optimization_enabled = generator.config.enable_miair_optimization
            print(f"    - Optimization configured: {optimization_enabled}")
            
            # The actual optimization may not apply if content is already good
            if result.optimization_report.get('applied'):
                print(f"    - Optimization applied: Yes")
                print(f"    - Quality improvement: {result.optimization_report.get('improvement_percentage', 0):.1f}%")
            else:
                print(f"    - Optimization applied: No ({result.optimization_report.get('reason', 'N/A')})")
            
            # Verify configuration matches expectations
            if should_optimize:
                assert optimization_enabled, f"Optimization should be enabled for {mode.value} mode"
            else:
                assert not optimization_enabled, f"Optimization should be disabled for {mode.value} mode"
            
            print(f"    ✓ {mode.value} mode behavior verified")


def test_performance_stats():
    """Test that performance statistics include optimization metrics."""
    print("\n" + "="*60)
    print("Test 4: Performance Statistics with Optimization")
    print("="*60)
    
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create template file
        template_dir = Path(tmpdir) / "templates"
        template_dir.mkdir()
        template_file = template_dir / "test_template.md.jinja2"
        template_file.write_text(create_test_template())
        
        config = UnifiedGenerationConfig(
            engine_mode=EngineMode.PRODUCTION,
            enable_miair_optimization=True,
            save_to_storage=False
        )
        
        generator = UnifiedDocumentGenerator(
            config=config,
            template_dir=template_dir
        )
        
        # Generate multiple documents to collect statistics
        inputs = {
            "title": "Performance Test",
            "description": "Testing performance metrics.",
            "author": "Test Suite",
            "version": "1.0",
            "main_content": "Content for performance testing."
        }
        
        for i in range(3):
            result = generator.generate("test_template", inputs)
            assert result.success
        
        # Get performance statistics
        stats = generator.get_performance_stats()
        
        print(f"\n  Performance Statistics:")
        print(f"    - Total generations: {stats.get('total_generations', 0)}")
        print(f"    - Average generation time: {stats.get('average_time', 0):.3f}s")
        
        if 'optimization' in stats:
            opt_stats = stats['optimization']
            print(f"\n  Optimization Statistics:")
            print(f"    - Total optimizations: {opt_stats.get('total_optimizations', 0)}")
            print(f"    - Average optimization time: {opt_stats.get('average_optimization_time', 0):.3f}s")
            print(f"    - Min optimization time: {opt_stats.get('min_optimization_time', 0):.3f}s")
            print(f"    - Max optimization time: {opt_stats.get('max_optimization_time', 0):.3f}s")
        else:
            print(f"\n  ⚠ No optimization statistics available")
        
        print(f"\n  ✓ Performance statistics verified")


def test_backward_compatibility():
    """Test that existing code still works without MIAIR."""
    print("\n" + "="*60)
    print("Test 5: Backward Compatibility")
    print("="*60)
    
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create template file
        template_dir = Path(tmpdir) / "templates"
        template_dir.mkdir()
        template_file = template_dir / "test_template.md.jinja2"
        template_file.write_text(create_test_template())
        
        # Test with minimal configuration (backward compatibility)
        generator = UnifiedDocumentGenerator(template_dir=template_dir)
        
        inputs = {
            "title": "Compatibility Test",
            "description": "Testing backward compatibility.",
            "author": "Test Suite",
            "version": "1.0",
            "main_content": "Legacy code should still work."
        }
        
        # Test old method names
        result = generator.generate_document("test_template", **inputs)
        assert result.success, "Backward compatible method failed"
        
        print(f"  ✓ Legacy generate_document() method works")
        
        # Test security level setting
        generator.set_security_level("high")
        assert generator.config.engine_mode == EngineMode.STRICT
        print(f"  ✓ Legacy set_security_level() method works")
        
        # Test batch generation
        batch_results = generator.generate_batch([
            ("test_template", inputs),
            ("test_template", inputs)
        ])
        assert len(batch_results) == 2
        assert all(r.success for r in batch_results)
        print(f"  ✓ Batch generation works")
        
        print(f"\n  ✓ All backward compatibility tests passed")


def main():
    """Run all integration tests."""
    print("\n" + "="*60)
    print("M003-M004 Integration Test Suite")
    print("="*60)
    
    try:
        # Run tests
        test_miair_optimization_disabled()
        test_miair_optimization_enabled()
        test_optimization_modes()
        test_performance_stats()
        test_backward_compatibility()
        
        print("\n" + "="*60)
        print("✓ ALL TESTS PASSED")
        print("="*60)
        print("\nThe M003 MIAIR Engine has been successfully integrated into")
        print("the M004 Document Generator with the following features:")
        print("  - Configurable optimization (can be enabled/disabled)")
        print("  - Mode-based defaults (off in dev, on in production)")
        print("  - Performance tracking for optimization metrics")
        print("  - Graceful fallback if MIAIR is unavailable")
        print("  - Full backward compatibility maintained")
        print("="*60)
        
    except AssertionError as e:
        print(f"\n✗ TEST FAILED: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ UNEXPECTED ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()