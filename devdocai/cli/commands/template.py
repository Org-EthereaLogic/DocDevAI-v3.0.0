"""
Template management commands for DevDocAI CLI.

Integrates with M006 Template Registry module.
"""

import sys
from pathlib import Path
from typing import Optional, List, Dict, Any
import json
import yaml

import click
from click import Context

# Import M006 Template Registry
try:
    from devdocai.templates.registry_unified import TemplateRegistryUnified
    from devdocai.templates.parser_unified import TemplateParserUnified
    TEMPLATE_AVAILABLE = True
except ImportError as e:
    TEMPLATE_AVAILABLE = False
    IMPORT_ERROR = str(e)


# Template categories
TEMPLATE_CATEGORIES = [
    'api', 'database', 'architecture', 'testing', 'security',
    'performance', 'deployment', 'documentation', 'general'
]


@click.group('template', invoke_without_command=True)
@click.pass_context
def template_group(ctx: Context):
    """Manage documentation templates."""
    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())


@template_group.command('list')
@click.option('--category', '-c', type=click.Choice(TEMPLATE_CATEGORIES),
              help='Filter by category')
@click.option('--format', '-f', type=click.Choice(['table', 'json', 'yaml']),
              default='table', help='Output format')
@click.option('--detailed', is_flag=True,
              help='Show detailed template information')
@click.pass_obj
def template_list(cli_ctx, category: Optional[str], format: str, detailed: bool):
    """
    List available documentation templates.
    
    Examples:
    
        # List all templates
        devdocai template list
        
        # List by category
        devdocai template list --category api
        
        # Show detailed information
        devdocai template list --detailed
    """
    if not TEMPLATE_AVAILABLE:
        cli_ctx.log(f"Template registry not available: {IMPORT_ERROR}", "error")
        sys.exit(1)
    
    try:
        # Initialize template registry
        registry = TemplateRegistryUnified()
        
        # Get templates
        if category:
            templates = registry.list_templates(category=category)
        else:
            templates = registry.list_templates()
        
        if not templates:
            cli_ctx.log("No templates found", "warning")
            return
        
        # Format output
        if format == 'json' or cli_ctx.json_output:
            if detailed:
                # Include full template details
                template_data = []
                for template in templates:
                    full_template = registry.get_template(template['name'])
                    if full_template:
                        template_data.append({
                            'name': full_template.name,
                            'category': full_template.category,
                            'description': full_template.description,
                            'version': full_template.version,
                            'variables': full_template.metadata.get('variables', []),
                            'tags': full_template.tags
                        })
                cli_ctx.output(template_data, format_type='json')
            else:
                cli_ctx.output(templates, format_type='json')
                
        elif format == 'yaml':
            cli_ctx.output(templates, format_type='yaml')
            
        else:
            # Table format
            if detailed:
                for template in templates:
                    full_template = registry.get_template(template['name'])
                    if full_template:
                        click.echo(f"\n{'='*60}")
                        click.echo(f"Name: {full_template.name}")
                        click.echo(f"Category: {full_template.category}")
                        click.echo(f"Description: {full_template.description}")
                        click.echo(f"Version: {full_template.version}")
                        if full_template.tags:
                            click.echo(f"Tags: {', '.join(full_template.tags)}")
                        if full_template.metadata.get('variables'):
                            click.echo(f"Variables: {', '.join(full_template.metadata['variables'])}")
            else:
                # Simple table
                click.echo(f"{'Name':<30} {'Category':<15} {'Description':<40}")
                click.echo("-" * 85)
                for template in templates:
                    name = template['name'][:29]
                    cat = template['category'][:14]
                    desc = template.get('description', '')[:39]
                    click.echo(f"{name:<30} {cat:<15} {desc:<40}")
        
        cli_ctx.log(f"\nTotal templates: {len(templates)}", "info")
        
    except Exception as e:
        cli_ctx.log(f"Failed to list templates: {str(e)}", "error")
        if cli_ctx.debug:
            import traceback
            traceback.print_exc()
        sys.exit(1)


@template_group.command('show')
@click.argument('name')
@click.option('--output', '-o', type=click.Path(),
              help='Save template to file')
@click.pass_obj
def template_show(cli_ctx, name: str, output: Optional[str]):
    """
    Show template details and content.
    
    Examples:
    
        # Show template content
        devdocai template show api-endpoint
        
        # Save template to file
        devdocai template show api-endpoint --output template.md
    """
    if not TEMPLATE_AVAILABLE:
        cli_ctx.log(f"Template registry not available: {IMPORT_ERROR}", "error")
        sys.exit(1)
    
    try:
        # Initialize template registry
        registry = TemplateRegistryUnified()
        
        # Get template
        template = registry.get_template(name)
        
        if not template:
            cli_ctx.log(f"Template '{name}' not found", "error")
            
            # Suggest similar templates
            all_templates = registry.list_templates()
            similar = [t['name'] for t in all_templates if name.lower() in t['name'].lower()]
            if similar:
                cli_ctx.log("Did you mean one of these?", "info")
                for suggestion in similar[:5]:
                    click.echo(f"  - {suggestion}")
            sys.exit(1)
        
        # Display or save template
        if output:
            output_path = Path(output)
            output_path.write_text(template.content)
            cli_ctx.log(f"Template saved to {output_path}", "success")
        else:
            # Display template information
            click.echo(f"\n{'='*60}")
            click.echo(f"Template: {template.name}")
            click.echo(f"Category: {template.category}")
            click.echo(f"Description: {template.description}")
            click.echo(f"Version: {template.version}")
            
            if template.metadata.get('variables'):
                click.echo(f"\nVariables:")
                for var in template.metadata['variables']:
                    click.echo(f"  - {{{{{var}}}}}")
            
            click.echo(f"\n{'='*60}")
            click.echo("Content:")
            click.echo(f"{'='*60}\n")
            click.echo(template.content)
            
    except Exception as e:
        cli_ctx.log(f"Failed to show template: {str(e)}", "error")
        if cli_ctx.debug:
            import traceback
            traceback.print_exc()
        sys.exit(1)


@template_group.command('create')
@click.argument('name')
@click.option('--category', '-c', type=click.Choice(TEMPLATE_CATEGORIES),
              default='general', help='Template category')
@click.option('--description', '-d', help='Template description')
@click.option('--from-file', '-f', type=click.Path(exists=True),
              help='Create template from file')
@click.option('--interactive', '-i', is_flag=True,
              help='Interactive template creation')
@click.pass_obj
def template_create(cli_ctx, name: str, category: str, description: Optional[str],
                    from_file: Optional[str], interactive: bool):
    """
    Create a new documentation template.
    
    Examples:
    
        # Create from file
        devdocai template create my-api-template --from-file template.md --category api
        
        # Interactive creation
        devdocai template create my-template --interactive
    """
    if not TEMPLATE_AVAILABLE:
        cli_ctx.log(f"Template registry not available: {IMPORT_ERROR}", "error")
        sys.exit(1)
    
    try:
        # Initialize template registry
        registry = TemplateRegistryUnified()
        
        # Check if template already exists
        if registry.get_template(name):
            cli_ctx.log(f"Template '{name}' already exists", "error")
            sys.exit(1)
        
        # Get template content
        if from_file:
            # Read from file
            file_path = Path(from_file)
            content = file_path.read_text()
            
        elif interactive:
            # Interactive creation
            click.echo("Creating template interactively...")
            
            if not description:
                description = click.prompt("Description", default=f"Custom {category} template")
            
            click.echo("\nEnter template content (press Ctrl+D when done):")
            lines = []
            try:
                while True:
                    line = input()
                    lines.append(line)
            except EOFError:
                pass
            content = "\n".join(lines)
            
            # Ask for variables
            click.echo("\nDefine template variables (comma-separated, or press Enter to skip):")
            var_input = click.prompt("Variables", default="")
            variables = [v.strip() for v in var_input.split(",") if v.strip()]
            
        else:
            # Default template content
            content = f"""# {name}

## Description
{description or 'Custom documentation template'}

## Content
{{{{description}}}}

## Details
{{{{details}}}}

## Examples
{{{{examples}}}}

## Notes
{{{{notes}}}}
"""
            variables = ['description', 'details', 'examples', 'notes']
        
        # Parse template to extract variables
        parser = TemplateParserUnified()
        if not interactive or not variables:
            variables = parser.extract_variables(content)
        
        # Create template
        template_data = {
            'name': name,
            'category': category,
            'description': description or f"Custom {category} template",
            'content': content,
            'version': '1.0.0',
            'tags': [category, 'custom'],
            'metadata': {
                'variables': variables,
                'author': 'CLI User',
                'created_via': 'devdocai-cli'
            }
        }
        
        # Add template to registry
        success = registry.add_template(
            name=name,
            content=content,
            category=category,
            description=template_data['description'],
            version=template_data['version'],
            tags=template_data['tags'],
            metadata=template_data['metadata']
        )
        
        if success:
            cli_ctx.log(f"Template '{name}' created successfully", "success")
            if variables:
                cli_ctx.log(f"Variables: {', '.join(variables)}", "info")
        else:
            cli_ctx.log(f"Failed to create template", "error")
            sys.exit(1)
            
    except Exception as e:
        cli_ctx.log(f"Failed to create template: {str(e)}", "error")
        if cli_ctx.debug:
            import traceback
            traceback.print_exc()
        sys.exit(1)


@template_group.command('edit')
@click.argument('name')
@click.option('--editor', '-e', help='Editor to use (default: $EDITOR)')
@click.option('--output', '-o', type=click.Path(),
              help='Save edited template to file instead of updating')
@click.pass_obj
def template_edit(cli_ctx, name: str, editor: Optional[str], output: Optional[str]):
    """
    Edit an existing template.
    
    Examples:
    
        # Edit template in default editor
        devdocai template edit api-endpoint
        
        # Edit with specific editor
        devdocai template edit api-endpoint --editor vim
        
        # Save edited version to file
        devdocai template edit api-endpoint --output modified.md
    """
    if not TEMPLATE_AVAILABLE:
        cli_ctx.log(f"Template registry not available: {IMPORT_ERROR}", "error")
        sys.exit(1)
    
    try:
        # Initialize template registry
        registry = TemplateRegistryUnified()
        
        # Get template
        template = registry.get_template(name)
        
        if not template:
            cli_ctx.log(f"Template '{name}' not found", "error")
            sys.exit(1)
        
        # Determine editor
        if not editor:
            editor = os.environ.get('EDITOR', 'nano')
        
        # Create temporary file with template content
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as tmp:
            tmp.write(template.content)
            tmp_path = tmp.name
        
        try:
            # Open in editor
            import subprocess
            subprocess.call([editor, tmp_path])
            
            # Read edited content
            with open(tmp_path, 'r') as f:
                edited_content = f.read()
            
            # Check if content changed
            if edited_content == template.content:
                cli_ctx.log("No changes made", "info")
                return
            
            if output:
                # Save to file
                output_path = Path(output)
                output_path.write_text(edited_content)
                cli_ctx.log(f"Edited template saved to {output_path}", "success")
            else:
                # Update template in registry
                success = registry.update_template(
                    name=name,
                    content=edited_content
                )
                
                if success:
                    cli_ctx.log(f"Template '{name}' updated successfully", "success")
                else:
                    cli_ctx.log("Failed to update template", "error")
                    sys.exit(1)
                    
        finally:
            # Clean up temporary file
            os.unlink(tmp_path)
            
    except Exception as e:
        cli_ctx.log(f"Failed to edit template: {str(e)}", "error")
        if cli_ctx.debug:
            import traceback
            traceback.print_exc()
        sys.exit(1)


@template_group.command('delete')
@click.argument('name')
@click.option('--force', '-f', is_flag=True,
              help='Force deletion without confirmation')
@click.pass_obj
def template_delete(cli_ctx, name: str, force: bool):
    """
    Delete a template.
    
    Examples:
    
        # Delete with confirmation
        devdocai template delete my-template
        
        # Force delete
        devdocai template delete my-template --force
    """
    if not TEMPLATE_AVAILABLE:
        cli_ctx.log(f"Template registry not available: {IMPORT_ERROR}", "error")
        sys.exit(1)
    
    try:
        # Initialize template registry
        registry = TemplateRegistryUnified()
        
        # Check if template exists
        template = registry.get_template(name)
        if not template:
            cli_ctx.log(f"Template '{name}' not found", "error")
            sys.exit(1)
        
        # Confirm deletion
        if not force:
            if not click.confirm(f"Delete template '{name}'?"):
                cli_ctx.log("Deletion cancelled", "info")
                return
        
        # Delete template
        success = registry.delete_template(name)
        
        if success:
            cli_ctx.log(f"Template '{name}' deleted successfully", "success")
        else:
            cli_ctx.log(f"Failed to delete template", "error")
            sys.exit(1)
            
    except Exception as e:
        cli_ctx.log(f"Failed to delete template: {str(e)}", "error")
        if cli_ctx.debug:
            import traceback
            traceback.print_exc()
        sys.exit(1)


@template_group.command('export')
@click.option('--category', '-c', type=click.Choice(TEMPLATE_CATEGORIES),
              help='Export specific category')
@click.option('--output', '-o', type=click.Path(), required=True,
              help='Output file path')
@click.option('--format', '-f', type=click.Choice(['json', 'yaml', 'zip']),
              default='json', help='Export format')
@click.pass_obj
def template_export(cli_ctx, category: Optional[str], output: str, format: str):
    """
    Export templates to file.
    
    Examples:
    
        # Export all templates to JSON
        devdocai template export --output templates.json
        
        # Export category to YAML
        devdocai template export --category api --output api-templates.yaml --format yaml
    """
    if not TEMPLATE_AVAILABLE:
        cli_ctx.log(f"Template registry not available: {IMPORT_ERROR}", "error")
        sys.exit(1)
    
    try:
        # Initialize template registry
        registry = TemplateRegistryUnified()
        
        # Get templates
        if category:
            templates = registry.list_templates(category=category)
        else:
            templates = registry.list_templates()
        
        if not templates:
            cli_ctx.log("No templates to export", "warning")
            return
        
        # Get full template data
        export_data = []
        for template_info in templates:
            template = registry.get_template(template_info['name'])
            if template:
                export_data.append({
                    'name': template.name,
                    'category': template.category,
                    'description': template.description,
                    'content': template.content,
                    'version': template.version,
                    'tags': template.tags,
                    'metadata': template.metadata
                })
        
        # Export based on format
        output_path = Path(output)
        
        if format == 'json':
            with open(output_path, 'w') as f:
                json.dump(export_data, f, indent=2)
                
        elif format == 'yaml':
            with open(output_path, 'w') as f:
                yaml.dump(export_data, f, default_flow_style=False)
                
        elif format == 'zip':
            import zipfile
            with zipfile.ZipFile(output_path, 'w') as zf:
                for template in export_data:
                    # Save each template as a separate file
                    filename = f"{template['category']}/{template['name']}.md"
                    zf.writestr(filename, template['content'])
                    
                    # Save metadata
                    meta_filename = f"{template['category']}/{template['name']}.meta.json"
                    meta_data = {k: v for k, v in template.items() if k != 'content'}
                    zf.writestr(meta_filename, json.dumps(meta_data, indent=2))
        
        cli_ctx.log(f"Exported {len(export_data)} templates to {output_path}", "success")
        
    except Exception as e:
        cli_ctx.log(f"Failed to export templates: {str(e)}", "error")
        if cli_ctx.debug:
            import traceback
            traceback.print_exc()
        sys.exit(1)