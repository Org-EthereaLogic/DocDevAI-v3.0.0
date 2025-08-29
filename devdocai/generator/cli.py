#!/usr/bin/env python3
"""
M004 Document Generator CLI - Command-line interface for testing and basic usage.

Provides a simple command-line interface for generating documents using templates.
"""

import sys
import json
import argparse
import logging
from pathlib import Path
from typing import Dict, Any, Optional

from .core.engine import DocumentGenerator, GenerationConfig, GenerationResult
from ..core.config import ConfigurationManager
from ..storage import LocalStorageSystem
from ..common.logging import setup_logging, get_logger

logger = get_logger(__name__)


def setup_cli_logging(verbose: bool = False) -> None:
    """Setup logging for CLI usage."""
    log_level = "DEBUG" if verbose else "INFO"
    setup_logging(log_level=log_level, use_colors=True)


def load_inputs_from_file(file_path: Path) -> Dict[str, Any]:
    """Load template inputs from JSON or YAML file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            if file_path.suffix.lower() in ['.yaml', '.yml']:
                import yaml
                return yaml.safe_load(f) or {}
            else:
                return json.load(f)
    except FileNotFoundError:
        logger.error(f"Input file not found: {file_path}")
        sys.exit(1)
    except (json.JSONDecodeError, yaml.YAMLError) as e:
        logger.error(f"Error parsing input file: {e}")
        sys.exit(1)


def save_output_to_file(content: str, output_path: Path, format_type: str) -> None:
    """Save generated content to output file."""
    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        logger.info(f"Document saved to: {output_path}")
        logger.info(f"Format: {format_type}")
        logger.info(f"Size: {len(content)} characters")
        
    except IOError as e:
        logger.error(f"Error saving output file: {e}")
        sys.exit(1)


def list_templates_command(args: argparse.Namespace) -> None:
    """Handle list templates command."""
    generator = DocumentGenerator()
    templates = generator.list_templates(category=args.category)
    
    if not templates:
        if args.category:
            print(f"No templates found for category: {args.category}")
        else:
            print("No templates found")
        return
    
    print(f"Available templates ({len(templates)} found):")
    print()
    
    # Group by type if not filtering by category
    if not args.category:
        by_type = {}
        for template in templates:
            if template.type not in by_type:
                by_type[template.type] = []
            by_type[template.type].append(template)
        
        for template_type, type_templates in by_type.items():
            print(f"📁 {template_type.title()}:")
            for template in type_templates:
                print(f"  📄 {template.name}")
                print(f"     Category: {template.category}")
                print(f"     Description: {template.description or 'No description'}")
                print(f"     Variables: {len(template.variables)} required, {len(template.optional_variables)} optional")
                print()
    else:
        for template in templates:
            print(f"📄 {template.name}")
            print(f"   Type: {template.type}")
            print(f"   Description: {template.description or 'No description'}")
            print(f"   Variables: {len(template.variables)} required, {len(template.optional_variables)} optional")
            print()


def template_info_command(args: argparse.Namespace) -> None:
    """Handle template info command."""
    generator = DocumentGenerator()
    template = generator.get_template_info(args.template)
    
    if not template:
        logger.error(f"Template not found: {args.template}")
        sys.exit(1)
    
    print(f"Template: {template.name}")
    print(f"Title: {template.title}")
    print(f"Type: {template.type}")
    print(f"Category: {template.category}")
    print(f"Version: {template.version}")
    if template.author:
        print(f"Author: {template.author}")
    if template.description:
        print(f"Description: {template.description}")
    print()
    
    if template.variables:
        print("Required Variables:")
        for var in template.variables:
            print(f"  - {var}")
        print()
    
    if template.optional_variables:
        print("Optional Variables:")
        for var in template.optional_variables:
            print(f"  - {var}")
        print()
    
    if template.sections:
        print("Document Sections:")
        for section in template.sections:
            print(f"  - {section}")
        print()
    
    if template.tags:
        print(f"Tags: {', '.join(template.tags)}")
        print()


def validate_command(args: argparse.Namespace) -> None:
    """Handle validate inputs command."""
    generator = DocumentGenerator()
    inputs = load_inputs_from_file(args.inputs)
    
    errors = generator.validate_template_inputs(args.template, inputs)
    
    if not errors:
        print(f"✅ Inputs are valid for template: {args.template}")
    else:
        print(f"❌ Validation errors for template: {args.template}")
        for error in errors:
            print(f"  • {error}")
        sys.exit(1)


def generate_command(args: argparse.Namespace) -> None:
    """Handle generate document command."""
    # Load inputs
    inputs = load_inputs_from_file(args.inputs)
    
    # Create generator
    try:
        config_manager = ConfigurationManager() if not args.no_config else None
        storage_system = LocalStorageSystem() if not args.no_storage else None
        generator = DocumentGenerator(
            config_manager=config_manager,
            storage_system=storage_system
        )
    except Exception as e:
        logger.error(f"Failed to initialize generator: {e}")
        sys.exit(1)
    
    # Create generation config
    gen_config = GenerationConfig(
        output_format=args.format,
        save_to_storage=not args.no_storage,
        include_metadata=not args.no_metadata,
        validate_inputs=not args.no_validate,
        project_name=args.project_name,
        author=args.author,
        version=args.version
    )
    
    # Generate document
    result = generator.generate_document(args.template, inputs, gen_config)
    
    if result.success:
        logger.info(f"✅ Document generated successfully in {result.generation_time:.3f}s")
        
        if result.document_id and not args.no_storage:
            logger.info(f"Document ID: {result.document_id}")
        
        # Save to output file
        if args.output:
            save_output_to_file(result.content, args.output, result.format)
        else:
            # Print to stdout
            print(result.content)
        
        # Show warnings if any
        if result.warnings:
            logger.warning("Warnings:")
            for warning in result.warnings:
                logger.warning(f"  • {warning}")
    else:
        logger.error(f"❌ Document generation failed: {result.error_message}")
        sys.exit(1)


def create_sample_inputs_command(args: argparse.Namespace) -> None:
    """Handle create sample inputs command."""
    generator = DocumentGenerator()
    template = generator.get_template_info(args.template)
    
    if not template:
        logger.error(f"Template not found: {args.template}")
        sys.exit(1)
    
    # Create sample inputs with placeholders
    sample_inputs = {}
    
    for var in template.variables:
        sample_inputs[var] = f"[REQUIRED: {var}]"
    
    for var in template.optional_variables:
        sample_inputs[var] = f"[OPTIONAL: {var}]"
    
    # Add some common fields with more helpful defaults
    common_defaults = {
        'title': f'Sample {template.title}',
        'description': f'This is a sample {template.name} document',
        'author': 'Your Name',
        'version': '1.0',
        'project_name': 'Sample Project',
        'generated_date': '2024-01-01'
    }
    
    for key, value in common_defaults.items():
        if key in sample_inputs:
            sample_inputs[key] = value
    
    # Save sample inputs
    output_path = args.output or Path(f"{args.template}_sample_inputs.json")
    
    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(sample_inputs, f, indent=2)
        
        logger.info(f"Sample inputs created: {output_path}")
        logger.info(f"Edit the file and replace placeholders with actual values")
        
    except IOError as e:
        logger.error(f"Error creating sample inputs file: {e}")
        sys.exit(1)


def main() -> None:
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="DevDocAI Document Generator CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # List all available templates
  python -m devdocai.generator.cli list

  # Get information about a specific template
  python -m devdocai.generator.cli info prd

  # Create sample inputs for a template
  python -m devdocai.generator.cli sample prd -o prd_inputs.json

  # Validate inputs for a template
  python -m devdocai.generator.cli validate prd prd_inputs.json

  # Generate a document
  python -m devdocai.generator.cli generate prd prd_inputs.json -o output.md

  # Generate HTML output
  python -m devdocai.generator.cli generate prd prd_inputs.json -f html -o output.html
        """)
    
    parser.add_argument('-v', '--verbose', action='store_true',
                       help='Enable verbose logging')
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # List templates command
    list_parser = subparsers.add_parser('list', help='List available templates')
    list_parser.add_argument('-c', '--category', help='Filter by category')
    
    # Template info command
    info_parser = subparsers.add_parser('info', help='Show template information')
    info_parser.add_argument('template', help='Template name')
    
    # Validate inputs command
    validate_parser = subparsers.add_parser('validate', help='Validate template inputs')
    validate_parser.add_argument('template', help='Template name')
    validate_parser.add_argument('inputs', type=Path, help='Input file (JSON or YAML)')
    
    # Generate document command
    generate_parser = subparsers.add_parser('generate', help='Generate document')
    generate_parser.add_argument('template', help='Template name')
    generate_parser.add_argument('inputs', type=Path, help='Input file (JSON or YAML)')
    generate_parser.add_argument('-o', '--output', type=Path, help='Output file')
    generate_parser.add_argument('-f', '--format', choices=['markdown', 'html'], 
                                default='markdown', help='Output format')
    generate_parser.add_argument('--project-name', help='Project name')
    generate_parser.add_argument('--author', help='Author name')
    generate_parser.add_argument('--version', default='1.0', help='Document version')
    generate_parser.add_argument('--no-config', action='store_true',
                                help='Disable configuration manager')
    generate_parser.add_argument('--no-storage', action='store_true',
                                help='Disable storage integration')
    generate_parser.add_argument('--no-metadata', action='store_true',
                                help='Exclude metadata from output')
    generate_parser.add_argument('--no-validate', action='store_true',
                                help='Skip input validation')
    
    # Create sample inputs command
    sample_parser = subparsers.add_parser('sample', help='Create sample inputs file')
    sample_parser.add_argument('template', help='Template name')
    sample_parser.add_argument('-o', '--output', type=Path, help='Output file')
    
    # Parse arguments
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    # Setup logging
    setup_cli_logging(args.verbose)
    
    # Execute command
    try:
        if args.command == 'list':
            list_templates_command(args)
        elif args.command == 'info':
            template_info_command(args)
        elif args.command == 'validate':
            validate_command(args)
        elif args.command == 'generate':
            generate_command(args)
        elif args.command == 'sample':
            create_sample_inputs_command(args)
        else:
            parser.print_help()
            sys.exit(1)
            
    except KeyboardInterrupt:
        logger.info("Operation cancelled by user")
        sys.exit(130)
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()