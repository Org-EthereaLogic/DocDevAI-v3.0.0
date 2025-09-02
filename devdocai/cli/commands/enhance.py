"""
Enhancement pipeline commands for DevDocAI CLI.

Integrates with M009 Enhancement Pipeline module.
"""

import sys
from pathlib import Path
from typing import Optional, List, Dict, Any
import json

import click
from click import Context

# Import M009 Enhancement Pipeline
try:
    from devdocai.enhancement.enhancement_unified import UnifiedEnhancementPipeline
    from devdocai.enhancement.config_unified import EnhancementConfig, OperationMode
    ENHANCEMENT_AVAILABLE = True
except ImportError as e:
    ENHANCEMENT_AVAILABLE = False
    IMPORT_ERROR = str(e)


# Available enhancement strategies
STRATEGIES = {
    'clarity': 'Improve readability and understandability',
    'completeness': 'Add missing information and details',
    'technical_accuracy': 'Enhance technical precision and correctness',
    'consistency': 'Ensure consistent terminology and style',
    'examples': 'Add practical examples and use cases',
    'all': 'Apply all enhancement strategies'
}


@click.group('enhance', invoke_without_command=True)
@click.pass_context
def enhance_group(ctx: Context):
    """Enhance documentation using AI-powered strategies."""
    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())


@enhance_group.command('document')
@click.argument('path', type=click.Path(exists=True))
@click.option('--strategy', '-s', multiple=True,
              type=click.Choice(list(STRATEGIES.keys())),
              default=['all'], help='Enhancement strategies to apply')
@click.option('--iterations', '-i', type=int, default=1,
              help='Number of enhancement iterations (1-5)')
@click.option('--threshold', '-t', type=float, default=0.85,
              help='Quality threshold to stop iterations (0.0-1.0)')
@click.option('--output', '-o', type=click.Path(),
              help='Output file path (default: overwrites input)')
@click.option('--backup', '-b', is_flag=True,
              help='Create backup of original file')
@click.option('--mode', type=click.Choice(['basic', 'performance', 'secure', 'enterprise']),
              default='performance', help='Operation mode')
@click.option('--dry-run', is_flag=True,
              help='Preview changes without applying them')
@click.pass_obj
def enhance_document(cli_ctx, path: str, strategy: List[str], iterations: int,
                      threshold: float, output: Optional[str], backup: bool,
                      mode: str, dry_run: bool):
    """
    Enhance documentation using AI-powered strategies.
    
    Examples:
    
        # Enhance with all strategies
        devdocai enhance document README.md
        
        # Specific strategies with iterations
        devdocai enhance document api_docs.md -s clarity -s examples -i 3
        
        # Enhance until quality threshold
        devdocai enhance document docs.md --threshold 0.9
        
        # Preview changes without applying
        devdocai enhance document README.md --dry-run
    """
    if not ENHANCEMENT_AVAILABLE:
        cli_ctx.log(f"Enhancement pipeline not available: {IMPORT_ERROR}", "error")
        sys.exit(1)
    
    # Validate iterations
    if not 1 <= iterations <= 5:
        cli_ctx.log("Iterations must be between 1 and 5", "error")
        sys.exit(1)
    
    try:
        # Initialize enhancement pipeline
        op_mode = OperationMode[mode.upper()]
        config = EnhancementConfig(
            operation_mode=op_mode,
            max_iterations=iterations,
            quality_threshold=threshold
        )
        pipeline = UnifiedEnhancementPipeline(config)
        
        # Read document
        doc_path = Path(path)
        original_content = doc_path.read_text()
        
        # Create backup if requested
        if backup and not dry_run:
            backup_path = doc_path.with_suffix(doc_path.suffix + '.bak')
            backup_path.write_text(original_content)
            cli_ctx.log(f"Backup created: {backup_path}", "info")
        
        # Process strategies
        if 'all' in strategy:
            strategies_to_apply = ['clarity', 'completeness', 'technical_accuracy',
                                   'consistency', 'examples']
        else:
            strategies_to_apply = list(strategy)
        
        cli_ctx.log(f"Applying strategies: {', '.join(strategies_to_apply)}", "info")
        
        # Enhance document
        enhanced_content = original_content
        history = []
        
        for iteration in range(1, iterations + 1):
            cli_ctx.log(f"Enhancement iteration {iteration}/{iterations}", "info")
            
            with click.progressbar(strategies_to_apply, 
                                   label=f'Iteration {iteration}') as strats:
                for strat in strats:
                    try:
                        # Apply enhancement
                        result = pipeline.enhance(
                            content=enhanced_content,
                            strategy=strat
                        )
                        
                        if result and result.get('enhanced_content'):
                            enhanced_content = result['enhanced_content']
                            
                            # Track changes
                            history.append({
                                'iteration': iteration,
                                'strategy': strat,
                                'quality_before': result.get('quality_before', 0),
                                'quality_after': result.get('quality_after', 0),
                                'changes': result.get('changes_made', [])
                            })
                            
                    except Exception as e:
                        cli_ctx.log(f"Error applying strategy '{strat}': {str(e)}", "warning")
            
            # Check quality threshold
            if pipeline.check_quality(enhanced_content) >= threshold:
                cli_ctx.log(f"Quality threshold {threshold:.1%} reached", "success")
                break
        
        # Show changes summary
        if history:
            cli_ctx.log("\nEnhancement Summary:", "info")
            for entry in history[-5:]:  # Show last 5 changes
                improvement = entry['quality_after'] - entry['quality_before']
                click.echo(f"  - {entry['strategy']}: +{improvement:.1%} quality improvement")
        
        # Preview or apply changes
        if dry_run:
            cli_ctx.log("\nDry run - changes not applied", "warning")
            cli_ctx.log("Preview of enhanced content:", "info")
            
            # Show diff-like preview (first 50 lines)
            preview_lines = enhanced_content.split('\n')[:50]
            for line in preview_lines:
                click.echo(f"  {line}")
            
            if len(enhanced_content.split('\n')) > 50:
                click.echo("  ... (truncated)")
                
        else:
            # Save enhanced content
            if output:
                output_path = Path(output)
            else:
                output_path = doc_path
            
            output_path.write_text(enhanced_content)
            cli_ctx.log(f"Enhanced documentation saved to {output_path}", "success")
            
            # Calculate improvement
            original_lines = len(original_content.split('\n'))
            enhanced_lines = len(enhanced_content.split('\n'))
            line_diff = enhanced_lines - original_lines
            
            cli_ctx.log(f"Lines: {original_lines} → {enhanced_lines} ({line_diff:+d})", "info")
        
    except Exception as e:
        cli_ctx.log(f"Enhancement failed: {str(e)}", "error")
        if cli_ctx.debug:
            import traceback
            traceback.print_exc()
        sys.exit(1)


@enhance_group.command('batch')
@click.argument('directory', type=click.Path(exists=True, file_okay=False))
@click.option('--pattern', '-p', default='*.md',
              help='File pattern to match')
@click.option('--recursive', '-r', is_flag=True,
              help='Process subdirectories recursively')
@click.option('--strategy', '-s', type=click.Choice(list(STRATEGIES.keys())),
              default='all', help='Enhancement strategy')
@click.option('--parallel', '-P', type=int, default=1,
              help='Number of parallel workers (1-4)')
@click.option('--report', type=click.Path(),
              help='Save enhancement report to file')
@click.pass_obj
def enhance_batch(cli_ctx, directory: str, pattern: str, recursive: bool,
                  strategy: str, parallel: int, report: Optional[str]):
    """
    Batch enhance multiple documents.
    
    Examples:
    
        # Enhance all markdown files
        devdocai enhance batch docs/
        
        # Recursive with specific strategy
        devdocai enhance batch . -r --strategy clarity
        
        # Parallel processing with report
        devdocai enhance batch docs/ --parallel 4 --report enhancement.json
    """
    if not ENHANCEMENT_AVAILABLE:
        cli_ctx.log("Enhancement pipeline not available", "error")
        sys.exit(1)
    
    # Validate parallel workers
    if not 1 <= parallel <= 4:
        cli_ctx.log("Parallel workers must be between 1 and 4", "error")
        sys.exit(1)
    
    try:
        dir_path = Path(directory)
        
        # Find files
        if recursive:
            files = list(dir_path.rglob(pattern))
        else:
            files = list(dir_path.glob(pattern))
        
        if not files:
            cli_ctx.log(f"No files matching '{pattern}' found", "warning")
            return
        
        cli_ctx.log(f"Found {len(files)} files to enhance", "info")
        
        # Initialize pipeline
        config = EnhancementConfig(
            operation_mode=OperationMode.PERFORMANCE,
            enable_caching=True
        )
        pipeline = UnifiedEnhancementPipeline(config)
        
        # Process files
        results = []
        errors = []
        
        with click.progressbar(files, label='Enhancing documents') as file_list:
            for file_path in file_list:
                try:
                    # Read content
                    content = file_path.read_text()
                    
                    # Apply enhancement
                    if strategy == 'all':
                        strategies = ['clarity', 'completeness', 'technical_accuracy']
                    else:
                        strategies = [strategy]
                    
                    enhanced = content
                    improvements = []
                    
                    for strat in strategies:
                        result = pipeline.enhance(content=enhanced, strategy=strat)
                        if result and result.get('enhanced_content'):
                            enhanced = result['enhanced_content']
                            improvements.append({
                                'strategy': strat,
                                'improvement': result.get('quality_after', 0) - 
                                              result.get('quality_before', 0)
                            })
                    
                    # Save enhanced content
                    file_path.write_text(enhanced)
                    
                    results.append({
                        'file': str(file_path.relative_to(dir_path)),
                        'status': 'success',
                        'improvements': improvements,
                        'size_before': len(content),
                        'size_after': len(enhanced)
                    })
                    
                except Exception as e:
                    errors.append({
                        'file': str(file_path.relative_to(dir_path)),
                        'error': str(e)
                    })
        
        # Generate report
        report_data = {
            'total_files': len(files),
            'successful': len(results),
            'failed': len(errors),
            'results': results,
            'errors': errors
        }
        
        if report:
            # Save report
            report_path = Path(report)
            if report_path.suffix == '.json':
                with open(report_path, 'w') as f:
                    json.dump(report_data, f, indent=2)
            else:
                # Text report
                with open(report_path, 'w') as f:
                    f.write("Enhancement Batch Report\n")
                    f.write("=" * 60 + "\n")
                    f.write(f"Total files: {report_data['total_files']}\n")
                    f.write(f"Successful: {report_data['successful']}\n")
                    f.write(f"Failed: {report_data['failed']}\n\n")
                    
                    for result in results:
                        f.write(f"\n{result['file']}:\n")
                        for imp in result['improvements']:
                            f.write(f"  - {imp['strategy']}: +{imp['improvement']:.1%}\n")
            
            cli_ctx.log(f"Report saved to {report_path}", "success")
        
        # Display summary
        cli_ctx.log(f"\nEnhancement complete: {len(results)}/{len(files)} successful", 
                   "success" if not errors else "warning")
        
        if errors:
            cli_ctx.log(f"{len(errors)} files failed:", "error")
            for error in errors[:5]:  # Show first 5 errors
                click.echo(f"  - {error['file']}: {error['error']}")
            
    except Exception as e:
        cli_ctx.log(f"Batch enhancement failed: {str(e)}", "error")
        if cli_ctx.debug:
            import traceback
            traceback.print_exc()
        sys.exit(1)


@enhance_group.command('pipeline')
@click.option('--list', 'list_pipelines', is_flag=True,
              help='List available enhancement pipelines')
@click.option('--create', help='Create custom pipeline configuration')
@click.option('--apply', help='Apply pipeline configuration to documents')
@click.pass_obj
def enhance_pipeline(cli_ctx, list_pipelines: bool, create: Optional[str],
                      apply: Optional[str]):
    """
    Manage enhancement pipeline configurations.
    
    Examples:
    
        # List available pipelines
        devdocai enhance pipeline --list
        
        # Create custom pipeline
        devdocai enhance pipeline --create my-pipeline
        
        # Apply pipeline
        devdocai enhance pipeline --apply my-pipeline
    """
    if not ENHANCEMENT_AVAILABLE:
        cli_ctx.log("Enhancement pipeline not available", "error")
        sys.exit(1)
    
    if list_pipelines:
        # List predefined pipelines
        pipelines = {
            'standard': {
                'description': 'Standard enhancement pipeline',
                'strategies': ['clarity', 'completeness'],
                'iterations': 2
            },
            'comprehensive': {
                'description': 'Comprehensive enhancement with all strategies',
                'strategies': ['clarity', 'completeness', 'technical_accuracy', 
                              'consistency', 'examples'],
                'iterations': 3
            },
            'quick': {
                'description': 'Quick single-pass enhancement',
                'strategies': ['clarity'],
                'iterations': 1
            },
            'technical': {
                'description': 'Technical documentation enhancement',
                'strategies': ['technical_accuracy', 'examples'],
                'iterations': 2
            }
        }
        
        cli_ctx.log("Available Enhancement Pipelines:", "info")
        for name, config in pipelines.items():
            click.echo(f"\n{name}:")
            click.echo(f"  Description: {config['description']}")
            click.echo(f"  Strategies: {', '.join(config['strategies'])}")
            click.echo(f"  Iterations: {config['iterations']}")
    
    elif create:
        cli_ctx.log(f"Creating pipeline configuration: {create}", "info")
        
        # Interactive pipeline creation
        click.echo("Define your enhancement pipeline:")
        
        # Select strategies
        click.echo("\nAvailable strategies:")
        for key, desc in STRATEGIES.items():
            if key != 'all':
                click.echo(f"  - {key}: {desc}")
        
        selected = click.prompt("Select strategies (comma-separated)", 
                                default="clarity,completeness")
        strategies = [s.strip() for s in selected.split(',')]
        
        # Set iterations
        iterations = click.prompt("Number of iterations", type=int, default=2)
        
        # Set threshold
        threshold = click.prompt("Quality threshold", type=float, default=0.85)
        
        # Create configuration
        pipeline_config = {
            'name': create,
            'strategies': strategies,
            'iterations': iterations,
            'threshold': threshold,
            'created': str(Path.cwd())
        }
        
        # Save configuration
        config_path = Path.home() / '.devdocai' / 'pipelines' / f'{create}.json'
        config_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(config_path, 'w') as f:
            json.dump(pipeline_config, f, indent=2)
        
        cli_ctx.log(f"Pipeline configuration saved to {config_path}", "success")
    
    elif apply:
        cli_ctx.log(f"Applying pipeline: {apply}", "info")
        cli_ctx.log("Pipeline application is planned for future release", "warning")
    
    else:
        click.echo(ctx.get_help())