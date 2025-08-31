"""
SBOM Digital Signature module.

Provides Ed25519 digital signatures for SBOM documents to ensure
integrity and authenticity.
"""

import logging
import base64
import hashlib
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, Any, Optional, Union, Tuple
from pathlib import Path

try:
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import ed25519
    from cryptography.exceptions import InvalidSignature
    CRYPTOGRAPHY_AVAILABLE = True
except ImportError:
    CRYPTOGRAPHY_AVAILABLE = False
    ed25519 = None

logger = logging.getLogger(__name__)


class SignatureAlgorithm(str, Enum):
    """Supported signature algorithms."""
    ED25519 = "ed25519"
    RSA_PSS = "rsa-pss"  # Future support
    ECDSA = "ecdsa"      # Future support


class SBOMSigner:
    """
    Digital signature provider for SBOM documents.
    
    Uses Ed25519 signatures by default for security and performance.
    """
    
    def __init__(self, algorithm: SignatureAlgorithm = SignatureAlgorithm.ED25519,
                 key_file: Optional[Path] = None):
        """
        Initialize SBOM signer.
        
        Args:
            algorithm: Signature algorithm to use
            key_file: Optional path to private key file
        """
        if not CRYPTOGRAPHY_AVAILABLE:
            raise ImportError("cryptography library required for SBOM signing")
        
        self.algorithm = algorithm
        self.key_file = key_file or Path.home() / '.devdocai' / 'sbom_signing_key.pem'
        
        self._private_key = None
        self._public_key = None
        
        if algorithm != SignatureAlgorithm.ED25519:
            raise NotImplementedError(f"Algorithm {algorithm} not yet supported")
    
    def generate_key_pair(self, save_to_file: bool = True) -> Tuple[bytes, bytes]:
        """
        Generate new Ed25519 key pair.
        
        Args:
            save_to_file: Whether to save private key to file
            
        Returns:
            Tuple of (private_key_bytes, public_key_bytes)
        """
        if not CRYPTOGRAPHY_AVAILABLE:
            raise ImportError("cryptography library required")
        
        # Generate private key
        private_key = ed25519.Ed25519PrivateKey.generate()
        public_key = private_key.public_key()
        
        # Serialize keys
        private_bytes = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        )
        
        public_bytes = public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )
        
        # Save private key if requested
        if save_to_file:
            self.key_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.key_file, 'wb') as f:
                f.write(private_bytes)
            
            # Set restrictive permissions on private key
            self.key_file.chmod(0o600)
            
            logger.info(f"Ed25519 key pair generated and saved to {self.key_file}")
        
        self._private_key = private_key
        self._public_key = public_key
        
        return private_bytes, public_bytes
    
    def load_private_key(self, key_data: Optional[Union[str, bytes, Path]] = None) -> bool:
        """
        Load private key from file or data.
        
        Args:
            key_data: Key data, file path, or None to use default file
            
        Returns:
            True if successful
        """
        try:
            if key_data is None:
                if not self.key_file.exists():
                    logger.info("No signing key found, generating new key pair")
                    self.generate_key_pair()
                    return True
                key_data = self.key_file
            
            if isinstance(key_data, (str, Path)):
                with open(key_data, 'rb') as f:
                    key_bytes = f.read()
            else:
                key_bytes = key_data
            
            self._private_key = serialization.load_pem_private_key(
                key_bytes, 
                password=None
            )
            self._public_key = self._private_key.public_key()
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to load private key: {e}")
            return False
    
    def sign(self, data: Union[str, bytes]) -> Dict[str, Any]:
        """
        Sign data and return signature information.
        
        Args:
            data: Data to sign
            
        Returns:
            Signature information dictionary
        """
        if not self._private_key:
            if not self.load_private_key():
                raise RuntimeError("No signing key available")
        
        # Convert to bytes if necessary
        if isinstance(data, str):
            data_bytes = data.encode('utf-8')
        else:
            data_bytes = data
        
        # Calculate content hash
        content_hash = hashlib.sha256(data_bytes).hexdigest()
        
        # Generate signature
        signature_bytes = self._private_key.sign(data_bytes)
        signature_b64 = base64.b64encode(signature_bytes).decode('utf-8')
        
        # Get public key for verification
        public_key_bytes = self._public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )
        public_key_b64 = base64.b64encode(public_key_bytes).decode('utf-8')
        
        return {
            'algorithm': self.algorithm.value,
            'signature': signature_b64,
            'public_key': public_key_b64,
            'content_hash': content_hash,
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'signer_info': {
                'tool': 'DevDocAI-M010',
                'version': '3.0.0'
            }
        }
    
    def verify(self, data: Union[str, bytes], signature_info: Dict[str, Any]) -> bool:
        """
        Verify signature.
        
        Args:
            data: Original data that was signed
            signature_info: Signature information from sign()
            
        Returns:
            True if signature is valid
        """
        try:
            # Convert to bytes if necessary
            if isinstance(data, str):
                data_bytes = data.encode('utf-8')
            else:
                data_bytes = data
            
            # Verify content hash
            content_hash = hashlib.sha256(data_bytes).hexdigest()
            if content_hash != signature_info.get('content_hash'):
                logger.warning("Content hash mismatch in signature verification")
                return False
            
            # Load public key from signature info
            public_key_b64 = signature_info.get('public_key')
            if not public_key_b64:
                raise ValueError("No public key in signature info")
            
            public_key_bytes = base64.b64decode(public_key_b64)
            public_key = serialization.load_pem_public_key(public_key_bytes)
            
            # Decode signature
            signature_b64 = signature_info.get('signature')
            if not signature_b64:
                raise ValueError("No signature in signature info")
            
            signature_bytes = base64.b64decode(signature_b64)
            
            # Verify signature
            public_key.verify(signature_bytes, data_bytes)
            
            logger.info("SBOM signature verification successful")
            return True
            
        except InvalidSignature:
            logger.warning("SBOM signature verification failed - invalid signature")
            return False
        except Exception as e:
            logger.error(f"SBOM signature verification error: {e}")
            return False
    
    def get_public_key_info(self) -> Optional[Dict[str, Any]]:
        """Get public key information for sharing."""
        if not self._public_key:
            return None
        
        public_key_bytes = self._public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )
        
        return {
            'algorithm': self.algorithm.value,
            'public_key': base64.b64encode(public_key_bytes).decode('utf-8'),
            'key_id': hashlib.sha256(public_key_bytes).hexdigest()[:16]
        }


class SBOMSignatureValidator:
    """
    Utility class for validating SBOM signatures.
    """
    
    @staticmethod
    def validate_signature_format(signature_info: Dict[str, Any]) -> bool:
        """
        Validate signature information format.
        
        Args:
            signature_info: Signature information dictionary
            
        Returns:
            True if format is valid
        """
        required_fields = ['algorithm', 'signature', 'public_key', 'content_hash', 'timestamp']
        
        for field in required_fields:
            if field not in signature_info:
                logger.error(f"Missing required signature field: {field}")
                return False
        
        # Validate algorithm
        if signature_info['algorithm'] not in [alg.value for alg in SignatureAlgorithm]:
            logger.error(f"Unsupported signature algorithm: {signature_info['algorithm']}")
            return False
        
        # Validate base64 encoding
        try:
            base64.b64decode(signature_info['signature'])
            base64.b64decode(signature_info['public_key'])
        except Exception:
            logger.error("Invalid base64 encoding in signature")
            return False
        
        return True
    
    @staticmethod
    def verify_sbom_signature(sbom_content: Union[str, Dict[str, Any]], 
                            signature_info: Dict[str, Any]) -> bool:
        """
        Verify SBOM signature.
        
        Args:
            sbom_content: SBOM content that was signed
            signature_info: Signature information
            
        Returns:
            True if signature is valid
        """
        if not SBOMSignatureValidator.validate_signature_format(signature_info):
            return False
        
        algorithm = SignatureAlgorithm(signature_info['algorithm'])
        signer = SBOMSigner(algorithm=algorithm)
        
        return signer.verify(sbom_content, signature_info)


# Convenience functions
def sign_sbom(sbom_content: Union[str, Dict[str, Any]], 
             key_file: Optional[Path] = None) -> Dict[str, Any]:
    """
    Sign SBOM content with default settings.
    
    Args:
        sbom_content: SBOM content to sign
        key_file: Optional private key file
        
    Returns:
        Signature information
    """
    signer = SBOMSigner(key_file=key_file)
    
    if isinstance(sbom_content, dict):
        import json
        content_str = json.dumps(sbom_content, sort_keys=True)
    else:
        content_str = sbom_content
    
    return signer.sign(content_str)


def verify_sbom_signature(sbom_content: Union[str, Dict[str, Any]], 
                         signature_info: Dict[str, Any]) -> bool:
    """
    Verify SBOM signature with default settings.
    
    Args:
        sbom_content: SBOM content
        signature_info: Signature information
        
    Returns:
        True if valid
    """
    return SBOMSignatureValidator.verify_sbom_signature(sbom_content, signature_info)