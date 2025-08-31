"""
SBOM Testing Assertions.

Custom assertion helpers for comprehensive SBOM validation,
performance testing, and compliance verification.
"""

from typing import Dict, List, Any, Optional, Union, Tuple
import json
import time
from dataclasses import dataclass

from .core import DependencyNode, CVEVulnerability, SBOMFormat, SBOMTestMetrics
from .validators import ValidationResult, ValidationSeverity


class SBOMAssertions:
    """
    Custom assertion helpers for SBOM testing.
    
    Provides high-level assertions for:
    - Format compliance validation
    - Performance requirement verification
    - Security vulnerability analysis
    - License compliance checking
    - Dependency completeness validation
    """
    
    def assert_valid_sbom_format(
        self, 
        validation_result: ValidationResult, 
        min_compliance_score: float = 0.95
    ):
        """
        Assert SBOM format is valid with minimum compliance score.
        
        Args:
            validation_result: Result from format validation
            min_compliance_score: Minimum compliance score (0.0-1.0)
            
        Raises:
            AssertionError: If validation fails or compliance insufficient
        """
        # Check basic validity
        if not validation_result.is_valid:
            errors = validation_result.get_errors()
            error_messages = [f"  - {err.field}: {err.message}" for err in errors]
            raise AssertionError(
                f"SBOM format validation failed with {len(errors)} error(s):\n" +
                "\n".join(error_messages)
            )
        
        # Check compliance score
        if validation_result.compliance_score < min_compliance_score:
            warnings = validation_result.get_warnings()
            warning_messages = [f"  - {warn.field}: {warn.message}" for warn in warnings[:5]]  # Show first 5
            
            raise AssertionError(
                f"SBOM compliance score insufficient: {validation_result.compliance_score:.2f} < {min_compliance_score:.2f}\n"
                f"Warnings ({len(warnings)} total):\n" + "\n".join(warning_messages) +
                (f"\n  ... and {len(warnings)-5} more" if len(warnings) > 5 else "")
            )
    
    def assert_dependency_tree_complete(
        self, 
        dependency_tree: DependencyNode, 
        expected_packages: Optional[List[str]] = None,
        min_depth: int = 1
    ):
        """
        Assert dependency tree completeness and structure.
        
        Args:
            dependency_tree: Dependency tree to validate
            expected_packages: Optional list of expected package names
            min_depth: Minimum required tree depth
            
        Raises:
            AssertionError: If tree is incomplete or malformed
        """
        if not dependency_tree:
            raise AssertionError("Dependency tree is empty or None")
        
        # Check basic node properties
        self._assert_node_complete(dependency_tree, "root")
        
        # Calculate tree metrics
        total_nodes = self._count_nodes(dependency_tree)
        max_depth = self._calculate_max_depth(dependency_tree)
        
        if max_depth < min_depth:
            raise AssertionError(
                f"Dependency tree depth insufficient: {max_depth} < {min_depth} (minimum)"
            )
        
        if total_nodes == 1 and min_depth > 0:
            raise AssertionError("Dependency tree has no dependencies (single root node)")
        
        # Check for expected packages if provided
        if expected_packages:
            found_packages = self._extract_package_names(dependency_tree)
            missing_packages = set(expected_packages) - set(found_packages)
            
            if missing_packages:
                raise AssertionError(
                    f"Missing expected packages in dependency tree: {sorted(missing_packages)}"
                )
        
        # Validate tree structure integrity
        self._validate_tree_integrity(dependency_tree)
    
    def _assert_node_complete(self, node: DependencyNode, path: str):
        """Assert individual node has required properties."""
        if not node.name:
            raise AssertionError(f"Node at {path} missing name")
        
        if not node.version:
            raise AssertionError(f"Node {path} ({node.name}) missing version")
        
        # Optional but recommended properties
        if not node.package_url:
            # This is a warning, not an error, but we track it
            pass
        
        # Validate children recursively
        for i, child in enumerate(node.children):
            child_path = f"{path}.children[{i}]"
            self._assert_node_complete(child, child_path)
    
    def _count_nodes(self, node: DependencyNode) -> int:
        """Count total nodes in tree."""
        count = 1
        for child in node.children:
            count += self._count_nodes(child)
        return count
    
    def _calculate_max_depth(self, node: DependencyNode, current_depth: int = 0) -> int:
        """Calculate maximum depth of tree."""
        if not node.children:
            return current_depth
        
        max_child_depth = 0
        for child in node.children:
            child_depth = self._calculate_max_depth(child, current_depth + 1)
            max_child_depth = max(max_child_depth, child_depth)
        
        return max_child_depth
    
    def _extract_package_names(self, node: DependencyNode) -> List[str]:
        """Extract all package names from tree."""
        names = [node.name]
        for child in node.children:
            names.extend(self._extract_package_names(child))
        return names
    
    def _validate_tree_integrity(self, node: DependencyNode, visited: Optional[set] = None):
        """Validate tree has no cycles and proper structure."""
        if visited is None:
            visited = set()
        
        # Check for cycles
        node_id = f"{node.name}@{node.version}"
        if node_id in visited:
            raise AssertionError(f"Cycle detected in dependency tree: {node_id}")
        
        visited.add(node_id)
        
        # Validate children
        for child in node.children:
            self._validate_tree_integrity(child, visited.copy())
    
    def assert_license_detection_accuracy(
        self, 
        detected_licenses: List[Dict[str, Any]], 
        expected_licenses: List[Dict[str, Any]], 
        min_accuracy: float = 0.95
    ):
        """
        Assert license detection meets accuracy requirements.
        
        Args:
            detected_licenses: List of detected license results
            expected_licenses: List of expected license results
            min_accuracy: Minimum accuracy threshold (0.0-1.0)
            
        Raises:
            AssertionError: If accuracy is below threshold
        """
        if len(expected_licenses) == 0:
            raise AssertionError("No expected licenses provided for accuracy calculation")
        
        correct_detections = 0
        errors = []
        
        # Create lookup for expected results
        expected_lookup = {exp["text_id"]: exp for exp in expected_licenses}
        
        for detected in detected_licenses:
            text_id = detected.get("text_id")
            if text_id not in expected_lookup:
                errors.append(f"Unexpected detection for text_id: {text_id}")
                continue
            
            expected = expected_lookup[text_id]
            
            # Check license match
            detected_license = detected.get("license")
            expected_license = expected.get("expected_license")
            
            if detected_license == expected_license:
                correct_detections += 1
            else:
                errors.append(
                    f"License mismatch for {text_id}: "
                    f"detected='{detected_license}', expected='{expected_license}'"
                )
        
        accuracy = correct_detections / len(expected_licenses)
        
        if accuracy < min_accuracy:
            error_sample = errors[:5]  # Show first 5 errors
            error_msg = (
                f"License detection accuracy below threshold: {accuracy:.3f} < {min_accuracy:.3f}\n"
                f"Correct: {correct_detections}/{len(expected_licenses)}\n"
                f"Sample errors:\n" + "\n".join(f"  - {err}" for err in error_sample)
            )
            if len(errors) > 5:
                error_msg += f"\n  ... and {len(errors)-5} more errors"
            
            raise AssertionError(error_msg)
    
    def assert_cve_scanning_effectiveness(
        self, 
        scan_results: List[Dict[str, Any]], 
        known_vulnerabilities: List[CVEVulnerability], 
        min_precision: float = 0.98, 
        min_recall: float = 0.98
    ):
        """
        Assert CVE scanning meets precision and recall requirements.
        
        Args:
            scan_results: Results from CVE scanning
            known_vulnerabilities: Known vulnerabilities for testing
            min_precision: Minimum precision threshold (0.0-1.0)
            min_recall: Minimum recall threshold (0.0-1.0)
            
        Raises:
            AssertionError: If precision or recall below threshold
        """
        if not known_vulnerabilities:
            raise AssertionError("No known vulnerabilities provided for CVE testing")
        
        # Extract CVE IDs from results and known vulns
        detected_cves = set()
        for result in scan_results:
            if "cve_ids" in result:
                detected_cves.update(result["cve_ids"])
        
        known_cves = set(vuln.cve_id for vuln in known_vulnerabilities)
        
        # Calculate precision, recall, F1
        true_positives = len(detected_cves & known_cves)
        false_positives = len(detected_cves - known_cves)
        false_negatives = len(known_cves - detected_cves)
        
        precision = true_positives / (true_positives + false_positives) if (true_positives + false_positives) > 0 else 0.0
        recall = true_positives / (true_positives + false_negatives) if (true_positives + false_negatives) > 0 else 0.0
        f1_score = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0
        
        errors = []
        
        if precision < min_precision:
            errors.append(f"Precision below threshold: {precision:.3f} < {min_precision:.3f}")
            if false_positives > 0:
                fp_sample = list(detected_cves - known_cves)[:3]
                errors.append(f"False positives (sample): {fp_sample}")
        
        if recall < min_recall:
            errors.append(f"Recall below threshold: {recall:.3f} < {min_recall:.3f}")
            if false_negatives > 0:
                fn_sample = list(known_cves - detected_cves)[:3]
                errors.append(f"False negatives (sample): {fn_sample}")
        
        if errors:
            summary = (
                f"CVE scanning effectiveness insufficient:\n"
                f"  Precision: {precision:.3f} (target: {min_precision:.3f})\n"
                f"  Recall: {recall:.3f} (target: {min_recall:.3f})\n"
                f"  F1 Score: {f1_score:.3f}\n"
                f"  True Positives: {true_positives}\n"
                f"  False Positives: {false_positives}\n"
                f"  False Negatives: {false_negatives}\n"
                f"Issues:\n" + "\n".join(f"  - {err}" for err in errors)
            )
            raise AssertionError(summary)
    
    def assert_signature_verification(
        self, 
        signature_data: bytes, 
        public_key: bytes, 
        content: bytes, 
        algorithm: str = "ed25519"
    ):
        """
        Assert Ed25519 digital signature verification.
        
        Args:
            signature_data: Digital signature bytes
            public_key: Public key bytes
            content: Original content that was signed
            algorithm: Signature algorithm (default: ed25519)
            
        Raises:
            AssertionError: If signature verification fails
        """
        try:
            if algorithm.lower() == "ed25519":
                from cryptography.hazmat.primitives.asymmetric import ed25519
                from cryptography.exceptions import InvalidSignature
                
                # Load public key
                try:
                    pub_key = ed25519.Ed25519PublicKey.from_public_bytes(public_key)
                except ValueError as e:
                    raise AssertionError(f"Invalid Ed25519 public key: {e}")
                
                # Verify signature
                try:
                    pub_key.verify(signature_data, content)
                except InvalidSignature:
                    raise AssertionError("Ed25519 signature verification failed")
                
            else:
                raise AssertionError(f"Unsupported signature algorithm: {algorithm}")
                
        except ImportError as e:
            raise AssertionError(f"Cryptography library not available for signature verification: {e}")
    
    def assert_generation_performance(
        self, 
        generation_time: float, 
        target_time: float, 
        project_size: str = "unknown",
        dependency_count: Optional[int] = None
    ):
        """
        Assert SBOM generation performance meets requirements.
        
        Args:
            generation_time: Actual generation time in seconds
            target_time: Target generation time in seconds
            project_size: Size category of test project
            dependency_count: Number of dependencies processed
            
        Raises:
            AssertionError: If generation time exceeds target
        """
        if generation_time > target_time:
            perf_info = f"Project: {project_size}"
            if dependency_count:
                perf_info += f", Dependencies: {dependency_count}"
                throughput = dependency_count / generation_time
                perf_info += f", Throughput: {throughput:.1f} deps/sec"
            
            raise AssertionError(
                f"SBOM generation performance target not met: {generation_time:.2f}s > {target_time:.2f}s\n"
                f"{perf_info}"
            )
    
    def assert_file_size_reasonable(
        self, 
        sbom_content: str, 
        max_size_mb: float = 10.0,
        dependency_count: Optional[int] = None
    ):
        """
        Assert SBOM file size is reasonable.
        
        Args:
            sbom_content: SBOM content as string
            max_size_mb: Maximum reasonable size in MB
            dependency_count: Number of dependencies for context
            
        Raises:
            AssertionError: If file size is unreasonable
        """
        size_bytes = len(sbom_content.encode('utf-8'))
        size_mb = size_bytes / (1024 * 1024)
        
        if size_mb > max_size_mb:
            context = ""
            if dependency_count:
                bytes_per_dep = size_bytes / dependency_count
                context = f" ({bytes_per_dep:.0f} bytes per dependency)"
            
            raise AssertionError(
                f"SBOM file size unreasonable: {size_mb:.2f}MB > {max_size_mb:.2f}MB{context}"
            )
    
    def assert_format_consistency(
        self, 
        sbom_formats: Dict[SBOMFormat, str], 
        dependency_tree: DependencyNode
    ):
        """
        Assert different SBOM formats contain consistent information.
        
        Args:
            sbom_formats: Dictionary of format to content
            dependency_tree: Original dependency tree for reference
            
        Raises:
            AssertionError: If formats are inconsistent
        """
        if len(sbom_formats) < 2:
            raise AssertionError("Need at least 2 formats for consistency checking")
        
        # Extract package counts from each format
        package_counts = {}
        
        for format_type, content in sbom_formats.items():
            try:
                if format_type in [SBOMFormat.SPDX_JSON, SBOMFormat.SPDX_YAML]:
                    data = json.loads(content) if format_type == SBOMFormat.SPDX_JSON else yaml.safe_load(content)
                    package_counts[format_type] = len(data.get("packages", []))
                    
                elif format_type == SBOMFormat.CYCLONE_DX_JSON:
                    data = json.loads(content)
                    package_counts[format_type] = len(data.get("components", []))
                    
                elif format_type == SBOMFormat.SPDX_TAG_VALUE:
                    # Count PackageName tags
                    package_counts[format_type] = content.count("PackageName:")
                    
                else:
                    # For XML formats, do basic counting
                    package_counts[format_type] = content.count("<component") + content.count("spdx:Package")
                    
            except Exception as e:
                raise AssertionError(f"Failed to parse {format_type}: {e}")
        
        # Check consistency
        reference_count = self._count_nodes(dependency_tree)
        inconsistencies = []
        
        for format_type, count in package_counts.items():
            # Allow some variance for different format interpretations
            if abs(count - reference_count) > 2:  # Allow ±2 difference
                inconsistencies.append(f"{format_type}: {count} packages (expected ~{reference_count})")
        
        if inconsistencies:
            raise AssertionError(
                f"SBOM format consistency check failed:\n" +
                "\n".join(f"  - {inc}" for inc in inconsistencies)
            )
    
    def assert_metadata_completeness(
        self, 
        sbom_content: str, 
        format_type: SBOMFormat, 
        required_metadata: List[str] = None
    ):
        """
        Assert SBOM contains required metadata fields.
        
        Args:
            sbom_content: SBOM content as string
            format_type: SBOM format type
            required_metadata: List of required metadata fields
            
        Raises:
            AssertionError: If required metadata is missing
        """
        if required_metadata is None:
            if format_type in [SBOMFormat.SPDX_JSON, SBOMFormat.SPDX_YAML]:
                required_metadata = ["spdxVersion", "documentName", "creationInfo"]
            elif format_type in [SBOMFormat.CYCLONE_DX_JSON, SBOMFormat.CYCLONE_DX_XML]:
                required_metadata = ["bomFormat", "specVersion", "metadata"]
            else:
                required_metadata = []
        
        missing_metadata = []
        
        try:
            if format_type == SBOMFormat.SPDX_JSON:
                data = json.loads(sbom_content)
                for field in required_metadata:
                    if field not in data:
                        missing_metadata.append(field)
            
            elif format_type == SBOMFormat.CYCLONE_DX_JSON:
                data = json.loads(sbom_content)
                for field in required_metadata:
                    if field not in data:
                        missing_metadata.append(field)
            
            elif format_type == SBOMFormat.SPDX_TAG_VALUE:
                for field in required_metadata:
                    # Convert field names for tag-value format
                    tag_name = field.replace("spdxVersion", "SPDXVersion").replace("documentName", "DocumentName")
                    if f"{tag_name}:" not in sbom_content:
                        missing_metadata.append(field)
            
            # Add checks for other formats as needed
            
        except Exception as e:
            raise AssertionError(f"Failed to parse SBOM for metadata check: {e}")
        
        if missing_metadata:
            raise AssertionError(
                f"SBOM missing required metadata fields: {missing_metadata}"
            )


# ============================================================================
# HELPER FUNCTIONS FOR COMPLEX ASSERTIONS
# ============================================================================

def validate_dependency_completeness(
    sbom_content: str, 
    original_manifest: Dict[str, Any], 
    format_type: SBOMFormat
) -> Tuple[bool, List[str]]:
    """
    Validate that SBOM contains all dependencies from original manifest.
    
    Args:
        sbom_content: SBOM content to check
        original_manifest: Original package manifest (package.json, requirements.txt, etc.)
        format_type: SBOM format type
        
    Returns:
        Tuple of (is_complete, list_of_missing_packages)
    """
    # Extract expected dependencies from manifest
    expected_deps = set()
    
    if "dependencies" in original_manifest:
        expected_deps.update(original_manifest["dependencies"].keys())
    if "devDependencies" in original_manifest:
        expected_deps.update(original_manifest["devDependencies"].keys())
    
    # Extract actual dependencies from SBOM
    actual_deps = set()
    
    try:
        if format_type == SBOMFormat.SPDX_JSON:
            data = json.loads(sbom_content)
            for package in data.get("packages", []):
                if "name" in package:
                    actual_deps.add(package["name"])
        
        elif format_type == SBOMFormat.CYCLONE_DX_JSON:
            data = json.loads(sbom_content)
            for component in data.get("components", []):
                if "name" in component:
                    actual_deps.add(component["name"])
    
    except Exception:
        return False, ["Failed to parse SBOM content"]
    
    missing_deps = list(expected_deps - actual_deps)
    return len(missing_deps) == 0, missing_deps


def calculate_sbom_quality_score(validation_result: ValidationResult, metrics: SBOMTestMetrics) -> float:
    """
    Calculate overall SBOM quality score from validation and metrics.
    
    Args:
        validation_result: Format validation result
        metrics: Performance and quality metrics
        
    Returns:
        Quality score between 0.0 and 1.0
    """
    # Weighted scoring
    scores = {
        "format_compliance": (validation_result.compliance_score, 0.25),
        "license_detection": (metrics.license_detection_accuracy, 0.20),
        "cve_precision": (metrics.cve_scan_precision, 0.20),
        "cve_recall": (metrics.cve_scan_recall, 0.20),
        "performance": (min(1.0, 30.0 / metrics.generation_time) if metrics.generation_time > 0 else 0.0, 0.10),
        "signature_verification": (1.0 if metrics.signature_verification_success else 0.0, 0.05)
    }
    
    total_score = 0.0
    for component, (score, weight) in scores.items():
        total_score += score * weight
    
    return min(total_score, 1.0)  # Cap at 1.0