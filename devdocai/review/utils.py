"""
Utility functions and classes for M007 Review Engine.

Common utilities extracted from the unified implementation to reduce duplication
and provide shared functionality across all operation modes.
"""

import re
import json
import hashlib
import logging
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
from pathlib import Path

from .models import (
    ReviewResult,
    ReviewSeverity,
    ReviewIssue,
    DimensionResult,
    ReviewStatus
)

logger = logging.getLogger(__name__)


class ReportGenerator:
    """Unified report generator for all output formats."""
    
    @staticmethod
    def generate_markdown_report(result: ReviewResult, mode: str = "unknown") -> str:
        """Generate comprehensive markdown report."""
        lines = [
            f"# Document Review Report",
            f"",
            f"**Document ID:** {result.document_id}",
            f"**Document Type:** {result.document_type}",
            f"**Review ID:** {result.review_id}",
            f"**Operation Mode:** {mode.upper()}",
            f"**Timestamp:** {result.timestamp.isoformat()}",
            f"",
            f"## Overall Assessment",
            f"",
            f"- **Status:** {result.status.value.upper()}",
            f"- **Overall Score:** {result.overall_score:.1f}/100",
            f"- **Total Issues:** {result.metrics.total_issues}",
            f"- **Execution Time:** {result.metrics.execution_time_ms:.1f}ms",
            f"",
            f"## Dimension Analysis",
            f""
        ]
        
        for dim_result in result.dimension_results:
            lines.extend([
                f"### {dim_result.dimension.value.replace('_', ' ').title()}",
                f"",
                f"- **Score:** {dim_result.score:.1f}/100 (Weight: {dim_result.weight:.2f})",
                f"- **Checks:** {dim_result.passed_checks}/{dim_result.total_checks} passed",
                f"- **Issues:** {len(dim_result.issues)}",
                f"- **Execution Time:** {dim_result.execution_time_ms:.1f}ms",
                f""
            ])
            
            if dim_result.issues:
                lines.append("#### Issues:")
                for issue in dim_result.issues[:5]:  # Top 5 issues
                    lines.extend([
                        f"",
                        f"**[{issue.severity.value.upper()}]** {issue.title}",
                        f"",
                        f"{issue.description}",
                    ])
                    
                    if issue.location:
                        lines.append(f"*Location:* {issue.location}")
                    
                    if issue.suggestion:
                        lines.append(f"*Suggestion:* {issue.suggestion}")
                    
                    if issue.code_snippet:
                        lines.extend([
                            f"",
                            f"```",
                            f"{issue.code_snippet[:200]}...",
                            f"```"
                        ])
                    
                    lines.append("")
                
                if len(dim_result.issues) > 5:
                    lines.append(f"*... and {len(dim_result.issues) - 5} more issues*")
            
            lines.append("")
        
        # Issue Summary
        lines.extend([
            f"## Issue Summary by Severity",
            f""
        ])
        
        for severity, count in result.metrics.issues_by_severity.items():
            if count > 0:
                emoji = {
                    'blocker': '🚨',
                    'critical': '❌', 
                    'high': '⚠️',
                    'medium': '⚡',
                    'low': '💡',
                    'info': 'ℹ️'
                }.get(severity, '•')
                lines.append(f"- {emoji} **{severity.upper()}**: {count}")
        
        lines.append("")
        
        # Recommendations
        if result.recommended_actions:
            lines.extend([
                f"## Recommended Actions",
                f""
            ])
            for i, action in enumerate(result.recommended_actions, 1):
                lines.append(f"{i}. {action}")
            lines.append("")
        
        # Approval Conditions
        if result.approval_conditions:
            lines.extend([
                f"## Approval Conditions",
                f""
            ])
            for i, condition in enumerate(result.approval_conditions, 1):
                lines.append(f"{i}. {condition}")
            lines.append("")
        
        # Reviewer Notes
        if result.reviewer_notes:
            lines.extend([
                f"## Reviewer Notes",
                f"",
                result.reviewer_notes,
                f""
            ])
        
        # Performance Metrics
        lines.extend([
            f"## Performance Metrics",
            f"",
            f"- **Total Execution Time:** {result.metrics.execution_time_ms:.1f}ms",
            f"- **Total Checks Performed:** {result.metrics.total_checks_performed}",
            f"- **Overall Pass Rate:** {result.metrics.overall_pass_rate:.1f}%",
            f"- **Auto-fixable Issues:** {result.metrics.auto_fixable_count} ({result.metrics.auto_fix_rate:.1f}%)",
            f""
        ])
        
        if 'cache_hit_rate' in result.metadata:
            lines.append(f"- **Cache Hit Rate:** {result.metadata['cache_hit_rate']*100:.1f}%")
        
        return "\n".join(lines)
    
    @staticmethod  
    def generate_html_report(result: ReviewResult, mode: str = "unknown") -> str:
        """Generate comprehensive HTML report."""
        severity_colors = {
            'blocker': '#dc3545',
            'critical': '#fd7e14',
            'high': '#ffc107',
            'medium': '#28a745',
            'low': '#17a2b8',
            'info': '#6c757d'
        }
        
        status_color = {
            'approved': '#28a745',
            'approved_with_conditions': '#ffc107',
            'needs_revision': '#fd7e14',
            'rejected': '#dc3545',
            'pending': '#6c757d',
            'in_progress': '#17a2b8'
        }.get(result.status.value, '#6c757d')
        
        html = f"""
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Review Report - {result.document_id}</title>
            <style>
                body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; margin: 20px; line-height: 1.6; }}
                .header {{ border-bottom: 2px solid #e9ecef; padding-bottom: 20px; margin-bottom: 30px; }}
                .status {{ padding: 8px 16px; border-radius: 4px; color: white; font-weight: bold; display: inline-block; background: {status_color}; }}
                .score {{ font-size: 2.5em; font-weight: bold; color: {status_color}; margin: 20px 0; }}
                .dimensions {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; margin: 30px 0; }}
                .dimension {{ border: 1px solid #dee2e6; border-radius: 8px; padding: 20px; }}
                .dimension-header {{ font-size: 1.2em; font-weight: bold; margin-bottom: 15px; color: #495057; }}
                .score-bar {{ width: 100%; height: 20px; background: #e9ecef; border-radius: 10px; overflow: hidden; margin: 10px 0; }}
                .score-fill {{ height: 100%; background: linear-gradient(90deg, #dc3545 0%, #ffc107 50%, #28a745 100%); transition: width 0.3s ease; }}
                .issues {{ margin-top: 20px; }}
                .issue {{ margin: 15px 0; padding: 15px; border-left: 4px solid; border-radius: 0 4px 4px 0; }}
                .issue-title {{ font-weight: bold; margin-bottom: 8px; }}
                .issue-description {{ margin-bottom: 10px; }}
                .issue-meta {{ font-size: 0.9em; color: #6c757d; }}
                .summary {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin: 30px 0; }}
                .summary-card {{ text-align: center; padding: 20px; border: 1px solid #dee2e6; border-radius: 8px; }}
                .summary-number {{ font-size: 2em; font-weight: bold; }}
                .recommendations {{ background: #f8f9fa; padding: 20px; border-radius: 8px; margin: 20px 0; }}
                .code-snippet {{ background: #f8f9fa; border: 1px solid #e9ecef; border-radius: 4px; padding: 10px; font-family: 'Monaco', 'Consolas', monospace; font-size: 0.9em; margin: 10px 0; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>📋 Document Review Report</h1>
                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; margin: 20px 0;">
                    <div><strong>Document ID:</strong> {result.document_id}</div>
                    <div><strong>Mode:</strong> {mode.upper()}</div>
                    <div><strong>Type:</strong> {result.document_type}</div>
                    <div><strong>Review ID:</strong> {result.review_id}</div>
                </div>
                <div style="margin: 20px 0;">
                    <div class="status">{result.status.value.upper()}</div>
                    <div class="score">{result.overall_score:.1f}/100</div>
                </div>
            </div>
            
            <div class="summary">
                <div class="summary-card">
                    <div class="summary-number" style="color: {severity_colors.get('critical', '#6c757d')}">{result.metrics.total_issues}</div>
                    <div>Total Issues</div>
                </div>
                <div class="summary-card">
                    <div class="summary-number" style="color: {severity_colors.get('high', '#6c757d')}">{result.metrics.execution_time_ms:.0f}ms</div>
                    <div>Execution Time</div>
                </div>
                <div class="summary-card">
                    <div class="summary-number" style="color: #28a745;">{result.metrics.overall_pass_rate:.1f}%</div>
                    <div>Pass Rate</div>
                </div>
                <div class="summary-card">
                    <div class="summary-number" style="color: #17a2b8;">{result.metrics.auto_fixable_count}</div>
                    <div>Auto-fixable</div>
                </div>
            </div>
            
            <h2>📊 Dimension Analysis</h2>
            <div class="dimensions">
        """
        
        for dim_result in result.dimension_results:
            score_percentage = dim_result.score
            fill_width = min(100, max(0, score_percentage))
            
            html += f"""
                <div class="dimension">
                    <div class="dimension-header">{dim_result.dimension.value.replace('_', ' ').title()}</div>
                    <div class="score-bar">
                        <div class="score-fill" style="width: {fill_width}%"></div>
                    </div>
                    <div style="margin: 10px 0;">
                        <strong>{dim_result.score:.1f}/100</strong> 
                        (Weight: {dim_result.weight:.2f}, Issues: {len(dim_result.issues)})
                    </div>
                    <div style="font-size: 0.9em; color: #6c757d;">
                        Checks: {dim_result.passed_checks}/{dim_result.total_checks} passed
                        ({dim_result.pass_rate:.1f}%)
                    </div>
            """
            
            if dim_result.issues:
                html += '<div class="issues">'
                for issue in dim_result.issues[:3]:  # Top 3 issues
                    issue_color = severity_colors.get(issue.severity.value, '#6c757d')
                    html += f"""
                        <div class="issue" style="border-left-color: {issue_color}; background: {issue_color}15;">
                            <div class="issue-title" style="color: {issue_color};">
                                [{issue.severity.value.upper()}] {issue.title}
                            </div>
                            <div class="issue-description">{issue.description}</div>
                    """
                    
                    if issue.location:
                        html += f'<div class="issue-meta">📍 Location: {issue.location}</div>'
                    
                    if issue.suggestion:
                        html += f'<div class="issue-meta">💡 Suggestion: {issue.suggestion}</div>'
                    
                    if issue.code_snippet:
                        snippet = issue.code_snippet[:200]
                        html += f'<div class="code-snippet">{snippet}...</div>'
                    
                    html += '</div>'
                
                if len(dim_result.issues) > 3:
                    html += f'<div style="text-align: center; color: #6c757d; font-style: italic;">... and {len(dim_result.issues) - 3} more issues</div>'
                
                html += '</div>'
            
            html += '</div>'
        
        html += """
            </div>
            
            <h2>📈 Issue Breakdown</h2>
            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 15px; margin: 20px 0;">
        """
        
        for severity, count in result.metrics.issues_by_severity.items():
            if count > 0:
                color = severity_colors.get(severity, '#6c757d')
                html += f"""
                    <div style="text-align: center; padding: 15px; border: 2px solid {color}; border-radius: 8px; background: {color}15;">
                        <div style="font-size: 1.5em; font-weight: bold; color: {color};">{count}</div>
                        <div style="color: {color}; font-weight: bold;">{severity.upper()}</div>
                    </div>
                """
        
        html += "</div>"
        
        # Recommendations
        if result.recommended_actions:
            html += """
                <div class="recommendations">
                    <h3>🎯 Recommended Actions</h3>
                    <ol style="margin: 0; padding-left: 20px;">
            """
            for action in result.recommended_actions:
                html += f"<li style='margin: 10px 0;'>{action}</li>"
            html += "</ol></div>"
        
        # Approval Conditions
        if result.approval_conditions:
            html += """
                <div style="background: #fff3cd; border: 1px solid #ffeaa7; padding: 20px; border-radius: 8px; margin: 20px 0;">
                    <h3 style="color: #856404;">⚠️ Approval Conditions</h3>
                    <ol style="margin: 0; padding-left: 20px;">
            """
            for condition in result.approval_conditions:
                html += f"<li style='margin: 10px 0; color: #856404;'>{condition}</li>"
            html += "</ol></div>"
        
        # Footer
        html += f"""
            <div style="margin-top: 50px; padding-top: 20px; border-top: 1px solid #dee2e6; text-align: center; color: #6c757d; font-size: 0.9em;">
                Generated on {result.timestamp.strftime('%Y-%m-%d at %H:%M:%S')} • 
                M007 Review Engine ({mode.upper()} mode)
            </div>
            
        </body>
        </html>
        """
        
        return html
    
    @staticmethod
    def generate_json_report(result: ReviewResult) -> str:
        """Generate JSON format report."""
        return json.dumps(result.to_dict(), indent=2, default=str)
    
    @staticmethod
    def generate_summary_report(result: ReviewResult) -> str:
        """Generate concise text summary."""
        return result.to_summary()


class ValidationUtils:
    """Common validation utilities."""
    
    @staticmethod
    def validate_content_size(content: str, mode: str) -> Tuple[bool, Optional[str]]:
        """Validate content size based on mode."""
        max_sizes = {
            'basic': 1024 * 1024,  # 1MB
            'optimized': 5 * 1024 * 1024,  # 5MB
            'secure': 2 * 1024 * 1024,  # 2MB
            'enterprise': 10 * 1024 * 1024,  # 10MB
        }
        
        max_size = max_sizes.get(mode.lower(), 1024 * 1024)
        if len(content) > max_size:
            return False, f"Content size ({len(content)} bytes) exceeds limit for {mode} mode ({max_size} bytes)"
        
        return True, None
    
    @staticmethod
    def validate_document_type(doc_type: str) -> Tuple[bool, Optional[str]]:
        """Validate document type."""
        allowed_types = {
            'readme', 'api', 'guide', 'changelog', 'documentation',
            'tutorial', 'specification', 'manual', 'reference', 'generic'
        }
        
        if doc_type.lower() not in allowed_types:
            return False, f"Unsupported document type: {doc_type}"
        
        return True, None
    
    @staticmethod
    def sanitize_filename(filename: str) -> str:
        """Sanitize filename for safe file operations."""
        # Remove/replace dangerous characters
        sanitized = re.sub(r'[<>:"/\\|?*]', '_', filename)
        sanitized = re.sub(r'[^\w\-_\. ]', '', sanitized)
        sanitized = sanitized.strip('.')  # Remove leading/trailing dots
        
        # Limit length
        if len(sanitized) > 255:
            name, ext = Path(sanitized).stem, Path(sanitized).suffix
            sanitized = name[:250 - len(ext)] + ext
        
        return sanitized or "document"
    
    @staticmethod
    def extract_metadata_from_content(content: str) -> Dict[str, Any]:
        """Extract metadata from document content."""
        metadata = {}
        
        # Extract title (first header)
        title_match = re.search(r'^#\s+(.+)$', content, re.MULTILINE)
        if title_match:
            metadata['title'] = title_match.group(1).strip()
        
        # Count various elements
        metadata.update({
            'line_count': len(content.splitlines()),
            'word_count': len(content.split()),
            'char_count': len(content),
            'header_count': len(re.findall(r'^#{1,6}\s+', content, re.MULTILINE)),
            'code_block_count': len(re.findall(r'```', content)) // 2,
            'link_count': len(re.findall(r'\[([^\]]+)\]\(([^)]+)\)', content)),
            'image_count': len(re.findall(r'!\[([^\]]*)\]\(([^)]+)\)', content)),
        })
        
        # Detect language
        if '```python' in content or 'def ' in content or 'import ' in content:
            metadata['primary_language'] = 'python'
        elif '```javascript' in content or '```js' in content or 'function ' in content:
            metadata['primary_language'] = 'javascript'
        elif '```java' in content or 'public class' in content:
            metadata['primary_language'] = 'java'
        elif '```go' in content or 'func ' in content or 'package main' in content:
            metadata['primary_language'] = 'go'
        else:
            metadata['primary_language'] = 'unknown'
        
        return metadata


class MetricsCalculator:
    """Utilities for calculating review metrics."""
    
    @staticmethod
    def calculate_complexity_score(content: str) -> float:
        """Calculate content complexity score (0-100)."""
        # Basic complexity heuristics
        lines = content.splitlines()
        
        factors = {
            'line_count': min(100, len(lines)) / 100 * 20,  # Max 20 points for length
            'avg_line_length': min(100, sum(len(line) for line in lines) / max(len(lines), 1)) / 100 * 15,
            'nesting_depth': min(10, max(line.count('\t') + line.count('    ') // 4 for line in lines)) / 10 * 15,
            'code_blocks': min(10, len(re.findall(r'```', content)) // 2) / 10 * 20,
            'technical_terms': len(re.findall(r'\b(?:function|class|method|algorithm|implementation|architecture)\b', content, re.IGNORECASE)) / max(len(content.split()), 1) * 100 * 10,
            'link_density': len(re.findall(r'\[([^\]]+)\]\(([^)]+)\)', content)) / max(len(lines), 1) * 20
        }
        
        return min(100, sum(factors.values()))
    
    @staticmethod
    def calculate_readability_score(content: str) -> float:
        """Calculate readability score (0-100, higher is better)."""
        words = content.split()
        sentences = re.split(r'[.!?]+', content)
        sentences = [s.strip() for s in sentences if s.strip()]
        
        if not words or not sentences:
            return 0
        
        # Simple readability metrics
        avg_words_per_sentence = len(words) / len(sentences)
        avg_chars_per_word = sum(len(word) for word in words) / len(words)
        
        # Readability score (inverted complexity)
        score = 100
        
        # Penalize long sentences
        if avg_words_per_sentence > 20:
            score -= (avg_words_per_sentence - 20) * 2
        
        # Penalize long words
        if avg_chars_per_word > 6:
            score -= (avg_chars_per_word - 6) * 3
        
        # Bonus for good structure
        headers = len(re.findall(r'^#{1,6}\s+', content, re.MULTILINE))
        if headers > 0:
            score += min(10, headers)
        
        # Bonus for lists
        lists = len(re.findall(r'^[\*\-\+]\s+|^\d+\.\s+', content, re.MULTILINE))
        if lists > 0:
            score += min(10, lists // 3)
        
        return max(0, min(100, score))
    
    @staticmethod
    def calculate_maintenance_score(issues: List[ReviewIssue]) -> float:
        """Calculate maintenance burden score (0-100, lower is better)."""
        if not issues:
            return 0
        
        # Weight issues by severity
        severity_weights = {
            ReviewSeverity.BLOCKER: 20,
            ReviewSeverity.CRITICAL: 15,
            ReviewSeverity.HIGH: 10,
            ReviewSeverity.MEDIUM: 5,
            ReviewSeverity.LOW: 2,
            ReviewSeverity.INFO: 1
        }
        
        total_weight = sum(severity_weights.get(issue.severity, 5) for issue in issues)
        
        # Normalize to 0-100 scale
        return min(100, total_weight)


class CacheKeyGenerator:
    """Utilities for generating cache keys."""
    
    @staticmethod
    def generate_content_hash(content: str, algorithm: str = 'sha256') -> str:
        """Generate hash for content."""
        hash_func = getattr(hashlib, algorithm)
        return hash_func(content.encode('utf-8')).hexdigest()
    
    @staticmethod
    def generate_cache_key(
        document_id: str,
        content: str,
        document_type: str = "generic",
        mode: str = "basic"
    ) -> str:
        """Generate comprehensive cache key."""
        content_hash = CacheKeyGenerator.generate_content_hash(content)[:16]
        return f"{document_id}:{document_type}:{content_hash}:{mode}"
    
    @staticmethod
    def generate_pattern_cache_key(pattern_name: str, content: str) -> str:
        """Generate cache key for pattern matching results."""
        content_hash = CacheKeyGenerator.generate_content_hash(content)[:8]
        return f"pattern:{pattern_name}:{content_hash}"


class PerformanceMonitor:
    """Utilities for monitoring performance."""
    
    def __init__(self):
        self.timings: Dict[str, List[float]] = {}
        self.counters: Dict[str, int] = {}
    
    def start_timer(self, operation: str) -> float:
        """Start timing an operation."""
        return datetime.now().timestamp()
    
    def end_timer(self, operation: str, start_time: float):
        """End timing and record result."""
        duration = datetime.now().timestamp() - start_time
        
        if operation not in self.timings:
            self.timings[operation] = []
        
        self.timings[operation].append(duration)
        
        # Keep only last 100 measurements
        if len(self.timings[operation]) > 100:
            self.timings[operation] = self.timings[operation][-100:]
    
    def increment_counter(self, counter: str, amount: int = 1):
        """Increment a counter."""
        self.counters[counter] = self.counters.get(counter, 0) + amount
    
    def get_average_time(self, operation: str) -> Optional[float]:
        """Get average time for an operation."""
        if operation not in self.timings or not self.timings[operation]:
            return None
        
        return sum(self.timings[operation]) / len(self.timings[operation])
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get comprehensive performance statistics."""
        stats = {
            'timings': {},
            'counters': dict(self.counters)
        }
        
        for operation, times in self.timings.items():
            if times:
                stats['timings'][operation] = {
                    'count': len(times),
                    'average': sum(times) / len(times),
                    'min': min(times),
                    'max': max(times),
                    'total': sum(times)
                }
        
        return stats
    
    def reset(self):
        """Reset all metrics."""
        self.timings.clear()
        self.counters.clear()


# Global performance monitor instance
performance_monitor = PerformanceMonitor()


def get_performance_stats() -> Dict[str, Any]:
    """Get global performance statistics."""
    return performance_monitor.get_statistics()