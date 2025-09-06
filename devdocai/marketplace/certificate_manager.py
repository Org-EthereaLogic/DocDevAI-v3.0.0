"""
Certificate Manager
Handles certificate validation and revocation checking for template signatures.
"""

import json
import logging
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Set

logger = logging.getLogger(__name__)


class CertificateManager:
    """
    Certificate management for template signature validation.
    
    Handles certificate revocation lists (CRL), validation,
    and trust chain verification.
    """
    
    def __init__(
        self,
        crl_update_interval: int = 3600,
        trusted_roots: Optional[List[str]] = None
    ):
        """
        Initialize the certificate manager.
        
        Args:
            crl_update_interval: Seconds between CRL updates
            trusted_roots: List of trusted root certificates
        """
        self.crl_update_interval = crl_update_interval
        self.last_crl_update = 0
        
        # Certificate Revocation List (in-memory for demo)
        self.revoked_certificates: Set[str] = set()
        
        # Trusted root certificates
        self.trusted_roots = set(trusted_roots or [
            "devdocai-root-ca-2024",
            "devdocai-community-ca-2024",
            "devdocai-enterprise-ca-2024"
        ])
        
        # Certificate cache
        self.certificate_cache: Dict[str, Dict] = {}
        
        # Statistics
        self.checks_performed = 0
        self.revoked_found = 0
        self.valid_found = 0
        
        # Load CRL on initialization
        self._update_crl()
        
        logger.info("Certificate manager initialized")
    
    def check_certificate(
        self,
        certificate_id: str,
        check_revocation: bool = True,
        check_expiry: bool = True
    ) -> bool:
        """
        Check if a certificate is valid.
        
        Args:
            certificate_id: Certificate identifier
            check_revocation: Check against CRL
            check_expiry: Check expiration date
            
        Returns:
            True if certificate is valid
        """
        self.checks_performed += 1
        
        # Update CRL if needed
        if check_revocation and self._should_update_crl():
            self._update_crl()
        
        # Check revocation
        if check_revocation and certificate_id in self.revoked_certificates:
            logger.warning(f"Certificate {certificate_id} is revoked")
            self.revoked_found += 1
            return False
        
        # Check expiry (demo implementation)
        if check_expiry:
            cert_info = self._get_certificate_info(certificate_id)
            if cert_info and not self._is_valid_period(cert_info):
                logger.warning(f"Certificate {certificate_id} is expired")
                return False
        
        # Check trust chain (demo implementation)
        if not self._verify_trust_chain(certificate_id):
            logger.warning(f"Certificate {certificate_id} has invalid trust chain")
            return False
        
        self.valid_found += 1
        logger.debug(f"Certificate {certificate_id} is valid")
        return True
    
    def add_to_revocation_list(
        self,
        certificate_id: str,
        reason: str = "unspecified"
    ) -> bool:
        """
        Add a certificate to the revocation list.
        
        Args:
            certificate_id: Certificate to revoke
            reason: Revocation reason
            
        Returns:
            True if added successfully
        """
        if certificate_id not in self.revoked_certificates:
            self.revoked_certificates.add(certificate_id)
            logger.info(f"Certificate {certificate_id} revoked: {reason}")
            return True
        return False
    
    def is_revoked(self, certificate_id: str) -> bool:
        """
        Check if a certificate is revoked.
        
        Args:
            certificate_id: Certificate to check
            
        Returns:
            True if revoked
        """
        return certificate_id in self.revoked_certificates
    
    def add_trusted_root(self, root_certificate_id: str) -> bool:
        """
        Add a trusted root certificate.
        
        Args:
            root_certificate_id: Root certificate to trust
            
        Returns:
            True if added
        """
        if root_certificate_id not in self.trusted_roots:
            self.trusted_roots.add(root_certificate_id)
            logger.info(f"Added trusted root: {root_certificate_id}")
            return True
        return False
    
    def get_trusted_roots(self) -> List[str]:
        """Get list of trusted root certificates."""
        return list(self.trusted_roots)
    
    def _should_update_crl(self) -> bool:
        """Check if CRL should be updated."""
        return (time.time() - self.last_crl_update) > self.crl_update_interval
    
    def _update_crl(self):
        """
        Update the Certificate Revocation List.
        
        In production, this would fetch from a CRL distribution point.
        For demo, we'll use a predefined list.
        """
        try:
            # Demo CRL - in production, fetch from network
            demo_revoked = [
                "compromised-cert-001",
                "expired-cert-2023",
                "untrusted-cert-xyz"
            ]
            
            self.revoked_certificates.update(demo_revoked)
            self.last_crl_update = time.time()
            
            logger.debug(f"CRL updated with {len(self.revoked_certificates)} revoked certificates")
            
        except Exception as e:
            logger.error(f"Failed to update CRL: {e}")
    
    def _get_certificate_info(self, certificate_id: str) -> Optional[Dict]:
        """
        Get certificate information.
        
        Args:
            certificate_id: Certificate identifier
            
        Returns:
            Certificate info or None
        """
        # Check cache
        if certificate_id in self.certificate_cache:
            return self.certificate_cache[certificate_id]
        
        # Demo certificate info
        # In production, this would parse actual certificate
        cert_info = {
            "id": certificate_id,
            "subject": f"CN=Template Author {certificate_id}",
            "issuer": "devdocai-community-ca-2024",
            "not_before": datetime.now() - timedelta(days=365),
            "not_after": datetime.now() + timedelta(days=365),
            "public_key": f"demo_public_key_{certificate_id}"
        }
        
        # Cache the info
        self.certificate_cache[certificate_id] = cert_info
        
        return cert_info
    
    def _is_valid_period(self, cert_info: Dict) -> bool:
        """
        Check if certificate is within valid period.
        
        Args:
            cert_info: Certificate information
            
        Returns:
            True if within valid period
        """
        now = datetime.now()
        not_before = cert_info.get("not_before")
        not_after = cert_info.get("not_after")
        
        if isinstance(not_before, datetime) and isinstance(not_after, datetime):
            return not_before <= now <= not_after
        
        # Default to valid for demo
        return True
    
    def _verify_trust_chain(self, certificate_id: str) -> bool:
        """
        Verify certificate trust chain.
        
        Args:
            certificate_id: Certificate to verify
            
        Returns:
            True if trust chain is valid
        """
        cert_info = self._get_certificate_info(certificate_id)
        if not cert_info:
            return False
        
        issuer = cert_info.get("issuer")
        
        # Check if issuer is a trusted root
        if issuer in self.trusted_roots:
            return True
        
        # For demo, check if certificate ID contains trusted keywords
        trusted_keywords = ["devdocai", "official", "verified"]
        if any(keyword in certificate_id.lower() for keyword in trusted_keywords):
            return True
        
        return False
    
    def get_stats(self) -> Dict:
        """Get certificate manager statistics."""
        return {
            "checks_performed": self.checks_performed,
            "revoked_found": self.revoked_found,
            "valid_found": self.valid_found,
            "revoked_count": len(self.revoked_certificates),
            "trusted_roots": len(self.trusted_roots),
            "cached_certificates": len(self.certificate_cache),
            "last_crl_update": datetime.fromtimestamp(self.last_crl_update).isoformat()
            if self.last_crl_update > 0 else "never"
        }
    
    def clear_cache(self):
        """Clear certificate cache."""
        self.certificate_cache.clear()
        logger.info("Certificate cache cleared")
    
    def __repr__(self) -> str:
        """String representation."""
        return (
            f"CertificateManager("
            f"revoked={len(self.revoked_certificates)}, "
            f"trusted_roots={len(self.trusted_roots)}, "
            f"checks={self.checks_performed})"
        )