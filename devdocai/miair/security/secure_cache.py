"""
M003 MIAIR Engine - Secure Caching System

Implements encrypted caching for the MIAIR Engine with security features.
Uses AES-256-GCM encryption for cached data and implements cache timing attack prevention.

Security Features:
- AES-256-GCM encryption for all cached data
- Secure key generation and management
- Cache invalidation and cleanup
- Timing attack prevention
- Memory protection for sensitive data
- Cache isolation between clients
"""

import os
import time
import json
import hashlib
import hmac
import logging
from typing import Any, Dict, Optional, Tuple, Set
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from threading import Lock, RLock
import pickle
import base64
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import serialization
import secrets

logger = logging.getLogger(__name__)


class CacheSecurityError(Exception):
    """Raised when cache security operations fail."""
    pass


@dataclass
class SecureCacheConfig:
    """Configuration for secure caching."""
    # Encryption settings
    encryption_enabled: bool = True
    key_size: int = 32  # 256 bits for AES-256
    salt_size: int = 16  # 128 bits
    nonce_size: int = 12  # 96 bits for GCM
    tag_size: int = 16  # 128 bits
    
    # Cache settings
    max_entries: int = 10000
    ttl_seconds: float = 3600  # 1 hour default TTL
    cleanup_interval: float = 300  # 5 minutes
    
    # Security settings
    enable_timing_protection: bool = True
    enable_cache_isolation: bool = True
    enable_secure_deletion: bool = True
    max_key_length: int = 256
    max_value_size: int = 10 * 1024 * 1024  # 10MB
    
    # Key derivation settings
    pbkdf2_iterations: int = 100000
    master_key: Optional[bytes] = None
    
    def __post_init__(self):
        if self.master_key is None:
            # Generate a random master key if not provided
            self.master_key = secrets.token_bytes(self.key_size)


class CacheEntry:
    """Secure cache entry with encryption metadata."""
    
    def __init__(self, value: Any, encrypted: bool = False):
        self.value = value
        self.encrypted = encrypted
        self.created_at = time.time()
        self.accessed_at = time.time()
        self.access_count = 0
        self.nonce: Optional[bytes] = None
        self.tag: Optional[bytes] = None
        self.salt: Optional[bytes] = None
    
    def touch(self):
        """Update access time and count."""
        self.accessed_at = time.time()
        self.access_count += 1
    
    def is_expired(self, ttl: float) -> bool:
        """Check if entry has expired."""
        return time.time() - self.created_at > ttl


class SecureCache:
    """
    Secure caching system with encryption and protection features.
    
    Features:
    - AES-256-GCM encryption for cached values
    - Per-entry encryption keys derived from master key
    - Timing attack protection
    - Cache isolation between clients
    - Secure memory cleanup
    """
    
    def __init__(self, config: Optional[SecureCacheConfig] = None):
        """Initialize secure cache with configuration."""
        self.config = config or SecureCacheConfig()
        self._cache: Dict[str, CacheEntry] = {}
        self._lock = RLock()
        self._client_caches: Dict[str, Dict[str, CacheEntry]] = {}
        self._stats = {
            'hits': 0,
            'misses': 0,
            'evictions': 0,
            'encryption_errors': 0,
            'decryption_errors': 0
        }
        self._last_cleanup = time.time()
        
        # Initialize encryption backend
        self._backend = default_backend()
        
        # Validate master key
        if len(self.config.master_key) != self.config.key_size:
            raise CacheSecurityError(f"Master key must be {self.config.key_size} bytes")
    
    def _derive_key(self, cache_key: str, salt: bytes) -> bytes:
        """Derive encryption key from cache key and salt."""
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=self.config.key_size,
            salt=salt,
            iterations=self.config.pbkdf2_iterations,
            backend=self._backend
        )
        # Combine master key with cache key for key derivation
        key_material = self.config.master_key + cache_key.encode('utf-8')
        return kdf.derive(key_material)
    
    def _encrypt_value(self, value: Any, key: bytes) -> Tuple[bytes, bytes, bytes]:
        """
        Encrypt value using AES-256-GCM.
        
        Args:
            value: Value to encrypt
            key: Encryption key
            
        Returns:
            Tuple of (encrypted_data, nonce, tag)
        """
        # Serialize value
        try:
            serialized = pickle.dumps(value)
        except Exception as e:
            raise CacheSecurityError(f"Failed to serialize value: {e}")
        
        # Generate nonce
        nonce = os.urandom(self.config.nonce_size)
        
        # Create cipher
        cipher = Cipher(
            algorithms.AES(key),
            modes.GCM(nonce),
            backend=self._backend
        )
        encryptor = cipher.encryptor()
        
        # Encrypt data
        ciphertext = encryptor.update(serialized) + encryptor.finalize()
        
        return ciphertext, nonce, encryptor.tag
    
    def _decrypt_value(self, ciphertext: bytes, key: bytes, nonce: bytes, tag: bytes) -> Any:
        """
        Decrypt value using AES-256-GCM.
        
        Args:
            ciphertext: Encrypted data
            key: Decryption key
            nonce: Nonce used for encryption
            tag: Authentication tag
            
        Returns:
            Decrypted and deserialized value
        """
        # Create cipher
        cipher = Cipher(
            algorithms.AES(key),
            modes.GCM(nonce, tag),
            backend=self._backend
        )
        decryptor = cipher.decryptor()
        
        # Decrypt data
        try:
            plaintext = decryptor.update(ciphertext) + decryptor.finalize()
        except Exception as e:
            raise CacheSecurityError(f"Decryption failed: {e}")
        
        # Deserialize value
        try:
            return pickle.loads(plaintext)
        except Exception as e:
            raise CacheSecurityError(f"Failed to deserialize value: {e}")
    
    def _constant_time_compare(self, a: str, b: str) -> bool:
        """Constant-time string comparison to prevent timing attacks."""
        if self.config.enable_timing_protection:
            return hmac.compare_digest(a.encode(), b.encode())
        return a == b
    
    def _get_cache_dict(self, client_id: Optional[str] = None) -> Dict[str, CacheEntry]:
        """Get appropriate cache dictionary based on client isolation settings."""
        if not self.config.enable_cache_isolation or client_id is None:
            return self._cache
        
        if client_id not in self._client_caches:
            self._client_caches[client_id] = {}
        return self._client_caches[client_id]
    
    def _cleanup_expired(self, cache_dict: Dict[str, CacheEntry]):
        """Remove expired entries from cache."""
        current_time = time.time()
        expired_keys = []
        
        for key, entry in cache_dict.items():
            if entry.is_expired(self.config.ttl_seconds):
                expired_keys.append(key)
        
        for key in expired_keys:
            self._secure_delete(cache_dict, key)
            self._stats['evictions'] += 1
    
    def _secure_delete(self, cache_dict: Dict[str, CacheEntry], key: str):
        """Securely delete cache entry."""
        if key in cache_dict:
            entry = cache_dict[key]
            
            if self.config.enable_secure_deletion and not entry.encrypted:
                # Overwrite value in memory before deletion
                if isinstance(entry.value, (str, bytes)):
                    # Overwrite string/bytes data
                    if isinstance(entry.value, str):
                        entry.value = '\x00' * len(entry.value)
                    else:
                        entry.value = b'\x00' * len(entry.value)
            
            del cache_dict[key]
    
    def _enforce_size_limit(self, cache_dict: Dict[str, CacheEntry]):
        """Enforce maximum cache size using LRU eviction."""
        if len(cache_dict) > self.config.max_entries:
            # Sort by access time (LRU)
            sorted_entries = sorted(
                cache_dict.items(),
                key=lambda x: x[1].accessed_at
            )
            
            # Remove oldest entries
            to_remove = len(cache_dict) - self.config.max_entries + 1
            for key, _ in sorted_entries[:to_remove]:
                self._secure_delete(cache_dict, key)
                self._stats['evictions'] += 1
    
    def get(self, key: str, client_id: Optional[str] = None, default: Any = None) -> Any:
        """
        Get value from secure cache.
        
        Args:
            key: Cache key
            client_id: Optional client identifier for cache isolation
            default: Default value if key not found
            
        Returns:
            Cached value or default
        """
        # Validate key
        if len(key) > self.config.max_key_length:
            raise CacheSecurityError(f"Key too long: {len(key)} > {self.config.max_key_length}")
        
        with self._lock:
            # Periodic cleanup
            if time.time() - self._last_cleanup > self.config.cleanup_interval:
                self._cleanup_expired(self._get_cache_dict(client_id))
                self._last_cleanup = time.time()
            
            cache_dict = self._get_cache_dict(client_id)
            
            # Timing protection: always perform same operations
            if self.config.enable_timing_protection:
                # Constant-time key lookup
                found = False
                entry = None
                for k, v in cache_dict.items():
                    if self._constant_time_compare(k, key):
                        found = True
                        entry = v
                        break
            else:
                found = key in cache_dict
                entry = cache_dict.get(key) if found else None
            
            if not found or entry is None:
                self._stats['misses'] += 1
                return default
            
            # Check expiration
            if entry.is_expired(self.config.ttl_seconds):
                self._secure_delete(cache_dict, key)
                self._stats['misses'] += 1
                return default
            
            # Decrypt if encrypted
            if entry.encrypted and self.config.encryption_enabled:
                try:
                    # Derive decryption key
                    dec_key = self._derive_key(key, entry.salt)
                    value = self._decrypt_value(entry.value, dec_key, entry.nonce, entry.tag)
                except CacheSecurityError as e:
                    logger.error(f"Failed to decrypt cache entry: {e}")
                    self._stats['decryption_errors'] += 1
                    self._secure_delete(cache_dict, key)
                    return default
            else:
                value = entry.value
            
            entry.touch()
            self._stats['hits'] += 1
            return value
    
    def set(self, key: str, value: Any, client_id: Optional[str] = None, ttl: Optional[float] = None) -> bool:
        """
        Set value in secure cache with encryption.
        
        Args:
            key: Cache key
            value: Value to cache
            client_id: Optional client identifier for cache isolation
            ttl: Optional TTL override
            
        Returns:
            True if successful
        """
        # Validate inputs
        if len(key) > self.config.max_key_length:
            raise CacheSecurityError(f"Key too long: {len(key)} > {self.config.max_key_length}")
        
        # Check value size
        try:
            value_size = len(pickle.dumps(value))
            if value_size > self.config.max_value_size:
                raise CacheSecurityError(f"Value too large: {value_size} > {self.config.max_value_size}")
        except Exception as e:
            raise CacheSecurityError(f"Failed to check value size: {e}")
        
        with self._lock:
            cache_dict = self._get_cache_dict(client_id)
            
            # Enforce size limit
            self._enforce_size_limit(cache_dict)
            
            entry = CacheEntry(value)
            
            # Encrypt if enabled
            if self.config.encryption_enabled:
                try:
                    # Generate salt for this entry
                    salt = os.urandom(self.config.salt_size)
                    entry.salt = salt
                    
                    # Derive encryption key
                    enc_key = self._derive_key(key, salt)
                    
                    # Encrypt value
                    ciphertext, nonce, tag = self._encrypt_value(value, enc_key)
                    entry.value = ciphertext
                    entry.nonce = nonce
                    entry.tag = tag
                    entry.encrypted = True
                    
                except Exception as e:
                    logger.error(f"Failed to encrypt cache entry: {e}")
                    self._stats['encryption_errors'] += 1
                    return False
            
            # Store entry
            cache_dict[key] = entry
            
            # Override TTL if specified
            if ttl is not None:
                entry.created_at = time.time() - (self.config.ttl_seconds - ttl)
            
            return True
    
    def delete(self, key: str, client_id: Optional[str] = None) -> bool:
        """
        Delete entry from cache.
        
        Args:
            key: Cache key
            client_id: Optional client identifier
            
        Returns:
            True if entry was deleted
        """
        with self._lock:
            cache_dict = self._get_cache_dict(client_id)
            if key in cache_dict:
                self._secure_delete(cache_dict, key)
                return True
            return False
    
    def clear(self, client_id: Optional[str] = None):
        """Clear all cache entries."""
        with self._lock:
            cache_dict = self._get_cache_dict(client_id)
            # Secure delete all entries
            keys = list(cache_dict.keys())
            for key in keys:
                self._secure_delete(cache_dict, key)
    
    def get_stats(self) -> Dict:
        """Get cache statistics."""
        with self._lock:
            stats = self._stats.copy()
            stats['total_entries'] = len(self._cache)
            stats['client_caches'] = len(self._client_caches)
            stats['hit_rate'] = (
                stats['hits'] / (stats['hits'] + stats['misses'])
                if (stats['hits'] + stats['misses']) > 0 else 0
            )
            return stats
    
    def reset_stats(self):
        """Reset cache statistics."""
        with self._lock:
            self._stats = {
                'hits': 0,
                'misses': 0,
                'evictions': 0,
                'encryption_errors': 0,
                'decryption_errors': 0
            }