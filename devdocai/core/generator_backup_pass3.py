"""
M004 Document Generator - AI-Powered Documentation Generation
DevDocAI v3.0.0 - Pass 1: Core Implementation

This module provides AI-powered document generation using LLM integration.
Templates guide AI prompts, not content substitution.
"""

import os
import json
import yaml
import asyncio
import logging
import hashlib
import hmac
import time
import pickle
import secrets
import psutil
from pathlib import Path
from typing import Dict, Any, List, Optional, Union, Tuple, Set
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
from collections import OrderedDict, defaultdict
import re
import ast
from functools import lru_cache, wraps
import threading
from queue import Queue, Empty
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
import base64

# Local imports
from ..core.config import ConfigurationManager
from ..core.storage import StorageManager, Document, DocumentMetadata
from ..intelligence.llm_adapter import LLMAdapter, LLMResponse

logger = logging.getLogger(__name__)


# ============================================================================
# Exceptions
# ============================================================================

class DocumentGenerationError(Exception):
    """Base exception for document generation errors."""
    pass


class TemplateNotFoundError(DocumentGenerationError):
    """Raised when a template cannot be found."""
    pass


class ContextExtractionError(DocumentGenerationError):
    """Raised when context extraction fails."""
    pass


class QualityValidationError(DocumentGenerationError):
    """Raised when document quality validation fails."""
    pass


class PromptConstructionError(DocumentGenerationError):
    """Raised when prompt construction fails."""
    pass


# ============================================================================
# Security Manager - Pass 3 Security Hardening
# ============================================================================

class SecurityManager:
    """Centralized security management for high-throughput document generation."""
    
    def __init__(self, config: ConfigurationManager):
        """Initialize security manager with enterprise-grade controls."""
        self.config = config
        
        # Security configuration
        self.max_batch_size = getattr(config.security, 'max_batch_size', 1000)
        self.max_file_count = getattr(config.security, 'max_file_count', 1000)
        self.max_cache_size = getattr(config.security, 'max_cache_size', 10000)
        self.rate_limit_per_minute = getattr(config.security, 'rate_limit_per_minute', 240)  # 4 docs/sec
        self.path_traversal_enabled = getattr(config.security, 'path_traversal_protection', True)
        
        # Resource quotas per memory mode
        self.resource_quotas = {
            'baseline': {'memory_mb': 512, 'cpu_percent': 25, 'concurrent': 10},
            'standard': {'memory_mb': 1024, 'cpu_percent': 50, 'concurrent': 50},
            'enhanced': {'memory_mb': 2048, 'cpu_percent': 75, 'concurrent': 200},
            'performance': {'memory_mb': 4096, 'cpu_percent': 100, 'concurrent': 1000}
        }
        
        # Rate limiting
        self.request_timestamps = defaultdict(list)
        self.rate_limit_lock = threading.RLock()
        
        # Security audit logging
        self.audit_log = []
        self.audit_lock = threading.RLock()
        
        # Cache security
        self.cache_salt = secrets.token_bytes(32)
        self.cache_key = self._derive_cache_key()
        
        # Path validation patterns
        self.path_blacklist = [
            r'\.\./',  # Parent directory traversal
            r'^/',     # Absolute paths
            r'^\~',    # Home directory
            r'[<>"|?*]',  # Invalid path characters
            r'\.git',  # Git directories
            r'\.env',  # Environment files
            r'\.ssh',  # SSH directories
            r'\.aws',  # AWS credentials
            r'node_modules',  # Dependency directories
            r'__pycache__',  # Python cache
        ]
        
        # PII patterns from M008
        self.pii_patterns = [
            (r'\b[A-Z][a-z]+ [A-Z][a-z]+\b', 'NAME'),
            (r'\b\d{3}-\d{2}-\d{4}\b', 'SSN'),
            (r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', 'EMAIL'),
            (r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b', 'PHONE'),
            (r'\b\d{16}\b', 'CREDIT_CARD'),
            (r'\b(?:\d{1,3}\.){3}\d{1,3}\b', 'IP_ADDRESS'),
        ]
        
        # Initialize metrics
        self.security_metrics = {
            'cache_validations': 0,
            'path_validations': 0,
            'rate_limit_blocks': 0,
            'pii_detections': 0,
            'injection_attempts': 0,
            'resource_violations': 0
        }
    
    def _derive_cache_key(self) -> bytes:
        """Derive encryption key for cache using PBKDF2."""
        # Get master key from config (should be encrypted)
        master_key = getattr(self.config.security, 'master_key', b'default_key_change_me')
        if isinstance(master_key, str):
            master_key = master_key.encode()
        
        # Derive key using PBKDF2 with SHA256
        from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2
        kdf = PBKDF2(
            algorithm=hashes.SHA256(),
            length=32,
            salt=self.cache_salt,
            iterations=100000,
            backend=default_backend()
        )
        return kdf.derive(master_key)
    
    def validate_path(self, path: Union[str, Path]) -> bool:
        """Validate file path against security rules."""
        self.security_metrics['path_validations'] += 1
        
        if not self.path_traversal_enabled:
            return True
        
        try:
            # Convert to Path object
            path_obj = Path(path) if isinstance(path, str) else path
            
            # Resolve to absolute path to check traversal
            resolved = path_obj.resolve()
            
            # Check if path is within allowed directory
            allowed_dir = Path.cwd()
            if not str(resolved).startswith(str(allowed_dir)):
                self._log_security_event('PATH_TRAVERSAL', {'path': str(path), 'resolved': str(resolved)})
                return False
            
            # Check against blacklist patterns
            path_str = str(path)
            for pattern in self.path_blacklist:
                if re.search(pattern, path_str):
                    self._log_security_event('PATH_BLACKLIST', {'path': path_str, 'pattern': pattern})
                    return False
            
            return True
            
        except Exception as e:
            self._log_security_event('PATH_VALIDATION_ERROR', {'path': str(path), 'error': str(e)})
            return False
    
    def validate_batch_size(self, batch_size: int) -> bool:
        """Validate batch size against limits."""
        if batch_size > self.max_batch_size:
            self.security_metrics['resource_violations'] += 1
            self._log_security_event('BATCH_SIZE_EXCEEDED', {'size': batch_size, 'max': self.max_batch_size})
            return False
        return True
    
    def check_rate_limit(self, user_id: str = 'default') -> bool:
        """Check if request is within rate limits."""
        with self.rate_limit_lock:
            now = time.time()
            
            # Clean old timestamps
            self.request_timestamps[user_id] = [
                ts for ts in self.request_timestamps[user_id]
                if now - ts < 60
            ]
            
            # Check limit
            if len(self.request_timestamps[user_id]) >= self.rate_limit_per_minute:
                self.security_metrics['rate_limit_blocks'] += 1
                self._log_security_event('RATE_LIMIT_EXCEEDED', {'user_id': user_id})
                return False
            
            # Add current timestamp
            self.request_timestamps[user_id].append(now)
            return True
    
    def sanitize_input(self, text: str) -> str:
        """Sanitize input text for injection attacks."""
        if not text:
            return text
        
        # Check for potential injection patterns
        injection_patterns = [
            r'<script[^>]*>.*?</script>',  # Script tags
            r'javascript:',  # JavaScript protocol
            r'on\w+\s*=',  # Event handlers
            r'\{\{.*?\}\}',  # Template injection
            r'\$\{.*?\}',  # Template literals
            r'`.*?`',  # Backticks (command injection)
        ]
        
        for pattern in injection_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                self.security_metrics['injection_attempts'] += 1
                self._log_security_event('INJECTION_ATTEMPT', {'pattern': pattern})
                # Remove the injection attempt
                text = re.sub(pattern, '', text, flags=re.IGNORECASE)
        
        return text
    
    def detect_pii(self, text: str) -> List[Tuple[str, str]]:
        """Detect PII in text content."""
        detections = []
        
        for pattern, pii_type in self.pii_patterns:
            matches = re.findall(pattern, text)
            if matches:
                self.security_metrics['pii_detections'] += len(matches)
                for match in matches:
                    detections.append((match, pii_type))
                    self._log_security_event('PII_DETECTED', {'type': pii_type, 'count': len(matches)})
        
        return detections
    
    def sign_cache_entry(self, content: str, fingerprint: str) -> str:
        """Generate HMAC signature for cache entry."""
        message = f"{fingerprint}:{content}".encode()
        signature = hmac.new(self.cache_key, message, hashlib.sha256).digest()
        return base64.b64encode(signature).decode()
    
    def verify_cache_signature(self, content: str, fingerprint: str, signature: str) -> bool:
        """Verify HMAC signature of cache entry."""
        self.security_metrics['cache_validations'] += 1
        
        try:
            expected_signature = self.sign_cache_entry(content, fingerprint)
            return hmac.compare_digest(signature, expected_signature)
        except Exception as e:
            self._log_security_event('CACHE_SIGNATURE_INVALID', {'error': str(e)})
            return False
    
    def encrypt_cache_content(self, content: bytes) -> bytes:
        """Encrypt cache content for L3 disk storage."""
        # Generate random IV
        iv = os.urandom(16)
        
        # Create cipher
        cipher = Cipher(
            algorithms.AES(self.cache_key),
            modes.GCM(iv),
            backend=default_backend()
        )
        
        encryptor = cipher.encryptor()
        ciphertext = encryptor.update(content) + encryptor.finalize()
        
        # Return IV + tag + ciphertext
        return iv + encryptor.tag + ciphertext
    
    def decrypt_cache_content(self, encrypted: bytes) -> bytes:
        """Decrypt cache content from L3 disk storage."""
        # Extract IV, tag, and ciphertext
        iv = encrypted[:16]
        tag = encrypted[16:32]
        ciphertext = encrypted[32:]
        
        # Create cipher
        cipher = Cipher(
            algorithms.AES(self.cache_key),
            modes.GCM(iv, tag),
            backend=default_backend()
        )
        
        decryptor = cipher.decryptor()
        return decryptor.update(ciphertext) + decryptor.finalize()
    
    def validate_ast_node(self, node: ast.AST) -> bool:
        """Validate AST node for safe parsing."""
        # Blacklist of dangerous AST node types
        dangerous_nodes = [
            ast.Import,
            ast.ImportFrom,
            ast.Call,  # Could call dangerous functions
            ast.Exec,  # Direct code execution (Python 2)
            ast.Global,
            ast.Nonlocal,
        ]
        
        for dangerous in dangerous_nodes:
            if isinstance(node, dangerous):
                self._log_security_event('DANGEROUS_AST_NODE', {'node_type': type(node).__name__})
                return False
        
        # Recursively check child nodes
        for child in ast.walk(node):
            if any(isinstance(child, d) for d in dangerous_nodes):
                return False
        
        return True
    
    def get_resource_quota(self, memory_mode: str) -> Dict[str, int]:
        """Get resource quota for memory mode."""
        return self.resource_quotas.get(memory_mode, self.resource_quotas['standard'])
    
    def _log_security_event(self, event_type: str, details: Dict[str, Any]):
        """Log security event with tamper protection."""
        with self.audit_lock:
            event = {
                'timestamp': datetime.now().isoformat(),
                'event_type': event_type,
                'details': details,
                'correlation_id': secrets.token_hex(8)
            }
            
            # Sign the event for tamper protection
            event_str = json.dumps(event, sort_keys=True)
            event['signature'] = hmac.new(
                self.cache_key, 
                event_str.encode(), 
                hashlib.sha256
            ).hexdigest()
            
            self.audit_log.append(event)
            
            # Also log to standard logger
            logger.warning(f"Security Event: {event_type} - {details}")
            
            # Rotate log if too large
            if len(self.audit_log) > 10000:
                self.audit_log = self.audit_log[-5000:]
    
    def get_security_metrics(self) -> Dict[str, Any]:
        """Get security metrics and audit summary."""
        with self.audit_lock:
            recent_events = defaultdict(int)
            for event in self.audit_log[-1000:]:
                recent_events[event['event_type']] += 1
            
            return {
                'metrics': self.security_metrics.copy(),
                'recent_events': dict(recent_events),
                'audit_log_size': len(self.audit_log)
            }
    
    def validate_resource_usage(self, memory_mb: float, cpu_percent: float, concurrent: int, memory_mode: str) -> bool:
        """Validate resource usage against quotas."""
        quota = self.get_resource_quota(memory_mode)
        
        violations = []
        if memory_mb > quota['memory_mb']:
            violations.append(f"Memory: {memory_mb}MB > {quota['memory_mb']}MB")
        if cpu_percent > quota['cpu_percent']:
            violations.append(f"CPU: {cpu_percent}% > {quota['cpu_percent']}%")
        if concurrent > quota['concurrent']:
            violations.append(f"Concurrent: {concurrent} > {quota['concurrent']}")
        
        if violations:
            self.security_metrics['resource_violations'] += 1
            self._log_security_event('RESOURCE_QUOTA_EXCEEDED', {
                'violations': violations,
                'memory_mode': memory_mode
            })
            return False
        
        return True


# ============================================================================
# Data Classes
# ============================================================================

@dataclass
class ValidationResult:
    """Result of document validation."""
    is_valid: bool
    score: float
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    suggestions: List[str] = field(default_factory=list)


@dataclass
class GenerationResult:
    """Result of document generation."""
    document_id: str
    type: str
    content: str
    quality_score: float
    metadata: Dict[str, Any] = field(default_factory=dict)
    generation_time: float = 0.0
    tokens_used: int = 0
    cost: float = 0.0
    cache_hit: bool = False
    performance_metrics: Dict[str, float] = field(default_factory=dict)


@dataclass
class CacheEntry:
    """Entry in response cache with security enhancements."""
    content: str
    timestamp: datetime
    hit_count: int = 0
    fingerprint: str = ""
    tokens_used: int = 0
    cost: float = 0.0
    signature: str = ""  # HMAC signature for integrity validation
    encrypted: bool = False  # Whether content is encrypted
    user_id: str = "default"  # For cache isolation


@dataclass
class BatchRequest:
    """Request in batch processing."""
    document_type: str
    project_path: str
    context: Dict[str, Any]
    priority: int = 0
    request_id: str = ""


# ============================================================================
# ResponseCache Class - Performance Optimization
# ============================================================================

class ResponseCache:
    """Multi-tier cache for LLM responses with security-hardened similarity matching."""
    
    def __init__(self, config: ConfigurationManager, security_manager: Optional['SecurityManager'] = None):
        """Initialize response cache with security controls."""
        self.config = config
        self.security_manager = security_manager or SecurityManager(config)
        self.memory_mode = getattr(config.system, 'memory_mode', 'standard')
        self.cache_ttl = getattr(config.system, 'cache_ttl', 3600)  # 1 hour default
        
        # Set cache size based on memory mode
        cache_sizes = {
            'baseline': 100,    # 2GB RAM
            'standard': 500,    # 4GB RAM
            'enhanced': 2000,   # 8GB RAM
            'performance': 10000  # 16GB+ RAM
        }
        self.max_cache_size = cache_sizes.get(self.memory_mode, 500)
        
        # Multi-tier cache
        self.l1_cache = OrderedDict()  # Hot cache - exact matches
        self.l2_cache = OrderedDict()  # Warm cache - similar matches
        self.l3_cache = {}  # Cold cache - disk-based for large responses
        
        # Cache statistics
        self.stats = {
            'hits': 0,
            'misses': 0,
            'evictions': 0,
            'similarity_matches': 0
        }
        
        # Lock for thread safety
        self.lock = threading.RLock()
        
        # Create cache directory for L3
        self.cache_dir = Path(getattr(config.system, 'cache_dir', '/tmp/devdocai_cache'))
        self.cache_dir.mkdir(parents=True, exist_ok=True)
    
    def _generate_fingerprint(self, prompt: str, context: Dict[str, Any]) -> str:
        """Generate unique fingerprint for cache key."""
        # Create stable hash from prompt and context
        key_parts = [prompt]
        
        # Add sorted context keys for stability
        for k in sorted(context.keys()):
            key_parts.append(f"{k}:{str(context[k])[:100]}")
        
        key_string = '|'.join(key_parts)
        return hashlib.sha256(key_string.encode()).hexdigest()[:16]
    
    def get(self, prompt: str, context: Dict[str, Any], similarity_threshold: float = 0.85, user_id: str = 'default') -> Optional[CacheEntry]:
        """Get cached response with security validation and similarity matching."""
        with self.lock:
            fingerprint = self._generate_fingerprint(prompt, context)
            
            # Check L1 cache (exact match)
            if fingerprint in self.l1_cache:
                entry = self.l1_cache[fingerprint]
                
                # Verify cache integrity and user isolation
                if self._is_valid_secure(entry, fingerprint, user_id):
                    entry.hit_count += 1
                    self.stats['hits'] += 1
                    # Move to end (LRU)
                    self.l1_cache.move_to_end(fingerprint)
                    return entry
                else:
                    # Remove corrupted or unauthorized entry
                    del self.l1_cache[fingerprint]
                    self.security_manager._log_security_event('CACHE_INTEGRITY_FAILURE', {
                        'fingerprint': fingerprint,
                        'user_id': user_id
                    })
            
            # Check L2 cache (similarity match)
            if self.memory_mode in ['enhanced', 'performance']:
                similar_entry = self._find_similar(prompt, similarity_threshold)
                if similar_entry:
                    self.stats['similarity_matches'] += 1
                    return similar_entry
            
            # Check L3 cache (disk)
            if self.memory_mode == 'performance':
                disk_entry = self._load_from_disk(fingerprint)
                if disk_entry:
                    # Promote to L1
                    self.l1_cache[fingerprint] = disk_entry
                    self.stats['hits'] += 1
                    return disk_entry
            
            self.stats['misses'] += 1
            return None
    
    def put(self, prompt: str, context: Dict[str, Any], response: str, 
            tokens_used: int = 0, cost: float = 0.0, user_id: str = 'default'):
        """Store response in cache with security controls."""
        with self.lock:
            # Sanitize response for injection attacks
            response = self.security_manager.sanitize_input(response)
            
            # Check for PII in response
            pii_detections = self.security_manager.detect_pii(response)
            if pii_detections:
                logger.warning(f"PII detected in cache content: {len(pii_detections)} instances")
            
            fingerprint = self._generate_fingerprint(prompt, context)
            
            # Generate signature for integrity
            signature = self.security_manager.sign_cache_entry(response, fingerprint)
            
            entry = CacheEntry(
                content=response,
                timestamp=datetime.now(),
                fingerprint=fingerprint,
                tokens_used=tokens_used,
                cost=cost,
                signature=signature,
                user_id=user_id
            )
            
            # Add to L1 cache
            self.l1_cache[fingerprint] = entry
            
            # Evict if necessary
            if len(self.l1_cache) > self.max_cache_size:
                self._evict()
    
    def _is_valid(self, entry: CacheEntry) -> bool:
        """Check if cache entry is still valid."""
        age = (datetime.now() - entry.timestamp).total_seconds()
        return age < self.cache_ttl
    
    def _is_valid_secure(self, entry: CacheEntry, fingerprint: str, user_id: str) -> bool:
        """Check if cache entry is valid with security verification."""
        # Check basic validity
        if not self._is_valid(entry):
            return False
        
        # Check user isolation (cache isolation per user)
        if entry.user_id != user_id and entry.user_id != 'default':
            self.security_manager._log_security_event('CACHE_ISOLATION_VIOLATION', {
                'expected_user': user_id,
                'entry_user': entry.user_id
            })
            return False
        
        # Verify signature for integrity
        if entry.signature:
            if not self.security_manager.verify_cache_signature(
                entry.content, fingerprint, entry.signature
            ):
                return False
        
        return True
    
    def _find_similar(self, prompt: str, threshold: float) -> Optional[CacheEntry]:
        """Find similar cached response."""
        # Simple similarity based on prompt overlap
        # In production, use more sophisticated similarity metrics
        prompt_words = set(prompt.lower().split())
        
        for fingerprint, entry in self.l1_cache.items():
            if not self._is_valid(entry):
                continue
            
            # Quick similarity check (simplified)
            # Real implementation would use embeddings
            cached_prompt_estimate = entry.content[:200]
            cached_words = set(cached_prompt_estimate.lower().split())
            
            similarity = len(prompt_words & cached_words) / max(len(prompt_words), 1)
            if similarity >= threshold:
                entry.hit_count += 1
                return entry
        
        return None
    
    def _evict(self):
        """Evict least recently used entries."""
        # Move oldest entries to L3 (disk) if in performance mode
        evict_count = max(1, self.max_cache_size // 10)
        
        for _ in range(evict_count):
            if not self.l1_cache:
                break
            
            fingerprint, entry = self.l1_cache.popitem(last=False)
            self.stats['evictions'] += 1
            
            # Save to disk in performance mode
            if self.memory_mode == 'performance':
                self._save_to_disk(fingerprint, entry)
    
    def _save_to_disk(self, fingerprint: str, entry: CacheEntry):
        """Save cache entry to disk with encryption."""
        try:
            cache_file = self.cache_dir / f"{fingerprint}.cache"
            
            # Serialize entry
            serialized = pickle.dumps(entry)
            
            # Encrypt before saving
            encrypted = self.security_manager.encrypt_cache_content(serialized)
            
            # Save encrypted content
            with open(cache_file, 'wb') as f:
                f.write(encrypted)
            
            # Mark entry as encrypted
            entry.encrypted = True
            
        except Exception as e:
            logger.warning(f"Failed to save cache to disk: {e}")
            self.security_manager._log_security_event('CACHE_SAVE_FAILURE', {
                'fingerprint': fingerprint,
                'error': str(e)
            })
    
    def _load_from_disk(self, fingerprint: str) -> Optional[CacheEntry]:
        """Load cache entry from disk with decryption."""
        try:
            cache_file = self.cache_dir / f"{fingerprint}.cache"
            if cache_file.exists():
                with open(cache_file, 'rb') as f:
                    encrypted = f.read()
                
                # Decrypt content
                try:
                    decrypted = self.security_manager.decrypt_cache_content(encrypted)
                    entry = pickle.loads(decrypted)
                except Exception as decrypt_error:
                    # Try loading unencrypted for backward compatibility
                    with open(cache_file, 'rb') as f:
                        entry = pickle.load(f)
                
                # Validate entry
                if self._is_valid(entry):
                    # Verify integrity if signature present
                    if entry.signature:
                        if not self.security_manager.verify_cache_signature(
                            entry.content, entry.fingerprint, entry.signature
                        ):
                            self.security_manager._log_security_event('CACHE_LOAD_INTEGRITY_FAILURE', {
                                'fingerprint': fingerprint
                            })
                            return None
                    return entry
                    
        except Exception as e:
            logger.warning(f"Failed to load cache from disk: {e}")
            self.security_manager._log_security_event('CACHE_LOAD_FAILURE', {
                'fingerprint': fingerprint,
                'error': str(e)
            })
        return None
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        with self.lock:
            total = self.stats['hits'] + self.stats['misses']
            hit_rate = self.stats['hits'] / max(total, 1)
            
            return {
                'hits': self.stats['hits'],
                'misses': self.stats['misses'],
                'hit_rate': hit_rate,
                'evictions': self.stats['evictions'],
                'similarity_matches': self.stats['similarity_matches'],
                'cache_size': len(self.l1_cache),
                'max_size': self.max_cache_size
            }


# ============================================================================
# ContextCache Class - Performance Optimization
# ============================================================================

class ContextCache:
    """Cache for extracted project contexts."""
    
    def __init__(self, config: ConfigurationManager):
        """Initialize context cache."""
        self.config = config
        self.cache = OrderedDict()
        self.max_size = 100
        self.lock = threading.RLock()
    
    def get(self, project_path: str) -> Optional[Dict[str, Any]]:
        """Get cached context."""
        with self.lock:
            # Check if path exists and hasn't changed
            path = Path(project_path)
            if not path.exists():
                return None
            
            cache_key = str(path.absolute())
            if cache_key in self.cache:
                entry, timestamp = self.cache[cache_key]
                
                # Check if context is still fresh (5 minutes)
                if (datetime.now() - timestamp).total_seconds() < 300:
                    # Move to end (LRU)
                    self.cache.move_to_end(cache_key)
                    return entry
            
            return None
    
    def put(self, project_path: str, context: Dict[str, Any]):
        """Store context in cache."""
        with self.lock:
            path = Path(project_path)
            cache_key = str(path.absolute())
            
            self.cache[cache_key] = (context, datetime.now())
            
            # Evict if necessary
            if len(self.cache) > self.max_size:
                self.cache.popitem(last=False)


# ============================================================================
# BatchProcessor Class - Performance Optimization
# ============================================================================

class BatchProcessor:
    """Process multiple documents in parallel batches with security controls."""
    
    def __init__(self, config: ConfigurationManager, generator, security_manager: Optional[SecurityManager] = None):
        """Initialize batch processor with security controls."""
        self.config = config
        self.generator = generator
        self.security_manager = security_manager or SecurityManager(config)
        self.memory_mode = getattr(config.system, 'memory_mode', 'standard')
        
        # Concurrency based on memory mode
        concurrency_map = {
            'baseline': 10,
            'standard': 50,
            'enhanced': 200,
            'performance': 1000
        }
        self.max_concurrent = concurrency_map.get(self.memory_mode, 50)
        
        # Processing queue
        self.queue = Queue(maxsize=self.max_concurrent * 2)
        self.results = {}
        self.processing = set()
        self.lock = threading.RLock()
    
    async def process_batch(self, requests: List[BatchRequest], user_id: str = 'default') -> Dict[str, GenerationResult]:
        """Process batch of document generation requests with security validation."""
        start_time = time.time()
        
        # Validate batch size
        if not self.security_manager.validate_batch_size(len(requests)):
            raise DocumentGenerationError(f"Batch size {len(requests)} exceeds maximum allowed")
        
        # Check rate limiting
        if not self.security_manager.check_rate_limit(user_id):
            raise DocumentGenerationError("Rate limit exceeded. Please try again later.")
        
        # Validate resource usage
        quota = self.security_manager.get_resource_quota(self.memory_mode)
        if len(requests) > quota['concurrent']:
            self.security_manager._log_security_event('BATCH_CONCURRENT_EXCEEDED', {
                'requested': len(requests),
                'max_allowed': quota['concurrent']
            })
            # Process in smaller chunks
            requests = requests[:quota['concurrent']]
        
        # Sanitize all request contexts
        for request in requests:
            for key, value in request.context.items():
                if isinstance(value, str):
                    request.context[key] = self.security_manager.sanitize_input(value)
        
        # Group similar requests for better cache utilization
        grouped = self._group_similar_requests(requests)
        
        # Process groups in parallel
        tasks = []
        for group in grouped:
            task = self._process_group(group)
            tasks.append(task)
        
        # Wait for all groups to complete
        group_results = await asyncio.gather(*tasks)
        
        # Flatten results
        results = {}
        for group_result in group_results:
            results.update(group_result)
        
        # Add performance metrics
        elapsed = time.time() - start_time
        docs_per_second = len(requests) / max(elapsed, 0.001)
        
        logger.info(f"Batch processed {len(requests)} documents in {elapsed:.2f}s ({docs_per_second:.1f} docs/s)")
        
        return results
    
    def _group_similar_requests(self, requests: List[BatchRequest]) -> List[List[BatchRequest]]:
        """Group similar requests for better cache utilization."""
        groups = defaultdict(list)
        
        for request in requests:
            # Group by document type and similar context
            group_key = f"{request.document_type}"
            
            # Add context similarity (simplified)
            if 'project_name' in request.context:
                group_key += f"_{request.context['project_name'][:10]}"
            
            groups[group_key].append(request)
        
        # Convert to list of groups
        return list(groups.values())
    
    async def _process_group(self, group: List[BatchRequest]) -> Dict[str, GenerationResult]:
        """Process a group of similar requests."""
        results = {}
        
        # Process in parallel with semaphore to limit concurrency
        semaphore = asyncio.Semaphore(min(len(group), self.max_concurrent))
        
        async def process_single(request: BatchRequest):
            async with semaphore:
                try:
                    result = await self.generator.generate(
                        document_type=request.document_type,
                        project_path=request.project_path,
                        custom_context=request.context,
                        parallel_sections=True
                    )
                    
                    # Convert to GenerationResult
                    gen_result = GenerationResult(
                        document_id=result['document_id'],
                        type=result['type'],
                        content=result['content'],
                        quality_score=result['quality_score'],
                        metadata=result['metadata'],
                        generation_time=result['generation_time']
                    )
                    
                    results[request.request_id] = gen_result
                    
                except Exception as e:
                    logger.error(f"Failed to process request {request.request_id}: {e}")
                    results[request.request_id] = None
        
        # Process all requests in group
        tasks = [process_single(req) for req in group]
        await asyncio.gather(*tasks)
        
        return results


# ============================================================================
# PerformanceMonitor Class - Performance Optimization
# ============================================================================

class PerformanceMonitor:
    """Monitor and report performance metrics with security controls."""
    
    def __init__(self, security_manager: Optional[SecurityManager] = None):
        """Initialize performance monitor with security controls."""
        self.metrics = defaultdict(list)
        self.start_times = {}
        self.lock = threading.RLock()
        self.security_manager = security_manager
        self.max_metrics_per_operation = 10000  # Prevent memory exhaustion
    
    def start_operation(self, operation: str) -> str:
        """Start timing an operation."""
        op_id = f"{operation}_{time.time()}"
        with self.lock:
            self.start_times[op_id] = time.time()
        return op_id
    
    def end_operation(self, op_id: str, metadata: Optional[Dict] = None):
        """End timing an operation with security controls."""
        with self.lock:
            if op_id in self.start_times:
                elapsed = time.time() - self.start_times[op_id]
                operation = op_id.split('_')[0]
                
                # Sanitize metadata to prevent injection
                if metadata and self.security_manager:
                    for key, value in metadata.items():
                        if isinstance(value, str):
                            metadata[key] = self.security_manager.sanitize_input(value)
                
                # Add metric with size limits
                if len(self.metrics[operation]) < self.max_metrics_per_operation:
                    # Add timing jitter to prevent timing attacks
                    jitter = secrets.randbelow(100) / 10000  # 0-0.01s random jitter
                    self.metrics[operation].append({
                        'duration': elapsed + jitter,
                        'timestamp': time.time(),
                        'metadata': metadata or {}
                    })
                else:
                    # Rotate old metrics
                    self.metrics[operation] = self.metrics[operation][-5000:]
                    if self.security_manager:
                        self.security_manager._log_security_event('METRICS_ROTATION', {
                            'operation': operation,
                            'count': len(self.metrics[operation])
                        })
                
                del self.start_times[op_id]
    
    def get_stats(self, operation: Optional[str] = None) -> Dict[str, Any]:
        """Get performance statistics."""
        with self.lock:
            if operation:
                if operation not in self.metrics:
                    return {}
                
                durations = [m['duration'] for m in self.metrics[operation]]
                return self._calculate_stats(operation, durations)
            else:
                # Return stats for all operations
                all_stats = {}
                for op, metrics in self.metrics.items():
                    durations = [m['duration'] for m in metrics]
                    all_stats[op] = self._calculate_stats(op, durations)
                return all_stats
    
    def _calculate_stats(self, operation: str, durations: List[float]) -> Dict[str, Any]:
        """Calculate statistics for durations."""
        if not durations:
            return {}
        
        return {
            'operation': operation,
            'count': len(durations),
            'total': sum(durations),
            'mean': sum(durations) / len(durations),
            'min': min(durations),
            'max': max(durations),
            'throughput': len(durations) / sum(durations) if sum(durations) > 0 else 0
        }


# ============================================================================
# TemplateManager Class
# ============================================================================

class TemplateManager:
    """Manages document templates for AI-guided generation."""
    
    def __init__(self, config: ConfigurationManager):
        """Initialize template manager."""
        self.config = config
        self.template_dir = Path(getattr(config.system, 'templates_dir', '/tmp/templates'))
        self._cache: Dict[str, Dict[str, Any]] = {}
        
        # Create template directory if it doesn't exist
        self.template_dir.mkdir(parents=True, exist_ok=True)
        
        # Load built-in templates if directory is empty
        if not list(self.template_dir.glob('*.yaml')) and not list(self.template_dir.glob('*.yml')):
            self._create_default_templates()
    
    def _create_default_templates(self):
        """Create default document templates."""
        default_templates = {
            'readme': {
                'document_type': 'readme',
                'name': 'README Documentation',
                'sections': [
                    {
                        'name': 'header',
                        'prompt_template': 'Generate a professional README header for {project_name}. Include appropriate badges for build status, test coverage, and license.',
                        'required': True
                    },
                    {
                        'name': 'description',
                        'prompt_template': 'Write a clear and compelling description for {project_name}. The project is: {project_description}. Highlight key features and benefits.',
                        'required': True
                    },
                    {
                        'name': 'installation',
                        'prompt_template': 'Create detailed installation instructions for {project_name}, a Python {python_version} project. Include pip installation, development setup, and any system requirements.',
                        'required': True
                    },
                    {
                        'name': 'usage',
                        'prompt_template': 'Write comprehensive usage examples for {project_name}. Include basic usage, advanced features, and common use cases with code examples.',
                        'required': True
                    },
                    {
                        'name': 'api',
                        'prompt_template': 'Generate API documentation for the main classes and functions in {project_name}. Focus on: {main_modules}',
                        'required': False
                    },
                    {
                        'name': 'contributing',
                        'prompt_template': 'Create contributing guidelines for {project_name}. Include development setup, coding standards, and pull request process.',
                        'required': False
                    }
                ],
                'context_requirements': [
                    'project_name',
                    'project_description',
                    'python_version'
                ],
                'quality_criteria': {
                    'min_length': 500,
                    'max_length': 10000,
                    'required_sections': ['header', 'description', 'installation', 'usage']
                }
            },
            'api_doc': {
                'document_type': 'api_doc',
                'name': 'API Documentation',
                'sections': [
                    {
                        'name': 'overview',
                        'prompt_template': 'Create an API overview for {project_name}. Describe the main modules, classes, and their purposes.',
                        'required': True
                    },
                    {
                        'name': 'classes',
                        'prompt_template': 'Document all classes in {project_name}. For each class, include description, methods, attributes, and usage examples. Classes found: {classes}',
                        'required': True
                    },
                    {
                        'name': 'functions',
                        'prompt_template': 'Document all functions in {project_name}. Include parameters, return values, exceptions, and examples. Functions found: {functions}',
                        'required': True
                    }
                ],
                'context_requirements': [
                    'project_name',
                    'classes',
                    'functions'
                ],
                'quality_criteria': {
                    'min_length': 1000,
                    'required_sections': ['overview', 'classes', 'functions']
                }
            },
            'changelog': {
                'document_type': 'changelog',
                'name': 'Changelog',
                'sections': [
                    {
                        'name': 'header',
                        'prompt_template': 'Create a changelog header for {project_name} following Keep a Changelog format.',
                        'required': True
                    },
                    {
                        'name': 'version',
                        'prompt_template': 'Document version {version} changes. Include Added, Changed, Fixed, and Removed sections based on: {recent_changes}',
                        'required': True
                    }
                ],
                'context_requirements': [
                    'project_name',
                    'version'
                ],
                'quality_criteria': {
                    'min_length': 200,
                    'required_sections': ['header', 'version']
                }
            }
        }
        
        # Save default templates
        for template_name, template_data in default_templates.items():
            template_file = self.template_dir / f"{template_name}.yaml"
            with open(template_file, 'w') as f:
                yaml.dump(template_data, f, default_flow_style=False)
        
        logger.info(f"Created {len(default_templates)} default templates in {self.template_dir}")
    
    def load_template(self, template_name: str) -> Dict[str, Any]:
        """Load a template by name."""
        # Check cache first
        if template_name in self._cache:
            return self._cache[template_name]
        
        # Try loading from file
        template_file = None
        for ext in ['.yaml', '.yml']:
            candidate = self.template_dir / f"{template_name}{ext}"
            if candidate.exists():
                template_file = candidate
                break
        
        if not template_file:
            available = self.list_templates()
            raise TemplateNotFoundError(
                f"Template not found: {template_name}. "
                f"Available templates: {', '.join(available)}"
            )
        
        # Load and validate template
        with open(template_file, 'r') as f:
            template = yaml.safe_load(f)
        
        self.validate_template(template)
        
        # Cache for future use
        self._cache[template_name] = template
        
        return template
    
    def validate_template(self, template: Dict[str, Any]) -> bool:
        """Validate template structure."""
        required_fields = ['document_type', 'sections']
        
        for field in required_fields:
            if field not in template:
                raise ValueError(f"Missing required field: {field}")
        
        if not isinstance(template['sections'], list):
            raise ValueError("'sections' must be a list")
        
        for section in template['sections']:
            if 'name' not in section:
                raise ValueError("Each section must have a 'name' field")
            if 'prompt_template' not in section:
                raise ValueError(f"Section '{section['name']}' missing 'prompt_template'")
        
        return True
    
    def list_templates(self) -> List[str]:
        """List available templates."""
        templates = []
        
        for file in self.template_dir.glob('*.yaml'):
            templates.append(file.stem)
        for file in self.template_dir.glob('*.yml'):
            templates.append(file.stem)
        
        return sorted(set(templates))


# ============================================================================
# ContextBuilder Class
# ============================================================================

class ContextBuilder:
    """Extracts context from project for document generation with security controls."""
    
    def __init__(self, config: ConfigurationManager, security_manager: Optional[SecurityManager] = None):
        """Initialize context builder with security controls."""
        self.config = config
        self.security_manager = security_manager or SecurityManager(config)
        self._extractors = {
            'python': self._extract_python_context,
            'package': self._extract_package_context,
            'git': self._extract_git_context,
            'files': self._extract_file_context
        }
        self.max_files_to_scan = 1000  # Prevent resource exhaustion
    
    def extract_from_project(self, project_path: str) -> Dict[str, Any]:
        """Extract comprehensive context from project with security validation."""
        # Validate path security
        if not self.security_manager.validate_path(project_path):
            raise ContextExtractionError(f"Invalid or unsafe project path: {project_path}")
        
        project_dir = Path(project_path)
        
        if not project_dir.exists():
            raise ContextExtractionError(f"Project path does not exist: {project_path}")
        
        context = {
            'project_path': str(project_dir.absolute()),
            'project_name': self.security_manager.sanitize_input(project_dir.name),
            'extracted_at': datetime.now().isoformat()
        }
        
        # Run all extractors with security controls
        for name, extractor in self._extractors.items():
            try:
                extractor_context = extractor(project_dir)
                # Sanitize extracted context
                for key, value in extractor_context.items():
                    if isinstance(value, str):
                        extractor_context[key] = self.security_manager.sanitize_input(value)
                context.update(extractor_context)
            except Exception as e:
                logger.warning(f"Extractor '{name}' failed: {e}")
        
        return context
    
    def _extract_python_context(self, project_dir: Path) -> Dict[str, Any]:
        """Extract Python-specific context with security controls."""
        context = {
            'modules': [],
            'classes': [],
            'functions': [],
            'main_modules': []
        }
        
        # Find Python files with security limits
        py_files = []
        file_count = 0
        for py_file in project_dir.rglob('*.py'):
            # Validate each file path
            if self.security_manager.validate_path(py_file):
                py_files.append(py_file)
                file_count += 1
                if file_count >= min(20, self.max_files_to_scan):
                    break
        
        for py_file in py_files:
            try:
                # Size limit check (prevent large file DOS)
                if py_file.stat().st_size > 1024 * 1024:  # 1MB limit
                    logger.warning(f"Skipping large file: {py_file}")
                    continue
                
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Safe AST parsing with validation
                try:
                    tree = ast.parse(content)
                    
                    # Validate AST nodes for security
                    if not self.security_manager.validate_ast_node(tree):
                        logger.warning(f"Unsafe AST detected in {py_file}, skipping")
                        continue
                except SyntaxError:
                    # Skip files with syntax errors
                    continue
                
                module_name = self.security_manager.sanitize_input(py_file.stem)
                context['modules'].append(module_name)
                
                for node in ast.walk(tree):
                    if isinstance(node, ast.ClassDef):
                        context['classes'].append(self.security_manager.sanitize_input(node.name))
                    elif isinstance(node, ast.FunctionDef):
                        if not node.name.startswith('_'):
                            context['functions'].append(self.security_manager.sanitize_input(node.name))
                
                # Check if it's a main module
                if py_file.name in ['__init__.py', 'main.py', f'{project_dir.name}.py']:
                    context['main_modules'].append(module_name)
                    
            except Exception as e:
                logger.debug(f"Failed to parse {py_file}: {e}")
        
        # Remove duplicates
        context['classes'] = list(set(context['classes']))[:20]
        context['functions'] = list(set(context['functions']))[:30]
        
        return context
    
    def _extract_package_context(self, project_dir: Path) -> Dict[str, Any]:
        """Extract package/project metadata."""
        context = {}
        
        # Check for pyproject.toml
        pyproject_file = project_dir / 'pyproject.toml'
        if pyproject_file.exists():
            try:
                import tomli
                with open(pyproject_file, 'rb') as f:
                    pyproject = tomli.load(f)
                
                project = pyproject.get('project', {})
                context['project_name'] = project.get('name', project_dir.name)
                context['project_description'] = project.get('description', '')
                context['version'] = project.get('version', '0.1.0')
                context['python_version'] = project.get('requires-python', '>=3.8')
                context['dependencies'] = project.get('dependencies', [])
                
            except Exception as e:
                logger.debug(f"Failed to parse pyproject.toml: {e}")
        
        # Check for setup.py
        setup_file = project_dir / 'setup.py'
        if setup_file.exists() and 'project_name' not in context:
            try:
                with open(setup_file, 'r') as f:
                    content = f.read()
                
                # Basic regex extraction (not executing setup.py)
                name_match = re.search(r"name\s*=\s*['\"]([^'\"]+)['\"]", content)
                if name_match:
                    context['project_name'] = name_match.group(1)
                
                desc_match = re.search(r"description\s*=\s*['\"]([^'\"]+)['\"]", content)
                if desc_match:
                    context['project_description'] = desc_match.group(1)
                    
            except Exception as e:
                logger.debug(f"Failed to parse setup.py: {e}")
        
        # Check for requirements.txt
        requirements_file = project_dir / 'requirements.txt'
        if requirements_file.exists() and 'dependencies' not in context:
            try:
                with open(requirements_file, 'r') as f:
                    deps = [line.strip() for line in f if line.strip() and not line.startswith('#')]
                    context['dependencies'] = deps[:20]  # Limit number
            except Exception as e:
                logger.debug(f"Failed to parse requirements.txt: {e}")
        
        # Check for README
        for readme_name in ['README.md', 'README.rst', 'README.txt', 'README']:
            readme_file = project_dir / readme_name
            if readme_file.exists():
                try:
                    with open(readme_file, 'r', encoding='utf-8') as f:
                        content = f.read(1000)  # First 1000 chars
                        context['readme_content'] = content
                        
                        # Extract description if not found
                        if 'project_description' not in context:
                            lines = content.split('\n')
                            for line in lines[1:5]:  # Check first few lines after title
                                if line.strip() and not line.startswith('#'):
                                    context['project_description'] = line.strip()
                                    break
                except Exception as e:
                    logger.debug(f"Failed to read README: {e}")
                break
        
        return context
    
    def _extract_git_context(self, project_dir: Path) -> Dict[str, Any]:
        """Extract git repository context."""
        context = {}
        
        git_dir = project_dir / '.git'
        if not git_dir.exists():
            return context
        
        try:
            # Get recent commits (simplified, no git command execution)
            context['has_git'] = True
            
            # Check for .gitignore
            gitignore = project_dir / '.gitignore'
            if gitignore.exists():
                context['has_gitignore'] = True
        except Exception as e:
            logger.debug(f"Failed to extract git context: {e}")
        
        return context
    
    def _extract_file_context(self, project_dir: Path) -> Dict[str, Any]:
        """Extract general file structure context."""
        context = {
            'file_count': 0,
            'total_size': 0,
            'file_types': {}
        }
        
        try:
            for file in project_dir.rglob('*'):
                if file.is_file():
                    context['file_count'] += 1
                    context['total_size'] += file.stat().st_size
                    
                    ext = file.suffix.lower()
                    if ext:
                        context['file_types'][ext] = context['file_types'].get(ext, 0) + 1
            
            # Sort file types by count
            context['file_types'] = dict(
                sorted(context['file_types'].items(), key=lambda x: x[1], reverse=True)[:10]
            )
            
        except Exception as e:
            logger.debug(f"Failed to extract file context: {e}")
        
        return context
    
    def merge_contexts(self, *contexts: Dict[str, Any]) -> Dict[str, Any]:
        """Merge multiple contexts, later ones override earlier ones."""
        merged = {}
        
        for context in contexts:
            merged.update(context)
        
        return merged


# ============================================================================
# PromptEngine Class
# ============================================================================

class PromptEngine:
    """Constructs prompts for LLM from templates and context."""
    
    def __init__(self, config: ConfigurationManager):
        """Initialize prompt engine."""
        self.config = config
        self.max_prompt_length = config.get('ai.max_prompt_length', 8000)
        self.model = config.get('ai.model', 'gpt-4')
    
    def construct_prompt(self, template: str, context: Dict[str, Any]) -> str:
        """Construct a prompt from template and context."""
        # Format template with context
        prompt = self.format_template(template, context)
        
        # Optimize length if needed
        if len(prompt) > self.max_prompt_length:
            prompt = self.optimize_prompt(prompt)
        
        return prompt
    
    def construct_system_prompt(self, document_type: str) -> str:
        """Construct system prompt for specific document type."""
        system_prompts = {
            'readme': (
                "You are a technical documentation expert specializing in creating "
                "comprehensive, clear, and professional README files. Focus on clarity, "
                "completeness, and following best practices. Use Markdown formatting."
            ),
            'api_doc': (
                "You are an API documentation specialist. Create detailed, accurate, "
                "and developer-friendly API documentation. Include clear descriptions, "
                "parameter details, return values, and practical examples."
            ),
            'changelog': (
                "You are a changelog writer following the Keep a Changelog format. "
                "Organize changes into Added, Changed, Deprecated, Removed, Fixed, "
                "and Security categories. Be concise but informative."
            ),
            'default': (
                "You are a professional technical writer creating high-quality "
                "documentation. Focus on clarity, accuracy, and completeness."
            )
        }
        
        return system_prompts.get(document_type, system_prompts['default'])
    
    def format_template(self, template: str, context: Dict[str, Any], use_defaults: bool = True) -> str:
        """Format template with context values."""
        # Create a copy to avoid modifying original
        formatted = template
        
        # Find all placeholders
        placeholders = re.findall(r'\{(\w+)\}', template)
        
        for placeholder in placeholders:
            if placeholder in context:
                value = context[placeholder]
                
                # Handle different value types
                if isinstance(value, list):
                    value = ', '.join(str(v) for v in value[:10])  # Limit list size
                elif isinstance(value, dict):
                    value = json.dumps(value, indent=2)[:500]  # Limit dict size
                else:
                    value = str(value)
                
                formatted = formatted.replace(f'{{{placeholder}}}', value)
                
            elif use_defaults:
                # Use sensible defaults for missing values
                defaults = {
                    'project_name': 'MyProject',
                    'project_description': 'A Python project',
                    'version': '0.1.0',
                    'author': 'Developer',
                    'python_version': '3.8+',
                    'license': 'MIT'
                }
                
                if placeholder in defaults:
                    formatted = formatted.replace(f'{{{placeholder}}}', defaults[placeholder])
                else:
                    # Remove unfilled placeholders
                    formatted = formatted.replace(f'{{{placeholder}}}', f'[{placeholder}]')
        
        return formatted
    
    def optimize_prompt(self, prompt: str) -> str:
        """Optimize prompt length while preserving information."""
        if len(prompt) <= self.max_prompt_length:
            return prompt
        
        # Truncate with ellipsis
        truncated = prompt[:self.max_prompt_length - 100]
        
        # Try to end at a sentence boundary
        last_period = truncated.rfind('.')
        if last_period > self.max_prompt_length - 500:
            truncated = truncated[:last_period + 1]
        
        truncated += "\n\n[Content truncated for length...]"
        
        return truncated
    
    def add_examples(self, base_prompt: str, examples: List[str]) -> str:
        """Add examples to prompt for better generation."""
        if not examples:
            return base_prompt
        
        prompt_with_examples = base_prompt + "\n\nExamples:\n"
        
        for i, example in enumerate(examples[:3], 1):  # Limit to 3 examples
            prompt_with_examples += f"\nExample {i}:\n{example}\n"
        
        return prompt_with_examples
    
    def create_section_prompt(self, section: Dict[str, Any], context: Dict[str, Any], 
                            previous_sections: Optional[str] = None) -> str:
        """Create prompt for a specific section."""
        prompt_template = section.get('prompt_template', '')
        
        # Add context about previous sections if available
        if previous_sections:
            prompt = f"Previous sections of the document:\n\n{previous_sections}\n\n"
            prompt += "Now generate the next section:\n\n"
        else:
            prompt = ""
        
        # Add the section-specific prompt
        prompt += self.construct_prompt(prompt_template, context)
        
        # Add any section-specific examples
        if 'examples' in section:
            prompt = self.add_examples(prompt, section['examples'])
        
        return prompt


# ============================================================================
# DocumentValidator Class
# ============================================================================

class DocumentValidator:
    """Validates generated documents against quality criteria."""
    
    def __init__(self, config: ConfigurationManager):
        """Initialize document validator."""
        self.config = config
        self.min_quality_score = config.get('quality.min_score', 85)
        self.grammar_check_enabled = config.get('quality.check_grammar', True)
        self.check_completeness = config.get('quality.check_completeness', True)
    
    def validate(self, document: str, template: Dict[str, Any]) -> ValidationResult:
        """Validate document against template criteria."""
        errors = []
        warnings = []
        suggestions = []
        
        # Get quality criteria from template
        criteria = template.get('quality_criteria', {})
        
        # Check length requirements
        doc_length = len(document)
        min_length = criteria.get('min_length', 100)
        max_length = criteria.get('max_length', 100000)
        
        if doc_length < min_length:
            errors.append(f"Document too short: {doc_length} chars (minimum: {min_length})")
        elif doc_length > max_length:
            warnings.append(f"Document too long: {doc_length} chars (maximum: {max_length})")
        
        # Check required sections
        required_sections = criteria.get('required_sections', [])
        for section_name in required_sections:
            # Simple check - look for section headers
            if section_name.lower() not in document.lower():
                errors.append(f"Missing required section: {section_name}")
        
        # Calculate quality score
        score = self.calculate_score(document)
        
        # Check grammar if enabled
        if self.grammar_check_enabled:
            grammar_ok = self.check_grammar_simple(document)
            if not grammar_ok:
                warnings.append("Grammar issues detected")
                score *= 0.9  # Reduce score for grammar issues
        
        # Determine validity
        is_valid = len(errors) == 0 and score >= self.min_quality_score
        
        # Add suggestions
        if score < 90:
            suggestions.append("Consider adding more detailed content")
        if len(warnings) > 0:
            suggestions.append("Review and address warnings for better quality")
        
        return ValidationResult(
            is_valid=is_valid,
            score=score,
            errors=errors,
            warnings=warnings,
            suggestions=suggestions
        )
    
    def calculate_score(self, document: str) -> float:
        """Calculate quality score for document."""
        score = 100.0
        
        # Length score
        doc_length = len(document)
        if doc_length < 200:
            score -= 20
        elif doc_length < 500:
            score -= 10
        
        # Structure score - check for headers
        header_count = document.count('#')
        if header_count < 2:
            score -= 15
        elif header_count < 4:
            score -= 5
        
        # Content quality indicators
        # Check for code blocks
        if '```' in document:
            score += 5  # Bonus for including code examples
        
        # Check for lists
        if '- ' in document or '* ' in document or '1. ' in document:
            score += 3  # Bonus for structured content
        
        # Check for links
        if '[' in document and '](' in document:
            score += 2  # Bonus for references
        
        # Ensure score stays in valid range
        score = max(0, min(100, score))
        
        return score
    
    def check_grammar(self, text: str) -> bool:
        """Perform grammar check (placeholder for advanced implementation)."""
        return self.check_grammar_simple(text)
    
    def check_grammar_simple(self, text: str) -> bool:
        """Simple grammar check based on basic rules."""
        # Very basic checks - in production, use language tool
        issues = 0
        
        # Check for double spaces
        if '  ' in text:
            issues += 1
        
        # Check for missing capitalization after periods
        sentences = text.split('. ')
        for sentence in sentences[:-1]:
            next_idx = sentences.index(sentence) + 1
            if next_idx < len(sentences) and sentences[next_idx]:
                if sentences[next_idx][0].islower():
                    issues += 1
        
        # Return True if minimal issues
        return issues < 3
    
    def validate_sections(self, document: str, required_sections: List[str]) -> List[str]:
        """Validate that all required sections are present."""
        missing_sections = []
        
        for section in required_sections:
            # Look for section as a header (case-insensitive)
            section_pattern = rf'#+\s*{re.escape(section)}'
            if not re.search(section_pattern, document, re.IGNORECASE):
                missing_sections.append(section)
        
        return missing_sections


# ============================================================================
# Main DocumentGenerator Class
# ============================================================================

class DocumentGenerator:
    """Main orchestrator for AI-powered document generation with performance optimization."""
    
    def __init__(self, 
                 config: Optional[ConfigurationManager] = None,
                 llm_adapter: Optional[LLMAdapter] = None,
                 storage: Optional[StorageManager] = None):
        """Initialize document generator with security-hardened performance enhancements."""
        self.config = config or ConfigurationManager()
        self.llm_adapter = llm_adapter or LLMAdapter(self.config)
        self.storage = storage or StorageManager(self.config)
        
        # Initialize security manager
        self.security_manager = SecurityManager(self.config)
        
        # Initialize components with security integration
        self.template_manager = TemplateManager(self.config)
        self.context_builder = ContextBuilder(self.config, self.security_manager)
        self.prompt_engine = PromptEngine(self.config)
        self.validator = DocumentValidator(self.config)
        
        # Performance optimization components with security
        self.response_cache = ResponseCache(self.config, self.security_manager)
        self.context_cache = ContextCache(self.config)
        self.performance_monitor = PerformanceMonitor(self.security_manager)
        self.batch_processor = BatchProcessor(self.config, self, self.security_manager)
        
        # Memory mode configuration
        self.memory_mode = getattr(self.config.system, 'memory_mode', 'standard')
        
        # Thread/Process pools based on memory mode
        worker_counts = {
            'baseline': 4,
            'standard': 8,
            'enhanced': 16,
            'performance': 32
        }
        self.max_workers = worker_counts.get(self.memory_mode, 8)
        self.executor = ThreadPoolExecutor(max_workers=self.max_workers)
        
        # Process pool for CPU-intensive operations (context extraction)
        if self.memory_mode in ['enhanced', 'performance']:
            self.process_pool = ProcessPoolExecutor(max_workers=self.max_workers // 2)
        else:
            self.process_pool = None
        
        # Statistics
        self.stats = {
            'documents_generated': 0,
            'cache_hits': 0,
            'total_time': 0.0,
            'total_tokens': 0,
            'total_cost': 0.0
        }
        
        logger.info(f"DocumentGenerator initialized with {self.memory_mode} memory mode, {self.max_workers} workers")
    
    async def generate(self,
                      document_type: str,
                      project_path: str,
                      custom_context: Optional[Dict[str, Any]] = None,
                      parallel_sections: bool = False,
                      retry_on_failure: bool = False,
                      max_retries: int = 3,
                      use_cache: bool = True,
                      batch_id: Optional[str] = None,
                      user_id: str = 'default') -> Dict[str, Any]:
        """Generate a document using AI with security-hardened performance optimizations."""
        start_time = datetime.now()
        perf_id = self.performance_monitor.start_operation('document_generation')
        
        try:
            # Security: Rate limiting
            if not self.security_manager.check_rate_limit(user_id):
                raise DocumentGenerationError("Rate limit exceeded. Please try again later.")
            
            # Security: Path validation
            if not self.security_manager.validate_path(project_path):
                raise DocumentGenerationError(f"Invalid or unsafe project path: {project_path}")
            
            # Security: Sanitize custom context
            if custom_context:
                for key, value in custom_context.items():
                    if isinstance(value, str):
                        custom_context[key] = self.security_manager.sanitize_input(value)
            
            # Security: Resource quota check
            import psutil
            process = psutil.Process()
            memory_mb = process.memory_info().rss / 1024 / 1024
            cpu_percent = process.cpu_percent()
            
            if not self.security_manager.validate_resource_usage(
                memory_mb, cpu_percent, 1, self.memory_mode
            ):
                raise DocumentGenerationError("Resource quota exceeded")
            
            # Load template
            template = self.template_manager.load_template(document_type)
            
            # Extract context from project (with caching)
            project_context = None
            if use_cache:
                project_context = self.context_cache.get(project_path)
            
            if project_context is None:
                context_perf_id = self.performance_monitor.start_operation('context_extraction')
                project_context = await self._extract_context_optimized(project_path)
                self.performance_monitor.end_operation(context_perf_id)
                
                # Cache the context
                if use_cache:
                    self.context_cache.put(project_path, project_context)
            
            # Merge with custom context if provided
            if custom_context:
                context = self.context_builder.merge_contexts(project_context, custom_context)
            else:
                context = project_context
            
            # Check cache for similar documents
            cache_hit = False
            cached_response = None
            
            if use_cache:
                cached_response = self.response_cache.get(
                    self.prompt_engine.construct_system_prompt(document_type),
                    context
                )
            
            if cached_response:
                content = cached_response.content
                cache_hit = True
                self.stats['cache_hits'] += 1
                logger.info(f"Cache hit for {document_type} document")
            else:
                # Generate document content
                gen_perf_id = self.performance_monitor.start_operation('content_generation')
                
                if self.memory_mode == 'performance' and len(template['sections']) > 2:
                    # Use optimized parallel generation for performance mode
                    content = await self._generate_parallel_optimized(template, context)
                elif parallel_sections and len(template['sections']) > 1:
                    content = await self._generate_parallel_sections(template, context)
                else:
                    content = await self._generate_sequential_sections(template, context)
                
                self.performance_monitor.end_operation(gen_perf_id)
                
                # Cache the generated content
                if use_cache and not cache_hit:
                    self.response_cache.put(
                        self.prompt_engine.construct_system_prompt(document_type),
                        context,
                        content
                    )
            
            # Validate generated document
            validation_result = self.validator.validate(content, template)
            
            # Retry if validation fails and retry is enabled
            retry_count = 0
            while not validation_result.is_valid and retry_on_failure and retry_count < max_retries:
                logger.info(f"Validation failed, retrying... (attempt {retry_count + 1}/{max_retries})")
                
                # Regenerate with adjusted parameters
                self.prompt_engine.model = 'gpt-4'  # Try with better model
                content = await self._generate_sequential_sections(template, context)
                validation_result = self.validator.validate(content, template)
                retry_count += 1
            
            # Check final validation
            if not validation_result.is_valid and not retry_on_failure:
                raise QualityValidationError(
                    f"Document failed quality standards. Score: {validation_result.score}, "
                    f"Errors: {', '.join(validation_result.errors)}"
                )
            
            # Generate document ID
            document_id = f"doc_{hashlib.md5(content.encode()).hexdigest()[:8]}"
            
            # Store document
            metadata = DocumentMetadata(
                author="AI Generator",
                tags=[document_type, "ai-generated"],
                version="1.0",
                custom={
                    'quality_score': validation_result.score,
                    'generation_time': (datetime.now() - start_time).total_seconds(),
                    'template': document_type,
                    'project': context.get('project_name', 'unknown')
                }
            )
            
            document = Document(
                id=document_id,  # Provide ID upfront
                type=document_type,
                content=content,
                metadata=metadata,
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
            
            # Save document
            self.storage.save_document(document)
            
            # End performance monitoring
            self.performance_monitor.end_operation(perf_id)
            
            # Update statistics
            generation_time = (datetime.now() - start_time).total_seconds()
            self.stats['documents_generated'] += 1
            self.stats['total_time'] += generation_time
            
            # Prepare result with performance metrics
            result = {
                'document_id': document_id,
                'type': document_type,
                'content': content,
                'quality_score': validation_result.score,
                'metadata': metadata.to_dict(),
                'generation_time': generation_time,
                'cache_hit': cache_hit,
                'performance_metrics': {
                    'generation_time': generation_time,
                    'cache_hit': cache_hit,
                    'memory_mode': self.memory_mode,
                    'parallel_generation': parallel_sections or self.memory_mode == 'performance',
                    'docs_per_second': 1.0 / max(generation_time, 0.001)
                },
                'validation': {
                    'is_valid': validation_result.is_valid,
                    'errors': validation_result.errors,
                    'warnings': validation_result.warnings,
                    'suggestions': validation_result.suggestions
                }
            }
            
            logger.info(f"Successfully generated {document_type} document with score {validation_result.score}")
            
            return result
            
        except Exception as e:
            logger.error(f"Document generation failed: {e}")
            raise DocumentGenerationError(f"Failed to generate document: {e}")
    
    async def _generate_sequential_sections(self, template: Dict[str, Any], context: Dict[str, Any]) -> str:
        """Generate document sections sequentially."""
        sections_content = []
        system_prompt = self.prompt_engine.construct_system_prompt(template['document_type'])
        
        for section in template['sections']:
            # Build prompt for this section
            previous_content = '\n\n'.join(sections_content) if sections_content else None
            section_prompt = self.prompt_engine.create_section_prompt(
                section, context, previous_content
            )
            
            # Generate section content
            try:
                response = self.llm_adapter.generate(
                    prompt=section_prompt,
                    max_tokens=self.config.get('ai.max_tokens', 2000),
                    temperature=self.config.get('ai.temperature', 0.7)
                )
                
                section_content = response.content
                
                # Add section header if not present
                section_name = section['name'].replace('_', ' ').title()
                if not section_content.startswith('#'):
                    section_content = f"## {section_name}\n\n{section_content}"
                
                sections_content.append(section_content)
                
            except Exception as e:
                logger.error(f"Failed to generate section '{section['name']}': {e}")
                if section.get('required', True):
                    raise
                else:
                    # Skip optional section on failure
                    continue
        
        # Combine all sections
        document = '\n\n'.join(sections_content)
        
        return document
    
    async def _generate_parallel_sections(self, template: Dict[str, Any], context: Dict[str, Any]) -> str:
        """Generate document sections in parallel."""
        sections_content = {}
        tasks = []
        
        async def generate_section(section: Dict[str, Any], section_idx: int):
            """Generate a single section."""
            section_prompt = self.prompt_engine.create_section_prompt(section, context)
            
            try:
                # Run synchronous LLM call in thread pool
                loop = asyncio.get_event_loop()
                response = await loop.run_in_executor(
                    self.executor,
                    self.llm_adapter.generate,
                    section_prompt,
                    None,  # provider
                    self.config.get('ai.max_tokens', 2000),
                    self.config.get('ai.temperature', 0.7)
                )
                
                section_content = response.content
                
                # Add section header if not present
                section_name = section['name'].replace('_', ' ').title()
                if not section_content.startswith('#'):
                    section_content = f"## {section_name}\n\n{section_content}"
                
                sections_content[section_idx] = section_content
                
            except Exception as e:
                logger.error(f"Failed to generate section '{section['name']}': {e}")
                if section.get('required', True):
                    raise
                else:
                    sections_content[section_idx] = None
        
        # Create tasks for all sections
        for idx, section in enumerate(template['sections']):
            task = generate_section(section, idx)
            tasks.append(task)
        
        # Execute all tasks in parallel
        await asyncio.gather(*tasks)
        
        # Combine sections in order
        document_parts = []
        for idx in range(len(template['sections'])):
            if idx in sections_content and sections_content[idx]:
                document_parts.append(sections_content[idx])
        
        document = '\n\n'.join(document_parts)
        
        return document
    
    def list_templates(self) -> List[str]:
        """List available document templates."""
        return self.template_manager.list_templates()
    
    def get_template_info(self, template_name: str) -> Dict[str, Any]:
        """Get information about a specific template."""
        template = self.template_manager.load_template(template_name)
        
        return {
            'name': template.get('name', template_name),
            'type': template['document_type'],
            'sections': [s['name'] for s in template['sections']],
            'required_context': template.get('context_requirements', []),
            'quality_criteria': template.get('quality_criteria', {})
        }
    
    async def regenerate_section(self, 
                                 document_id: str,
                                 section_name: str,
                                 additional_context: Optional[Dict[str, Any]] = None) -> str:
        """Regenerate a specific section of an existing document."""
        # Retrieve existing document
        document = self.storage.get_document(document_id)
        
        if not document:
            raise DocumentGenerationError(f"Document not found: {document_id}")
        
        # Load template
        template = self.template_manager.load_template(document.type)
        
        # Find section in template
        section = None
        for s in template['sections']:
            if s['name'] == section_name:
                section = s
                break
        
        if not section:
            raise DocumentGenerationError(f"Section not found: {section_name}")
        
        # Extract context (combine stored metadata with additional context)
        context = document.metadata.custom.copy()
        if additional_context:
            context.update(additional_context)
        
        # Generate new section content
        section_prompt = self.prompt_engine.create_section_prompt(section, context)
        
        response = self.llm_adapter.generate(
            prompt=section_prompt,
            max_tokens=self.config.get('ai.max_tokens', 2000),
            temperature=self.config.get('ai.temperature', 0.7)
        )
        
        return response.content
    
    async def _extract_context_optimized(self, project_path: str) -> Dict[str, Any]:
        """Extract context with performance optimizations."""
        # Use process pool for CPU-intensive extraction if available
        if self.process_pool:
            loop = asyncio.get_event_loop()
            context = await loop.run_in_executor(
                self.process_pool,
                self.context_builder.extract_from_project,
                project_path
            )
        else:
            context = self.context_builder.extract_from_project(project_path)
        
        return context
    
    async def _generate_parallel_optimized(self, template: Dict[str, Any], context: Dict[str, Any]) -> str:
        """Optimized parallel generation with batching and caching."""
        sections_content = {}
        
        # Group sections by similarity for batch processing
        section_groups = self._group_similar_sections(template['sections'])
        
        async def generate_batch(sections: List[Dict], start_idx: int):
            """Generate multiple sections in a batch."""
            batch_prompts = []
            indices = []
            
            for i, section in enumerate(sections):
                section_prompt = self.prompt_engine.create_section_prompt(section, context)
                batch_prompts.append(section_prompt)
                indices.append(start_idx + i)
            
            # Check cache for each prompt
            cached_results = {}
            uncached_prompts = []
            uncached_indices = []
            
            for i, prompt in enumerate(batch_prompts):
                cached = self.response_cache.get(prompt, context)
                if cached:
                    cached_results[indices[i]] = cached.content
                else:
                    uncached_prompts.append(prompt)
                    uncached_indices.append(indices[i])
            
            # Generate uncached content in parallel
            if uncached_prompts:
                tasks = []
                for prompt in uncached_prompts:
                    task = self._generate_single_cached(prompt, context)
                    tasks.append(task)
                
                results = await asyncio.gather(*tasks)
                
                for idx, content in zip(uncached_indices, results):
                    sections_content[idx] = content
            
            # Add cached results
            sections_content.update(cached_results)
        
        # Process all groups in parallel
        tasks = []
        idx = 0
        for group in section_groups:
            task = generate_batch(group, idx)
            tasks.append(task)
            idx += len(group)
        
        await asyncio.gather(*tasks)
        
        # Combine sections in order
        document_parts = []
        for idx in range(len(template['sections'])):
            if idx in sections_content and sections_content[idx]:
                # Add section header if not present
                section = template['sections'][idx]
                section_name = section['name'].replace('_', ' ').title()
                section_content = sections_content[idx]
                
                if not section_content.startswith('#'):
                    section_content = f"## {section_name}\n\n{section_content}"
                
                document_parts.append(section_content)
        
        return '\n\n'.join(document_parts)
    
    def _group_similar_sections(self, sections: List[Dict]) -> List[List[Dict]]:
        """Group similar sections for batch processing."""
        # Simple grouping by required flag and prompt similarity
        required_sections = []
        optional_sections = []
        
        for section in sections:
            if section.get('required', True):
                required_sections.append(section)
            else:
                optional_sections.append(section)
        
        # Group into batches of up to 3 sections
        groups = []
        batch_size = 3
        
        for i in range(0, len(required_sections), batch_size):
            groups.append(required_sections[i:i+batch_size])
        
        for i in range(0, len(optional_sections), batch_size):
            groups.append(optional_sections[i:i+batch_size])
        
        return groups
    
    async def _generate_single_cached(self, prompt: str, context: Dict[str, Any], user_id: str = 'default') -> str:
        """Generate single section with caching and security."""
        # Check cache first with user isolation
        cached = self.response_cache.get(prompt, context, user_id=user_id)
        if cached:
            return cached.content
        
        # Generate new content
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            self.executor,
            self.llm_adapter.generate,
            prompt,
            None,  # provider
            self.config.get('ai.max_tokens', 2000),
            self.config.get('ai.temperature', 0.7)
        )
        
        # Cache the response with user isolation
        self.response_cache.put(prompt, context, response.content, 
                               response.tokens_used, response.cost, user_id)
        
        return response.content
    
    async def generate_batch(self, requests: List[BatchRequest], user_id: str = 'default') -> Dict[str, GenerationResult]:
        """Generate multiple documents in a batch with security controls."""
        return await self.batch_processor.process_batch(requests, user_id)
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get performance statistics."""
        cache_stats = self.response_cache.get_stats()
        perf_stats = self.performance_monitor.get_stats()
        
        # Calculate overall performance
        total_time = self.stats['total_time']
        docs_generated = self.stats['documents_generated']
        avg_time = total_time / max(docs_generated, 1)
        docs_per_second = docs_generated / max(total_time, 0.001)
        docs_per_minute = docs_per_second * 60
        
        return {
            'documents_generated': docs_generated,
            'average_generation_time': avg_time,
            'documents_per_second': docs_per_second,
            'documents_per_minute': docs_per_minute,
            'cache_statistics': cache_stats,
            'performance_metrics': perf_stats,
            'memory_mode': self.memory_mode,
            'max_workers': self.max_workers,
            'total_cost': self.stats['total_cost'],
            'total_tokens': self.stats['total_tokens']
        }
    
    def get_security_metrics(self) -> Dict[str, Any]:
        """Get comprehensive security metrics and audit information."""
        return self.security_manager.get_security_metrics()
    
    def clear_caches(self):
        """Clear all caches with security audit."""
        self.security_manager._log_security_event('CACHE_CLEAR', {
            'timestamp': datetime.now().isoformat()
        })
        self.response_cache = ResponseCache(self.config, self.security_manager)
        self.context_cache = ContextCache(self.config)
        logger.info("All caches cleared")


# ============================================================================
# Convenience Functions
# ============================================================================

async def generate_document(document_type: str, 
                           project_path: str,
                           config: Optional[ConfigurationManager] = None,
                           **kwargs) -> Dict[str, Any]:
    """Convenience function to generate a document."""
    generator = DocumentGenerator(config=config)
    return await generator.generate(document_type, project_path, **kwargs)


def list_available_templates(config: Optional[ConfigurationManager] = None) -> List[str]:
    """List available document templates."""
    manager = TemplateManager(config or ConfigurationManager())
    return manager.list_templates()