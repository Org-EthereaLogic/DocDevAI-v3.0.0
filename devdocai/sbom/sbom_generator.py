"""
SBOM Generator - M010 Core Implementation
Generates Software Bill of Materials with digital signatures
Per SDD Section 5.5 specifications
"""

import json
import hashlib
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict

from .dependency_scanner import DependencyScanner
from .license_detector import LicenseDetector
from .vulnerability_scanner import VulnerabilityScanner
from .signer import Ed25519Signer


@dataclass
class Component:
    """Represents a software component in the SBOM"""
    name: str
    version: str
    purl: str  # Package URL
    license: Optional[str] = None
    copyright: Optional[str] = None
    supplier: Optional[str] = None
    author: Optional[str] = None
    file_analyzed: bool = False
    verification_code: Optional[str] = None
    checksums: Dict[str, str] = None
    dependencies: List[str] = None
    
    def __post_init__(self):
        if self.checksums is None:
            self.checksums = {}
        if self.dependencies is None:
            self.dependencies = []


@dataclass
class Vulnerability:
    """Represents a vulnerability finding"""
    id: str
    source: str
    severity: str
    description: str
    affected_components: List[str]
    cve: Optional[str] = None
    cvss_score: Optional[float] = None
    fix_available: bool = False
    fix_version: Optional[str] = None


class SBOMGenerator:
    """
    Main SBOM Generator class implementing SDD 5.5 specifications
    Supports SPDX 2.3 and CycloneDX 1.4 formats
    """
    
    def __init__(self):
        """Initialize SBOM Generator with required components"""
        self.scanner = DependencyScanner()
        self.license_detector = LicenseDetector()
        self.vulnerability_scanner = VulnerabilityScanner()
        self.signer = Ed25519Signer()
        
    def generate(self, project_path: str, format: str = 'spdx') -> Dict[str, Any]:
        """
        Generate SBOM with complete dependency analysis
        
        Args:
            project_path: Path to the project to analyze
            format: Output format ('spdx' or 'cyclonedx')
            
        Returns:
            SBOM document in requested format
        """
        project_path = Path(project_path)
        if not project_path.exists():
            raise ValueError(f"Project path does not exist: {project_path}")
            
        # Scan dependencies
        print(f"Scanning dependencies in {project_path}...")
        dependencies = self.scanner.scan_project(str(project_path))
        
        # Detect licenses
        print("Detecting licenses...")
        for dep in dependencies:
            dep.license = self.license_detector.detect(dep)
            
        # Scan for vulnerabilities
        print("Scanning for vulnerabilities...")
        vulnerabilities = self.vulnerability_scanner.scan(dependencies)
        
        # Build SBOM
        print(f"Building SBOM in {format} format...")
        sbom = self.build_sbom(
            format=format,
            dependencies=dependencies,
            vulnerabilities=vulnerabilities,
            project_path=str(project_path)
        )
        
        # Sign SBOM
        print("Signing SBOM with Ed25519...")
        signature = self.signer.sign(sbom)
        sbom['signature'] = signature
        
        return sbom
        
    def build_sbom(self, format: str, dependencies: List[Component], 
                   vulnerabilities: List[Vulnerability], project_path: str) -> Dict[str, Any]:
        """
        Build SBOM document in requested format
        
        Args:
            format: 'spdx' or 'cyclonedx'
            dependencies: List of discovered components
            vulnerabilities: List of vulnerabilities
            project_path: Path to the project
            
        Returns:
            SBOM document dictionary
        """
        if format.lower() == 'spdx':
            return self._build_spdx_sbom(dependencies, vulnerabilities, project_path)
        elif format.lower() == 'cyclonedx':
            return self._build_cyclonedx_sbom(dependencies, vulnerabilities, project_path)
        else:
            raise ValueError(f"Unsupported format: {format}")
            
    def _build_spdx_sbom(self, dependencies: List[Component], 
                         vulnerabilities: List[Vulnerability], 
                         project_path: str) -> Dict[str, Any]:
        """
        Build SPDX 2.3 compliant SBOM
        
        Args:
            dependencies: List of components
            vulnerabilities: List of vulnerabilities
            project_path: Project path
            
        Returns:
            SPDX 2.3 formatted SBOM
        """
        doc_namespace = f"https://devdocai.com/sbom/{uuid.uuid4()}"
        creation_time = datetime.now(timezone.utc).isoformat()
        
        sbom = {
            "spdxVersion": "SPDX-2.3",
            "dataLicense": "CC0-1.0",
            "SPDXID": "SPDXRef-DOCUMENT",
            "name": f"SBOM for {Path(project_path).name}",
            "documentNamespace": doc_namespace,
            "creationInfo": {
                "created": creation_time,
                "creators": ["Tool: DevDocAI-3.5.0"],
                "licenseListVersion": "3.20"
            },
            "packages": [],
            "relationships": [],
            "vulnerabilities": []
        }
        
        # Add main project package
        project_name = Path(project_path).name
        main_package = {
            "SPDXID": "SPDXRef-Package-Main",
            "name": project_name,
            "downloadLocation": "NOASSERTION",
            "filesAnalyzed": False,
            "supplier": "NOASSERTION",
            "originator": "NOASSERTION"
        }
        sbom["packages"].append(main_package)
        
        # Add dependencies as packages
        for idx, dep in enumerate(dependencies):
            package = {
                "SPDXID": f"SPDXRef-Package-{idx}",
                "name": dep.name,
                "versionInfo": dep.version,
                "downloadLocation": dep.purl if dep.purl else "NOASSERTION",
                "filesAnalyzed": dep.file_analyzed,
                "licenseConcluded": dep.license if dep.license else "NOASSERTION",
                "copyrightText": dep.copyright if dep.copyright else "NOASSERTION",
                "supplier": dep.supplier if dep.supplier else "NOASSERTION"
            }
            
            if dep.checksums:
                package["checksums"] = [
                    {"algorithm": algo.upper(), "checksumValue": value}
                    for algo, value in dep.checksums.items()
                ]
                
            sbom["packages"].append(package)
            
            # Add relationship
            sbom["relationships"].append({
                "spdxElementId": "SPDXRef-Package-Main",
                "relatedSpdxElement": f"SPDXRef-Package-{idx}",
                "relationshipType": "DEPENDS_ON"
            })
            
        # Add vulnerabilities
        for vuln in vulnerabilities:
            vuln_entry = {
                "id": vuln.id,
                "source": vuln.source,
                "severity": vuln.severity,
                "description": vuln.description,
                "affectedPackages": vuln.affected_components
            }
            if vuln.cve:
                vuln_entry["cve"] = vuln.cve
            if vuln.cvss_score:
                vuln_entry["cvssScore"] = vuln.cvss_score
            if vuln.fix_available:
                vuln_entry["fixAvailable"] = True
                if vuln.fix_version:
                    vuln_entry["fixVersion"] = vuln.fix_version
                    
            sbom["vulnerabilities"].append(vuln_entry)
            
        return sbom
        
    def _build_cyclonedx_sbom(self, dependencies: List[Component], 
                              vulnerabilities: List[Vulnerability],
                              project_path: str) -> Dict[str, Any]:
        """
        Build CycloneDX 1.4 compliant SBOM
        
        Args:
            dependencies: List of components
            vulnerabilities: List of vulnerabilities
            project_path: Project path
            
        Returns:
            CycloneDX 1.4 formatted SBOM
        """
        sbom = {
            "bomFormat": "CycloneDX",
            "specVersion": "1.4",
            "serialNumber": f"urn:uuid:{uuid.uuid4()}",
            "version": 1,
            "metadata": {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "tools": [
                    {
                        "vendor": "DevDocAI",
                        "name": "SBOM Generator",
                        "version": "3.5.0"
                    }
                ],
                "component": {
                    "type": "application",
                    "name": Path(project_path).name,
                    "version": "1.0.0"
                }
            },
            "components": [],
            "vulnerabilities": []
        }
        
        # Add components
        for dep in dependencies:
            component = {
                "type": "library",
                "bom-ref": f"pkg:{dep.purl}" if dep.purl else f"{dep.name}@{dep.version}",
                "name": dep.name,
                "version": dep.version,
                "purl": dep.purl
            }
            
            if dep.license:
                component["licenses"] = [{"license": {"id": dep.license}}]
                
            if dep.author:
                component["author"] = dep.author
                
            if dep.checksums:
                component["hashes"] = [
                    {"alg": algo.upper(), "content": value}
                    for algo, value in dep.checksums.items()
                ]
                
            sbom["components"].append(component)
            
        # Add vulnerabilities
        for vuln in vulnerabilities:
            vuln_entry = {
                "id": vuln.id,
                "source": {
                    "name": vuln.source
                },
                "ratings": [
                    {
                        "severity": vuln.severity
                    }
                ],
                "description": vuln.description,
                "affects": [
                    {"ref": comp} for comp in vuln.affected_components
                ]
            }
            
            if vuln.cvss_score:
                vuln_entry["ratings"][0]["score"] = vuln.cvss_score
                
            if vuln.cve:
                vuln_entry["references"] = [
                    {
                        "id": vuln.cve,
                        "source": {
                            "name": "NVD"
                        }
                    }
                ]
                
            sbom["vulnerabilities"].append(vuln_entry)
            
        return sbom
        
    def validate_sbom(self, sbom: Dict[str, Any]) -> bool:
        """
        Validate SBOM structure and completeness
        
        Args:
            sbom: SBOM document to validate
            
        Returns:
            True if valid, raises ValueError if invalid
        """
        if "spdxVersion" in sbom:
            return self._validate_spdx(sbom)
        elif "bomFormat" in sbom:
            return self._validate_cyclonedx(sbom)
        else:
            raise ValueError("Unknown SBOM format")
            
    def _validate_spdx(self, sbom: Dict[str, Any]) -> bool:
        """Validate SPDX format SBOM"""
        required_fields = ["spdxVersion", "dataLicense", "SPDXID", "name", 
                          "documentNamespace", "creationInfo"]
        for field in required_fields:
            if field not in sbom:
                raise ValueError(f"Missing required SPDX field: {field}")
                
        if sbom["spdxVersion"] != "SPDX-2.3":
            raise ValueError(f"Unsupported SPDX version: {sbom['spdxVersion']}")
            
        return True
        
    def _validate_cyclonedx(self, sbom: Dict[str, Any]) -> bool:
        """Validate CycloneDX format SBOM"""
        required_fields = ["bomFormat", "specVersion", "serialNumber", 
                          "version", "metadata"]
        for field in required_fields:
            if field not in sbom:
                raise ValueError(f"Missing required CycloneDX field: {field}")
                
        if sbom["specVersion"] != "1.4":
            raise ValueError(f"Unsupported CycloneDX version: {sbom['specVersion']}")
            
        return True
        
    def export_sbom(self, sbom: Dict[str, Any], output_path: str) -> None:
        """
        Export SBOM to file
        
        Args:
            sbom: SBOM document
            output_path: Path to write SBOM file
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(sbom, f, indent=2, ensure_ascii=False)
            
        print(f"SBOM exported to: {output_path}")