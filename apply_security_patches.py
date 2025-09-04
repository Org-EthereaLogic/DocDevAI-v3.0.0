#!/usr/bin/env python3
"""
Security Patch Script for DevDocAI API Servers
Fixes critical vulnerabilities identified by CodeQL:
1. Debug mode in production (HIGH)
2. Path traversal vulnerabilities (HIGH)
3. Information disclosure via exceptions (MEDIUM)
"""

import os
import re
import sys
from pathlib import Path

# List of all API server files
API_SERVERS = [
    'ai_powered_api_server.py',
    'api_server.py',
    'direct_api_server.py',
    'integrated_api_server.py',
    'production_api_server.py',
    'real_ai_api_server.py',
    'real_api_server.py',
    'simple_api_server.py'
]

def patch_debug_mode(file_path):
    """Replace debug=True with environment-based configuration."""
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Check if already has environment-based debug setting
    if 'FLASK_ENV' in content or 'FLASK_DEBUG' in content:
        print(f"  ✓ {file_path} already has environment-based debug")
        return False
    
    # Add import at the top if not present
    if 'import os' not in content:
        content = 'import os\n' + content
    
    # Replace all instances of debug=True with environment-based setting
    original_content = content
    
    # Pattern to match app.run with debug=True
    patterns = [
        (r'app\.run\(([^)]*?)debug=True([^)]*?)\)',
         r'app.run(\1debug=os.getenv("FLASK_ENV") == "development"\2)'),
        (r'app\.run\(([^)]*?)debug\s*=\s*True([^)]*?)\)',
         r'app.run(\1debug=os.getenv("FLASK_ENV") == "development"\2)'),
    ]
    
    for pattern, replacement in patterns:
        content = re.sub(pattern, replacement, content)
    
    if content != original_content:
        with open(file_path, 'w') as f:
            f.write(content)
        print(f"  ✓ Patched debug mode in {file_path}")
        return True
    return False

def add_path_validation(file_path):
    """Add path traversal protection to file operations."""
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Check if already has path validation
    if 'validate_file_path' in content:
        print(f"  ✓ {file_path} already has path validation")
        return False
    
    # Path validation function to add
    path_validation_code = '''
def validate_file_path(file_path):
    """Validate file path to prevent directory traversal attacks."""
    from pathlib import Path
    
    # Define allowed directories
    ALLOWED_DIRS = [
        '/workspaces/DocDevAI-v3.0.0/documents/',
        '/workspaces/DocDevAI-v3.0.0/templates/',
        '/workspaces/DocDevAI-v3.0.0/data/',
        '/tmp/devdocai/'  # For temporary files
    ]
    
    try:
        # Resolve to absolute path
        requested_path = Path(file_path).resolve()
        
        # Check if path is within allowed directories
        for allowed_dir in ALLOWED_DIRS:
            allowed = Path(allowed_dir).resolve()
            try:
                requested_path.relative_to(allowed)
                return str(requested_path)
            except ValueError:
                continue
        
        # Path is not in any allowed directory
        raise ValueError(f"Access denied: Path outside allowed directories")
    except Exception as e:
        raise ValueError(f"Invalid file path: {str(e)}")
'''
    
    # Add the validation function after imports
    import_section_end = content.find('\n\n')
    if import_section_end > 0:
        content = content[:import_section_end] + '\n' + path_validation_code + content[import_section_end:]
    
    # Replace unsafe file operations
    # Pattern for open() calls with user input
    content = re.sub(
        r'open\(([^,\)]+file_path[^,\)]*)',
        r'open(validate_file_path(\1)',
        content
    )
    
    # Pattern for os.path.exists() with user input
    content = re.sub(
        r'os\.path\.exists\(([^)]*file_path[^)]*)\)',
        r'os.path.exists(validate_file_path(\1))',
        content
    )
    
    with open(file_path, 'w') as f:
        f.write(content)
    print(f"  ✓ Added path validation to {file_path}")
    return True

def add_error_sanitization(file_path):
    """Add error sanitization to prevent information disclosure."""
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Check if already has error sanitization
    if 'safe_error_response' in content:
        print(f"  ✓ {file_path} already has error sanitization")
        return False
    
    # Error sanitization function
    error_sanitization_code = '''
def safe_error_response(error, status_code=500):
    """Return sanitized error response to prevent information disclosure."""
    import logging
    from flask import jsonify
    
    # Log full error details internally
    logging.error(f"API Error: {error}", exc_info=True)
    
    # Generic error messages for clients
    error_messages = {
        400: "Invalid request",
        401: "Authentication required",
        403: "Access denied",
        404: "Resource not found",
        405: "Method not allowed",
        422: "Validation failed",
        429: "Too many requests",
        500: "Internal server error",
        502: "Service temporarily unavailable",
        503: "Service unavailable"
    }
    
    return jsonify({
        'success': False,
        'error': error_messages.get(status_code, "An error occurred"),
        'status_code': status_code
    }), status_code
'''
    
    # Add the sanitization function after imports
    import_section_end = content.find('\n\n')
    if import_section_end > 0:
        # Only add if not already present
        if 'safe_error_response' not in content:
            content = content[:import_section_end] + '\n' + error_sanitization_code + content[import_section_end:]
    
    # Replace unsafe error responses
    # Pattern: 'error': str(e) or 'error': str(error)
    patterns = [
        (r"'error':\s*str\(e\)", "'error': safe_error_response(e)[0].json['error']"),
        (r'"error":\s*str\(e\)', '"error": safe_error_response(e)[0].json["error"]'),
        (r"'error':\s*str\(error\)", "'error': safe_error_response(error)[0].json['error']"),
        (r'"error":\s*str\(error\)', '"error": safe_error_response(error)[0].json["error"]'),
        (r"'message':\s*str\(e\)", "'message': safe_error_response(e)[0].json['error']"),
        (r'"message":\s*str\(e\)', '"message": safe_error_response(e)[0].json["error"]'),
    ]
    
    for pattern, replacement in patterns:
        content = re.sub(pattern, replacement, content)
    
    # Also add proper error handling in except blocks
    content = re.sub(
        r'except Exception as e:\s*\n\s*return jsonify\({',
        'except Exception as e:\n        return safe_error_response(e, 500)\n        # Original unsafe code commented:\n        # return jsonify({',
        content
    )
    
    with open(file_path, 'w') as f:
        f.write(content)
    print(f"  ✓ Added error sanitization to {file_path}")
    return True

def main():
    print("🔒 DevDocAI Security Patch Script")
    print("=" * 50)
    
    patches_applied = 0
    
    for server_file in API_SERVERS:
        if not os.path.exists(server_file):
            print(f"⚠️  {server_file} not found, skipping...")
            continue
        
        print(f"\n📄 Processing {server_file}:")
        
        # Apply patches
        if patch_debug_mode(server_file):
            patches_applied += 1
        
        if 'real_ai_api_server.py' in server_file:
            # Apply path validation only to the file with the vulnerability
            if add_path_validation(server_file):
                patches_applied += 1
        
        if add_error_sanitization(server_file):
            patches_applied += 1
    
    print("\n" + "=" * 50)
    print(f"✅ Security patches applied: {patches_applied}")
    print("\n📋 Next steps:")
    print("1. Review the patched files")
    print("2. Test the API servers to ensure they still work")
    print("3. Run security tests to verify vulnerabilities are fixed")
    print("4. Commit the security fixes")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())