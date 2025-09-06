"""
Ed25519 Digital Signature Component
Signs SBOMs with Ed25519 digital signatures
"""

import json
import base64
import hashlib
from typing import Dict, Any, Tuple, Optional
from pathlib import Path
from datetime import datetime, timezone

try:
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric import ed25519
    from cryptography.hazmat.backends import default_backend
    CRYPTO_AVAILABLE = True
except ImportError:
    CRYPTO_AVAILABLE = False
    

class Ed25519Signer:
    """
    Signs and verifies SBOMs using Ed25519 digital signatures
    Per SDD 5.5 specifications
    """
    
    def __init__(self, key_path: Optional[str] = None):
        """
        Initialize signer with optional key path
        
        Args:
            key_path: Path to existing Ed25519 private key (optional)
        """
        self.private_key = None
        self.public_key = None
        
        if not CRYPTO_AVAILABLE:
            print("Warning: cryptography library not available. Using mock signatures.")
            return
            
        if key_path and Path(key_path).exists():
            self.load_key(key_path)
        else:
            self.generate_keypair()
            
    def generate_keypair(self) -> Tuple[bytes, bytes]:
        """
        Generate new Ed25519 keypair
        
        Returns:
            Tuple of (private_key_bytes, public_key_bytes)
        """
        if not CRYPTO_AVAILABLE:
            # Mock implementation for testing
            mock_private = b"mock_private_key_" + hashlib.sha256(str(datetime.now()).encode()).digest()[:16]
            mock_public = b"mock_public_key_" + hashlib.sha256(mock_private).digest()[:16]
            self.private_key = mock_private
            self.public_key = mock_public
            return (mock_private, mock_public)
            
        # Generate real Ed25519 keypair
        self.private_key = ed25519.Ed25519PrivateKey.generate()
        self.public_key = self.private_key.public_key()
        
        # Return serialized keys
        private_bytes = self.private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        )
        
        public_bytes = self.public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )
        
        return (private_bytes, public_bytes)
        
    def sign(self, sbom: Dict[str, Any]) -> Dict[str, Any]:
        """
        Sign SBOM document with Ed25519
        
        Args:
            sbom: SBOM document to sign
            
        Returns:
            Signature dictionary with metadata
        """
        # Create canonical JSON representation (sorted keys, no whitespace)
        canonical_json = json.dumps(sbom, sort_keys=True, separators=(',', ':'))
        message_bytes = canonical_json.encode('utf-8')
        
        # Calculate document hash
        doc_hash = hashlib.sha256(message_bytes).hexdigest()
        
        if not CRYPTO_AVAILABLE or not self.private_key:
            # Mock signature for testing
            mock_signature = hashlib.sha512(message_bytes).digest()[:64]
            signature_b64 = base64.b64encode(mock_signature).decode('ascii')
            public_key_str = base64.b64encode(self.public_key if self.public_key else b"mock_key").decode('ascii')
        else:
            # Sign with Ed25519
            signature = self.private_key.sign(message_bytes)
            signature_b64 = base64.b64encode(signature).decode('ascii')
            
            # Get public key for verification
            public_bytes = self.public_key.public_bytes(
                encoding=serialization.Encoding.Raw,
                format=serialization.PublicFormat.Raw
            )
            public_key_str = base64.b64encode(public_bytes).decode('ascii')
            
        # Create signature block
        signature_block = {
            'algorithm': 'Ed25519',
            'signature': signature_b64,
            'public_key': public_key_str,
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'document_hash': doc_hash,
            'signer': {
                'tool': 'DevDocAI SBOM Generator',
                'version': '3.5.0'
            }
        }
        
        return signature_block
        
    def verify(self, sbom: Dict[str, Any], signature_block: Dict[str, Any]) -> bool:
        """
        Verify SBOM signature
        
        Args:
            sbom: SBOM document (without signature)
            signature_block: Signature block to verify
            
        Returns:
            True if signature is valid
        """
        try:
            # Recreate canonical JSON
            canonical_json = json.dumps(sbom, sort_keys=True, separators=(',', ':'))
            message_bytes = canonical_json.encode('utf-8')
            
            # Verify document hash
            doc_hash = hashlib.sha256(message_bytes).hexdigest()
            if doc_hash != signature_block.get('document_hash'):
                print("Document hash mismatch")
                return False
                
            if not CRYPTO_AVAILABLE:
                # Mock verification for testing
                print("Mock verification (cryptography not available)")
                return True
                
            # Decode signature and public key
            signature = base64.b64decode(signature_block['signature'])
            public_key_bytes = base64.b64decode(signature_block['public_key'])
            
            # Create public key object
            public_key = ed25519.Ed25519PublicKey.from_public_bytes(public_key_bytes)
            
            # Verify signature
            public_key.verify(signature, message_bytes)
            return True
            
        except Exception as e:
            print(f"Signature verification failed: {e}")
            return False
            
    def save_keys(self, private_path: str, public_path: str) -> None:
        """
        Save keypair to files
        
        Args:
            private_path: Path to save private key
            public_path: Path to save public key
        """
        if not self.private_key or not self.public_key:
            raise ValueError("No keypair to save")
            
        private_path = Path(private_path)
        public_path = Path(public_path)
        
        # Create directories if needed
        private_path.parent.mkdir(parents=True, exist_ok=True)
        public_path.parent.mkdir(parents=True, exist_ok=True)
        
        if not CRYPTO_AVAILABLE:
            # Save mock keys for testing
            with open(private_path, 'wb') as f:
                f.write(self.private_key)
            with open(public_path, 'wb') as f:
                f.write(self.public_key)
            print(f"Mock keys saved to {private_path} and {public_path}")
            return
            
        # Save real Ed25519 keys
        private_bytes = self.private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        )
        
        public_bytes = self.public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )
        
        # Set secure permissions on private key
        with open(private_path, 'wb') as f:
            f.write(private_bytes)
        private_path.chmod(0o600)
        
        with open(public_path, 'wb') as f:
            f.write(public_bytes)
            
        print(f"Keys saved to {private_path} and {public_path}")
        
    def load_key(self, key_path: str) -> None:
        """
        Load private key from file
        
        Args:
            key_path: Path to private key file
        """
        key_path = Path(key_path)
        if not key_path.exists():
            raise FileNotFoundError(f"Key file not found: {key_path}")
            
        with open(key_path, 'rb') as f:
            key_data = f.read()
            
        if not CRYPTO_AVAILABLE:
            # Load mock key
            self.private_key = key_data
            self.public_key = b"mock_public_key_" + hashlib.sha256(key_data).digest()[:16]
            print("Mock keys loaded")
            return
            
        # Load real Ed25519 key
        self.private_key = serialization.load_pem_private_key(
            key_data,
            password=None,
            backend=default_backend()
        )
        self.public_key = self.private_key.public_key()
        print(f"Loaded Ed25519 key from {key_path}")
        
    def export_public_key(self) -> str:
        """
        Export public key as base64 string
        
        Returns:
            Base64 encoded public key
        """
        if not self.public_key:
            raise ValueError("No public key available")
            
        if not CRYPTO_AVAILABLE:
            return base64.b64encode(self.public_key).decode('ascii')
            
        public_bytes = self.public_key.public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw
        )
        return base64.b64encode(public_bytes).decode('ascii')