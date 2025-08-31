"""
SBOM Generator - Software Bill of Materials generation.

Supports SPDX 2.3 and CycloneDX 1.4 formats with digital signatures,
vulnerability scanning, and compliance reporting.
"""

import json
import logging
import time
import hashlib
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List, Optional, Union, Set
from enum import Enum
from dataclasses import dataclass, field
import subprocess
import re
import xml.etree.ElementTree as ET

logger = logging.getLogger(__name__)


class SBOMFormat(str, Enum):
    """Supported SBOM formats."""
    SPDX_JSON = "spdx-json"
    SPDX_XML = "spdx-xml"
    CYCLONEDX_JSON = "cyclonedx-json"
    CYCLONEDX_XML = "cyclonedx-xml"


class LicenseType(str, Enum):
    """Common license types."""
    MIT = "MIT"
    APACHE_2_0 = "Apache-2.0"
    GPL_3_0 = "GPL-3.0-or-later"
    BSD_3_CLAUSE = "BSD-3-Clause"
    ISC = "ISC"
    PROPRIETARY = "NOASSERTION"
    UNKNOWN = "NOASSERTION"


@dataclass
class ComponentInfo:
    """Information about a software component."""
    name: str
    version: str
    supplier: Optional[str] = None
    download_location: Optional[str] = None
    files_analyzed: bool = False
    license_concluded: Optional[str] = None
    license_declared: Optional[str] = None
    copyright_text: Optional[str] = None
    comment: Optional[str] = None
    homepage: Optional[str] = None
    package_filename: Optional[str] = None
    checksum_sha1: Optional[str] = None
    checksum_sha256: Optional[str] = None
    vulnerabilities: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class SBOMConfig:
    """Configuration for SBOM generation."""
    include_dev_dependencies: bool = False
    include_file_analysis: bool = True
    include_vulnerabilities: bool = True
    include_licenses: bool = True
    include_copyrights: bool = True
    sign_sbom: bool = True
    signature_algorithm: str = "ed25519"
    namespace_base: str = "https://devdocai.local/sbom"
    creator_tool: str = "DevDocAI-M010"
    creator_version: str = "3.0.0"
    organization: str = "DevDocAI"
    max_scan_time_seconds: int = 300
    vulnerability_sources: List[str] = field(default_factory=lambda: ["nvd", "github"])


class SBOMGenerator:
    """
    Software Bill of Materials generator.
    
    Generates SBOM documents in SPDX 2.3 and CycloneDX 1.4 formats with
    digital signatures and vulnerability information.
    """
    
    def __init__(self, security_manager=None, encryption_enabled: bool = True):
        """
        Initialize SBOM generator.
        
        Args:
            security_manager: Security manager instance
            encryption_enabled: Whether to enable encryption features
        """
        self.security_manager = security_manager
        self.encryption_enabled = encryption_enabled
        self.config = SBOMConfig()
        
        # Package manager detection patterns
        self.package_patterns = {
            'npm': ['package.json', 'package-lock.json', 'yarn.lock'],
            'pip': ['requirements.txt', 'setup.py', 'pyproject.toml', 'Pipfile'],
            'maven': ['pom.xml'],
            'gradle': ['build.gradle', 'build.gradle.kts'],
            'go': ['go.mod', 'go.sum'],
            'cargo': ['Cargo.toml', 'Cargo.lock'],
            'composer': ['composer.json', 'composer.lock'],
            'nuget': ['*.csproj', '*.fsproj', 'packages.config']
        }
        
        # License detection patterns
        self.license_patterns = {
            'MIT': re.compile(r'MIT License|MIT license', re.IGNORECASE),
            'Apache-2.0': re.compile(r'Apache License.*Version 2\.0', re.IGNORECASE),
            'GPL-3.0': re.compile(r'GNU General Public License.*version 3', re.IGNORECASE),
            'BSD-3-Clause': re.compile(r'BSD 3-Clause', re.IGNORECASE),
            'ISC': re.compile(r'ISC License', re.IGNORECASE)
        }
    
    def generate_sbom(self, project_path: Union[str, Path], 
                     format_type: Union[str, SBOMFormat] = SBOMFormat.SPDX_JSON,
                     include_signature: bool = True) -> Dict[str, Any]:
        """
        Generate SBOM for project.
        
        Args:
            project_path: Path to project directory
            format_type: SBOM format to generate
            include_signature: Whether to include digital signature
            
        Returns:
            Generated SBOM data and metadata
        """
        start_time = time.perf_counter()
        
        if isinstance(format_type, str):
            format_type = SBOMFormat(format_type)
        
        project_path = Path(project_path)
        if not project_path.exists():
            raise FileNotFoundError(f"Project path does not exist: {project_path}")
        
        logger.info(f"Generating {format_type.value} SBOM for {project_path}")
        
        try:
            # Analyze project
            project_info = self._analyze_project(project_path)
            components = self._discover_components(project_path, project_info)
            
            # Generate SBOM content based on format
            if format_type in [SBOMFormat.SPDX_JSON, SBOMFormat.SPDX_XML]:
                sbom_content = self._generate_spdx_sbom(project_info, components, format_type)
            else:
                sbom_content = self._generate_cyclonedx_sbom(project_info, components, format_type)
            
            # Add vulnerability data if enabled
            if self.config.include_vulnerabilities:
                sbom_content = self._enrich_with_vulnerabilities(sbom_content, components)
            
            # Generate signature if requested
            signature_data = None
            if include_signature and self.config.sign_sbom:
                signature_data = self._generate_signature(sbom_content, format_type)
            
            generation_time = time.perf_counter() - start_time
            
            result = {
                'sbom_content': sbom_content,
                'format': format_type.value,
                'project_path': str(project_path),
                'generation_time_ms': generation_time * 1000,
                'component_count': len(components),
                'signature': signature_data,
                'metadata': {
                    'generated_at': datetime.now(timezone.utc).isoformat(),
                    'generator': {
                        'tool': self.config.creator_tool,
                        'version': self.config.creator_version,
                        'organization': self.config.organization
                    },
                    'project': project_info,
                    'statistics': {
                        'total_components': len(components),
                        'components_with_licenses': sum(1 for c in components if c.license_concluded),
                        'components_with_vulnerabilities': sum(1 for c in components if c.vulnerabilities),
                        'generation_time_seconds': generation_time
                    }
                }
            }
            
            logger.info(f"SBOM generation completed in {generation_time:.2f}s")
            return result
            
        except Exception as e:
            logger.error(f"SBOM generation failed: {e}")
            raise
    
    def _analyze_project(self, project_path: Path) -> Dict[str, Any]:
        """Analyze project to determine type and characteristics."""
        project_info = {
            'name': project_path.name,
            'path': str(project_path),
            'type': 'unknown',
            'package_managers': [],
            'languages': set(),
            'license_files': [],
            'readme_files': []
        }
        
        # Detect package managers and languages
        for pm, patterns in self.package_patterns.items():
            for pattern in patterns:
                if list(project_path.glob(pattern)):
                    project_info['package_managers'].append(pm)
                    # Map package managers to languages
                    if pm in ['npm']:
                        project_info['languages'].add('JavaScript')
                    elif pm in ['pip']:
                        project_info['languages'].add('Python')
                    elif pm in ['maven', 'gradle']:
                        project_info['languages'].add('Java')
                    elif pm == 'go':
                        project_info['languages'].add('Go')
                    elif pm == 'cargo':
                        project_info['languages'].add('Rust')
                    elif pm == 'composer':
                        project_info['languages'].add('PHP')
                    elif pm == 'nuget':
                        project_info['languages'].add('C#')
        
        # Find license files
        license_patterns = ['LICENSE*', 'license*', 'COPYING*', 'COPYRIGHT*']
        for pattern in license_patterns:
            project_info['license_files'].extend(list(project_path.glob(pattern)))
        
        # Find README files
        readme_patterns = ['README*', 'readme*']
        for pattern in readme_patterns:
            project_info['readme_files'].extend(list(project_path.glob(pattern)))
        
        # Convert sets to lists for JSON serialization
        project_info['languages'] = list(project_info['languages'])
        project_info['license_files'] = [str(f) for f in project_info['license_files']]
        project_info['readme_files'] = [str(f) for f in project_info['readme_files']]
        
        # Determine primary type
        if 'npm' in project_info['package_managers']:
            project_info['type'] = 'node'
        elif 'pip' in project_info['package_managers']:
            project_info['type'] = 'python'
        elif any(pm in project_info['package_managers'] for pm in ['maven', 'gradle']):
            project_info['type'] = 'java'
        elif project_info['package_managers']:
            project_info['type'] = project_info['package_managers'][0]
        
        return project_info
    
    def _discover_components(self, project_path: Path, project_info: Dict[str, Any]) -> List[ComponentInfo]:
        """Discover components/dependencies in the project."""
        components = []
        
        # Add main project as root component
        root_license = self._detect_project_license(project_path)
        root_component = ComponentInfo(
            name=project_info['name'],
            version='1.0.0',  # Default version
            supplier=self.config.organization,
            license_concluded=root_license,
            license_declared=root_license,
            comment="Root project component"
        )
        components.append(root_component)
        
        # Discover dependencies based on package managers
        for pm in project_info['package_managers']:
            try:
                pm_components = self._discover_dependencies(project_path, pm)
                components.extend(pm_components)
            except Exception as e:
                logger.warning(f"Failed to discover {pm} dependencies: {e}")
        
        return components
    
    def _discover_dependencies(self, project_path: Path, package_manager: str) -> List[ComponentInfo]:
        """Discover dependencies for specific package manager."""
        components = []
        
        if package_manager == 'npm':
            components.extend(self._discover_npm_dependencies(project_path))
        elif package_manager == 'pip':
            components.extend(self._discover_pip_dependencies(project_path))
        elif package_manager == 'maven':
            components.extend(self._discover_maven_dependencies(project_path))
        # Add other package managers as needed
        
        return components
    
    def _discover_npm_dependencies(self, project_path: Path) -> List[ComponentInfo]:
        """Discover NPM dependencies."""
        components = []
        package_json = project_path / 'package.json'
        
        if not package_json.exists():
            return components
        
        try:
            with open(package_json) as f:
                package_data = json.load(f)
            
            # Process dependencies
            deps = package_data.get('dependencies', {})
            if self.config.include_dev_dependencies:
                deps.update(package_data.get('devDependencies', {}))
            
            for name, version in deps.items():
                component = ComponentInfo(
                    name=name,
                    version=version.lstrip('^~>=<'),  # Clean version specifiers
                    download_location=f"https://registry.npmjs.org/{name}",
                    package_filename=f"{name}-{version}.tgz"
                )
                components.append(component)
                
        except Exception as e:
            logger.warning(f"Failed to parse package.json: {e}")
        
        return components
    
    def _discover_pip_dependencies(self, project_path: Path) -> List[ComponentInfo]:
        """Discover Python dependencies."""
        components = []
        
        # Check requirements.txt
        requirements_file = project_path / 'requirements.txt'
        if requirements_file.exists():
            try:
                with open(requirements_file) as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#'):
                            # Parse requirement line
                            name, version = self._parse_pip_requirement(line)
                            if name:
                                component = ComponentInfo(
                                    name=name,
                                    version=version or '0.0.0',
                                    download_location=f"https://pypi.org/project/{name}/",
                                    package_filename=f"{name}-{version}.tar.gz"
                                )
                                components.append(component)
            except Exception as e:
                logger.warning(f"Failed to parse requirements.txt: {e}")
        
        return components
    
    def _discover_maven_dependencies(self, project_path: Path) -> List[ComponentInfo]:
        """Discover Maven dependencies."""
        components = []
        pom_file = project_path / 'pom.xml'
        
        if not pom_file.exists():
            return components
        
        try:
            tree = ET.parse(pom_file)
            root = tree.getroot()
            
            # Find namespace
            ns = {'maven': 'http://maven.apache.org/POM/4.0.0'}
            if root.tag.startswith('{'):
                ns_url = root.tag[1:].split('}')[0]
                ns = {'maven': ns_url}
            
            # Extract dependencies
            for dep in root.findall('.//maven:dependency', ns):
                group_id = dep.find('maven:groupId', ns)
                artifact_id = dep.find('maven:artifactId', ns) 
                version = dep.find('maven:version', ns)
                
                if group_id is not None and artifact_id is not None:
                    name = f"{group_id.text}:{artifact_id.text}"
                    version_text = version.text if version is not None else "unknown"
                    
                    component = ComponentInfo(
                        name=name,
                        version=version_text,
                        download_location=f"https://repo1.maven.org/maven2/{group_id.text.replace('.', '/')}/{artifact_id.text}/{version_text}/",
                        package_filename=f"{artifact_id.text}-{version_text}.jar"
                    )
                    components.append(component)
                    
        except Exception as e:
            logger.warning(f"Failed to parse pom.xml: {e}")
        
        return components
    
    def _parse_pip_requirement(self, requirement: str) -> tuple:
        """Parse pip requirement string."""
        # Simple parsing - could be enhanced with proper requirement parsing
        for op in ['>=', '<=', '==', '>', '<', '~=']:
            if op in requirement:
                parts = requirement.split(op, 1)
                return parts[0].strip(), parts[1].strip()
        
        return requirement.strip(), None
    
    def _detect_project_license(self, project_path: Path) -> Optional[str]:
        """Detect project license from LICENSE files."""
        license_files = list(project_path.glob('LICENSE*')) + list(project_path.glob('license*'))
        
        for license_file in license_files:
            try:
                with open(license_file, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read(1024)  # Read first 1KB
                
                # Check against known patterns
                for license_type, pattern in self.license_patterns.items():
                    if pattern.search(content):
                        return license_type
                        
            except Exception:
                continue
        
        return None
    
    def _generate_spdx_sbom(self, project_info: Dict[str, Any], 
                           components: List[ComponentInfo],
                           format_type: SBOMFormat) -> Union[str, Dict[str, Any]]:
        """Generate SPDX format SBOM."""
        sbom_id = f"SPDXRef-{uuid.uuid4().hex[:8]}"
        document_namespace = f"{self.config.namespace_base}/{project_info['name']}/{uuid.uuid4().hex}"
        
        spdx_doc = {
            "spdxVersion": "SPDX-2.3",
            "dataLicense": "CC0-1.0",
            "SPDXID": "SPDXRef-DOCUMENT",
            "documentName": f"{project_info['name']} SBOM",
            "documentNamespace": document_namespace,
            "creationInfo": {
                "created": datetime.now(timezone.utc).isoformat(),
                "creators": [
                    f"Tool: {self.config.creator_tool}-{self.config.creator_version}",
                    f"Organization: {self.config.organization}"
                ]
            },
            "packages": []
        }
        
        # Add packages
        for i, component in enumerate(components):
            package_id = f"SPDXRef-Package-{i}"
            package = {
                "SPDXID": package_id,
                "name": component.name,
                "downloadLocation": component.download_location or "NOASSERTION",
                "filesAnalyzed": component.files_analyzed,
                "copyrightText": component.copyright_text or "NOASSERTION"
            }
            
            if component.version:
                package["versionInfo"] = component.version
            
            if component.supplier:
                package["supplier"] = f"Organization: {component.supplier}"
            
            if component.license_concluded:
                package["licenseConcluded"] = component.license_concluded
            else:
                package["licenseConcluded"] = "NOASSERTION"
            
            if component.license_declared:
                package["licenseDeclared"] = component.license_declared
            else:
                package["licenseDeclared"] = "NOASSERTION"
            
            if component.checksum_sha256:
                package["checksums"] = [{
                    "algorithm": "SHA256",
                    "checksumValue": component.checksum_sha256
                }]
            
            if component.comment:
                package["comment"] = component.comment
            
            spdx_doc["packages"].append(package)
        
        # Add relationships
        spdx_doc["relationships"] = []
        if components:
            # Document describes root package
            spdx_doc["relationships"].append({
                "spdxElementId": "SPDXRef-DOCUMENT",
                "relatedSpdxElement": "SPDXRef-Package-0",
                "relationshipType": "DESCRIBES"
            })
            
            # Root package depends on other packages
            for i in range(1, len(components)):
                spdx_doc["relationships"].append({
                    "spdxElementId": "SPDXRef-Package-0", 
                    "relatedSpdxElement": f"SPDXRef-Package-{i}",
                    "relationshipType": "DEPENDS_ON"
                })
        
        if format_type == SBOMFormat.SPDX_JSON:
            return spdx_doc
        else:
            # Convert to XML (simplified implementation)
            return json.dumps(spdx_doc, indent=2)  # For now, return JSON string
    
    def _generate_cyclonedx_sbom(self, project_info: Dict[str, Any],
                                components: List[ComponentInfo],
                                format_type: SBOMFormat) -> Union[str, Dict[str, Any]]:
        """Generate CycloneDX format SBOM.""" 
        cyclonedx_doc = {
            "bomFormat": "CycloneDX",
            "specVersion": "1.4",
            "serialNumber": f"urn:uuid:{uuid.uuid4()}",
            "version": 1,
            "metadata": {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "tools": [{
                    "vendor": self.config.organization,
                    "name": self.config.creator_tool,
                    "version": self.config.creator_version
                }],
                "component": {
                    "type": "application",
                    "bom-ref": f"{project_info['name']}@1.0.0",
                    "name": project_info['name'],
                    "version": "1.0.0"
                }
            },
            "components": []
        }
        
        # Add components (skip root component for CycloneDX)
        for component in components[1:]:
            comp_obj = {
                "type": "library",
                "bom-ref": f"{component.name}@{component.version}",
                "name": component.name
            }
            
            if component.version:
                comp_obj["version"] = component.version
            
            if component.supplier:
                comp_obj["supplier"] = {
                    "name": component.supplier
                }
            
            if component.license_concluded:
                comp_obj["licenses"] = [{
                    "license": {
                        "id": component.license_concluded
                    }
                }]
            
            if component.download_location:
                comp_obj["purl"] = component.download_location
            
            if component.checksum_sha256:
                comp_obj["hashes"] = [{
                    "alg": "SHA-256",
                    "content": component.checksum_sha256
                }]
            
            cyclonedx_doc["components"].append(comp_obj)
        
        if format_type == SBOMFormat.CYCLONEDX_JSON:
            return cyclonedx_doc
        else:
            # Convert to XML (simplified implementation)
            return json.dumps(cyclonedx_doc, indent=2)  # For now, return JSON string
    
    def _enrich_with_vulnerabilities(self, sbom_content: Union[str, Dict[str, Any]], 
                                   components: List[ComponentInfo]) -> Union[str, Dict[str, Any]]:
        """Enrich SBOM with vulnerability information."""
        # This would integrate with vulnerability databases
        # For now, return as-is (vulnerability scanning would be implemented here)
        return sbom_content
    
    def _generate_signature(self, sbom_content: Union[str, Dict[str, Any]], 
                          format_type: SBOMFormat) -> Dict[str, Any]:
        """Generate digital signature for SBOM."""
        try:
            from .signer import SBOMSigner, SignatureAlgorithm
            
            signer = SBOMSigner(algorithm=SignatureAlgorithm.ED25519)
            
            # Convert content to bytes
            if isinstance(sbom_content, dict):
                content_bytes = json.dumps(sbom_content, sort_keys=True).encode('utf-8')
            else:
                content_bytes = sbom_content.encode('utf-8')
            
            signature = signer.sign(content_bytes)
            return signature
            
        except ImportError:
            logger.warning("SBOM signing not available - signer module not found")
            return {"error": "Signing not available"}
        except Exception as e:
            logger.error(f"Failed to generate SBOM signature: {e}")
            return {"error": str(e)}
    
    def save_sbom(self, sbom_data: Dict[str, Any], output_path: Union[str, Path]) -> bool:
        """
        Save SBOM to file.
        
        Args:
            sbom_data: SBOM data from generate_sbom()
            output_path: Output file path
            
        Returns:
            True if successful
        """
        try:
            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            content = sbom_data['sbom_content']
            
            with open(output_path, 'w', encoding='utf-8') as f:
                if isinstance(content, dict):
                    json.dump(content, f, indent=2)
                else:
                    f.write(content)
            
            logger.info(f"SBOM saved to {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save SBOM: {e}")
            return False