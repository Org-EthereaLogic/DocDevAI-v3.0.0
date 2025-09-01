"""
Unified Enhance Command - Documentation enhancement.
"""

from pathlib import Path
from typing import Optional

import click

from devdocai.cli.config_unified import CLIConfig
from devdocai.enhancement import EnhancementPipeline


def create_command(config: CLIConfig) -> click.Command:
    """Factory function to create enhance command."""
    
    @click.command(name='enhance')
    @click.argument('source', type=click.Path(exists=True))
    @click.option('--strategy', '-s', 
                  type=click.Choice(['clarity', 'completeness', 'examples', 'all']),
                  default='all', help='Enhancement strategy')
    @click.option('--output', '-o', type=click.Path(), help='Output file path')
    @click.option('--llm-provider', type=click.Choice(['openai', 'anthropic', 'local']),
                  help='LLM provider for enhancement')
    @click.pass_obj
    def enhance_command(ctx, source: str, strategy: str, output: Optional[str],
                        llm_provider: Optional[str]):
        """Enhance existing documentation with AI."""
        try:
            # Create pipeline with appropriate mode
            if ctx.config.mode.value == 'enterprise':
                mode = 'ENTERPRISE'
            elif ctx.config.is_security_enabled():
                mode = 'SECURE'
            elif ctx.config.is_performance_enabled():
                mode = 'PERFORMANCE'
            else:
                mode = 'BASIC'
            
            pipeline = EnhancementPipeline(operation_mode=mode)
            
            # Read source documentation
            source_path = Path(source)
            if not source_path.exists():
                raise click.ClickException(f"Source file not found: {source}")
            
            content = source_path.read_text()
            
            # Enhance documentation
            ctx.log(f"Enhancing documentation with {strategy} strategy...", "info")
            
            if strategy == 'all':
                enhanced = pipeline.enhance(content)
            else:
                enhanced = pipeline.enhance_with_strategy(content, strategy)
            
            # Write output
            if output:
                output_path = Path(output)
                output_path.parent.mkdir(parents=True, exist_ok=True)
                output_path.write_text(enhanced['content'])
                ctx.log(f"Enhanced documentation written to: {output}", "success")
            else:
                ctx.output(enhanced)
            
            # Show metrics
            if enhanced.get('metrics'):
                ctx.log(f"Quality improvement: {enhanced['metrics'].get('improvement', 0):.1f}%", "info")
            
        except Exception as e:
            ctx.log(str(e), "error")
            raise click.ClickException(str(e))
    
    return enhance_command