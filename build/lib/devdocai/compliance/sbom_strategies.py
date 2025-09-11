"""
M010 SBOM Generator - Strategies Module
DevDocAI v3.0.0 - Strategy patterns for package scanning and format building

This module implements the Strategy pattern for extensible package scanning
across different package managers and SBOM format generation.
"""

import hashlib
import json
import logging
import re
import xml.etree.ElementTree as ET
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from pathlib import Path
from typing import List

from .sbom_types import SBOM, Package, Relationship, SBOMFormat

logger = logging.getLogger(__name__)


# ============================================================================
# Package Scanner Strategy
# ============================================================================


class PackageScannerStrategy(ABC):
    """Abstract base class for package scanning strategies."""

    @abstractmethod
    def scan(self, project_path: Path) -> List[Package]:
        """Scan for packages in the project."""
        pass

    @abstractmethod
    def supports(self, project_path: Path) -> bool:
        """Check if this scanner supports the project."""
        pass


class PythonPackageScanner(PackageScannerStrategy):
    """Scanner for Python packages."""

    def scan(self, project_path: Path) -> List[Package]:
        """Scan Python dependencies."""
        packages = []

        # Check requirements.txt
        req_file = project_path / "requirements.txt"
        if req_file.exists():
            logger.debug("Scanning requirements.txt")
            packages.extend(self._parse_requirements_txt(req_file))

        # Check pyproject.toml
        pyproject_file = project_path / "pyproject.toml"
        if pyproject_file.exists():
            logger.debug("Scanning pyproject.toml")
            packages.extend(self._parse_pyproject_toml(pyproject_file))

        # Check Pipfile
        pipfile = project_path / "Pipfile"
        if pipfile.exists():
            logger.debug("Scanning Pipfile")
            packages.extend(self._parse_pipfile(pipfile))

        return packages

    def supports(self, project_path: Path) -> bool:
        """Check if Python project."""
        return any(
            [
                (project_path / "requirements.txt").exists(),
                (project_path / "pyproject.toml").exists(),
                (project_path / "Pipfile").exists(),
                (project_path / "setup.py").exists(),
            ]
        )

    def _parse_requirements_txt(self, file_path: Path) -> List[Package]:
        """Parse requirements.txt file."""
        packages = []

        try:
            with open(file_path, encoding="utf-8") as f:
                for line_num, line in enumerate(f, 1):
                    if line_num > 10000:  # Limit lines to prevent DoS
                        break

                    line = line.strip()
                    if line and not line.startswith("#"):
                        # Parse package==version format
                        match = re.match(r"^([a-zA-Z0-9\-_]+)(?:==|>=|<=|>|<|~=)(.+)$", line)
                        if match:
                            name, version = match.groups()
                            packages.append(
                                Package(
                                    name=name,
                                    version=version,
                                    purl=f"pkg:pypi/{name}@{version}",
                                )
                            )
        except Exception as e:
            logger.error(f"Error parsing requirements.txt: {e}")

        return packages

    def _parse_pyproject_toml(self, file_path: Path) -> List[Package]:
        """Parse pyproject.toml file."""
        packages = []
        try:
            import tomli

            with open(file_path, "rb") as f:
                data = tomli.load(f)

            # Check poetry dependencies
            if "tool" in data and "poetry" in data["tool"]:
                deps = data["tool"]["poetry"].get("dependencies", {})
                for name, spec in deps.items():
                    if name != "python":  # Skip Python version constraint
                        if isinstance(spec, str):
                            version = spec.strip("^~")
                            packages.append(
                                Package(
                                    name=name,
                                    version=version,
                                    purl=f"pkg:pypi/{name}@{version}",
                                )
                            )
                        elif isinstance(spec, dict):
                            version = spec.get("version", "*").strip("^~")
                            packages.append(
                                Package(
                                    name=name,
                                    version=version,
                                    purl=f"pkg:pypi/{name}@{version}",
                                )
                            )

            # Check setuptools dependencies
            if "project" in data:
                deps = data["project"].get("dependencies", [])
                for dep in deps:
                    match = re.match(r"^([a-zA-Z0-9\-_]+)(?:\[.*\])?(?:==|>=|<=|>|<|~=)(.+)$", dep)
                    if match:
                        name, version = match.groups()
                        packages.append(
                            Package(
                                name=name,
                                version=version,
                                purl=f"pkg:pypi/{name}@{version}",
                            )
                        )
        except ImportError:
            logger.warning("tomli not installed, skipping pyproject.toml parsing")
        except Exception as e:
            logger.error(f"Error parsing pyproject.toml: {e}")

        return packages

    def _parse_pipfile(self, file_path: Path) -> List[Package]:
        """Parse Pipfile."""
        packages = []
        try:
            import tomli

            with open(file_path, "rb") as f:
                data = tomli.load(f)

            for section in ["packages", "dev-packages"]:
                if section in data:
                    for name, spec in data[section].items():
                        if isinstance(spec, str):
                            version = spec.strip("=")
                        elif isinstance(spec, dict) and "version" in spec:
                            version = spec["version"].strip("=")
                        else:
                            version = "*"

                        packages.append(
                            Package(
                                name=name,
                                version=version,
                                purl=f"pkg:pypi/{name}@{version}",
                            )
                        )
        except ImportError:
            logger.warning("tomli not installed, skipping Pipfile parsing")
        except Exception as e:
            logger.error(f"Error parsing Pipfile: {e}")

        return packages


class NodePackageScanner(PackageScannerStrategy):
    """Scanner for Node.js packages."""

    def scan(self, project_path: Path) -> List[Package]:
        """Scan Node.js dependencies."""
        packages = []

        # Check package-lock.json (preferred for accuracy)
        lock_file = project_path / "package-lock.json"
        if lock_file.exists():
            logger.debug("Scanning package-lock.json")
            try:
                with open(lock_file, encoding="utf-8") as f:
                    data = json.load(f)
                    if "packages" in data:
                        for path, info in data["packages"].items():
                            if path and "node_modules/" in path:
                                name = path.split("node_modules/")[-1]
                                version = info.get("version", "unknown")
                                packages.append(
                                    Package(
                                        name=name,
                                        version=version,
                                        purl=f"pkg:npm/{name}@{version}",
                                    )
                                )
            except Exception as e:
                logger.error(f"Error parsing package-lock.json: {e}")

        # Fallback to package.json
        elif (project_path / "package.json").exists():
            logger.debug("Scanning package.json")
            try:
                with open(project_path / "package.json", encoding="utf-8") as f:
                    data = json.load(f)
                    for dep_type in ["dependencies", "devDependencies"]:
                        if dep_type in data:
                            for name, version in data[dep_type].items():
                                packages.append(
                                    Package(
                                        name=name,
                                        version=version.strip("^~"),
                                        purl=f"pkg:npm/{name}@{version.strip('^~')}",
                                    )
                                )
            except Exception as e:
                logger.error(f"Error parsing package.json: {e}")

        return packages

    def supports(self, project_path: Path) -> bool:
        """Check if Node.js project."""
        return any(
            [
                (project_path / "package.json").exists(),
                (project_path / "package-lock.json").exists(),
                (project_path / "yarn.lock").exists(),
            ]
        )


class JavaPackageScanner(PackageScannerStrategy):
    """Scanner for Java packages."""

    def scan(self, project_path: Path) -> List[Package]:
        """Scan Java dependencies (Maven/Gradle)."""
        packages = []

        # Check pom.xml (Maven)
        pom_file = project_path / "pom.xml"
        if pom_file.exists():
            logger.debug("Scanning pom.xml")
            try:
                tree = ET.parse(pom_file)
                root = tree.getroot()
                ns = {"m": "http://maven.apache.org/POM/4.0.0"}

                for dep in root.findall(".//m:dependency", ns):
                    group_id = dep.find("m:groupId", ns)
                    artifact_id = dep.find("m:artifactId", ns)
                    version = dep.find("m:version", ns)

                    if group_id is not None and artifact_id is not None:
                        name = f"{group_id.text}:{artifact_id.text}"
                        ver = version.text if version is not None else "unknown"
                        packages.append(
                            Package(
                                name=name,
                                version=ver,
                                purl=f"pkg:maven/{group_id.text}/{artifact_id.text}@{ver}",
                            )
                        )
            except Exception as e:
                logger.error(f"Error parsing pom.xml: {e}")

        # Check build.gradle (Gradle)
        gradle_file = project_path / "build.gradle"
        if gradle_file.exists():
            logger.debug("Scanning build.gradle")
            # Gradle parsing is complex, would need gradle wrapper execution
            logger.warning("Gradle scanning not fully implemented")

        return packages

    def supports(self, project_path: Path) -> bool:
        """Check if Java project."""
        return any(
            [
                (project_path / "pom.xml").exists(),
                (project_path / "build.gradle").exists(),
                (project_path / "build.gradle.kts").exists(),
            ]
        )


class DotNetPackageScanner(PackageScannerStrategy):
    """Scanner for .NET packages."""

    def scan(self, project_path: Path) -> List[Package]:
        """Scan .NET dependencies."""
        packages = []

        # Check *.csproj files
        for csproj in project_path.glob("**/*.csproj"):
            logger.debug(f"Scanning {csproj}")
            try:
                tree = ET.parse(csproj)
                root = tree.getroot()

                for ref in root.findall(".//PackageReference"):
                    name = ref.get("Include")
                    version = ref.get("Version")
                    if name and version:
                        packages.append(
                            Package(
                                name=name,
                                version=version,
                                purl=f"pkg:nuget/{name}@{version}",
                            )
                        )
            except Exception as e:
                logger.error(f"Error parsing {csproj}: {e}")

        return packages

    def supports(self, project_path: Path) -> bool:
        """Check if .NET project."""
        return any(
            [
                list(project_path.glob("**/*.csproj")),
                list(project_path.glob("**/*.vbproj")),
                list(project_path.glob("**/*.fsproj")),
            ]
        )


class GoPackageScanner(PackageScannerStrategy):
    """Scanner for Go packages."""

    def scan(self, project_path: Path) -> List[Package]:
        """Scan Go dependencies."""
        packages = []

        go_mod = project_path / "go.mod"
        if go_mod.exists():
            logger.debug("Scanning go.mod")
            try:
                with open(go_mod, encoding="utf-8") as f:
                    in_require = False
                    for line in f:
                        line = line.strip()
                        if line == "require (":
                            in_require = True
                        elif line == ")":
                            in_require = False
                        elif in_require and line:
                            parts = line.split()
                            if len(parts) >= 2:
                                name = parts[0]
                                version = parts[1]
                                packages.append(
                                    Package(
                                        name=name,
                                        version=version,
                                        purl=f"pkg:golang/{name}@{version}",
                                    )
                                )
            except Exception as e:
                logger.error(f"Error parsing go.mod: {e}")

        return packages

    def supports(self, project_path: Path) -> bool:
        """Check if Go project."""
        return any(
            [
                (project_path / "go.mod").exists(),
                (project_path / "go.sum").exists(),
            ]
        )


class RustPackageScanner(PackageScannerStrategy):
    """Scanner for Rust packages."""

    def scan(self, project_path: Path) -> List[Package]:
        """Scan Rust dependencies."""
        packages = []

        cargo_lock = project_path / "Cargo.lock"
        if cargo_lock.exists():
            logger.debug("Scanning Cargo.lock")
            try:
                import tomli

                with open(cargo_lock, "rb") as f:
                    data = tomli.load(f)

                for package in data.get("package", []):
                    name = package.get("name")
                    version = package.get("version")
                    if name and version:
                        packages.append(
                            Package(
                                name=name,
                                version=version,
                                purl=f"pkg:cargo/{name}@{version}",
                            )
                        )
            except ImportError:
                logger.warning("tomli not installed, skipping Cargo.lock parsing")
            except Exception as e:
                logger.error(f"Error parsing Cargo.lock: {e}")

        return packages

    def supports(self, project_path: Path) -> bool:
        """Check if Rust project."""
        return any(
            [
                (project_path / "Cargo.toml").exists(),
                (project_path / "Cargo.lock").exists(),
            ]
        )


# ============================================================================
# Format Builder Strategy
# ============================================================================


class FormatBuilderStrategy(ABC):
    """Abstract base class for SBOM format building strategies."""

    @abstractmethod
    def build(self, project_path: Path, packages: List[Package], vulnerabilities: List) -> SBOM:
        """Build SBOM in specific format."""
        pass


class SPDXFormatBuilder(FormatBuilderStrategy):
    """Builder for SPDX 2.3 format."""

    def build(self, project_path: Path, packages: List[Package], vulnerabilities: List) -> SBOM:
        """Build SPDX 2.3 format SBOM."""
        # Generate document namespace
        timestamp = datetime.now(timezone.utc).isoformat()
        namespace = f"https://devdocai.com/spdxdocs/{project_path.name}-{timestamp}"

        # Build relationships
        relationships = []
        doc_spdx_id = "SPDXRef-DOCUMENT"

        for i, package in enumerate(packages):
            pkg_spdx_id = f"SPDXRef-Package-{i}"
            relationships.append(
                Relationship(
                    source=doc_spdx_id,
                    target=pkg_spdx_id,
                    relationship_type="DESCRIBES",
                )
            )

            # Add dependency relationships
            for dep in package.dependencies:
                dep_idx = next(
                    (j for j, p in enumerate(packages) if p.name == dep),
                    None,
                )
                if dep_idx is not None:
                    relationships.append(
                        Relationship(
                            source=pkg_spdx_id,
                            target=f"SPDXRef-Package-{dep_idx}",
                            relationship_type="DEPENDS_ON",
                        )
                    )

        return SBOM(
            format=SBOMFormat.SPDX,
            spec_version="SPDX-2.3",
            created=datetime.now(timezone.utc),
            creator="DevDocAI SBOM Generator",
            document_namespace=namespace,
            name=f"{project_path.name}-sbom",
            packages=packages,
            relationships=relationships,
            vulnerabilities=vulnerabilities,
            metadata={
                "spdxVersion": "SPDX-2.3",
                "dataLicense": "CC0-1.0",
                "SPDXID": doc_spdx_id,
                "documentName": f"{project_path.name} Software Bill of Materials",
                "documentNamespace": namespace,
                "creatorComment": "Generated by DevDocAI v3.0.0",
            },
        )


class CycloneDXFormatBuilder(FormatBuilderStrategy):
    """Builder for CycloneDX 1.4 format."""

    def build(self, project_path: Path, packages: List[Package], vulnerabilities: List) -> SBOM:
        """Build CycloneDX 1.4 format SBOM."""
        # Build dependency graph
        dependencies = {}
        for package in packages:
            if package.dependencies:
                dependencies[package.name] = package.dependencies

        return SBOM(
            format=SBOMFormat.CYCLONEDX,
            spec_version="1.4",
            created=datetime.now(timezone.utc),
            creator="DevDocAI SBOM Generator",
            document_namespace=f"urn:uuid:{project_path.name}-{datetime.now().isoformat()}",
            name=f"{project_path.name}-sbom",
            packages=packages,
            relationships=[],  # CycloneDX uses different structure
            vulnerabilities=vulnerabilities,
            metadata={
                "bomFormat": "CycloneDX",
                "specVersion": "1.4",
                "serialNumber": f"urn:uuid:{hashlib.sha256(str(project_path).encode()).hexdigest()[:8]}",
                "version": 1,
                "metadata": {
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "tools": [
                        {
                            "vendor": "DevDocAI",
                            "name": "SBOM Generator",
                            "version": "3.0.0",
                        }
                    ],
                    "component": {
                        "type": "application",
                        "name": project_path.name,
                        "version": "1.0.0",
                    },
                },
                "dependencies": dependencies,
            },
        )


# ============================================================================
# Factory Classes
# ============================================================================


class PackageScannerFactory:
    """Factory for creating package scanners."""

    _scanners = [
        PythonPackageScanner(),
        NodePackageScanner(),
        JavaPackageScanner(),
        DotNetPackageScanner(),
        GoPackageScanner(),
        RustPackageScanner(),
    ]

    @classmethod
    def get_scanners(cls, project_path: Path) -> List[PackageScannerStrategy]:
        """Get all applicable scanners for a project."""
        return [s for s in cls._scanners if s.supports(project_path)]

    @classmethod
    def register_scanner(cls, scanner: PackageScannerStrategy):
        """Register a new scanner."""
        cls._scanners.append(scanner)


class FormatBuilderFactory:
    """Factory for creating format builders."""

    _builders = {
        SBOMFormat.SPDX: SPDXFormatBuilder(),
        SBOMFormat.CYCLONEDX: CycloneDXFormatBuilder(),
    }

    @classmethod
    def get_builder(cls, format: SBOMFormat) -> FormatBuilderStrategy:
        """Get builder for specified format."""
        if format not in cls._builders:
            raise ValueError(f"Unsupported SBOM format: {format}")
        return cls._builders[format]

    @classmethod
    def register_builder(cls, format: SBOMFormat, builder: FormatBuilderStrategy):
        """Register a new format builder."""
        cls._builders[format] = builder
