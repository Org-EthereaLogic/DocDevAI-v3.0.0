#!/usr/bin/env python3
"""
Test script to verify DevDocAI CLI is working correctly.

Run this after installation to ensure the CLI is properly configured.
"""

import subprocess
import sys
from pathlib import Path


def run_command(cmd):
    """Run a CLI command and return the result."""
    try:
        result = subprocess.run(
            cmd, 
            shell=True, 
            capture_output=True, 
            text=True,
            timeout=5
        )
        return result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return -1, "", "Command timed out"
    except Exception as e:
        return -1, "", str(e)


def test_cli():
    """Test various CLI commands."""
    print("Testing DevDocAI CLI Installation...")
    print("=" * 60)
    
    tests = [
        ("Version check", "python -m devdocai.cli.main --version"),
        ("Help output", "python -m devdocai.cli.main --help"),
        ("Generate help", "python -m devdocai.cli.main generate --help"),
        ("Analyze help", "python -m devdocai.cli.main analyze --help"),
        ("Config help", "python -m devdocai.cli.main config --help"),
        ("Template help", "python -m devdocai.cli.main template --help"),
        ("Enhance help", "python -m devdocai.cli.main enhance --help"),
        ("Security help", "python -m devdocai.cli.main security --help"),
        ("Completion", "python -m devdocai.cli.main completion"),
    ]
    
    passed = 0
    failed = 0
    
    for test_name, command in tests:
        print(f"\nTesting: {test_name}")
        print(f"Command: {command}")
        
        returncode, stdout, stderr = run_command(command)
        
        if returncode == 0:
            print(f"✓ PASSED")
            if "--version" in command:
                print(f"  Output: {stdout.strip()[:100]}")
            passed += 1
        else:
            print(f"✗ FAILED (exit code: {returncode})")
            if stderr:
                print(f"  Error: {stderr.strip()[:200]}")
            failed += 1
    
    print("\n" + "=" * 60)
    print(f"Results: {passed} passed, {failed} failed")
    
    if failed == 0:
        print("✓ All CLI tests passed successfully!")
        return 0
    else:
        print(f"⚠ {failed} test(s) failed. Please check the errors above.")
        return 1


def test_module_imports():
    """Test that CLI modules can be imported."""
    print("\nTesting module imports...")
    print("-" * 40)
    
    modules = [
        "devdocai.cli.main",
        "devdocai.cli.commands.generate",
        "devdocai.cli.commands.analyze",
        "devdocai.cli.commands.config",
        "devdocai.cli.commands.template",
        "devdocai.cli.commands.enhance",
        "devdocai.cli.commands.security",
        "devdocai.cli.utils.output",
        "devdocai.cli.utils.progress",
        "devdocai.cli.utils.validators",
    ]
    
    passed = 0
    failed = 0
    
    for module in modules:
        try:
            __import__(module)
            print(f"✓ {module}")
            passed += 1
        except ImportError as e:
            print(f"✗ {module}: {e}")
            failed += 1
    
    print(f"\nImport results: {passed} passed, {failed} failed")
    return failed


def create_test_file():
    """Create a test file for CLI operations."""
    test_file = Path("test_document.md")
    test_file.write_text("""# Test Document

This is a test document for DevDocAI CLI testing.

## Features
- Feature 1
- Feature 2
- Feature 3

## API Reference
```python
def test_function():
    '''Test function for documentation.'''
    return "Hello, World!"
```

## Examples
Example usage goes here.
""")
    return test_file


def test_cli_operations():
    """Test actual CLI operations with files."""
    print("\nTesting CLI operations...")
    print("-" * 40)
    
    # Create test file
    test_file = create_test_file()
    
    operations = [
        ("Generate (may fail without modules)", 
         f"python -m devdocai.cli.main generate file {test_file} --format markdown"),
        ("Analyze (may fail without modules)", 
         f"python -m devdocai.cli.main analyze document {test_file}"),
        ("Config list (may fail without modules)", 
         "python -m devdocai.cli.main config list"),
    ]
    
    for op_name, command in operations:
        print(f"\nTesting: {op_name}")
        returncode, stdout, stderr = run_command(command)
        
        if returncode == 0:
            print(f"✓ Command executed successfully")
        elif "not available" in stderr.lower() or "not available" in stdout.lower():
            print(f"ℹ Module not available (expected if dependencies missing)")
        else:
            print(f"✗ Command failed: {stderr.strip()[:100]}")
    
    # Cleanup
    test_file.unlink(missing_ok=True)
    print("\n✓ Test file cleaned up")


def main():
    """Main test function."""
    print("\n" + "=" * 60)
    print("DevDocAI CLI Test Suite")
    print("=" * 60)
    
    # Test imports
    import_failures = test_module_imports()
    
    # Test CLI commands
    cli_result = test_cli()
    
    # Test operations if CLI works
    if cli_result == 0:
        test_cli_operations()
    
    print("\n" + "=" * 60)
    if import_failures == 0 and cli_result == 0:
        print("✓ All tests completed successfully!")
        print("\nTo install the CLI system-wide, run:")
        print("  pip install -e .")
        print("\nThen you can use:")
        print("  devdocai --help")
        print("  dda --help  (short alias)")
        return 0
    else:
        print("⚠ Some tests failed. Please review the errors above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())