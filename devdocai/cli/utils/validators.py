"""
Input validation utilities for DevDocAI CLI.

Provides validators for paths, templates, configurations, etc.
"""

import os
import re
from pathlib import Path
from typing import Optional, List, Dict, Any

import click


def validate_path(path: str, must_exist: bool = True, 
                  file_okay: bool = True, dir_okay: bool = True) -> Path:
    """
    Validate a file or directory path.
    
    Args:
        path: Path to validate
        must_exist: Whether path must exist
        file_okay: Whether path can be a file
        dir_okay: Whether path can be a directory
        
    Returns:
        Validated Path object
        
    Raises:
        click.BadParameter: If validation fails
    """
    path_obj = Path(path).expanduser().resolve()
    
    if must_exist and not path_obj.exists():
        raise click.BadParameter(f"Path does not exist: {path}")
    
    if path_obj.exists():
        if path_obj.is_file() and not file_okay:
            raise click.BadParameter(f"Path is a file, expected directory: {path}")
        if path_obj.is_dir() and not dir_okay:
            raise click.BadParameter(f"Path is a directory, expected file: {path}")
    
    return path_obj


def validate_template(template_name: str, available_templates: List[str]) -> str:
    """
    Validate template name against available templates.
    
    Args:
        template_name: Template name to validate
        available_templates: List of available template names
        
    Returns:
        Validated template name
        
    Raises:
        click.BadParameter: If template not found
    """
    if template_name not in available_templates:
        # Try case-insensitive match
        lower_templates = {t.lower(): t for t in available_templates}
        if template_name.lower() in lower_templates:
            return lower_templates[template_name.lower()]
        
        # Suggest similar templates
        similar = [t for t in available_templates 
                  if template_name.lower() in t.lower()]
        
        msg = f"Template '{template_name}' not found."
        if similar:
            msg += f" Did you mean one of: {', '.join(similar[:3])}?"
        else:
            msg += f" Available templates: {', '.join(available_templates[:5])}"
            if len(available_templates) > 5:
                msg += f" (and {len(available_templates) - 5} more)"
        
        raise click.BadParameter(msg)
    
    return template_name


def validate_config(config: Dict[str, Any], schema: Optional[Dict] = None) -> Dict:
    """
    Validate configuration dictionary against schema.
    
    Args:
        config: Configuration dictionary
        schema: Optional schema to validate against
        
    Returns:
        Validated configuration
        
    Raises:
        click.BadParameter: If validation fails
    """
    if not config:
        raise click.BadParameter("Configuration cannot be empty")
    
    if schema:
        # Validate required fields
        required = schema.get('required', [])
        for field in required:
            if field not in config:
                raise click.BadParameter(f"Missing required field: {field}")
        
        # Validate field types
        properties = schema.get('properties', {})
        for field, value in config.items():
            if field in properties:
                expected_type = properties[field].get('type')
                if expected_type:
                    if not _check_type(value, expected_type):
                        raise click.BadParameter(
                            f"Invalid type for {field}: expected {expected_type}, "
                            f"got {type(value).__name__}"
                        )
    
    return config


def validate_dimension(dimension: str, available_dimensions: List[str]) -> str:
    """
    Validate quality dimension name.
    
    Args:
        dimension: Dimension name to validate
        available_dimensions: List of available dimensions
        
    Returns:
        Validated dimension name
        
    Raises:
        click.BadParameter: If dimension not valid
    """
    if dimension == 'all':
        return dimension
    
    if dimension not in available_dimensions:
        raise click.BadParameter(
            f"Invalid dimension '{dimension}'. "
            f"Available: {', '.join(available_dimensions)}, all"
        )
    
    return dimension


def validate_file_pattern(pattern: str) -> str:
    """
    Validate file pattern (glob pattern).
    
    Args:
        pattern: File pattern to validate
        
    Returns:
        Validated pattern
        
    Raises:
        click.BadParameter: If pattern invalid
    """
    # Check for invalid characters
    invalid_chars = ['<', '>', ':', '"', '|', '\0']
    for char in invalid_chars:
        if char in pattern:
            raise click.BadParameter(f"Invalid character in pattern: {char}")
    
    # Check for valid glob pattern
    valid_pattern = re.compile(r'^[\w\-\.\*\?\[\]]+$')
    if not valid_pattern.match(pattern):
        raise click.BadParameter(f"Invalid file pattern: {pattern}")
    
    return pattern


def validate_json_string(json_str: str) -> Dict:
    """
    Validate and parse JSON string.
    
    Args:
        json_str: JSON string to validate
        
    Returns:
        Parsed JSON object
        
    Raises:
        click.BadParameter: If JSON invalid
    """
    import json
    
    try:
        return json.loads(json_str)
    except json.JSONDecodeError as e:
        raise click.BadParameter(f"Invalid JSON: {e}")


def validate_yaml_string(yaml_str: str) -> Dict:
    """
    Validate and parse YAML string.
    
    Args:
        yaml_str: YAML string to validate
        
    Returns:
        Parsed YAML object
        
    Raises:
        click.BadParameter: If YAML invalid
    """
    import yaml
    
    try:
        return yaml.safe_load(yaml_str)
    except yaml.YAMLError as e:
        raise click.BadParameter(f"Invalid YAML: {e}")


def validate_url(url: str) -> str:
    """
    Validate URL format.
    
    Args:
        url: URL to validate
        
    Returns:
        Validated URL
        
    Raises:
        click.BadParameter: If URL invalid
    """
    url_pattern = re.compile(
        r'^https?://'  # http:// or https://
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain
        r'localhost|'  # localhost
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # IP
        r'(?::\d+)?'  # optional port
        r'(?:/?|[/?]\S+)$', re.IGNORECASE
    )
    
    if not url_pattern.match(url):
        raise click.BadParameter(f"Invalid URL format: {url}")
    
    return url


def validate_email(email: str) -> str:
    """
    Validate email address format.
    
    Args:
        email: Email to validate
        
    Returns:
        Validated email
        
    Raises:
        click.BadParameter: If email invalid
    """
    email_pattern = re.compile(
        r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    )
    
    if not email_pattern.match(email):
        raise click.BadParameter(f"Invalid email format: {email}")
    
    return email


def validate_version(version: str) -> str:
    """
    Validate semantic version string.
    
    Args:
        version: Version string to validate
        
    Returns:
        Validated version
        
    Raises:
        click.BadParameter: If version invalid
    """
    # Semantic versioning pattern
    version_pattern = re.compile(
        r'^(\d+)\.(\d+)\.(\d+)'
        r'(?:-([0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*))?'
        r'(?:\+([0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*))?$'
    )
    
    if not version_pattern.match(version):
        raise click.BadParameter(
            f"Invalid version format: {version}. "
            "Expected semantic version (e.g., 1.0.0, 2.1.0-beta.1)"
        )
    
    return version


def validate_percentage(value: float) -> float:
    """
    Validate percentage value (0.0-1.0 or 0-100).
    
    Args:
        value: Percentage value
        
    Returns:
        Normalized percentage (0.0-1.0)
        
    Raises:
        click.BadParameter: If value invalid
    """
    # If value is greater than 1, assume it's in 0-100 range
    if value > 1:
        value = value / 100
    
    if not 0 <= value <= 1:
        raise click.BadParameter(
            f"Percentage must be between 0 and 1 (or 0-100), got {value}"
        )
    
    return value


def validate_positive_int(value: int, name: str = "value") -> int:
    """
    Validate positive integer value.
    
    Args:
        value: Integer to validate
        name: Name of value for error message
        
    Returns:
        Validated integer
        
    Raises:
        click.BadParameter: If value invalid
    """
    if value <= 0:
        raise click.BadParameter(f"{name} must be positive, got {value}")
    
    return value


def validate_range(value: float, min_val: float, max_val: float,
                   name: str = "value") -> float:
    """
    Validate value is within range.
    
    Args:
        value: Value to validate
        min_val: Minimum allowed value
        max_val: Maximum allowed value
        name: Name of value for error message
        
    Returns:
        Validated value
        
    Raises:
        click.BadParameter: If value out of range
    """
    if not min_val <= value <= max_val:
        raise click.BadParameter(
            f"{name} must be between {min_val} and {max_val}, got {value}"
        )
    
    return value


def _check_type(value: Any, expected_type: str) -> bool:
    """
    Check if value matches expected type.
    
    Args:
        value: Value to check
        expected_type: Expected type name
        
    Returns:
        True if type matches
    """
    type_map = {
        'string': str,
        'integer': int,
        'number': (int, float),
        'boolean': bool,
        'array': list,
        'object': dict
    }
    
    expected = type_map.get(expected_type)
    if expected:
        return isinstance(value, expected)
    
    return True  # Unknown type, allow