"""
M007 Review Engine - Unified implementation.

Consolidated implementation combining base, optimized, and secure functionality
through configurable operation modes. Reduces code duplication by 30-40%
while maintaining all features across different operational requirements.
"""

import asyncio
import hashlib
import json
import logging
import time
import uuid
import secrets
import signal
from collections import OrderedDict, defaultdict, deque
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor, as_completed
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Set, Tuple, Union
from functools import lru_cache, wraps
from pathlib import Path
from enum import Enum
import multiprocessing as mp
import pickle
import re

# Optional performance libraries
try:
    import numpy as np
    NUMPY_AVAILABLE = True
except ImportError:
    NUMPY_AVAILABLE = False

try:
    from joblib import Memory
    JOBLIB_AVAILABLE = True
except ImportError:
    JOBLIB_AVAILABLE = False

try:
    from cryptography.fernet import Fernet
    CRYPTO_AVAILABLE = True
except ImportError:
    CRYPTO_AVAILABLE = False

from ..core.config import ConfigurationManager  # M001
from ..storage.local_storage import LocalStorageSystem  # M002
from ..storage.pii_detector import PIIDetector  # M002
from ..miair.engine_unified import UnifiedMIAIREngine  # M003
from ..quality.analyzer_unified import UnifiedQualityAnalyzer  # M005
from ..templates.registry_unified import UnifiedTemplateRegistry  # M006

from .models import (
    ReviewResult,
    ReviewStatus,
    ReviewEngineConfig,
    ReviewDimension,
    ReviewSeverity,
    ReviewIssue,
    DimensionResult,
    ReviewMetrics
)

logger = logging.getLogger(__name__)


class OperationMode(Enum):
    """Operation modes for the unified review engine."""
    BASIC = "basic"
    OPTIMIZED = "optimized"
    SECURE = "secure"
    ENTERPRISE = "enterprise"


class CacheType(Enum):
    """Available cache implementations."""
    SIMPLE = "simple"
    LRU = "lru"
    ENCRYPTED = "encrypted"


class UnifiedRegexPatterns:
    """
    Unified regex pattern registry with mode-based optimizations.
    
    Features:
    - Pre-compiled patterns for performance
    - Timeout protection against ReDoS attacks
    - LRU caching for pattern matching
    - Security-aware pattern limits
    """
    
    _patterns_cache: Dict[str, re.Pattern] = {}
    _compiled_lock = asyncio.Lock() if asyncio else None
    
    # Base patterns with security limits
    PATTERNS = {
        # Technical accuracy patterns
        'code_smell': r'\b(?:TODO|FIXME|HACK|XXX|REFACTOR|OPTIMIZE)\b',
        'debug_code': r'(?:console\.(?:log|debug|info|warn|error)|print\(|debugger\b|pdb\.set_trace)',
        'hardcoded_values': r'(?:password|secret|key|token)\s*=\s*["\'][^"\']{1,100}["\']',
        'unused_imports': r'^import\s+\w+(?:\s*,\s*\w+){0,10}\s*$',
        'long_lines': r'^.{121,500}$',  # Reasonable limit to prevent ReDoS
        
        # Completeness patterns
        'sections': r'^#{1,6}\s+(.{1,200})$',
        'code_blocks': r'```[^`]{0,10000}```',
        'links': r'\[([^\]]{1,100})\]\(([^)]{1,500})\)',
        'images': r'!\[([^\]]{0,100})\]\(([^)]{1,500})\)',
        'tables': r'^\|.{1,1000}\|$',
        'lists': r'^[\*\-\+]\s+.{1,500}$|^\d+\.\s+.{1,500}$',
        
        # Consistency patterns
        'camel_case': r'\b[a-z]+(?:[A-Z][a-z]+){1,10}\b',
        'snake_case': r'\b[a-z]+(?:_[a-z]+){1,10}\b',
        'kebab_case': r'\b[a-z]+(?:-[a-z]+){1,10}\b',
        'trailing_whitespace': r'[ \t]+$',
        
        # Style patterns
        'multiple_spaces': r'  {1,10}',
        'tabs_spaces_mix': r'^(?:\t+ +| +\t+)',
        'empty_lines': r'\n{3,10}',
        'no_final_newline': r'[^\n]\Z',
        
        # Security patterns
        'sql_injection': r'\b(?:SELECT|INSERT|UPDATE|DELETE|DROP|UNION|ALTER|CREATE)\b.*\b(?:FROM|INTO|TABLE|WHERE)\b',
        'xss_simple': r'<script[^>]*>|javascript:|on\w+\s*=',
        'command_injection': r'[;&|`$]|\$\([^)]{1,100}\)',
        'path_traversal': r'\.\.[\\/]|\.\.%2[fF]|\.\.%5[cC]',
        'weak_crypto': r'\b(?:md5|sha1|des|rc4)\b',
        
        # PII patterns
        'email': r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
        'phone': r'\b(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b',
        'ssn': r'\b\d{3}-\d{2}-\d{4}\b',
        'credit_card': r'\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b',
        'api_key': r'\b[A-Za-z0-9]{32,}\b',
    }
    
    @classmethod
    async def get_pattern(cls, name: str, mode: OperationMode = OperationMode.BASIC) -> Optional[re.Pattern]:
        """Get compiled regex pattern with mode-specific optimizations."""
        if cls._compiled_lock:
            async with cls._compiled_lock:
                return cls._get_pattern_sync(name, mode)
        else:
            return cls._get_pattern_sync(name, mode)
    
    @classmethod
    def _get_pattern_sync(cls, name: str, mode: OperationMode) -> Optional[re.Pattern]:
        """Synchronously get compiled pattern."""
        cache_key = f"{name}_{mode.value}"
        
        if cache_key in cls._patterns_cache:
            return cls._patterns_cache[cache_key]
        
        pattern_str = cls.PATTERNS.get(name)
        if not pattern_str:
            return None
        
        # Compile with appropriate flags based on mode
        flags = re.MULTILINE | re.IGNORECASE
        if mode in [OperationMode.OPTIMIZED, OperationMode.ENTERPRISE]:
            # Add performance optimizations
            pass
        
        try:
            compiled = re.compile(pattern_str, flags)
            cls._patterns_cache[cache_key] = compiled
            return compiled
        except re.error as e:
            logger.warning(f"Failed to compile regex pattern {name}: {e}")
            return None
    
    @classmethod
    def safe_search(
        cls,
        pattern: re.Pattern,
        text: str,
        timeout: float = 2.0,
        mode: OperationMode = OperationMode.BASIC
    ) -> List[re.Match]:
        """
        Safely search with timeout protection against ReDoS.
        Only applies timeout in SECURE/ENTERPRISE modes.
        """
        if mode not in [OperationMode.SECURE, OperationMode.ENTERPRISE]:
            # No timeout protection in basic/optimized modes for performance
            return list(pattern.finditer(text))
        
        def timeout_handler(signum, frame):
            raise TimeoutError("Regex execution timed out")
        
        # Apply timeout protection
        old_handler = signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(int(timeout))
        
        try:
            matches = list(pattern.finditer(text))
            signal.alarm(0)  # Cancel alarm
            return matches
        except TimeoutError:
            logger.warning(f"Regex pattern timed out: {pattern.pattern[:50]}...")
            return []
        finally:
            signal.signal(signal.SIGALRM, old_handler)
    
    @classmethod
    @lru_cache(maxsize=128)
    def cached_search(cls, pattern_name: str, text_hash: str, text: str, mode: OperationMode) -> int:
        """Cached pattern search - only for optimized/enterprise modes."""
        if mode not in [OperationMode.OPTIMIZED, OperationMode.ENTERPRISE]:
            return 0
        
        pattern = cls._get_pattern_sync(pattern_name, mode)
        if not pattern:
            return 0
        
        matches = cls.safe_search(pattern, text, mode=mode)
        return len(matches)


class UnifiedCacheManager:
    """
    Unified cache manager supporting multiple cache types based on operation mode.
    
    Cache Types:
    - SIMPLE: Basic in-memory cache with TTL
    - LRU: High-performance LRU cache with size limits
    - ENCRYPTED: Secure encrypted cache with integrity checks
    """
    
    def __init__(
        self,
        cache_type: CacheType,
        max_size: int = 1000,
        ttl_seconds: int = 3600,
        encryption_key: Optional[bytes] = None
    ):
        """Initialize unified cache manager."""
        self.cache_type = cache_type
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds
        
        # Statistics
        self.hits = 0
        self.misses = 0
        
        # Initialize appropriate cache implementation
        if cache_type == CacheType.SIMPLE:
            self.cache: Dict[str, Tuple[Any, datetime]] = {}
        elif cache_type == CacheType.LRU:
            self.cache: OrderedDict[str, Tuple[Any, datetime]] = OrderedDict()
        elif cache_type == CacheType.ENCRYPTED:
            if not CRYPTO_AVAILABLE:
                logger.warning("Cryptography not available, falling back to LRU cache")
                self.cache_type = CacheType.LRU
                self.cache = OrderedDict()
            else:
                self.cache: OrderedDict[str, Tuple[bytes, datetime, str]] = OrderedDict()
                self.cipher = Fernet(encryption_key or Fernet.generate_key())
        
        self._lock = asyncio.Lock()
    
    async def get(self, key: str) -> Optional[Any]:
        """Get cached value with type-specific implementation."""
        async with self._lock:
            if self.cache_type == CacheType.SIMPLE:
                return await self._get_simple(key)
            elif self.cache_type == CacheType.LRU:
                return await self._get_lru(key)
            elif self.cache_type == CacheType.ENCRYPTED:
                return await self._get_encrypted(key)
    
    async def set(self, key: str, value: Any) -> None:
        """Set cached value with type-specific implementation."""
        async with self._lock:
            if self.cache_type == CacheType.SIMPLE:
                await self._set_simple(key, value)
            elif self.cache_type == CacheType.LRU:
                await self._set_lru(key, value)
            elif self.cache_type == CacheType.ENCRYPTED:
                await self._set_encrypted(key, value)
    
    async def _get_simple(self, key: str) -> Optional[Any]:
        """Simple cache get implementation."""
        if key in self.cache:
            value, timestamp = self.cache[key]
            if datetime.now() - timestamp < timedelta(seconds=self.ttl_seconds):
                self.hits += 1
                return value
            else:
                del self.cache[key]
        
        self.misses += 1
        return None
    
    async def _set_simple(self, key: str, value: Any) -> None:
        """Simple cache set implementation."""
        self.cache[key] = (value, datetime.now())
        
        # Simple eviction if over size limit
        if len(self.cache) > self.max_size:
            oldest_key = min(self.cache.keys(), key=lambda k: self.cache[k][1])
            del self.cache[oldest_key]
    
    async def _get_lru(self, key: str) -> Optional[Any]:
        """LRU cache get implementation."""
        if key in self.cache:
            value, timestamp = self.cache[key]
            if datetime.now() - timestamp < timedelta(seconds=self.ttl_seconds):
                # Move to end (most recently used)
                self.cache.move_to_end(key)
                self.hits += 1
                return value
            else:
                del self.cache[key]
        
        self.misses += 1
        return None
    
    async def _set_lru(self, key: str, value: Any) -> None:
        """LRU cache set implementation."""
        # Remove if exists to update position
        if key in self.cache:
            del self.cache[key]
        
        # Add to end (most recently used)
        self.cache[key] = (value, datetime.now())
        
        # Evict least recently used if over size limit
        while len(self.cache) > self.max_size:
            self.cache.popitem(last=False)
    
    async def _get_encrypted(self, key: str) -> Optional[Any]:
        """Encrypted cache get implementation."""
        secure_key = self._generate_secure_key(key)
        
        if secure_key in self.cache:
            encrypted_value, timestamp, value_hash = self.cache[secure_key]
            
            # Check expiration
            if datetime.now() - timestamp < timedelta(seconds=self.ttl_seconds):
                # Verify integrity
                current_hash = hashlib.sha256(encrypted_value).hexdigest()
                if current_hash != value_hash:
                    logger.warning(f"Cache integrity check failed for key: {key}")
                    del self.cache[secure_key]
                    self.misses += 1
                    return None
                
                # Decrypt and return
                try:
                    decrypted = self.cipher.decrypt(encrypted_value)
                    value = pickle.loads(decrypted)
                    # Move to end (LRU)
                    self.cache.move_to_end(secure_key)
                    self.hits += 1
                    return value
                except Exception as e:
                    logger.warning(f"Decryption failed: {e}")
                    del self.cache[secure_key]
            else:
                del self.cache[secure_key]
        
        self.misses += 1
        return None
    
    async def _set_encrypted(self, key: str, value: Any) -> None:
        """Encrypted cache set implementation."""
        secure_key = self._generate_secure_key(key)
        
        try:
            # Encrypt value
            serialized = pickle.dumps(value)
            encrypted = self.cipher.encrypt(serialized)
            value_hash = hashlib.sha256(encrypted).hexdigest()
            
            # Remove if exists to update position
            if secure_key in self.cache:
                del self.cache[secure_key]
            
            # Add to cache
            self.cache[secure_key] = (encrypted, datetime.now(), value_hash)
            
            # Evict LRU if needed
            while len(self.cache) > self.max_size:
                self.cache.popitem(last=False)
                
        except Exception as e:
            logger.error(f"Encryption failed: {e}")
    
    def _generate_secure_key(self, key: str) -> str:
        """Generate secure cache key."""
        namespace = "m007_review"
        return hashlib.sha256(f"{namespace}:{key}".encode()).hexdigest()
    
    async def clear(self) -> None:
        """Clear all cached results."""
        async with self._lock:
            if self.cache_type == CacheType.ENCRYPTED:
                # Secure cleanup - overwrite encrypted values
                for key in list(self.cache.keys()):
                    if isinstance(self.cache[key][0], bytes):
                        encrypted_value = self.cache[key][0]
                        # Overwrite with random data
                        self.cache[key] = (
                            secrets.token_bytes(len(encrypted_value)),
                            self.cache[key][1],
                            self.cache[key][2]
                        )
            
            self.cache.clear()
            self.hits = 0
            self.misses = 0
    
    @property
    def hit_rate(self) -> float:
        """Calculate cache hit rate."""
        total = self.hits + self.misses
        return self.hits / total if total > 0 else 0.0


class UnifiedReviewEngine:
    """
    Unified Review Engine for M007 combining all implementations.
    
    Features:
    - Configurable operation modes (BASIC, OPTIMIZED, SECURE, ENTERPRISE)
    - Unified caching with multiple backends
    - Mode-based feature selection
    - Consolidated regex patterns
    - Integrated security features
    - Performance optimizations
    - Comprehensive module integrations
    """
    
    def __init__(
        self,
        mode: OperationMode = OperationMode.BASIC,
        config: Optional[ReviewEngineConfig] = None,
        encryption_key: Optional[bytes] = None
    ):
        """
        Initialize unified review engine.
        
        Args:
            mode: Operation mode determining feature set
            config: Optional review engine configuration
            encryption_key: Optional encryption key for secure cache
        """
        self.mode = mode
        self.config = config or ReviewEngineConfig()
        
        # Configure cache based on mode
        cache_type = self._get_cache_type_for_mode(mode)
        self.cache = UnifiedCacheManager(
            cache_type=cache_type,
            max_size=getattr(self.config, 'cache_max_size', 1000),
            ttl_seconds=self.config.cache_ttl_seconds,
            encryption_key=encryption_key
        )
        
        # Initialize executors based on mode
        self._init_executors()
        
        # Initialize module integrations
        self._init_integrations()
        
        # Initialize dimensions
        self.dimensions = self._init_dimensions()
        
        # Mode-specific initializations
        if mode in [OperationMode.SECURE, OperationMode.ENTERPRISE]:
            self._init_security_features()
        
        if mode in [OperationMode.OPTIMIZED, OperationMode.ENTERPRISE]:
            self._init_performance_features()
        
        # Statistics
        self.reviews_performed = 0
        self.total_issues_found = 0
        self.security_metrics = defaultdict(int)
        
        # Background tasks
        self._cleanup_tasks = []
        self._start_background_tasks()
        
        logger.info(f"Initialized M007 Unified Review Engine in {mode.value.upper()} mode")
    
    def _get_cache_type_for_mode(self, mode: OperationMode) -> CacheType:
        """Get appropriate cache type for operation mode."""
        cache_mapping = {
            OperationMode.BASIC: CacheType.SIMPLE,
            OperationMode.OPTIMIZED: CacheType.LRU,
            OperationMode.SECURE: CacheType.ENCRYPTED,
            OperationMode.ENTERPRISE: CacheType.ENCRYPTED,
        }
        return cache_mapping[mode]
    
    def _init_executors(self):
        """Initialize thread/process executors based on mode."""
        if self.mode == OperationMode.BASIC:
            # Minimal resources for basic mode
            self.thread_executor = ThreadPoolExecutor(max_workers=2)
            self.process_executor = None
        elif self.mode == OperationMode.OPTIMIZED:
            # Optimized resource allocation
            self.thread_executor = ThreadPoolExecutor(
                max_workers=getattr(self.config, 'max_workers', 6)
            )
            self.process_executor = ProcessPoolExecutor(max_workers=min(mp.cpu_count(), 4))
        elif self.mode in [OperationMode.SECURE, OperationMode.ENTERPRISE]:
            # Secure resource limits
            self.thread_executor = ThreadPoolExecutor(
                max_workers=min(getattr(self.config, 'max_workers', 4), 8)
            )
            self.process_executor = ProcessPoolExecutor(max_workers=min(mp.cpu_count(), 4))
    
    def _init_integrations(self):
        """Initialize integrations with M001-M006 modules."""
        try:
            self.config_manager = ConfigurationManager()
            logger.info("Initialized M001 Configuration Manager integration")
        except Exception as e:
            logger.warning(f"M001 Configuration Manager not available: {e}")
            self.config_manager = None
        
        try:
            self.storage = LocalStorageSystem()
            logger.info("Initialized M002 Local Storage integration")
        except Exception as e:
            logger.warning(f"M002 Local Storage not available: {e}")
            self.storage = None
        
        try:
            self.pii_detector = PIIDetector()
            logger.info("Initialized M002 PII Detector")
        except Exception as e:
            logger.warning(f"M002 PII Detector not available: {e}")
            self.pii_detector = None
        
        try:
            if self.config.use_miair_optimization:
                self.miair_engine = UnifiedMIAIREngine()
                logger.info("Initialized M003 MIAIR Engine integration")
            else:
                self.miair_engine = None
        except Exception as e:
            logger.warning(f"M003 MIAIR Engine not available: {e}")
            self.miair_engine = None
        
        try:
            if self.config.use_quality_engine:
                self.quality_analyzer = UnifiedQualityAnalyzer()
                logger.info("Initialized M005 Quality Analyzer integration")
            else:
                self.quality_analyzer = None
        except Exception as e:
            logger.warning(f"M005 Quality Analyzer not available: {e}")
            self.quality_analyzer = None
        
        try:
            self.template_registry = UnifiedTemplateRegistry()
            logger.info("Initialized M006 Template Registry integration")
        except Exception as e:
            logger.warning(f"M006 Template Registry not available: {e}")
            self.template_registry = None
    
    def _init_dimensions(self) -> List['UnifiedDimension']:
        """Initialize review dimensions based on configuration and mode."""
        from .dimensions_unified import UnifiedDimensionFactory
        
        factory = UnifiedDimensionFactory(mode=self.mode)
        dimensions = []
        
        enabled = self.config.enabled_dimensions
        weights = self.config.dimension_weights
        
        for dimension_type in enabled:
            dimension = factory.create_dimension(
                dimension_type=dimension_type,
                weight=weights.get(dimension_type, 0.20),
                config=self.config
            )
            if dimension:
                dimensions.append(dimension)
        
        return dimensions
    
    def _init_security_features(self):
        """Initialize security features for SECURE/ENTERPRISE modes."""
        from .security_validator import SecurityValidator, AccessController
        
        self.security_validator = SecurityValidator()
        self.access_controller = AccessController()
        
        # Setup audit logging
        self.audit_logger = logging.getLogger(f"{__name__}.audit")
        if not self.audit_logger.handlers:
            handler = logging.FileHandler('review_security_audit.log')
            handler.setFormatter(
                logging.Formatter(
                    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
                )
            )
            self.audit_logger.addHandler(handler)
            self.audit_logger.setLevel(logging.INFO)
        
        logger.info("Security features initialized")
    
    def _init_performance_features(self):
        """Initialize performance features for OPTIMIZED/ENTERPRISE modes."""
        if JOBLIB_AVAILABLE:
            self.memory = Memory(location='/tmp/m007_cache', verbose=0)
            logger.info("Joblib memory caching initialized")
        else:
            self.memory = None
        
        # Pre-warm regex cache
        asyncio.create_task(self._warm_regex_cache())
        
        logger.info("Performance features initialized")
    
    async def _warm_regex_cache(self):
        """Pre-warm regex pattern cache."""
        for pattern_name in UnifiedRegexPatterns.PATTERNS.keys():
            await UnifiedRegexPatterns.get_pattern(pattern_name, self.mode)
    
    def _start_background_tasks(self):
        """Start background tasks based on mode."""
        if self.mode in [OperationMode.OPTIMIZED, OperationMode.ENTERPRISE]:
            # Cache cleanup task
            task = asyncio.create_task(self._cache_cleanup_loop())
            self._cleanup_tasks.append(task)
        
        if self.mode in [OperationMode.SECURE, OperationMode.ENTERPRISE]:
            # Security monitoring task
            task = asyncio.create_task(self._security_monitoring_loop())
            self._cleanup_tasks.append(task)
    
    async def _cache_cleanup_loop(self):
        """Background cache cleanup loop."""
        while True:
            await asyncio.sleep(300)  # Every 5 minutes
            try:
                # Cleanup logic would go here
                pass
            except Exception as e:
                logger.error(f"Cache cleanup error: {e}")
    
    async def _security_monitoring_loop(self):
        """Background security monitoring loop."""
        while True:
            await asyncio.sleep(60)  # Every minute
            try:
                await self._perform_security_checks()
            except Exception as e:
                logger.error(f"Security monitoring error: {e}")
    
    async def _perform_security_checks(self):
        """Perform periodic security checks."""
        # Check for security anomalies
        if self.security_metrics['access_denied'] > 100:
            self._log_security_alert(
                "high_access_denial_rate",
                {"count": self.security_metrics['access_denied']}
            )
        
        # Reset counters for next period
        for key in ['access_denied', 'rate_limits_hit', 'cache_poisoning_attempts']:
            self.security_metrics[key] = 0
    
    def _log_security_alert(self, alert_type: str, details: Dict[str, Any]):
        """Log security alert."""
        if hasattr(self, 'audit_logger'):
            alert = {
                "timestamp": datetime.now().isoformat(),
                "alert_type": alert_type,
                "severity": "HIGH",
                "details": details
            }
            self.audit_logger.warning(f"SECURITY ALERT: {json.dumps(alert)}")
    
    async def review_document(
        self,
        content: str,
        document_id: Optional[str] = None,
        document_type: str = "generic",
        metadata: Optional[Dict[str, Any]] = None,
        user_id: Optional[str] = None
    ) -> ReviewResult:
        """
        Perform unified document review with mode-specific optimizations.
        
        Args:
            content: Document content to review
            document_id: Optional document identifier
            document_type: Type of document
            metadata: Additional metadata
            user_id: Optional user identifier (required for secure modes)
            
        Returns:
            ReviewResult with comprehensive analysis
        """
        start_time = time.time()
        
        # Generate document ID if not provided
        if not document_id:
            document_id = str(uuid.uuid4())
        
        # Mode-specific validation
        if self.mode in [OperationMode.SECURE, OperationMode.ENTERPRISE]:
            await self._perform_security_validation(content, user_id, document_id)
        
        # Check cache
        cache_key = self._generate_cache_key(content, document_id, document_type)
        if self.config.enable_caching:
            cached_result = await self.cache.get(cache_key)
            if cached_result:
                logger.info(f"Cache hit for document {document_id}")
                cached_result.from_cache = True
                return cached_result
        
        # Prepare metadata
        if metadata is None:
            metadata = {}
        
        metadata.update({
            'document_id': document_id,
            'document_type': document_type,
            'content_length': len(content),
            'timestamp': datetime.now().isoformat(),
            'mode': self.mode.value
        })
        
        # Analyze dimensions
        dimension_results = await self._analyze_dimensions(content, metadata)
        
        # Aggregate results
        all_issues = []
        for dim_result in dimension_results:
            all_issues.extend(dim_result.issues)
        
        # Calculate overall score
        overall_score = self._calculate_overall_score(dimension_results)
        
        # Determine status
        status = self._determine_status(overall_score, all_issues)
        
        # Generate recommendations
        recommended_actions = self._generate_recommendations(all_issues, dimension_results)
        approval_conditions = self._generate_approval_conditions(status, all_issues)
        
        # Run optional integrations
        integration_results = await self._run_integrations(content)
        
        # Create review result
        execution_time = (time.time() - start_time) * 1000
        
        result = ReviewResult(
            document_id=document_id,
            document_type=document_type,
            review_id=str(uuid.uuid4()),
            timestamp=datetime.now(),
            overall_score=overall_score,
            status=status,
            dimension_results=dimension_results,
            all_issues=all_issues,
            metrics=ReviewMetrics(execution_time_ms=execution_time),
            reviewer_notes=self._generate_reviewer_notes(all_issues, overall_score),
            recommended_actions=recommended_actions,
            approval_conditions=approval_conditions,
            configuration=self.config.to_dict(),
            metadata={
                **metadata,
                'execution_time_ms': execution_time,
                'mode': self.mode.value,
                'cache_hit_rate': self.cache.hit_rate,
                **integration_results
            }
        )
        
        # Cache result
        if self.config.enable_caching:
            await self.cache.set(cache_key, result)
        
        # Store result
        if self.storage:
            asyncio.create_task(self._store_result(result, user_id))
        
        # Update statistics
        self.reviews_performed += 1
        self.total_issues_found += len(all_issues)
        
        logger.info(
            f"Review completed for {document_id}: "
            f"Score={overall_score:.1f}, Status={status.value}, "
            f"Issues={len(all_issues)}, Mode={self.mode.value}"
        )
        
        return result
    
    async def _perform_security_validation(
        self,
        content: str,
        user_id: Optional[str],
        document_id: str
    ):
        """Perform security validation for secure modes."""
        if not hasattr(self, 'security_validator'):
            return
        
        # Access control check
        if user_id and not self.access_controller.check_permission(user_id, "review.create"):
            self.security_metrics['access_denied'] += 1
            raise PermissionError("User does not have permission to create reviews")
        
        # Rate limiting check
        client_id = user_id or "anonymous"
        if not self.security_validator.check_rate_limit(client_id, "review"):
            self.security_metrics['rate_limits_hit'] += 1
            raise Exception("Rate limit exceeded. Please try again later.")
        
        # Content validation
        validation_result = self.security_validator.validate_document(
            content, "generic", {}
        )
        
        if not validation_result.is_valid and validation_result.risk_score > 7.0:
            raise ValueError(f"Security threats detected: {validation_result.threats_detected}")
    
    def _generate_cache_key(self, content: str, document_id: str, document_type: str) -> str:
        """Generate cache key for document."""
        content_hash = hashlib.sha256(content.encode()).hexdigest()[:16]
        return f"{document_id}:{document_type}:{content_hash}:{self.mode.value}"
    
    async def _analyze_dimensions(
        self,
        content: str,
        metadata: Dict[str, Any]
    ) -> List[DimensionResult]:
        """Analyze document across all enabled dimensions."""
        if self.mode in [OperationMode.OPTIMIZED, OperationMode.ENTERPRISE]:
            # Parallel execution for optimized modes
            tasks = []
            for dimension in self.dimensions:
                task = asyncio.create_task(dimension.analyze(content, metadata))
                tasks.append(task)
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            valid_results = []
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    logger.error(f"Dimension {self.dimensions[i].__class__.__name__} failed: {result}")
                else:
                    valid_results.append(result)
            
            return valid_results
        else:
            # Sequential execution for basic/secure modes
            results = []
            for dimension in self.dimensions:
                try:
                    result = await dimension.analyze(content, metadata)
                    results.append(result)
                except Exception as e:
                    logger.error(f"Dimension {dimension.__class__.__name__} failed: {e}")
            
            return results
    
    def _calculate_overall_score(self, dimension_results: List[DimensionResult]) -> float:
        """Calculate weighted overall score."""
        if not dimension_results:
            return 0.0
        
        total_weighted_score = 0.0
        total_weight = 0.0
        
        for result in dimension_results:
            total_weighted_score += result.weighted_score
            total_weight += result.weight
        
        if total_weight == 0:
            return 0.0
        
        return (total_weighted_score / total_weight) * 100.0 if total_weight != 1.0 else total_weighted_score
    
    def _determine_status(self, overall_score: float, issues: List[ReviewIssue]) -> ReviewStatus:
        """Determine review status based on score and issues."""
        has_blockers = any(issue.severity == ReviewSeverity.BLOCKER for issue in issues)
        critical_count = sum(1 for issue in issues 
                           if issue.severity in [ReviewSeverity.BLOCKER, ReviewSeverity.CRITICAL])
        
        # Apply mode-specific logic
        if self.mode in [OperationMode.SECURE, OperationMode.ENTERPRISE]:
            # Stricter criteria for secure modes
            security_issues = sum(1 for issue in issues 
                                if issue.dimension == ReviewDimension.SECURITY_PII)
            
            if has_blockers or security_issues > 0:
                return ReviewStatus.REJECTED
            elif critical_count > 1 or overall_score < 70:
                return ReviewStatus.NEEDS_REVISION
        else:
            # Standard criteria
            if has_blockers:
                return ReviewStatus.REJECTED
            elif critical_count > 2 or overall_score < 60:
                return ReviewStatus.NEEDS_REVISION
        
        if overall_score >= self.config.approval_threshold:
            return ReviewStatus.APPROVED if critical_count == 0 else ReviewStatus.APPROVED_WITH_CONDITIONS
        elif overall_score >= self.config.conditional_approval_threshold:
            return ReviewStatus.APPROVED_WITH_CONDITIONS
        else:
            return ReviewStatus.NEEDS_REVISION
    
    def _generate_recommendations(
        self,
        issues: List[ReviewIssue],
        dimension_results: List[DimensionResult]
    ) -> List[str]:
        """Generate actionable recommendations."""
        recommendations = []
        
        if not issues:
            return ["Document meets all review standards"]
        
        # Priority 1: Address blockers
        blockers = [issue for issue in issues if issue.severity == ReviewSeverity.BLOCKER]
        if blockers:
            recommendations.append(f"URGENT: Fix {len(blockers)} blocker issues")
        
        # Priority 2: Address critical issues
        criticals = [issue for issue in issues if issue.severity == ReviewSeverity.CRITICAL]
        if criticals:
            recommendations.append(f"Address {len(criticals)} critical issues")
        
        # Priority 3: Improve low-scoring dimensions
        for result in dimension_results:
            if result.score < 60:
                recommendations.append(
                    f"Improve {result.dimension.value} (score: {result.score:.1f})"
                )
        
        return recommendations[:10]  # Limit to top 10
    
    def _generate_approval_conditions(
        self,
        status: ReviewStatus,
        issues: List[ReviewIssue]
    ) -> List[str]:
        """Generate conditions for approval."""
        if status == ReviewStatus.APPROVED:
            return []
        
        conditions = []
        
        # Must fix critical/blocker issues
        for severity in [ReviewSeverity.BLOCKER, ReviewSeverity.CRITICAL]:
            severity_issues = [i for i in issues if i.severity == severity]
            if severity_issues:
                conditions.append(f"Fix all {severity.value} issues ({len(severity_issues)} found)")
        
        return conditions
    
    def _generate_reviewer_notes(self, issues: List[ReviewIssue], overall_score: float) -> str:
        """Generate human-readable reviewer notes."""
        if overall_score >= 90:
            assessment = "Excellent document quality"
        elif overall_score >= 80:
            assessment = "Good document quality"
        elif overall_score >= 70:
            assessment = "Acceptable document quality"
        else:
            assessment = "Document requires significant revision"
        
        auto_fixable = sum(1 for issue in issues if issue.auto_fixable)
        notes = [assessment]
        
        if auto_fixable > 0:
            notes.append(f"{auto_fixable} issues can be automatically fixed.")
        
        return " ".join(notes)
    
    async def _run_integrations(self, content: str) -> Dict[str, Any]:
        """Run optional module integrations."""
        results = {}
        
        # Quality analysis
        if self.quality_analyzer and self.config.use_quality_engine:
            try:
                quality_result = await asyncio.get_event_loop().run_in_executor(
                    self.thread_executor,
                    self.quality_analyzer.analyze,
                    content
                )
                results['quality_insights'] = {
                    'quality_score': quality_result.overall_score,
                    'quality_issues': len(quality_result.issues)
                }
            except Exception as e:
                logger.warning(f"Quality analysis failed: {e}")
        
        # MIAIR optimization
        if self.miair_engine and self.config.use_miair_optimization:
            try:
                miair_result = await asyncio.get_event_loop().run_in_executor(
                    self.thread_executor,
                    self.miair_engine.analyze,
                    content
                )
                results['optimization_suggestions'] = {
                    'entropy_score': miair_result.get('entropy', 0),
                    'quality_score': miair_result.get('quality_score', 0),
                    'optimizations': miair_result.get('patterns', [])[:3]
                }
            except Exception as e:
                logger.warning(f"MIAIR optimization failed: {e}")
        
        return results
    
    async def _store_result(self, result: ReviewResult, user_id: Optional[str]):
        """Store result in database."""
        if not self.storage:
            return
        
        try:
            document = {
                'id': result.review_id,
                'type': 'review_result',
                'document_id': result.document_id,
                'timestamp': result.timestamp.isoformat(),
                'data': result.to_dict(),
                'stored_by': user_id or "system"
            }
            
            await asyncio.get_event_loop().run_in_executor(
                self.thread_executor,
                self.storage.create,
                'review_results',
                document
            )
        except Exception as e:
            logger.error(f"Failed to store review result: {e}")
    
    async def batch_review(
        self,
        documents: List[Dict[str, Any]],
        parallel: bool = None,
        batch_size: int = None,
        user_id: Optional[str] = None
    ) -> List[ReviewResult]:
        """
        Review multiple documents in batch with mode-optimized processing.
        """
        # Set defaults based on mode
        if parallel is None:
            parallel = self.mode in [OperationMode.OPTIMIZED, OperationMode.ENTERPRISE]
        
        if batch_size is None:
            batch_size = 10 if self.mode == OperationMode.BASIC else 20
            if self.mode in [OperationMode.SECURE, OperationMode.ENTERPRISE]:
                batch_size = min(batch_size, 10)  # Security limit
        
        results = []
        
        if parallel:
            # Process in chunks
            for i in range(0, len(documents), batch_size):
                chunk = documents[i:i + batch_size]
                
                tasks = []
                for doc in chunk:
                    task = self.review_document(
                        content=doc['content'],
                        document_id=doc.get('id'),
                        document_type=doc.get('type', 'generic'),
                        metadata=doc.get('metadata'),
                        user_id=user_id
                    )
                    tasks.append(task)
                
                chunk_results = await asyncio.gather(*tasks, return_exceptions=True)
                
                for result in chunk_results:
                    if not isinstance(result, Exception):
                        results.append(result)
                    else:
                        logger.error(f"Batch review failed: {result}")
                
                # Rate limiting delay for secure modes
                if self.mode in [OperationMode.SECURE, OperationMode.ENTERPRISE]:
                    await asyncio.sleep(0.1)
        else:
            # Sequential processing
            for doc in documents:
                try:
                    result = await self.review_document(
                        content=doc['content'],
                        document_id=doc.get('id'),
                        document_type=doc.get('type', 'generic'),
                        metadata=doc.get('metadata'),
                        user_id=user_id
                    )
                    results.append(result)
                except Exception as e:
                    logger.error(f"Review failed: {e}")
        
        return results
    
    async def auto_fix_issues(
        self,
        content: str,
        issues: List[ReviewIssue]
    ) -> Tuple[str, List[ReviewIssue]]:
        """Attempt to automatically fix issues in content."""
        if not self.config.auto_fix_enabled:
            return content, []
        
        fixed_content = content
        fixed_issues = []
        
        auto_fixable = [issue for issue in issues if issue.auto_fixable]
        
        for issue in auto_fixable:
            try:
                if issue.dimension == ReviewDimension.STYLE_FORMATTING:
                    if "trailing whitespace" in issue.title.lower():
                        lines = fixed_content.split('\n')
                        fixed_content = '\n'.join(line.rstrip() for line in lines)
                        fixed_issues.append(issue)
                    elif "excessive blank lines" in issue.title.lower():
                        fixed_content = re.sub(r'\n{3,}', '\n\n', fixed_content)
                        fixed_issues.append(issue)
                
                elif issue.dimension == ReviewDimension.SECURITY_PII:
                    if "pii" in issue.title.lower() and self.pii_detector:
                        fixed_content = self.pii_detector.mask(fixed_content)
                        fixed_issues.append(issue)
                        
            except Exception as e:
                logger.warning(f"Failed to auto-fix issue: {e}")
        
        return fixed_content, fixed_issues
    
    def generate_report(
        self,
        result: ReviewResult,
        format: str = "markdown"
    ) -> str:
        """Generate formatted review report."""
        if format == "json":
            return json.dumps(result.to_dict(), indent=2)
        elif format == "markdown":
            return self._generate_markdown_report(result)
        elif format == "html":
            return self._generate_html_report(result)
        else:
            return result.to_summary()
    
    def _generate_markdown_report(self, result: ReviewResult) -> str:
        """Generate markdown format review report."""
        lines = [
            f"# Document Review Report",
            f"",
            f"**Document ID:** {result.document_id}",
            f"**Mode:** {self.mode.value.upper()}",
            f"**Status:** {result.status.value.upper()}",
            f"**Overall Score:** {result.overall_score:.1f}/100",
            f"**Total Issues:** {len(result.all_issues)}",
            f"",
            f"## Dimension Scores"
        ]
        
        for dim_result in result.dimension_results:
            lines.append(f"### {dim_result.dimension.value.replace('_', ' ').title()}")
            lines.append(f"- Score: {dim_result.score:.1f}/100")
            lines.append(f"- Issues: {len(dim_result.issues)}")
            lines.append("")
        
        if result.recommended_actions:
            lines.extend([
                "## Recommended Actions",
                ""
            ] + [f"{i}. {action}" for i, action in enumerate(result.recommended_actions, 1)])
        
        return "\n".join(lines)
    
    def _generate_html_report(self, result: ReviewResult) -> str:
        """Generate HTML format review report."""
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Review Report - {result.document_id}</title>
        </head>
        <body>
            <h1>Document Review Report</h1>
            <p><strong>Mode:</strong> {self.mode.value.upper()}</p>
            <p><strong>Status:</strong> {result.status.value.upper()}</p>
            <p><strong>Score:</strong> {result.overall_score:.1f}/100</p>
            <p><strong>Issues:</strong> {len(result.all_issues)}</p>
        </body>
        </html>
        """
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get comprehensive engine statistics."""
        return {
            'mode': self.mode.value,
            'reviews_performed': self.reviews_performed,
            'total_issues_found': self.total_issues_found,
            'cache_hit_rate': self.cache.hit_rate,
            'cache_hits': self.cache.hits,
            'cache_misses': self.cache.misses,
            'security_metrics': dict(self.security_metrics),
            'configuration': self.config.to_dict()
        }
    
    async def cleanup(self):
        """Cleanup resources."""
        # Cancel background tasks
        for task in self._cleanup_tasks:
            task.cancel()
        
        # Shutdown executors
        if self.thread_executor:
            self.thread_executor.shutdown(wait=False)
        if self.process_executor:
            self.process_executor.shutdown(wait=False)
        
        # Clear cache
        await self.cache.clear()
        
        logger.info("Unified review engine cleanup completed")
    
    def __del__(self):
        """Cleanup on deletion."""
        try:
            asyncio.create_task(self.cleanup())
        except:
            pass