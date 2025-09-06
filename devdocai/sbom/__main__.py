"""
SBOM Generator CLI Interface
Enables command-line usage: python -m devdocai.sbom
"""

import sys
import json
import argparse
from pathlib import Path
from typing import Optional

from .sbom_generator import SBOMGenerator
from .signer import Ed25519Signer


def main():
    """Main CLI entry point for SBOM Generator"""
    parser = argparse.ArgumentParser(
        description='DevDocAI SBOM Generator - Generate Software Bill of Materials',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Generate SBOM for current directory
  python -m devdocai.sbom --generate

  # Generate SBOM for specific project
  python -m devdocai.sbom --generate --project /path/to/project

  # Generate CycloneDX format SBOM
  python -m devdocai.sbom --generate --format cyclonedx

  # Export SBOM to file
  python -m devdocai.sbom --generate --output sbom.json

  # Verify SBOM signature
  python -m devdocai.sbom --verify sbom.json
        """
    )
    
    # Action arguments
    action_group = parser.add_mutually_exclusive_group(required=True)
    action_group.add_argument(
        '--generate', '-g',
        action='store_true',
        help='Generate SBOM for a project'
    )
    action_group.add_argument(
        '--verify', '-v',
        metavar='SBOM_FILE',
        help='Verify SBOM signature'
    )
    action_group.add_argument(
        '--info',
        action='store_true',
        help='Show SBOM generator information'
    )
    
    # Options
    parser.add_argument(
        '--project', '-p',
        default='.',
        help='Project path to analyze (default: current directory)'
    )
    parser.add_argument(
        '--format', '-f',
        choices=['spdx', 'cyclonedx'],
        default='spdx',
        help='SBOM format (default: spdx)'
    )
    parser.add_argument(
        '--output', '-o',
        help='Output file path (default: stdout)'
    )
    parser.add_argument(
        '--key',
        help='Path to Ed25519 private key for signing'
    )
    parser.add_argument(
        '--no-sign',
        action='store_true',
        help='Skip digital signature'
    )
    parser.add_argument(
        '--pretty',
        action='store_true',
        help='Pretty print JSON output'
    )
    
    args = parser.parse_args()
    
    try:
        if args.info:
            show_info()
            return 0
            
        elif args.generate:
            return generate_sbom(args)
            
        elif args.verify:
            return verify_sbom(args.verify)
            
    except KeyboardInterrupt:
        print("\nOperation cancelled by user")
        return 130
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


def show_info():
    """Display SBOM generator information"""
    print("""
╔════════════════════════════════════════════════╗
║     DevDocAI SBOM Generator (M010) v3.5.0     ║
╠════════════════════════════════════════════════╣
║                                                ║
║  Software Bill of Materials Generation        ║
║  Per SDD Section 5.5 Specifications           ║
║                                                ║
║  Features:                                     ║
║  • SPDX 2.3 compliant SBOM generation        ║
║  • CycloneDX 1.4 format support              ║
║  • Ed25519 digital signatures                 ║
║  • Dependency analysis for multiple langs     ║
║  • License compliance checking                ║
║  • Vulnerability scanning                     ║
║                                                ║
║  Supported Ecosystems:                        ║
║  • Python (requirements.txt, pyproject.toml)  ║
║  • Node.js (package.json)                     ║
║  • Rust (Cargo.toml)                          ║
║  • Java (pom.xml, build.gradle)               ║
║  • Go (go.mod)                                 ║
║                                                ║
╚════════════════════════════════════════════════╝
    """)


def generate_sbom(args) -> int:
    """
    Generate SBOM for project
    
    Args:
        args: Command line arguments
        
    Returns:
        Exit code (0 for success)
    """
    project_path = Path(args.project).resolve()
    
    if not project_path.exists():
        print(f"Error: Project path does not exist: {project_path}", file=sys.stderr)
        return 1
        
    if not project_path.is_dir():
        print(f"Error: Project path is not a directory: {project_path}", file=sys.stderr)
        return 1
        
    print(f"\n═══ DevDocAI SBOM Generator v3.5.0 ═══")
    print(f"Project: {project_path}")
    print(f"Format: {args.format.upper()}")
    print()
    
    # Initialize generator
    generator = SBOMGenerator()
    
    # Generate SBOM
    try:
        sbom = generator.generate(str(project_path), format=args.format)
        
        # Remove signature if --no-sign specified
        if args.no_sign and 'signature' in sbom:
            del sbom['signature']
            print("Signature: Skipped")
        elif 'signature' in sbom:
            print(f"Signature: Ed25519 signed at {sbom['signature']['timestamp']}")
            
        # Validate SBOM structure
        if generator.validate_sbom(sbom):
            print("Validation: ✓ SBOM structure valid")
        else:
            print("Validation: ✗ SBOM structure invalid", file=sys.stderr)
            return 1
            
        # Generate vulnerability report
        if 'vulnerabilities' in sbom and sbom['vulnerabilities']:
            from .vulnerability_scanner import VulnerabilityScanner
            scanner = VulnerabilityScanner()
            
            # Convert vulnerability dicts back to objects for report
            from .sbom_generator import Vulnerability
            vuln_objects = []
            for v in sbom['vulnerabilities']:
                vuln_objects.append(Vulnerability(
                    id=v.get('id', 'unknown'),
                    source=v.get('source', 'unknown'),
                    severity=v.get('severity', 'unknown'),
                    description=v.get('description', ''),
                    affected_components=v.get('affectedPackages', v.get('affects', [])),
                    cve=v.get('cve'),
                    cvss_score=v.get('cvssScore'),
                    fix_available=v.get('fixAvailable', False),
                    fix_version=v.get('fixVersion')
                ))
                
            report = scanner.generate_vulnerability_report(vuln_objects)
            print(f"\nVulnerability Report:")
            print(f"  Total: {report['total']}")
            if report['by_severity']:
                print(f"  By Severity:")
                for sev, count in report['by_severity'].items():
                    if count > 0:
                        print(f"    - {sev.capitalize()}: {count}")
            if report['fix_available'] > 0:
                print(f"  Fixes Available: {report['fix_available']}")
                
        # Output SBOM
        if args.output:
            output_path = Path(args.output)
            generator.export_sbom(sbom, str(output_path))
            print(f"\n✓ SBOM exported to: {output_path}")
        else:
            # Print to stdout
            if args.pretty:
                print("\n" + json.dumps(sbom, indent=2))
            else:
                print("\n" + json.dumps(sbom))
                
        print(f"\n✓ SBOM generation complete")
        return 0
        
    except Exception as e:
        print(f"\n✗ SBOM generation failed: {e}", file=sys.stderr)
        return 1


def verify_sbom(sbom_file: str) -> int:
    """
    Verify SBOM signature
    
    Args:
        sbom_file: Path to SBOM file
        
    Returns:
        Exit code (0 for success)
    """
    sbom_path = Path(sbom_file)
    
    if not sbom_path.exists():
        print(f"Error: SBOM file not found: {sbom_path}", file=sys.stderr)
        return 1
        
    print(f"\n═══ SBOM Signature Verification ═══")
    print(f"File: {sbom_path}")
    
    try:
        # Load SBOM
        with open(sbom_path, 'r') as f:
            sbom_with_sig = json.load(f)
            
        # Check for signature
        if 'signature' not in sbom_with_sig:
            print("\n✗ No signature found in SBOM", file=sys.stderr)
            return 1
            
        # Extract signature and document
        signature_block = sbom_with_sig['signature']
        sbom_doc = {k: v for k, v in sbom_with_sig.items() if k != 'signature'}
        
        print(f"\nSignature Details:")
        print(f"  Algorithm: {signature_block.get('algorithm', 'unknown')}")
        print(f"  Timestamp: {signature_block.get('timestamp', 'unknown')}")
        print(f"  Signer: {signature_block.get('signer', {}).get('tool', 'unknown')}")
        
        # Verify signature
        signer = Ed25519Signer()
        if signer.verify(sbom_doc, signature_block):
            print(f"\n✓ Signature verification PASSED")
            print(f"  Document hash verified: {signature_block.get('document_hash', 'unknown')[:16]}...")
            return 0
        else:
            print(f"\n✗ Signature verification FAILED", file=sys.stderr)
            return 1
            
    except json.JSONDecodeError as e:
        print(f"\n✗ Invalid JSON in SBOM file: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"\n✗ Verification failed: {e}", file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())