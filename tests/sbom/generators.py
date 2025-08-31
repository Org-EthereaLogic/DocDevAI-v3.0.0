"""
SBOM Test Data Generators.

Comprehensive test data generation for SBOM testing scenarios,
including synthetic projects, vulnerability data, and edge cases.
"""

import json
import xml.etree.ElementTree as ET
import yaml
import hashlib
import random
import uuid
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
import tempfile
import os

from .core import (
    DependencyNode, CVEVulnerability, LicenseType, SBOMFormat,
    create_sample_sbom
)

# Import existing testing utilities
from devdocai.common.testing import TestDataGenerator as BaseTestDataGenerator


class SBOMTestDataGenerator(BaseTestDataGenerator):
    """
    Enhanced test data generator for SBOM testing.
    
    Generates realistic test data for:
    - Dependency trees with various structures
    - License scenarios with edge cases
    - CVE vulnerability data
    - Package metadata and signatures
    - Performance testing datasets
    """
    
    # Common package ecosystems for realistic testing
    ECOSYSTEMS = {
        "npm": {
            "packages": ["react", "vue", "express", "lodash", "axios", "webpack", "babel"],
            "file_extensions": [".js", ".json", ".ts"],
            "manifest": "package.json",
            "lock_file": "package-lock.json"
        },
        "pypi": {
            "packages": ["django", "flask", "requests", "pandas", "numpy", "pytest"],
            "file_extensions": [".py", ".txt", ".cfg"],
            "manifest": "requirements.txt",
            "lock_file": "Pipfile.lock"
        },
        "maven": {
            "packages": ["spring-boot", "jackson", "junit", "slf4j", "hibernate"],
            "file_extensions": [".java", ".xml", ".properties"],
            "manifest": "pom.xml",
            "lock_file": None
        },
        "nuget": {
            "packages": ["Microsoft.AspNetCore", "Newtonsoft.Json", "EntityFramework"],
            "file_extensions": [".cs", ".csproj", ".config"],
            "manifest": "packages.config",
            "lock_file": "packages.lock.json"
        }
    }
    
    # License distribution for realistic scenarios (based on real-world data)
    LICENSE_DISTRIBUTION = [
        ("MIT", LicenseType.PERMISSIVE, 0.35),
        ("Apache-2.0", LicenseType.PERMISSIVE, 0.15),
        ("BSD-3-Clause", LicenseType.PERMISSIVE, 0.08),
        ("GPL-3.0", LicenseType.COPYLEFT, 0.05),
        ("ISC", LicenseType.PERMISSIVE, 0.08),
        ("BSD-2-Clause", LicenseType.PERMISSIVE, 0.06),
        ("LGPL-2.1", LicenseType.COPYLEFT, 0.03),
        ("MPL-2.0", LicenseType.PERMISSIVE, 0.02),
        ("Unlicense", LicenseType.PUBLIC_DOMAIN, 0.02),
        ("Proprietary", LicenseType.PROPRIETARY, 0.05),
        (None, LicenseType.UNKNOWN, 0.11)  # Unknown/missing licenses
    ]
    
    def __init__(self, seed: Optional[int] = None):
        """Initialize generator with optional seed for reproducible results."""
        super().__init__()
        if seed:
            random.seed(seed)
        self.cve_counter = 1000
        self.package_counter = 1000
    
    def generate_realistic_dependency_tree(
        self, 
        ecosystem: str = "npm",
        complexity: str = "medium",
        include_vulnerabilities: bool = True,
        license_compliance_issues: bool = True
    ) -> DependencyNode:
        """
        Generate realistic dependency tree with configurable complexity.
        
        Args:
            ecosystem: Package ecosystem (npm, pypi, maven, nuget)
            complexity: Tree complexity (simple, medium, complex, enterprise)
            include_vulnerabilities: Whether to include CVE vulnerabilities
            license_compliance_issues: Whether to include license conflicts
            
        Returns:
            Root dependency node with realistic structure
        """
        complexity_config = {
            "simple": {"max_depth": 2, "max_breadth": 3, "total_packages": 8},
            "medium": {"max_depth": 4, "max_breadth": 5, "total_packages": 25},
            "complex": {"max_depth": 6, "max_breadth": 7, "total_packages": 75},
            "enterprise": {"max_depth": 8, "max_breadth": 10, "total_packages": 200}
        }
        
        config = complexity_config.get(complexity, complexity_config["medium"])
        eco_data = self.ECOSYSTEMS.get(ecosystem, self.ECOSYSTEMS["npm"])
        
        def create_realistic_node(depth: int, parent_name: str = None) -> Optional[DependencyNode]:
            if depth >= config["max_depth"]:
                return None
            
            # Generate package name
            base_name = random.choice(eco_data["packages"])
            suffix = f"-{random.choice(['core', 'utils', 'helpers', 'tools', 'lib'])}"
            name = f"{base_name}{suffix}-{self.package_counter}"
            self.package_counter += 1
            
            # Generate semantic version
            major = random.randint(0, 5)
            minor = random.randint(0, 20)
            patch = random.randint(0, 50)
            version = f"{major}.{minor}.{patch}"
            
            # Add pre-release or build metadata occasionally
            if random.random() < 0.1:
                version += f"-{random.choice(['alpha', 'beta', 'rc'])}.{random.randint(1, 5)}"
            if random.random() < 0.05:
                version += f"+{random.randint(100000, 999999)}"
            
            # Assign license based on realistic distribution
            license_name, license_type = self._select_license_realistic()
            
            # Handle license compliance issues
            if license_compliance_issues and parent_name:
                license_name, license_type = self._handle_license_conflicts(
                    license_name, license_type, depth
                )
            
            # Generate CVE vulnerabilities
            cve_ids = []
            if include_vulnerabilities and random.random() < (0.15 - depth * 0.02):  # Higher chance in direct dependencies
                num_cves = random.choices([1, 2, 3], weights=[0.7, 0.25, 0.05])[0]
                for _ in range(num_cves):
                    cve_id = self._generate_realistic_cve()
                    cve_ids.append(cve_id)
            
            # Generate package URL (PURL)
            purl = self._generate_purl(ecosystem, name, version)
            
            # Generate file hash
            hash_input = f"{ecosystem}:{name}@{version}:{random.randint(1000000, 9999999)}"
            file_hash = hashlib.sha256(hash_input.encode()).hexdigest()
            
            # Generate supplier information
            suppliers = [
                f"https://registry.{ecosystem}.org/{name}",
                f"https://github.com/{name.split('-')[0]}/{name}",
                f"https://{name.replace('-', '')}.com",
                "https://example.com/internal"
            ]
            supplier = random.choice(suppliers)
            
            node = DependencyNode(
                name=name,
                version=version,
                license=license_name,
                license_type=license_type,
                cve_ids=cve_ids,
                package_url=purl,
                supplier=supplier,
                hash_sha256=file_hash
            )
            
            # Add children recursively
            if depth < config["max_depth"] - 1:
                max_children = min(config["max_breadth"], max(1, config["max_breadth"] - depth))
                num_children = random.randint(0, max_children)
                
                for _ in range(num_children):
                    child = create_realistic_node(depth + 1, name)
                    if child:
                        node.children.append(child)
            
            return node
        
        root = create_realistic_node(0)
        return root
    
    def _select_license_realistic(self) -> Tuple[Optional[str], LicenseType]:
        """Select license based on realistic distribution."""
        rand_val = random.random()
        cumulative_prob = 0.0
        
        for license_name, license_type, probability in self.LICENSE_DISTRIBUTION:
            cumulative_prob += probability
            if rand_val <= cumulative_prob:
                return license_name, license_type
        
        # Fallback
        return "MIT", LicenseType.PERMISSIVE
    
    def _handle_license_conflicts(
        self, 
        license_name: Optional[str], 
        license_type: LicenseType, 
        depth: int
    ) -> Tuple[Optional[str], LicenseType]:
        """Introduce realistic license compliance issues."""
        # Create GPL contamination scenarios
        if depth > 2 and random.random() < 0.05:
            return "GPL-3.0", LicenseType.COPYLEFT
        
        # Create proprietary license conflicts
        if depth > 1 and random.random() < 0.03:
            return "Proprietary", LicenseType.PROPRIETARY
        
        # Create missing license scenarios
        if random.random() < 0.08:
            return None, LicenseType.UNKNOWN
        
        return license_name, license_type
    
    def _generate_realistic_cve(self) -> str:
        """Generate realistic CVE identifier."""
        year = random.choices(
            [2020, 2021, 2022, 2023, 2024],
            weights=[0.05, 0.10, 0.20, 0.35, 0.30]
        )[0]
        
        cve_num = self.cve_counter
        self.cve_counter += 1
        
        return f"CVE-{year}-{cve_num}"
    
    def _generate_purl(self, ecosystem: str, name: str, version: str) -> str:
        """Generate Package URL (PURL)."""
        ecosystem_map = {
            "npm": "npm",
            "pypi": "pypi", 
            "maven": "maven",
            "nuget": "nuget"
        }
        
        purl_type = ecosystem_map.get(ecosystem, "generic")
        return f"pkg:{purl_type}/{name}@{version}"
    
    def generate_cve_database(self, count: int = 100) -> List[CVEVulnerability]:
        """
        Generate realistic CVE vulnerability database.
        
        Args:
            count: Number of CVE entries to generate
            
        Returns:
            List of CVE vulnerability objects
        """
        cves = []
        
        # CVSS score distribution (based on real NVD data)
        severity_distribution = [
            ("CRITICAL", 9.0, 10.0, 0.08),
            ("HIGH", 7.0, 8.9, 0.22),
            ("MEDIUM", 4.0, 6.9, 0.45),
            ("LOW", 0.1, 3.9, 0.25)
        ]
        
        # Vulnerability types for realistic descriptions
        vuln_types = [
            "Remote code execution",
            "Cross-site scripting (XSS)",
            "SQL injection", 
            "Path traversal",
            "Authentication bypass",
            "Privilege escalation",
            "Information disclosure",
            "Denial of service",
            "Buffer overflow",
            "Use after free",
            "Integer overflow",
            "XML external entity (XXE)"
        ]
        
        for i in range(count):
            # Select severity and generate CVSS score
            severity, min_score, max_score, _ = random.choices(
                severity_distribution,
                weights=[dist[3] for dist in severity_distribution]
            )[0]
            
            cvss_score = round(random.uniform(min_score, max_score), 1)
            
            # Generate CVE ID
            year = random.choices(
                [2020, 2021, 2022, 2023, 2024],
                weights=[0.05, 0.15, 0.25, 0.35, 0.20]
            )[0]
            cve_id = f"CVE-{year}-{1000 + i}"
            
            # Generate description
            vuln_type = random.choice(vuln_types)
            package_name = random.choice(list(self.ECOSYSTEMS.values())[0]["packages"])
            description = f"{vuln_type} vulnerability in {package_name} package"
            
            # Generate dates
            published = datetime.now(timezone.utc) - timedelta(
                days=random.randint(1, 1095)  # Up to 3 years ago
            )
            modified = published + timedelta(
                days=random.randint(0, 180)  # Modified up to 6 months later
            )
            
            # Generate affected packages
            affected_count = random.choices([1, 2, 3, 4], weights=[0.6, 0.25, 0.10, 0.05])[0]
            affected_packages = []
            for _ in range(affected_count):
                pkg_name = random.choice(list(self.ECOSYSTEMS.values())[0]["packages"])
                version = f"{random.randint(0, 5)}.{random.randint(0, 20)}.{random.randint(0, 50)}"
                affected_packages.append(f"{pkg_name}@{version}")
            
            cve = CVEVulnerability(
                cve_id=cve_id,
                cvss_score=cvss_score,
                severity=severity,
                description=description,
                published_date=published.isoformat(),
                last_modified=modified.isoformat(),
                affected_packages=affected_packages
            )
            
            cves.append(cve)
        
        return sorted(cves, key=lambda x: x.published_date, reverse=True)
    
    def generate_license_test_scenarios(self) -> List[Dict[str, Any]]:
        """
        Generate test scenarios for license identification accuracy.
        
        Returns:
            List of license test scenarios with expected results
        """
        scenarios = []
        
        # Standard SPDX licenses
        standard_licenses = [
            "MIT", "Apache-2.0", "GPL-2.0", "GPL-3.0", "BSD-2-Clause", 
            "BSD-3-Clause", "ISC", "MPL-2.0", "LGPL-2.1", "LGPL-3.0"
        ]
        
        for license_id in standard_licenses:
            scenarios.append({
                "license_text": self._generate_license_text(license_id),
                "expected_license": license_id,
                "expected_type": self._get_license_type(license_id),
                "confidence_threshold": 0.95,
                "test_type": "standard_spdx"
            })
        
        # License variations and edge cases
        edge_cases = [
            {
                "license_text": "Licensed under MIT with additional terms",
                "expected_license": "MIT",
                "expected_type": LicenseType.PERMISSIVE,
                "confidence_threshold": 0.80,
                "test_type": "modified_standard"
            },
            {
                "license_text": "Copyright 2024. All rights reserved.",
                "expected_license": None,
                "expected_type": LicenseType.PROPRIETARY,
                "confidence_threshold": 0.90,
                "test_type": "proprietary"
            },
            {
                "license_text": "This software is in the public domain",
                "expected_license": "Unlicense",
                "expected_type": LicenseType.PUBLIC_DOMAIN,
                "confidence_threshold": 0.85,
                "test_type": "public_domain"
            },
            {
                "license_text": "",
                "expected_license": None,
                "expected_type": LicenseType.UNKNOWN,
                "confidence_threshold": 0.0,
                "test_type": "no_license"
            }
        ]
        
        scenarios.extend(edge_cases)
        
        # Dual/multiple licenses
        dual_licenses = [
            {
                "license_text": "Licensed under MIT OR Apache-2.0",
                "expected_license": "MIT OR Apache-2.0",
                "expected_type": LicenseType.PERMISSIVE,
                "confidence_threshold": 0.80,
                "test_type": "dual_license"
            },
            {
                "license_text": "GPL-2.0+ OR GPL-3.0+",
                "expected_license": "GPL-2.0+",
                "expected_type": LicenseType.COPYLEFT,
                "confidence_threshold": 0.75,
                "test_type": "version_range"
            }
        ]
        
        scenarios.extend(dual_licenses)
        
        return scenarios
    
    def _generate_license_text(self, license_id: str) -> str:
        """Generate realistic license text for testing."""
        license_templates = {
            "MIT": """
                MIT License
                
                Permission is hereby granted, free of charge, to any person obtaining a copy
                of this software and associated documentation files...
            """,
            "Apache-2.0": """
                Licensed under the Apache License, Version 2.0 (the "License");
                you may not use this file except in compliance with the License...
            """,
            "GPL-3.0": """
                This program is free software: you can redistribute it and/or modify
                it under the terms of the GNU General Public License as published by...
            """,
            "BSD-3-Clause": """
                Redistribution and use in source and binary forms, with or without
                modification, are permitted provided that the following conditions are met...
            """
        }
        
        return license_templates.get(license_id, f"License: {license_id}").strip()
    
    def _get_license_type(self, license_id: str) -> LicenseType:
        """Get license type for given license ID."""
        copyleft_licenses = ["GPL-2.0", "GPL-3.0", "LGPL-2.1", "LGPL-3.0"]
        permissive_licenses = ["MIT", "Apache-2.0", "BSD-2-Clause", "BSD-3-Clause", "ISC"]
        public_domain = ["Unlicense", "CC0-1.0"]
        
        if license_id in copyleft_licenses:
            return LicenseType.COPYLEFT
        elif license_id in permissive_licenses:
            return LicenseType.PERMISSIVE
        elif license_id in public_domain:
            return LicenseType.PUBLIC_DOMAIN
        else:
            return LicenseType.UNKNOWN
    
    def generate_performance_test_projects(
        self, 
        sizes: List[str] = None
    ) -> Dict[str, Path]:
        """
        Generate test projects of different sizes for performance testing.
        
        Args:
            sizes: Project size categories to generate
            
        Returns:
            Dictionary mapping size to project path
        """
        if sizes is None:
            sizes = ["small", "medium", "large", "enterprise"]
        
        size_configs = {
            "small": {"packages": 10, "depth": 2, "files": 25},
            "medium": {"packages": 50, "depth": 4, "files": 150},
            "large": {"packages": 200, "depth": 6, "files": 500},
            "enterprise": {"packages": 1000, "depth": 8, "files": 2000}
        }
        
        projects = {}
        
        for size in sizes:
            config = size_configs.get(size, size_configs["medium"])
            project_dir = Path(tempfile.mkdtemp(prefix=f"sbom_test_{size}_"))
            
            # Generate dependency tree
            dependency_tree = self.generate_realistic_dependency_tree(
                complexity=size,
                ecosystem="npm"
            )
            
            # Create project structure
            self._create_project_structure(project_dir, config, dependency_tree)
            
            projects[size] = project_dir
        
        return projects
    
    def _create_project_structure(
        self, 
        project_dir: Path, 
        config: Dict[str, int], 
        dependency_tree: DependencyNode
    ):
        """Create realistic project structure with files."""
        # Create package.json
        package_json = {
            "name": f"test-project-{project_dir.name}",
            "version": "1.0.0",
            "description": f"Performance test project with {config['packages']} packages",
            "dependencies": {},
            "devDependencies": {}
        }
        
        # Add dependencies from tree
        def extract_deps(node, is_dev=False):
            target = package_json["devDependencies"] if is_dev else package_json["dependencies"]
            target[node.name] = f"^{node.version}"
            
            for i, child in enumerate(node.children):
                extract_deps(child, is_dev=(i % 4 == 0))  # 25% dev dependencies
        
        extract_deps(dependency_tree)
        
        with open(project_dir / "package.json", "w") as f:
            json.dump(package_json, f, indent=2)
        
        # Create source files
        src_dir = project_dir / "src"
        src_dir.mkdir()
        
        for i in range(config["files"]):
            file_content = f"""
                // Generated file {i}
                const dependency{i} = require('{dependency_tree.name}');
                
                function process{i}() {{
                    return dependency{i}.process();
                }}
                
                module.exports = {{ process{i} }};
            """
            
            with open(src_dir / f"module{i}.js", "w") as f:
                f.write(file_content.strip())
        
        # Create test files
        test_dir = project_dir / "test"
        test_dir.mkdir()
        
        for i in range(config["files"] // 4):  # 25% test coverage
            test_content = f"""
                const {{ process{i} }} = require('../src/module{i}');
                
                describe('Module {i}', () => {{
                    test('processes correctly', () => {{
                        expect(process{i}()).toBeDefined();
                    }});
                }});
            """
            
            with open(test_dir / f"module{i}.test.js", "w") as f:
                f.write(test_content.strip())
    
    def generate_sbom_formats_suite(self, dependency_tree: DependencyNode) -> Dict[SBOMFormat, str]:
        """
        Generate SBOM in all supported formats for testing.
        
        Args:
            dependency_tree: Dependency tree to convert
            
        Returns:
            Dictionary mapping format to SBOM content
        """
        formats = {}
        
        # Generate SPDX formats
        spdx_json = create_sample_sbom(SBOMFormat.SPDX_JSON, dependency_tree)
        formats[SBOMFormat.SPDX_JSON] = spdx_json
        
        # Convert JSON to YAML
        spdx_data = json.loads(spdx_json)
        formats[SBOMFormat.SPDX_YAML] = yaml.dump(spdx_data, default_flow_style=False)
        
        # Generate SPDX Tag-Value format
        formats[SBOMFormat.SPDX_TAG_VALUE] = self._generate_spdx_tag_value(spdx_data)
        
        # Generate SPDX RDF/XML format
        formats[SBOMFormat.SPDX_RDF_XML] = self._generate_spdx_rdf_xml(spdx_data)
        
        # Generate CycloneDX formats
        cyclonedx_json = create_sample_sbom(SBOMFormat.CYCLONE_DX_JSON, dependency_tree)
        formats[SBOMFormat.CYCLONE_DX_JSON] = cyclonedx_json
        
        # Convert CycloneDX JSON to XML
        cyclonedx_data = json.loads(cyclonedx_json)
        formats[SBOMFormat.CYCLONE_DX_XML] = self._generate_cyclonedx_xml(cyclonedx_data)
        
        return formats
    
    def _generate_spdx_tag_value(self, spdx_data: Dict[str, Any]) -> str:
        """Generate SPDX Tag-Value format from JSON data."""
        lines = []
        
        # Document level
        lines.append(f"SPDXVersion: {spdx_data.get('spdxVersion', 'SPDX-2.3')}")
        lines.append(f"DataLicense: {spdx_data.get('dataLicense', 'CC0-1.0')}")
        lines.append(f"SPDXID: {spdx_data.get('SPDXID', 'SPDXRef-DOCUMENT')}")
        lines.append(f"DocumentName: {spdx_data.get('documentName', 'Test Document')}")
        lines.append(f"DocumentNamespace: {spdx_data.get('documentNamespace', 'https://example.com')}")
        
        # Creation info
        creation_info = spdx_data.get('creationInfo', {})
        lines.append(f"CreatedBy: {', '.join(creation_info.get('creators', ['Tool: SBOM-Test']))}")
        lines.append(f"Created: {creation_info.get('created', datetime.now().isoformat())}")
        
        # Packages
        for package in spdx_data.get('packages', []):
            lines.append("")  # Empty line between packages
            lines.append(f"PackageName: {package.get('name', 'Unknown')}")
            lines.append(f"SPDXID: {package.get('SPDXID', 'SPDXRef-Package')}")
            lines.append(f"PackageVersion: {package.get('versionInfo', 'Unknown')}")
            lines.append(f"PackageDownloadLocation: {package.get('downloadLocation', 'NOASSERTION')}")
            lines.append(f"FilesAnalyzed: {str(package.get('filesAnalyzed', False)).lower()}")
            lines.append(f"PackageLicenseConcluded: {package.get('licenseConcluded', 'NOASSERTION')}")
            lines.append(f"PackageLicenseDeclared: {package.get('licenseDeclared', 'NOASSERTION')}")
            lines.append(f"PackageCopyrightText: {package.get('copyrightText', 'NOASSERTION')}")
        
        return "\n".join(lines)
    
    def _generate_spdx_rdf_xml(self, spdx_data: Dict[str, Any]) -> str:
        """Generate SPDX RDF/XML format from JSON data."""
        # Simplified RDF/XML generation
        return f'''<?xml version="1.0" encoding="UTF-8"?>
<rdf:RDF
    xmlns:spdx="http://spdx.org/rdf/terms#"
    xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"
    xmlns:rdfs="http://www.w3.org/2000/01/rdf-schema#">
    
    <spdx:SpdxDocument rdf:about="{spdx_data.get('documentNamespace', 'https://example.com')}">
        <spdx:spdxVersion>{spdx_data.get('spdxVersion', 'SPDX-2.3')}</spdx:spdxVersion>
        <spdx:dataLicense>{spdx_data.get('dataLicense', 'CC0-1.0')}</spdx:dataLicense>
        <spdx:name>{spdx_data.get('documentName', 'Test Document')}</spdx:name>
        <spdx:spdxId>{spdx_data.get('SPDXID', 'SPDXRef-DOCUMENT')}</spdx:spdxId>
    </spdx:SpdxDocument>
    
</rdf:RDF>'''
    
    def _generate_cyclonedx_xml(self, cyclonedx_data: Dict[str, Any]) -> str:
        """Generate CycloneDX XML format from JSON data."""
        # Create XML structure
        bom = ET.Element("bom")
        bom.set("xmlns", "http://cyclonedx.org/schema/bom/1.4")
        bom.set("serialNumber", cyclonedx_data.get("serialNumber", "urn:uuid:" + str(uuid.uuid4())))
        bom.set("version", str(cyclonedx_data.get("version", 1)))
        
        # Metadata
        if "metadata" in cyclonedx_data:
            metadata = ET.SubElement(bom, "metadata")
            if "timestamp" in cyclonedx_data["metadata"]:
                timestamp = ET.SubElement(metadata, "timestamp")
                timestamp.text = cyclonedx_data["metadata"]["timestamp"]
        
        # Components
        if "components" in cyclonedx_data:
            components = ET.SubElement(bom, "components")
            for comp_data in cyclonedx_data["components"]:
                component = ET.SubElement(components, "component")
                component.set("type", comp_data.get("type", "library"))
                
                name = ET.SubElement(component, "name")
                name.text = comp_data.get("name", "Unknown")
                
                if "version" in comp_data:
                    version = ET.SubElement(component, "version")
                    version.text = comp_data["version"]
        
        return ET.tostring(bom, encoding="unicode", xml_declaration=True)
    
    def cleanup_test_projects(self, projects: Dict[str, Path]):
        """Clean up generated test projects."""
        import shutil
        
        for size, project_path in projects.items():
            if project_path.exists():
                shutil.rmtree(project_path)