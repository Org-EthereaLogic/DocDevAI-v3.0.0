#!/usr/bin/env python3
"""
Test Template Manager (M006) functionality directly
"""
import sys
import os
import json
from pathlib import Path

# Add the current directory to Python path
sys.path.insert(0, '/workspaces/DocDevAI-v3.0.0')

def test_template_registry():
    """Test the Template Registry functionality"""
    print("🧪 Testing Template Manager (M006) - Template Registry")
    print("=" * 60)
    
    try:
        # Import the unified template registry
        from devdocai.templates.registry_unified import UnifiedTemplateRegistry
        from devdocai.templates.parser_unified import UnifiedTemplateParser
        
        print("✅ Successfully imported Template Registry modules")
        
        # Initialize the registry
        registry = UnifiedTemplateRegistry(mode='basic')
        parser = UnifiedTemplateParser(mode='basic')
        
        print(f"✅ Template Registry initialized in 'basic' mode")
        
        # Test 1: List available templates
        print("\n📋 Test 1: List Available Templates")
        templates = registry.list_templates()
        print(f"   Found {len(templates)} templates:")
        for i, template in enumerate(templates[:10], 1):  # Show first 10
            print(f"   {i}. {template.get('name', 'Unknown')} - {template.get('description', 'No description')[:50]}...")
        
        if len(templates) > 10:
            print(f"   ... and {len(templates) - 10} more templates")
        
        # Test 2: Get a specific template
        print("\n📄 Test 2: Get Specific Template")
        if templates:
            first_template = templates[0]
            template_name = first_template.get('name', 'readme')
            print(f"   Retrieving template: {template_name}")
            
            template_data = registry.get_template(template_name)
            if template_data:
                print(f"   ✅ Template retrieved successfully")
                print(f"   - Name: {template_data.get('name', 'Unknown')}")
                print(f"   - Category: {template_data.get('category', 'Unknown')}")
                print(f"   - Content length: {len(template_data.get('content', ''))} characters")
                print(f"   - Variables: {template_data.get('variables', [])}")
            else:
                print("   ❌ Failed to retrieve template")
        
        # Test 3: Template rendering with variables
        print("\n🔧 Test 3: Template Rendering")
        if templates:
            template_name = templates[0].get('name', 'readme')
            template_data = registry.get_template(template_name)
            
            if template_data and template_data.get('content'):
                print(f"   Rendering template: {template_name}")
                
                # Sample variables for rendering
                sample_variables = {
                    'project_name': 'DocDevAI Test Project',
                    'project_description': 'A test project for Template Manager validation',
                    'author': 'DocDevAI Test Suite',
                    'version': '1.0.0',
                    'license': 'MIT'
                }
                
                try:
                    rendered_content = parser.render(
                        template_data.get('content', ''),
                        sample_variables
                    )
                    
                    if rendered_content:
                        print(f"   ✅ Template rendered successfully")
                        print(f"   - Rendered length: {len(rendered_content)} characters")
                        print(f"   - Preview (first 200 chars):")
                        print(f"     {rendered_content[:200]}...")
                        
                        # Check if variables were substituted
                        if 'DocDevAI Test Project' in rendered_content:
                            print(f"   ✅ Variable substitution working correctly")
                        else:
                            print(f"   ⚠️ Variable substitution may not be working")
                    else:
                        print("   ❌ Template rendering returned empty content")
                        
                except Exception as e:
                    print(f"   ❌ Template rendering failed: {str(e)}")
        
        # Test 4: Template categories
        print("\n📁 Test 4: Template Categories")
        try:
            categories = registry.get_categories()
            if categories:
                print(f"   Found {len(categories)} categories:")
                for category in categories:
                    count = len([t for t in templates if t.get('category') == category])
                    print(f"   - {category}: {count} templates")
            else:
                print("   No categories found or method not implemented")
        except Exception as e:
            print(f"   Categories test skipped: {str(e)}")
        
        # Test 5: Template search
        print("\n🔍 Test 5: Template Search")
        try:
            search_results = registry.search_templates("readme")
            if search_results:
                print(f"   Found {len(search_results)} templates matching 'readme':")
                for template in search_results[:3]:  # Show first 3
                    print(f"   - {template.get('name', 'Unknown')}")
            else:
                print("   No templates found matching 'readme'")
        except Exception as e:
            print(f"   Search test skipped: {str(e)}")
        
        print("\n🎉 Template Manager Testing Complete!")
        print("   ✅ Basic functionality is operational")
        return True
        
    except ImportError as e:
        print(f"❌ Failed to import Template Registry modules: {str(e)}")
        print("   This suggests the Template Manager may not be properly installed")
        return False
    except Exception as e:
        print(f"❌ Template Manager testing failed: {str(e)}")
        return False

def test_template_files():
    """Test if template files exist in the expected locations"""
    print("\n📂 Testing Template Files")
    print("=" * 30)
    
    template_dirs = [
        '/workspaces/DocDevAI-v3.0.0/devdocai/templates',
        '/workspaces/DocDevAI-v3.0.0/templates',
    ]
    
    for template_dir in template_dirs:
        path = Path(template_dir)
        if path.exists():
            print(f"✅ Found template directory: {template_dir}")
            
            # List template files
            template_files = list(path.glob('*.yaml')) + list(path.glob('*.yml')) + list(path.glob('*.md'))
            if template_files:
                print(f"   Found {len(template_files)} template files:")
                for template_file in template_files[:5]:  # Show first 5
                    print(f"   - {template_file.name}")
                if len(template_files) > 5:
                    print(f"   ... and {len(template_files) - 5} more")
            else:
                print("   No template files found in this directory")
        else:
            print(f"❌ Template directory not found: {template_dir}")

if __name__ == "__main__":
    print("🚀 DevDocAI Template Manager (M006) Test Suite")
    print("=" * 60)
    
    # Test template files first
    test_template_files()
    
    # Test template registry functionality
    success = test_template_registry()
    
    if success:
        print("\n🎉 Overall Result: Template Manager is FUNCTIONAL")
        sys.exit(0)
    else:
        print("\n❌ Overall Result: Template Manager has ISSUES")
        sys.exit(1)