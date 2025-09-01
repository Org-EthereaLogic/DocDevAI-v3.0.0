"""
Quality analysis commands for DevDocAI CLI.

Integrates with M005 Quality Engine module.
"""

import sys
from pathlib import Path
from typing import Optional, List, Dict, Any
import json

import click
from click import Context

# Import M005 Quality Engine
try:
    from devdocai.quality.analyzer_unified import QualityAnalyzerUnified
    from devdocai.quality.config_unified import QualityConfig, OperationMode
    from devdocai.quality.dimensions_unified import (
        CompletenessAnalyzer,
        ClarityAnalyzer,
        TechnicalAccuracyAnalyzer,
        MaintainabilityAnalyzer,
        UsabilityAnalyzer
    )
    ANALYZER_AVAILABLE = True
except ImportError as e:
    ANALYZER_AVAILABLE = False
    IMPORT_ERROR = str(e)


# Available quality dimensions
DIMENSIONS = {
    'completeness': 'Measures documentation coverage and thoroughness',
    'clarity': 'Evaluates readability and understandability',
    'technical_accuracy': 'Checks technical correctness and precision',
    'maintainability': 'Assesses ease of updating and maintaining',
    'usability': 'Evaluates user-friendliness and accessibility',
    'all': 'Analyze all dimensions'
}


@click.group('analyze', invoke_without_command=True)
@click.pass_context
def analyze_group(ctx: Context):
    """Analyze documentation quality and provide improvement suggestions."""
    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())


@analyze_group.command('document')
@click.argument('path', type=click.Path(exists=True))
@click.option('--dimensions', '-d', multiple=True,
              type=click.Choice(list(DIMENSIONS.keys())),
              default=['all'], help='Quality dimensions to analyze')
@click.option('--threshold', '-t', type=float, default=0.8,
              help='Quality threshold (0.0-1.0)')
@click.option('--detailed', is_flag=True,
              help='Show detailed analysis with suggestions')
@click.option('--output', '-o', type=click.Path(),
              help='Save analysis report to file')
@click.option('--format', '-f', 
              type=click.Choice(['text', 'json', 'html', 'markdown']),
              default='text', help='Output format for report')
@click.option('--mode', type=click.Choice(['basic', 'optimized', 'secure', 'balanced']),
              default='balanced', help='Operation mode')
@click.pass_obj
def analyze_document(cli_ctx, path: str, dimensions: List[str], threshold: float,
                      detailed: bool, output: Optional[str], format: str, mode: str):
    """
    Analyze documentation quality across multiple dimensions.
    
    Examples:
    
        # Analyze all dimensions
        devdocai analyze document README.md
        
        # Analyze specific dimensions
        devdocai analyze document api_docs.md -d clarity -d completeness
        
        # Generate detailed report
        devdocai analyze document docs/ --detailed --output report.html
    """
    if not ANALYZER_AVAILABLE:
        cli_ctx.log(f"Quality analyzer not available: {IMPORT_ERROR}", "error")
        sys.exit(1)
    
    try:
        # Initialize analyzer with selected mode
        op_mode = OperationMode[mode.upper()]
        config = QualityConfig(operation_mode=op_mode)
        analyzer = QualityAnalyzerUnified(config)
        
        # Read document content
        doc_path = Path(path)
        if doc_path.is_file():
            content = doc_path.read_text()
            documents = [{'path': str(doc_path), 'content': content}]
        else:
            # Process directory
            documents = []
            for file_path in doc_path.rglob('*.md'):
                content = file_path.read_text()
                documents.append({'path': str(file_path), 'content': content})
            
            if not documents:
                cli_ctx.log("No markdown files found in directory", "warning")
                return
        
        # Process dimensions
        if 'all' in dimensions:
            dimensions_to_analyze = ['completeness', 'clarity', 'technical_accuracy',
                                     'maintainability', 'usability']
        else:
            dimensions_to_analyze = list(dimensions)
        
        # Analyze documents
        all_results = []
        
        with click.progressbar(documents, label='Analyzing documents') as docs:
            for doc in docs:
                try:
                    # Perform analysis
                    result = analyzer.analyze(
                        content=doc['content'],
                        dimensions=dimensions_to_analyze
                    )
                    
                    # Add document path to result
                    result['document'] = doc['path']
                    
                    # Check threshold
                    overall_score = result.get('overall_score', 0)
                    result['passes_threshold'] = overall_score >= threshold
                    
                    # Add suggestions if detailed mode
                    if detailed:
                        suggestions = analyzer.get_suggestions(
                            content=doc['content'],
                            scores=result.get('dimension_scores', {})
                        )
                        result['suggestions'] = suggestions
                    
                    all_results.append(result)
                    
                except Exception as e:
                    cli_ctx.log(f"Error analyzing {doc['path']}: {str(e)}", "error")
                    if cli_ctx.debug:
                        import traceback
                        traceback.print_exc()
        
        # Format output
        if format == 'json' or cli_ctx.json_output:
            report = all_results
        elif format == 'html':
            report = _format_html_report(all_results, threshold)
        elif format == 'markdown':
            report = _format_markdown_report(all_results, threshold)
        else:
            report = _format_text_report(all_results, threshold, detailed)
        
        # Save or display report
        if output:
            output_path = Path(output)
            if format == 'json':
                with open(output_path, 'w') as f:
                    json.dump(report, f, indent=2)
            else:
                with open(output_path, 'w') as f:
                    f.write(report)
            cli_ctx.log(f"Analysis report saved to {output_path}", "success")
        else:
            if isinstance(report, str):
                click.echo(report)
            else:
                cli_ctx.output(report)
        
        # Summary statistics
        passed = sum(1 for r in all_results if r['passes_threshold'])
        total = len(all_results)
        cli_ctx.log(f"\nAnalysis complete: {passed}/{total} documents pass quality threshold", 
                   "success" if passed == total else "warning")
        
    except Exception as e:
        cli_ctx.log(f"Analysis failed: {str(e)}", "error")
        if cli_ctx.debug:
            import traceback
            traceback.print_exc()
        sys.exit(1)


@analyze_group.command('batch')
@click.argument('directory', type=click.Path(exists=True, file_okay=False))
@click.option('--pattern', '-p', default='*.md',
              help='File pattern to match')
@click.option('--recursive', '-r', is_flag=True,
              help='Process subdirectories recursively')
@click.option('--summary', is_flag=True,
              help='Show summary statistics only')
@click.option('--export', '-e', type=click.Path(),
              help='Export results to CSV file')
@click.pass_obj
def analyze_batch(cli_ctx, directory: str, pattern: str, recursive: bool,
                  summary: bool, export: Optional[str]):
    """
    Batch analyze multiple documents in a directory.
    
    Examples:
    
        # Analyze all markdown files
        devdocai analyze batch docs/
        
        # Analyze recursively with pattern
        devdocai analyze batch . --recursive --pattern "*.rst"
        
        # Export results to CSV
        devdocai analyze batch docs/ --export results.csv
    """
    if not ANALYZER_AVAILABLE:
        cli_ctx.log("Quality analyzer not available", "error")
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
        
        cli_ctx.log(f"Found {len(files)} files to analyze", "info")
        
        # Initialize analyzer
        config = QualityConfig(operation_mode=OperationMode.OPTIMIZED)
        analyzer = QualityAnalyzerUnified(config)
        
        # Analyze files
        results = []
        with click.progressbar(files, label='Analyzing files') as file_list:
            for file_path in file_list:
                try:
                    content = file_path.read_text()
                    result = analyzer.analyze(
                        content=content,
                        dimensions=['completeness', 'clarity', 'technical_accuracy']
                    )
                    
                    results.append({
                        'file': str(file_path.relative_to(dir_path)),
                        'overall_score': result.get('overall_score', 0),
                        'completeness': result.get('dimension_scores', {}).get('completeness', 0),
                        'clarity': result.get('dimension_scores', {}).get('clarity', 0),
                        'technical_accuracy': result.get('dimension_scores', {}).get('technical_accuracy', 0)
                    })
                except Exception as e:
                    cli_ctx.log(f"Error analyzing {file_path}: {str(e)}", "error")
        
        # Sort by score
        results.sort(key=lambda x: x['overall_score'], reverse=True)
        
        # Display or export results
        if export:
            # Export to CSV
            import csv
            with open(export, 'w', newline='') as f:
                if results:
                    writer = csv.DictWriter(f, fieldnames=results[0].keys())
                    writer.writeheader()
                    writer.writerows(results)
            cli_ctx.log(f"Results exported to {export}", "success")
        
        if summary:
            # Show summary statistics
            avg_score = sum(r['overall_score'] for r in results) / len(results)
            best = max(results, key=lambda x: x['overall_score'])
            worst = min(results, key=lambda x: x['overall_score'])
            
            summary_data = {
                'total_files': len(results),
                'average_score': f"{avg_score:.2f}",
                'best_document': f"{best['file']} ({best['overall_score']:.2f})",
                'worst_document': f"{worst['file']} ({worst['overall_score']:.2f})"
            }
            cli_ctx.output(summary_data)
        else:
            # Show detailed results
            cli_ctx.output(results)
            
    except Exception as e:
        cli_ctx.log(f"Batch analysis failed: {str(e)}", "error")
        if cli_ctx.debug:
            import traceback
            traceback.print_exc()
        sys.exit(1)


def _format_text_report(results: List[Dict], threshold: float, detailed: bool) -> str:
    """Format analysis results as text report."""
    lines = []
    lines.append("=" * 60)
    lines.append("Documentation Quality Analysis Report")
    lines.append("=" * 60)
    lines.append(f"Quality Threshold: {threshold:.1%}\n")
    
    for result in results:
        lines.append(f"\nDocument: {result['document']}")
        lines.append("-" * 40)
        
        overall = result.get('overall_score', 0)
        status = "✓ PASS" if result['passes_threshold'] else "✗ FAIL"
        lines.append(f"Overall Score: {overall:.1%} {status}")
        
        if 'dimension_scores' in result:
            lines.append("\nDimension Scores:")
            for dim, score in result['dimension_scores'].items():
                lines.append(f"  - {dim.replace('_', ' ').title()}: {score:.1%}")
        
        if detailed and 'suggestions' in result:
            lines.append("\nImprovement Suggestions:")
            for suggestion in result['suggestions']:
                lines.append(f"  • {suggestion}")
    
    return "\n".join(lines)


def _format_markdown_report(results: List[Dict], threshold: float) -> str:
    """Format analysis results as markdown report."""
    lines = []
    lines.append("# Documentation Quality Analysis Report\n")
    lines.append(f"**Quality Threshold:** {threshold:.1%}\n")
    
    for result in results:
        lines.append(f"## {result['document']}\n")
        
        overall = result.get('overall_score', 0)
        status = "✅" if result['passes_threshold'] else "❌"
        lines.append(f"**Overall Score:** {overall:.1%} {status}\n")
        
        if 'dimension_scores' in result:
            lines.append("### Dimension Scores\n")
            for dim, score in result['dimension_scores'].items():
                lines.append(f"- **{dim.replace('_', ' ').title()}:** {score:.1%}")
            lines.append("")
        
        if 'suggestions' in result.get('suggestions', []):
            lines.append("### Suggestions\n")
            for suggestion in result['suggestions']:
                lines.append(f"- {suggestion}")
            lines.append("")
    
    return "\n".join(lines)


def _format_html_report(results: List[Dict], threshold: float) -> str:
    """Format analysis results as HTML report."""
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Documentation Quality Report</title>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 20px; }}
            h1 {{ color: #333; }}
            .pass {{ color: green; }}
            .fail {{ color: red; }}
            .document {{ margin: 20px 0; padding: 15px; border: 1px solid #ddd; }}
            .score-bar {{ background: #f0f0f0; height: 20px; margin: 5px 0; }}
            .score-fill {{ background: #4CAF50; height: 100%; }}
        </style>
    </head>
    <body>
        <h1>Documentation Quality Analysis Report</h1>
        <p>Quality Threshold: {threshold:.1%}</p>
    """
    
    for result in results:
        overall = result.get('overall_score', 0)
        status_class = 'pass' if result['passes_threshold'] else 'fail'
        
        html += f"""
        <div class="document">
            <h2>{result['document']}</h2>
            <p class="{status_class}">Overall Score: {overall:.1%}</p>
            <div class="score-bar">
                <div class="score-fill" style="width: {overall*100}%"></div>
            </div>
        """
        
        if 'dimension_scores' in result:
            html += "<h3>Dimension Scores</h3><ul>"
            for dim, score in result['dimension_scores'].items():
                html += f"<li>{dim.replace('_', ' ').title()}: {score:.1%}</li>"
            html += "</ul>"
        
        html += "</div>"
    
    html += "</body></html>"
    return html