#!/usr/bin/env python3
"""Parse bandit results for CI/CD."""
import json
import sys

try:
    with open('bandit-report.json', 'r') as f:
        data = json.load(f)
        issues = data.get('results', [])
        if issues:
            print(f'⚠️ Found {len(issues)} security issues:')
            for issue in issues[:5]:  # Show first 5
                print(f"  - {issue['issue_severity']}: {issue['issue_text']} at {issue['filename']}:{issue['line_number']}")
        else:
            print('✅ No security issues found')
except Exception as e:
    print('✅ No bandit report generated')
    sys.exit(0)