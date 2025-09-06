"""
Document generation commands for DevDocAI CLI.

Integrates with M004 Document Generator module.
"""

import os
import sys
from pathlib import Path
from typing import Optional, List, Dict, Any
import json
from concurrent.futures import ProcessPoolExecutor, as_completed
import multiprocessing as mp
from functools import lru_cache

import click
from click import Context

# Lazy imports flag
GENERATOR_AVAILABLE = None
IMPORT_ERROR = None

def _lazy_import_generator():
    """Lazy import of generator modules."""
    global GENERATOR_AVAILABLE, IMPORT_ERROR
    
    if GENERATOR_AVAILABLE is not None:
        return GENERATOR_AVAILABLE
    
    try:
        # Import only when actually needed
        global UnifiedDocumentGenerator, UnifiedGenerationConfig, EngineMode, UnifiedTemplateRegistry
        from devdocai.generator.core.unified_engine import UnifiedDocumentGenerator, UnifiedGenerationConfig, EngineMode
        from devdocai.templates.registry_unified import UnifiedTemplateRegistry, OperationMode
        GENERATOR_AVAILABLE = True
    except ImportError as e:
        GENERATOR_AVAILABLE = False
        IMPORT_ERROR = str(e)
    
    return GENERATOR_AVAILABLE

# Cache for generator instances
@lru_cache(maxsize=4)
def get_generator(mode: str):
    """Get cached generator instance."""
    if not _lazy_import_generator():
        raise ImportError(f"Generator not available: {IMPORT_ERROR}")
    
    op_mode = EngineMode[mode.upper()] if mode.upper() in [e.name for e in EngineMode] else EngineMode.STANDARD
    config = UnifiedGenerationConfig(mode=op_mode)
    return UnifiedDocumentGenerator(config)

# Cache for template registry
@lru_cache(maxsize=1)
def get_template_registry():
    """Get cached template registry."""
    if not _lazy_import_generator():
        raise ImportError(f"Template registry not available: {IMPORT_ERROR}")
    
    return TemplateRegistryUnified()

def process_file_parallel(args):
    """Process a single file (for parallel processing)."""
    file_path, template, mode, format_type = args
    
    try:
        generator = get_generator(mode)
        registry = get_template_registry()
        
        # Read file content
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Get template
        template_obj = registry.get_template(template)
        if not template_obj:
            template_obj = registry.get_template('general')
        
        # Generate documentation
        context = {
            'source_code': content,
            'file_path': str(file_path),
            'file_name': file_path.name,
            'language': file_path.suffix[1:] if file_path.suffix else 'unknown'
        }
        
        doc = generator.generate(
            source_code=content,
            template=template_obj.content if template_obj else '',
            context=context,
            output_format=format_type
        )
        
        return file_path, doc, None
        
    except Exception as e:
        return file_path, None, str(e)


@click.group('generate', invoke_without_command=True)
@click.pass_context
def generate_group(ctx: Context):
    """Generate documentation from source code and other inputs."""
    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())


@generate_group.command('file')
@click.argument('path', type=click.Path(exists=True))
@click.option('--template', '-t', default='general', 
              help='Template to use for generation')
@click.option('--output', '-o', type=click.Path(),
              help='Output file path (default: stdout)')
@click.option('--format', '-f', type=click.Choice(['markdown', 'pdf']),
              default='markdown', help='Output format')
@click.option('--batch', '-b', is_flag=True,
              help='Process all files in directory')
@click.option('--recursive', '-r', is_flag=True,
              help='Process directories recursively')
@click.option('--pattern', '-p', default='*.py',
              help='File pattern for batch processing (e.g., *.py)')
@click.option('--mode', type=click.Choice(['basic', 'optimized', 'secure', 'balanced']),
              default='balanced', help='Operation mode')
@click.option('--parallel', '-P', type=int, default=0,
              help='Number of parallel workers (0=auto, based on CPU count)')
@click.pass_obj
def generate_file(cli_ctx, path: str, template: str, output: Optional[str],
                   format: str, batch: bool, recursive: bool, pattern: str, mode: str, parallel: int):
    """
    Generate documentation for a file or directory.
    
    Examples:
    
        # Generate docs for a single file
        devdocai generate file api.py --template api-endpoint
        
        # Generate docs for all Python files in a directory
        devdocai generate file src/ --batch --pattern "*.py"
        
        # Generate HTML documentation
        devdocai generate file module.py --format html --output docs.html
    """
    # Lazy check for generator availability
    if not _lazy_import_generator():
        cli_ctx.log(f"Document generator not available: {IMPORT_ERROR}", "error")
        sys.exit(1)
    
    try:
        path_obj = Path(path)
        files_to_process = []
        
        if batch or path_obj.is_dir():
            # Batch processing
            if recursive:
                files_to_process = list(path_obj.rglob(pattern))
            else:
                files_to_process = list(path_obj.glob(pattern))
            
            if not files_to_process:
                cli_ctx.log(f"No files matching pattern '{pattern}' found", "warning")
                return
                
            cli_ctx.log(f"Found {len(files_to_process)} files to process", "info")
        else:
            # Single file processing
            files_to_process = [path_obj]
        
        # Determine number of workers for parallel processing
        if parallel == 0:
            parallel = min(mp.cpu_count(), 4)  # Auto-detect, max 4
        elif parallel == 1:
            parallel = 0  # Disable parallel processing
        
        results = []
        errors = []
        
        if parallel > 1 and len(files_to_process) > 1:
            # Parallel processing
            cli_ctx.log(f"Using {parallel} parallel workers", "debug")
            
            # Prepare arguments for parallel processing
            args_list = [
                (f, template, mode, format) 
                for f in files_to_process
            ]
            
            # Process in parallel
            with ProcessPoolExecutor(max_workers=parallel) as executor:
                futures = {executor.submit(process_file_parallel, args): args[0] 
                          for args in args_list}
                
                with click.progressbar(length=len(files_to_process), 
                                       label='Generating documentation') as bar:
                    for future in as_completed(futures):
                        file_path, doc, error = future.result()
                        bar.update(1)
                        
                        if error:
                            errors.append((file_path, error))
                            cli_ctx.log(f"Error processing {file_path}: {error}", "error")
                        else:
                            results.append({
                                'file': str(file_path),
                                'documentation': doc,
                                'template': template,
                                'format': format
                            })
        else:
            # Sequential processing (single file or parallel=1)
            # Initialize generator for sequential use
            generator = get_generator(mode)
            template_registry = get_template_registry()
            
            with click.progressbar(files_to_process, label='Generating documentation') as files:
                for file_path in files:
                    try:
                        # Read source code
                        source_code = file_path.read_text()
                        
                        # Get template
                        template_obj = template_registry.get_template(template)
                        if not template_obj:
                            cli_ctx.log(f"Template '{template}' not found, using default", "warning")
                            template_obj = template_registry.get_template('general')
                        
                        # Generate documentation
                        context = {
                            'source_code': source_code,
                            'file_path': str(file_path),
                            'file_name': file_path.name,
                            'language': file_path.suffix[1:] if file_path.suffix else 'unknown'
                        }
                        
                        doc = generator.generate(
                            source_code=source_code,
                            template=template_obj.content,
                            context=context,
                            output_format=format
                        )
                        
                        results.append({
                            'file': str(file_path),
                            'documentation': doc,
                            'template': template,
                            'format': format
                        })
                        
                    except Exception as e:
                        errors.append((file_path, str(e)))
                        cli_ctx.log(f"Error processing {file_path}: {str(e)}", "error")
                        if cli_ctx.debug:
                            import traceback
                            traceback.print_exc()
        
        # Output results
        if output:
            output_path = Path(output)
            if batch:
                # Save batch results
                if format == 'json':
                    with open(output_path, 'w') as f:
                        json.dump(results, f, indent=2)
                else:
                    # Concatenate all documentation
                    all_docs = '\n\n---\n\n'.join([r['documentation'] for r in results])
                    with open(output_path, 'w') as f:
                        f.write(all_docs)
                cli_ctx.log(f"Documentation saved to {output_path}", "success")
            else:
                # Save single result
                with open(output_path, 'w') as f:
                    if format == 'json':
                        json.dump(results[0], f, indent=2)
                    else:
                        f.write(results[0]['documentation'])
                cli_ctx.log(f"Documentation saved to {output_path}", "success")
        else:
            # Output to stdout
            if cli_ctx.json_output or format == 'json':
                cli_ctx.output(results, format_type='json')
            else:
                for result in results:
                    if batch:
                        click.echo(f"\n{'='*60}")
                        click.echo(f"File: {result['file']}")
                        click.echo(f"{'='*60}\n")
                    click.echo(result['documentation'])
        
        cli_ctx.log(f"Successfully generated documentation for {len(results)} file(s)", "success")
        
    except Exception as e:
        cli_ctx.log(f"Generation failed: {str(e)}", "error")
        if cli_ctx.debug:
            import traceback
            traceback.print_exc()
        sys.exit(1)


@generate_group.command('api')
@click.argument('spec_file', type=click.Path(exists=True))
@click.option('--format', '-f', type=click.Choice(['openapi', 'swagger', 'postman']),
              default='openapi', help='API specification format')
@click.option('--output', '-o', type=click.Path(),
              help='Output directory for generated docs')
@click.pass_obj
def generate_api(cli_ctx, spec_file: str, format: str, output: Optional[str]):
    """
    Generate API documentation from specification files.
    
    Examples:
    
        # Generate from OpenAPI spec
        devdocai generate api openapi.yaml
        
        # Generate from Swagger spec
        devdocai generate api swagger.json --format swagger
    """
    cli_ctx.log(f"Generating API documentation from {spec_file}", "info")
    
    if not GENERATOR_AVAILABLE:
        cli_ctx.log("Document generator not available", "error")
        sys.exit(1)
    
    try:
        # Read specification file
        spec_path = Path(spec_file)
        spec_content = spec_path.read_text()
        
        # Parse based on format
        if spec_path.suffix in ['.yaml', '.yml']:
            import yaml
            spec_data = yaml.safe_load(spec_content)
        else:
            spec_data = json.loads(spec_content)
        
        # Initialize generator
        config = UnifiedGenerationConfig(mode=EngineMode.STANDARD)
        generator = UnifiedDocumentGenerator(config)
        
        # Generate documentation
        template_registry = TemplateRegistryUnified()
        api_template = template_registry.get_template('api-endpoint')
        
        if not api_template:
            cli_ctx.log("API template not found", "error")
            sys.exit(1)
        
        doc = generator.generate(
            source_code=spec_content,
            template=api_template.content,
            context={'spec': spec_data, 'format': format},
            output_format='markdown'
        )
        
        # Save or output
        if output:
            output_path = Path(output)
            output_path.mkdir(parents=True, exist_ok=True)
            doc_file = output_path / f"{spec_path.stem}_docs.md"
            doc_file.write_text(doc)
            cli_ctx.log(f"API documentation saved to {doc_file}", "success")
        else:
            click.echo(doc)
        
    except Exception as e:
        cli_ctx.log(f"API generation failed: {str(e)}", "error")
        if cli_ctx.debug:
            import traceback
            traceback.print_exc()
        sys.exit(1)


@generate_group.command('database')
@click.argument('connection_string')
@click.option('--tables', '-t', multiple=True,
              help='Specific tables to document (default: all)')
@click.option('--schema', '-s', help='Database schema to use')
@click.option('--output', '-o', type=click.Path(),
              help='Output file path')
@click.pass_obj
def generate_database(cli_ctx, connection_string: str, tables: List[str],
                      schema: Optional[str], output: Optional[str]):
    """
    Generate database documentation from schema.
    
    Examples:
    
        # Document all tables
        devdocai generate database "postgresql://localhost/mydb"
        
        # Document specific tables
        devdocai generate database "sqlite:///data.db" -t users -t posts
    """
    cli_ctx.log("Database documentation generation", "info")
    
    # This would integrate with database introspection tools
    # For now, show a placeholder implementation
    cli_ctx.log("Database documentation generation is planned for future release", "warning")
    
    # Placeholder output
    doc_structure = {
        'connection': connection_string,
        'tables': list(tables) if tables else ['all'],
        'schema': schema or 'default',
        'status': 'pending_implementation'
    }
    
    cli_ctx.output(doc_structure)