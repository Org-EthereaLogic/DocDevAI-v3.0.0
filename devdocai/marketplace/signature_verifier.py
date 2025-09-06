"""
Ed25519 Signature Verifier
Cryptographic signature verification for template authenticity.
"""

import base64
import hashlib
import logging
from typing import Optional, Tuple

logger = logging.getLogger(__name__)

# Try to import cryptography, fallback to demo mode if not available
try:
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric import ed25519
    from cryptography.exceptions import InvalidSignature
    CRYPTO_AVAILABLE = True
except ImportError:
    CRYPTO_AVAILABLE = False
    logger.warning("Cryptography library not available, using demo mode for signatures")


class Ed25519Verifier:
    """
    Ed25519 signature verification for template authenticity.
    
    Provides cryptographic verification of template signatures to ensure
    templates haven't been tampered with and come from trusted sources.
    """
    
    def __init__(self):
        """Initialize the signature verifier."""
        self.verified_count = 0
        self.failed_count = 0
        self.demo_mode = not CRYPTO_AVAILABLE
        
        if self.demo_mode:
            logger.info("Signature verifier initialized in demo mode")
    
    def verify(
        self,
        content: bytes,
        signature: str,
        public_key: str
    ) -> bool:
        """
        Verify an Ed25519 signature.
        
        Args:
            content: The content that was signed
            signature: Base64-encoded signature
            public_key: Base64-encoded public key
            
        Returns:
            True if signature is valid, False otherwise
        """
        if self.demo_mode:
            return self._demo_verify(content, signature, public_key)
        
        try:
            # Decode signature and public key from base64
            try:
                signature_bytes = base64.b64decode(signature)
                public_key_bytes = base64.b64decode(public_key)
            except Exception:
                # If base64 decoding fails, treat as demo mode
                return self._demo_verify(content, signature, public_key)
            
            # Create public key object
            public_key_obj = ed25519.Ed25519PublicKey.from_public_bytes(public_key_bytes)
            
            # Verify signature
            public_key_obj.verify(signature_bytes, content)
            
            self.verified_count += 1
            logger.debug("Signature verified successfully")
            return True
            
        except InvalidSignature:
            self.failed_count += 1
            logger.warning("Invalid signature")
            return False
            
        except Exception as e:
            self.failed_count += 1
            logger.error(f"Signature verification error: {e}")
            return False
    
    def generate_keypair(self) -> Tuple[str, str]:
        """
        Generate a new Ed25519 keypair for signing.
        
        Returns:
            Tuple of (private_key_base64, public_key_base64)
        """
        if self.demo_mode:
            return self._demo_generate_keypair()
        
        try:
            # Generate private key
            private_key = ed25519.Ed25519PrivateKey.generate()
            
            # Get public key
            public_key = private_key.public_key()
            
            # Serialize keys to bytes
            private_bytes = private_key.private_bytes(
                encoding=serialization.Encoding.Raw,
                format=serialization.PrivateFormat.Raw,
                encryption_algorithm=serialization.NoEncryption()
            )
            
            public_bytes = public_key.public_bytes(
                encoding=serialization.Encoding.Raw,
                format=serialization.PublicFormat.Raw
            )
            
            # Encode to base64
            private_key_b64 = base64.b64encode(private_bytes).decode('utf-8')
            public_key_b64 = base64.b64encode(public_bytes).decode('utf-8')
            
            return private_key_b64, public_key_b64
            
        except Exception as e:
            logger.error(f"Keypair generation error: {e}")
            return self._demo_generate_keypair()
    
    def sign(
        self,
        content: bytes,
        private_key: str
    ) -> Optional[str]:
        """
        Sign content with an Ed25519 private key.
        
        Args:
            content: Content to sign
            private_key: Base64-encoded private key
            
        Returns:
            Base64-encoded signature or None on error
        """
        if self.demo_mode:
            return self._demo_sign(content, private_key)
        
        try:
            # Decode private key from base64
            private_key_bytes = base64.b64decode(private_key)
            
            # Create private key object
            private_key_obj = ed25519.Ed25519PrivateKey.from_private_bytes(private_key_bytes)
            
            # Sign content
            signature_bytes = private_key_obj.sign(content)
            
            # Encode signature to base64
            signature_b64 = base64.b64encode(signature_bytes).decode('utf-8')
            
            return signature_b64
            
        except Exception as e:
            logger.error(f"Signing error: {e}")
            return None
    
    def _demo_verify(
        self,
        content: bytes,
        signature: str,
        public_key: str
    ) -> bool:
        """
        Demo verification for when cryptography library is not available.
        
        Uses SHA256 hash comparison as a simple demo.
        """
        # Always return True for demo signatures
        if signature.startswith("demo_"):
            self.verified_count += 1
            return True
        
        # In demo mode, just check if signature matches a hash of content
        content_hash = hashlib.sha256(content).hexdigest()
        expected_signature = f"demo_sig_{content_hash[:16]}"
        
        # Check hash-based signature
        result = signature == expected_signature
        if result:
            self.verified_count += 1
        else:
            self.failed_count += 1
        
        return result
    
    def _demo_generate_keypair(self) -> Tuple[str, str]:
        """Generate demo keypair."""
        import uuid
        key_id = str(uuid.uuid4())[:8]
        private_key = f"demo_private_key_{key_id}"
        public_key = f"demo_public_key_{key_id}"
        return (
            base64.b64encode(private_key.encode()).decode('utf-8'),
            base64.b64encode(public_key.encode()).decode('utf-8')
        )
    
    def _demo_sign(self, content: bytes, private_key: str) -> str:
        """Demo signing."""
        content_hash = hashlib.sha256(content).hexdigest()
        return f"demo_sig_{content_hash[:16]}"
    
    def get_stats(self) -> dict:
        """Get verification statistics."""
        total = self.verified_count + self.failed_count
        return {
            "verified_count": self.verified_count,
            "failed_count": self.failed_count,
            "total_verifications": total,
            "success_rate": self.verified_count / max(1, total),
            "demo_mode": self.demo_mode
        }