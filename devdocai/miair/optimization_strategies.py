"""
M003 MIAIR Engine - Optimization Strategies

Implements the Strategy pattern for document optimization approaches.

Key Features:
- BasicStrategy: Simple iterative optimization
- PerformanceStrategy: High-performance with caching and parallelization
- SecureStrategy: Security-focused with validation and audit
- EnterpriseStrategy: Full-featured with all capabilities
- Pluggable improvement identification and application
- Progress tracking and convergence detection

Each strategy implements different approaches to achieve the target entropy
and quality improvement goals, balancing performance, security, and features.
"""

import logging
import time
import concurrent.futures
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Tuple, Set
from collections import OrderedDict
from datetime import datetime, timezone
import hashlib
import threading

from .models import Document, OperationMode, SemanticElement, ElementType


logger = logging.getLogger(__name__)


class DocumentImprovement:
    """Represents a potential improvement to a document."""
    
    def __init__(
        self,
        type: str,
        description: str,
        priority: float,
        impact: float,
        position: int = 0,
        metadata: Optional[Dict[str, Any]] = None
    ):
        self.type = type
        self.description = description
        self.priority = priority  # 0.0 to 1.0, higher = more important
        self.impact = impact      # 0.0 to 1.0, estimated entropy reduction
        self.position = position
        self.metadata = metadata or {}
        self.applied = False
        self.timestamp = datetime.now(timezone.utc)


class OptimizationCache:
    """LRU cache for optimization results."""
    
    def __init__(self, max_size: int = 100):
        self.cache = OrderedDict()
        self.max_size = max_size
        self.lock = threading.Lock()  # Thread-safe operations
        
        logger.debug(f"OptimizationCache initialized with max_size={max_size}")
    
    def get(self, key: str) -> Optional[Dict[str, Any]]:
        """Get cached result."""
        with self.lock:
            if key in self.cache:
                # Move to end (most recently used)
                self.cache.move_to_end(key)
                result = self.cache[key]
                result['hit_count'] = result.get('hit_count', 0) + 1
                logger.debug(f"Cache hit for key {key[:8]}...")
                return result
            
            logger.debug(f"Cache miss for key {key[:8]}...")
            return None
    
    def set(self, key: str, document: Document, entropy: float, quality: float):
        """Set cached result."""
        with self.lock:
            # Create cache entry
            entry = {
                'document': document,
                'entropy': entropy,
                'quality': quality,
                'timestamp': datetime.now(timezone.utc),
                'hit_count': 0
            }
            
            self.cache[key] = entry
            self.cache.move_to_end(key)
            
            # Evict least recently used if over limit
            if len(self.cache) > self.max_size:
                evicted_key = self.cache.popitem(last=False)
                logger.debug(f"Evicted cache entry {evicted_key[0][:8]}...")
            
            logger.debug(f"Cached result for key {key[:8]}...")
    
    def generate_key(self, document: Document, target_entropy: float) -> str:
        """Generate cache key for document and parameters."""
        content_hash = hashlib.md5(document.content.encode()).hexdigest()
        key_data = f"{content_hash}_{target_entropy}_{document.type.value}"
        return hashlib.md5(key_data.encode()).hexdigest()
    
    def clear(self):
        """Clear all cached entries."""
        with self.lock:
            self.cache.clear()
            logger.debug("Optimization cache cleared")


class OptimizationStrategy(ABC):
    """Base class for document optimization strategies."""
    
    def __init__(self):
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
    
    @abstractmethod
    def optimize(
        self,
        document: Document,
        target_entropy: float,
        max_iterations: int,
        entropy_calculator=None,
        quality_metrics=None
    ) -> Document:
        """
        Optimize document to achieve target entropy.
        
        Args:
            document: Document to optimize
            target_entropy: Target entropy value (0.0 to 1.0)
            max_iterations: Maximum optimization iterations
            entropy_calculator: Entropy calculator instance
            quality_metrics: Quality metrics calculator
            
        Returns:
            Optimized document
        """
        pass
    
    def identify_improvements(
        self, 
        document: Document,
        semantic_elements: List[SemanticElement] = None
    ) -> List[DocumentImprovement]:
        """
        Identify potential improvements for the document.
        
        Args:
            document: Document to analyze
            semantic_elements: Pre-extracted semantic elements (optional)
            
        Returns:
            List of potential improvements, sorted by priority
        """
        improvements = []
        
        # Structure improvements
        improvements.extend(self._identify_structure_improvements(document))
        
        # Content improvements
        improvements.extend(self._identify_content_improvements(document))
        
        # Technical improvements
        improvements.extend(self._identify_technical_improvements(document))
        
        # Format improvements
        improvements.extend(self._identify_format_improvements(document))
        
        # Sort by priority (high to low)
        improvements.sort(key=lambda x: x.priority, reverse=True)
        
        return improvements
    
    def apply_improvements(
        self,
        document: Document,
        improvements: List[DocumentImprovement]
    ) -> Document:
        """
        Apply improvements to document.
        
        Args:
            document: Document to improve
            improvements: List of improvements to apply
            
        Returns:
            Improved document
        """
        improved_doc = document.copy()
        applied_count = 0
        
        for improvement in improvements:
            if self._should_apply_improvement(improvement):
                improved_doc = self._apply_single_improvement(improved_doc, improvement)
                improvement.applied = True
                applied_count += 1
        
        # Update metadata
        improved_doc.metadata['improvements_applied'] = applied_count
        improved_doc.metadata['improvement_types'] = [
            imp.type for imp in improvements if imp.applied
        ]
        
        self.logger.debug(f"Applied {applied_count}/{len(improvements)} improvements")
        
        return improved_doc
    
    def _identify_structure_improvements(self, document: Document) -> List[DocumentImprovement]:
        """Identify structure-related improvements."""
        improvements = []
        content = document.content
        
        # Check for missing headers
        if not content.startswith('#'):
            improvements.append(DocumentImprovement(
                type='add_main_header',
                description='Add main header (H1) to document',
                priority=0.8,
                impact=0.3,
                metadata={'suggested_header': self._suggest_main_header(content)}
            ))
        
        # Check header hierarchy
        header_levels = self._extract_header_levels(content)
        if header_levels and header_levels[0] != 1:
            improvements.append(DocumentImprovement(
                type='fix_header_hierarchy',
                description='Fix header hierarchy - should start with H1',
                priority=0.7,
                impact=0.2
            ))
        
        # Check for level skipping
        for i in range(1, len(header_levels)):
            if header_levels[i] > header_levels[i-1] + 1:
                improvements.append(DocumentImprovement(
                    type='fix_header_skipping',
                    description=f'Fix header level skipping: H{header_levels[i-1]} to H{header_levels[i]}',
                    priority=0.6,
                    impact=0.15,
                    metadata={'from_level': header_levels[i-1], 'to_level': header_levels[i]}
                ))
        
        return improvements
    
    def _identify_content_improvements(self, document: Document) -> List[DocumentImprovement]:
        """Identify content-related improvements."""
        improvements = []
        content = document.content
        
        # Check paragraph lengths
        paragraphs = content.split('\n\n')
        short_paragraphs = sum(1 for p in paragraphs if 0 < len(p.strip()) < 50)
        
        if short_paragraphs > len(paragraphs) * 0.3:
            improvements.append(DocumentImprovement(
                type='expand_short_paragraphs',
                description='Expand short paragraphs for better clarity',
                priority=0.5,
                impact=0.2,
                metadata={'short_paragraph_count': short_paragraphs}
            ))
        
        # Check for repetitive content
        lines = content.splitlines()
        line_counts = {}
        for line in lines:
            normalized = line.strip().lower()
            if len(normalized) > 10:
                line_counts[normalized] = line_counts.get(normalized, 0) + 1
        
        repetitive_lines = sum(1 for count in line_counts.values() if count > 2)
        if repetitive_lines > 0:
            improvements.append(DocumentImprovement(
                type='reduce_repetition',
                description='Reduce repetitive content',
                priority=0.6,
                impact=0.25,
                metadata={'repetitive_line_count': repetitive_lines}
            ))
        
        return improvements
    
    def _identify_technical_improvements(self, document: Document) -> List[DocumentImprovement]:
        """Identify technical documentation improvements."""
        improvements = []
        content = document.content
        
        # Check for code examples
        has_code_blocks = '```' in content
        has_inline_code = '`' in content
        
        if not has_code_blocks and not has_inline_code:
            if document.type.value in ['api_documentation', 'technical_spec', 'tutorial']:
                improvements.append(DocumentImprovement(
                    type='add_code_examples',
                    description='Add code examples for better technical clarity',
                    priority=0.7,
                    impact=0.3
                ))
        
        # Check for definitions
        technical_terms = len(self._extract_technical_terms(content))
        has_definitions = ':' in content and any(
            line.strip().endswith(':') for line in content.splitlines()
        )
        
        if technical_terms > 3 and not has_definitions:
            improvements.append(DocumentImprovement(
                type='add_definitions',
                description='Add definitions for technical terms',
                priority=0.6,
                impact=0.25,
                metadata={'technical_term_count': technical_terms}
            ))
        
        return improvements
    
    def _identify_format_improvements(self, document: Document) -> List[DocumentImprovement]:
        """Identify formatting improvements."""
        improvements = []
        content = document.content
        
        # Check for list formatting
        bullet_indicators = [line for line in content.splitlines() 
                           if line.strip() and not line.startswith(('-', '*', '+', '1.'))]
        potential_lists = sum(1 for line in bullet_indicators 
                             if line.strip().startswith(('•', '○', '◦')))
        
        if potential_lists > 0:
            improvements.append(DocumentImprovement(
                type='improve_list_formatting',
                description='Convert bullet points to proper markdown lists',
                priority=0.4,
                impact=0.1,
                metadata={'potential_list_items': potential_lists}
            ))
        
        # Check for emphasis usage
        emphasis_count = content.count('**') + content.count('*')
        if emphasis_count == 0 and len(content) > 500:
            improvements.append(DocumentImprovement(
                type='add_emphasis',
                description='Add emphasis to key terms and concepts',
                priority=0.3,
                impact=0.1
            ))
        
        return improvements
    
    def _should_apply_improvement(self, improvement: DocumentImprovement) -> bool:
        """Determine if an improvement should be applied."""
        # Apply high-priority improvements
        if improvement.priority >= 0.7:
            return True
        
        # Apply medium-priority improvements with good impact
        if improvement.priority >= 0.5 and improvement.impact >= 0.2:
            return True
        
        # Skip low-priority improvements in Pass 1
        return False
    
    def _apply_single_improvement(
        self, 
        document: Document, 
        improvement: DocumentImprovement
    ) -> Document:
        """Apply a single improvement to the document."""
        content = document.content
        
        if improvement.type == 'add_main_header':
            # Add main header at the beginning
            header = improvement.metadata.get('suggested_header', 'Documentation')
            content = f"# {header}\n\n{content}"
        
        elif improvement.type == 'fix_header_hierarchy':
            # Promote all headers by one level
            content = self._fix_header_hierarchy(content)
        
        elif improvement.type == 'expand_short_paragraphs':
            # Add placeholder text to expand short paragraphs
            content = self._expand_short_paragraphs(content)
        
        elif improvement.type == 'reduce_repetition':
            # Remove or consolidate repetitive content
            content = self._reduce_repetition(content)
        
        elif improvement.type == 'add_code_examples':
            # Add placeholder for code examples
            content = self._add_code_example_placeholders(content)
        
        elif improvement.type == 'add_definitions':
            # Add definition section
            content = self._add_definition_section(content)
        
        elif improvement.type == 'improve_list_formatting':
            # Convert to proper markdown lists
            content = self._improve_list_formatting(content)
        
        elif improvement.type == 'add_emphasis':
            # Add emphasis to key terms
            content = self._add_emphasis_to_terms(content)
        
        # Create improved document
        improved_doc = document.copy()
        improved_doc.content = content
        
        return improved_doc
    
    def _suggest_main_header(self, content: str) -> str:
        """Suggest a main header based on content."""
        # Look for first meaningful line
        lines = [line.strip() for line in content.splitlines() if line.strip()]
        if lines:
            first_line = lines[0]
            # If it looks like a title, use it
            if len(first_line) < 80 and not first_line.endswith('.'):
                return first_line
        
        return "Documentation"
    
    def _extract_header_levels(self, content: str) -> List[int]:
        """Extract header levels from content."""
        import re
        headers = re.findall(r'^(#{1,6})', content, re.MULTILINE)
        return [len(header) for header in headers]
    
    def _extract_technical_terms(self, content: str) -> List[str]:
        """Extract technical terms from content."""
        import re
        # Simple heuristic for technical terms
        terms = re.findall(r'\b[A-Z][A-Z0-9_]{2,}\b|\b[a-z_]+_[a-z_]+\b', content)
        return list(set(terms))
    
    def _fix_header_hierarchy(self, content: str) -> str:
        """Fix header hierarchy by adjusting levels."""
        import re
        # Find all headers and adjust levels
        def adjust_header(match):
            level = len(match.group(1))
            text = match.group(2)
            new_level = max(1, level - 1)  # Promote by one level
            return f"{'#' * new_level} {text}"
        
        return re.sub(r'^(#{2,6})\s+(.+)$', adjust_header, content, flags=re.MULTILINE)
    
    def _expand_short_paragraphs(self, content: str) -> str:
        """Expand short paragraphs with additional content."""
        paragraphs = content.split('\n\n')
        expanded = []
        
        for para in paragraphs:
            stripped = para.strip()
            if 0 < len(stripped) < 50:
                # Add explanatory text to short paragraphs
                expanded.append(f"{stripped} This section provides important information that helps readers understand the key concepts and implementation details.")
            else:
                expanded.append(para)
        
        return '\n\n'.join(expanded)
    
    def _reduce_repetition(self, content: str) -> str:
        """Reduce repetitive content."""
        lines = content.splitlines()
        seen_lines = set()
        filtered_lines = []
        
        for line in lines:
            normalized = line.strip().lower()
            if len(normalized) > 10 and normalized not in seen_lines:
                filtered_lines.append(line)
                seen_lines.add(normalized)
            elif len(normalized) <= 10:
                filtered_lines.append(line)  # Keep short lines (formatting, etc.)
        
        return '\n'.join(filtered_lines)
    
    def _add_code_example_placeholders(self, content: str) -> str:
        """Add code example placeholders."""
        # Add after first header or at the beginning
        lines = content.splitlines()
        insertion_point = 0
        
        for i, line in enumerate(lines):
            if line.startswith('#'):
                insertion_point = i + 1
                break
        
        example = "\n```python\n# Example code will be added here\nprint('Hello, World!')\n```\n"
        lines.insert(insertion_point, example)
        
        return '\n'.join(lines)
    
    def _add_definition_section(self, content: str) -> str:
        """Add a definitions section."""
        terms = self._extract_technical_terms(content)
        if terms:
            definitions = "\n## Definitions\n\n"
            for term in terms[:3]:  # Add up to 3 definitions
                definitions += f"**{term}**: A technical term used in this documentation.\n\n"
            
            # Insert after first header
            lines = content.splitlines()
            for i, line in enumerate(lines):
                if line.startswith('#'):
                    lines.insert(i + 1, definitions)
                    break
            
            return '\n'.join(lines)
        
        return content
    
    def _improve_list_formatting(self, content: str) -> str:
        """Improve list formatting."""
        import re
        # Convert bullet points to markdown lists
        content = re.sub(r'^•\s+', '- ', content, flags=re.MULTILINE)
        content = re.sub(r'^○\s+', '  - ', content, flags=re.MULTILINE)
        content = re.sub(r'^◦\s+', '    - ', content, flags=re.MULTILINE)
        
        return content
    
    def _add_emphasis_to_terms(self, content: str) -> str:
        """Add emphasis to technical terms."""
        terms = self._extract_technical_terms(content)
        
        for term in terms[:5]:  # Emphasize first 5 technical terms
            # Add emphasis on first occurrence
            pattern = r'\b' + re.escape(term) + r'\b'
            content = re.sub(pattern, f'**{term}**', content, count=1)
        
        return content


class BasicStrategy(OptimizationStrategy):
    """Basic sequential optimization strategy."""
    
    def optimize(
        self,
        document: Document,
        target_entropy: float,
        max_iterations: int,
        entropy_calculator=None,
        quality_metrics=None
    ) -> Document:
        """Simple iterative optimization."""
        current_doc = document.copy()
        
        for iteration in range(max_iterations):
            self.logger.debug(f"BasicStrategy iteration {iteration + 1}/{max_iterations}")
            
            # Calculate current entropy
            if entropy_calculator:
                current_entropy = entropy_calculator.calculate_entropy(current_doc, iteration)
            else:
                current_entropy = 0.5  # Fallback
            
            # Check if target achieved
            if current_entropy <= target_entropy:
                self.logger.info(f"Target entropy achieved in {iteration + 1} iterations")
                break
            
            # Identify improvements
            improvements = self.identify_improvements(current_doc)
            
            if not improvements:
                self.logger.warning("No improvements identified")
                break
            
            # Apply improvements
            previous_doc = current_doc
            current_doc = self.apply_improvements(current_doc, improvements)
            
            # Check for convergence (no improvement)
            if current_doc.content == previous_doc.content:
                self.logger.info("Optimization converged - no further improvements")
                break
        
        # Update metadata
        current_doc.metadata['optimization_iterations'] = min(iteration + 1, max_iterations)
        current_doc.metadata['optimization_strategy'] = 'basic'
        
        return current_doc


class PerformanceStrategy(OptimizationStrategy):
    """High-performance optimization with caching and parallelization."""
    
    def __init__(self):
        super().__init__()
        self.cache = OptimizationCache(max_size=200)  # Larger cache
        self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=4)
    
    def optimize(
        self,
        document: Document,
        target_entropy: float,
        max_iterations: int,
        entropy_calculator=None,
        quality_metrics=None
    ) -> Document:
        """Optimized with caching and parallel processing."""
        start_time = time.time()
        
        # Check cache first
        cache_key = self.cache.generate_key(document, target_entropy)
        cached = self.cache.get(cache_key)
        
        if cached and cached['entropy'] <= target_entropy:
            self.logger.info("Using cached optimization result")
            cached_doc = cached['document']
            cached_doc.metadata['cached_result'] = True
            cached_doc.metadata['cache_hit_count'] = cached['hit_count']
            return cached_doc
        
        current_doc = document.copy()
        
        for iteration in range(max_iterations):
            self.logger.debug(f"PerformanceStrategy iteration {iteration + 1}/{max_iterations}")
            
            # Calculate current entropy
            if entropy_calculator:
                current_entropy = entropy_calculator.calculate_entropy(current_doc, iteration)
            else:
                current_entropy = 0.5
            
            if current_entropy <= target_entropy:
                break
            
            # Parallel improvement identification
            improvements = self._parallel_identify_improvements(current_doc)
            
            if not improvements:
                break
            
            # Batch apply improvements
            current_doc = self._batch_apply_improvements(current_doc, improvements)
            
            # Cache intermediate result
            if quality_metrics:
                quality = quality_metrics.calculate_quality_score(current_doc).overall
            else:
                quality = 85.0  # Fallback
                
            self.cache.set(cache_key, current_doc, current_entropy, quality)
        
        # Update metadata
        execution_time = (time.time() - start_time) * 1000  # Convert to ms
        current_doc.metadata['optimization_iterations'] = min(iteration + 1, max_iterations)
        current_doc.metadata['optimization_strategy'] = 'performance'
        current_doc.metadata['execution_time_ms'] = execution_time
        current_doc.metadata['cached_result'] = False
        
        return current_doc
    
    def _parallel_identify_improvements(self, document: Document) -> List[DocumentImprovement]:
        """Identify improvements in parallel."""
        futures = []
        
        with self.executor:
            # Submit different improvement types to parallel workers
            futures.append(self.executor.submit(self._identify_structure_improvements, document))
            futures.append(self.executor.submit(self._identify_content_improvements, document))
            futures.append(self.executor.submit(self._identify_technical_improvements, document))
            futures.append(self.executor.submit(self._identify_format_improvements, document))
            
            # Collect results
            improvements = []
            for future in concurrent.futures.as_completed(futures):
                try:
                    improvements.extend(future.result())
                except Exception as e:
                    self.logger.warning(f"Parallel improvement identification failed: {e}")
        
        # Sort by priority
        improvements.sort(key=lambda x: x.priority, reverse=True)
        return improvements
    
    def _batch_apply_improvements(
        self, 
        document: Document, 
        improvements: List[DocumentImprovement]
    ) -> Document:
        """Apply improvements in batches for better performance."""
        # Group improvements by type for batch processing
        improvement_groups = {}
        for imp in improvements:
            if self._should_apply_improvement(imp):
                if imp.type not in improvement_groups:
                    improvement_groups[imp.type] = []
                improvement_groups[imp.type].append(imp)
        
        current_doc = document
        
        # Apply each group of improvements
        for group_type, group_improvements in improvement_groups.items():
            for improvement in group_improvements:
                current_doc = self._apply_single_improvement(current_doc, improvement)
                improvement.applied = True
        
        return current_doc


class SecureStrategy(OptimizationStrategy):
    """Security-focused optimization with validation and audit."""
    
    def __init__(self):
        super().__init__()
        self.security_validator = self._create_security_validator()
        self.audit_logger = self._create_audit_logger()
    
    def optimize(
        self,
        document: Document,
        target_entropy: float,
        max_iterations: int,
        entropy_calculator=None,
        quality_metrics=None
    ) -> Document:
        """Secure optimization with validation at each step."""
        # Initial validation
        validation_result = self._validate_document(document)
        if not validation_result['valid']:
            raise ValueError(f"Document validation failed: {validation_result['issues']}")
        
        current_doc = document.copy()
        
        for iteration in range(max_iterations):
            self.logger.debug(f"SecureStrategy iteration {iteration + 1}/{max_iterations}")
            
            # Audit each iteration
            self._audit_iteration(document.id, iteration)
            
            # Calculate current entropy
            if entropy_calculator:
                current_entropy = entropy_calculator.calculate_entropy(current_doc, iteration)
            else:
                current_entropy = 0.5
            
            if current_entropy <= target_entropy:
                break
            
            # Identify improvements with security validation
            improvements = self.identify_improvements(current_doc)
            validated_improvements = self._validate_improvements(improvements)
            
            if not validated_improvements:
                self.logger.warning("No valid improvements after security validation")
                break
            
            # Apply validated improvements
            previous_doc = current_doc
            current_doc = self.apply_improvements(current_doc, validated_improvements)
            
            # Validate output
            output_validation = self._validate_document(current_doc)
            if not output_validation['valid']:
                self.logger.warning("Output validation failed, reverting changes")
                current_doc = previous_doc
                break
        
        # Final audit
        self._audit_completion(document.id, iteration + 1)
        
        # Update metadata
        current_doc.metadata['optimization_iterations'] = min(iteration + 1, max_iterations)
        current_doc.metadata['optimization_strategy'] = 'secure'
        current_doc.metadata['security_validated'] = True
        
        return current_doc
    
    def _create_security_validator(self) -> Dict[str, Any]:
        """Create security validator (simplified for Pass 1)."""
        return {
            'max_content_size': 2_000_000,  # 2MB limit
            'blocked_patterns': [
                r'<script\b[^<]*(?:(?!<\/script>)<[^<]*)*<\/script>',  # Script tags
                r'javascript:',  # JavaScript URLs
                r'data:',  # Data URLs
            ],
            'max_improvements_per_iteration': 10
        }
    
    def _create_audit_logger(self) -> Dict[str, Any]:
        """Create audit logger (simplified for Pass 1)."""
        return {
            'log_entries': [],
            'enabled': True
        }
    
    def _validate_document(self, document: Document) -> Dict[str, Any]:
        """Validate document for security issues."""
        issues = []
        
        # Size validation
        if len(document.content) > self.security_validator['max_content_size']:
            issues.append(f"Document too large: {len(document.content)} bytes")
        
        # Pattern validation
        for pattern in self.security_validator['blocked_patterns']:
            import re
            if re.search(pattern, document.content, re.IGNORECASE):
                issues.append(f"Blocked pattern detected: {pattern}")
        
        return {
            'valid': len(issues) == 0,
            'issues': issues,
            'risk_level': 'high' if issues else 'low'
        }
    
    def _validate_improvements(self, improvements: List[DocumentImprovement]) -> List[DocumentImprovement]:
        """Validate improvements for security concerns."""
        validated = []
        
        for improvement in improvements:
            # Skip potentially risky improvements
            if improvement.type in ['add_code_examples']:  # Might contain executable code
                self.logger.warning(f"Skipping potentially risky improvement: {improvement.type}")
                continue
            
            # Limit number of improvements per iteration
            if len(validated) >= self.security_validator['max_improvements_per_iteration']:
                break
                
            validated.append(improvement)
        
        return validated
    
    def _audit_iteration(self, document_id: str, iteration: int):
        """Log audit entry for iteration."""
        if self.audit_logger['enabled']:
            entry = {
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'document_id': document_id,
                'iteration': iteration,
                'action': 'optimization_iteration'
            }
            self.audit_logger['log_entries'].append(entry)
            self.logger.debug(f"Audit: iteration {iteration} for document {document_id}")
    
    def _audit_completion(self, document_id: str, total_iterations: int):
        """Log audit entry for completion."""
        if self.audit_logger['enabled']:
            entry = {
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'document_id': document_id,
                'total_iterations': total_iterations,
                'action': 'optimization_completed'
            }
            self.audit_logger['log_entries'].append(entry)
            self.logger.info(f"Audit: optimization completed for document {document_id}")


class EnterpriseStrategy(OptimizationStrategy):
    """Full-featured optimization with all capabilities."""
    
    def __init__(self):
        super().__init__()
        self.cache = OptimizationCache(max_size=500)  # Large cache
        self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=8)
        self.security_validator = SecureStrategy()._create_security_validator()
        self.audit_logger = SecureStrategy()._create_audit_logger()
        self.analytics = self._create_analytics_engine()
    
    def optimize(
        self,
        document: Document,
        target_entropy: float,
        max_iterations: int,
        entropy_calculator=None,
        quality_metrics=None
    ) -> Document:
        """Enterprise optimization with full feature set."""
        start_time = time.time()
        
        # Pre-optimization analytics
        self._analyze_document(document)
        
        # Validate and check cache
        validation_result = self._validate_document(document)
        if not validation_result['valid']:
            raise ValueError(f"Document validation failed: {validation_result['issues']}")
        
        cache_key = self.cache.generate_key(document, target_entropy)
        cached = self.cache.get(cache_key)
        if cached and cached['entropy'] <= target_entropy:
            self.logger.info("Using cached enterprise optimization result")
            return cached['document']
        
        current_doc = document.copy()
        
        for iteration in range(max_iterations):
            self.logger.debug(f"EnterpriseStrategy iteration {iteration + 1}/{max_iterations}")
            
            # Audit iteration
            self._audit_iteration(document.id, iteration)
            
            # Calculate current entropy
            if entropy_calculator:
                current_entropy = entropy_calculator.calculate_entropy(current_doc, iteration)
            else:
                current_entropy = 0.5
            
            if current_entropy <= target_entropy:
                break
            
            # Multi-modal optimization (combines all approaches)
            improvements = self._multi_modal_improvements(current_doc)
            
            if not improvements:
                break
            
            # Validate and apply
            validated = self._validate_improvements(improvements)
            current_doc = self._advanced_apply(current_doc, validated)
            
            # Cache and analyze
            if quality_metrics:
                quality = quality_metrics.calculate_quality_score(current_doc).overall
            else:
                quality = 85.0
                
            self.cache.set(cache_key, current_doc, current_entropy, quality)
            self._track_iteration(iteration, current_doc)
        
        # Post-optimization analytics
        execution_time = (time.time() - start_time) * 1000
        self._generate_report(document, current_doc, execution_time)
        
        # Update metadata
        current_doc.metadata['optimization_iterations'] = min(iteration + 1, max_iterations)
        current_doc.metadata['optimization_strategy'] = 'enterprise'
        current_doc.metadata['execution_time_ms'] = execution_time
        current_doc.metadata['analytics_enabled'] = True
        
        return current_doc
    
    def _create_analytics_engine(self) -> Dict[str, Any]:
        """Create analytics engine for enterprise features."""
        return {
            'metrics': [],
            'enabled': True,
            'track_performance': True,
            'track_quality': True
        }
    
    def _analyze_document(self, document: Document):
        """Pre-optimization analytics."""
        if self.analytics['enabled']:
            analysis = {
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'document_id': document.id,
                'content_length': len(document.content),
                'content_lines': len(document.content.splitlines()),
                'document_type': document.type.value
            }
            self.analytics['metrics'].append(analysis)
    
    def _multi_modal_improvements(self, document: Document) -> List[DocumentImprovement]:
        """Multi-modal improvement identification using all strategies."""
        # Combine parallel identification with security validation
        performance_strategy = PerformanceStrategy()
        improvements = performance_strategy._parallel_identify_improvements(document)
        
        # Add enterprise-specific improvements
        improvements.extend(self._identify_enterprise_improvements(document))
        
        return improvements
    
    def _identify_enterprise_improvements(self, document: Document) -> List[DocumentImprovement]:
        """Identify enterprise-specific improvements."""
        improvements = []
        
        # Advanced analytics-based improvements
        improvements.append(DocumentImprovement(
            type='optimize_readability',
            description='Optimize content for readability metrics',
            priority=0.6,
            impact=0.2,
            metadata={'analytics_based': True}
        ))
        
        # Multi-language support
        if document.metadata.get('language') != 'en':
            improvements.append(DocumentImprovement(
                type='internationalization',
                description='Optimize for international audiences',
                priority=0.5,
                impact=0.15
            ))
        
        return improvements
    
    def _validate_improvements(self, improvements: List[DocumentImprovement]) -> List[DocumentImprovement]:
        """Enterprise-level improvement validation."""
        secure_strategy = SecureStrategy()
        return secure_strategy._validate_improvements(improvements)
    
    def _advanced_apply(
        self, 
        document: Document, 
        improvements: List[DocumentImprovement]
    ) -> Document:
        """Advanced improvement application with optimization."""
        # Use performance strategy for batch application
        performance_strategy = PerformanceStrategy()
        return performance_strategy._batch_apply_improvements(document, improvements)
    
    def _track_iteration(self, iteration: int, document: Document):
        """Track iteration metrics."""
        if self.analytics['enabled'] and self.analytics['track_performance']:
            metric = {
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'iteration': iteration,
                'content_length': len(document.content),
                'document_id': document.id
            }
            self.analytics['metrics'].append(metric)
    
    def _generate_report(self, original: Document, optimized: Document, execution_time: float):
        """Generate optimization report."""
        if self.analytics['enabled']:
            report = {
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'original_length': len(original.content),
                'optimized_length': len(optimized.content),
                'length_change': len(optimized.content) - len(original.content),
                'execution_time_ms': execution_time,
                'total_metrics': len(self.analytics['metrics'])
            }
            self.analytics['metrics'].append(report)
            self.logger.info(f"Enterprise optimization report generated: {report}")
    
    def _validate_document(self, document: Document) -> Dict[str, Any]:
        """Enterprise document validation."""
        secure_strategy = SecureStrategy()
        return secure_strategy._validate_document(document)
    
    def _audit_iteration(self, document_id: str, iteration: int):
        """Enterprise audit logging."""
        secure_strategy = SecureStrategy()
        secure_strategy.audit_logger = self.audit_logger
        secure_strategy._audit_iteration(document_id, iteration)


def create_strategy(mode: OperationMode) -> OptimizationStrategy:
    """
    Factory function to create optimization strategy based on mode.
    
    Args:
        mode: Operation mode
        
    Returns:
        Appropriate optimization strategy instance
    """
    strategies = {
        OperationMode.BASIC: BasicStrategy,
        OperationMode.PERFORMANCE: PerformanceStrategy,
        OperationMode.SECURE: SecureStrategy,
        OperationMode.ENTERPRISE: EnterpriseStrategy
    }
    
    strategy_class = strategies.get(mode, BasicStrategy)
    return strategy_class()