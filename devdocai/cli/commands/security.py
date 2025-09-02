"""
Security operations commands for DevDocAI CLI.

Integrates with M010 Security Module.
"""

import sys
import os
from pathlib import Path
from typing import Optional, List, Dict, Any
import json
from datetime import datetime

import click
from click import Context

# Import M010 Security Module
try:
    from devdocai.security.security_manager_unified import UnifiedSecurityManager
    from devdocai.core.config import ConfigurationManager
    SECURITY_AVAILABLE = True
except ImportError as e:
    SECURITY_AVAILABLE = False
    IMPORT_ERROR = str(e)


@click.group('security', invoke_without_command=True)
@click.pass_context
def security_group(ctx: Context):
    """Security scanning and compliance operations."""
    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())


@security_group.command('scan')
@click.argument('path', type=click.Path(exists=True))
@click.option('--type', '-t', 'scan_type',
              type=click.Choice(['all', 'vulnerabilities', 'pii', 'threats']),
              default='all', help='Type of security scan')
@click.option('--recursive', '-r', is_flag=True,
              help='Scan directories recursively')
@click.option('--output', '-o', type=click.Path(),
              help='Save scan report to file')
@click.option('--format', '-f', type=click.Choice(['json', 'html', 'markdown']),
              default='json', help='Report format')
@click.option('--severity', type=click.Choice(['all', 'critical', 'high', 'medium', 'low']),
              default='all', help='Minimum severity to report')
@click.option('--mode', type=click.Choice(['basic', 'performance', 'secure', 'enterprise']),
              default='secure', help='Operation mode')
@click.pass_obj
def security_scan(cli_ctx, path: str, scan_type: str, recursive: bool,
                  output: Optional[str], format: str, severity: str, mode: str):
    """
    Perform security scan on files or directories.
    
    Examples:
    
        # Scan single file for all issues
        devdocai security scan api.py
        
        # Scan directory for PII
        devdocai security scan docs/ --type pii --recursive
        
        # Generate HTML report
        devdocai security scan src/ --output report.html --format html
        
        # Show only critical issues
        devdocai security scan . --severity critical
    """
    if not SECURITY_AVAILABLE:
        cli_ctx.log(f"Security module not available: {IMPORT_ERROR}", "error")
        sys.exit(1)
    
    try:
        # Initialize security manager
        op_mode = OperationMode[mode.upper()]
        config = SecurityConfig(operation_mode=op_mode)
        security_manager = UnifiedSecurityManager(config)
        
        path_obj = Path(path)
        files_to_scan = []
        
        # Collect files to scan
        if path_obj.is_file():
            files_to_scan = [path_obj]
        else:
            if recursive:
                files_to_scan = list(path_obj.rglob('*'))
            else:
                files_to_scan = list(path_obj.glob('*'))
            
            # Filter only files
            files_to_scan = [f for f in files_to_scan if f.is_file()]
        
        if not files_to_scan:
            cli_ctx.log("No files to scan", "warning")
            return
        
        cli_ctx.log(f"Scanning {len(files_to_scan)} files...", "info")
        
        # Perform scan
        all_findings = []
        
        with click.progressbar(files_to_scan, label='Security scanning') as files:
            for file_path in files:
                try:
                    content = file_path.read_text(errors='ignore')
                    
                    findings = {
                        'file': str(file_path),
                        'timestamp': datetime.now().isoformat(),
                        'issues': []
                    }
                    
                    # Perform requested scans
                    if scan_type in ['all', 'pii']:
                        # PII detection
                        pii_results = security_manager.detect_pii(content)
                        if pii_results and pii_results.get('pii_found'):
                            for pii in pii_results['pii_entities']:
                                findings['issues'].append({
                                    'type': 'pii',
                                    'severity': 'high',
                                    'entity': pii['type'],
                                    'location': pii.get('location', 'unknown'),
                                    'description': f"PII detected: {pii['type']}"
                                })
                    
                    if scan_type in ['all', 'threats']:
                        # Threat detection
                        threat_results = security_manager.detect_threats({
                            'source': str(file_path),
                            'content': content[:1000]  # Analyze first 1000 chars
                        })
                        if threat_results and threat_results.get('threats'):
                            for threat in threat_results['threats']:
                                findings['issues'].append({
                                    'type': 'threat',
                                    'severity': threat.get('severity', 'medium'),
                                    'category': threat.get('type'),
                                    'description': threat.get('description', 'Security threat detected')
                                })
                    
                    if scan_type in ['all', 'vulnerabilities']:
                        # Check for common vulnerabilities
                        vuln_patterns = {
                            'hardcoded_secret': r'(api[_-]?key|secret|password|token)\s*=\s*["\'][^"\']+["\']',
                            'sql_injection': r'(SELECT|INSERT|UPDATE|DELETE).*\+.*["\']',
                            'command_injection': r'(exec|system|eval|subprocess\.call)\s*\(',
                            'path_traversal': r'\.\./|\.\.\\',
                            'xss_vulnerability': r'innerHTML\s*=|document\.write\('
                        }
                        
                        import re
                        for vuln_type, pattern in vuln_patterns.items():
                            if re.search(pattern, content, re.IGNORECASE):
                                findings['issues'].append({
                                    'type': 'vulnerability',
                                    'severity': 'high' if 'secret' in vuln_type else 'medium',
                                    'category': vuln_type,
                                    'description': f"Potential {vuln_type.replace('_', ' ')}"
                                })
                    
                    if findings['issues']:
                        all_findings.append(findings)
                        
                except Exception as e:
                    cli_ctx.log(f"Error scanning {file_path}: {str(e)}", "warning")
        
        # Filter by severity
        if severity != 'all':
            severity_levels = {'critical': 4, 'high': 3, 'medium': 2, 'low': 1}
            min_level = severity_levels[severity]
            
            for finding in all_findings:
                finding['issues'] = [
                    issue for issue in finding['issues']
                    if severity_levels.get(issue['severity'], 0) >= min_level
                ]
            
            all_findings = [f for f in all_findings if f['issues']]
        
        # Generate report
        report = {
            'scan_type': scan_type,
            'total_files': len(files_to_scan),
            'files_with_issues': len(all_findings),
            'total_issues': sum(len(f['issues']) for f in all_findings),
            'severity_filter': severity,
            'findings': all_findings
        }
        
        # Format output
        if format == 'html':
            report_html = _format_security_html(report)
            if output:
                Path(output).write_text(report_html)
                cli_ctx.log(f"HTML report saved to {output}", "success")
            else:
                click.echo(report_html)
                
        elif format == 'markdown':
            report_md = _format_security_markdown(report)
            if output:
                Path(output).write_text(report_md)
                cli_ctx.log(f"Markdown report saved to {output}", "success")
            else:
                click.echo(report_md)
                
        else:  # JSON
            if output:
                with open(output, 'w') as f:
                    json.dump(report, f, indent=2)
                cli_ctx.log(f"JSON report saved to {output}", "success")
            else:
                cli_ctx.output(report)
        
        # Summary
        if report['total_issues'] > 0:
            cli_ctx.log(f"\n⚠️  Found {report['total_issues']} security issues in {report['files_with_issues']} files",
                       "warning")
        else:
            cli_ctx.log("\n✓ No security issues found", "success")
            
    except Exception as e:
        cli_ctx.log(f"Security scan failed: {str(e)}", "error")
        if cli_ctx.debug:
            import traceback
            traceback.print_exc()
        sys.exit(1)


@security_group.command('sbom')
@click.argument('path', type=click.Path(exists=True))
@click.option('--format', '-f', type=click.Choice(['spdx', 'cyclonedx', 'json']),
              default='spdx', help='SBOM format')
@click.option('--output', '-o', type=click.Path(), required=True,
              help='Output file path')
@click.option('--sign', is_flag=True,
              help='Digitally sign the SBOM')
@click.option('--validate', is_flag=True,
              help='Validate dependencies for vulnerabilities')
@click.pass_obj
def security_sbom(cli_ctx, path: str, format: str, output: str, sign: bool, validate: bool):
    """
    Generate Software Bill of Materials (SBOM).
    
    Examples:
    
        # Generate SPDX format SBOM
        devdocai security sbom . --output sbom.spdx
        
        # Generate signed CycloneDX SBOM
        devdocai security sbom src/ --format cyclonedx --output sbom.xml --sign
        
        # Generate and validate
        devdocai security sbom . --output sbom.json --validate
    """
    if not SECURITY_AVAILABLE:
        cli_ctx.log(f"Security module not available: {IMPORT_ERROR}", "error")
        sys.exit(1)
    
    try:
        # Initialize security manager
        config = SecurityConfig(operation_mode=OperationMode.ENTERPRISE)
        security_manager = UnifiedSecurityManager(config)
        
        cli_ctx.log(f"Generating SBOM for {path}...", "info")
        
        # Generate SBOM
        sbom_result = security_manager.generate_sbom(
            project_path=path,
            format=format.upper() if format != 'json' else 'SPDX',
            include_checksums=True,
            sign_document=sign
        )
        
        if not sbom_result or not sbom_result.get('sbom'):
            cli_ctx.log("Failed to generate SBOM", "error")
            sys.exit(1)
        
        # Validate if requested
        if validate:
            cli_ctx.log("Validating dependencies...", "info")
            # This would check against vulnerability databases
            # For now, show placeholder
            cli_ctx.log("Dependency validation is planned for future release", "warning")
        
        # Save SBOM
        output_path = Path(output)
        
        if format == 'json':
            with open(output_path, 'w') as f:
                json.dump(sbom_result['sbom'], f, indent=2)
        else:
            output_path.write_text(sbom_result['sbom'])
        
        cli_ctx.log(f"SBOM saved to {output_path}", "success")
        
        # Show summary
        if 'statistics' in sbom_result:
            stats = sbom_result['statistics']
            cli_ctx.log("\nSBOM Statistics:", "info")
            click.echo(f"  Components: {stats.get('total_components', 0)}")
            click.echo(f"  Dependencies: {stats.get('total_dependencies', 0)}")
            click.echo(f"  Licenses: {stats.get('unique_licenses', 0)}")
            
            if sign:
                click.echo(f"  Signature: {sbom_result.get('signature', 'N/A')[:50]}...")
                
    except Exception as e:
        cli_ctx.log(f"SBOM generation failed: {str(e)}", "error")
        if cli_ctx.debug:
            import traceback
            traceback.print_exc()
        sys.exit(1)


@security_group.command('pii-detect')
@click.argument('path', type=click.Path(exists=True))
@click.option('--languages', '-l', multiple=True,
              type=click.Choice(['en', 'es', 'fr', 'de', 'all']),
              default=['en'], help='Languages to detect')
@click.option('--mask', is_flag=True,
              help='Mask detected PII in output')
@click.option('--output', '-o', type=click.Path(),
              help='Save results to file')
@click.option('--detailed', is_flag=True,
              help='Show detailed PII information')
@click.pass_obj
def security_pii_detect(cli_ctx, path: str, languages: List[str], mask: bool,
                        output: Optional[str], detailed: bool):
    """
    Detect personally identifiable information (PII).
    
    Examples:
    
        # Detect PII in file
        devdocai security pii-detect document.txt
        
        # Multi-language detection
        devdocai security pii-detect data.csv -l en -l es -l fr
        
        # Mask PII in output
        devdocai security pii-detect user_data.json --mask --output masked.json
    """
    if not SECURITY_AVAILABLE:
        cli_ctx.log(f"Security module not available: {IMPORT_ERROR}", "error")
        sys.exit(1)
    
    try:
        # Initialize security manager
        config = SecurityConfig(operation_mode=OperationMode.SECURE)
        security_manager = UnifiedSecurityManager(config)
        
        # Read content
        path_obj = Path(path)
        content = path_obj.read_text()
        
        # Process languages
        if 'all' in languages:
            lang_list = ['en', 'es', 'fr', 'de']
        else:
            lang_list = list(languages)
        
        cli_ctx.log(f"Detecting PII for languages: {', '.join(lang_list)}", "info")
        
        # Detect PII
        all_pii = []
        for lang in lang_list:
            result = security_manager.detect_pii(content, language=lang)
            if result and result.get('pii_found'):
                for entity in result['pii_entities']:
                    entity['language'] = lang
                    all_pii.append(entity)
        
        if not all_pii:
            cli_ctx.log("No PII detected", "success")
            return
        
        # Group by type
        pii_by_type = {}
        for entity in all_pii:
            pii_type = entity['type']
            if pii_type not in pii_by_type:
                pii_by_type[pii_type] = []
            pii_by_type[pii_type].append(entity)
        
        # Display results
        cli_ctx.log(f"\n⚠️  Found {len(all_pii)} PII entities:", "warning")
        
        for pii_type, entities in pii_by_type.items():
            click.echo(f"\n{pii_type} ({len(entities)} found):")
            
            if detailed:
                for entity in entities[:5]:  # Show first 5
                    value = entity.get('value', '<masked>')
                    if mask and not value.startswith('<'):
                        value = value[:3] + '***' + value[-3:] if len(value) > 6 else '***'
                    click.echo(f"  - {value} (confidence: {entity.get('confidence', 0):.1%})")
            else:
                click.echo(f"  Total: {len(entities)} instances")
        
        # Mask content if requested
        if mask:
            masked_content = content
            for entity in all_pii:
                if 'value' in entity:
                    masked_content = masked_content.replace(
                        entity['value'],
                        f"<{entity['type'].upper()}_REDACTED>"
                    )
            
            if output:
                Path(output).write_text(masked_content)
                cli_ctx.log(f"\nMasked content saved to {output}", "success")
            else:
                click.echo("\nMasked content preview:")
                preview = masked_content[:500]
                click.echo(preview)
                if len(masked_content) > 500:
                    click.echo("... (truncated)")
        
        # Save detailed report if output specified
        elif output:
            report = {
                'file': str(path),
                'languages': lang_list,
                'total_pii': len(all_pii),
                'pii_by_type': {k: len(v) for k, v in pii_by_type.items()},
                'entities': all_pii if detailed else None
            }
            
            with open(output, 'w') as f:
                json.dump(report, f, indent=2)
            cli_ctx.log(f"\nPII report saved to {output}", "success")
            
    except Exception as e:
        cli_ctx.log(f"PII detection failed: {str(e)}", "error")
        if cli_ctx.debug:
            import traceback
            traceback.print_exc()
        sys.exit(1)


@security_group.command('compliance')
@click.option('--framework', '-f',
              type=click.Choice(['gdpr', 'owasp', 'soc2', 'iso27001', 'nist', 'all']),
              default='all', help='Compliance framework to check')
@click.option('--output', '-o', type=click.Path(),
              help='Save compliance report')
@click.option('--format', type=click.Choice(['json', 'html', 'pdf']),
              default='json', help='Report format')
@click.pass_obj
def security_compliance(cli_ctx, framework: str, output: Optional[str], format: str):
    """
    Check compliance with security frameworks.
    
    Examples:
    
        # Check all compliance frameworks
        devdocai security compliance
        
        # Check GDPR compliance
        devdocai security compliance --framework gdpr
        
        # Generate HTML report
        devdocai security compliance --output report.html --format html
    """
    if not SECURITY_AVAILABLE:
        cli_ctx.log(f"Security module not available: {IMPORT_ERROR}", "error")
        sys.exit(1)
    
    try:
        # Initialize security manager
        config = SecurityConfig(operation_mode=OperationMode.ENTERPRISE)
        security_manager = UnifiedSecurityManager(config)
        
        cli_ctx.log(f"Checking compliance for: {framework.upper()}", "info")
        
        # Get compliance assessment
        if framework == 'all':
            frameworks = ['GDPR', 'OWASP', 'SOC2', 'ISO27001', 'NIST']
        else:
            frameworks = [framework.upper()]
        
        all_results = {}
        
        for fw in frameworks:
            result = security_manager.assess_compliance(framework=fw)
            if result:
                all_results[fw] = result
        
        # Generate report
        report = {
            'timestamp': datetime.now().isoformat(),
            'frameworks': frameworks,
            'results': all_results,
            'overall_compliance': sum(r.get('score', 0) for r in all_results.values()) / len(all_results) if all_results else 0
        }
        
        # Display results
        cli_ctx.log("\nCompliance Assessment Results:", "info")
        for fw, result in all_results.items():
            score = result.get('score', 0)
            status = "✓" if score >= 0.8 else "⚠️" if score >= 0.6 else "✗"
            click.echo(f"\n{fw}: {status} {score:.1%} compliant")
            
            if 'requirements' in result:
                met = sum(1 for r in result['requirements'] if r.get('met'))
                total = len(result['requirements'])
                click.echo(f"  Requirements: {met}/{total} met")
            
            if 'recommendations' in result and result['recommendations']:
                click.echo(f"  Recommendations:")
                for rec in result['recommendations'][:3]:  # Show top 3
                    click.echo(f"    - {rec}")
        
        # Save report
        if output:
            output_path = Path(output)
            
            if format == 'html':
                html_report = _format_compliance_html(report)
                output_path.write_text(html_report)
            elif format == 'pdf':
                cli_ctx.log("PDF export is planned for future release", "warning")
                # For now, save as JSON
                with open(output_path, 'w') as f:
                    json.dump(report, f, indent=2)
            else:
                with open(output_path, 'w') as f:
                    json.dump(report, f, indent=2)
            
            cli_ctx.log(f"\nCompliance report saved to {output_path}", "success")
            
    except Exception as e:
        cli_ctx.log(f"Compliance check failed: {str(e)}", "error")
        if cli_ctx.debug:
            import traceback
            traceback.print_exc()
        sys.exit(1)


def _format_security_html(report: Dict) -> str:
    """Format security scan report as HTML."""
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Security Scan Report</title>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 20px; }}
            .summary {{ background: #f0f0f0; padding: 15px; margin: 20px 0; }}
            .finding {{ margin: 15px 0; padding: 10px; border-left: 3px solid #ff0000; }}
            .severity-critical {{ border-color: #8b0000; }}
            .severity-high {{ border-color: #ff0000; }}
            .severity-medium {{ border-color: #ff8c00; }}
            .severity-low {{ border-color: #ffd700; }}
        </style>
    </head>
    <body>
        <h1>Security Scan Report</h1>
        <div class="summary">
            <p>Scan Type: {report['scan_type']}</p>
            <p>Total Files: {report['total_files']}</p>
            <p>Files with Issues: {report['files_with_issues']}</p>
            <p>Total Issues: {report['total_issues']}</p>
        </div>
    """
    
    for finding in report['findings']:
        html += f"<h2>{finding['file']}</h2>"
        for issue in finding['issues']:
            severity_class = f"severity-{issue['severity']}"
            html += f"""
            <div class="finding {severity_class}">
                <strong>{issue['type'].upper()}</strong> - {issue['severity']}
                <p>{issue['description']}</p>
            </div>
            """
    
    html += "</body></html>"
    return html


def _format_security_markdown(report: Dict) -> str:
    """Format security scan report as Markdown."""
    lines = []
    lines.append("# Security Scan Report\n")
    lines.append(f"**Scan Type:** {report['scan_type']}  ")
    lines.append(f"**Total Files:** {report['total_files']}  ")
    lines.append(f"**Files with Issues:** {report['files_with_issues']}  ")
    lines.append(f"**Total Issues:** {report['total_issues']}\n")
    
    for finding in report['findings']:
        lines.append(f"\n## {finding['file']}\n")
        for issue in finding['issues']:
            emoji = "🔴" if issue['severity'] == 'critical' else "🟠" if issue['severity'] == 'high' else "🟡"
            lines.append(f"- {emoji} **{issue['type'].upper()}** ({issue['severity']}): {issue['description']}")
    
    return "\n".join(lines)


def _format_compliance_html(report: Dict) -> str:
    """Format compliance report as HTML."""
    overall = report['overall_compliance']
    status_color = "#00ff00" if overall >= 0.8 else "#ffff00" if overall >= 0.6 else "#ff0000"
    
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Compliance Report</title>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 20px; }}
            .overall {{ font-size: 24px; color: {status_color}; margin: 20px 0; }}
            .framework {{ margin: 20px 0; padding: 15px; border: 1px solid #ddd; }}
            .compliant {{ color: green; }}
            .partial {{ color: orange; }}
            .non-compliant {{ color: red; }}
        </style>
    </head>
    <body>
        <h1>Compliance Assessment Report</h1>
        <div class="overall">Overall Compliance: {overall:.1%}</div>
        <p>Generated: {report['timestamp']}</p>
    """
    
    for fw, result in report['results'].items():
        score = result.get('score', 0)
        status_class = 'compliant' if score >= 0.8 else 'partial' if score >= 0.6 else 'non-compliant'
        
        html += f"""
        <div class="framework">
            <h2>{fw}</h2>
            <p class="{status_class}">Compliance Score: {score:.1%}</p>
        """
        
        if 'recommendations' in result:
            html += "<h3>Recommendations:</h3><ul>"
            for rec in result['recommendations']:
                html += f"<li>{rec}</li>"
            html += "</ul>"
        
        html += "</div>"
    
    html += "</body></html>"
    return html