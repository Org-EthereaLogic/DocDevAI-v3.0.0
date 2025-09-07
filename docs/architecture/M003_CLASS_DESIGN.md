# M003 MIAIR Engine - Detailed Class Design

## Core Class Specifications

### 1. MIAIREngine (engine_unified.py)

```python
from enum import Enum
from typing import Optional, Dict, Any, List, Tuple
from abc import ABC, abstractmethod
import logging

class OperationMode(Enum):
    """Operation modes for MIAIR Engine."""
    BASIC = "basic"          # Core functionality only
    PERFORMANCE = "performance"  # Optimized with caching
    SECURE = "secure"        # Security hardened
    ENTERPRISE = "enterprise"   # Full features

class MIAIREngine:
    """
    Meta-Iterative AI Refinement Engine for documentation quality optimization.
    
    Implements Shannon entropy calculations with fractal-time scaling to achieve
    60-75% quality improvement through iterative refinement.
    """
    
    def __init__(
        self,
        mode: OperationMode = OperationMode.BASIC,
        config_manager: Optional['ConfigurationManager'] = None,
        storage_manager: Optional['StorageManager'] = None
    ):
        """
        Initialize MIAIR Engine with specified operation mode.
        
        Args:
            mode: Operation mode determining feature set
            config_manager: Optional M001 configuration integration
            storage_manager: Optional M002 storage integration
        """
        self.mode = mode
        self.logger = logging.getLogger(__name__)
        
        # Core configuration
        self.entropy_threshold = 0.35  # Maximum acceptable entropy
        self.target_entropy = 0.15     # Target optimization level
        self.coherence_target = 0.94   # Target coherence score
        self.quality_gate = 85         # Minimum quality percentage
        self.max_iterations = 7        # Maximum optimization iterations
        
        # Integration points
        self.config = config_manager
        self.storage = storage_manager
        
        # Load configuration if available
        if self.config:
            self._load_configuration()
        
        # Initialize core components (always loaded)
        self.entropy_calculator = EntropyCalculator()
        self.semantic_analyzer = SemanticAnalyzer()
        self.quality_metrics = QualityMetrics()
        
        # Initialize mode-specific components
        self._initialize_mode_components()
        
        # Load optimization strategy
        self.strategy = self._load_strategy()
    
    def optimize(
        self,
        document: 'Document',
        target_entropy: Optional[float] = None,
        max_iterations: Optional[int] = None
    ) -> 'OptimizationResult':
        """
        Optimize document to achieve target entropy and quality improvement.
        
        Args:
            document: Document to optimize
            target_entropy: Override default target entropy
            max_iterations: Override default max iterations
            
        Returns:
            OptimizationResult with optimized document and metrics
        """
        target_entropy = target_entropy or self.target_entropy
        max_iterations = max_iterations or self.max_iterations
        
        # Validate input
        if self.mode in [OperationMode.SECURE, OperationMode.ENTERPRISE]:
            validation = self.security_validator.validate_document(document)
            if not validation.valid:
                raise ValueError(f"Document validation failed: {validation.issues}")
        
        # Calculate initial metrics
        initial_entropy = self.entropy_calculator.calculate_entropy(document)
        initial_quality = self.quality_metrics.calculate_quality_score(document)
        
        # Check if already optimized
        if initial_entropy <= target_entropy and initial_quality >= self.quality_gate:
            return OptimizationResult(
                document=document,
                initial_entropy=initial_entropy,
                final_entropy=initial_entropy,
                improvement=0.0,
                iterations=0,
                quality_score=initial_quality
            )
        
        # Perform optimization using selected strategy
        optimized_doc = self.strategy.optimize(
            document=document,
            target_entropy=target_entropy,
            max_iterations=max_iterations
        )
        
        # Calculate final metrics
        final_entropy = self.entropy_calculator.calculate_entropy(optimized_doc)
        final_quality = self.quality_metrics.calculate_quality_score(optimized_doc)
        improvement = self._calculate_improvement(initial_entropy, final_entropy)
        
        # Store results if storage available
        if self.storage:
            self._store_optimization_results(document, optimized_doc, improvement)
        
        # Audit logging for secure modes
        if self.mode in [OperationMode.SECURE, OperationMode.ENTERPRISE]:
            self.audit_logger.log_optimization(
                document_id=document.id,
                initial_entropy=initial_entropy,
                final_entropy=final_entropy,
                improvement=improvement
            )
        
        return OptimizationResult(
            document=optimized_doc,
            initial_entropy=initial_entropy,
            final_entropy=final_entropy,
            improvement=improvement,
            iterations=optimized_doc.metadata.get('iterations', 0),
            quality_score=final_quality
        )
    
    def analyze(self, document: 'Document') -> 'AnalysisResult':
        """
        Analyze document without optimization.
        
        Returns entropy score, quality metrics, and improvement potential.
        """
        entropy = self.entropy_calculator.calculate_entropy(document)
        quality = self.quality_metrics.calculate_quality_score(document)
        semantic_elements = self.semantic_analyzer.extract_semantic_elements(document)
        
        improvement_potential = self._estimate_improvement_potential(
            current_entropy=entropy,
            target_entropy=self.target_entropy
        )
        
        return AnalysisResult(
            entropy=entropy,
            quality_score=quality,
            semantic_elements=semantic_elements,
            improvement_potential=improvement_potential,
            meets_quality_gate=quality >= self.quality_gate
        )
```

### 2. EntropyCalculator (entropy_calculator.py)

```python
import math
from typing import List, Dict, Any
from collections import Counter

class EntropyCalculator:
    """
    Implements Shannon entropy calculation with fractal-time scaling.
    
    Formula: S = -Σ[p(xi) × log2(p(xi))] × f(Tx)
    """
    
    def __init__(self):
        self.min_probability = 1e-10  # Avoid log(0)
        
    def calculate_entropy(
        self,
        document: 'Document',
        iteration: int = 0
    ) -> float:
        """
        Calculate Shannon entropy for document.
        
        Args:
            document: Document to analyze
            iteration: Current iteration for fractal scaling
            
        Returns:
            Entropy score between 0.0 and 1.0
        """
        # Extract semantic elements
        elements = self._extract_elements(document)
        
        if not elements:
            return 1.0  # Maximum entropy for empty document
        
        # Calculate probability distribution
        prob_dist = self.calculate_probability_distribution(elements)
        
        # Calculate Shannon entropy
        entropy = 0.0
        for probability in prob_dist.values():
            if probability > self.min_probability:
                entropy -= probability * math.log2(probability)
        
        # Normalize to [0, 1] range
        if len(prob_dist) > 1:
            max_entropy = math.log2(len(prob_dist))
            entropy = entropy / max_entropy if max_entropy > 0 else 0.0
        
        # Apply fractal-time scaling
        scaled_entropy = self.fractal_time_scaling(entropy, iteration)
        
        # Ensure bounds
        return max(0.0, min(1.0, scaled_entropy))
    
    def calculate_probability_distribution(
        self,
        elements: List['SemanticElement']
    ) -> Dict[str, float]:
        """
        Calculate probability distribution of semantic elements.
        
        Args:
            elements: List of semantic elements
            
        Returns:
            Dictionary mapping element types to probabilities
        """
        if not elements:
            return {}
        
        # Count element occurrences
        element_counts = Counter(elem.type for elem in elements)
        total_count = sum(element_counts.values())
        
        # Calculate probabilities
        prob_dist = {
            elem_type: count / total_count
            for elem_type, count in element_counts.items()
        }
        
        return prob_dist
    
    def fractal_time_scaling(
        self,
        entropy: float,
        iteration: int
    ) -> float:
        """
        Apply fractal-time scaling factor f(Tx).
        
        Reduces entropy impact as iterations increase, modeling
        diminishing returns in optimization.
        
        Args:
            entropy: Base entropy value
            iteration: Current iteration number
            
        Returns:
            Scaled entropy value
        """
        # Fractal scaling function
        # f(Tx) = 1 / (1 + log(1 + iteration))
        scaling_factor = 1.0 / (1.0 + math.log(1.0 + iteration))
        
        return entropy * scaling_factor
```

### 3. SemanticAnalyzer (semantic_analyzer.py)

```python
import re
from typing import List, Dict, Any, Set
from dataclasses import dataclass
from enum import Enum

class ElementType(Enum):
    """Types of semantic elements in documents."""
    HEADER = "header"
    PARAGRAPH = "paragraph"
    CODE_BLOCK = "code_block"
    LIST_ITEM = "list_item"
    LINK = "link"
    EMPHASIS = "emphasis"
    TECHNICAL_TERM = "technical_term"
    REQUIREMENT = "requirement"
    SPECIFICATION = "specification"

@dataclass
class SemanticElement:
    """Represents a semantic element in a document."""
    type: ElementType
    content: str
    position: int
    importance: float  # 0.0 to 1.0
    metadata: Dict[str, Any]

class SemanticAnalyzer:
    """
    Extracts and analyzes semantic elements from documents.
    """
    
    def __init__(self):
        self.patterns = self._compile_patterns()
        
    def extract_semantic_elements(
        self,
        document: 'Document'
    ) -> List[SemanticElement]:
        """
        Extract all semantic elements from document.
        
        Args:
            document: Document to analyze
            
        Returns:
            List of semantic elements with metadata
        """
        elements = []
        content = document.content
        
        # Extract structural elements
        elements.extend(self._extract_structure(content))
        
        # Extract technical terms and concepts
        elements.extend(self._extract_concepts(content))
        
        # Extract requirements and specifications
        elements.extend(self._extract_requirements(content))
        
        # Extract code and technical content
        elements.extend(self._extract_code_blocks(content))
        
        # Calculate importance scores
        self._calculate_importance_scores(elements)
        
        return sorted(elements, key=lambda x: x.position)
    
    def identify_patterns(
        self,
        elements: List[SemanticElement]
    ) -> Dict[str, Any]:
        """
        Identify patterns in semantic elements.
        
        Returns patterns like repetition, structure issues, etc.
        """
        patterns = {
            'repetitions': self._find_repetitions(elements),
            'structure_issues': self._analyze_structure(elements),
            'missing_elements': self._identify_missing(elements),
            'coherence_score': self._calculate_coherence(elements)
        }
        
        return patterns
    
    def analyze_coherence(
        self,
        elements: List[SemanticElement]
    ) -> float:
        """
        Analyze document coherence based on element relationships.
        
        Returns:
            Coherence score between 0.0 and 1.0
        """
        if not elements:
            return 0.0
        
        # Analyze element transitions
        transition_score = self._analyze_transitions(elements)
        
        # Analyze topic consistency
        topic_score = self._analyze_topic_consistency(elements)
        
        # Analyze structural coherence
        structure_score = self._analyze_structural_coherence(elements)
        
        # Weighted average
        coherence = (
            transition_score * 0.4 +
            topic_score * 0.3 +
            structure_score * 0.3
        )
        
        return min(1.0, max(0.0, coherence))
```

### 4. OptimizationStrategy (optimization_strategies.py)

```python
from abc import ABC, abstractmethod
from typing import List, Optional
import concurrent.futures

class OptimizationStrategy(ABC):
    """Base class for document optimization strategies."""
    
    @abstractmethod
    def optimize(
        self,
        document: 'Document',
        target_entropy: float,
        max_iterations: int
    ) -> 'Document':
        """Optimize document to achieve target entropy."""
        pass

class BasicStrategy(OptimizationStrategy):
    """Basic sequential optimization strategy."""
    
    def optimize(
        self,
        document: 'Document',
        target_entropy: float,
        max_iterations: int
    ) -> 'Document':
        """
        Simple iterative optimization.
        """
        current_doc = document.copy()
        
        for iteration in range(max_iterations):
            # Calculate current entropy
            current_entropy = self.calculate_entropy(current_doc)
            
            # Check if target achieved
            if current_entropy <= target_entropy:
                break
            
            # Identify improvements
            improvements = self.identify_improvements(current_doc)
            
            # Apply improvements
            current_doc = self.apply_improvements(current_doc, improvements)
            
            # Check for convergence
            new_entropy = self.calculate_entropy(current_doc)
            if new_entropy >= current_entropy:
                break  # No improvement
        
        current_doc.metadata['iterations'] = iteration + 1
        return current_doc

class PerformanceStrategy(OptimizationStrategy):
    """High-performance optimization with caching and parallelization."""
    
    def __init__(self):
        self.cache = OptimizationCache()
        self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=4)
    
    def optimize(
        self,
        document: 'Document',
        target_entropy: float,
        max_iterations: int
    ) -> 'Document':
        """
        Optimized with caching and parallel processing.
        """
        # Check cache
        cache_key = self._generate_cache_key(document)
        cached = self.cache.get(cache_key)
        if cached and cached.entropy <= target_entropy:
            return cached.document
        
        current_doc = document.copy()
        
        for iteration in range(max_iterations):
            current_entropy = self.calculate_entropy(current_doc)
            
            if current_entropy <= target_entropy:
                break
            
            # Parallel improvement identification
            improvements = self._parallel_identify_improvements(current_doc)
            
            # Batch apply improvements
            current_doc = self._batch_apply_improvements(current_doc, improvements)
            
            # Cache intermediate result
            self.cache.set(cache_key, current_doc)
        
        current_doc.metadata['iterations'] = iteration + 1
        return current_doc

class SecureStrategy(OptimizationStrategy):
    """Security-focused optimization with validation and audit."""
    
    def __init__(self):
        self.validator = SecurityValidator()
        self.audit_logger = AuditLogger()
    
    def optimize(
        self,
        document: 'Document',
        target_entropy: float,
        max_iterations: int
    ) -> 'Document':
        """
        Secure optimization with validation at each step.
        """
        # Validate input
        self.validator.validate_document(document)
        
        current_doc = document.copy()
        
        for iteration in range(max_iterations):
            # Audit each iteration
            self.audit_logger.log_iteration(document.id, iteration)
            
            current_entropy = self.calculate_entropy(current_doc)
            
            if current_entropy <= target_entropy:
                break
            
            # Identify improvements with validation
            improvements = self.identify_improvements(current_doc)
            validated_improvements = self.validator.validate_improvements(improvements)
            
            # Apply validated improvements
            current_doc = self.apply_improvements(current_doc, validated_improvements)
            
            # Validate output
            self.validator.validate_document(current_doc)
        
        # Final audit
        self.audit_logger.log_completion(document.id, iteration + 1)
        
        current_doc.metadata['iterations'] = iteration + 1
        return current_doc

class EnterpriseStrategy(OptimizationStrategy):
    """Full-featured optimization with all capabilities."""
    
    def __init__(self):
        self.cache = OptimizationCache()
        self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=8)
        self.validator = SecurityValidator()
        self.audit_logger = AuditLogger()
        self.analytics = AdvancedAnalytics()
    
    def optimize(
        self,
        document: 'Document',
        target_entropy: float,
        max_iterations: int
    ) -> 'Document':
        """
        Enterprise optimization with full feature set.
        """
        # Pre-optimization analytics
        self.analytics.analyze_document(document)
        
        # Validate and cache check
        self.validator.validate_document(document)
        cache_key = self._generate_cache_key(document)
        cached = self.cache.get(cache_key)
        if cached and cached.entropy <= target_entropy:
            return cached.document
        
        current_doc = document.copy()
        
        for iteration in range(max_iterations):
            self.audit_logger.log_iteration(document.id, iteration)
            
            current_entropy = self.calculate_entropy(current_doc)
            
            if current_entropy <= target_entropy:
                break
            
            # Multi-model optimization
            improvements = self._multi_model_improvements(current_doc)
            
            # Validate and apply
            validated = self.validator.validate_improvements(improvements)
            current_doc = self._advanced_apply(current_doc, validated)
            
            # Cache and analyze
            self.cache.set(cache_key, current_doc)
            self.analytics.track_iteration(iteration, current_doc)
        
        # Post-optimization analytics
        self.analytics.generate_report(document, current_doc)
        
        current_doc.metadata['iterations'] = iteration + 1
        return current_doc
```

### 5. QualityMetrics (quality_metrics.py)

```python
from typing import Dict, Any, List
from dataclasses import dataclass

@dataclass
class QualityScore:
    """Represents a quality score with breakdown."""
    overall: float  # 0-100
    completeness: float
    clarity: float
    consistency: float
    structure: float
    technical_accuracy: float

class QualityMetrics:
    """
    Calculate and track document quality metrics.
    """
    
    def __init__(self):
        self.weights = {
            'completeness': 0.25,
            'clarity': 0.25,
            'consistency': 0.20,
            'structure': 0.15,
            'technical_accuracy': 0.15
        }
    
    def calculate_quality_score(
        self,
        document: 'Document'
    ) -> QualityScore:
        """
        Calculate comprehensive quality score.
        
        Args:
            document: Document to evaluate
            
        Returns:
            QualityScore with breakdown
        """
        completeness = self._assess_completeness(document)
        clarity = self._assess_clarity(document)
        consistency = self._assess_consistency(document)
        structure = self._assess_structure(document)
        technical_accuracy = self._assess_technical_accuracy(document)
        
        # Calculate weighted overall score
        overall = (
            completeness * self.weights['completeness'] +
            clarity * self.weights['clarity'] +
            consistency * self.weights['consistency'] +
            structure * self.weights['structure'] +
            technical_accuracy * self.weights['technical_accuracy']
        )
        
        return QualityScore(
            overall=overall,
            completeness=completeness,
            clarity=clarity,
            consistency=consistency,
            structure=structure,
            technical_accuracy=technical_accuracy
        )
    
    def measure_improvement(
        self,
        initial_score: QualityScore,
        final_score: QualityScore
    ) -> float:
        """
        Measure quality improvement percentage.
        
        Returns:
            Improvement percentage (0-100)
        """
        if initial_score.overall == 0:
            return 100.0 if final_score.overall > 0 else 0.0
        
        improvement = (
            (final_score.overall - initial_score.overall) /
            initial_score.overall * 100
        )
        
        return max(0.0, min(100.0, improvement))
    
    def validate_quality_gate(
        self,
        score: QualityScore,
        quality_gate: float = 85.0
    ) -> bool:
        """
        Check if document meets quality gate.
        
        Args:
            score: Quality score to validate
            quality_gate: Minimum acceptable quality (default 85%)
            
        Returns:
            True if meets quality gate
        """
        return score.overall >= quality_gate
```

## Integration Interfaces

### M001 Configuration Integration

```python
class ConfigurationIntegration:
    """Integration with M001 Configuration Manager."""
    
    @staticmethod
    def load_miair_config(config_manager: 'ConfigurationManager') -> Dict[str, Any]:
        """Load MIAIR-specific configuration."""
        config = config_manager.get_config()
        
        return {
            'entropy_threshold': config.quality.entropy_threshold,
            'target_entropy': config.quality.entropy_target,
            'quality_gate': config.quality.quality_gate,
            'max_iterations': config.quality.max_iterations,
            'memory_mode': config_manager.memory_mode,
            'operation_mode': ConfigurationIntegration._map_memory_to_operation(
                config_manager.memory_mode
            )
        }
    
    @staticmethod
    def _map_memory_to_operation(memory_mode: 'MemoryMode') -> OperationMode:
        """Map memory mode to operation mode."""
        mapping = {
            'baseline': OperationMode.BASIC,
            'standard': OperationMode.BASIC,
            'enhanced': OperationMode.PERFORMANCE,
            'performance': OperationMode.ENTERPRISE
        }
        return mapping.get(memory_mode.value, OperationMode.BASIC)
```

### M002 Storage Integration

```python
class StorageIntegration:
    """Integration with M002 Storage System."""
    
    @staticmethod
    def store_optimization_results(
        storage_manager: 'StorageManager',
        document_id: str,
        optimization_result: 'OptimizationResult'
    ):
        """Store optimization results in storage system."""
        # Create document version
        storage_manager.create_version(
            document_id=document_id,
            content=optimization_result.document.content,
            metadata={
                'entropy': optimization_result.final_entropy,
                'quality_score': optimization_result.quality_score,
                'improvement': optimization_result.improvement,
                'iterations': optimization_result.iterations
            }
        )
        
        # Store MIAIR metrics
        storage_manager.store_metadata(
            document_id=document_id,
            key='miair_optimization',
            value={
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'initial_entropy': optimization_result.initial_entropy,
                'final_entropy': optimization_result.final_entropy,
                'improvement_percentage': optimization_result.improvement,
                'iterations_used': optimization_result.iterations,
                'quality_score': optimization_result.quality_score
            }
        )
```

## Models (models.py)

```python
from dataclasses import dataclass
from typing import Dict, Any, List, Optional
from datetime import datetime

@dataclass
class Document:
    """Document model for MIAIR processing."""
    id: str
    content: str
    type: str
    metadata: Dict[str, Any]
    created_at: datetime
    updated_at: datetime
    
    def copy(self) -> 'Document':
        """Create a deep copy of the document."""
        return Document(
            id=self.id,
            content=self.content,
            type=self.type,
            metadata=self.metadata.copy(),
            created_at=self.created_at,
            updated_at=datetime.now()
        )

@dataclass
class OptimizationResult:
    """Result of MIAIR optimization."""
    document: Document
    initial_entropy: float
    final_entropy: float
    improvement: float  # Percentage
    iterations: int
    quality_score: float
    
@dataclass
class AnalysisResult:
    """Result of MIAIR analysis."""
    entropy: float
    quality_score: float
    semantic_elements: List['SemanticElement']
    improvement_potential: float
    meets_quality_gate: bool

@dataclass
class ValidationResult:
    """Result of security validation."""
    valid: bool
    issues: List[str]
    risk_level: str  # low, medium, high

@dataclass
class CachedResult:
    """Cached optimization result."""
    document: Document
    entropy: float
    quality_score: float
    timestamp: datetime
    hit_count: int = 0
```

## Next Steps

This detailed class design provides:

1. **Complete implementation blueprint** for all M003 components
2. **Clear interfaces** for M001/M002 integration
3. **Comprehensive method signatures** with documentation
4. **4 operation modes** following M002 pattern
5. **All data models** required for implementation

The design is ready for Pass 1 implementation with clear structure and interfaces defined.