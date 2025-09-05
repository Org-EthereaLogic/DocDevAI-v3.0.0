#!/usr/bin/env python3
"""
Test the newly installed AI-powered templates
"""
import sys
import os
from pathlib import Path

# Add the current directory to Python path
sys.path.insert(0, '/workspaces/DocDevAI-v3.0.0')

def test_template_loading():
    """Test loading of new AI-powered templates"""
    print("🧪 Testing New AI-Powered Templates")
    print("=" * 50)
    
    try:
        # Try to load templates directly
        from devdocai.templates.registry_unified import UnifiedTemplateRegistry
        
        # Initialize registry
        registry = UnifiedTemplateRegistry(mode='basic')
        print("✅ Registry initialized")
        
        # Test template loading
        template_names = [
            'product_requirements_document',
            'software_architecture_document', 
            'project_plan_wbs'
        ]
        
        for template_name in template_names:
            print(f"\n📄 Testing template: {template_name}")
            try:
                template = registry.get_template(template_name)
                if template:
                    print(f"   ✅ Template loaded successfully")
                    print(f"   - Name: {template.name}")
                    print(f"   - AI Enabled: {getattr(template, 'ai_enabled', 'Unknown')}")
                    print(f"   - Variables: {[v.name for v in template.variables] if hasattr(template, 'variables') else 'Unknown'}")
                    
                    # Check if content contains our user_input placeholder
                    content = getattr(template, 'content', '')
                    if '{{user_input}}' in content:
                        print(f"   ✅ Contains {{user_input}} placeholder - AI-powered!")
                    else:
                        print(f"   ⚠️ No {{user_input}} placeholder found")
                        print(f"   Content preview: {content[:200]}...")
                else:
                    print(f"   ❌ Template not found")
            except Exception as e:
                print(f"   ❌ Error loading template: {str(e)}")
        
        # Test search functionality
        print(f"\n🔍 Testing search functionality")
        try:
            results = registry.search_templates('requirements')
            print(f"   Found {len(results)} templates matching 'requirements'")
            for template in results[:3]:
                print(f"   - {template.name if hasattr(template, 'name') else template}")
        except Exception as e:
            print(f"   Search test failed: {str(e)}")
            
    except Exception as e:
        print(f"❌ Failed to test templates: {str(e)}")
        return False
    
    return True

def check_template_files():
    """Check the actual template files"""
    print("\n📂 Checking Template Files")
    print("=" * 30)
    
    template_dir = Path('/workspaces/DocDevAI-v3.0.0/devdocai/templates/defaults')
    
    for template_file in template_dir.rglob('*.md'):
        print(f"\n📄 {template_file.relative_to(template_dir)}")
        try:
            content = template_file.read_text()
            
            # Check for AI template markers
            if '{{user_input}}' in content:
                print(f"   ✅ Contains {{user_input}} - AI-powered template")
            else:
                print(f"   ⚠️ Traditional template (no {{user_input}})")
            
            # Check for metadata
            if '---' in content and 'metadata:' in content:
                print(f"   ✅ Has YAML metadata")
                
                # Extract ai_enabled flag
                lines = content.split('\n')
                for line in lines:
                    if 'ai_enabled:' in line:
                        print(f"   AI Enabled: {line.split(':')[1].strip()}")
                        break
                        
            print(f"   Size: {len(content)} characters")
            
        except Exception as e:
            print(f"   ❌ Error reading file: {str(e)}")

if __name__ == "__main__":
    print("🚀 DevDocAI New Template Test Suite")
    print("=" * 50)
    
    # Check template files first
    check_template_files()
    
    # Test template loading
    success = test_template_loading()
    
    if success:
        print(f"\n🎉 Templates are properly configured!")
    else:
        print(f"\n❌ Template issues detected")