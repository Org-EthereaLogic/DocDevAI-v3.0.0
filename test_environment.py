#!/usr/bin/env python3
"""
Simple environment test to verify DevDocAI development setup.
Run this after container build to ensure everything works.
"""

import sys
import platform

def test_python_version():
    """Verify Python version is 3.8+"""
    version = sys.version_info
    print(f"✓ Python {version.major}.{version.minor}.{version.micro}")
    assert version.major == 3 and version.minor >= 8, "Python 3.8+ required"

def test_imports():
    """Test that core dependencies are importable"""
    imports = [
        ('click', 'CLI framework'),
        ('pydantic', 'Data validation'),
        ('dotenv', 'Environment management'),
        ('yaml', 'YAML parsing'),
        ('sqlalchemy', 'Database ORM'),
        ('cryptography', 'Encryption'),
        ('argon2', 'Password hashing'),
        ('pytest', 'Testing framework'),
        ('jinja2', 'Template engine'),
    ]
    
    for module_name, description in imports:
        try:
            __import__(module_name)
            print(f"✓ {module_name:15} - {description}")
        except ImportError as e:
            print(f"✗ {module_name:15} - MISSING: {e}")
            return False
    return True

def test_project_structure():
    """Verify project structure is correct"""
    import os
    
    required_files = [
        'pyproject.toml',
        'requirements.txt',
        '.devcontainer/devcontainer.json'
    ]
    
    for file_path in required_files:
        if os.path.exists(file_path):
            print(f"✓ {file_path}")
        else:
            print(f"✗ {file_path} - MISSING")
            return False
    return True

def main():
    """Run all environment tests"""
    print("\n" + "="*50)
    print("DevDocAI v3.0.0 - Environment Test")
    print("="*50 + "\n")
    
    print("System Information:")
    print(f"Platform: {platform.system()} {platform.release()}")
    print(f"Machine: {platform.machine()}")
    print(f"Python Implementation: {platform.python_implementation()}")
    print()
    
    print("Testing Python Version...")
    test_python_version()
    print()
    
    print("Testing Core Dependencies...")
    if not test_imports():
        print("\n⚠️  Some dependencies are missing. Run: pip install -r requirements.txt")
        sys.exit(1)
    print()
    
    print("Testing Project Structure...")
    if not test_project_structure():
        print("\n⚠️  Project structure issues detected")
        sys.exit(1)
    
    print("\n" + "="*50)
    print("✅ Environment is ready for DevDocAI development!")
    print("="*50 + "\n")
    
    print("Next steps:")
    print("1. Create devdocai/ directory for source code")
    print("2. Start with M001 Configuration Manager")
    print("3. Follow 15-minute TDD blocks")
    print("4. Keep it simple - 80 lines, not 500!")

if __name__ == "__main__":
    main()