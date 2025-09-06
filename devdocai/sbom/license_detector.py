"""
License Detector Component
Detects and identifies software licenses
"""

import re
from typing import Optional, Dict, List, Any
from pathlib import Path


class LicenseDetector:
    """
    Detects licenses for software components
    Uses SPDX license identifiers
    """
    
    def __init__(self):
        """Initialize license detector with common license patterns"""
        # Common SPDX license identifiers and their patterns
        self.license_patterns = {
            'MIT': [
                r'MIT License',
                r'Permission is hereby granted, free of charge',
                r'THE SOFTWARE IS PROVIDED "AS IS"'
            ],
            'Apache-2.0': [
                r'Apache License,?\s+Version 2\.0',
                r'Licensed under the Apache License, Version 2\.0'
            ],
            'GPL-3.0': [
                r'GNU GENERAL PUBLIC LICENSE\s+Version 3',
                r'GPLv3',
                r'GPL-3\.0'
            ],
            'GPL-2.0': [
                r'GNU GENERAL PUBLIC LICENSE\s+Version 2',
                r'GPLv2',
                r'GPL-2\.0'
            ],
            'BSD-3-Clause': [
                r'BSD 3-Clause License',
                r'Redistribution and use in source and binary forms, with or without modification'
            ],
            'BSD-2-Clause': [
                r'BSD 2-Clause License',
                r'Simplified BSD License'
            ],
            'ISC': [
                r'ISC License',
                r'Permission to use, copy, modify, and/or distribute this software'
            ],
            'LGPL-3.0': [
                r'GNU LESSER GENERAL PUBLIC LICENSE\s+Version 3',
                r'LGPLv3',
                r'LGPL-3\.0'
            ],
            'LGPL-2.1': [
                r'GNU LESSER GENERAL PUBLIC LICENSE\s+Version 2\.1',
                r'LGPLv2\.1',
                r'LGPL-2\.1'
            ],
            'MPL-2.0': [
                r'Mozilla Public License Version 2\.0',
                r'MPL-2\.0'
            ],
            'CC0-1.0': [
                r'CC0 1\.0 Universal',
                r'Creative Commons Zero',
                r'No rights reserved'
            ],
            'Unlicense': [
                r'This is free and unencumbered software released into the public domain',
                r'Unlicense'
            ],
            'Proprietary': [
                r'All rights reserved',
                r'Proprietary',
                r'Commercial License'
            ]
        }
        
        # Map common license file names to SPDX identifiers
        self.filename_hints = {
            'MIT': ['MIT', 'MIT-LICENSE', 'MIT.txt'],
            'Apache-2.0': ['APACHE', 'APACHE-2.0', 'Apache-2.0.txt'],
            'GPL-3.0': ['GPL', 'GPLv3', 'COPYING', 'GPL-3.0.txt'],
            'BSD-3-Clause': ['BSD', 'BSD-3-Clause.txt'],
            'ISC': ['ISC', 'ISC.txt']
        }
        
        # Common package metadata license mappings
        self.metadata_mappings = {
            'mit': 'MIT',
            'apache-2.0': 'Apache-2.0',
            'apache2': 'Apache-2.0',
            'gpl-3.0': 'GPL-3.0',
            'gplv3': 'GPL-3.0',
            'gpl-2.0': 'GPL-2.0',
            'gplv2': 'GPL-2.0',
            'bsd-3-clause': 'BSD-3-Clause',
            'bsd-2-clause': 'BSD-2-Clause',
            'bsd': 'BSD-3-Clause',
            'isc': 'ISC',
            'lgpl-3.0': 'LGPL-3.0',
            'lgplv3': 'LGPL-3.0',
            'lgpl-2.1': 'LGPL-2.1',
            'lgplv2.1': 'LGPL-2.1',
            'mpl-2.0': 'MPL-2.0',
            'cc0-1.0': 'CC0-1.0',
            'cc0': 'CC0-1.0',
            'unlicense': 'Unlicense',
            'proprietary': 'Proprietary'
        }
        
    def detect(self, component) -> Optional[str]:
        """
        Detect license for a component
        
        Args:
            component: Component object with name and version
            
        Returns:
            SPDX license identifier or None
        """
        # Try to detect from component metadata if available
        if hasattr(component, 'license') and component.license:
            normalized = self._normalize_license(component.license)
            if normalized:
                return normalized
                
        # If component has a path, check for license files
        if hasattr(component, 'path') and component.path:
            license_from_file = self._detect_from_files(Path(component.path))
            if license_from_file:
                return license_from_file
                
        # Check known licenses for popular packages
        known_license = self._check_known_licenses(component.name)
        if known_license:
            return known_license
            
        return None
        
    def _normalize_license(self, license_str: str) -> Optional[str]:
        """
        Normalize a license string to SPDX identifier
        
        Args:
            license_str: Raw license string
            
        Returns:
            SPDX identifier or None
        """
        if not license_str:
            return None
            
        # Direct SPDX match
        if license_str in self.license_patterns.keys():
            return license_str
            
        # Try lowercase mapping
        lower_license = license_str.lower().strip()
        if lower_license in self.metadata_mappings:
            return self.metadata_mappings[lower_license]
            
        # Try pattern matching
        for spdx_id, patterns in self.license_patterns.items():
            for pattern in patterns:
                if re.search(pattern, license_str, re.IGNORECASE):
                    return spdx_id
                    
        return None
        
    def _detect_from_files(self, project_path: Path) -> Optional[str]:
        """
        Detect license from license files in project
        
        Args:
            project_path: Path to project directory
            
        Returns:
            SPDX identifier or None
        """
        common_license_files = [
            'LICENSE', 'LICENSE.txt', 'LICENSE.md',
            'LICENCE', 'LICENCE.txt', 'LICENCE.md',
            'COPYING', 'COPYING.txt', 'COPYING.md',
            'COPYRIGHT', 'COPYRIGHT.txt', 'COPYRIGHT.md'
        ]
        
        for filename in common_license_files:
            license_file = project_path / filename
            if license_file.exists():
                try:
                    with open(license_file, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()
                        
                    # Check content against patterns
                    for spdx_id, patterns in self.license_patterns.items():
                        for pattern in patterns:
                            if re.search(pattern, content, re.IGNORECASE):
                                return spdx_id
                                
                except Exception:
                    continue
                    
        # Check for specific license file names
        for spdx_id, filenames in self.filename_hints.items():
            for filename in filenames:
                if (project_path / filename).exists():
                    return spdx_id
                    
        return None
        
    def _check_known_licenses(self, package_name: str) -> Optional[str]:
        """
        Check known licenses for popular packages
        
        Args:
            package_name: Name of the package
            
        Returns:
            SPDX identifier or None
        """
        # Common known package licenses
        known_licenses = {
            # Python packages
            'django': 'BSD-3-Clause',
            'flask': 'BSD-3-Clause',
            'numpy': 'BSD-3-Clause',
            'pandas': 'BSD-3-Clause',
            'requests': 'Apache-2.0',
            'pytest': 'MIT',
            'scipy': 'BSD-3-Clause',
            'matplotlib': 'BSD-3-Clause',
            'scikit-learn': 'BSD-3-Clause',
            'tensorflow': 'Apache-2.0',
            'pytorch': 'BSD-3-Clause',
            
            # JavaScript packages
            'react': 'MIT',
            'vue': 'MIT',
            'angular': 'MIT',
            'express': 'MIT',
            'webpack': 'MIT',
            'babel': 'MIT',
            'typescript': 'Apache-2.0',
            'jest': 'MIT',
            'mocha': 'MIT',
            'lodash': 'MIT',
            'axios': 'MIT',
            
            # Java packages
            'spring-core': 'Apache-2.0',
            'spring-boot': 'Apache-2.0',
            'junit': 'EPL-2.0',
            'commons-lang': 'Apache-2.0',
            'guava': 'Apache-2.0',
            'jackson-core': 'Apache-2.0',
            'slf4j-api': 'MIT',
            'log4j': 'Apache-2.0',
            
            # Go packages
            'github.com/gin-gonic/gin': 'MIT',
            'github.com/gorilla/mux': 'BSD-3-Clause',
            'github.com/spf13/cobra': 'Apache-2.0',
            'github.com/spf13/viper': 'MIT',
            'github.com/stretchr/testify': 'MIT',
            'github.com/sirupsen/logrus': 'MIT',
            
            # Rust packages
            'serde': 'MIT OR Apache-2.0',
            'tokio': 'MIT',
            'actix-web': 'MIT OR Apache-2.0',
            'diesel': 'MIT OR Apache-2.0',
            'rocket': 'MIT OR Apache-2.0',
            'clap': 'MIT OR Apache-2.0'
        }
        
        # Check exact match
        if package_name in known_licenses:
            return known_licenses[package_name]
            
        # Check partial match for scoped packages
        for known_pkg, license_id in known_licenses.items():
            if package_name.endswith(f"/{known_pkg}") or package_name.endswith(f"\\{known_pkg}"):
                return license_id
                
        return None
        
    def validate_license_compatibility(self, licenses: List[str]) -> Dict[str, Any]:
        """
        Check license compatibility between components
        
        Args:
            licenses: List of SPDX license identifiers
            
        Returns:
            Compatibility report
        """
        # Define license compatibility matrix (simplified)
        compatibility_issues = []
        
        # GPL family is incompatible with many licenses
        gpl_licenses = {'GPL-2.0', 'GPL-3.0', 'LGPL-2.1', 'LGPL-3.0'}
        proprietary = {'Proprietary'}
        
        has_gpl = any(lic in gpl_licenses for lic in licenses)
        has_proprietary = any(lic in proprietary for lic in licenses)
        
        if has_gpl and has_proprietary:
            compatibility_issues.append({
                'severity': 'high',
                'issue': 'GPL and Proprietary licenses are incompatible',
                'affected': list(gpl_licenses.intersection(licenses)) + list(proprietary.intersection(licenses))
            })
            
        # Check for viral licenses
        viral_licenses = {'GPL-2.0', 'GPL-3.0'}
        has_viral = any(lic in viral_licenses for lic in licenses)
        
        if has_viral:
            compatibility_issues.append({
                'severity': 'medium',
                'issue': 'Project contains viral GPL licenses that may affect distribution',
                'affected': list(viral_licenses.intersection(licenses))
            })
            
        return {
            'compatible': len(compatibility_issues) == 0,
            'issues': compatibility_issues,
            'licenses_found': list(set(licenses))
        }