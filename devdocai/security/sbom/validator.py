"""
SBOM Validator - Validation for SPDX and CycloneDX SBOM formats.

Provides comprehensive validation of SBOM documents against official
specifications and security best practices.
"""

import json
import logging
import re
from datetime import datetime
from typing import Dict, Any, List, Optional, Union
from enum import Enum
from dataclasses import dataclass
import xml.etree.ElementTree as ET

from .generator import SBOMFormat

logger = logging.getLogger(__name__)


class ValidationSeverity(str, Enum):
    """Validation issue severity levels."""
    ERROR = "error"      # Critical errors that make SBOM invalid
    WARNING = "warning"  # Issues that should be addressed
    INFO = "info"        # Minor issues or suggestions


@dataclass
class ValidationIssue:
    """Represents a validation issue."""
    severity: ValidationSeverity
    field: str
    message: str
    location: Optional[str] = None
    suggestion: Optional[str] = None


@dataclass
class SBOMValidationResult:
    """Result of SBOM validation."""
    is_valid: bool
    format_detected: Optional[SBOMFormat]
    compliance_score: float  # 0.0 to 1.0
    issues: List[ValidationIssue]
    statistics: Dict[str, Any]
    validation_time_ms: float
    
    def has_errors(self) -> bool:
        """Check if there are any error-level issues."""
        return any(issue.severity == ValidationSeverity.ERROR for issue in self.issues)
    
    def get_issues_by_severity(self, severity: ValidationSeverity) -> List[ValidationIssue]:
        """Get issues by severity level."""
        return [issue for issue in self.issues if issue.severity == severity]


class SBOMValidator:
    """
    Comprehensive SBOM validator for SPDX and CycloneDX formats.
    
    Validates structure, required fields, compliance with specifications,
    and security best practices.
    """
    
    def __init__(self):
        """Initialize SBOM validator."""
        # SPDX validation patterns
        self.spdx_patterns = {
            'spdx_id': re.compile(r'^SPDXRef-[a-zA-Z0-9\-\.]+$'),
            'version': re.compile(r'^SPDX-\d+\.\d+$'),
            'license': re.compile(r'^[A-Za-z0-9\-\.\+]+(\s+WITH\s+[A-Za-z0-9\-\.\+]+)?$|^NOASSERTION$|^NONE$'),
            'namespace': re.compile(r'^https?://[^\s]+$|^urn:[a-zA-Z0-9][a-zA-Z0-9-]{1,31}:.*$'),
            'checksum': re.compile(r'^[a-fA-F0-9]+$')
        }
        
        # CycloneDX validation patterns
        self.cyclonedx_patterns = {
            'bom_ref': re.compile(r'^[a-zA-Z0-9\-\.\@\:\_]+$'),
            'version': re.compile(r'^1\.\d+$'),
            'serial_number': re.compile(r'^urn:uuid:[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$'),
            'hash_alg': re.compile(r'^(MD5|SHA-1|SHA-256|SHA-384|SHA-512|SHA3-256|SHA3-384|SHA3-512|BLAKE2b-256|BLAKE2b-384|BLAKE2b-512|BLAKE3)$')
        }
        
        # Required fields for each format
        self.spdx_required_fields = {
            'document': ['spdxVersion', 'dataLicense', 'SPDXID', 'documentName', 'documentNamespace', 'creationInfo'],
            'creation_info': ['created'],
            'package': ['SPDXID', 'name', 'downloadLocation', 'filesAnalyzed', 'copyrightText']
        }
        
        self.cyclonedx_required_fields = {
            'document': ['bomFormat', 'specVersion', 'serialNumber', 'version'],
            'component': ['type', 'bom-ref', 'name'],
            'metadata': ['timestamp']
        }
    
    def validate(self, sbom_content: Union[str, Dict[str, Any]], 
                format_hint: Optional[Union[str, SBOMFormat]] = None) -> SBOMValidationResult:
        """
        Validate SBOM content.
        
        Args:
            sbom_content: SBOM content to validate
            format_hint: Optional format hint
            
        Returns:
            Validation result
        """
        start_time = datetime.now()
        issues = []
        statistics = {}
        
        try:
            # Parse content if string
            if isinstance(sbom_content, str):
                try:
                    content_dict = json.loads(sbom_content)
                except json.JSONDecodeError as e:
                    # Try XML parsing
                    try:
                        ET.fromstring(sbom_content)
                        # For now, treat XML as valid but return warning
                        issues.append(ValidationIssue(
                            severity=ValidationSeverity.WARNING,
                            field="format",
                            message="XML format validation not fully implemented",
                            suggestion="Use JSON format for complete validation"
                        ))
                        content_dict = {}  # Empty dict for XML
                    except ET.ParseError:
                        issues.append(ValidationIssue(
                            severity=ValidationSeverity.ERROR,
                            field="format",
                            message=f"Invalid JSON/XML format: {str(e)}"
                        ))
                        return self._create_result(False, None, issues, {}, start_time)
            else:
                content_dict = sbom_content
            
            # Detect format
            detected_format = self._detect_format(content_dict, format_hint)
            if not detected_format:
                issues.append(ValidationIssue(
                    severity=ValidationSeverity.ERROR,
                    field="format",
                    message="Could not detect SBOM format (SPDX or CycloneDX)"
                ))
                return self._create_result(False, None, issues, {}, start_time)
            
            # Validate based on detected format
            if detected_format in [SBOMFormat.SPDX_JSON, SBOMFormat.SPDX_XML]:
                format_issues, stats = self._validate_spdx(content_dict)
            else:
                format_issues, stats = self._validate_cyclonedx(content_dict)
            
            issues.extend(format_issues)
            statistics.update(stats)
            
            # Calculate compliance score
            compliance_score = self._calculate_compliance_score(issues, statistics)
            
            # Determine if valid (no error-level issues)
            is_valid = not any(issue.severity == ValidationSeverity.ERROR for issue in issues)
            
            return self._create_result(is_valid, detected_format, issues, statistics, start_time, compliance_score)
            
        except Exception as e:
            logger.error(f"Validation failed with exception: {e}")
            issues.append(ValidationIssue(
                severity=ValidationSeverity.ERROR,
                field="validation",
                message=f"Validation failed: {str(e)}"
            ))
            return self._create_result(False, None, issues, {}, start_time)
    
    def _detect_format(self, content: Dict[str, Any], 
                      format_hint: Optional[Union[str, SBOMFormat]]) -> Optional[SBOMFormat]:
        """Detect SBOM format from content."""
        if format_hint:
            if isinstance(format_hint, str):
                try:
                    return SBOMFormat(format_hint)
                except ValueError:
                    pass
            else:
                return format_hint
        
        # Auto-detect from content
        if 'spdxVersion' in content:
            return SBOMFormat.SPDX_JSON
        elif 'bomFormat' in content and content.get('bomFormat') == 'CycloneDX':
            return SBOMFormat.CYCLONEDX_JSON
        
        return None
    
    def _validate_spdx(self, content: Dict[str, Any]) -> tuple:
        """Validate SPDX format SBOM."""
        issues = []
        statistics = {
            'format': 'SPDX',
            'packages_count': 0,
            'relationships_count': 0,
            'files_count': 0
        }
        
        # Validate document-level fields
        for field in self.spdx_required_fields['document']:
            if field not in content:
                issues.append(ValidationIssue(
                    severity=ValidationSeverity.ERROR,
                    field=f"document.{field}",
                    message=f"Required field '{field}' is missing"
                ))
        
        # Validate SPDX version
        if 'spdxVersion' in content:
            if not self.spdx_patterns['version'].match(content['spdxVersion']):
                issues.append(ValidationIssue(
                    severity=ValidationSeverity.ERROR,
                    field="document.spdxVersion",
                    message=f"Invalid SPDX version format: {content['spdxVersion']}",
                    suggestion="Use format 'SPDX-X.Y' (e.g., 'SPDX-2.3')"
                ))
        
        # Validate data license
        if 'dataLicense' in content and content['dataLicense'] != 'CC0-1.0':
            issues.append(ValidationIssue(
                severity=ValidationSeverity.ERROR,
                field="document.dataLicense",
                message=f"Invalid data license: {content['dataLicense']}",
                suggestion="SPDX documents must use 'CC0-1.0'"
            ))
        
        # Validate SPDX ID
        if 'SPDXID' in content:
            if not self.spdx_patterns['spdx_id'].match(content['SPDXID']):
                issues.append(ValidationIssue(
                    severity=ValidationSeverity.ERROR,
                    field="document.SPDXID",
                    message=f"Invalid SPDX ID format: {content['SPDXID']}",
                    suggestion="Use format 'SPDXRef-DOCUMENT'"
                ))
        
        # Validate document namespace
        if 'documentNamespace' in content:
            if not self.spdx_patterns['namespace'].match(content['documentNamespace']):
                issues.append(ValidationIssue(
                    severity=ValidationSeverity.WARNING,
                    field="document.documentNamespace",
                    message=f"Document namespace should be a valid URI: {content['documentNamespace']}"
                ))
        
        # Validate creation info
        if 'creationInfo' in content:
            creation_info = content['creationInfo']
            for field in self.spdx_required_fields['creation_info']:
                if field not in creation_info:
                    issues.append(ValidationIssue(
                        severity=ValidationSeverity.ERROR,
                        field=f"creationInfo.{field}",
                        message=f"Required creation info field '{field}' is missing"
                    ))
        
        # Validate packages
        if 'packages' in content:
            statistics['packages_count'] = len(content['packages'])
            for i, package in enumerate(content['packages']):
                package_issues = self._validate_spdx_package(package, i)
                issues.extend(package_issues)
        else:
            issues.append(ValidationIssue(
                severity=ValidationSeverity.WARNING,
                field="document.packages",
                message="No packages defined in SBOM"
            ))
        
        # Validate relationships
        if 'relationships' in content:
            statistics['relationships_count'] = len(content['relationships'])
            for i, relationship in enumerate(content['relationships']):
                rel_issues = self._validate_spdx_relationship(relationship, i)
                issues.extend(rel_issues)
        
        return issues, statistics
    
    def _validate_spdx_package(self, package: Dict[str, Any], index: int) -> List[ValidationIssue]:
        """Validate SPDX package."""
        issues = []
        
        # Check required fields
        for field in self.spdx_required_fields['package']:
            if field not in package:
                issues.append(ValidationIssue(
                    severity=ValidationSeverity.ERROR,
                    field=f"packages[{index}].{field}",
                    message=f"Required package field '{field}' is missing"
                ))
        
        # Validate SPDX ID
        if 'SPDXID' in package:
            if not self.spdx_patterns['spdx_id'].match(package['SPDXID']):
                issues.append(ValidationIssue(
                    severity=ValidationSeverity.ERROR,
                    field=f"packages[{index}].SPDXID",
                    message=f"Invalid package SPDX ID: {package['SPDXID']}"
                ))
        
        # Validate download location
        if 'downloadLocation' in package:
            dl_location = package['downloadLocation']
            if dl_location not in ['NOASSERTION', 'NONE'] and not self._is_valid_url(dl_location):
                issues.append(ValidationIssue(
                    severity=ValidationSeverity.WARNING,
                    field=f"packages[{index}].downloadLocation",
                    message=f"Invalid download location format: {dl_location}"
                ))
        
        # Validate license fields
        for license_field in ['licenseConcluded', 'licenseDeclared']:
            if license_field in package:
                license_value = package[license_field]
                if license_value not in ['NOASSERTION', 'NONE'] and not self._is_valid_license(license_value):
                    issues.append(ValidationIssue(
                        severity=ValidationSeverity.WARNING,
                        field=f"packages[{index}].{license_field}",
                        message=f"Non-standard license identifier: {license_value}",
                        suggestion="Use SPDX License List identifiers"
                    ))
        
        # Validate checksums
        if 'checksums' in package:
            for j, checksum in enumerate(package['checksums']):
                if 'algorithm' not in checksum:
                    issues.append(ValidationIssue(
                        severity=ValidationSeverity.ERROR,
                        field=f"packages[{index}].checksums[{j}].algorithm",
                        message="Checksum algorithm is required"
                    ))
                
                if 'checksumValue' not in checksum:
                    issues.append(ValidationIssue(
                        severity=ValidationSeverity.ERROR,
                        field=f"packages[{index}].checksums[{j}].checksumValue",
                        message="Checksum value is required"
                    ))
                elif not self.spdx_patterns['checksum'].match(checksum['checksumValue']):
                    issues.append(ValidationIssue(
                        severity=ValidationSeverity.ERROR,
                        field=f"packages[{index}].checksums[{j}].checksumValue",
                        message=f"Invalid checksum format: {checksum['checksumValue']}"
                    ))
        
        return issues
    
    def _validate_spdx_relationship(self, relationship: Dict[str, Any], index: int) -> List[ValidationIssue]:
        """Validate SPDX relationship."""
        issues = []
        
        required_fields = ['spdxElementId', 'relatedSpdxElement', 'relationshipType']
        for field in required_fields:
            if field not in relationship:
                issues.append(ValidationIssue(
                    severity=ValidationSeverity.ERROR,
                    field=f"relationships[{index}].{field}",
                    message=f"Required relationship field '{field}' is missing"
                ))
        
        # Validate relationship type
        valid_relationship_types = [
            'DESCRIBES', 'DESCRIBED_BY', 'CONTAINS', 'CONTAINED_BY', 
            'DEPENDS_ON', 'DEPENDENCY_OF', 'BUILD_DEPENDENCY_OF', 'DEV_DEPENDENCY_OF',
            'OPTIONAL_DEPENDENCY_OF', 'PROVIDED_DEPENDENCY_OF', 'TEST_DEPENDENCY_OF',
            'RUNTIME_DEPENDENCY_OF', 'EXAMPLE_OF', 'GENERATES', 'GENERATED_FROM',
            'ANCESTOR_OF', 'DESCENDANT_OF', 'VARIANT_OF', 'DISTRIBUTION_ARTIFACT',
            'PATCH_FOR', 'PATCH_APPLIED', 'COPY_OF', 'FILE_ADDED', 'FILE_DELETED',
            'FILE_MODIFIED', 'EXPANDED_FROM_ARCHIVE', 'DYNAMIC_LINK', 'STATIC_LINK',
            'DATA_FILE_OF', 'TEST_CASE_OF', 'BUILD_TOOL_OF', 'DEV_TOOL_OF', 'TEST_OF',
            'TEST_TOOL_OF', 'METAFILE_OF', 'PACKAGE_OF', 'AMENDS', 'PREREQUISITE_FOR',
            'HAS_PREREQUISITE', 'OTHER'
        ]
        
        if 'relationshipType' in relationship:
            if relationship['relationshipType'] not in valid_relationship_types:
                issues.append(ValidationIssue(
                    severity=ValidationSeverity.WARNING,
                    field=f"relationships[{index}].relationshipType",
                    message=f"Non-standard relationship type: {relationship['relationshipType']}",
                    suggestion=f"Use one of: {', '.join(valid_relationship_types)}"
                ))
        
        return issues
    
    def _validate_cyclonedx(self, content: Dict[str, Any]) -> tuple:
        """Validate CycloneDX format SBOM."""
        issues = []
        statistics = {
            'format': 'CycloneDX',
            'components_count': 0,
            'services_count': 0,
            'vulnerabilities_count': 0
        }
        
        # Validate document-level fields
        for field in self.cyclonedx_required_fields['document']:
            if field not in content:
                issues.append(ValidationIssue(
                    severity=ValidationSeverity.ERROR,
                    field=f"document.{field}",
                    message=f"Required field '{field}' is missing"
                ))
        
        # Validate BOM format
        if 'bomFormat' in content and content['bomFormat'] != 'CycloneDX':
            issues.append(ValidationIssue(
                severity=ValidationSeverity.ERROR,
                field="document.bomFormat",
                message=f"Invalid BOM format: {content['bomFormat']}",
                suggestion="Must be 'CycloneDX'"
            ))
        
        # Validate spec version
        if 'specVersion' in content:
            if not self.cyclonedx_patterns['version'].match(content['specVersion']):
                issues.append(ValidationIssue(
                    severity=ValidationSeverity.ERROR,
                    field="document.specVersion",
                    message=f"Invalid spec version: {content['specVersion']}",
                    suggestion="Use format '1.X' (e.g., '1.4')"
                ))
        
        # Validate serial number
        if 'serialNumber' in content:
            if not self.cyclonedx_patterns['serial_number'].match(content['serialNumber']):
                issues.append(ValidationIssue(
                    severity=ValidationSeverity.ERROR,
                    field="document.serialNumber",
                    message=f"Invalid serial number format: {content['serialNumber']}",
                    suggestion="Use format 'urn:uuid:XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX'"
                ))
        
        # Validate metadata
        if 'metadata' in content:
            metadata = content['metadata']
            if 'timestamp' not in metadata:
                issues.append(ValidationIssue(
                    severity=ValidationSeverity.ERROR,
                    field="metadata.timestamp",
                    message="Required metadata field 'timestamp' is missing"
                ))
        
        # Validate components
        if 'components' in content:
            statistics['components_count'] = len(content['components'])
            for i, component in enumerate(content['components']):
                comp_issues = self._validate_cyclonedx_component(component, i)
                issues.extend(comp_issues)
        
        # Validate services
        if 'services' in content:
            statistics['services_count'] = len(content['services'])
        
        # Validate vulnerabilities
        if 'vulnerabilities' in content:
            statistics['vulnerabilities_count'] = len(content['vulnerabilities'])
        
        return issues, statistics
    
    def _validate_cyclonedx_component(self, component: Dict[str, Any], index: int) -> List[ValidationIssue]:
        """Validate CycloneDX component."""
        issues = []
        
        # Check required fields
        for field in self.cyclonedx_required_fields['component']:
            if field not in component:
                issues.append(ValidationIssue(
                    severity=ValidationSeverity.ERROR,
                    field=f"components[{index}].{field}",
                    message=f"Required component field '{field}' is missing"
                ))
        
        # Validate component type
        valid_types = ['application', 'framework', 'library', 'container', 'operating-system', 
                      'device', 'firmware', 'file']
        if 'type' in component and component['type'] not in valid_types:
            issues.append(ValidationIssue(
                severity=ValidationSeverity.WARNING,
                field=f"components[{index}].type",
                message=f"Non-standard component type: {component['type']}",
                suggestion=f"Use one of: {', '.join(valid_types)}"
            ))
        
        # Validate bom-ref
        if 'bom-ref' in component:
            if not self.cyclonedx_patterns['bom_ref'].match(component['bom-ref']):
                issues.append(ValidationIssue(
                    severity=ValidationSeverity.WARNING,
                    field=f"components[{index}].bom-ref",
                    message=f"Invalid bom-ref format: {component['bom-ref']}"
                ))
        
        # Validate hashes
        if 'hashes' in component:
            for j, hash_obj in enumerate(component['hashes']):
                if 'alg' not in hash_obj:
                    issues.append(ValidationIssue(
                        severity=ValidationSeverity.ERROR,
                        field=f"components[{index}].hashes[{j}].alg",
                        message="Hash algorithm is required"
                    ))
                elif not self.cyclonedx_patterns['hash_alg'].match(hash_obj['alg']):
                    issues.append(ValidationIssue(
                        severity=ValidationSeverity.WARNING,
                        field=f"components[{index}].hashes[{j}].alg",
                        message=f"Non-standard hash algorithm: {hash_obj['alg']}"
                    ))
                
                if 'content' not in hash_obj:
                    issues.append(ValidationIssue(
                        severity=ValidationSeverity.ERROR,
                        field=f"components[{index}].hashes[{j}].content",
                        message="Hash content is required"
                    ))
        
        return issues
    
    def _calculate_compliance_score(self, issues: List[ValidationIssue], 
                                  statistics: Dict[str, Any]) -> float:
        """Calculate compliance score based on validation results."""
        if not issues:
            return 1.0
        
        # Weight different issue types
        error_weight = 1.0
        warning_weight = 0.3
        info_weight = 0.1
        
        # Calculate penalty
        error_count = len([i for i in issues if i.severity == ValidationSeverity.ERROR])
        warning_count = len([i for i in issues if i.severity == ValidationSeverity.WARNING])
        info_count = len([i for i in issues if i.severity == ValidationSeverity.INFO])
        
        total_penalty = (error_count * error_weight + 
                        warning_count * warning_weight + 
                        info_count * info_weight)
        
        # Calculate score (errors have higher impact)
        if error_count > 0:
            base_score = 0.5  # Start at 50% if there are errors
        else:
            base_score = 1.0
        
        # Reduce score based on penalty
        penalty_factor = min(total_penalty / 10.0, 0.8)  # Max 80% penalty
        score = max(base_score * (1.0 - penalty_factor), 0.0)
        
        return round(score, 3)
    
    def _is_valid_url(self, url: str) -> bool:
        """Check if string is a valid URL."""
        url_pattern = re.compile(
            r'^https?://'  # http:// or https://
            r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain
            r'localhost|'  # localhost
            r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # IP
            r'(?::\d+)?'  # optional port
            r'(?:/?|[/?]\S+)$', re.IGNORECASE)
        return bool(url_pattern.match(url))
    
    def _is_valid_license(self, license_id: str) -> bool:
        """Check if license identifier is valid SPDX license."""
        # This is a simplified check - in production, this would validate
        # against the official SPDX License List
        common_licenses = [
            'MIT', 'Apache-2.0', 'GPL-2.0', 'GPL-3.0', 'BSD-2-Clause', 'BSD-3-Clause',
            'ISC', 'MPL-2.0', 'CC0-1.0', 'Unlicense', 'LGPL-2.1', 'LGPL-3.0'
        ]
        return license_id in common_licenses or self.spdx_patterns['license'].match(license_id)
    
    def _create_result(self, is_valid: bool, format_detected: Optional[SBOMFormat],
                      issues: List[ValidationIssue], statistics: Dict[str, Any],
                      start_time: datetime, compliance_score: float = 0.0) -> SBOMValidationResult:
        """Create validation result."""
        validation_time = (datetime.now() - start_time).total_seconds() * 1000
        
        return SBOMValidationResult(
            is_valid=is_valid,
            format_detected=format_detected,
            compliance_score=compliance_score,
            issues=issues,
            statistics=statistics,
            validation_time_ms=validation_time
        )