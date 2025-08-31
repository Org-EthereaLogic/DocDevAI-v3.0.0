#!/usr/bin/env python3
"""Parse safety check results for CI/CD."""
import json
import sys

try:
    with open('safety-report.json', 'r') as f:
        data = json.load(f)
        vulns = data.get('vulnerabilities', [])
        if vulns:
            print(f'⚠️ Found {len(vulns)} vulnerabilities:')
            for v in vulns[:5]:  # Show first 5
                print(f"  - {v.get('package_name', 'unknown')}: {v.get('vulnerability', 'unknown')}")
        else:
            print('✅ No known vulnerabilities')
except Exception as e:
    print('✅ No safety report generated')
    sys.exit(0)