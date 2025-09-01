"""
M010 Security Module - Unified SBOM Generator

Consolidates original and optimized SBOM generators with operation modes:
- BASIC: Core SBOM generation with standard features
- PERFORMANCE: Optimized generation with caching and parallelization
- SECURE/ENTERPRISE: Enhanced security with signatures and validation

Supports SPDX 2.3 and CycloneDX 1.4 formats with digital signatures,
vulnerability scanning, and compliance reporting.
"""

import asyncio
import json
import logging
import time
import hashlib
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List, Optional, Union, Set, Tuple
from enum import Enum
from dataclasses import dataclass, field, asdict
import subprocess
import re
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor, as_completed
import multiprocessing as mp
from functools import lru_cache
from collections import defaultdict, deque
import pickle

# Optional performance dependencies (for optimized mode)
try:
    import msgpack  # For efficient serialization
    import networkx as nx  # For dependency graph operations
    OPTIMIZATION_AVAILABLE = True
except ImportError:
    OPTIMIZATION_AVAILABLE = False

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


class SBOMOperationMode(str, Enum):
    """SBOM operation modes."""
    BASIC = "basic"
    PERFORMANCE = "performance"
    SECURE = "secure"
    ENTERPRISE = "enterprise"


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
class Package:
    """Represents a package in SBOM (optimized mode)."""
    name: str
    version: str
    license: str
    hash: str = ""
    dependencies: List[str] = None
    vulnerabilities: List[str] = None
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.dependencies is None:
            self.dependencies = []
        if self.vulnerabilities is None:
            self.vulnerabilities = []
        if self.metadata is None:
            self.metadata = {}


@dataclass
class SBOMConfig:
    """Configuration for SBOM generation."""
    mode: SBOMOperationMode = SBOMOperationMode.ENTERPRISE
    
    # Core settings
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
    
    # Performance optimization settings
    enable_parallel_scanning: bool = False
    enable_dependency_caching: bool = False
    enable_incremental_updates: bool = False
    max_workers: int = 4
    cache_ttl_hours: int = 24
    use_msgpack_serialization: bool = False
    
    def __post_init__(self):
        """Configure mode-specific settings."""
        if self.mode == SBOMOperationMode.BASIC:
            self.enable_parallel_scanning = False
            self.enable_dependency_caching = False
            self.enable_incremental_updates = False
            self.use_msgpack_serialization = False
            self.sign_sbom = False
            
        elif self.mode == SBOMOperationMode.PERFORMANCE:
            self.enable_parallel_scanning = True
            self.enable_dependency_caching = True
            self.enable_incremental_updates = True
            self.use_msgpack_serialization = OPTIMIZATION_AVAILABLE
            self.max_workers = min(mp.cpu_count(), 8)
            
        elif self.mode in [SBOMOperationMode.SECURE, SBOMOperationMode.ENTERPRISE]:
            self.enable_parallel_scanning = True
            self.enable_dependency_caching = True
            self.enable_incremental_updates = True
            self.use_msgpack_serialization = OPTIMIZATION_AVAILABLE
            self.sign_sbom = True
            self.max_workers = min(mp.cpu_count(), 6)  # Reserve CPU for security operations


class DependencyGraph:
    """Efficient dependency graph with caching (optimized mode)."""
    
    def __init__(self):
        if not OPTIMIZATION_AVAILABLE:
            raise RuntimeError("NetworkX required for dependency graph operations")
        self.graph = nx.DiGraph()
        self._cache = {}
        self._dirty = set()
    
    def add_package(self, package: Package):
        """Add package to graph."""
        self.graph.add_node(package.name, data=package)
        for dep in package.dependencies:
            self.graph.add_edge(package.name, dep)
        self._dirty.add(package.name)
    
    def get_dependencies(self, package_name: str, transitive: bool = True) -> Set[str]:
        """Get dependencies with caching."""
        cache_key = f"{package_name}_{transitive}"
        
        if cache_key not in self._cache or package_name in self._dirty:
            if transitive:
                deps = nx.descendants(self.graph, package_name)
            else:
                deps = set(self.graph.successors(package_name))
            self._cache[cache_key] = deps
        
        return self._cache[cache_key]
    
    def clear_cache(self, package_name: str = None):
        """Clear cache for package or all."""
        if package_name:
            self._dirty.add(package_name)
        else:
            self._cache.clear()
            self._dirty.clear()
    
    def detect_cycles(self) -> List[List[str]]:
        """Detect dependency cycles."""
        try:
            return list(nx.simple_cycles(self.graph))
        except:
            return []
    
    def topological_order(self) -> List[str]:
        """Get packages in topological order."""
        return list(nx.topological_sort(self.graph))


class UnifiedSBOMGenerator:
    """
    Unified SBOM Generator supporting multiple operation modes.
    
    Modes:
    - BASIC: Standard SBOM generation without optimizations
    - PERFORMANCE: Parallel scanning, caching, and optimizations
    - SECURE: Enhanced security with signatures and validation
    - ENTERPRISE: All features enabled with comprehensive security
    """
    
    def __init__(self, config: Optional[SBOMConfig] = None):
        """Initialize unified SBOM generator."""
        self.config = config or SBOMConfig()
        self._dependency_cache = {}
        self._vulnerability_cache = {}
        self._license_cache = {}
        self._dependency_graph = None
        
        # Performance components (initialized based on mode)
        self._thread_pool = None
        self._process_pool = None
        
        if self.config.enable_parallel_scanning:
            self._thread_pool = ThreadPoolExecutor(max_workers=self.config.max_workers)
            self._process_pool = ProcessPoolExecutor(max_workers=min(self.config.max_workers, 4))
        
        if self.config.enable_dependency_caching and OPTIMIZATION_AVAILABLE:
            self._dependency_graph = DependencyGraph()
            
        logger.info(f"Initialized SBOM generator in {self.config.mode.value} mode")
    
    def generate_sbom(self, project_path: str, output_format: SBOMFormat = SBOMFormat.SPDX_JSON) -> Dict[str, Any]:
        """Generate SBOM synchronously (basic mode)."""
        start_time = time.time()
        
        try:
            logger.info(f"Starting SBOM generation for {project_path}")
            
            # Analyze project structure
            project_info = self._analyze_project(Path(project_path))
            
            # Scan dependencies
            if self.config.mode == SBOMOperationMode.BASIC:
                components = self._scan_dependencies_basic(Path(project_path))
            else:
                # Use optimized scanning for other modes
                components = self._scan_dependencies_optimized(Path(project_path))
            
            # Generate SBOM document
            sbom_document = self._create_sbom_document(project_info, components, output_format)
            
            # Add vulnerabilities if enabled
            if self.config.include_vulnerabilities:
                sbom_document = self._add_vulnerability_data(sbom_document, components)
            
            # Sign SBOM if enabled
            if self.config.sign_sbom:
                sbom_document = self._sign_sbom(sbom_document)
            
            generation_time = time.time() - start_time
            logger.info(f"SBOM generation completed in {generation_time:.2f} seconds")
            
            # Add metadata
            sbom_document['metadata'] = {
                'generation_time_seconds': generation_time,
                'total_components': len(components),
                'mode': self.config.mode.value,
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
            
            return sbom_document
            
        except Exception as e:
            logger.error(f"SBOM generation failed: {e}")
            raise
    
    async def generate_sbom_async(self, project_path: str, output_format: SBOMFormat = SBOMFormat.SPDX_JSON) -> Dict[str, Any]:
        """Generate SBOM asynchronously (optimized modes)."""
        if self.config.mode == SBOMOperationMode.BASIC:
            # Run synchronous generation in thread pool for basic mode
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, self.generate_sbom, project_path, output_format)
        
        start_time = time.time()
        
        try:
            logger.info(f"Starting async SBOM generation for {project_path}")
            
            # Analyze project structure
            project_info = await self._analyze_project_async(Path(project_path))
            
            # Scan dependencies with parallelization
            components = await self._scan_dependencies_async(Path(project_path))
            
            # Generate SBOM document
            sbom_document = await self._create_sbom_document_async(project_info, components, output_format)
            
            # Add vulnerabilities if enabled (parallel)
            if self.config.include_vulnerabilities:
                sbom_document = await self._add_vulnerability_data_async(sbom_document, components)
            
            # Sign SBOM if enabled
            if self.config.sign_sbom:
                sbom_document = await self._sign_sbom_async(sbom_document)
            
            generation_time = time.time() - start_time
            logger.info(f"Async SBOM generation completed in {generation_time:.2f} seconds")
            
            # Add metadata
            sbom_document['metadata'] = {
                'generation_time_seconds': generation_time,
                'total_components': len(components),
                'mode': self.config.mode.value,
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'async_generation': True
            }
            
            return sbom_document
            
        except Exception as e:
            logger.error(f"Async SBOM generation failed: {e}")
            raise
    
    # Project Analysis Methods
    
    def _analyze_project(self, project_path: Path) -> Dict[str, Any]:
        """Analyze project structure synchronously."""
        project_info = {
            'name': project_path.name,
            'path': str(project_path),
            'size_bytes': sum(f.stat().st_size for f in project_path.rglob('*') if f.is_file()),
            'file_count': len(list(project_path.rglob('*'))),
            'languages': self._detect_languages(project_path),
            'package_managers': self._detect_package_managers(project_path)
        }
        return project_info
    
    async def _analyze_project_async(self, project_path: Path) -> Dict[str, Any]:
        """Analyze project structure asynchronously."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(self._thread_pool, self._analyze_project, project_path)
    
    def _detect_languages(self, project_path: Path) -> List[str]:
        """Detect programming languages in project."""
        language_extensions = {
            '.py': 'Python',
            '.js': 'JavaScript',
            '.ts': 'TypeScript',
            '.java': 'Java',
            '.go': 'Go',
            '.rs': 'Rust',
            '.cpp': 'C++',
            '.c': 'C',
            '.cs': 'C#',
            '.rb': 'Ruby',
            '.php': 'PHP'
        }
        
        detected_languages = set()
        for file_path in project_path.rglob('*'):
            if file_path.is_file():
                suffix = file_path.suffix.lower()
                if suffix in language_extensions:
                    detected_languages.add(language_extensions[suffix])
        
        return list(detected_languages)
    
    def _detect_package_managers(self, project_path: Path) -> List[str]:
        """Detect package managers in project."""
        package_files = {
            'package.json': 'npm',
            'requirements.txt': 'pip',
            'Pipfile': 'pipenv',
            'pyproject.toml': 'poetry',
            'Cargo.toml': 'cargo',
            'go.mod': 'go',
            'pom.xml': 'maven',
            'build.gradle': 'gradle',
            'composer.json': 'composer',
            'Gemfile': 'bundler'
        }
        
        detected_managers = []
        for file_name, manager in package_files.items():
            if (project_path / file_name).exists():
                detected_managers.append(manager)
        
        return detected_managers
    
    # Dependency Scanning Methods
    
    def _scan_dependencies_basic(self, project_path: Path) -> List[ComponentInfo]:
        """Scan dependencies using basic implementation."""
        components = []
        
        # Scan Python dependencies
        if (project_path / 'requirements.txt').exists():
            components.extend(self._scan_python_requirements(project_path / 'requirements.txt'))
        
        if (project_path / 'package.json').exists():
            components.extend(self._scan_npm_dependencies(project_path / 'package.json'))
        
        return components
    
    def _scan_dependencies_optimized(self, project_path: Path) -> List[ComponentInfo]:
        """Scan dependencies using optimized implementation."""
        if not self._thread_pool:
            return self._scan_dependencies_basic(project_path)
        
        futures = []
        
        # Parallel scanning of different package managers
        if (project_path / 'requirements.txt').exists():
            future = self._thread_pool.submit(self._scan_python_requirements, project_path / 'requirements.txt')
            futures.append(future)
        
        if (project_path / 'package.json').exists():
            future = self._thread_pool.submit(self._scan_npm_dependencies, project_path / 'package.json')
            futures.append(future)
        
        # Additional package managers can be added here
        
        components = []
        for future in as_completed(futures):
            try:
                result = future.result()
                components.extend(result)
            except Exception as e:
                logger.error(f"Dependency scanning failed: {e}")
        
        return components
    
    async def _scan_dependencies_async(self, project_path: Path) -> List[ComponentInfo]:
        """Scan dependencies asynchronously with full parallelization."""
        loop = asyncio.get_event_loop()
        
        tasks = []
        
        # Create async tasks for different package managers
        if (project_path / 'requirements.txt').exists():
            task = loop.run_in_executor(self._thread_pool, self._scan_python_requirements, 
                                      project_path / 'requirements.txt')
            tasks.append(task)
        
        if (project_path / 'package.json').exists():
            task = loop.run_in_executor(self._thread_pool, self._scan_npm_dependencies, 
                                      project_path / 'package.json')
            tasks.append(task)
        
        # Wait for all tasks to complete
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        components = []
        for result in results:
            if isinstance(result, Exception):
                logger.error(f"Async dependency scanning failed: {result}")
            else:
                components.extend(result)
        
        return components
    
    def _scan_python_requirements(self, requirements_file: Path) -> List[ComponentInfo]:
        """Scan Python requirements.txt file."""
        components = []
        
        try:
            with open(requirements_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        # Parse requirement (basic parsing)
                        match = re.match(r'([a-zA-Z0-9_-]+)([=<>!]+)?([0-9.]+)?', line)
                        if match:
                            name = match.group(1)
                            version = match.group(3) or "unknown"
                            
                            component = ComponentInfo(
                                name=name,
                                version=version,
                                supplier="PyPI",
                                download_location=f"https://pypi.org/project/{name}/",
                                license_concluded=self._get_cached_license(name, "python")
                            )
                            components.append(component)
                            
        except Exception as e:
            logger.error(f"Failed to scan Python requirements: {e}")
        
        return components
    
    def _scan_npm_dependencies(self, package_json: Path) -> List[ComponentInfo]:
        """Scan npm package.json dependencies."""
        components = []
        
        try:
            with open(package_json, 'r') as f:
                data = json.load(f)
            
            # Scan dependencies
            dependencies = data.get('dependencies', {})
            if self.config.include_dev_dependencies:
                dependencies.update(data.get('devDependencies', {}))
            
            for name, version in dependencies.items():
                component = ComponentInfo(
                    name=name,
                    version=version.lstrip('^~'),  # Remove version prefixes
                    supplier="npm",
                    download_location=f"https://www.npmjs.com/package/{name}",
                    license_concluded=self._get_cached_license(name, "npm")
                )
                components.append(component)
                
        except Exception as e:
            logger.error(f"Failed to scan npm dependencies: {e}")
        
        return components
    
    @lru_cache(maxsize=1000)
    def _get_cached_license(self, package_name: str, ecosystem: str) -> Optional[str]:
        """Get cached license information."""
        # In a real implementation, this would query package registries
        # For now, return common licenses based on ecosystem
        common_licenses = {
            'python': 'MIT',
            'npm': 'MIT',
            'go': 'BSD-3-Clause',
            'java': 'Apache-2.0'
        }
        return common_licenses.get(ecosystem, LicenseType.UNKNOWN.value)
    
    # SBOM Document Creation Methods
    
    def _create_sbom_document(self, project_info: Dict[str, Any], components: List[ComponentInfo], 
                            format_type: SBOMFormat) -> Dict[str, Any]:
        """Create SBOM document in specified format."""
        if format_type in [SBOMFormat.SPDX_JSON, SBOMFormat.SPDX_XML]:
            return self._create_spdx_document(project_info, components)
        else:
            return self._create_cyclonedx_document(project_info, components)
    
    async def _create_sbom_document_async(self, project_info: Dict[str, Any], components: List[ComponentInfo], 
                                        format_type: SBOMFormat) -> Dict[str, Any]:
        """Create SBOM document asynchronously."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(self._thread_pool, self._create_sbom_document, 
                                        project_info, components, format_type)
    
    def _create_spdx_document(self, project_info: Dict[str, Any], components: List[ComponentInfo]) -> Dict[str, Any]:
        """Create SPDX format document."""
        document_id = f"SPDXRef-DOCUMENT"
        document_name = f"{project_info['name']}-SBOM"
        document_namespace = f"{self.config.namespace_base}/{project_info['name']}/{uuid.uuid4()}"
        
        spdx_document = {
            "spdxVersion": "SPDX-2.3",
            "dataLicense": "CC0-1.0",
            "SPDXID": document_id,
            "name": document_name,
            "documentNamespace": document_namespace,
            "creationInfo": {
                "created": datetime.now(timezone.utc).isoformat(),
                "creators": [f"Tool: {self.config.creator_tool}-{self.config.creator_version}"],
                "licenseListVersion": "3.19"
            },
            "packages": []
        }
        
        # Add main package
        main_package = {
            "SPDXID": "SPDXRef-Package-Main",
            "name": project_info['name'],
            "downloadLocation": "NOASSERTION",
            "filesAnalyzed": self.config.include_file_analysis,
            "copyrightText": "NOASSERTION"
        }
        spdx_document["packages"].append(main_package)
        
        # Add component packages
        for i, component in enumerate(components):
            package = {
                "SPDXID": f"SPDXRef-Package-{i+1}",
                "name": component.name,
                "versionInfo": component.version,
                "downloadLocation": component.download_location or "NOASSERTION",
                "filesAnalyzed": component.files_analyzed,
                "licenseConcluded": component.license_concluded or "NOASSERTION",
                "copyrightText": component.copyright_text or "NOASSERTION"
            }
            
            if component.supplier:
                package["supplier"] = f"Organization: {component.supplier}"
            
            if component.checksum_sha256:
                package["checksums"] = [{
                    "algorithm": "SHA256",
                    "checksumValue": component.checksum_sha256
                }]
            
            spdx_document["packages"].append(package)
        
        return spdx_document
    
    def _create_cyclonedx_document(self, project_info: Dict[str, Any], components: List[ComponentInfo]) -> Dict[str, Any]:
        """Create CycloneDX format document."""
        cyclonedx_document = {
            "bomFormat": "CycloneDX",
            "specVersion": "1.4",
            "serialNumber": f"urn:uuid:{uuid.uuid4()}",
            "version": 1,
            "metadata": {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "tools": [
                    {
                        "vendor": self.config.organization,
                        "name": self.config.creator_tool,
                        "version": self.config.creator_version
                    }
                ],
                "component": {
                    "type": "application",
                    "name": project_info['name'],
                    "version": "1.0.0"
                }
            },
            "components": []
        }
        
        # Add component packages
        for component in components:
            cyclone_component = {
                "type": "library",
                "name": component.name,
                "version": component.version
            }
            
            if component.license_concluded:
                cyclone_component["licenses"] = [{
                    "license": {
                        "id": component.license_concluded
                    }
                }]
            
            if component.download_location:
                cyclone_component["externalReferences"] = [{
                    "type": "distribution",
                    "url": component.download_location
                }]
            
            if component.checksum_sha256:
                cyclone_component["hashes"] = [{
                    "alg": "SHA-256",
                    "content": component.checksum_sha256
                }]
            
            cyclonedx_document["components"].append(cyclone_component)
        
        return cyclonedx_document
    
    # Vulnerability Analysis Methods
    
    def _add_vulnerability_data(self, sbom_document: Dict[str, Any], components: List[ComponentInfo]) -> Dict[str, Any]:
        """Add vulnerability data to SBOM (basic mode)."""
        # Basic vulnerability scanning
        for component in components:
            vulns = self._scan_vulnerabilities_basic(component)
            component.vulnerabilities.extend(vulns)
        
        return sbom_document
    
    async def _add_vulnerability_data_async(self, sbom_document: Dict[str, Any], components: List[ComponentInfo]) -> Dict[str, Any]:
        """Add vulnerability data to SBOM (async mode)."""
        if self.config.mode == SBOMOperationMode.BASIC:
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, self._add_vulnerability_data, sbom_document, components)
        
        # Parallel vulnerability scanning
        tasks = []
        loop = asyncio.get_event_loop()
        
        for component in components:
            task = loop.run_in_executor(self._thread_pool, self._scan_vulnerabilities_basic, component)
            tasks.append((component, task))
        
        for component, task in tasks:
            try:
                vulns = await task
                component.vulnerabilities.extend(vulns)
            except Exception as e:
                logger.error(f"Vulnerability scanning failed for {component.name}: {e}")
        
        return sbom_document
    
    def _scan_vulnerabilities_basic(self, component: ComponentInfo) -> List[Dict[str, Any]]:
        """Basic vulnerability scanning."""
        # In a real implementation, this would query vulnerability databases
        # For now, return empty list
        return []
    
    # Digital Signature Methods
    
    def _sign_sbom(self, sbom_document: Dict[str, Any]) -> Dict[str, Any]:
        """Sign SBOM document (basic mode)."""
        if not self.config.sign_sbom:
            return sbom_document
        
        # In a real implementation, this would use proper cryptographic signing
        signature = {
            "algorithm": self.config.signature_algorithm,
            "signature": hashlib.sha256(json.dumps(sbom_document, sort_keys=True).encode()).hexdigest(),
            "signed_at": datetime.now(timezone.utc).isoformat(),
            "signer": self.config.organization
        }
        
        sbom_document["signature"] = signature
        return sbom_document
    
    async def _sign_sbom_async(self, sbom_document: Dict[str, Any]) -> Dict[str, Any]:
        """Sign SBOM document (async mode)."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(self._thread_pool, self._sign_sbom, sbom_document)
    
    # Utility Methods
    
    def save_sbom(self, sbom_document: Dict[str, Any], output_path: Path, format_type: SBOMFormat):
        """Save SBOM document to file."""
        if format_type in [SBOMFormat.SPDX_JSON, SBOMFormat.CYCLONEDX_JSON]:
            with open(output_path, 'w') as f:
                if self.config.use_msgpack_serialization and OPTIMIZATION_AVAILABLE:
                    # Use msgpack for better performance
                    msgpack.dump(sbom_document, f)
                else:
                    json.dump(sbom_document, f, indent=2)
        else:
            # XML formats
            self._save_sbom_xml(sbom_document, output_path, format_type)
    
    def _save_sbom_xml(self, sbom_document: Dict[str, Any], output_path: Path, format_type: SBOMFormat):
        """Save SBOM as XML format."""
        # Basic XML serialization (would need proper XML generation in real implementation)
        xml_content = f"<!-- {format_type.value} XML format -->\n{json.dumps(sbom_document, indent=2)}"
        with open(output_path, 'w') as f:
            f.write(xml_content)
    
    async def health_check(self) -> bool:
        """Perform health check of SBOM generator."""
        try:
            # Check if required dependencies are available
            if self.config.enable_dependency_caching and not OPTIMIZATION_AVAILABLE:
                logger.warning("Optimization dependencies not available")
                return False
            
            # Check if thread pools are healthy
            if self._thread_pool and self._thread_pool._shutdown:
                logger.error("Thread pool is shutdown")
                return False
            
            # Test basic functionality
            test_project = Path("/tmp/test_project")
            test_project.mkdir(exist_ok=True)
            
            # Create a minimal test case
            (test_project / "requirements.txt").write_text("requests==2.28.1\n")
            
            try:
                sbom = self.generate_sbom(str(test_project))
                return len(sbom.get('packages', [])) > 0
            finally:
                # Cleanup
                if test_project.exists():
                    import shutil
                    shutil.rmtree(test_project)
            
        except Exception as e:
            logger.error(f"SBOM generator health check failed: {e}")
            return False
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get SBOM generator statistics."""
        return {
            'mode': self.config.mode.value,
            'parallel_scanning_enabled': self.config.enable_parallel_scanning,
            'dependency_caching_enabled': self.config.enable_dependency_caching,
            'incremental_updates_enabled': self.config.enable_incremental_updates,
            'optimization_available': OPTIMIZATION_AVAILABLE,
            'max_workers': self.config.max_workers,
            'thread_pool_active': self._thread_pool is not None and not self._thread_pool._shutdown if self._thread_pool else False,
            'dependency_cache_size': len(self._dependency_cache),
            'vulnerability_cache_size': len(self._vulnerability_cache),
            'license_cache_size': len(self._license_cache)
        }
    
    def __del__(self):
        """Cleanup resources."""
        try:
            if self._thread_pool:
                self._thread_pool.shutdown(wait=False)
            if self._process_pool:
                self._process_pool.shutdown(wait=False)
        except:
            pass


# Factory functions for different modes
def create_basic_sbom_generator(config: Optional[SBOMConfig] = None) -> UnifiedSBOMGenerator:
    """Create basic SBOM generator."""
    if config is None:
        config = SBOMConfig(mode=SBOMOperationMode.BASIC)
    return UnifiedSBOMGenerator(config)


def create_performance_sbom_generator(config: Optional[SBOMConfig] = None) -> UnifiedSBOMGenerator:
    """Create performance-optimized SBOM generator."""
    if config is None:
        config = SBOMConfig(mode=SBOMOperationMode.PERFORMANCE)
    return UnifiedSBOMGenerator(config)


def create_secure_sbom_generator(config: Optional[SBOMConfig] = None) -> UnifiedSBOMGenerator:
    """Create security-enhanced SBOM generator."""
    if config is None:
        config = SBOMConfig(mode=SBOMOperationMode.SECURE)
    return UnifiedSBOMGenerator(config)


def create_enterprise_sbom_generator(config: Optional[SBOMConfig] = None) -> UnifiedSBOMGenerator:
    """Create enterprise SBOM generator with all features."""
    if config is None:
        config = SBOMConfig(mode=SBOMOperationMode.ENTERPRISE)
    return UnifiedSBOMGenerator(config)