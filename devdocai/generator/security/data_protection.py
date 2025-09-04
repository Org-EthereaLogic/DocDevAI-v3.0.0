"""
Data Protection and PII Handling for AI Document Generation.

Integrates with M002 PII detector and M010 security module to provide
comprehensive data protection for LLM-based document generation.

Security Features:
- PII detection and masking before LLM calls
- Encrypted caching of sensitive data
- Session isolation and data segregation
- GDPR/CCPA compliance support
- Secure context handling
- API key rotation and protection
"""

import os
import json
import logging
import hashlib
import secrets
from typing import Dict, List, Optional, Any, Tuple, Set
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
import base64

# Cryptography imports
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2
from cryptography.hazmat.backends import default_backend

# Import existing PII detector from M002/M010
try:
    from devdocai.security.pii_detector_unified import UnifiedPIIDetector
except ImportError:
    # Fallback if unified version not available
    from devdocai.storage.pii_detector import PIIDetector as UnifiedPIIDetector

logger = logging.getLogger(__name__)


class DataClassification(Enum):
    """Data sensitivity classification levels."""
    PUBLIC = "public"
    INTERNAL = "internal"
    CONFIDENTIAL = "confidential"
    SECRET = "secret"
    TOP_SECRET = "top_secret"


class ComplianceMode(Enum):
    """Compliance mode for data handling."""
    NONE = "none"
    GDPR = "gdpr"
    CCPA = "ccpa"
    HIPAA = "hipaa"
    SOC2 = "soc2"
    ALL = "all"


@dataclass
class PIIMatch:
    """Represents a detected PII instance."""
    text: str
    category: str
    start: int
    end: int
    confidence: float
    masked_value: str


@dataclass
class ProtectedData:
    """Container for protected data with encryption."""
    original_hash: str
    encrypted_data: bytes
    classification: DataClassification
    pii_detected: bool
    pii_categories: List[str]
    created_at: datetime
    expires_at: Optional[datetime]
    access_count: int = 0


class DataProtectionManager:
    """
    Comprehensive data protection for AI document generation.
    
    Features:
    - PII detection and masking
    - Data encryption at rest
    - Session isolation
    - Compliance support
    - Secure key management
    """
    
    def __init__(
        self,
        compliance_mode: ComplianceMode = ComplianceMode.GDPR,
        enable_encryption: bool = True,
        enable_pii_detection: bool = True,
        cache_dir: Optional[Path] = None
    ):
        """
        Initialize data protection manager.
        
        Args:
            compliance_mode: Compliance requirements to enforce
            enable_encryption: Enable data encryption
            enable_pii_detection: Enable PII detection
            cache_dir: Directory for secure cache storage
        """
        self.compliance_mode = compliance_mode
        self.enable_encryption = enable_encryption
        self.enable_pii_detection = enable_pii_detection
        self.cache_dir = cache_dir or Path("./secure_cache")
        
        # Initialize PII detector
        if enable_pii_detection:
            self._init_pii_detector()
            
        # Initialize encryption
        if enable_encryption:
            self._init_encryption()
            
        # Session isolation
        self.session_data: Dict[str, Dict[str, ProtectedData]] = {}
        self.session_keys: Dict[str, bytes] = {}
        
        # Compliance tracking
        self.compliance_log: List[Dict[str, Any]] = []
        
        # API key management
        self.api_keys: Dict[str, Tuple[str, datetime]] = {}  # key_id -> (encrypted_key, rotation_date)
        
    def _init_pii_detector(self):
        """Initialize PII detection system."""
        try:
            # Use unified PII detector from M010
            self.pii_detector = UnifiedPIIDetector(
                language="en",
                confidence_threshold=0.8,
                enable_context_analysis=True
            )
            logger.info("Initialized unified PII detector")
        except Exception as e:
            logger.warning(f"Could not initialize unified PII detector: {e}")
            # Create basic fallback PII detector
            self.pii_detector = None
            self._init_fallback_pii_patterns()
            
    def _init_fallback_pii_patterns(self):
        """Initialize fallback PII patterns if unified detector unavailable."""
        self.pii_patterns = {
            "email": r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
            "phone": r"\b(?:\+?1[-.]?)?\(?[0-9]{3}\)?[-.]?[0-9]{3}[-.]?[0-9]{4}\b",
            "ssn": r"\b(?!000|666)[0-9]{3}-(?!00)[0-9]{2}-(?!0000)[0-9]{4}\b",
            "credit_card": r"\b(?:4[0-9]{12}(?:[0-9]{3})?|5[1-5][0-9]{14}|3[47][0-9]{13}|3(?:0[0-5]|[68][0-9])[0-9]{11}|6(?:011|5[0-9]{2})[0-9]{12}|(?:2131|1800|35\d{3})\d{11})\b",
            "ip_address": r"\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b",
            "aws_key": r"AKIA[0-9A-Z]{16}",
            "api_key": r"\b[A-Za-z0-9]{32,}\b",  # Generic API key pattern
        }
        
    def _init_encryption(self):
        """Initialize encryption system."""
        # Generate master key from environment or create new
        master_key_env = os.environ.get("DEVDOCAI_MASTER_KEY")
        
        if master_key_env:
            self.master_key = base64.b64decode(master_key_env.encode())
        else:
            # Generate new master key (should be stored securely)
            self.master_key = Fernet.generate_key()
            logger.warning("Generated new master key - store securely!")
            
        # Create cipher suite
        self.cipher_suite = Fernet(self.master_key)
        
        # Create secure cache directory
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        os.chmod(self.cache_dir, 0o700)  # Restrict access
        
    def scan_for_pii(self, text: str) -> Tuple[bool, List[PIIMatch], str]:
        """
        Scan text for PII and return masked version.
        
        Args:
            text: Text to scan
            
        Returns:
            Tuple of (has_pii, pii_matches, masked_text)
        """
        if not self.enable_pii_detection:
            return False, [], text
            
        pii_matches = []
        masked_text = text
        
        if self.pii_detector:
            # Use unified PII detector
            try:
                result = self.pii_detector.detect_pii(text)
                
                # Process detection results
                for detection in result.get("detections", []):
                    match = PIIMatch(
                        text=detection["text"],
                        category=detection["category"],
                        start=detection["start"],
                        end=detection["end"],
                        confidence=detection["confidence"],
                        masked_value=self._mask_value(detection["text"], detection["category"])
                    )
                    pii_matches.append(match)
                    
                # Apply masking
                masked_text = result.get("masked_text", text)
                
            except Exception as e:
                logger.error(f"PII detection failed: {e}")
                # Fall back to pattern matching
                pii_matches, masked_text = self._fallback_pii_detection(text)
        else:
            # Use fallback pattern matching
            pii_matches, masked_text = self._fallback_pii_detection(text)
            
        has_pii = len(pii_matches) > 0
        
        # Log for compliance
        if has_pii and self.compliance_mode != ComplianceMode.NONE:
            self._log_compliance_event("pii_detected", {
                "categories": list(set(m.category for m in pii_matches)),
                "count": len(pii_matches)
            })
            
        return has_pii, pii_matches, masked_text
        
    def _fallback_pii_detection(self, text: str) -> Tuple[List[PIIMatch], str]:
        """Fallback PII detection using regex patterns."""
        import re
        
        matches = []
        masked_text = text
        
        for category, pattern in self.pii_patterns.items():
            for match in re.finditer(pattern, text):
                pii_match = PIIMatch(
                    text=match.group(),
                    category=category,
                    start=match.start(),
                    end=match.end(),
                    confidence=0.7,  # Lower confidence for pattern matching
                    masked_value=self._mask_value(match.group(), category)
                )
                matches.append(pii_match)
                
        # Apply masking (simple replacement)
        for match in sorted(matches, key=lambda x: x.start, reverse=True):
            masked_text = masked_text[:match.start] + match.masked_value + masked_text[match.end:]
            
        return matches, masked_text
        
    def _mask_value(self, value: str, category: str) -> str:
        """Generate masked value based on PII category."""
        if category == "email":
            parts = value.split("@")
            if len(parts) == 2:
                return f"{parts[0][:2]}***@{parts[1]}"
            return "***@***.***"
        elif category == "phone":
            return "***-***-" + value[-4:] if len(value) >= 4 else "***-***-****"
        elif category == "ssn":
            return "***-**-" + value[-4:] if len(value) >= 4 else "***-**-****"
        elif category == "credit_card":
            return "**** **** **** " + value[-4:] if len(value) >= 4 else "**** **** **** ****"
        else:
            # Generic masking
            if len(value) <= 4:
                return "****"
            return value[:2] + "*" * (len(value) - 4) + value[-2:]
            
    def encrypt_data(
        self,
        data: str,
        classification: DataClassification = DataClassification.CONFIDENTIAL,
        session_id: Optional[str] = None
    ) -> ProtectedData:
        """
        Encrypt sensitive data with classification.
        
        Args:
            data: Data to encrypt
            classification: Data sensitivity level
            session_id: Session for isolation
            
        Returns:
            Protected data container
        """
        if not self.enable_encryption:
            # Return unencrypted if encryption disabled
            return ProtectedData(
                original_hash=hashlib.sha256(data.encode()).hexdigest(),
                encrypted_data=data.encode(),
                classification=classification,
                pii_detected=False,
                pii_categories=[],
                created_at=datetime.now(),
                expires_at=None
            )
            
        # Check for PII
        has_pii, pii_matches, _ = self.scan_for_pii(data)
        
        # Get session-specific key if provided
        if session_id:
            encryption_key = self._get_session_key(session_id)
        else:
            encryption_key = self.master_key
            
        # Encrypt data
        cipher = Fernet(encryption_key)
        encrypted = cipher.encrypt(data.encode())
        
        # Create protected data container
        protected = ProtectedData(
            original_hash=hashlib.sha256(data.encode()).hexdigest(),
            encrypted_data=encrypted,
            classification=classification,
            pii_detected=has_pii,
            pii_categories=list(set(m.category for m in pii_matches)),
            created_at=datetime.now(),
            expires_at=self._calculate_expiration(classification)
        )
        
        # Store in session if provided
        if session_id:
            if session_id not in self.session_data:
                self.session_data[session_id] = {}
            self.session_data[session_id][protected.original_hash] = protected
            
        return protected
        
    def decrypt_data(
        self,
        protected: ProtectedData,
        session_id: Optional[str] = None,
        purpose: str = "processing"
    ) -> Optional[str]:
        """
        Decrypt protected data with audit logging.
        
        Args:
            protected: Protected data container
            session_id: Session for isolation
            purpose: Reason for decryption
            
        Returns:
            Decrypted data or None if failed
        """
        if not self.enable_encryption:
            return protected.encrypted_data.decode()
            
        try:
            # Get appropriate key
            if session_id:
                decryption_key = self._get_session_key(session_id)
            else:
                decryption_key = self.master_key
                
            # Decrypt data
            cipher = Fernet(decryption_key)
            decrypted = cipher.decrypt(protected.encrypted_data)
            
            # Update access count
            protected.access_count += 1
            
            # Log access for compliance
            self._log_compliance_event("data_accessed", {
                "classification": protected.classification.value,
                "purpose": purpose,
                "has_pii": protected.pii_detected,
                "session": session_id
            })
            
            return decrypted.decode()
            
        except Exception as e:
            logger.error(f"Decryption failed: {e}")
            return None
            
    def _get_session_key(self, session_id: str) -> bytes:
        """Get or create session-specific encryption key."""
        if session_id not in self.session_keys:
            # Derive session key from master key
            kdf = PBKDF2(
                algorithm=hashes.SHA256(),
                length=32,
                salt=session_id.encode(),
                iterations=100000,
                backend=default_backend()
            )
            session_key = base64.urlsafe_b64encode(kdf.derive(self.master_key))
            self.session_keys[session_id] = session_key
            
        return self.session_keys[session_id]
        
    def _calculate_expiration(self, classification: DataClassification) -> Optional[datetime]:
        """Calculate data expiration based on classification and compliance."""
        if self.compliance_mode == ComplianceMode.GDPR:
            # GDPR data retention limits
            retention_days = {
                DataClassification.PUBLIC: None,  # No expiration
                DataClassification.INTERNAL: 365,
                DataClassification.CONFIDENTIAL: 90,
                DataClassification.SECRET: 30,
                DataClassification.TOP_SECRET: 7
            }
        elif self.compliance_mode == ComplianceMode.CCPA:
            # CCPA retention limits
            retention_days = {
                DataClassification.PUBLIC: None,
                DataClassification.INTERNAL: 365,
                DataClassification.CONFIDENTIAL: 120,
                DataClassification.SECRET: 60,
                DataClassification.TOP_SECRET: 30
            }
        else:
            # Default retention
            retention_days = {
                DataClassification.PUBLIC: None,
                DataClassification.INTERNAL: None,
                DataClassification.CONFIDENTIAL: 180,
                DataClassification.SECRET: 90,
                DataClassification.TOP_SECRET: 30
            }
            
        days = retention_days.get(classification)
        if days:
            return datetime.now() + timedelta(days=days)
        return None
        
    def isolate_session(self, session_id: str) -> Dict[str, Any]:
        """
        Create isolated session for data processing.
        
        Args:
            session_id: Unique session identifier
            
        Returns:
            Session configuration
        """
        # Initialize session storage
        self.session_data[session_id] = {}
        
        # Generate session key
        session_key = self._get_session_key(session_id)
        
        # Create session config
        config = {
            "session_id": session_id,
            "created_at": datetime.now().isoformat(),
            "isolation_level": "strict",
            "encryption_enabled": self.enable_encryption,
            "pii_detection_enabled": self.enable_pii_detection,
            "compliance_mode": self.compliance_mode.value
        }
        
        # Log session creation
        self._log_compliance_event("session_created", config)
        
        return config
        
    def cleanup_session(self, session_id: str, secure_delete: bool = True):
        """
        Clean up session data with secure deletion.
        
        Args:
            session_id: Session to clean up
            secure_delete: Overwrite data before deletion
        """
        if session_id in self.session_data:
            # Secure deletion if requested
            if secure_delete:
                for data_hash, protected in self.session_data[session_id].items():
                    # Overwrite encrypted data
                    protected.encrypted_data = secrets.token_bytes(len(protected.encrypted_data))
                    
            # Remove session data
            del self.session_data[session_id]
            
        if session_id in self.session_keys:
            # Overwrite session key
            if secure_delete:
                self.session_keys[session_id] = secrets.token_bytes(32)
            del self.session_keys[session_id]
            
        # Log cleanup
        self._log_compliance_event("session_cleaned", {"session_id": session_id})
        
    def rotate_api_key(self, key_id: str, new_key: str) -> bool:
        """
        Rotate API key with secure storage.
        
        Args:
            key_id: Key identifier
            new_key: New API key value
            
        Returns:
            Success status
        """
        try:
            # Encrypt new key
            encrypted_key = self.cipher_suite.encrypt(new_key.encode())
            
            # Store with rotation timestamp
            self.api_keys[key_id] = (encrypted_key, datetime.now())
            
            # Log rotation
            self._log_compliance_event("api_key_rotated", {"key_id": key_id})
            
            return True
            
        except Exception as e:
            logger.error(f"API key rotation failed: {e}")
            return False
            
    def get_api_key(self, key_id: str) -> Optional[str]:
        """
        Retrieve decrypted API key.
        
        Args:
            key_id: Key identifier
            
        Returns:
            Decrypted API key or None
        """
        if key_id not in self.api_keys:
            return None
            
        try:
            encrypted_key, rotation_date = self.api_keys[key_id]
            
            # Check if key needs rotation (30 days)
            if datetime.now() - rotation_date > timedelta(days=30):
                logger.warning(f"API key {key_id} needs rotation")
                
            # Decrypt and return
            return self.cipher_suite.decrypt(encrypted_key).decode()
            
        except Exception as e:
            logger.error(f"API key retrieval failed: {e}")
            return None
            
    def _log_compliance_event(self, event_type: str, details: Dict[str, Any]):
        """Log compliance-related events."""
        event = {
            "timestamp": datetime.now().isoformat(),
            "event_type": event_type,
            "compliance_mode": self.compliance_mode.value,
            "details": details
        }
        
        self.compliance_log.append(event)
        
        # Also log to standard logger
        logger.info(f"Compliance event: {event_type} - {details}")
        
    def get_compliance_report(self) -> Dict[str, Any]:
        """Generate compliance report."""
        # Analyze compliance log
        event_counts = {}
        for event in self.compliance_log:
            event_type = event["event_type"]
            event_counts[event_type] = event_counts.get(event_type, 0) + 1
            
        # Calculate PII statistics
        pii_events = [e for e in self.compliance_log if e["event_type"] == "pii_detected"]
        pii_categories = set()
        for event in pii_events:
            categories = event["details"].get("categories", [])
            pii_categories.update(categories)
            
        return {
            "compliance_mode": self.compliance_mode.value,
            "total_events": len(self.compliance_log),
            "event_distribution": event_counts,
            "pii_detections": len(pii_events),
            "pii_categories_found": list(pii_categories),
            "active_sessions": len(self.session_data),
            "encrypted_items": sum(len(s) for s in self.session_data.values()),
            "api_keys_managed": len(self.api_keys),
            "report_generated": datetime.now().isoformat()
        }
        
    def cleanup_expired_data(self) -> int:
        """Clean up expired data based on retention policies."""
        cleaned = 0
        
        for session_id, session_items in list(self.session_data.items()):
            for data_hash, protected in list(session_items.items()):
                if protected.expires_at and datetime.now() > protected.expires_at:
                    # Secure deletion
                    protected.encrypted_data = secrets.token_bytes(len(protected.encrypted_data))
                    del session_items[data_hash]
                    cleaned += 1
                    
        logger.info(f"Cleaned up {cleaned} expired data items")
        return cleaned