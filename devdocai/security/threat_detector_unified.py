"""
M010 Security Module - Unified Threat Detector

Consolidates basic and optimized threat detectors with operation modes:
- BASIC: Core threat detection with standard patterns
- PERFORMANCE: Optimized detection with caching and parallelization
- SECURE/ENTERPRISE: Enhanced security with advanced threat intelligence

Supports real-time threat detection, behavioral analysis, and threat intelligence integration.
"""

import asyncio
import json
import logging
import time
import hashlib
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, Any, List, Optional, Union, Set, Tuple
from enum import Enum
from dataclasses import dataclass, field
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
from functools import lru_cache
from collections import defaultdict, deque
import multiprocessing as mp
import re

# Optional optimization dependencies
try:
    import numpy as np
    import pandas as pd
    ANALYTICS_AVAILABLE = True
except ImportError:
    ANALYTICS_AVAILABLE = False

logger = logging.getLogger(__name__)


class ThreatOperationMode(str, Enum):
    """Threat detection operation modes."""
    BASIC = "basic"
    PERFORMANCE = "performance"
    SECURE = "secure"
    ENTERPRISE = "enterprise"


class ThreatLevel(str, Enum):
    """Threat severity levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ThreatType(str, Enum):
    """Types of security threats."""
    MALWARE = "malware"
    INJECTION = "injection"
    XSS = "xss"
    CSRF = "csrf"
    AUTHENTICATION_BYPASS = "auth_bypass"
    PRIVILEGE_ESCALATION = "privilege_escalation"
    DATA_EXFILTRATION = "data_exfiltration"
    DENIAL_OF_SERVICE = "dos"
    BRUTE_FORCE = "brute_force"
    SUSPICIOUS_ACTIVITY = "suspicious_activity"
    CODE_INJECTION = "code_injection"
    PATH_TRAVERSAL = "path_traversal"
    BUFFER_OVERFLOW = "buffer_overflow"
    UNKNOWN = "unknown"


class ThreatSeverity(Enum):
    """Threat severity levels for optimized mode."""
    INFORMATIONAL = "informational"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class SecurityThreat:
    """Represents a detected security threat."""
    threat_id: str
    threat_type: ThreatType
    severity: ThreatLevel
    confidence: float
    description: str
    source: str = "unknown"
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    affected_resources: List[str] = field(default_factory=list)
    indicators: List[str] = field(default_factory=list)
    mitigation_steps: List[str] = field(default_factory=list)
    false_positive_probability: float = 0.0
    context: Dict[str, Any] = field(default_factory=dict)
    related_threats: List[str] = field(default_factory=list)


@dataclass
class ThreatEvent:
    """Represents a threat event for optimized processing."""
    event_id: str
    timestamp: datetime
    event_type: str
    severity: ThreatSeverity
    source_ip: Optional[str] = None
    user_agent: Optional[str] = None
    payload: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass 
class ThreatConfig:
    """Configuration for threat detection."""
    mode: ThreatOperationMode = ThreatOperationMode.ENTERPRISE
    
    # Core settings
    enable_real_time_detection: bool = True
    enable_behavioral_analysis: bool = False
    confidence_threshold: float = 0.7
    severity_threshold: ThreatLevel = ThreatLevel.LOW
    max_detection_time_ms: int = 5000
    
    # Performance optimization settings
    enable_parallel_processing: bool = False
    enable_result_caching: bool = False
    enable_bloom_filtering: bool = False
    cache_ttl_minutes: int = 30
    max_workers: int = 4
    batch_size: int = 100
    
    # Advanced threat intelligence settings
    enable_threat_intelligence: bool = False
    enable_machine_learning: bool = False
    enable_anomaly_detection: bool = False
    threat_feed_urls: List[str] = field(default_factory=list)
    
    # Monitoring and alerting
    enable_alerting: bool = False
    enable_audit_logging: bool = False
    alert_webhook_url: Optional[str] = None
    max_alerts_per_hour: int = 100
    
    def __post_init__(self):
        """Configure mode-specific settings."""
        if self.mode == ThreatOperationMode.BASIC:
            self.enable_parallel_processing = False
            self.enable_result_caching = False
            self.enable_bloom_filtering = False
            self.enable_behavioral_analysis = False
            self.enable_threat_intelligence = False
            self.enable_machine_learning = False
            self.enable_anomaly_detection = False
            self.enable_alerting = False
            
        elif self.mode == ThreatOperationMode.PERFORMANCE:
            self.enable_parallel_processing = True
            self.enable_result_caching = True
            self.enable_bloom_filtering = ANALYTICS_AVAILABLE
            self.max_workers = min(mp.cpu_count(), 8)
            self.batch_size = 500
            
        elif self.mode == ThreatOperationMode.SECURE:
            self.enable_parallel_processing = True
            self.enable_result_caching = True
            self.enable_behavioral_analysis = True
            self.enable_alerting = True
            self.enable_audit_logging = True
            
        elif self.mode == ThreatOperationMode.ENTERPRISE:
            self.enable_parallel_processing = True
            self.enable_result_caching = True
            self.enable_bloom_filtering = ANALYTICS_AVAILABLE
            self.enable_behavioral_analysis = True
            self.enable_threat_intelligence = True
            self.enable_machine_learning = ANALYTICS_AVAILABLE
            self.enable_anomaly_detection = ANALYTICS_AVAILABLE
            self.enable_alerting = True
            self.enable_audit_logging = True


class BloomFilter:
    """Memory-efficient bloom filter for threat detection (performance mode)."""
    
    def __init__(self, capacity: int = 10000, error_rate: float = 0.1):
        if not ANALYTICS_AVAILABLE:
            raise RuntimeError("NumPy required for bloom filter operations")
            
        self.capacity = capacity
        self.error_rate = error_rate
        self.num_bits = int(-capacity * np.log(error_rate) / (np.log(2) ** 2))
        self.num_hashes = int(self.num_bits * np.log(2) / capacity)
        self.bit_array = np.zeros(self.num_bits, dtype=bool)
        self.count = 0
    
    def _hash(self, item: str, seed: int) -> int:
        """Generate hash for item with seed."""
        hash_value = hash(item + str(seed))
        return abs(hash_value) % self.num_bits
    
    def add(self, item: str):
        """Add item to bloom filter."""
        for i in range(self.num_hashes):
            index = self._hash(item, i)
            self.bit_array[index] = True
        self.count += 1
    
    def contains(self, item: str) -> bool:
        """Check if item might be in filter."""
        for i in range(self.num_hashes):
            index = self._hash(item, i)
            if not self.bit_array[index]:
                return False
        return True
    
    def clear(self):
        """Clear the bloom filter."""
        self.bit_array.fill(False)
        self.count = 0


class SlidingWindowCounter:
    """Sliding window counter for rate limiting and anomaly detection (performance mode)."""
    
    def __init__(self, window_size_minutes: int = 60, bucket_size_minutes: int = 1):
        self.window_size = window_size_minutes
        self.bucket_size = bucket_size_minutes
        self.num_buckets = window_size_minutes // bucket_size_minutes
        self.buckets = deque([0] * self.num_buckets, maxlen=self.num_buckets)
        self.bucket_timestamps = deque([datetime.now()] * self.num_buckets, maxlen=self.num_buckets)
        self.lock = threading.Lock()
    
    def increment(self, timestamp: Optional[datetime] = None):
        """Increment counter for current or specified timestamp."""
        if timestamp is None:
            timestamp = datetime.now()
        
        with self.lock:
            self._update_buckets(timestamp)
            self.buckets[-1] += 1
    
    def get_count(self, timestamp: Optional[datetime] = None) -> int:
        """Get total count in sliding window."""
        if timestamp is None:
            timestamp = datetime.now()
        
        with self.lock:
            self._update_buckets(timestamp)
            return sum(self.buckets)
    
    def _update_buckets(self, current_time: datetime):
        """Update buckets based on current time."""
        if not self.bucket_timestamps:
            return
        
        last_timestamp = self.bucket_timestamps[-1]
        time_diff = (current_time - last_timestamp).total_seconds() / 60  # in minutes
        
        if time_diff >= self.bucket_size:
            buckets_to_advance = min(int(time_diff // self.bucket_size), self.num_buckets)
            
            for _ in range(buckets_to_advance):
                self.buckets.append(0)
                self.bucket_timestamps.append(current_time)


@dataclass
class ThreatStatistics:
    """Statistics for threat detection operations."""
    total_detections: int = 0
    detections_by_type: Dict[str, int] = field(default_factory=dict)
    detections_by_severity: Dict[str, int] = field(default_factory=dict)
    false_positives: int = 0
    true_positives: int = 0
    avg_detection_time_ms: float = 0.0
    cache_hits: int = 0
    cache_misses: int = 0
    blocked_threats: int = 0
    last_detection: Optional[datetime] = None
    last_updated: datetime = field(default_factory=datetime.now)


class UnifiedThreatDetector:
    """
    Unified Threat Detector supporting multiple operation modes.
    
    Modes:
    - BASIC: Standard pattern-based threat detection
    - PERFORMANCE: Optimized detection with caching and parallelization
    - SECURE: Enhanced security with behavioral analysis and alerting
    - ENTERPRISE: Full ML-powered detection with threat intelligence
    """
    
    def __init__(self, config: Optional[ThreatConfig] = None):
        """Initialize unified threat detector."""
        self.config = config or ThreatConfig()
        self._result_cache = {}
        self._cache_lock = threading.RLock()
        self._statistics = ThreatStatistics()
        self._known_threats_cache = set()
        
        # Performance components
        self._thread_pool = None
        if self.config.enable_parallel_processing:
            self._thread_pool = ThreadPoolExecutor(max_workers=self.config.max_workers)
        
        # Optimized components (performance mode)
        self._bloom_filter = None
        self._sliding_window = None
        if self.config.enable_bloom_filtering and ANALYTICS_AVAILABLE:
            self._bloom_filter = BloomFilter(capacity=50000)
            self._sliding_window = SlidingWindowCounter(window_size_minutes=60)
        
        # Threat patterns (compiled for efficiency)
        self._threat_patterns = self._compile_threat_patterns()
        
        # Behavioral analysis components
        self._behavior_baselines = {}
        self._anomaly_thresholds = {}
        
        logger.info(f"Initialized threat detector in {self.config.mode.value} mode")
    
    def _compile_threat_patterns(self) -> Dict[ThreatType, List[Dict[str, Any]]]:
        """Compile threat detection patterns."""
        patterns = {
            ThreatType.MALWARE: [
                {
                    'pattern': re.compile(r'(eval|exec|system|shell_exec)\s*\(', re.IGNORECASE),
                    'description': 'Dynamic code execution',
                    'severity': ThreatLevel.HIGH
                },
                {
                    'pattern': re.compile(r'base64_decode\s*\(', re.IGNORECASE),
                    'description': 'Base64 decoding (potential payload)',
                    'severity': ThreatLevel.MEDIUM
                }
            ],
            ThreatType.INJECTION: [
                {
                    'pattern': re.compile(r"('|\"|;|--|\s+(OR|AND)\s+)", re.IGNORECASE),
                    'description': 'SQL injection patterns',
                    'severity': ThreatLevel.CRITICAL
                },
                {
                    'pattern': re.compile(r'(\$\{.*\}|#\{.*\})', re.IGNORECASE),
                    'description': 'Expression language injection',
                    'severity': ThreatLevel.HIGH
                }
            ],
            ThreatType.XSS: [
                {
                    'pattern': re.compile(r'<script\b[^>]*>.*?</script\b[^>]*>', re.IGNORECASE | re.DOTALL),
                    'description': 'Script tag injection',
                    'severity': ThreatLevel.HIGH
                },
                {
                    'pattern': re.compile(r'javascript:', re.IGNORECASE),
                    'description': 'JavaScript protocol injection',
                    'severity': ThreatLevel.MEDIUM
                }
            ],
            ThreatType.PATH_TRAVERSAL: [
                {
                    'pattern': re.compile(r'(\.\./|\.\.\\\|%2e%2e%2f|%2e%2e%5c)', re.IGNORECASE),
                    'description': 'Directory traversal attempt',
                    'severity': ThreatLevel.HIGH
                }
            ],
            ThreatType.CODE_INJECTION: [
                {
                    'pattern': re.compile(r'<%.*?%>', re.IGNORECASE | re.DOTALL),
                    'description': 'Server-side template injection',
                    'severity': ThreatLevel.CRITICAL
                },
                {
                    'pattern': re.compile(r'\$\(.*?\)', re.IGNORECASE),
                    'description': 'Command injection pattern',
                    'severity': ThreatLevel.HIGH
                }
            ],
            ThreatType.BRUTE_FORCE: [
                {
                    'pattern': re.compile(r'(login|auth|signin).*(failed|error|invalid)', re.IGNORECASE),
                    'description': 'Failed authentication attempt',
                    'severity': ThreatLevel.MEDIUM
                }
            ]
        }
        return patterns
    
    def detect_threats(self, data: Any, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Detect threats synchronously (basic mode)."""
        start_time = time.time()
        
        try:
            # Convert data to string for pattern matching
            content = self._prepare_content(data)
            
            # Check cache first
            if self.config.enable_result_caching:
                cache_key = self._generate_cache_key(content, context)
                cached_result = self._get_cached_result(cache_key)
                if cached_result:
                    self._statistics.cache_hits += 1
                    return cached_result
                self._statistics.cache_misses += 1
            
            # Perform threat detection
            threats = self._detect_threats_basic(content, context)
            
            # Apply behavioral analysis if enabled
            if self.config.enable_behavioral_analysis:
                threats = self._apply_behavioral_analysis(threats, context)
            
            # Generate result
            result = self._generate_detection_result(content, threats, time.time() - start_time)
            
            # Cache result if caching is enabled
            if self.config.enable_result_caching:
                self._cache_result(cache_key, result)
            
            # Update statistics
            self._update_statistics(result)
            
            # Handle alerting if enabled
            if self.config.enable_alerting and result['summary']['total_threats'] > 0:
                self._handle_alerts(result, context)
            
            # Audit logging if enabled
            if self.config.enable_audit_logging:
                self._log_detection_audit(result, context)
            
            return result
            
        except Exception as e:
            logger.error(f"Threat detection failed: {e}")
            raise
    
    async def detect_threats_async(self, data: Any, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Detect threats asynchronously (optimized modes)."""
        if self.config.mode == ThreatOperationMode.BASIC:
            # Run synchronous detection in thread pool for basic mode
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, self.detect_threats, data, context)
        
        start_time = time.time()
        
        try:
            # Convert data to string for pattern matching
            content = self._prepare_content(data)
            
            # Check cache first
            if self.config.enable_result_caching:
                cache_key = self._generate_cache_key(content, context)
                cached_result = self._get_cached_result(cache_key)
                if cached_result:
                    self._statistics.cache_hits += 1
                    return cached_result
                self._statistics.cache_misses += 1
            
            # Perform parallel threat detection
            threats = await self._detect_threats_async(content, context)
            
            # Apply behavioral analysis if enabled
            if self.config.enable_behavioral_analysis:
                threats = await self._apply_behavioral_analysis_async(threats, context)
            
            # Apply anomaly detection if enabled
            if self.config.enable_anomaly_detection:
                threats = await self._apply_anomaly_detection(threats, context)
            
            # Generate result
            result = self._generate_detection_result(content, threats, time.time() - start_time)
            
            # Cache result if caching is enabled
            if self.config.enable_result_caching:
                self._cache_result(cache_key, result)
            
            # Update statistics
            self._update_statistics(result)
            
            # Handle alerting if enabled
            if self.config.enable_alerting and result['summary']['total_threats'] > 0:
                await self._handle_alerts_async(result, context)
            
            # Audit logging if enabled
            if self.config.enable_audit_logging:
                await self._log_detection_audit_async(result, context)
            
            return result
            
        except Exception as e:
            logger.error(f"Async threat detection failed: {e}")
            raise
    
    def _prepare_content(self, data: Any) -> str:
        """Prepare data for threat detection."""
        if isinstance(data, str):
            return data
        elif isinstance(data, (dict, list)):
            return json.dumps(data, default=str)
        elif hasattr(data, '__dict__'):
            return json.dumps(data.__dict__, default=str)
        else:
            return str(data)
    
    def _detect_threats_basic(self, content: str, context: Optional[Dict[str, Any]] = None) -> List[SecurityThreat]:
        """Basic threat detection using pattern matching."""
        threats = []
        threat_id_counter = 0
        
        for threat_type, patterns in self._threat_patterns.items():
            for pattern_info in patterns:
                pattern = pattern_info['pattern']
                description = pattern_info['description']
                severity = pattern_info['severity']
                
                for match in pattern.finditer(content):
                    threat_id_counter += 1
                    threat = SecurityThreat(
                        threat_id=f"THR-{threat_id_counter:06d}",
                        threat_type=threat_type,
                        severity=severity,
                        confidence=self._calculate_confidence(match.group(), threat_type),
                        description=f"{description}: {match.group()[:100]}",
                        source="pattern_detection",
                        timestamp=datetime.now(timezone.utc),
                        indicators=[match.group()],
                        context=context or {}
                    )
                    
                    # Add basic mitigation steps
                    threat.mitigation_steps = self._get_mitigation_steps(threat_type)
                    
                    # Apply confidence threshold
                    if threat.confidence >= self.config.confidence_threshold:
                        threats.append(threat)
        
        return threats
    
    async def _detect_threats_async(self, content: str, context: Optional[Dict[str, Any]] = None) -> List[SecurityThreat]:
        """Asynchronous threat detection with parallelization."""
        if not self._thread_pool:
            return self._detect_threats_basic(content, context)
        
        # Split content into chunks for parallel processing
        chunks = self._split_content_into_chunks(content)
        
        # Create tasks for each chunk
        tasks = []
        loop = asyncio.get_event_loop()
        
        for chunk_start, chunk_text in chunks:
            task = loop.run_in_executor(
                self._thread_pool, 
                self._detect_threats_in_chunk, 
                chunk_text, 
                chunk_start, 
                context
            )
            tasks.append(task)
        
        # Wait for all tasks to complete
        chunk_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Combine results
        threats = []
        for result in chunk_results:
            if isinstance(result, Exception):
                logger.error(f"Chunk processing failed: {result}")
            else:
                threats.extend(result)
        
        # Remove duplicates and sort by severity
        threats = self._deduplicate_threats(threats)
        threats.sort(key=lambda x: (x.severity.value, -x.confidence), reverse=True)
        
        # Apply bloom filter for known threats if enabled
        if self._bloom_filter:
            threats = self._filter_known_threats(threats)
        
        return threats
    
    def _split_content_into_chunks(self, content: str) -> List[Tuple[int, str]]:
        """Split content into chunks for parallel processing."""
        chunk_size = max(1000, len(content) // self.config.max_workers)
        chunks = []
        
        for i in range(0, len(content), chunk_size):
            chunk_start = i
            chunk_end = min(i + chunk_size, len(content))
            
            # Ensure we don't split in the middle of a line
            if chunk_end < len(content):
                while chunk_end > chunk_start and content[chunk_end] != '\n':
                    chunk_end -= 1
            
            chunk_text = content[chunk_start:chunk_end]
            chunks.append((chunk_start, chunk_text))
        
        return chunks
    
    def _detect_threats_in_chunk(self, chunk_text: str, chunk_start: int, context: Optional[Dict[str, Any]] = None) -> List[SecurityThreat]:
        """Detect threats in a single chunk."""
        threats = []
        threat_id_counter = chunk_start
        
        for threat_type, patterns in self._threat_patterns.items():
            for pattern_info in patterns:
                pattern = pattern_info['pattern']
                description = pattern_info['description']
                severity = pattern_info['severity']
                
                for match in pattern.finditer(chunk_text):
                    threat_id_counter += 1
                    threat = SecurityThreat(
                        threat_id=f"THR-{threat_id_counter:06d}",
                        threat_type=threat_type,
                        severity=severity,
                        confidence=self._calculate_confidence(match.group(), threat_type),
                        description=f"{description}: {match.group()[:100]}",
                        source="parallel_detection",
                        timestamp=datetime.now(timezone.utc),
                        indicators=[match.group()],
                        context=context or {}
                    )
                    
                    threat.mitigation_steps = self._get_mitigation_steps(threat_type)
                    
                    if threat.confidence >= self.config.confidence_threshold:
                        threats.append(threat)
        
        return threats
    
    def _deduplicate_threats(self, threats: List[SecurityThreat]) -> List[SecurityThreat]:
        """Remove duplicate threats based on type and indicators."""
        seen_threats = set()
        deduplicated = []
        
        for threat in threats:
            threat_key = (threat.threat_type, tuple(threat.indicators))
            if threat_key not in seen_threats:
                seen_threats.add(threat_key)
                deduplicated.append(threat)
            else:
                # Find existing threat and update confidence if higher
                for existing_threat in deduplicated:
                    if (existing_threat.threat_type, tuple(existing_threat.indicators)) == threat_key:
                        if threat.confidence > existing_threat.confidence:
                            existing_threat.confidence = threat.confidence
                        break
        
        return deduplicated
    
    def _filter_known_threats(self, threats: List[SecurityThreat]) -> List[SecurityThreat]:
        """Filter out known threats using bloom filter."""
        if not self._bloom_filter:
            return threats
        
        filtered_threats = []
        for threat in threats:
            threat_signature = f"{threat.threat_type}:{threat.indicators[0] if threat.indicators else ''}"
            
            if not self._bloom_filter.contains(threat_signature):
                # New threat - add to bloom filter and include in results
                self._bloom_filter.add(threat_signature)
                filtered_threats.append(threat)
            else:
                # Known threat - still include if confidence is high or severity is critical
                if threat.confidence > 0.9 or threat.severity == ThreatLevel.CRITICAL:
                    filtered_threats.append(threat)
        
        return filtered_threats
    
    def _calculate_confidence(self, indicator: str, threat_type: ThreatType) -> float:
        """Calculate confidence score for threat detection."""
        base_confidence = 0.7
        
        # Adjust confidence based on threat type and indicator characteristics
        if threat_type == ThreatType.INJECTION:
            # SQL injection patterns
            if any(keyword in indicator.lower() for keyword in ['union', 'select', 'drop', 'delete']):
                base_confidence += 0.2
        elif threat_type == ThreatType.XSS:
            # XSS patterns
            if 'javascript:' in indicator.lower() or '<script' in indicator.lower():
                base_confidence += 0.15
        elif threat_type == ThreatType.MALWARE:
            # Malware patterns
            if any(func in indicator.lower() for func in ['eval', 'exec', 'system']):
                base_confidence += 0.1
        
        return min(base_confidence, 1.0)
    
    def _get_mitigation_steps(self, threat_type: ThreatType) -> List[str]:
        """Get mitigation steps for threat type."""
        mitigation_map = {
            ThreatType.INJECTION: [
                "Implement parameterized queries",
                "Use input validation and sanitization",
                "Apply principle of least privilege",
                "Enable SQL injection detection rules"
            ],
            ThreatType.XSS: [
                "Implement output encoding",
                "Use Content Security Policy (CSP)",
                "Validate and sanitize user inputs",
                "Enable XSS protection headers"
            ],
            ThreatType.MALWARE: [
                "Quarantine affected systems",
                "Run full system scan",
                "Update antivirus definitions",
                "Review system access logs"
            ],
            ThreatType.PATH_TRAVERSAL: [
                "Implement path canonicalization",
                "Use whitelist-based file access",
                "Restrict file system permissions",
                "Enable path traversal detection"
            ],
            ThreatType.CODE_INJECTION: [
                "Disable dynamic code execution",
                "Implement strict input validation",
                "Use secure coding practices",
                "Enable code injection detection"
            ],
            ThreatType.BRUTE_FORCE: [
                "Implement account lockout policies",
                "Enable rate limiting",
                "Use multi-factor authentication",
                "Monitor authentication logs"
            ]
        }
        
        return mitigation_map.get(threat_type, ["Apply general security hardening measures"])
    
    # Behavioral Analysis Methods
    
    def _apply_behavioral_analysis(self, threats: List[SecurityThreat], context: Optional[Dict[str, Any]] = None) -> List[SecurityThreat]:
        """Apply behavioral analysis to threats."""
        if not context:
            return threats
        
        # Analyze patterns and adjust threat scores
        for threat in threats:
            # Check for repeated patterns
            if self._is_repeated_pattern(threat, context):
                threat.confidence = min(threat.confidence + 0.1, 1.0)
                threat.description += " (repeated pattern detected)"
            
            # Check for suspicious timing
            if self._is_suspicious_timing(threat, context):
                threat.confidence = min(threat.confidence + 0.05, 1.0)
                threat.description += " (suspicious timing)"
        
        return threats
    
    async def _apply_behavioral_analysis_async(self, threats: List[SecurityThreat], context: Optional[Dict[str, Any]] = None) -> List[SecurityThreat]:
        """Apply behavioral analysis asynchronously."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(self._thread_pool, self._apply_behavioral_analysis, threats, context)
    
    def _is_repeated_pattern(self, threat: SecurityThreat, context: Dict[str, Any]) -> bool:
        """Check if threat represents a repeated pattern."""
        # Simple implementation - would be more sophisticated in production
        source_ip = context.get('source_ip')
        if source_ip and self._sliding_window:
            current_count = self._sliding_window.get_count()
            return current_count > 10  # Threshold for repeated attempts
        return False
    
    def _is_suspicious_timing(self, threat: SecurityThreat, context: Dict[str, Any]) -> bool:
        """Check for suspicious timing patterns."""
        # Check if multiple threats detected in short time window
        current_time = datetime.now(timezone.utc)
        recent_threshold = current_time - timedelta(minutes=5)
        
        if self._statistics.last_detection and self._statistics.last_detection > recent_threshold:
            return True
        return False
    
    async def _apply_anomaly_detection(self, threats: List[SecurityThreat], context: Optional[Dict[str, Any]] = None) -> List[SecurityThreat]:
        """Apply anomaly detection using ML techniques (enterprise mode)."""
        if not ANALYTICS_AVAILABLE or not context:
            return threats
        
        try:
            # Simple anomaly detection based on request patterns
            # In production, this would use more sophisticated ML models
            for threat in threats:
                anomaly_score = self._calculate_anomaly_score(threat, context)
                if anomaly_score > 0.8:
                    threat.confidence = min(threat.confidence + 0.15, 1.0)
                    threat.description += f" (anomaly score: {anomaly_score:.2f})"
        
        except Exception as e:
            logger.error(f"Anomaly detection failed: {e}")
        
        return threats
    
    def _calculate_anomaly_score(self, threat: SecurityThreat, context: Dict[str, Any]) -> float:
        """Calculate anomaly score for threat."""
        # Simple scoring based on available features
        score = 0.0
        
        # Check request size
        request_size = context.get('request_size', 0)
        if request_size > 10000:  # Large request
            score += 0.3
        
        # Check unusual user agent
        user_agent = context.get('user_agent', '')
        if not user_agent or 'bot' in user_agent.lower():
            score += 0.2
        
        # Check time of day (simple heuristic)
        current_hour = datetime.now().hour
        if current_hour < 6 or current_hour > 22:  # Off-hours
            score += 0.1
        
        # Check for multiple threat types
        if len(set(t.threat_type for t in [threat])) > 1:
            score += 0.2
        
        return min(score, 1.0)
    
    # Result Generation and Caching Methods
    
    def _generate_detection_result(self, content: str, threats: List[SecurityThreat], processing_time: float) -> Dict[str, Any]:
        """Generate comprehensive detection result."""
        # Categorize threats by type and severity
        threats_by_type = defaultdict(int)
        threats_by_severity = defaultdict(int)
        
        for threat in threats:
            threats_by_type[threat.threat_type.value] += 1
            threats_by_severity[threat.severity.value] += 1
        
        # Calculate overall risk score
        risk_score = self._calculate_risk_score(threats)
        
        # Generate recommendations
        recommendations = self._generate_recommendations(threats)
        
        result = {
            'summary': {
                'total_threats': len(threats),
                'risk_score': risk_score,
                'processing_time_ms': processing_time * 1000,
                'content_length': len(content),
                'detection_mode': self.config.mode.value,
                'confidence_threshold': self.config.confidence_threshold,
                'highest_severity': max([t.severity.value for t in threats], default='none')
            },
            'threats': [
                {
                    'id': threat.threat_id,
                    'type': threat.threat_type.value,
                    'severity': threat.severity.value,
                    'confidence': threat.confidence,
                    'description': threat.description,
                    'timestamp': threat.timestamp.isoformat(),
                    'source': threat.source,
                    'indicators': threat.indicators,
                    'mitigation_steps': threat.mitigation_steps,
                    'false_positive_probability': threat.false_positive_probability,
                    'affected_resources': threat.affected_resources,
                    'context': threat.context
                }
                for threat in threats
            ],
            'statistics': {
                'by_type': dict(threats_by_type),
                'by_severity': dict(threats_by_severity)
            },
            'recommendations': recommendations,
            'metadata': {
                'detector_version': '3.0.0',
                'mode': self.config.mode.value,
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'analytics_enabled': ANALYTICS_AVAILABLE and self.config.enable_machine_learning
            }
        }
        
        return result
    
    def _calculate_risk_score(self, threats: List[SecurityThreat]) -> float:
        """Calculate overall risk score based on threats."""
        if not threats:
            return 0.0
        
        severity_weights = {
            ThreatLevel.LOW: 0.2,
            ThreatLevel.MEDIUM: 0.5,
            ThreatLevel.HIGH: 0.8,
            ThreatLevel.CRITICAL: 1.0
        }
        
        total_weight = sum(severity_weights[threat.severity] * threat.confidence for threat in threats)
        max_possible_weight = len(threats) * 1.0
        
        return min(total_weight / max_possible_weight, 1.0) if max_possible_weight > 0 else 0.0
    
    def _generate_recommendations(self, threats: List[SecurityThreat]) -> List[str]:
        """Generate security recommendations based on detected threats."""
        recommendations = set()
        
        threat_types = set(threat.threat_type for threat in threats)
        
        if ThreatType.INJECTION in threat_types:
            recommendations.add("Implement comprehensive input validation")
            recommendations.add("Use parameterized queries and prepared statements")
        
        if ThreatType.XSS in threat_types:
            recommendations.add("Enable Content Security Policy (CSP)")
            recommendations.add("Implement output encoding for all user data")
        
        if ThreatType.MALWARE in threat_types:
            recommendations.add("Update antivirus and endpoint protection")
            recommendations.add("Conduct thorough system security audit")
        
        if len(threats) > 10:
            recommendations.add("Consider implementing Web Application Firewall (WAF)")
            recommendations.add("Enable real-time threat monitoring")
        
        # Add severity-based recommendations
        critical_threats = [t for t in threats if t.severity == ThreatLevel.CRITICAL]
        if critical_threats:
            recommendations.add("Immediate security review required for critical threats")
            recommendations.add("Consider temporarily restricting access")
        
        return list(recommendations)
    
    # Caching Methods
    
    def _generate_cache_key(self, content: str, context: Optional[Dict[str, Any]] = None) -> str:
        """Generate cache key for content and context."""
        content_hash = hashlib.sha256(content.encode()).hexdigest()
        context_hash = hashlib.sha256(str(context).encode()).hexdigest() if context else "no_context"
        return f"{content_hash}_{context_hash}_{self.config.confidence_threshold}"
    
    def _get_cached_result(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """Get cached result if available and not expired."""
        with self._cache_lock:
            if cache_key in self._result_cache:
                result, timestamp = self._result_cache[cache_key]
                if time.time() - timestamp < (self.config.cache_ttl_minutes * 60):
                    return result
                else:
                    del self._result_cache[cache_key]
        return None
    
    def _cache_result(self, cache_key: str, result: Dict[str, Any]):
        """Cache detection result."""
        with self._cache_lock:
            # Implement simple LRU eviction
            if len(self._result_cache) >= 1000:
                # Remove oldest entry
                oldest_key = min(self._result_cache.keys(), 
                               key=lambda k: self._result_cache[k][1])
                del self._result_cache[oldest_key]
            
            self._result_cache[cache_key] = (result, time.time())
    
    # Statistics and Alerting Methods
    
    def _update_statistics(self, result: Dict[str, Any]):
        """Update detection statistics."""
        self._statistics.total_detections += result['summary']['total_threats']
        self._statistics.last_detection = datetime.now()
        
        # Update type and severity counters
        for threat_type, count in result['statistics']['by_type'].items():
            self._statistics.detections_by_type[threat_type] = \
                self._statistics.detections_by_type.get(threat_type, 0) + count
        
        for severity, count in result['statistics']['by_severity'].items():
            self._statistics.detections_by_severity[severity] = \
                self._statistics.detections_by_severity.get(severity, 0) + count
        
        # Update sliding window counter
        if self._sliding_window:
            self._sliding_window.increment()
        
        self._statistics.last_updated = datetime.now()
    
    def _handle_alerts(self, result: Dict[str, Any], context: Optional[Dict[str, Any]] = None):
        """Handle alerting for detected threats."""
        high_severity_threats = [
            threat for threat in result['threats'] 
            if threat['severity'] in ['high', 'critical']
        ]
        
        if high_severity_threats and self.config.alert_webhook_url:
            # In production, this would send actual alerts
            alert_data = {
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'total_threats': len(high_severity_threats),
                'highest_severity': max(t['severity'] for t in high_severity_threats),
                'context': context,
                'threats': high_severity_threats[:5]  # Limit alert size
            }
            
            logger.warning(f"Security Alert: {json.dumps(alert_data)}")
    
    async def _handle_alerts_async(self, result: Dict[str, Any], context: Optional[Dict[str, Any]] = None):
        """Handle alerting asynchronously."""
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self._handle_alerts, result, context)
    
    def _log_detection_audit(self, result: Dict[str, Any], context: Optional[Dict[str, Any]] = None):
        """Log detection audit information."""
        audit_entry = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'mode': self.config.mode.value,
            'threats_detected': result['summary']['total_threats'],
            'risk_score': result['summary']['risk_score'],
            'processing_time_ms': result['summary']['processing_time_ms'],
            'context': context,
            'highest_severity': result['summary']['highest_severity']
        }
        
        logger.info(f"Threat Detection Audit: {json.dumps(audit_entry)}")
    
    async def _log_detection_audit_async(self, result: Dict[str, Any], context: Optional[Dict[str, Any]] = None):
        """Log detection audit information asynchronously."""
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self._log_detection_audit, result, context)
    
    # Health Check and Utility Methods
    
    async def health_check(self) -> bool:
        """Perform health check of threat detector."""
        try:
            # Test basic functionality
            test_content = "SELECT * FROM users WHERE id = 1 OR 1=1; <script>alert('xss')</script>"
            result = await self.detect_threats_async(test_content) if self.config.mode != ThreatOperationMode.BASIC else self.detect_threats(test_content)
            
            # Verify detection worked
            if result['summary']['total_threats'] >= 2:  # Should find SQL injection and XSS
                return True
            else:
                logger.warning("Health check detected fewer threats than expected")
                return False
                
        except Exception as e:
            logger.error(f"Threat detector health check failed: {e}")
            return False
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get comprehensive detector statistics."""
        return {
            'mode': self.config.mode.value,
            'total_detections': self._statistics.total_detections,
            'detections_by_type': dict(self._statistics.detections_by_type),
            'detections_by_severity': dict(self._statistics.detections_by_severity),
            'false_positives': self._statistics.false_positives,
            'true_positives': self._statistics.true_positives,
            'avg_detection_time_ms': round(self._statistics.avg_detection_time_ms, 2),
            'cache_hit_rate': (self._statistics.cache_hits / max(1, self._statistics.cache_hits + self._statistics.cache_misses)) * 100,
            'blocked_threats': self._statistics.blocked_threats,
            'patterns_loaded': sum(len(patterns) for patterns in self._threat_patterns.values()),
            'cache_size': len(self._result_cache),
            'bloom_filter_enabled': self._bloom_filter is not None,
            'analytics_available': ANALYTICS_AVAILABLE,
            'last_detection': self._statistics.last_detection.isoformat() if self._statistics.last_detection else None,
            'last_updated': self._statistics.last_updated.isoformat()
        }
    
    def clear_cache(self):
        """Clear detection cache."""
        with self._cache_lock:
            self._result_cache.clear()
            self._statistics.cache_hits = 0
            self._statistics.cache_misses = 0
        
        if self._bloom_filter:
            self._bloom_filter.clear()
    
    def __del__(self):
        """Cleanup resources."""
        try:
            if self._thread_pool:
                self._thread_pool.shutdown(wait=False)
        except:
            pass


# Factory functions for different modes
def create_basic_threat_detector(config: Optional[ThreatConfig] = None) -> UnifiedThreatDetector:
    """Create basic threat detector."""
    if config is None:
        config = ThreatConfig(mode=ThreatOperationMode.BASIC)
    return UnifiedThreatDetector(config)


def create_performance_threat_detector(config: Optional[ThreatConfig] = None) -> UnifiedThreatDetector:
    """Create performance-optimized threat detector."""
    if config is None:
        config = ThreatConfig(mode=ThreatOperationMode.PERFORMANCE)
    return UnifiedThreatDetector(config)


def create_secure_threat_detector(config: Optional[ThreatConfig] = None) -> UnifiedThreatDetector:
    """Create security-enhanced threat detector."""
    if config is None:
        config = ThreatConfig(mode=ThreatOperationMode.SECURE)
    return UnifiedThreatDetector(config)


def create_enterprise_threat_detector(config: Optional[ThreatConfig] = None) -> UnifiedThreatDetector:
    """Create enterprise threat detector with all features."""
    if config is None:
        config = ThreatConfig(mode=ThreatOperationMode.ENTERPRISE)
    return UnifiedThreatDetector(config)