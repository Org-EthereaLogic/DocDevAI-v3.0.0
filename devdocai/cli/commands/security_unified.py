"""
Unified Security Command - Security management and operations.
"""

from pathlib import Path
from typing import Optional

import click

from devdocai.cli.config_unified import CLIConfig
from devdocai.security.unified import SecurityManager


def create_command(config: CLIConfig) -> click.Command:
    """Factory function to create security command."""
    
    @click.group(name='security')
    @click.pass_obj
    def security_group(ctx):
        """Security management and operations."""
        if not ctx.config.is_security_enabled():
            ctx.log("Security features not enabled in current mode", "warning")
    
    @security_group.command('scan')
    @click.argument('source', type=click.Path(exists=True))
    @click.option('--type', '-t', 
                  type=click.Choice(['pii', 'vulnerabilities', 'dependencies', 'all']),
                  default='all', help='Scan type')
    @click.option('--output', '-o', type=click.Path(), help='Output report path')
    @click.pass_obj
    def security_scan(ctx, source: str, type: str, output: Optional[str]):
        """Perform security scan on source."""
        if not ctx.config.is_security_enabled():
            raise click.ClickException("Security features not enabled")
        
        try:
            # Create security manager
            manager = SecurityManager(
                operation_mode='ENTERPRISE' if ctx.config.mode.value == 'enterprise' else 'SECURE'
            )
            
            ctx.log(f"Performing {type} security scan...", "info")
            
            # Perform scan
            if type == 'pii':
                results = manager.scan_pii(source)
            elif type == 'vulnerabilities':
                results = manager.scan_vulnerabilities(source)
            elif type == 'dependencies':
                results = manager.scan_dependencies(source)
            else:
                results = manager.comprehensive_scan(source)
            
            # Output results
            if output:
                Path(output).write_text(str(results))
                ctx.log(f"Scan results written to: {output}", "success")
            else:
                ctx.output(results)
            
            # Show summary
            if results.get('issues_found', 0) > 0:
                ctx.log(f"Found {results['issues_found']} security issues", "warning")
            else:
                ctx.log("No security issues found", "success")
            
        except Exception as e:
            ctx.log(str(e), "error")
            raise click.ClickException(str(e))
    
    @security_group.command('audit')
    @click.option('--days', '-d', type=int, default=7, help='Days of audit history')
    @click.option('--severity', '-s',
                  type=click.Choice(['all', 'critical', 'high', 'medium', 'low']),
                  default='all', help='Filter by severity')
    @click.pass_obj
    def audit_log(ctx, days: int, severity: str):
        """View security audit log."""
        if not ctx.config.security.enable_audit:
            raise click.ClickException("Audit logging not enabled")
        
        try:
            from devdocai.cli.utils.security import SecurityAuditLogger
            logger = SecurityAuditLogger()
            
            # Get audit entries
            entries = logger.get_entries(days=days, severity=severity)
            
            # Format output
            ctx.log(f"Audit log entries (last {days} days):", "info")
            for entry in entries:
                ctx.output(entry)
            
            ctx.log(f"Total entries: {len(entries)}", "info")
            
        except Exception as e:
            ctx.log(str(e), "error")
            raise click.ClickException(str(e))
    
    @security_group.command('credentials')
    @click.option('--action', '-a',
                  type=click.Choice(['list', 'add', 'remove', 'rotate']),
                  required=True, help='Credential action')
    @click.option('--name', '-n', help='Credential name')
    @click.option('--value', '-v', help='Credential value (for add)')
    @click.pass_obj
    def manage_credentials(ctx, action: str, name: Optional[str], value: Optional[str]):
        """Manage secure credentials."""
        if not ctx.config.security.enable_credentials:
            raise click.ClickException("Credential management not enabled")
        
        try:
            from devdocai.cli.utils.security import SecureCredentialManager
            cred_manager = SecureCredentialManager()
            
            if action == 'list':
                creds = cred_manager.list_credentials()
                ctx.output({'credentials': creds})
            
            elif action == 'add':
                if not name or not value:
                    raise click.ClickException("Name and value required for add")
                cred_manager.add_credential(name, value)
                ctx.log(f"Credential '{name}' added", "success")
            
            elif action == 'remove':
                if not name:
                    raise click.ClickException("Name required for remove")
                cred_manager.remove_credential(name)
                ctx.log(f"Credential '{name}' removed", "success")
            
            elif action == 'rotate':
                if not name:
                    raise click.ClickException("Name required for rotate")
                new_value = cred_manager.rotate_credential(name)
                ctx.log(f"Credential '{name}' rotated", "success")
            
        except Exception as e:
            ctx.log(str(e), "error")
            raise click.ClickException(str(e))
    
    return security_group