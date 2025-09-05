#!/usr/bin/env python3
"""Test loading a single template to see what validation errors occur."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from devdocai.templates.loader import TemplateLoader
from devdocai.templates.validator import TemplateValidator

# Test loading one template
template_path = Path("/workspaces/DocDevAI-v3.0.0/devdocai/templates/defaults/requirements/product_requirements_document.md")

loader = TemplateLoader()
validator = TemplateValidator()

try:
    # Load the template
    template = loader.load(template_path)
    print(f"Template loaded: {template.metadata.get('id')}")
    
    # Validate it
    result = validator.validate(template)
    if result.is_valid:
        print("✅ Template is valid")
    else:
        print(f"❌ Template validation failed with {len(result.errors)} errors:")
        for error in result.errors[:10]:  # Show first 10 errors
            print(f"  - {error}")
            
except Exception as e:
    print(f"Error loading template: {e}")
    import traceback
    traceback.print_exc()