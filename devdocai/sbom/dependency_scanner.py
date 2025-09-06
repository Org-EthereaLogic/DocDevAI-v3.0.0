"""
Dependency Scanner Component
Scans project for dependencies across multiple package managers
"""

import json
import subprocess
from pathlib import Path
from typing import List, Dict, Any, Optional
import re
import toml


class DependencyScanner:
    """
    Scans projects for dependencies across various package managers
    Supports: pip, npm, cargo, maven, gradle, go.mod
    """
    
    def __init__(self):
        """Initialize dependency scanner"""
        self.supported_ecosystems = {
            'python': self._scan_python,
            'nodejs': self._scan_nodejs,
            'rust': self._scan_rust,
            'java': self._scan_java,
            'go': self._scan_go
        }
        
    def scan_project(self, project_path: str) -> List:
        """
        Scan project directory for all dependencies
        
        Args:
            project_path: Path to project root
            
        Returns:
            List of Component objects representing dependencies
        """
        from .sbom_generator import Component
        
        project_path = Path(project_path)
        all_dependencies = []
        
        # Detect and scan each ecosystem
        for ecosystem, scanner_func in self.supported_ecosystems.items():
            if self._detect_ecosystem(project_path, ecosystem):
                print(f"  Detected {ecosystem} project...")
                deps = scanner_func(project_path)
                all_dependencies.extend(deps)
                
        # Remove duplicates based on name and version
        seen = set()
        unique_deps = []
        for dep in all_dependencies:
            key = (dep.name, dep.version)
            if key not in seen:
                seen.add(key)
                unique_deps.append(dep)
                
        return unique_deps
        
    def _detect_ecosystem(self, project_path: Path, ecosystem: str) -> bool:
        """
        Detect if project uses a specific ecosystem
        
        Args:
            project_path: Project root path
            ecosystem: Ecosystem to check for
            
        Returns:
            True if ecosystem detected
        """
        ecosystem_files = {
            'python': ['requirements.txt', 'Pipfile', 'pyproject.toml', 'setup.py'],
            'nodejs': ['package.json', 'package-lock.json', 'yarn.lock'],
            'rust': ['Cargo.toml', 'Cargo.lock'],
            'java': ['pom.xml', 'build.gradle', 'build.gradle.kts'],
            'go': ['go.mod', 'go.sum']
        }
        
        if ecosystem not in ecosystem_files:
            return False
            
        for file_name in ecosystem_files[ecosystem]:
            if (project_path / file_name).exists():
                return True
                
        return False
        
    def _scan_python(self, project_path: Path) -> List:
        """Scan Python dependencies"""
        from .sbom_generator import Component
        
        dependencies = []
        
        # Try requirements.txt first
        req_file = project_path / 'requirements.txt'
        if req_file.exists():
            with open(req_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        # Parse requirement line
                        match = re.match(r'^([a-zA-Z0-9-_.]+)\s*([><=!~]+)?\s*([0-9.a-zA-Z-]*)', line)
                        if match:
                            name = match.group(1)
                            version = match.group(3) if match.group(3) else 'unknown'
                            dependencies.append(Component(
                                name=name,
                                version=version,
                                purl=f"pkg:pypi/{name}@{version}"
                            ))
                            
        # Try pyproject.toml
        pyproject = project_path / 'pyproject.toml'
        if pyproject.exists():
            try:
                data = toml.load(pyproject)
                # Check for dependencies in different sections
                for section in ['dependencies', 'project.dependencies', 'tool.poetry.dependencies']:
                    deps = self._get_nested_value(data, section.split('.'))
                    if deps and isinstance(deps, dict):
                        for name, version_spec in deps.items():
                            if name == 'python':
                                continue
                            version = self._extract_version(version_spec)
                            dependencies.append(Component(
                                name=name,
                                version=version,
                                purl=f"pkg:pypi/{name}@{version}"
                            ))
            except Exception as e:
                print(f"    Warning: Could not parse pyproject.toml: {e}")
                
        return dependencies
        
    def _scan_nodejs(self, project_path: Path) -> List:
        """Scan Node.js dependencies"""
        from .sbom_generator import Component
        
        dependencies = []
        package_json = project_path / 'package.json'
        
        if package_json.exists():
            try:
                with open(package_json, 'r') as f:
                    data = json.load(f)
                    
                for dep_type in ['dependencies', 'devDependencies', 'peerDependencies']:
                    if dep_type in data:
                        for name, version_spec in data[dep_type].items():
                            version = self._extract_version(version_spec)
                            dependencies.append(Component(
                                name=name,
                                version=version,
                                purl=f"pkg:npm/{name}@{version}"
                            ))
            except Exception as e:
                print(f"    Warning: Could not parse package.json: {e}")
                
        return dependencies
        
    def _scan_rust(self, project_path: Path) -> List:
        """Scan Rust dependencies"""
        from .sbom_generator import Component
        
        dependencies = []
        cargo_toml = project_path / 'Cargo.toml'
        
        if cargo_toml.exists():
            try:
                data = toml.load(cargo_toml)
                
                for dep_type in ['dependencies', 'dev-dependencies', 'build-dependencies']:
                    if dep_type in data:
                        for name, version_spec in data[dep_type].items():
                            version = self._extract_version(version_spec)
                            dependencies.append(Component(
                                name=name,
                                version=version,
                                purl=f"pkg:cargo/{name}@{version}"
                            ))
            except Exception as e:
                print(f"    Warning: Could not parse Cargo.toml: {e}")
                
        return dependencies
        
    def _scan_java(self, project_path: Path) -> List:
        """Scan Java dependencies (Maven/Gradle)"""
        from .sbom_generator import Component
        
        dependencies = []
        
        # Try Maven pom.xml
        pom_xml = project_path / 'pom.xml'
        if pom_xml.exists():
            try:
                import xml.etree.ElementTree as ET
                tree = ET.parse(pom_xml)
                root = tree.getroot()
                
                # Extract namespace
                ns = {'maven': 'http://maven.apache.org/POM/4.0.0'}
                
                # Find dependencies
                for dep in root.findall('.//maven:dependency', ns):
                    group_id = dep.find('maven:groupId', ns)
                    artifact_id = dep.find('maven:artifactId', ns)
                    version = dep.find('maven:version', ns)
                    
                    if group_id is not None and artifact_id is not None:
                        name = f"{group_id.text}:{artifact_id.text}"
                        ver = version.text if version is not None else 'unknown'
                        dependencies.append(Component(
                            name=name,
                            version=ver,
                            purl=f"pkg:maven/{group_id.text}/{artifact_id.text}@{ver}"
                        ))
            except Exception as e:
                print(f"    Warning: Could not parse pom.xml: {e}")
                
        # Try Gradle build.gradle
        build_gradle = project_path / 'build.gradle'
        if build_gradle.exists():
            # Simple regex-based parsing for Gradle
            try:
                with open(build_gradle, 'r') as f:
                    content = f.read()
                    
                # Match dependencies like: implementation 'group:artifact:version'
                pattern = r"(?:implementation|compile|api|testImplementation)\s+['\"]([^:]+):([^:]+):([^'\"]+)['\"]"
                matches = re.findall(pattern, content)
                
                for group, artifact, version in matches:
                    name = f"{group}:{artifact}"
                    dependencies.append(Component(
                        name=name,
                        version=version,
                        purl=f"pkg:maven/{group}/{artifact}@{version}"
                    ))
            except Exception as e:
                print(f"    Warning: Could not parse build.gradle: {e}")
                
        return dependencies
        
    def _scan_go(self, project_path: Path) -> List:
        """Scan Go dependencies"""
        from .sbom_generator import Component
        
        dependencies = []
        go_mod = project_path / 'go.mod'
        
        if go_mod.exists():
            try:
                with open(go_mod, 'r') as f:
                    in_require = False
                    for line in f:
                        line = line.strip()
                        
                        if line == 'require (':
                            in_require = True
                            continue
                        elif line == ')':
                            in_require = False
                            continue
                            
                        if in_require or line.startswith('require '):
                            # Parse require line
                            parts = line.replace('require ', '').split()
                            if len(parts) >= 2:
                                name = parts[0]
                                version = parts[1]
                                dependencies.append(Component(
                                    name=name,
                                    version=version,
                                    purl=f"pkg:golang/{name}@{version}"
                                ))
            except Exception as e:
                print(f"    Warning: Could not parse go.mod: {e}")
                
        return dependencies
        
    def _extract_version(self, version_spec: Any) -> str:
        """
        Extract version from various version specification formats
        
        Args:
            version_spec: Version specification (string or dict)
            
        Returns:
            Extracted version string
        """
        if isinstance(version_spec, str):
            # Remove version operators
            version = re.sub(r'^[~^>=<]+', '', version_spec)
            return version if version else 'unknown'
        elif isinstance(version_spec, dict):
            # Handle poetry/cargo style specifications
            if 'version' in version_spec:
                return self._extract_version(version_spec['version'])
            elif 'git' in version_spec:
                return version_spec.get('rev', version_spec.get('tag', 'git'))
            else:
                return 'unknown'
        else:
            return 'unknown'
            
    def _get_nested_value(self, data: Dict, keys: List[str]) -> Any:
        """
        Get nested value from dictionary
        
        Args:
            data: Dictionary to search
            keys: List of keys to traverse
            
        Returns:
            Value at nested location or None
        """
        current = data
        for key in keys:
            if isinstance(current, dict) and key in current:
                current = current[key]
            else:
                return None
        return current