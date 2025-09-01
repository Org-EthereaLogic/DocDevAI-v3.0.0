"""
M010 Security Module - Unified PII Detector

Consolidates advanced and optimized PII detectors with operation modes:
- BASIC: Core PII detection with standard patterns
- PERFORMANCE: Optimized detection with caching and parallelization
- SECURE/ENTERPRISE: Enhanced security with advanced ML and privacy protection

Supports multi-language PII detection, privacy levels, and compliance reporting.
"""

import asyncio
import json
import logging
import re
import time
import hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List, Optional, Union, Set, Tuple
from enum import Enum
from dataclasses import dataclass, field
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
from functools import lru_cache
from collections import defaultdict
import multiprocessing as mp

# Optional ML dependencies (for advanced modes)
try:
    import spacy
    import transformers
    ML_AVAILABLE = True
except ImportError:
    ML_AVAILABLE = False

logger = logging.getLogger(__name__)


class PIIOperationMode(str, Enum):
    """PII detection operation modes."""
    BASIC = "basic"
    PERFORMANCE = "performance"
    SECURE = "secure"
    ENTERPRISE = "enterprise"


class PIIDetectionMode(str, Enum):
    """PII detection modes."""
    STRICT = "strict"
    BALANCED = "balanced"
    PERMISSIVE = "permissive"


class PIILanguage(str, Enum):
    """Supported languages for PII detection."""
    ENGLISH = "en"
    SPANISH = "es"
    FRENCH = "fr"
    GERMAN = "de"
    ITALIAN = "it"
    PORTUGUESE = "pt"
    DUTCH = "nl"
    AUTO_DETECT = "auto"


class PIISensitivityLevel(str, Enum):
    """PII sensitivity levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class PrivacyLevel(str, Enum):
    """Privacy protection levels."""
    NONE = "none"
    BASIC = "basic"
    STANDARD = "standard"
    STRICT = "strict"


class MaskingStrategy(str, Enum):
    """PII masking strategies."""
    REDACT = "redact"           # Replace with [REDACTED]
    MASK = "mask"               # Replace with asterisks
    HASH = "hash"               # Replace with hash
    PARTIAL = "partial"         # Show partial information
    TOKENIZE = "tokenize"       # Replace with tokens


@dataclass
class PIIContext:
    """Context information for PII detection."""
    source_type: str = "unknown"
    document_classification: str = "unclassified"
    jurisdiction: str = "unknown"
    retention_policy: Optional[str] = None
    processing_purpose: Optional[str] = None


@dataclass
class PIIMatch:
    """Represents a detected PII match."""
    text: str
    pii_type: str
    confidence: float
    start_pos: int
    end_pos: int
    sensitivity: PIISensitivityLevel
    context: Optional[str] = None
    masked_text: Optional[str] = None
    recommendations: List[str] = field(default_factory=list)


@dataclass
class PIIConfig:
    """Configuration for PII detection."""
    mode: PIIOperationMode = PIIOperationMode.ENTERPRISE
    detection_mode: PIIDetectionMode = PIIDetectionMode.BALANCED
    language: PIILanguage = PIILanguage.AUTO_DETECT
    privacy_level: PrivacyLevel = PrivacyLevel.STANDARD
    masking_strategy: MaskingStrategy = MaskingStrategy.REDACT
    
    # Core settings
    enable_context_analysis: bool = True
    enable_ml_detection: bool = False
    confidence_threshold: float = 0.7
    include_metadata: bool = True
    
    # Performance optimization settings
    enable_parallel_processing: bool = False
    enable_result_caching: bool = False
    cache_ttl_minutes: int = 60
    max_workers: int = 4
    batch_size: int = 100
    
    # Advanced security settings
    enable_privacy_protection: bool = False
    enable_audit_logging: bool = False
    enable_compliance_reporting: bool = False
    gdpr_compliance: bool = False
    ccpa_compliance: bool = False
    
    def __post_init__(self):
        """Configure mode-specific settings."""
        if self.mode == PIIOperationMode.BASIC:
            self.enable_parallel_processing = False
            self.enable_result_caching = False
            self.enable_ml_detection = False
            self.enable_privacy_protection = False
            self.enable_audit_logging = False
            self.enable_compliance_reporting = False
            
        elif self.mode == PIIOperationMode.PERFORMANCE:
            self.enable_parallel_processing = True
            self.enable_result_caching = True
            self.max_workers = min(mp.cpu_count(), 8)
            self.batch_size = 500
            
        elif self.mode == PIIOperationMode.SECURE:
            self.enable_parallel_processing = True
            self.enable_result_caching = True
            self.enable_privacy_protection = True
            self.enable_audit_logging = True
            self.gdpr_compliance = True
            
        elif self.mode == PIIOperationMode.ENTERPRISE:
            self.enable_parallel_processing = True
            self.enable_result_caching = True
            self.enable_ml_detection = ML_AVAILABLE
            self.enable_privacy_protection = True
            self.enable_audit_logging = True
            self.enable_compliance_reporting = True
            self.gdpr_compliance = True
            self.ccpa_compliance = True


@dataclass
class PIIStatistics:
    """Statistics for PII detection operations."""
    total_documents_processed: int = 0
    total_pii_matches: int = 0
    matches_by_type: Dict[str, int] = field(default_factory=dict)
    matches_by_sensitivity: Dict[str, int] = field(default_factory=dict)
    avg_processing_time_ms: float = 0.0
    cache_hits: int = 0
    cache_misses: int = 0
    false_positives: int = 0
    false_negatives: int = 0
    last_updated: datetime = field(default_factory=datetime.now)


class UnifiedPIIDetector:
    """
    Unified PII Detector supporting multiple operation modes.
    
    Modes:
    - BASIC: Standard regex-based PII detection
    - PERFORMANCE: Optimized detection with caching and parallelization
    - SECURE: Enhanced privacy protection and audit logging
    - ENTERPRISE: Full ML-powered detection with compliance features
    """
    
    def __init__(self, config: Optional[PIIConfig] = None):
        """Initialize unified PII detector."""
        self.config = config or PIIConfig()
        self._result_cache = {}
        self._cache_lock = threading.RLock()
        self._statistics = PIIStatistics()
        
        # Performance components
        self._thread_pool = None
        if self.config.enable_parallel_processing:
            self._thread_pool = ThreadPoolExecutor(max_workers=self.config.max_workers)
        
        # ML components (advanced modes)
        self._nlp_model = None
        self._ml_classifier = None
        
        # PII patterns (compiled regex patterns for efficiency)
        self._pii_patterns = self._compile_pii_patterns()
        
        # Initialize ML components if available and enabled
        if self.config.enable_ml_detection and ML_AVAILABLE:
            self._initialize_ml_components()
        
        logger.info(f"Initialized PII detector in {self.config.mode.value} mode")
    
    def _compile_pii_patterns(self) -> Dict[str, Dict[str, Any]]:
        """Compile regex patterns for PII detection."""
        patterns = {
            'email': {
                'pattern': re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'),
                'sensitivity': PIISensitivityLevel.MEDIUM,
                'description': 'Email address'
            },
            'ssn': {
                'pattern': re.compile(r'\b\d{3}-?\d{2}-?\d{4}\b'),
                'sensitivity': PIISensitivityLevel.CRITICAL,
                'description': 'Social Security Number'
            },
            'phone': {
                'pattern': re.compile(r'\b(\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b'),
                'sensitivity': PIISensitivityLevel.MEDIUM,
                'description': 'Phone number'
            },
            'credit_card': {
                'pattern': re.compile(r'\b(?:\d{4}[-\s]?){3}\d{4}\b'),
                'sensitivity': PIISensitivityLevel.CRITICAL,
                'description': 'Credit card number'
            },
            'ip_address': {
                'pattern': re.compile(r'\b(?:\d{1,3}\.){3}\d{1,3}\b'),
                'sensitivity': PIISensitivityLevel.LOW,
                'description': 'IP address'
            },
            'date_of_birth': {
                'pattern': re.compile(r'\b\d{1,2}[/-]\d{1,2}[/-]\d{4}\b'),
                'sensitivity': PIISensitivityLevel.HIGH,
                'description': 'Date of birth'
            },
            'address': {
                'pattern': re.compile(r'\b\d+\s+[A-Za-z\s]+(?:Street|St|Avenue|Ave|Road|Rd|Boulevard|Blvd|Drive|Dr)\b', re.IGNORECASE),
                'sensitivity': PIISensitivityLevel.MEDIUM,
                'description': 'Street address'
            },
            'passport': {
                'pattern': re.compile(r'\b[A-Z]{1,2}\d{6,9}\b'),
                'sensitivity': PIISensitivityLevel.CRITICAL,
                'description': 'Passport number'
            },
            'license_plate': {
                'pattern': re.compile(r'\b[A-Z]{1,3}[-\s]?\d{3,4}\b'),
                'sensitivity': PIISensitivityLevel.LOW,
                'description': 'License plate'
            },
            'bank_account': {
                'pattern': re.compile(r'\b\d{8,17}\b'),
                'sensitivity': PIISensitivityLevel.CRITICAL,
                'description': 'Bank account number'
            }
        }
        
        # Add international patterns based on configuration
        if self.config.language != PIILanguage.ENGLISH:
            patterns.update(self._get_international_patterns())
        
        return patterns
    
    def _get_international_patterns(self) -> Dict[str, Dict[str, Any]]:
        """Get international PII patterns based on language/region."""
        international_patterns = {}
        
        if self.config.language in [PIILanguage.SPANISH, PIILanguage.AUTO_DETECT]:
            international_patterns['dni_spain'] = {
                'pattern': re.compile(r'\b\d{8}[A-Z]\b'),
                'sensitivity': PIISensitivityLevel.CRITICAL,
                'description': 'Spanish DNI'
            }
        
        if self.config.language in [PIILanguage.FRENCH, PIILanguage.AUTO_DETECT]:
            international_patterns['insee_france'] = {
                'pattern': re.compile(r'\b[12]\d{2}(0[1-9]|1[0-2])\d{2}\d{3}\d{2}\b'),
                'sensitivity': PIISensitivityLevel.CRITICAL,
                'description': 'French INSEE number'
            }
        
        return international_patterns
    
    def _initialize_ml_components(self):
        """Initialize ML components for advanced detection."""
        try:
            if ML_AVAILABLE:
                # Initialize spaCy model
                self._nlp_model = spacy.load("en_core_web_sm")
                logger.info("ML components initialized successfully")
            else:
                logger.warning("ML dependencies not available - falling back to regex patterns")
        except Exception as e:
            logger.error(f"Failed to initialize ML components: {e}")
            self.config.enable_ml_detection = False
    
    def detect_pii(self, content: str, context: Optional[PIIContext] = None) -> Dict[str, Any]:
        """Detect PII synchronously (basic mode)."""
        start_time = time.time()
        
        try:
            # Check cache first
            if self.config.enable_result_caching:
                cache_key = self._generate_cache_key(content, context)
                cached_result = self._get_cached_result(cache_key)
                if cached_result:
                    self._statistics.cache_hits += 1
                    return cached_result
                self._statistics.cache_misses += 1
            
            # Perform detection
            matches = self._detect_pii_basic(content, context)
            
            # Apply privacy protection if enabled
            if self.config.enable_privacy_protection:
                matches = self._apply_privacy_protection(matches)
            
            # Generate result
            result = self._generate_detection_result(content, matches, time.time() - start_time)
            
            # Cache result if caching is enabled
            if self.config.enable_result_caching:
                self._cache_result(cache_key, result)
            
            # Update statistics
            self._update_statistics(result)
            
            # Audit logging if enabled
            if self.config.enable_audit_logging:
                self._log_detection_audit(result, context)
            
            return result
            
        except Exception as e:
            logger.error(f"PII detection failed: {e}")
            raise
    
    async def detect_pii_async(self, content: str, context: Optional[PIIContext] = None) -> Dict[str, Any]:
        """Detect PII asynchronously (optimized modes)."""
        if self.config.mode == PIIOperationMode.BASIC:
            # Run synchronous detection in thread pool for basic mode
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, self.detect_pii, content, context)
        
        start_time = time.time()
        
        try:
            # Check cache first
            if self.config.enable_result_caching:
                cache_key = self._generate_cache_key(content, context)
                cached_result = self._get_cached_result(cache_key)
                if cached_result:
                    self._statistics.cache_hits += 1
                    return cached_result
                self._statistics.cache_misses += 1
            
            # Perform parallel detection
            matches = await self._detect_pii_async(content, context)
            
            # Apply privacy protection if enabled
            if self.config.enable_privacy_protection:
                matches = await self._apply_privacy_protection_async(matches)
            
            # Generate result
            result = self._generate_detection_result(content, matches, time.time() - start_time)
            
            # Cache result if caching is enabled
            if self.config.enable_result_caching:
                self._cache_result(cache_key, result)
            
            # Update statistics
            self._update_statistics(result)
            
            # Audit logging if enabled
            if self.config.enable_audit_logging:
                await self._log_detection_audit_async(result, context)
            
            return result
            
        except Exception as e:
            logger.error(f"Async PII detection failed: {e}")
            raise
    
    def _detect_pii_basic(self, content: str, context: Optional[PIIContext] = None) -> List[PIIMatch]:
        """Basic PII detection using regex patterns."""
        matches = []
        
        for pii_type, pattern_info in self._pii_patterns.items():
            pattern = pattern_info['pattern']
            sensitivity = pattern_info['sensitivity']
            description = pattern_info['description']
            
            for match in pattern.finditer(content):
                pii_match = PIIMatch(
                    text=match.group(),
                    pii_type=pii_type,
                    confidence=self._calculate_confidence(match.group(), pii_type),
                    start_pos=match.start(),
                    end_pos=match.end(),
                    sensitivity=sensitivity,
                    context=self._extract_context(content, match.start(), match.end()) if self.config.enable_context_analysis else None
                )
                
                # Apply confidence threshold
                if pii_match.confidence >= self.config.confidence_threshold:
                    matches.append(pii_match)
        
        return matches
    
    async def _detect_pii_async(self, content: str, context: Optional[PIIContext] = None) -> List[PIIMatch]:
        """Asynchronous PII detection with parallelization."""
        if not self._thread_pool:
            return self._detect_pii_basic(content, context)
        
        # Split content into chunks for parallel processing
        chunks = self._split_content_into_chunks(content)
        
        # Create tasks for each chunk
        tasks = []
        loop = asyncio.get_event_loop()
        
        for chunk_start, chunk_text in chunks:
            task = loop.run_in_executor(
                self._thread_pool, 
                self._detect_pii_in_chunk, 
                chunk_text, 
                chunk_start, 
                context
            )
            tasks.append(task)
        
        # Wait for all tasks to complete
        chunk_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Combine results
        matches = []
        for result in chunk_results:
            if isinstance(result, Exception):
                logger.error(f"Chunk processing failed: {result}")
            else:
                matches.extend(result)
        
        # Merge overlapping matches and sort by position
        matches = self._merge_overlapping_matches(matches)
        matches.sort(key=lambda x: x.start_pos)
        
        # Apply ML enhancement if enabled
        if self.config.enable_ml_detection and self._nlp_model:
            matches = await self._enhance_with_ml(content, matches)
        
        return matches
    
    def _split_content_into_chunks(self, content: str) -> List[Tuple[int, str]]:
        """Split content into chunks for parallel processing."""
        chunk_size = max(1000, len(content) // self.config.max_workers)
        chunks = []
        
        for i in range(0, len(content), chunk_size):
            chunk_start = i
            chunk_end = min(i + chunk_size, len(content))
            
            # Ensure we don't split in the middle of a word
            if chunk_end < len(content):
                while chunk_end > chunk_start and not content[chunk_end].isspace():
                    chunk_end -= 1
            
            chunk_text = content[chunk_start:chunk_end]
            chunks.append((chunk_start, chunk_text))
        
        return chunks
    
    def _detect_pii_in_chunk(self, chunk_text: str, chunk_start: int, context: Optional[PIIContext] = None) -> List[PIIMatch]:
        """Detect PII in a single chunk."""
        matches = []
        
        for pii_type, pattern_info in self._pii_patterns.items():
            pattern = pattern_info['pattern']
            sensitivity = pattern_info['sensitivity']
            
            for match in pattern.finditer(chunk_text):
                pii_match = PIIMatch(
                    text=match.group(),
                    pii_type=pii_type,
                    confidence=self._calculate_confidence(match.group(), pii_type),
                    start_pos=chunk_start + match.start(),
                    end_pos=chunk_start + match.end(),
                    sensitivity=sensitivity,
                    context=self._extract_context(chunk_text, match.start(), match.end()) if self.config.enable_context_analysis else None
                )
                
                if pii_match.confidence >= self.config.confidence_threshold:
                    matches.append(pii_match)
        
        return matches
    
    def _merge_overlapping_matches(self, matches: List[PIIMatch]) -> List[PIIMatch]:
        """Merge overlapping PII matches."""
        if not matches:
            return matches
        
        # Sort by start position
        sorted_matches = sorted(matches, key=lambda x: x.start_pos)
        merged = [sorted_matches[0]]
        
        for current in sorted_matches[1:]:
            last = merged[-1]
            
            # Check for overlap
            if current.start_pos <= last.end_pos:
                # Merge matches - keep the one with higher confidence
                if current.confidence > last.confidence:
                    merged[-1] = current
            else:
                merged.append(current)
        
        return merged
    
    async def _enhance_with_ml(self, content: str, matches: List[PIIMatch]) -> List[PIIMatch]:
        """Enhance detection results with ML analysis."""
        if not self._nlp_model:
            return matches
        
        try:
            # Process content with NLP model
            loop = asyncio.get_event_loop()
            doc = await loop.run_in_executor(self._thread_pool, self._nlp_model, content)
            
            # Analyze entities
            for ent in doc.ents:
                if ent.label_ in ['PERSON', 'ORG', 'GPE', 'MONEY', 'DATE']:
                    # Check if this entity overlaps with existing matches
                    overlaps = any(
                        m.start_pos <= ent.start_char < m.end_pos or 
                        ent.start_char <= m.start_pos < ent.end_char 
                        for m in matches
                    )
                    
                    if not overlaps:
                        # Add new ML-detected match
                        ml_match = PIIMatch(
                            text=ent.text,
                            pii_type=f"ml_{ent.label_.lower()}",
                            confidence=ent._.score if hasattr(ent._, 'score') else 0.8,
                            start_pos=ent.start_char,
                            end_pos=ent.end_char,
                            sensitivity=self._get_ml_sensitivity(ent.label_),
                            context=self._extract_context(content, ent.start_char, ent.end_char)
                        )
                        matches.append(ml_match)
            
        except Exception as e:
            logger.error(f"ML enhancement failed: {e}")
        
        return matches
    
    def _get_ml_sensitivity(self, label: str) -> PIISensitivityLevel:
        """Get sensitivity level for ML-detected entities."""
        sensitivity_map = {
            'PERSON': PIISensitivityLevel.HIGH,
            'ORG': PIISensitivityLevel.MEDIUM,
            'GPE': PIISensitivityLevel.LOW,
            'MONEY': PIISensitivityLevel.MEDIUM,
            'DATE': PIISensitivityLevel.MEDIUM
        }
        return sensitivity_map.get(label, PIISensitivityLevel.LOW)
    
    def _calculate_confidence(self, text: str, pii_type: str) -> float:
        """Calculate confidence score for PII match."""
        base_confidence = 0.8
        
        # Adjust confidence based on context and validation
        if pii_type == 'email' and '@' in text and '.' in text.split('@')[1]:
            return min(base_confidence + 0.15, 1.0)
        elif pii_type == 'ssn' and len(text.replace('-', '')) == 9:
            return min(base_confidence + 0.1, 1.0)
        elif pii_type == 'credit_card':
            # Basic Luhn algorithm check
            digits = ''.join(filter(str.isdigit, text))
            if len(digits) in [13, 14, 15, 16] and self._luhn_check(digits):
                return min(base_confidence + 0.2, 1.0)
        
        return base_confidence
    
    def _luhn_check(self, card_number: str) -> bool:
        """Perform Luhn algorithm check for credit card validation."""
        def digits_of(number):
            return [int(d) for d in str(number)]
        
        digits = digits_of(card_number)
        odd_digits = digits[-1::-2]
        even_digits = digits[-2::-2]
        checksum = sum(odd_digits)
        for digit in even_digits:
            checksum += sum(digits_of(digit * 2))
        
        return checksum % 10 == 0
    
    def _extract_context(self, content: str, start_pos: int, end_pos: int, context_length: int = 50) -> str:
        """Extract context around PII match."""
        context_start = max(0, start_pos - context_length)
        context_end = min(len(content), end_pos + context_length)
        
        context = content[context_start:context_end]
        
        # Mask the PII in the context
        pii_text = content[start_pos:end_pos]
        masked_pii = self._mask_text(pii_text, self.config.masking_strategy)
        context = context.replace(pii_text, masked_pii)
        
        return context.strip()
    
    def _apply_privacy_protection(self, matches: List[PIIMatch]) -> List[PIIMatch]:
        """Apply privacy protection to matches."""
        for match in matches:
            match.masked_text = self._mask_text(match.text, self.config.masking_strategy)
            
            # Add recommendations based on sensitivity
            if match.sensitivity == PIISensitivityLevel.CRITICAL:
                match.recommendations = [
                    "Immediate data classification required",
                    "Implement access controls",
                    "Enable encryption at rest and in transit",
                    "Consider data minimization"
                ]
            elif match.sensitivity == PIISensitivityLevel.HIGH:
                match.recommendations = [
                    "Data classification recommended",
                    "Review access permissions",
                    "Consider data retention policies"
                ]
        
        return matches
    
    async def _apply_privacy_protection_async(self, matches: List[PIIMatch]) -> List[PIIMatch]:
        """Apply privacy protection asynchronously."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(self._thread_pool, self._apply_privacy_protection, matches)
    
    def _mask_text(self, text: str, strategy: MaskingStrategy) -> str:
        """Mask text according to strategy."""
        if strategy == MaskingStrategy.REDACT:
            return "[REDACTED]"
        elif strategy == MaskingStrategy.MASK:
            return "*" * len(text)
        elif strategy == MaskingStrategy.HASH:
            return hashlib.sha256(text.encode()).hexdigest()[:16]
        elif strategy == MaskingStrategy.PARTIAL:
            if len(text) > 4:
                return text[:2] + "*" * (len(text) - 4) + text[-2:]
            else:
                return "*" * len(text)
        elif strategy == MaskingStrategy.TOKENIZE:
            return f"<TOKEN_{abs(hash(text)) % 10000}>"
        else:
            return text
    
    def _generate_detection_result(self, content: str, matches: List[PIIMatch], processing_time: float) -> Dict[str, Any]:
        """Generate comprehensive detection result."""
        # Categorize matches by type and sensitivity
        matches_by_type = defaultdict(int)
        matches_by_sensitivity = defaultdict(int)
        
        for match in matches:
            matches_by_type[match.pii_type] += 1
            matches_by_sensitivity[match.sensitivity.value] += 1
        
        # Calculate risk score
        risk_score = self._calculate_risk_score(matches)
        
        # Generate compliance assessment
        compliance_status = {}
        if self.config.enable_compliance_reporting:
            compliance_status = self._assess_compliance(matches)
        
        result = {
            'summary': {
                'total_matches': len(matches),
                'risk_score': risk_score,
                'processing_time_ms': processing_time * 1000,
                'content_length': len(content),
                'detection_mode': self.config.detection_mode.value,
                'confidence_threshold': self.config.confidence_threshold
            },
            'matches': [
                {
                    'text': match.text if not self.config.enable_privacy_protection else None,
                    'masked_text': match.masked_text,
                    'type': match.pii_type,
                    'confidence': match.confidence,
                    'sensitivity': match.sensitivity.value,
                    'position': {'start': match.start_pos, 'end': match.end_pos},
                    'context': match.context,
                    'recommendations': match.recommendations
                }
                for match in matches
            ],
            'statistics': {
                'by_type': dict(matches_by_type),
                'by_sensitivity': dict(matches_by_sensitivity)
            },
            'compliance': compliance_status,
            'metadata': {
                'detector_version': '3.0.0',
                'mode': self.config.mode.value,
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'ml_enhanced': self.config.enable_ml_detection and ML_AVAILABLE
            }
        }
        
        return result
    
    def _calculate_risk_score(self, matches: List[PIIMatch]) -> float:
        """Calculate overall risk score based on matches."""
        if not matches:
            return 0.0
        
        sensitivity_weights = {
            PIISensitivityLevel.LOW: 0.2,
            PIISensitivityLevel.MEDIUM: 0.5,
            PIISensitivityLevel.HIGH: 0.8,
            PIISensitivityLevel.CRITICAL: 1.0
        }
        
        total_weight = sum(sensitivity_weights[match.sensitivity] * match.confidence for match in matches)
        max_possible_weight = len(matches) * 1.0
        
        return min(total_weight / max_possible_weight, 1.0) if max_possible_weight > 0 else 0.0
    
    def _assess_compliance(self, matches: List[PIIMatch]) -> Dict[str, Any]:
        """Assess compliance with privacy regulations."""
        compliance = {
            'gdpr_compliant': True,
            'ccpa_compliant': True,
            'violations': [],
            'recommendations': []
        }
        
        critical_pii_types = ['ssn', 'credit_card', 'passport', 'bank_account']
        
        for match in matches:
            if match.pii_type in critical_pii_types:
                if self.config.gdpr_compliance:
                    compliance['violations'].append(f"GDPR: High-risk PII detected - {match.pii_type}")
                    compliance['gdpr_compliant'] = False
                
                if self.config.ccpa_compliance:
                    compliance['violations'].append(f"CCPA: Personal information detected - {match.pii_type}")
                    compliance['ccpa_compliant'] = False
        
        if not compliance['gdpr_compliant'] or not compliance['ccpa_compliant']:
            compliance['recommendations'].extend([
                "Implement data minimization practices",
                "Review data retention policies",
                "Ensure proper consent mechanisms",
                "Consider pseudonymization techniques"
            ])
        
        return compliance
    
    # Caching Methods
    
    def _generate_cache_key(self, content: str, context: Optional[PIIContext] = None) -> str:
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
    
    # Statistics and Logging Methods
    
    def _update_statistics(self, result: Dict[str, Any]):
        """Update detection statistics."""
        self._statistics.total_documents_processed += 1
        self._statistics.total_pii_matches += result['summary']['total_matches']
        
        # Update processing time average
        current_time = result['summary']['processing_time_ms']
        total_docs = self._statistics.total_documents_processed
        current_avg = self._statistics.avg_processing_time_ms
        
        new_avg = ((current_avg * (total_docs - 1)) + current_time) / total_docs
        self._statistics.avg_processing_time_ms = new_avg
        
        # Update type and sensitivity counters
        for pii_type, count in result['statistics']['by_type'].items():
            self._statistics.matches_by_type[pii_type] = \
                self._statistics.matches_by_type.get(pii_type, 0) + count
        
        for sensitivity, count in result['statistics']['by_sensitivity'].items():
            self._statistics.matches_by_sensitivity[sensitivity] = \
                self._statistics.matches_by_sensitivity.get(sensitivity, 0) + count
        
        self._statistics.last_updated = datetime.now()
    
    def _log_detection_audit(self, result: Dict[str, Any], context: Optional[PIIContext] = None):
        """Log detection audit information."""
        audit_entry = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'mode': self.config.mode.value,
            'matches_found': result['summary']['total_matches'],
            'risk_score': result['summary']['risk_score'],
            'context': context.__dict__ if context else None,
            'compliance_violations': len(result.get('compliance', {}).get('violations', [])),
            'processing_time_ms': result['summary']['processing_time_ms']
        }
        
        logger.info(f"PII Detection Audit: {json.dumps(audit_entry)}")
    
    async def _log_detection_audit_async(self, result: Dict[str, Any], context: Optional[PIIContext] = None):
        """Log detection audit information asynchronously."""
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self._log_detection_audit, result, context)
    
    # Health Check and Statistics Methods
    
    async def health_check(self) -> bool:
        """Perform health check of PII detector."""
        try:
            # Test basic functionality
            test_content = "Contact John Doe at john.doe@example.com or 555-123-4567"
            result = await self.detect_pii_async(test_content) if self.config.mode != PIIOperationMode.BASIC else self.detect_pii(test_content)
            
            # Verify detection worked
            if result['summary']['total_matches'] >= 2:  # Should find email and phone
                return True
            else:
                logger.warning("Health check detected fewer matches than expected")
                return False
                
        except Exception as e:
            logger.error(f"PII detector health check failed: {e}")
            return False
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get comprehensive detector statistics."""
        return {
            'mode': self.config.mode.value,
            'total_documents_processed': self._statistics.total_documents_processed,
            'total_pii_matches': self._statistics.total_pii_matches,
            'avg_processing_time_ms': round(self._statistics.avg_processing_time_ms, 2),
            'cache_hit_rate': (self._statistics.cache_hits / max(1, self._statistics.cache_hits + self._statistics.cache_misses)) * 100,
            'matches_by_type': dict(self._statistics.matches_by_type),
            'matches_by_sensitivity': dict(self._statistics.matches_by_sensitivity),
            'ml_enabled': self.config.enable_ml_detection and ML_AVAILABLE,
            'patterns_loaded': len(self._pii_patterns),
            'cache_size': len(self._result_cache),
            'last_updated': self._statistics.last_updated.isoformat()
        }
    
    def clear_cache(self):
        """Clear detection cache."""
        with self._cache_lock:
            self._result_cache.clear()
            self._statistics.cache_hits = 0
            self._statistics.cache_misses = 0
    
    def __del__(self):
        """Cleanup resources."""
        try:
            if self._thread_pool:
                self._thread_pool.shutdown(wait=False)
        except:
            pass


# Factory functions for different modes
def create_basic_pii_detector(config: Optional[PIIConfig] = None) -> UnifiedPIIDetector:
    """Create basic PII detector."""
    if config is None:
        config = PIIConfig(mode=PIIOperationMode.BASIC)
    return UnifiedPIIDetector(config)


def create_performance_pii_detector(config: Optional[PIIConfig] = None) -> UnifiedPIIDetector:
    """Create performance-optimized PII detector."""
    if config is None:
        config = PIIConfig(mode=PIIOperationMode.PERFORMANCE)
    return UnifiedPIIDetector(config)


def create_secure_pii_detector(config: Optional[PIIConfig] = None) -> UnifiedPIIDetector:
    """Create security-enhanced PII detector."""
    if config is None:
        config = PIIConfig(mode=PIIOperationMode.SECURE)
    return UnifiedPIIDetector(config)


def create_enterprise_pii_detector(config: Optional[PIIConfig] = None) -> UnifiedPIIDetector:
    """Create enterprise PII detector with all features."""
    if config is None:
        config = PIIConfig(mode=PIIOperationMode.ENTERPRISE)
    return UnifiedPIIDetector(config)