#!/usr/bin/env python3
"""
Check for unused Python dependencies in the project.
This script is used by pre-commit hooks and CI/CD pipelines.
"""

import ast
import sys
from pathlib import Path
from typing import Set, Dict, List

# Standard library modules to ignore
STDLIB_MODULES = {
    'os', 'sys', 'json', 're', 'math', 'random', 'datetime', 'time',
    'collections', 'itertools', 'functools', 'typing', 'pathlib',
    'unittest', 'test', 'copy', 'hashlib', 'logging', 'asyncio',
    'concurrent', 'multiprocessing', 'threading', 'queue', 'socket',
    'urllib', 'http', 'email', 'base64', 'io', 'tempfile', 'shutil',
    'subprocess', 'argparse', 'configparser', 'enum', 'dataclasses',
    'abc', 'warnings', 'traceback', 'inspect', 'importlib', 'contextlib',
    'weakref', 'gc', 'pickle', 'struct', 'binascii', 'codecs', 'locale',
    'secrets', 'uuid', 'platform', 'getpass', 'pwd', 'grp', 'stat',
    'types', 'operator', 'builtins', '__future__', 'textwrap', 'string',
    'decimal', 'fractions', 'numbers', 'cmath', 'statistics', 'array',
}

# Package name mappings (installed name -> import name)
PACKAGE_MAPPINGS = {
    'scikit-learn': 'sklearn',
    'sentence-transformers': 'sentence_transformers',
    'python-dotenv': 'dotenv',
    'argon2-cffi': 'argon2',
    'beautifulsoup4': 'bs4',
    'pytest-cov': 'pytest_cov',
    'pytest-asyncio': 'pytest_asyncio',
    'pillow': 'PIL',
    'pyyaml': 'yaml',
    'msgpack-python': 'msgpack',
    'python-dateutil': 'dateutil',
}

# Development-only packages that don't need to be imported
DEV_ONLY_PACKAGES = {
    'pytest', 'pytest-cov', 'pytest-asyncio', 'black', 'pylint', 
    'mypy', 'flake8', 'coverage', 'tox', 'sphinx', 'wheel',
    'setuptools', 'pip', 'twine', 'build', 'pre-commit',
    'vulture', 'bandit', 'safety', 'pip-audit', 'pipdeptree',
}

# Packages that might be imported conditionally or dynamically
CONDITIONAL_PACKAGES = {
    'uvloop',  # Might be imported conditionally for performance
    'redis',   # Optional distributed caching
    'openai',  # Optional AI provider
    'anthropic',  # Optional AI provider
    'google-generativeai',  # Optional AI provider
}

# Project-specific justified unused dependencies
# Add packages here with justification comments
JUSTIFIED_UNUSED = {
    # Example: 'package-name': "Justification for keeping this unused package",
    'jinja2': "Used for template rendering in M006, import happens dynamically",
    'alembic': "Database migration tool, used via CLI not imports",
    'sqlalchemy': "ORM used throughout M002, some imports are dynamic",
}


def get_imports_from_file(filepath: Path) -> Set[str]:
    """Extract all imported module names from a Python file."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Handle empty files
        if not content.strip():
            return set()
            
        tree = ast.parse(content)
        imports = set()
        
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    # Get the root module name
                    module_parts = alias.name.split('.')
                    imports.add(module_parts[0])
                    # Also add sub-modules for packages like 'concurrent.futures'
                    if len(module_parts) > 1:
                        imports.add('.'.join(module_parts[:2]))
                        
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    module_parts = node.module.split('.')
                    imports.add(module_parts[0])
                    if len(module_parts) > 1:
                        imports.add('.'.join(module_parts[:2]))
                        
        return imports
    except (SyntaxError, UnicodeDecodeError) as e:
        print(f"Warning: Could not parse {filepath}: {e}", file=sys.stderr)
        return set()
    except Exception as e:
        print(f"Warning: Error processing {filepath}: {e}", file=sys.stderr)
        return set()


def get_all_imports(project_dirs: List[str] = None) -> Set[str]:
    """Get all imports from the entire project."""
    if project_dirs is None:
        project_dirs = ['devdocai', 'tests', 'scripts']
    
    all_imports = set()
    
    for dir_name in project_dirs:
        if Path(dir_name).exists():
            for py_file in Path(dir_name).rglob('*.py'):
                # Skip migration files and __pycache__
                if 'migrations' in str(py_file) or '__pycache__' in str(py_file):
                    continue
                imports = get_imports_from_file(py_file)
                all_imports.update(imports)
    
    return all_imports


def parse_requirements_file(filepath: str) -> Dict[str, str]:
    """Parse requirements.txt and return a dict of package names to version specs."""
    packages = {}
    
    try:
        with open(filepath, 'r') as f:
            for line in f:
                line = line.strip()
                
                # Skip empty lines and comments
                if not line or line.startswith('#'):
                    continue
                
                # Remove inline comments
                if '#' in line:
                    line = line.split('#')[0].strip()
                
                # Extract package name (before any version specifier)
                for sep in ['>=', '==', '<=', '>', '<', '~=', '!=', '[']:
                    if sep in line:
                        pkg_name = line.split(sep)[0].strip()
                        break
                else:
                    pkg_name = line.strip()
                
                if pkg_name:
                    # Normalize package name
                    packages[pkg_name.lower()] = line
                    
    except FileNotFoundError:
        print(f"Warning: {filepath} not found", file=sys.stderr)
        
    return packages


def get_all_requirements() -> Dict[str, str]:
    """Get all packages from all requirements files."""
    all_packages = {}
    
    # Check main requirements.txt
    all_packages.update(parse_requirements_file('requirements.txt'))
    
    # Check for additional requirements files
    for req_file in Path('.').glob('*requirements*.txt'):
        if 'test' not in req_file.name and 'dev' not in req_file.name:
            all_packages.update(parse_requirements_file(str(req_file)))
    
    # Check module-specific requirements
    for req_file in Path('devdocai').rglob('requirements.txt'):
        all_packages.update(parse_requirements_file(str(req_file)))
    
    return all_packages


def normalize_package_name(name: str) -> str:
    """Normalize a package name for comparison."""
    return name.lower().replace('-', '_').replace('.', '_')


def check_unused_dependencies(verbose: bool = False) -> List[str]:
    """Check for unused dependencies and return a list of potentially unused packages."""
    # Get all imports from the project
    project_imports = get_all_imports()
    
    # Normalize import names
    normalized_imports = {normalize_package_name(imp) for imp in project_imports}
    
    # Get all installed packages
    all_packages = get_all_requirements()
    
    # Find potentially unused packages
    unused = []
    
    for pkg_name, pkg_line in all_packages.items():
        # Normalize package name
        pkg_normalized = normalize_package_name(pkg_name)
        
        # Skip development-only packages
        if pkg_normalized in {normalize_package_name(p) for p in DEV_ONLY_PACKAGES}:
            if verbose:
                print(f"ℹ️  Skipping dev package: {pkg_name}")
            continue
        
        # Skip justified unused packages
        if pkg_name in JUSTIFIED_UNUSED:
            if verbose:
                print(f"ℹ️  Justified unused: {pkg_name} - {JUSTIFIED_UNUSED[pkg_name]}")
            continue
        
        # Check if it's a conditional package
        if pkg_normalized in {normalize_package_name(p) for p in CONDITIONAL_PACKAGES}:
            if verbose:
                print(f"ℹ️  Conditional package: {pkg_name}")
            continue
        
        # Get the actual import name (might be different from package name)
        import_name = PACKAGE_MAPPINGS.get(pkg_name, pkg_normalized)
        import_name_normalized = normalize_package_name(import_name)
        
        # Check if the package is imported
        is_imported = (
            import_name_normalized in normalized_imports or
            import_name in project_imports or
            pkg_normalized in normalized_imports or
            # Check for sub-package imports (e.g., 'concurrent.futures')
            any(imp.startswith(import_name_normalized + '_') for imp in normalized_imports) or
            any(imp.startswith(pkg_normalized + '_') for imp in normalized_imports)
        )
        
        if not is_imported:
            unused.append(pkg_name)
            if verbose:
                print(f"⚠️  Potentially unused: {pkg_name}")
    
    return unused


def main():
    """Main entry point for the script."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Check for unused Python dependencies')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
    parser.add_argument('--strict', action='store_true', help='Exit with error code if unused deps found')
    parser.add_argument('--add-justified', nargs=2, metavar=('PACKAGE', 'REASON'),
                       help='Add a package to the justified unused list')
    
    args = parser.parse_args()
    
    if args.add_justified:
        package, reason = args.add_justified
        print(f"To add '{package}' to justified unused dependencies, edit this script and add:")
        print(f"    '{package}': \"{reason}\",")
        print("to the JUSTIFIED_UNUSED dictionary.")
        return 0
    
    unused = check_unused_dependencies(verbose=args.verbose)
    
    if unused:
        print("\n⚠️  Potentially unused dependencies detected:")
        print("=" * 50)
        for pkg in sorted(unused):
            print(f"  • {pkg}")
        
        print("\n📝 To resolve:")
        print("  1. Remove unused: pip uninstall <package>")
        print("  2. Update requirements.txt")
        print("  3. If needed but not imported directly, add to JUSTIFIED_UNUSED in this script")
        print(f"     Example: {sys.argv[0]} --add-justified <package> '<reason>'")
        
        if args.strict:
            return 1
    else:
        print("✅ No unused dependencies detected")
    
    return 0


if __name__ == '__main__':
    sys.exit(main())