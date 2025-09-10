"""
Unit tests for M010 SBOM Generator - Pass 1: Core Implementation
DevDocAI v3.0.0

Test coverage targets:
    - 90% overall coverage for M010
    - 100% coverage for critical security functions
    - Comprehensive validation of all SBOM formats
"""

import json
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest
from cryptography.hazmat.primitives.asymmetric import ed25519

from devdocai.compliance.sbom import (
    SBOM,
    DependencyScanner,
    DependencyScanError,
    Ed25519Signer,
    LicenseDetector,
    LicenseInfo,
    Package,
    Relationship,
    SBOMError,
    SBOMFormat,
    SBOMGenerator,
    SBOMSignature,
    SignatureError,
    Vulnerability,
    VulnerabilityScanner,
)
from devdocai.core.config import ConfigurationManager


# ============================================================================
# Test Fixtures
# ============================================================================


@pytest.fixture
def mock_config():
    """Mock configuration manager."""
    config = MagicMock(spec=ConfigurationManager)
    # Set up nested attributes properly
    config.security = MagicMock()
    config.security.encryption_enabled = True
    return config


@pytest.fixture
def sample_package():
    """Sample package for testing."""
    return Package(
        name="test-package",
        version="1.0.0",
        purl="pkg:pypi/test-package@1.0.0",
        license=LicenseInfo(
            license_id="MIT",
            license_name="MIT License",
            is_osi_approved=True,
            is_deprecated=False,
        ),
    )


@pytest.fixture
def sample_vulnerability():
    """Sample vulnerability for testing."""
    return Vulnerability(
        cve_id="CVE-2021-12345",
        severity="HIGH",
        cvss_score=7.5,
        description="Test vulnerability",
        affected_versions=["1.0.0"],
        fixed_versions=["1.0.1"],
        published_date=datetime(2021, 1, 1, tzinfo=timezone.utc),
    )


@pytest.fixture
def temp_project_dir():
    """Create temporary project directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        project_path = Path(tmpdir)
        
        # Create sample project files
        (project_path / "requirements.txt").write_text(
            "flask==2.0.1\nrequests==2.26.0\nnumpy>=1.21.0\n"
        )
        
        (project_path / "package.json").write_text(
            json.dumps({
                "name": "test-project",
                "version": "1.0.0",
                "dependencies": {
                    "express": "^4.17.1",
                    "lodash": "~4.17.21",
                }
            })
        )
        
        yield project_path


# ============================================================================
# Test Data Models
# ============================================================================


class TestDataModels:
    """Test SBOM data models."""

    def test_license_info_model(self):
        """Test LicenseInfo model."""
        license_info = LicenseInfo(
            license_id="Apache-2.0",
            license_name="Apache License 2.0",
            is_osi_approved=True,
            is_deprecated=False,
        )
        
        assert license_info.license_id == "Apache-2.0"
        assert license_info.license_name == "Apache License 2.0"
        assert license_info.is_osi_approved is True
        assert license_info.is_deprecated is False

    def test_vulnerability_model(self, sample_vulnerability):
        """Test Vulnerability model."""
        assert sample_vulnerability.cve_id == "CVE-2021-12345"
        assert sample_vulnerability.severity == "HIGH"
        assert sample_vulnerability.cvss_score == 7.5
        assert len(sample_vulnerability.affected_versions) == 1
        assert len(sample_vulnerability.fixed_versions) == 1

    def test_package_model(self, sample_package):
        """Test Package model."""
        assert sample_package.name == "test-package"
        assert sample_package.version == "1.0.0"
        assert sample_package.purl == "pkg:pypi/test-package@1.0.0"
        assert sample_package.license.license_id == "MIT"

    def test_relationship_model(self):
        """Test Relationship model."""
        rel = Relationship(
            source="SPDXRef-DOCUMENT",
            target="SPDXRef-Package-0",
            relationship_type="DESCRIBES",
        )
        
        assert rel.source == "SPDXRef-DOCUMENT"
        assert rel.target == "SPDXRef-Package-0"
        assert rel.relationship_type == "DESCRIBES"

    def test_sbom_signature_model(self):
        """Test SBOMSignature model."""
        sig = SBOMSignature(
            algorithm="Ed25519",
            value="test-signature",
            public_key="test-public-key",
            timestamp=datetime.now(timezone.utc),
            signer="Test Signer",
        )
        
        assert sig.algorithm == "Ed25519"
        assert sig.value == "test-signature"
        assert sig.public_key == "test-public-key"
        assert sig.signer == "Test Signer"

    def test_sbom_model(self, sample_package):
        """Test SBOM model."""
        sbom = SBOM(
            format=SBOMFormat.SPDX,
            spec_version="SPDX-2.3",
            created=datetime.now(timezone.utc),
            creator="Test Creator",
            document_namespace="https://test.com/sbom",
            name="test-sbom",
            packages=[sample_package],
        )
        
        assert sbom.format == SBOMFormat.SPDX
        assert sbom.spec_version == "SPDX-2.3"
        assert sbom.creator == "Test Creator"
        assert len(sbom.packages) == 1
        assert sbom.packages[0].name == "test-package"


# ============================================================================
# Test Dependency Scanner
# ============================================================================


class TestDependencyScanner:
    """Test dependency scanner component."""

    def test_scan_project_python(self, temp_project_dir):
        """Test scanning Python dependencies."""
        scanner = DependencyScanner()
        packages = scanner.scan_project(temp_project_dir)
        
        # Should find packages from requirements.txt
        package_names = {p.name for p in packages}
        assert "flask" in package_names
        assert "requests" in package_names
        assert "numpy" in package_names
        
        # Check versions
        flask_pkg = next(p for p in packages if p.name == "flask")
        assert flask_pkg.version == "2.0.1"
        assert flask_pkg.purl == "pkg:pypi/flask@2.0.1"

    def test_scan_project_nodejs(self, temp_project_dir):
        """Test scanning Node.js dependencies."""
        scanner = DependencyScanner()
        packages = scanner.scan_project(temp_project_dir)
        
        # Should find packages from package.json
        package_names = {p.name for p in packages}
        assert "express" in package_names
        assert "lodash" in package_names
        
        # Check versions (stripped of version specifiers)
        express_pkg = next(p for p in packages if p.name == "express")
        assert express_pkg.version == "4.17.1"
        assert express_pkg.purl == "pkg:npm/express@4.17.1"

    def test_scan_project_pyproject_toml(self):
        """Test scanning pyproject.toml."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_path = Path(tmpdir)
            
            # Create pyproject.toml with Poetry dependencies
            pyproject_content = """
[tool.poetry.dependencies]
python = "^3.9"
django = "^4.0"
celery = {version = "^5.2", extras = ["redis"]}
            """
            (project_path / "pyproject.toml").write_text(pyproject_content)
            
            scanner = DependencyScanner()
            packages = scanner.scan_project(project_path)
            
            package_names = {p.name for p in packages}
            assert "django" in package_names
            assert "celery" in package_names
            assert "python" not in package_names  # Python version should be excluded

    def test_scan_project_pipfile(self):
        """Test scanning Pipfile."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_path = Path(tmpdir)
            
            # Create Pipfile
            pipfile_content = """
[packages]
fastapi = "==0.68.0"
uvicorn = "*"

[dev-packages]
pytest = "^6.2"
            """
            (project_path / "Pipfile").write_text(pipfile_content)
            
            scanner = DependencyScanner()
            packages = scanner.scan_project(project_path)
            
            package_names = {p.name for p in packages}
            assert "fastapi" in package_names
            assert "uvicorn" in package_names
            assert "pytest" in package_names

    def test_scan_project_maven(self):
        """Test scanning Maven pom.xml."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_path = Path(tmpdir)
            
            # Create pom.xml
            pom_content = """<?xml version="1.0" encoding="UTF-8"?>
<project xmlns="http://maven.apache.org/POM/4.0.0">
    <dependencies>
        <dependency>
            <groupId>org.springframework</groupId>
            <artifactId>spring-core</artifactId>
            <version>5.3.9</version>
        </dependency>
    </dependencies>
</project>
            """
            (project_path / "pom.xml").write_text(pom_content)
            
            scanner = DependencyScanner()
            packages = scanner.scan_project(project_path)
            
            # Should find Spring dependency
            assert any("spring-core" in p.name for p in packages)

    def test_scan_project_dotnet(self):
        """Test scanning .NET csproj files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_path = Path(tmpdir)
            
            # Create .csproj file
            csproj_content = """<?xml version="1.0" encoding="utf-8"?>
<Project Sdk="Microsoft.NET.Sdk">
    <ItemGroup>
        <PackageReference Include="Newtonsoft.Json" Version="13.0.1" />
        <PackageReference Include="Microsoft.Extensions.Logging" Version="5.0.0" />
    </ItemGroup>
</Project>
            """
            (project_path / "test.csproj").write_text(csproj_content)
            
            scanner = DependencyScanner()
            packages = scanner.scan_project(project_path)
            
            package_names = {p.name for p in packages}
            assert "Newtonsoft.Json" in package_names
            assert "Microsoft.Extensions.Logging" in package_names

    def test_scan_project_go(self):
        """Test scanning Go modules."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_path = Path(tmpdir)
            
            # Create go.mod
            go_mod_content = """module example.com/myapp

go 1.17

require (
    github.com/gin-gonic/gin v1.7.4
    github.com/go-redis/redis/v8 v8.11.3
)
            """
            (project_path / "go.mod").write_text(go_mod_content)
            
            scanner = DependencyScanner()
            packages = scanner.scan_project(project_path)
            
            package_names = {p.name for p in packages}
            assert "github.com/gin-gonic/gin" in package_names
            assert "github.com/go-redis/redis/v8" in package_names

    def test_scan_project_rust(self):
        """Test scanning Rust dependencies."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_path = Path(tmpdir)
            
            # Create Cargo.lock
            cargo_lock_content = """
[[package]]
name = "serde"
version = "1.0.130"

[[package]]
name = "tokio"
version = "1.12.0"
            """
            (project_path / "Cargo.lock").write_text(cargo_lock_content)
            
            scanner = DependencyScanner()
            packages = scanner.scan_project(project_path)
            
            package_names = {p.name for p in packages}
            assert "serde" in package_names
            assert "tokio" in package_names

    def test_scan_project_cache(self, temp_project_dir):
        """Test dependency scanner caching."""
        scanner = DependencyScanner()
        
        # First scan
        packages1 = scanner.scan_project(temp_project_dir)
        
        # Second scan should use cache
        with patch.object(scanner, "_scan_python", return_value=[]) as mock_scan:
            packages2 = scanner.scan_project(temp_project_dir)
            mock_scan.assert_not_called()  # Should not rescan
        
        assert packages1 == packages2

    def test_deduplicate_packages(self):
        """Test package deduplication."""
        scanner = DependencyScanner()
        
        packages = [
            Package(name="flask", version="2.0.1", purl="pkg:pypi/flask@2.0.1"),
            Package(name="flask", version="2.0.1", purl="pkg:pypi/flask@2.0.1"),  # Duplicate
            Package(name="requests", version="2.26.0", purl="pkg:pypi/requests@2.26.0"),
        ]
        
        unique = scanner._deduplicate_packages(packages)
        assert len(unique) == 2
        assert {p.name for p in unique} == {"flask", "requests"}


# ============================================================================
# Test License Detector
# ============================================================================


class TestLicenseDetector:
    """Test license detector component."""

    def test_detect_common_licenses(self):
        """Test detection of common licenses."""
        detector = LicenseDetector()
        
        # Test MIT license detection
        mit_package = Package(
            name="mit-package",
            version="1.0.0",
            purl="pkg:pypi/mit-licensed@1.0.0",
        )
        license_info = detector.detect(mit_package)
        assert license_info is not None
        assert license_info.license_id == "MIT"
        assert license_info.is_osi_approved is True

    def test_detect_from_purl(self):
        """Test license detection from package URL."""
        detector = LicenseDetector()
        
        # Apache license
        apache_pkg = Package(
            name="apache-pkg",
            version="1.0.0",
            purl="pkg:pypi/apache-commons@1.0.0",
        )
        license_info = detector.detect(apache_pkg)
        assert license_info is not None
        assert license_info.license_id == "Apache-2.0"
        
        # GPL license
        gpl_pkg = Package(
            name="gpl-pkg",
            version="1.0.0",
            purl="pkg:pypi/gpl-software@1.0.0",
        )
        license_info = detector.detect(gpl_pkg)
        assert license_info is not None
        assert license_info.license_id == "GPL-3.0"

    def test_detect_from_files(self):
        """Test license detection from local files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            pkg_path = Path(tmpdir)
            
            # Create LICENSE file with MIT content
            license_content = """
MIT License

Copyright (c) 2025 Test

Permission is hereby granted, free of charge...
            """
            (pkg_path / "LICENSE").write_text(license_content)
            
            detector = LicenseDetector()
            package = Package(
                name="test",
                version="1.0.0",
                file_path=pkg_path,
            )
            
            license_info = detector.detect(package)
            assert license_info is not None
            assert license_info.license_id == "MIT"

    def test_detect_apache_from_text(self):
        """Test Apache license detection from text."""
        detector = LicenseDetector()
        
        apache_text = """
Apache License
Version 2.0, January 2004
http://www.apache.org/licenses/
        """
        
        license_info = detector._identify_license_from_text(apache_text)
        assert license_info is not None
        assert license_info.license_id == "Apache-2.0"

    def test_detect_bsd_from_text(self):
        """Test BSD license detection from text."""
        detector = LicenseDetector()
        
        bsd_text = """
BSD 3-Clause License

Copyright (c) 2025, Test
        """
        
        license_info = detector._identify_license_from_text(bsd_text)
        assert license_info is not None
        assert license_info.license_id == "BSD-3-Clause"

    def test_detect_no_license(self):
        """Test when no license is detected."""
        detector = LicenseDetector()
        
        package = Package(
            name="unlicensed",
            version="1.0.0",
        )
        
        license_info = detector.detect(package)
        assert license_info is None

    def test_detect_cache(self):
        """Test license detection caching."""
        detector = LicenseDetector()
        
        package = Package(
            name="test",
            version="1.0.0",
            purl="pkg:pypi/mit-test@1.0.0",
        )
        
        # First detection
        license1 = detector.detect(package)
        
        # Second detection should use cache
        with patch.object(detector, "_detect_from_purl", return_value=None) as mock_detect:
            license2 = detector.detect(package)
            mock_detect.assert_not_called()
        
        assert license1 == license2


# ============================================================================
# Test Vulnerability Scanner
# ============================================================================


class TestVulnerabilityScanner:
    """Test vulnerability scanner component."""

    def test_scan_packages(self, sample_package):
        """Test scanning packages for vulnerabilities."""
        scanner = VulnerabilityScanner()
        
        packages = [sample_package]
        vulnerabilities = scanner.scan(packages)
        
        # Test package should have no vulnerabilities
        assert len(vulnerabilities) == 0
        assert len(sample_package.vulnerabilities) == 0

    def test_scan_vulnerable_package(self):
        """Test scanning known vulnerable package."""
        scanner = VulnerabilityScanner()
        
        # Create Log4j package (known vulnerable)
        log4j_pkg = Package(
            name="log4j",
            version="2.14.0",
            purl="pkg:maven/org.apache.logging.log4j/log4j-core@2.14.0",
        )
        
        packages = [log4j_pkg]
        vulnerabilities = scanner.scan(packages)
        
        # Should find Log4Shell vulnerability
        assert len(vulnerabilities) == 1
        assert vulnerabilities[0].cve_id == "CVE-2021-44228"
        assert vulnerabilities[0].severity == "CRITICAL"
        assert vulnerabilities[0].cvss_score == 10.0
        
        # Package should have vulnerability attached
        assert len(log4j_pkg.vulnerabilities) == 1

    def test_scan_cache(self):
        """Test vulnerability scanning cache."""
        scanner = VulnerabilityScanner()
        
        package = Package(name="test", version="1.0.0")
        
        # First scan
        vulns1 = scanner.scan([package])
        
        # Second scan should use cache
        with patch.object(scanner, "_scan_package", return_value=[]) as mock_scan:
            vulns2 = scanner.scan([package])
            mock_scan.assert_not_called()
        
        assert vulns1 == vulns2


# ============================================================================
# Test Ed25519 Signer
# ============================================================================


class TestEd25519Signer:
    """Test Ed25519 digital signer component."""

    def test_initialize_keys(self, mock_config):
        """Test key initialization."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Set HOME to temp directory
            with patch.dict("os.environ", {"HOME": tmpdir}):
                signer = Ed25519Signer(mock_config)
                
                # Should generate new keys
                assert signer._private_key is not None
                assert signer._public_key is not None
                
                # Key file should be created
                key_path = Path(tmpdir) / ".devdocai" / "sbom_signing_key.enc"
                assert key_path.exists()

    def test_load_existing_keys(self, mock_config):
        """Test loading existing keys."""
        with tempfile.TemporaryDirectory() as tmpdir:
            key_path = Path(tmpdir) / ".devdocai" / "sbom_signing_key.enc"
            key_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Generate and save a key
            private_key = ed25519.Ed25519PrivateKey.generate()
            from cryptography.hazmat.primitives import serialization
            
            pem = private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.OpenSSH,
                encryption_algorithm=serialization.NoEncryption(),
            )
            key_path.write_bytes(pem)
            
            # Load the key
            with patch.dict("os.environ", {"HOME": tmpdir}):
                signer = Ed25519Signer(mock_config)
                assert signer._private_key is not None

    def test_sign_data(self, mock_config):
        """Test signing data."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch.dict("os.environ", {"HOME": tmpdir}):
                signer = Ed25519Signer(mock_config)
                
                # Sign some data
                data = {"test": "data", "number": 123}
                signature = signer.sign(data)
                
                assert signature is not None
                assert isinstance(signature, str)
                assert len(signature) > 0

    def test_verify_signature(self, mock_config):
        """Test signature verification."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch.dict("os.environ", {"HOME": tmpdir}):
                signer = Ed25519Signer(mock_config)
                
                # Sign and verify
                data = {"test": "data"}
                signature = signer.sign(data)
                
                # Should verify successfully
                assert signer.verify(data, signature) is True
                
                # Modified data should fail verification
                modified_data = {"test": "modified"}
                assert signer.verify(modified_data, signature) is False
                
                # Invalid signature should fail
                assert signer.verify(data, "invalid-signature") is False

    def test_sign_basemodel(self, mock_config, sample_package):
        """Test signing Pydantic BaseModel."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch.dict("os.environ", {"HOME": tmpdir}):
                signer = Ed25519Signer(mock_config)
                
                signature = signer.sign(sample_package)
                assert signature is not None
                assert signer.verify(sample_package, signature) is True

    def test_get_public_key(self, mock_config):
        """Test getting public key."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch.dict("os.environ", {"HOME": tmpdir}):
                signer = Ed25519Signer(mock_config)
                
                public_key = signer.public_key
                assert public_key is not None
                assert isinstance(public_key, str)
                assert len(public_key) > 0

    def test_sign_without_key(self, mock_config):
        """Test signing without initialized key."""
        signer = Ed25519Signer(mock_config)
        signer._private_key = None
        
        with pytest.raises(SignatureError, match="Signing key not initialized"):
            signer.sign({"test": "data"})

    def test_verify_without_key(self, mock_config):
        """Test verifying without initialized key."""
        signer = Ed25519Signer(mock_config)
        signer._public_key = None
        
        with pytest.raises(RuntimeError, match="Public key not initialized"):
            signer.verify({"test": "data"}, "signature")


# ============================================================================
# Test SBOM Generator
# ============================================================================


class TestSBOMGenerator:
    """Test main SBOM generator."""

    def test_generate_spdx_sbom(self, temp_project_dir, mock_config):
        """Test generating SPDX format SBOM."""
        generator = SBOMGenerator(mock_config)
        
        sbom = generator.generate(
            project_path=temp_project_dir,
            format=SBOMFormat.SPDX,
            sign=False,
            scan_vulnerabilities=False,
        )
        
        assert sbom is not None
        assert sbom.format == SBOMFormat.SPDX
        assert sbom.spec_version == "SPDX-2.3"
        assert len(sbom.packages) > 0
        assert sbom.document_namespace.startswith("https://devdocai.com/spdxdocs/")
        assert sbom.signature is None  # Not signed

    def test_generate_cyclonedx_sbom(self, temp_project_dir, mock_config):
        """Test generating CycloneDX format SBOM."""
        generator = SBOMGenerator(mock_config)
        
        sbom = generator.generate(
            project_path=temp_project_dir,
            format=SBOMFormat.CYCLONEDX,
            sign=False,
            scan_vulnerabilities=False,
        )
        
        assert sbom is not None
        assert sbom.format == SBOMFormat.CYCLONEDX
        assert sbom.spec_version == "1.4"
        assert len(sbom.packages) > 0
        assert sbom.metadata["bomFormat"] == "CycloneDX"

    def test_generate_with_signature(self, temp_project_dir, mock_config):
        """Test generating signed SBOM."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch.dict("os.environ", {"HOME": tmpdir}):
                generator = SBOMGenerator(mock_config)
                
                sbom = generator.generate(
                    project_path=temp_project_dir,
                    format=SBOMFormat.SPDX,
                    sign=True,
                    scan_vulnerabilities=False,
                )
                
                assert sbom.signature is not None
                assert sbom.signature.algorithm == "Ed25519"
                assert sbom.signature.value is not None
                assert sbom.signature.public_key is not None

    def test_generate_with_vulnerabilities(self, mock_config):
        """Test generating SBOM with vulnerability scanning."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_path = Path(tmpdir)
            
            # Create project with vulnerable package
            (project_path / "pom.xml").write_text("""<?xml version="1.0"?>
<project xmlns="http://maven.apache.org/POM/4.0.0">
    <dependencies>
        <dependency>
            <groupId>org.apache.logging.log4j</groupId>
            <artifactId>log4j-core</artifactId>
            <version>2.14.0</version>
        </dependency>
    </dependencies>
</project>""")
            
            generator = SBOMGenerator(mock_config)
            sbom = generator.generate(
                project_path=project_path,
                format=SBOMFormat.SPDX,
                sign=False,
                scan_vulnerabilities=True,
            )
            
            # Should find vulnerability
            assert len(sbom.vulnerabilities) > 0
            assert any(v.cve_id == "CVE-2021-44228" for v in sbom.vulnerabilities)

    def test_generate_invalid_project_path(self, mock_config):
        """Test generating SBOM with invalid project path."""
        generator = SBOMGenerator(mock_config)
        
        with pytest.raises(ValueError, match="Project path does not exist"):
            generator.generate(
                project_path=Path("/nonexistent/path"),
                format=SBOMFormat.SPDX,
            )

    def test_generate_file_not_directory(self, mock_config):
        """Test generating SBOM with file instead of directory."""
        with tempfile.NamedTemporaryFile() as tmpfile:
            generator = SBOMGenerator(mock_config)
            
            with pytest.raises(ValueError, match="Project path is not a directory"):
                generator.generate(
                    project_path=Path(tmpfile.name),
                    format=SBOMFormat.SPDX,
                )

    def test_export_sbom(self, temp_project_dir, mock_config):
        """Test exporting SBOM to file."""
        generator = SBOMGenerator(mock_config)
        
        sbom = generator.generate(
            project_path=temp_project_dir,
            format=SBOMFormat.SPDX,
            sign=False,
        )
        
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tmpfile:
            output_path = Path(tmpfile.name)
            
            generator.export(sbom, output_path, pretty=True)
            
            # Verify file was created
            assert output_path.exists()
            
            # Verify content is valid JSON
            with open(output_path, "r") as f:
                data = json.load(f)
                assert data["format"] == "spdx-2.3"
                assert "packages" in data
            
            # Clean up
            output_path.unlink()

    def test_export_sbom_compact(self, temp_project_dir, mock_config):
        """Test exporting SBOM without pretty printing."""
        generator = SBOMGenerator(mock_config)
        
        sbom = generator.generate(
            project_path=temp_project_dir,
            format=SBOMFormat.CYCLONEDX,
            sign=False,
        )
        
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tmpfile:
            output_path = Path(tmpfile.name)
            
            generator.export(sbom, output_path, pretty=False)
            
            # Verify file was created
            assert output_path.exists()
            
            # Verify content is compact (no newlines in JSON)
            content = output_path.read_text()
            assert "\n" not in content[:-1]  # Except for final newline
            
            # Clean up
            output_path.unlink()

    def test_validate_valid_spdx(self, temp_project_dir, mock_config):
        """Test validating valid SPDX SBOM."""
        generator = SBOMGenerator(mock_config)
        
        sbom = generator.generate(
            project_path=temp_project_dir,
            format=SBOMFormat.SPDX,
            sign=False,
        )
        
        is_valid, errors = generator.validate(sbom)
        assert is_valid is True
        assert len(errors) == 0

    def test_validate_valid_cyclonedx(self, temp_project_dir, mock_config):
        """Test validating valid CycloneDX SBOM."""
        generator = SBOMGenerator(mock_config)
        
        sbom = generator.generate(
            project_path=temp_project_dir,
            format=SBOMFormat.CYCLONEDX,
            sign=False,
        )
        
        is_valid, errors = generator.validate(sbom)
        assert is_valid is True
        assert len(errors) == 0

    def test_validate_invalid_sbom_no_packages(self, mock_config):
        """Test validating SBOM without packages."""
        generator = SBOMGenerator(mock_config)
        
        sbom = SBOM(
            format=SBOMFormat.SPDX,
            spec_version="SPDX-2.3",
            created=datetime.now(timezone.utc),
            creator="Test",
            document_namespace="https://test.com",
            name="test",
            packages=[],  # No packages
        )
        
        is_valid, errors = generator.validate(sbom)
        assert is_valid is False
        assert "SBOM must contain at least one package" in errors

    def test_validate_invalid_sbom_no_namespace(self, sample_package, mock_config):
        """Test validating SBOM without namespace."""
        generator = SBOMGenerator(mock_config)
        
        sbom = SBOM(
            format=SBOMFormat.SPDX,
            spec_version="SPDX-2.3",
            created=datetime.now(timezone.utc),
            creator="Test",
            document_namespace="",  # Empty namespace
            name="test",
            packages=[sample_package],
        )
        
        is_valid, errors = generator.validate(sbom)
        assert is_valid is False
        assert "SBOM must have a document namespace" in errors

    def test_validate_invalid_spdx_metadata(self, sample_package, mock_config):
        """Test validating SPDX SBOM with missing metadata."""
        generator = SBOMGenerator(mock_config)
        
        sbom = SBOM(
            format=SBOMFormat.SPDX,
            spec_version="SPDX-2.3",
            created=datetime.now(timezone.utc),
            creator="Test",
            document_namespace="https://test.com",
            name="test",
            packages=[sample_package],
            metadata={},  # Missing required metadata
        )
        
        is_valid, errors = generator.validate(sbom)
        assert is_valid is False
        assert any("spdxVersion" in error for error in errors)

    def test_validate_invalid_cyclonedx_metadata(self, sample_package, mock_config):
        """Test validating CycloneDX SBOM with missing metadata."""
        generator = SBOMGenerator(mock_config)
        
        sbom = SBOM(
            format=SBOMFormat.CYCLONEDX,
            spec_version="1.4",
            created=datetime.now(timezone.utc),
            creator="Test",
            document_namespace="urn:uuid:test",
            name="test",
            packages=[sample_package],
            metadata={},  # Missing required metadata
        )
        
        is_valid, errors = generator.validate(sbom)
        assert is_valid is False
        assert any("bomFormat" in error for error in errors)

    def test_validate_with_valid_signature(self, temp_project_dir, mock_config):
        """Test validating SBOM with valid signature."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch.dict("os.environ", {"HOME": tmpdir}):
                generator = SBOMGenerator(mock_config)
                
                sbom = generator.generate(
                    project_path=temp_project_dir,
                    format=SBOMFormat.SPDX,
                    sign=True,
                )
                
                is_valid, errors = generator.validate(sbom)
                assert is_valid is True
                assert len(errors) == 0

    def test_validate_with_invalid_signature(self, temp_project_dir, mock_config):
        """Test validating SBOM with invalid signature."""
        generator = SBOMGenerator(mock_config)
        
        sbom = generator.generate(
            project_path=temp_project_dir,
            format=SBOMFormat.SPDX,
            sign=False,
        )
        
        # Add invalid signature
        sbom.signature = SBOMSignature(
            algorithm="Ed25519",
            value="invalid-signature",
            public_key="invalid-key",
            timestamp=datetime.now(timezone.utc),
            signer="Test",
        )
        
        is_valid, errors = generator.validate(sbom)
        assert is_valid is False
        assert any("signature" in error.lower() for error in errors)

    def test_build_spdx_relationships(self, temp_project_dir, mock_config):
        """Test building SPDX relationships."""
        generator = SBOMGenerator(mock_config)
        
        sbom = generator.generate(
            project_path=temp_project_dir,
            format=SBOMFormat.SPDX,
            sign=False,
        )
        
        # Should have relationships
        assert len(sbom.relationships) > 0
        
        # Document should describe packages
        doc_relationships = [r for r in sbom.relationships if r.source == "SPDXRef-DOCUMENT"]
        assert len(doc_relationships) == len(sbom.packages)
        
        for rel in doc_relationships:
            assert rel.relationship_type == "DESCRIBES"

    def test_build_cyclonedx_dependencies(self, temp_project_dir, mock_config):
        """Test building CycloneDX dependencies."""
        generator = SBOMGenerator(mock_config)
        
        sbom = generator.generate(
            project_path=temp_project_dir,
            format=SBOMFormat.CYCLONEDX,
            sign=False,
        )
        
        # Should have metadata with dependencies
        assert "dependencies" in sbom.metadata
        assert isinstance(sbom.metadata["dependencies"], dict)


# ============================================================================
# Test Error Classes
# ============================================================================


class TestErrorClasses:
    """Test custom error classes."""

    def test_sbom_error(self):
        """Test base SBOM error."""
        error = SBOMError("Test error")
        assert str(error) == "Test error"
        assert isinstance(error, Exception)

    def test_dependency_scan_error(self):
        """Test dependency scan error."""
        error = DependencyScanError("Scan failed")
        assert isinstance(error, SBOMError)
        assert str(error) == "Scan failed"

    def test_signature_error(self):
        """Test signature error."""
        error = SignatureError("Signature invalid")
        assert isinstance(error, SBOMError)
        assert str(error) == "Signature invalid"


# ============================================================================
# Integration Tests
# ============================================================================


class TestIntegration:
    """Integration tests for SBOM generator."""

    def test_full_sbom_generation_workflow(self, mock_config):
        """Test complete SBOM generation workflow."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_path = Path(tmpdir)
            
            # Create a more complex project
            (project_path / "requirements.txt").write_text(
                "django==4.0.0\ncelery==5.2.0\npytest==7.0.0\n"
            )
            
            (project_path / "package.json").write_text(json.dumps({
                "name": "fullstack-app",
                "dependencies": {
                    "react": "^18.0.0",
                    "express": "^4.18.0",
                    "mongodb": "^4.3.0",
                }
            }))
            
            (project_path / "go.mod").write_text("""
module example.com/app

require (
    github.com/gorilla/mux v1.8.0
    github.com/lib/pq v1.10.4
)
            """)
            
            # Generate SBOM
            with patch.dict("os.environ", {"HOME": tmpdir}):
                generator = SBOMGenerator(mock_config)
                
                sbom = generator.generate(
                    project_path=project_path,
                    format=SBOMFormat.SPDX,
                    sign=True,
                    scan_vulnerabilities=True,
                )
                
                # Verify SBOM content
                assert len(sbom.packages) >= 8  # At least 8 packages
                assert sbom.signature is not None
                
                # Export SBOM
                output_path = project_path / "sbom.json"
                generator.export(sbom, output_path)
                assert output_path.exists()
                
                # Validate SBOM
                is_valid, errors = generator.validate(sbom)
                assert is_valid is True
                
                # Load and verify exported SBOM
                with open(output_path, "r") as f:
                    exported_data = json.load(f)
                    assert exported_data["format"] == "spdx-2.3"
                    assert len(exported_data["packages"]) >= 8
                    assert exported_data["signature"] is not None

    def test_performance_large_project(self, mock_config):
        """Test performance with large number of dependencies."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_path = Path(tmpdir)
            
            # Create project with many dependencies
            deps = [f"package{i}=={i}.0.0" for i in range(100)]
            (project_path / "requirements.txt").write_text("\n".join(deps))
            
            generator = SBOMGenerator(mock_config)
            
            import time
            start_time = time.time()
            
            sbom = generator.generate(
                project_path=project_path,
                format=SBOMFormat.SPDX,
                sign=False,
                scan_vulnerabilities=False,
            )
            
            elapsed_time = time.time() - start_time
            
            # Should complete within 30 seconds for <500 dependencies
            assert elapsed_time < 30
            assert len(sbom.packages) == 100

    def test_thread_safety(self, temp_project_dir, mock_config):
        """Test thread safety of SBOM generator."""
        import threading
        
        generator = SBOMGenerator(mock_config)
        results = []
        errors = []
        
        def generate_sbom():
            try:
                sbom = generator.generate(
                    project_path=temp_project_dir,
                    format=SBOMFormat.SPDX,
                    sign=False,
                )
                results.append(sbom)
            except Exception as e:
                errors.append(e)
        
        # Create multiple threads
        threads = []
        for _ in range(5):
            t = threading.Thread(target=generate_sbom)
            threads.append(t)
            t.start()
        
        # Wait for all threads
        for t in threads:
            t.join()
        
        # All should succeed
        assert len(errors) == 0
        assert len(results) == 5
        
        # All results should be equivalent
        for sbom in results:
            assert len(sbom.packages) == len(results[0].packages)