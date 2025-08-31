#!/usr/bin/env python3
"""Check for unused Python dependencies in CI/CD."""
import ast
import os
import sys
from pathlib import Path

def get_imports_from_file(filepath):
    """Extract all imports from a Python file."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            tree = ast.parse(f.read())
        
        imports = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.add(alias.name.split('.')[0])
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    imports.add(node.module.split('.')[0])
        return imports
    except:
        return set()

def get_all_imports(root_dir='devdocai'):
    """Get all imports from the project."""
    all_imports = set()
    for py_file in Path(root_dir).rglob('*.py'):
        all_imports.update(get_imports_from_file(py_file))
    
    # Add test imports
    if Path('tests').exists():
        for py_file in Path('tests').rglob('*.py'):
            all_imports.update(get_imports_from_file(py_file))
    
    return all_imports

def get_installed_packages():
    """Get list of installed packages from requirements.txt."""
    packages = set()
    with open('requirements.txt', 'r') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#'):
                # Extract package name (before any version specifier)
                pkg = line.split('>=')[0].split('==')[0].split('<')[0].split('>')[0].split('[')[0]
                packages.add(pkg.lower().replace('-', '_'))
    return packages

# Standard library modules to ignore
STDLIB = {
    'os', 'sys', 'json', 're', 'math', 'random', 'datetime', 'time',
    'collections', 'itertools', 'functools', 'typing', 'pathlib',
    'unittest', 'test', 'copy', 'hashlib', 'logging', 'asyncio',
    'concurrent', 'multiprocessing', 'threading', 'queue', 'socket',
    'urllib', 'http', 'email', 'base64', 'io', 'tempfile', 'shutil',
    'subprocess', 'argparse', 'configparser', 'enum', 'dataclasses',
    'abc', 'warnings', 'traceback', 'inspect', 'importlib', 'contextlib',
    'weakref', 'gc', 'pickle', 'struct', 'binascii', 'codecs', 'locale',
    'secrets', 'uuid', 'platform', 'getpass', 'pwd', 'grp', 'stat',
    'types', 'operator', 'builtins', '__future__'
}

# Package name mappings (package name -> import name)
PACKAGE_MAPPINGS = {
    'scikit_learn': 'sklearn',
    'sentence_transformers': 'sentence_transformers',
    'python_dotenv': 'dotenv',
    'argon2_cffi': 'argon2',
    'beautifulsoup4': 'bs4',
    'pytest_cov': 'pytest_cov',
    'pytest_asyncio': 'pytest_asyncio',
}

if __name__ == '__main__':
    project_imports = get_all_imports()
    installed_packages = get_installed_packages()
    
    # Normalize import names
    normalized_imports = set()
    for imp in project_imports:
        imp_lower = imp.lower().replace('-', '_')
        normalized_imports.add(imp_lower)
    
    # Check for unused packages
    unused = []
    for pkg in installed_packages:
        pkg_normalized = pkg.lower().replace('-', '_')
        
        # Check if package is imported directly or through mapping
        import_name = PACKAGE_MAPPINGS.get(pkg_normalized, pkg_normalized)
        
        # Skip development tools and testing libraries
        if any(dev in pkg_normalized for dev in ['pytest', 'black', 'pylint', 'mypy', 'jinja2']):
            continue
            
        if import_name not in normalized_imports and import_name not in STDLIB:
            # Special cases for packages that might be imported differently
            if pkg_normalized == 'aiohttp' and 'aiohttp' not in normalized_imports:
                unused.append(pkg)
            elif pkg_normalized not in ['pip', 'setuptools', 'wheel']:
                # Check if it's a sub-package import
                if not any(imp.startswith(import_name) for imp in normalized_imports):
                    unused.append(pkg)
    
    if unused:
        print(f"⚠️ Found {len(unused)} potentially unused dependencies:")
        for pkg in unused:
            print(f"  - {pkg}")
        sys.exit(1)
    else:
        print("✅ No unused dependencies detected")