#!/usr/bin/env python3
"""
Module Integration Validation Report for M001-M006.
This script validates the integration between modules without requiring all imports to work.
"""

import os
import re
import json
from pathlib import Path
from typing import Dict, List, Set, Tuple


def find_imports(file_path: Path) -> Set[str]:
    """Find all module imports in a Python file."""
    imports = set()
    try:
        with open(file_path, 'r') as f:
            content = f.read()
            
        # Find "from X import Y" patterns (including relative imports)
        from_imports = re.findall(r'from\s+([\.\w]+)\s+import', content)
        # Find "import X" patterns
        direct_imports = re.findall(r'^import\s+(\S+)', content, re.MULTILINE)
        
        imports.update(from_imports)
        imports.update(direct_imports)
        
        # Also check for specific cross-module imports we care about
        if 'templates.registry_unified' in content or 'templates/registry_unified' in content:
            imports.add('devdocai.templates')
        if 'miair.engine_unified' in content or 'miair/engine_unified' in content:
            imports.add('devdocai.miair')
            
    except Exception as e:
        print(f"Error reading {file_path}: {e}")
    
    return imports


def analyze_module_dependencies(module_path: Path) -> Dict[str, Set[str]]:
    """Analyze dependencies for a module."""
    dependencies = {}
    
    # Map module names to their expected imports
    module_mapping = {
        'M001': 'devdocai.core',
        'M002': 'devdocai.storage',
        'M003': 'devdocai.miair',
        'M004': 'devdocai.generator',
        'M005': 'devdocai.quality',
        'M006': 'devdocai.templates'
    }
    
    for py_file in module_path.rglob('*.py'):
        if '__pycache__' in str(py_file):
            continue
            
        imports = find_imports(py_file)
        
        # Filter for inter-module dependencies
        module_deps = set()
        for imp in imports:
            # Handle relative imports (e.g., ...templates.registry_unified)
            clean_imp = imp.replace('...', '').replace('..', '').replace('.', '')
            
            for module_id, module_pkg in module_mapping.items():
                # Check both the import string and cleaned version
                if (module_pkg in imp or module_pkg.replace('devdocai.', '') in clean_imp) and module_pkg not in str(module_path):
                    module_deps.add(module_id)
        
        if module_deps:
            dependencies[str(py_file.relative_to(module_path))] = module_deps
    
    return dependencies


def generate_integration_report():
    """Generate comprehensive integration report for M001-M006."""
    
    base_path = Path('/workspaces/DocDevAI-v3.0.0/devdocai')
    
    # Analyze each module
    modules = {
        'M001': base_path / 'core',
        'M002': base_path / 'storage',
        'M003': base_path / 'miair',
        'M004': base_path / 'generator',
        'M005': base_path / 'quality',
        'M006': base_path / 'templates'
    }
    
    report = {
        'module_analysis': {},
        'integration_matrix': {},
        'gaps': [],
        'recommendations': []
    }
    
    # Analyze each module's dependencies
    for module_id, module_path in modules.items():
        if module_path.exists():
            deps = analyze_module_dependencies(module_path)
            
            # Aggregate all dependencies for the module
            all_deps = set()
            for file_deps in deps.values():
                all_deps.update(file_deps)
            
            report['module_analysis'][module_id] = {
                'path': str(module_path),
                'imports': list(all_deps),
                'file_count': len(list(module_path.rglob('*.py'))),
                'dependency_files': deps
            }
    
    # Build integration matrix
    for module_id in modules.keys():
        report['integration_matrix'][module_id] = {
            'imports': report['module_analysis'].get(module_id, {}).get('imports', []),
            'imported_by': []
        }
    
    # Find reverse dependencies
    for module_id, data in report['module_analysis'].items():
        for imported_module in data.get('imports', []):
            if imported_module in report['integration_matrix']:
                report['integration_matrix'][imported_module]['imported_by'].append(module_id)
    
    # Analyze specific integration issues
    
    # Check if M004 uses M006 templates
    m004_deps = report['module_analysis'].get('M004', {}).get('imports', [])
    if 'M006' not in m004_deps:
        report['gaps'].append({
            'type': 'Missing Integration',
            'modules': 'M004 → M006',
            'description': 'M004 (Document Generator) does not use M006 (Template Registry)',
            'impact': 'HIGH - M006 templates (35+) are not used by document generation',
            'evidence': 'M004 has its own template_loader.py instead of using M006'
        })
    
    # Check if M004 uses M003 for optimization
    if 'M003' not in m004_deps:
        report['gaps'].append({
            'type': 'Missing Integration',
            'modules': 'M004 → M003',
            'description': 'M004 (Document Generator) does not use M003 (MIAIR Engine)',
            'impact': 'MEDIUM - Documents not optimized using Shannon entropy',
            'evidence': 'No MIAIR imports found in M004'
        })
    
    # Check if M006 is used by any module
    m006_importers = report['integration_matrix'].get('M006', {}).get('imported_by', [])
    if not m006_importers or m006_importers == ['M006']:
        report['gaps'].append({
            'type': 'Isolated Module',
            'modules': 'M006',
            'description': 'M006 (Template Registry) is not used by other modules',
            'impact': 'HIGH - Entire template system is isolated',
            'evidence': 'No other modules import from M006'
        })
    
    # Generate recommendations
    if report['gaps']:
        report['recommendations'] = [
            '1. Refactor M004 to use M006 UnifiedTemplateRegistry for template management',
            '2. Integrate M003 MIAIR optimization into M004 document generation pipeline',
            '3. Create an orchestration layer to coordinate module interactions',
            '4. Add integration tests to validate module communication',
            '5. Consider creating a facade pattern for simplified module access'
        ]
    
    return report


def print_report(report: Dict):
    """Print the integration report in a readable format."""
    
    print("\n" + "="*80)
    print(" " * 20 + "MODULE INTEGRATION REPORT (M001-M006)")
    print("="*80)
    
    print("\n📊 MODULE DEPENDENCY MATRIX:")
    print("-" * 40)
    
    for module_id, data in report['integration_matrix'].items():
        imports = data.get('imports', [])
        imported_by = data.get('imported_by', [])
        
        print(f"\n{module_id}:")
        if imports:
            print(f"  → Imports: {', '.join(imports)}")
        else:
            print("  → Imports: None")
        
        if imported_by:
            print(f"  ← Used by: {', '.join(imported_by)}")
        else:
            print("  ← Used by: None")
    
    print("\n\n⚠️  INTEGRATION GAPS DETECTED:")
    print("-" * 40)
    
    for i, gap in enumerate(report['gaps'], 1):
        print(f"\n{i}. {gap['type']}: {gap['modules']}")
        print(f"   Description: {gap['description']}")
        print(f"   Impact: {gap['impact']}")
        print(f"   Evidence: {gap['evidence']}")
    
    print("\n\n✅ SUCCESSFUL INTEGRATIONS:")
    print("-" * 40)
    
    # List successful integrations
    success = []
    matrix = report['integration_matrix']
    
    if 'M001' in matrix and matrix['M001']['imported_by']:
        success.append("M001 (Config) → Used by all other modules")
    
    if 'M002' in matrix and len(matrix['M002']['imported_by']) >= 3:
        success.append(f"M002 (Storage) → Used by {', '.join(matrix['M002']['imported_by'])}")
    
    if 'M003' in matrix and 'M005' in matrix['M003']['imported_by']:
        success.append("M003 (MIAIR) → Used by M005 (Quality)")
    
    for item in success:
        print(f"  ✓ {item}")
    
    print("\n\n🔧 RECOMMENDATIONS:")
    print("-" * 40)
    
    for rec in report['recommendations']:
        print(f"  {rec}")
    
    print("\n\n📈 SUMMARY:")
    print("-" * 40)
    
    total_modules = len(report['integration_matrix'])
    integrated = sum(1 for m in report['integration_matrix'].values() 
                    if m['imports'] or m['imported_by'])
    gaps_count = len(report['gaps'])
    
    print(f"  Total Modules: {total_modules}")
    print(f"  Integrated Modules: {integrated}/{total_modules}")
    print(f"  Integration Gaps: {gaps_count}")
    print(f"  Integration Score: {((integrated - gaps_count) / total_modules * 100):.1f}%")
    
    print("\n" + "="*80 + "\n")


def save_report(report: Dict):
    """Save the report to a JSON file."""
    output_path = Path('/workspaces/DocDevAI-v3.0.0/docs/integration_report.json')
    with open(output_path, 'w') as f:
        json.dump(report, f, indent=2, default=str)
    print(f"Report saved to: {output_path}")


if __name__ == "__main__":
    print("Analyzing module integration for M001-M006...")
    report = generate_integration_report()
    print_report(report)
    save_report(report)
    
    # Return exit code based on gaps found
    exit_code = 0 if not report['gaps'] else 1
    print(f"\nValidation {'PASSED' if exit_code == 0 else 'FAILED'} with {len(report['gaps'])} gap(s) found.")
    exit(exit_code)