"""
Migration script for transitioning from separate implementations to unified generator.

This module provides tools and utilities to migrate existing code that uses
the three separate implementations to the new unified implementation.
"""

import logging
import re
from pathlib import Path
from typing import List, Dict, Any, Optional
import ast
import json

logger = logging.getLogger(__name__)


class GeneratorMigration:
    """
    Handles migration from old generator implementations to unified.
    
    This class provides methods to:
    1. Update imports in existing code
    2. Convert old configuration to new format
    3. Map old API calls to new ones
    4. Validate migration completeness
    """
    
    # Import mappings from old to new
    IMPORT_MAPPINGS = {
        "from devdocai.generator.ai_document_generator import AIDocumentGenerator": 
            "from devdocai.generator.unified.generator import UnifiedAIDocumentGenerator as AIDocumentGenerator",
        
        "from devdocai.generator.ai_document_generator_optimized import OptimizedAIDocumentGenerator":
            "from devdocai.generator.unified.generator import UnifiedAIDocumentGenerator as OptimizedAIDocumentGenerator",
        
        "from devdocai.generator.ai_document_generator_secure import SecureAIDocumentGenerator":
            "from devdocai.generator.unified.generator import UnifiedAIDocumentGenerator as SecureAIDocumentGenerator",
        
        "from devdocai.generator.cache_manager import CacheManager":
            "from devdocai.generator.unified.component_factory import UnifiedCacheManager as CacheManager",
        
        "from devdocai.generator.security.prompt_guard import PromptGuard":
            "from devdocai.generator.unified.security import PromptGuard",
        
        "from devdocai.generator.security.rate_limiter import GenerationRateLimiter":
            "from devdocai.generator.unified.security import RateLimiter as GenerationRateLimiter"
    }
    
    # Class instantiation mappings
    CLASS_MAPPINGS = {
        "AIDocumentGenerator": {
            "new_class": "UnifiedAIDocumentGenerator",
            "mode": "BASIC",
            "notes": "Basic mode provides core functionality"
        },
        "OptimizedAIDocumentGenerator": {
            "new_class": "UnifiedAIDocumentGenerator", 
            "mode": "PERFORMANCE",
            "notes": "Performance mode includes caching and optimization"
        },
        "SecureAIDocumentGenerator": {
            "new_class": "UnifiedAIDocumentGenerator",
            "mode": "SECURE",
            "notes": "Secure mode includes all security features"
        }
    }
    
    def __init__(self, dry_run: bool = True):
        """
        Initialize migration tool.
        
        Args:
            dry_run: If True, only report changes without modifying files
        """
        self.dry_run = dry_run
        self.migration_report = {
            "files_analyzed": 0,
            "files_modified": 0,
            "imports_updated": 0,
            "instantiations_updated": 0,
            "warnings": [],
            "errors": []
        }
    
    def migrate_file(self, file_path: Path) -> bool:
        """
        Migrate a single Python file.
        
        Args:
            file_path: Path to the file to migrate
        
        Returns:
            True if migration successful, False otherwise
        """
        try:
            logger.info(f"Analyzing {file_path}")
            self.migration_report["files_analyzed"] += 1
            
            with open(file_path, 'r') as f:
                original_content = f.read()
            
            # Update imports
            modified_content = self._update_imports(original_content)
            
            # Update class instantiations
            modified_content = self._update_instantiations(modified_content)
            
            # Check if file was modified
            if modified_content != original_content:
                if not self.dry_run:
                    # Backup original
                    backup_path = file_path.with_suffix('.bak')
                    with open(backup_path, 'w') as f:
                        f.write(original_content)
                    
                    # Write modified content
                    with open(file_path, 'w') as f:
                        f.write(modified_content)
                    
                    logger.info(f"Modified {file_path} (backup: {backup_path})")
                else:
                    logger.info(f"Would modify {file_path} (dry run)")
                
                self.migration_report["files_modified"] += 1
                return True
            
            return False
            
        except Exception as e:
            error_msg = f"Error migrating {file_path}: {e}"
            logger.error(error_msg)
            self.migration_report["errors"].append(error_msg)
            return False
    
    def _update_imports(self, content: str) -> str:
        """Update import statements."""
        modified = content
        
        for old_import, new_import in self.IMPORT_MAPPINGS.items():
            if old_import in modified:
                modified = modified.replace(old_import, new_import)
                self.migration_report["imports_updated"] += 1
                logger.debug(f"Updated import: {old_import}")
        
        return modified
    
    def _update_instantiations(self, content: str) -> str:
        """Update class instantiations to include mode parameter."""
        modified = content
        
        for old_class, mapping in self.CLASS_MAPPINGS.items():
            # Pattern to match class instantiation
            pattern = rf"{old_class}\s*\("
            
            if re.search(pattern, content):
                # Add mode parameter to instantiation
                replacement = f"{mapping['new_class']}(mode=GenerationMode.{mapping['mode']}, "
                
                # Simple replacement (may need refinement for complex cases)
                modified = re.sub(
                    pattern,
                    replacement,
                    modified
                )
                
                # Ensure GenerationMode is imported
                if "from devdocai.generator.unified.config import GenerationMode" not in modified:
                    # Add import at the top
                    import_line = "from devdocai.generator.unified.config import GenerationMode\n"
                    modified = import_line + modified
                
                self.migration_report["instantiations_updated"] += 1
                
                # Add warning about mode selection
                warning = f"Check {old_class} instantiation - mode set to {mapping['mode']}"
                self.migration_report["warnings"].append(warning)
                logger.warning(warning)
        
        return modified
    
    def migrate_directory(self, directory: Path) -> Dict[str, Any]:
        """
        Migrate all Python files in a directory.
        
        Args:
            directory: Path to directory to migrate
        
        Returns:
            Migration report dictionary
        """
        logger.info(f"Starting migration of {directory}")
        
        python_files = list(directory.glob("**/*.py"))
        
        for file_path in python_files:
            # Skip migration files and tests
            if "migration" in str(file_path) or "__pycache__" in str(file_path):
                continue
            
            self.migrate_file(file_path)
        
        return self.migration_report
    
    def generate_migration_report(self) -> str:
        """Generate a detailed migration report."""
        report = []
        report.append("=" * 60)
        report.append("GENERATOR MIGRATION REPORT")
        report.append("=" * 60)
        report.append(f"\nMode: {'DRY RUN' if self.dry_run else 'LIVE'}")
        report.append(f"Files analyzed: {self.migration_report['files_analyzed']}")
        report.append(f"Files modified: {self.migration_report['files_modified']}")
        report.append(f"Imports updated: {self.migration_report['imports_updated']}")
        report.append(f"Instantiations updated: {self.migration_report['instantiations_updated']}")
        
        if self.migration_report["warnings"]:
            report.append("\nWARNINGS:")
            for warning in self.migration_report["warnings"]:
                report.append(f"  - {warning}")
        
        if self.migration_report["errors"]:
            report.append("\nERRORS:")
            for error in self.migration_report["errors"]:
                report.append(f"  - {error}")
        
        report.append("\n" + "=" * 60)
        
        return "\n".join(report)
    
    def save_report(self, path: Path):
        """Save migration report to file."""
        report_data = {
            **self.migration_report,
            "dry_run": self.dry_run,
            "timestamp": datetime.now().isoformat()
        }
        
        with open(path, 'w') as f:
            json.dump(report_data, f, indent=2)
        
        logger.info(f"Migration report saved to {path}")


class ConfigurationConverter:
    """
    Converts old configuration formats to unified configuration.
    """
    
    @staticmethod
    def convert_basic_config(old_config: Dict[str, Any]) -> Dict[str, Any]:
        """Convert basic generator configuration."""
        return {
            "mode": "basic",
            "template_dir": old_config.get("template_dir"),
            "output_dir": old_config.get("output_dir"),
            "enable_miair_optimization": old_config.get("enable_miair", True),
            "enable_quality_checks": old_config.get("quality_checks", True)
        }
    
    @staticmethod
    def convert_optimized_config(old_config: Dict[str, Any]) -> Dict[str, Any]:
        """Convert optimized generator configuration."""
        return {
            "mode": "performance",
            "cache": {
                "enabled": True,
                "semantic_cache_size": old_config.get("semantic_cache_size", 2000),
                "fragment_cache_size": old_config.get("fragment_cache_size", 10000),
                "ttl_seconds": old_config.get("cache_ttl", 7200)
            },
            "performance": {
                "enabled": True,
                "parallel_generation": old_config.get("parallel", True),
                "token_optimization_enabled": old_config.get("optimize_tokens", True),
                "streaming_enabled": old_config.get("streaming", True)
            },
            "llm": {
                "multi_llm_synthesis": old_config.get("multi_llm", True)
            }
        }
    
    @staticmethod
    def convert_secure_config(old_config: Dict[str, Any]) -> Dict[str, Any]:
        """Convert secure generator configuration."""
        return {
            "mode": "secure",
            "security": {
                "enabled": True,
                "rate_limiting_enabled": old_config.get("rate_limiting", True),
                "prompt_injection_detection": old_config.get("injection_detection", True),
                "pii_detection_enabled": old_config.get("pii_detection", True),
                "pii_redaction_enabled": old_config.get("pii_redaction", True),
                "audit_logging_enabled": old_config.get("audit_logging", True),
                "access_control_enabled": old_config.get("access_control", True)
            },
            "cache": {
                "encryption_enabled": old_config.get("encrypt_cache", True)
            }
        }


def migrate_codebase(
    root_dir: Path,
    dry_run: bool = True,
    exclude_dirs: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Migrate an entire codebase to use unified generator.
    
    Args:
        root_dir: Root directory of the codebase
        dry_run: If True, only report changes without modifying
        exclude_dirs: List of directory names to exclude
    
    Returns:
        Migration report
    """
    exclude_dirs = exclude_dirs or ["__pycache__", ".git", "node_modules", "venv"]
    
    migrator = GeneratorMigration(dry_run=dry_run)
    
    # Find all Python files
    python_files = []
    for file_path in Path(root_dir).glob("**/*.py"):
        # Check exclusions
        if any(exclude in str(file_path) for exclude in exclude_dirs):
            continue
        
        python_files.append(file_path)
    
    logger.info(f"Found {len(python_files)} Python files to analyze")
    
    # Migrate each file
    for file_path in python_files:
        migrator.migrate_file(file_path)
    
    # Generate and print report
    report = migrator.generate_migration_report()
    print(report)
    
    # Save report
    report_path = root_dir / "migration_report.json"
    migrator.save_report(report_path)
    
    return migrator.migration_report


if __name__ == "__main__":
    """
    Command-line interface for migration.
    
    Usage:
        python migration.py --dry-run  # Preview changes
        python migration.py --apply     # Apply changes
    """
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Migrate to unified document generator"
    )
    parser.add_argument(
        "--path",
        type=Path,
        default=Path.cwd(),
        help="Path to migrate (default: current directory)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview changes without modifying files"
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Apply changes (modifies files)"
    )
    
    args = parser.parse_args()
    
    if not args.dry_run and not args.apply:
        print("Error: Specify either --dry-run or --apply")
        exit(1)
    
    if args.dry_run and args.apply:
        print("Error: Cannot specify both --dry-run and --apply")
        exit(1)
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    # Run migration
    migrate_codebase(
        root_dir=args.path,
        dry_run=args.dry_run
    )