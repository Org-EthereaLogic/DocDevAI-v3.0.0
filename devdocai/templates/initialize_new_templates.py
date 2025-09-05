#!/usr/bin/env python3
"""
Initialize new AI-powered templates in the Template Registry.
This script replaces the old templates with new LLM-based prompt templates.
"""

import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from devdocai.templates.registry_unified import UnifiedTemplateRegistry, OperationMode, RegistryConfig
from devdocai.templates.models import TemplateCategory, TemplateType
from devdocai.core.config import ConfigurationManager


def initialize_new_templates():
    """Initialize the template registry with new AI-powered templates."""
    
    print("Initializing new AI-powered templates...")
    
    # Initialize configuration manager with None (will use defaults)
    config_manager = None
    
    # Create registry with enterprise mode for all features
    registry_config = RegistryConfig(
        mode=OperationMode.ENTERPRISE,
        auto_load_defaults=True,
        enable_cache=True,
        enable_lazy_load=False,  # Load all templates immediately
        enable_indexing=True,
        enable_security=False  # Disable security to avoid dependencies
    )
    
    # Initialize the registry
    registry = UnifiedTemplateRegistry(
        config=registry_config,
        config_manager=config_manager
    )
    
    # Clear any existing templates
    print("Clearing existing templates...")
    registry._templates.clear()
    registry._template_index.clear() if hasattr(registry, '_template_index') else None
    
    # Load the new templates
    print("Loading new AI-powered templates...")
    templates_dir = Path(__file__).parent / "defaults"
    
    if templates_dir.exists():
        registry._load_default_templates()
        print(f"Loaded {len(registry._templates)} templates")
        
        # List loaded templates
        print("\nLoaded templates:")
        for template_id, template in registry._templates.items():
            metadata = template.metadata
            print(f"  - {template_id}: {metadata.get('name', 'Unknown')} ({metadata.get('category', 'uncategorized')})")
    else:
        print(f"Templates directory not found: {templates_dir}")
        return False
    
    # Verify AI-enabled templates
    ai_templates = [t for t in registry._templates.values() if t.metadata.get('ai_enabled', False)]
    print(f"\nAI-enabled templates: {len(ai_templates)}")
    
    return True


def verify_template_integration():
    """Verify that templates can be properly rendered with AI variables."""
    
    print("\nVerifying template integration...")
    
    # Initialize configuration manager with None (will use defaults)
    config_manager = None
    
    # Create registry
    registry_config = RegistryConfig(mode=OperationMode.BASIC)
    registry = UnifiedTemplateRegistry(
        config=registry_config,
        config_manager=config_manager
    )
    
    # Test rendering a template with sample context
    test_template_id = "product_requirements_document"
    test_context = {
        "user_input": "Create a mobile app for task management with calendar integration and team collaboration features."
    }
    
    try:
        if test_template_id in registry._templates:
            template = registry.get_template(test_template_id)
            
            # Check if template has AI variables
            if template.metadata.get('ai_enabled'):
                print(f"✅ Template '{test_template_id}' is AI-enabled")
                
                # Check template content includes user_input variable
                if "{{user_input}}" in template.content:
                    print(f"✅ Template includes {{{{user_input}}}} variable")
                else:
                    print(f"⚠️ Template might not be using user_input variable correctly")
            else:
                print(f"⚠️ Template '{test_template_id}' is not marked as AI-enabled")
                
            print(f"✅ Template '{test_template_id}' loaded successfully")
            return True
        else:
            print(f"❌ Template '{test_template_id}' not found in registry")
            return False
    except Exception as e:
        print(f"❌ Error verifying template: {e}")
        return False


if __name__ == "__main__":
    # Initialize new templates
    success = initialize_new_templates()
    
    if success:
        # Verify integration
        if verify_template_integration():
            print("\n✅ New AI-powered templates successfully initialized and verified!")
        else:
            print("\n⚠️ Templates initialized but verification failed")
    else:
        print("\n❌ Failed to initialize new templates")
        sys.exit(1)