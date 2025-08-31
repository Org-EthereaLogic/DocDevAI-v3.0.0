"""
Core SBOM Testing Framework.

Provides the central testing infrastructure for SBOM validation, generation,
and security analysis. Integrates with existing M001-M008 testing patterns.
"""

import json
import xml.etree.ElementTree as ET
import yaml
import hashlib
import tempfile
import shutil
from pathlib import Path
from typing import Dict, List, Any, Optional, Union, Tuple
from datetime import datetime, timezone
from dataclasses import dataclass, field
from enum import Enum
import time
import logging

# Import existing testing utilities
from devdocai.common.testing import (
    BaseTestCase, 
    PerformanceTester, 
    TestDataGenerator, 
    temp_directory
)

logger = logging.getLogger(__name__)


class SBOMFormat(Enum):
    """Supported SBOM formats."""
    SPDX_JSON = "spdx-json"
    SPDX_YAML = "spdx-yaml"
    SPDX_TAG_VALUE = "spdx-tag"
    SPDX_RDF_XML = "spdx-rdf"
    SPDX_JSON_LD = "spdx-jsonld"
    CYCLONE_DX_JSON = "cyclonedx-json"
    CYCLONE_DX_XML = "cyclonedx-xml"


class LicenseType(Enum):
    """License classification types."""
    COMMERCIAL = "commercial"
    COPYLEFT = "copyleft"
    PERMISSIVE = "permissive"
    PROPRIETARY = "proprietary"
    PUBLIC_DOMAIN = "public-domain"
    UNKNOWN = "unknown"


@dataclass
class SBOMTestMetrics:
    """Performance and quality metrics for SBOM operations."""
    generation_time: float = 0.0
    validation_time: float = 0.0
    file_size: int = 0
    dependency_count: int = 0
    license_detection_accuracy: float = 0.0
    cve_scan_precision: float = 0.0
    cve_scan_recall: float = 0.0
    format_compliance_score: float = 0.0
    signature_verification_success: bool = False


@dataclass
class DependencyNode:
    """Represents a dependency in the dependency tree."""
    name: str
    version: str
    license: Optional[str] = None
    license_type: Optional[LicenseType] = None
    cve_ids: List[str] = field(default_factory=list)
    children: List['DependencyNode'] = field(default_factory=list)
    package_url: Optional[str] = None  # PURL format
    supplier: Optional[str] = None
    hash_sha256: Optional[str] = None


@dataclass 
class CVEVulnerability:
    """CVE vulnerability information."""
    cve_id: str
    cvss_score: float
    severity: str  # LOW, MEDIUM, HIGH, CRITICAL
    description: str
    published_date: str
    last_modified: str
    affected_packages: List[str] = field(default_factory=list)


class SBOMTestFramework(BaseTestCase):
    """
    Comprehensive SBOM testing framework.
    
    Provides testing infrastructure for SBOM generation, validation,
    and security analysis with enterprise-grade quality targets.
    """
    
    def __init__(self):
        super().__init__()
        self.metrics = SBOMTestMetrics()
        self.test_data_cache = {}
        self.performance_baseline = {}
    
    def setup_method(self):
        """Set up test environment."""
        super().setup_method()
        self.temp_sbom_dir = self.create_temp_dir()
        self.fixtures_dir = Path(__file__).parent / "fixtures"
    
    # ============================================================================
    # CORE TESTING INFRASTRUCTURE
    # ============================================================================
    
    def generate_test_dependency_tree(
        self, 
        depth: int = 3, 
        breadth: int = 4, 
        include_vulnerabilities: bool = True
    ) -> DependencyNode:
        """
        Generate test dependency tree with realistic structure.
        
        Args:
            depth: Maximum tree depth
            breadth: Maximum children per node
            include_vulnerabilities: Whether to include CVE data
            
        Returns:
            Root dependency node
        """
        def create_node(level: int, parent_name: str = None) -> DependencyNode:
            if level >= depth:
                return None
                
            # Generate realistic package names
            frameworks = ["react", "vue", "angular", "express", "flask", "django"]
            utilities = ["lodash", "axios", "moment", "chalk", "commander", "yargs"]
            pkg_pool = frameworks + utilities
            
            import random
            name = f"{random.choice(pkg_pool)}-{level}-{random.randint(1000, 9999)}"
            version = f"{random.randint(1, 5)}.{random.randint(0, 9)}.{random.randint(0, 9)}"
            
            # Generate realistic license
            licenses = [
                ("MIT", LicenseType.PERMISSIVE),
                ("Apache-2.0", LicenseType.PERMISSIVE), 
                ("GPL-3.0", LicenseType.COPYLEFT),
                ("BSD-3-Clause", LicenseType.PERMISSIVE),
                ("ISC", LicenseType.PERMISSIVE)
            ]
            license_name, license_type = random.choice(licenses)
            
            # Generate CVE vulnerabilities if requested
            cve_ids = []
            if include_vulnerabilities and random.random() < 0.15:  # 15% chance
                year = random.randint(2020, 2024)
                cve_num = random.randint(1000, 9999)
                cve_ids = [f"CVE-{year}-{cve_num}"]
            
            # Create node
            node = DependencyNode(
                name=name,
                version=version,
                license=license_name,
                license_type=license_type,
                cve_ids=cve_ids,
                package_url=f"pkg:npm/{name}@{version}",
                supplier=f"https://www.npmjs.com/package/{name}",
                hash_sha256=hashlib.sha256(f"{name}@{version}".encode()).hexdigest()
            )
            
            # Add children
            if level < depth - 1:
                child_count = random.randint(1, min(breadth, 4))
                for _ in range(child_count):
                    child = create_node(level + 1, name)
                    if child:
                        node.children.append(child)
            
            return node
        
        root = create_node(0)
        self.metrics.dependency_count = self._count_dependencies(root)
        return root
    
    def _count_dependencies(self, node: DependencyNode) -> int:
        """Recursively count total dependencies."""
        if not node:
            return 0
        count = 1
        for child in node.children:
            count += self._count_dependencies(child)
        return count
    
    def create_test_project(self, project_type: str = "npm") -> Path:
        """
        Create realistic test project with dependencies.
        
        Args:
            project_type: Type of project (npm, pip, maven, etc.)
            
        Returns:
            Path to created test project
        """
        project_dir = self.temp_sbom_dir / f"test_project_{project_type}_{int(time.time())}"
        project_dir.mkdir(exist_ok=True)
        
        if project_type == "npm":
            # Create package.json
            package_json = {
                "name": "test-sbom-project",
                "version": "1.0.0",
                "description": "Test project for SBOM generation",
                "dependencies": {
                    "express": "^4.18.2",
                    "lodash": "^4.17.21",
                    "axios": "^1.4.0"
                },
                "devDependencies": {
                    "jest": "^29.5.0",
                    "eslint": "^8.44.0"
                }
            }
            with open(project_dir / "package.json", "w") as f:
                json.dump(package_json, f, indent=2)
                
            # Create package-lock.json (simplified)
            package_lock = {
                "name": "test-sbom-project",
                "version": "1.0.0",
                "lockfileVersion": 3,
                "requires": True,
                "packages": {
                    "": {
                        "name": "test-sbom-project", 
                        "version": "1.0.0"
                    }
                }
            }
            with open(project_dir / "package-lock.json", "w") as f:
                json.dump(package_lock, f, indent=2)
                
        elif project_type == "pip":
            # Create requirements.txt
            requirements = [
                "requests==2.31.0",
                "pydantic>=2.0.0",
                "fastapi==0.100.0",
                "pytest>=7.4.0"
            ]
            with open(project_dir / "requirements.txt", "w") as f:
                f.write("\n".join(requirements))
                
            # Create setup.py
            setup_py = '''
from setuptools import setup, find_packages

setup(
    name="test-sbom-project",
    version="1.0.0",
    packages=find_packages(),
    install_requires=[
        "requests>=2.31.0",
        "pydantic>=2.0.0",
        "fastapi==0.100.0"
    ]
)
'''
            with open(project_dir / "setup.py", "w") as f:
                f.write(setup_py.strip())
        
        return project_dir
    
    def measure_sbom_generation(self, generator_func, *args, **kwargs) -> Tuple[Any, float]:
        """
        Measure SBOM generation performance.
        
        Args:
            generator_func: Function to generate SBOM
            *args, **kwargs: Arguments for generator function
            
        Returns:
            Tuple of (result, generation_time_seconds)
        """
        start_time = time.perf_counter()
        result = generator_func(*args, **kwargs)
        generation_time = time.perf_counter() - start_time
        
        self.metrics.generation_time = generation_time
        return result, generation_time
    
    def assert_performance_target(
        self, 
        measured_time: float, 
        target_time: float, 
        operation: str = "SBOM generation"
    ):
        """
        Assert performance meets target requirements.
        
        Args:
            measured_time: Actual measured time in seconds
            target_time: Target time requirement in seconds
            operation: Description of operation being tested
        """
        if measured_time > target_time:
            raise AssertionError(
                f"{operation} performance target not met: "
                f"{measured_time:.2f}s > {target_time:.2f}s target"
            )
        
        # Log performance success
        improvement = ((target_time - measured_time) / target_time) * 100
        logger.info(
            f"{operation} performance target met: {measured_time:.2f}s "
            f"({improvement:.1f}% under target)"
        )
    
    def create_cve_test_data(self) -> List[CVEVulnerability]:
        """Create realistic CVE test data."""
        cves = [
            CVEVulnerability(
                cve_id="CVE-2023-1234",
                cvss_score=9.8,
                severity="CRITICAL",
                description="Remote code execution in test package",
                published_date="2023-01-15T10:00:00Z",
                last_modified="2023-01-20T14:30:00Z",
                affected_packages=["express@4.17.1", "express@4.17.2"]
            ),
            CVEVulnerability(
                cve_id="CVE-2023-5678",
                cvss_score=6.1,
                severity="MEDIUM",
                description="Cross-site scripting vulnerability",
                published_date="2023-03-10T15:00:00Z",
                last_modified="2023-03-15T09:00:00Z",
                affected_packages=["lodash@4.17.20"]
            ),
            CVEVulnerability(
                cve_id="CVE-2023-9999",
                cvss_score=3.7,
                severity="LOW",
                description="Information disclosure issue",
                published_date="2023-06-01T12:00:00Z",
                last_modified="2023-06-05T16:00:00Z",
                affected_packages=["axios@0.27.0", "axios@0.27.1"]
            )
        ]
        return cves
    
    # ============================================================================
    # FORMAT-SPECIFIC HELPERS
    # ============================================================================
    
    def validate_json_structure(self, data: Dict[str, Any], schema: Dict[str, Any]) -> bool:
        """
        Validate JSON structure against schema.
        
        Args:
            data: JSON data to validate
            schema: Expected schema structure
            
        Returns:
            True if valid, False otherwise
        """
        try:
            # Basic schema validation (simplified)
            for key, expected_type in schema.items():
                if key not in data:
                    logger.error(f"Missing required key: {key}")
                    return False
                
                if not isinstance(data[key], expected_type):
                    logger.error(f"Invalid type for {key}: expected {expected_type}")
                    return False
            
            return True
        except Exception as e:
            logger.error(f"Schema validation error: {e}")
            return False
    
    def calculate_format_compliance_score(self, sbom_data: Any, format_type: SBOMFormat) -> float:
        """
        Calculate format compliance score (0.0 to 1.0).
        
        Args:
            sbom_data: SBOM data to analyze
            format_type: Expected SBOM format
            
        Returns:
            Compliance score between 0.0 and 1.0
        """
        try:
            score = 0.0
            checks = 0
            
            if format_type in [SBOMFormat.SPDX_JSON, SBOMFormat.SPDX_JSON_LD]:
                # SPDX JSON checks
                if isinstance(sbom_data, dict):
                    checks += 1
                    if "spdxVersion" in sbom_data:
                        score += 0.2
                    if "SPDXID" in sbom_data:
                        score += 0.2
                    if "documentName" in sbom_data:
                        score += 0.2
                    if "packages" in sbom_data:
                        score += 0.2
                    if "relationships" in sbom_data:
                        score += 0.2
                
            elif format_type == SBOMFormat.CYCLONE_DX_JSON:
                # CycloneDX JSON checks
                if isinstance(sbom_data, dict):
                    checks += 1
                    if "bomFormat" in sbom_data:
                        score += 0.25
                    if "specVersion" in sbom_data:
                        score += 0.25
                    if "components" in sbom_data:
                        score += 0.25
                    if "metadata" in sbom_data:
                        score += 0.25
            
            return score if checks > 0 else 0.0
            
        except Exception as e:
            logger.error(f"Compliance calculation error: {e}")
            return 0.0
    
    def cleanup_test_artifacts(self):
        """Clean up test artifacts and temporary files."""
        if hasattr(self, 'temp_sbom_dir') and self.temp_sbom_dir.exists():
            shutil.rmtree(self.temp_sbom_dir)
        
        # Clear caches
        self.test_data_cache.clear()
        self.performance_baseline.clear()


# ============================================================================
# TESTING UTILITIES
# ============================================================================

def create_sample_sbom(format_type: SBOMFormat, dependency_tree: DependencyNode) -> str:
    """
    Create sample SBOM in specified format.
    
    Args:
        format_type: Desired SBOM format
        dependency_tree: Dependency tree to convert
        
    Returns:
        SBOM content as string
    """
    timestamp = datetime.now(timezone.utc).isoformat()
    
    if format_type == SBOMFormat.SPDX_JSON:
        sbom_data = {
            "spdxVersion": "SPDX-2.3",
            "dataLicense": "CC0-1.0",
            "SPDXID": "SPDXRef-DOCUMENT",
            "documentName": "Test SBOM Document",
            "documentNamespace": f"https://example.com/sbom/{int(time.time())}",
            "creationInfo": {
                "created": timestamp,
                "creators": ["Tool: SBOM-Test-Framework"]
            },
            "packages": _convert_tree_to_spdx_packages(dependency_tree),
            "relationships": _generate_spdx_relationships(dependency_tree)
        }
        return json.dumps(sbom_data, indent=2)
    
    elif format_type == SBOMFormat.CYCLONE_DX_JSON:
        sbom_data = {
            "bomFormat": "CycloneDX",
            "specVersion": "1.4",
            "serialNumber": f"urn:uuid:{hashlib.md5(str(time.time()).encode()).hexdigest()}",
            "version": 1,
            "metadata": {
                "timestamp": timestamp,
                "tools": [{"vendor": "DevDocAI", "name": "SBOM-Test-Framework"}]
            },
            "components": _convert_tree_to_cyclone_components(dependency_tree)
        }
        return json.dumps(sbom_data, indent=2)
    
    else:
        raise ValueError(f"Unsupported format: {format_type}")


def _convert_tree_to_spdx_packages(node: DependencyNode) -> List[Dict[str, Any]]:
    """Convert dependency tree to SPDX packages."""
    packages = []
    
    def traverse(current_node):
        package = {
            "SPDXID": f"SPDXRef-Package-{current_node.name}",
            "name": current_node.name,
            "versionInfo": current_node.version,
            "downloadLocation": current_node.package_url or "NOASSERTION",
            "filesAnalyzed": False,
            "licenseConcluded": current_node.license or "NOASSERTION",
            "licenseDeclared": current_node.license or "NOASSERTION",
            "copyrightText": "NOASSERTION"
        }
        
        if current_node.hash_sha256:
            package["checksums"] = [{
                "algorithm": "SHA256",
                "value": current_node.hash_sha256
            }]
        
        packages.append(package)
        
        for child in current_node.children:
            traverse(child)
    
    traverse(node)
    return packages


def _generate_spdx_relationships(node: DependencyNode) -> List[Dict[str, Any]]:
    """Generate SPDX relationships from dependency tree."""
    relationships = [{
        "spdxElementId": "SPDXRef-DOCUMENT",
        "relationshipType": "DESCRIBES",
        "relatedSpdxElement": f"SPDXRef-Package-{node.name}"
    }]
    
    def traverse(current_node):
        for child in current_node.children:
            relationships.append({
                "spdxElementId": f"SPDXRef-Package-{current_node.name}",
                "relationshipType": "DEPENDS_ON", 
                "relatedSpdxElement": f"SPDXRef-Package-{child.name}"
            })
            traverse(child)
    
    traverse(node)
    return relationships


def _convert_tree_to_cyclone_components(node: DependencyNode) -> List[Dict[str, Any]]:
    """Convert dependency tree to CycloneDX components."""
    components = []
    
    def traverse(current_node):
        component = {
            "type": "library",
            "bom-ref": f"{current_node.name}@{current_node.version}",
            "name": current_node.name,
            "version": current_node.version
        }
        
        if current_node.package_url:
            component["purl"] = current_node.package_url
        
        if current_node.license:
            component["licenses"] = [{
                "license": {"id": current_node.license}
            }]
        
        if current_node.hash_sha256:
            component["hashes"] = [{
                "alg": "SHA-256",
                "content": current_node.hash_sha256
            }]
        
        components.append(component)
        
        for child in current_node.children:
            traverse(child)
    
    traverse(node)
    return components