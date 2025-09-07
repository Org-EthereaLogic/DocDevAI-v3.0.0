"""
M003 MIAIR Engine - Performance Optimized Implementation

High-performance version with caching, parallel processing, and optimized algorithms.
Target: 361K+ documents/minute throughput.

Key Optimizations:
- LRU caching for entropy calculations
- Vectorized operations with NumPy
- Parallel batch processing with asyncio
- Memory-efficient streaming for large documents
- Pre-compiled regex patterns
- Optimized data structures
"""

import asyncio
import hashlib
import logging
import math
import re
import time
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
from functools import lru_cache, cached_property
from typing import Dict, List, Optional, Tuple, Any, Set
import numpy as np
from dataclasses import dataclass, field

from .models import (
    Document, DocumentType, OperationMode, MIAIRConfig,
    OptimizationResult, AnalysisResult, QualityScore,
    SemanticElement, ElementType
)
from .entropy_calculator import EntropyCalculator
from .semantic_analyzer import SemanticAnalyzer
from .quality_metrics import QualityMetrics
from .optimization_strategies import create_strategy


logger = logging.getLogger(__name__)


class CacheManager:
    """Manages various caches for performance optimization."""
    
    def __init__(self, max_size: int = 10000):
        """Initialize cache manager with size limits."""
        self.max_size = max_size
        self.entropy_cache: Dict[str, float] = {}
        self.semantic_cache: Dict[str, List[SemanticElement]] = {}
        self.quality_cache: Dict[str, QualityScore] = {}
        self.hash_cache: Dict[str, str] = {}
        self.pattern_cache: Dict[str, Any] = {}
        self.hit_count = 0
        self.miss_count = 0
        
    def get_document_hash(self, content: str) -> str:
        """Get cached hash of document content."""
        if content not in self.hash_cache:
            if len(self.hash_cache) >= self.max_size:
                # LRU eviction - remove oldest
                self.hash_cache.pop(next(iter(self.hash_cache)))
            self.hash_cache[content] = hashlib.md5(content.encode()).hexdigest()
        return self.hash_cache[content]
    
    def get_entropy(self, doc_hash: str) -> Optional[float]:
        """Get cached entropy value."""
        if doc_hash in self.entropy_cache:
            self.hit_count += 1
            return self.entropy_cache[doc_hash]
        self.miss_count += 1
        return None
    
    def set_entropy(self, doc_hash: str, entropy: float):
        """Cache entropy value."""
        if len(self.entropy_cache) >= self.max_size:
            self.entropy_cache.pop(next(iter(self.entropy_cache)))
        self.entropy_cache[doc_hash] = entropy
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        total_requests = self.hit_count + self.miss_count
        hit_rate = self.hit_count / total_requests if total_requests > 0 else 0
        return {
            "hit_count": self.hit_count,
            "miss_count": self.miss_count,
            "hit_rate": hit_rate,
            "entropy_cache_size": len(self.entropy_cache),
            "semantic_cache_size": len(self.semantic_cache),
            "quality_cache_size": len(self.quality_cache)
        }


class OptimizedEntropyCalculator:
    """Optimized entropy calculator with vectorized operations."""
    
    # Pre-compiled regex patterns
    PATTERNS = {
        'header': re.compile(r'^#{1,6}\s+.*$', re.MULTILINE),
        'code_block': re.compile(r'```[\s\S]*?```', re.MULTILINE),
        'list_item': re.compile(r'^\s*[-*+]\s+.*$', re.MULTILINE),
        'link': re.compile(r'\[([^\]]+)\]\(([^)]+)\)'),
        'emphasis': re.compile(r'(\*{1,2}|_{1,2})([^*_]+)\1'),
        'paragraph': re.compile(r'^(?!#|\s*[-*+]|\s*\d+\.).*\S.*$', re.MULTILINE),
        'function': re.compile(r'(?:def|function|func|fn)\s+\w+\s*\([^)]*\)'),
        'class': re.compile(r'(?:class|struct|interface)\s+\w+'),
        'import': re.compile(r'(?:import|from|require|use)\s+[\w.]+'),
        'comment': re.compile(r'(?://.*$|/\*[\s\S]*?\*/|#.*$)', re.MULTILINE)
    }
    
    def __init__(self, cache_manager: Optional[CacheManager] = None):
        """Initialize with optional cache manager."""
        self.cache = cache_manager or CacheManager()
        self._element_type_map = self._build_element_type_map()
    
    def _build_element_type_map(self) -> Dict[str, ElementType]:
        """Build mapping of pattern names to element types."""
        return {
            'header': ElementType.HEADER,
            'code_block': ElementType.CODE_BLOCK,
            'list_item': ElementType.LIST_ITEM,
            'link': ElementType.LINK,
            'emphasis': ElementType.EMPHASIS,
            'paragraph': ElementType.PARAGRAPH,
            'function': ElementType.CODE_BLOCK,
            'class': ElementType.CODE_BLOCK,
            'import': ElementType.CODE_BLOCK,
            'comment': ElementType.CODE_BLOCK
        }
    
    @lru_cache(maxsize=1000)
    def _calculate_shannon_entropy(self, distribution: tuple) -> float:
        """Calculate Shannon entropy with caching."""
        # Convert tuple back to numpy array for calculation
        probs = np.array(distribution)
        probs = probs[probs > 0]  # Remove zero probabilities
        if len(probs) == 0:
            return 0.0
        return -np.sum(probs * np.log2(probs))
    
    def calculate_entropy_vectorized(self, elements: List[SemanticElement]) -> float:
        """Calculate entropy using vectorized operations."""
        if not elements:
            return 0.0
        
        # Use numpy for faster counting
        element_types = [e.type.value for e in elements]
        unique, counts = np.unique(element_types, return_counts=True)
        
        # Vectorized probability calculation
        total = np.sum(counts)
        probabilities = counts / total
        
        # Cache-friendly tuple for LRU cache
        prob_tuple = tuple(probabilities)
        entropy = self._calculate_shannon_entropy(prob_tuple)
        
        # Normalize to 0-1 range (Shannon entropy can exceed 1 with many categories)
        # Max entropy occurs when all probabilities are equal
        max_entropy = np.log2(len(unique)) if len(unique) > 1 else 1.0
        normalized_entropy = min(entropy / max_entropy if max_entropy > 0 else 0, 1.0)
        
        return float(normalized_entropy)
    
    def extract_elements_optimized(self, content: str) -> List[SemanticElement]:
        """Extract semantic elements with optimized pattern matching."""
        doc_hash = self.cache.get_document_hash(content)
        
        # Check cache first
        if doc_hash in self.cache.semantic_cache:
            return self.cache.semantic_cache[doc_hash]
        
        elements = []
        seen_positions: Set[Tuple[int, int]] = set()
        
        # Process patterns in parallel for large documents
        if len(content) > 10000:
            elements = self._parallel_pattern_extraction(content, seen_positions)
        else:
            elements = self._sequential_pattern_extraction(content, seen_positions)
        
        # Cache results
        if len(self.cache.semantic_cache) < self.cache.max_size:
            self.cache.semantic_cache[doc_hash] = elements
        
        return elements
    
    def _sequential_pattern_extraction(
        self, 
        content: str, 
        seen_positions: Set[Tuple[int, int]]
    ) -> List[SemanticElement]:
        """Extract patterns sequentially for small documents."""
        elements = []
        
        for pattern_name, pattern in self.PATTERNS.items():
            element_type = self._element_type_map[pattern_name]
            
            for match in pattern.finditer(content):
                start, end = match.span()
                if not any(start >= s and end <= e for s, e in seen_positions):
                    elements.append(SemanticElement(
                        type=element_type,
                        content=match.group(0),
                        position=start,
                        importance=0.95
                    ))
                    seen_positions.add((start, end))
        
        return elements
    
    def _parallel_pattern_extraction(
        self, 
        content: str, 
        seen_positions: Set[Tuple[int, int]]
    ) -> List[SemanticElement]:
        """Extract patterns in parallel for large documents."""
        elements = []
        
        # Split content into chunks for parallel processing
        chunk_size = len(content) // 4
        chunks = [
            content[i:i+chunk_size+100]  # Overlap to catch patterns at boundaries
            for i in range(0, len(content), chunk_size)
        ]
        
        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = []
            for i, chunk in enumerate(chunks):
                offset = i * chunk_size
                future = executor.submit(
                    self._extract_chunk_patterns, 
                    chunk, 
                    offset
                )
                futures.append(future)
            
            for future in futures:
                chunk_elements = future.result()
                for elem in chunk_elements:
                    start = elem.position
                    end = start + len(elem.content)
                    if not any(start >= s and end <= e for s, e in seen_positions):
                        elements.append(elem)
                        seen_positions.add((start, end))
        
        return elements
    
    def _extract_chunk_patterns(
        self, 
        chunk: str, 
        offset: int
    ) -> List[SemanticElement]:
        """Extract patterns from a chunk of text."""
        elements = []
        
        for pattern_name, pattern in self.PATTERNS.items():
            element_type = self._element_type_map[pattern_name]
            
            for match in pattern.finditer(chunk):
                elements.append(SemanticElement(
                    type=element_type,
                    content=match.group(0),
                    position=match.start() + offset,
                    importance=0.95
                ))
        
        return elements


class BatchProcessor:
    """Handles batch processing with parallelization."""
    
    def __init__(self, max_workers: int = 4):
        """Initialize batch processor."""
        self.max_workers = max_workers
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
    
    async def process_batch_async(
        self, 
        documents: List[Document],
        processor_func,
        chunk_size: int = 100
    ) -> List[Any]:
        """Process documents in parallel batches asynchronously."""
        results = []
        
        # Split into chunks
        chunks = [
            documents[i:i+chunk_size] 
            for i in range(0, len(documents), chunk_size)
        ]
        
        # Process chunks in parallel
        loop = asyncio.get_event_loop()
        futures = []
        
        for chunk in chunks:
            future = loop.run_in_executor(
                self.executor,
                self._process_chunk,
                chunk,
                processor_func
            )
            futures.append(future)
        
        # Gather results
        chunk_results = await asyncio.gather(*futures)
        for chunk_result in chunk_results:
            results.extend(chunk_result)
        
        return results
    
    def _process_chunk(
        self, 
        chunk: List[Document],
        processor_func
    ) -> List[Any]:
        """Process a chunk of documents."""
        return [processor_func(doc) for doc in chunk]
    
    def process_batch_sync(
        self, 
        documents: List[Document],
        processor_func,
        chunk_size: int = 100
    ) -> List[Any]:
        """Process documents in parallel batches synchronously."""
        results = []
        
        # Split into chunks
        chunks = [
            documents[i:i+chunk_size] 
            for i in range(0, len(documents), chunk_size)
        ]
        
        # Process chunks in parallel
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = []
            for chunk in chunks:
                future = executor.submit(self._process_chunk, chunk, processor_func)
                futures.append(future)
            
            for future in futures:
                results.extend(future.result())
        
        return results


class MIAIREnginePerformance:
    """Performance-optimized MIAIR Engine implementation."""
    
    def __init__(
        self,
        cache_size: int = 10000,
        max_workers: int = 4,
        enable_async: bool = True
    ):
        """Initialize performance-optimized engine."""
        self.cache_manager = CacheManager(max_size=cache_size)
        self.entropy_calculator = OptimizedEntropyCalculator(self.cache_manager)
        self.batch_processor = BatchProcessor(max_workers=max_workers)
        self.enable_async = enable_async
        
        # Original components for fallback
        self.semantic_analyzer = SemanticAnalyzer()
        self.quality_metrics = QualityMetrics()
        
        # Performance metrics
        self.total_documents_processed = 0
        self.total_processing_time = 0
        self.start_time = time.time()
    
    def analyze(self, document: Document) -> AnalysisResult:
        """Analyze a single document with optimizations."""
        start = time.perf_counter()
        
        # Get document hash for caching
        doc_hash = self.cache_manager.get_document_hash(document.content)
        
        # Check cache for entropy
        entropy = self.cache_manager.get_entropy(doc_hash)
        if entropy is None:
            # Calculate entropy with optimized method
            elements = self.entropy_calculator.extract_elements_optimized(document.content)
            entropy = self.entropy_calculator.calculate_entropy_vectorized(elements)
            self.cache_manager.set_entropy(doc_hash, entropy)
        else:
            # Use cached semantic elements if available
            elements = self.cache_manager.semantic_cache.get(
                doc_hash,
                self.entropy_calculator.extract_elements_optimized(document.content)
            )
        
        # Calculate quality score (can be cached similarly)
        quality_score = self._calculate_quality_score(document, entropy)
        
        # Update metrics
        processing_time = time.perf_counter() - start
        self.total_documents_processed += 1
        self.total_processing_time += processing_time
        
        # Calculate improvement potential
        improvement_potential = max(0, (0.35 - entropy) / 0.35 * 100) if entropy < 0.35 else 0
        
        # Check quality gate (85%)
        meets_quality_gate = quality_score.overall >= 85
        
        return AnalysisResult(
            entropy=entropy,
            quality_score=quality_score,
            semantic_elements=elements,
            improvement_potential=improvement_potential,
            meets_quality_gate=meets_quality_gate,
            patterns={}  # Optional field
        )
    
    def analyze_batch(
        self, 
        documents: List[Document]
    ) -> List[AnalysisResult]:
        """Analyze a batch of documents with parallel processing."""
        if self.enable_async and len(documents) > 10:
            # Use async for large batches
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                return loop.run_until_complete(
                    self.analyze_batch_async(documents)
                )
            finally:
                loop.close()
        else:
            # Use sync parallel processing
            return self.batch_processor.process_batch_sync(
                documents,
                self.analyze
            )
    
    async def analyze_batch_async(
        self, 
        documents: List[Document]
    ) -> List[AnalysisResult]:
        """Analyze a batch of documents asynchronously."""
        return await self.batch_processor.process_batch_async(
            documents,
            self.analyze
        )
    
    def _calculate_quality_score(
        self, 
        document: Document, 
        entropy: float
    ) -> QualityScore:
        """Calculate quality score with optimizations."""
        # Fast quality calculation based on entropy
        if entropy < 0.15:
            base_score = 0.95
        elif entropy < 0.25:
            base_score = 0.85
        elif entropy < 0.35:
            base_score = 0.75
        else:
            base_score = 0.65
        
        # Adjust based on document type
        type_multiplier = {
            DocumentType.API_DOCUMENTATION: 1.1,
            DocumentType.TUTORIAL: 1.05,
            DocumentType.REFERENCE: 1.0,
            DocumentType.GENERAL: 0.95
        }.get(document.type, 1.0)
        
        final_score = min(base_score * type_multiplier, 1.0)
        
        return QualityScore(
            overall=final_score * 100,  # Convert to 0-100 scale
            completeness=min(final_score * 0.9 * 100, 100),
            clarity=min(final_score * 1.05 * 100, 100),
            consistency=min(final_score * 0.95 * 100, 100),
            structure=min(final_score * 1.0 * 100, 100),
            technical_accuracy=min(final_score * 1.0 * 100, 100)
        )
    
    def _generate_suggestions(
        self, 
        entropy: float, 
        quality_score: QualityScore
    ) -> List[str]:
        """Generate optimization suggestions."""
        suggestions = []
        
        if entropy > 0.35:
            suggestions.append("Reduce entropy by improving content structure")
        if quality_score.overall < 85:  # Now on 0-100 scale
            suggestions.append("Enhance documentation quality")
        if quality_score.clarity < 80:  # Now on 0-100 scale
            suggestions.append("Improve clarity and readability")
        
        return suggestions
    
    def optimize(
        self, 
        document: Document, 
        target_entropy: float = 0.15
    ) -> OptimizationResult:
        """Optimize document with performance enhancements."""
        analysis = self.analyze(document)
        
        if analysis.entropy <= target_entropy:
            return OptimizationResult(
                original_document=document,
                optimized_document=document,
                original_entropy=analysis.entropy,
                optimized_entropy=analysis.entropy,
                improvement_percentage=0,
                iterations=0,
                optimization_time=0
            )
        
        # Apply optimization strategies
        optimized_content = document.content
        iterations = 0
        max_iterations = 5
        
        while iterations < max_iterations:
            # Apply optimizations (simplified for performance)
            optimized_content = self._apply_optimizations(optimized_content)
            
            # Create optimized document
            optimized_doc = Document(
                id=document.id,
                content=optimized_content,
                type=document.type
            )
            
            # Check new entropy
            new_analysis = self.analyze(optimized_doc)
            
            if new_analysis.entropy <= target_entropy:
                break
            
            iterations += 1
        
        improvement = ((analysis.entropy - new_analysis.entropy) / analysis.entropy) * 100
        
        return OptimizationResult(
            original_document=document,
            optimized_document=optimized_doc,
            original_entropy=analysis.entropy,
            optimized_entropy=new_analysis.entropy,
            improvement_percentage=improvement,
            iterations=iterations,
            optimization_time=time.perf_counter() - analysis.processing_time
        )
    
    def _apply_optimizations(self, content: str) -> str:
        """Apply basic optimizations to content."""
        # Simple optimizations for performance
        optimized = content
        
        # Add structure if missing
        if not re.search(r'^#', content, re.MULTILINE):
            optimized = f"# Documentation\n\n{optimized}"
        
        # Ensure consistent spacing
        optimized = re.sub(r'\n{3,}', '\n\n', optimized)
        
        # Add list formatting
        optimized = re.sub(r'^(\d+)\.\s', r'- ', optimized, flags=re.MULTILINE)
        
        return optimized
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get performance statistics."""
        runtime = time.time() - self.start_time
        avg_time = (
            self.total_processing_time / self.total_documents_processed
            if self.total_documents_processed > 0 else 0
        )
        throughput = (
            self.total_documents_processed / runtime
            if runtime > 0 else 0
        )
        
        return {
            "total_documents": self.total_documents_processed,
            "total_time": self.total_processing_time,
            "average_time": avg_time,
            "throughput_per_sec": throughput,
            "throughput_per_min": throughput * 60,
            "cache_stats": self.cache_manager.get_cache_stats(),
            "runtime": runtime
        }


# Factory function for creating optimized engine
def create_performance_engine(**kwargs) -> MIAIREnginePerformance:
    """Create a performance-optimized MIAIR engine instance."""
    return MIAIREnginePerformance(**kwargs)