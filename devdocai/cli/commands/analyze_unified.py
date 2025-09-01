"""
Unified Analyze Command - Mode-based code analysis.

Provides unified analysis functionality with configurable behavior
based on operation mode.
"""

import time
from pathlib import Path
from typing import Dict, Any, List, Optional

import click

from devdocai.cli.config_unified import CLIConfig
from devdocai.quality import QualityAnalyzer
from devdocai.review import ReviewEngine


class UnifiedAnalyzeCommand:
    """Unified analyze command with mode-based behavior."""
    
    def __init__(self, config: CLIConfig):
        """Initialize with configuration."""
        self.config = config
        self.analyzer = QualityAnalyzer()
        self.reviewer = ReviewEngine()
        
        # Initialize mode-specific features
        if config.is_performance_enabled():
            self._init_performance_features()
        if config.is_security_enabled():
            self._init_security_features()
    
    def _init_performance_features(self):
        """Initialize performance features."""
        from functools import lru_cache
        if self.config.performance.enable_caching:
            self._cache = lru_cache(maxsize=self.config.performance.cache_size)
            self.analyze_cached = self._cache(self._analyze_impl)
    
    def _init_security_features(self):
        """Initialize security features."""
        if self.config.security.enable_validation:
            from devdocai.cli.utils.security import InputSanitizer
            self.sanitizer = InputSanitizer()
        if self.config.security.enable_audit:
            from devdocai.cli.utils.security import SecurityAuditLogger
            self.audit_logger = SecurityAuditLogger()
    
    def analyze(self, source_path: str, detailed: bool, metrics_only: bool,
                suggestions: bool) -> Dict[str, Any]:
        """Perform analysis with mode-based processing."""
        start_time = time.time()
        
        # Security validation
        if self.config.is_security_enabled() and hasattr(self, 'sanitizer'):
            self.sanitizer.sanitize_path(source_path)
        
        # Use cached analysis if available
        if (self.config.is_performance_enabled() and 
            hasattr(self, 'analyze_cached')):
            result = self.analyze_cached(source_path, detailed, metrics_only, suggestions)
        else:
            result = self._analyze_impl(source_path, detailed, metrics_only, suggestions)
        
        # Add timing
        result['analysis_time'] = time.time() - start_time
        
        # Audit if enabled
        if self.config.is_security_enabled() and hasattr(self, 'audit_logger'):
            self.audit_logger.log_event(
                event_type="ANALYSIS_COMPLETE",
                severity="INFO",
                details={'source': source_path, 'duration': result['analysis_time']}
            )
        
        return result
    
    def _analyze_impl(self, source_path: str, detailed: bool, metrics_only: bool,
                     suggestions: bool) -> Dict[str, Any]:
        """Core analysis implementation."""
        source = Path(source_path)
        
        if not source.exists():
            raise click.ClickException(f"Source path '{source_path}' does not exist")
        
        # Perform quality analysis
        quality_results = self.analyzer.analyze(str(source))
        
        # Perform review if not metrics-only
        review_results = {}
        if not metrics_only:
            review_results = self.reviewer.review(str(source))
        
        # Build result
        result = {
            'source': str(source),
            'quality': quality_results,
            'metrics': quality_results.get('metrics', {}),
        }
        
        if not metrics_only:
            result['review'] = review_results
        
        if suggestions:
            result['suggestions'] = self._generate_suggestions(quality_results, review_results)
        
        if detailed:
            result['details'] = {
                'file_count': quality_results.get('file_count', 0),
                'line_count': quality_results.get('line_count', 0),
                'issues': quality_results.get('issues', [])
            }
        
        return result
    
    def _generate_suggestions(self, quality: Dict, review: Dict) -> List[str]:
        """Generate improvement suggestions."""
        suggestions = []
        
        # Quality-based suggestions
        if quality.get('complexity', 0) > 10:
            suggestions.append("Consider refactoring complex functions")
        if quality.get('coverage', 100) < 80:
            suggestions.append("Increase test coverage to at least 80%")
        
        # Review-based suggestions
        if review.get('documentation_score', 100) < 70:
            suggestions.append("Improve documentation coverage")
        
        return suggestions


def create_command(config: CLIConfig) -> click.Command:
    """Factory function to create analyze command."""
    
    @click.command(name='analyze')
    @click.argument('source', type=click.Path(exists=True))
    @click.option('--detailed', '-d', is_flag=True, help='Show detailed analysis')
    @click.option('--metrics-only', is_flag=True, help='Show only metrics')
    @click.option('--suggestions', is_flag=True, help='Include improvement suggestions')
    @click.pass_obj
    def analyze_command(ctx, source: str, detailed: bool, metrics_only: bool,
                        suggestions: bool):
        """Analyze code quality and documentation."""
        try:
            command = UnifiedAnalyzeCommand(ctx.config)
            result = command.analyze(source, detailed, metrics_only, suggestions)
            
            # Format output
            if metrics_only:
                ctx.output(result['metrics'])
            else:
                ctx.output(result)
            
            # Log summary
            quality_score = result['quality'].get('overall_score', 0)
            ctx.log(f"Analysis complete. Quality score: {quality_score:.1f}/100", "info")
            
        except Exception as e:
            ctx.log(str(e), "error")
            raise click.ClickException(str(e))
    
    return analyze_command