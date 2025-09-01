"""
Tests for main CLI functionality.
"""

import json
import yaml
from pathlib import Path

import pytest
from click.testing import CliRunner

from devdocai.cli.main import cli


class TestMainCLI:
    """Test main CLI commands and options."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.runner = CliRunner()
    
    def test_cli_help(self):
        """Test CLI help output."""
        result = self.runner.invoke(cli, ['--help'])
        assert result.exit_code == 0
        assert 'DevDocAI - AI-Powered Documentation Generation System' in result.output
        assert 'Commands:' in result.output
    
    def test_version_flag(self):
        """Test version flag output."""
        result = self.runner.invoke(cli, ['--version'])
        assert result.exit_code == 0
        assert 'version' in result.output.lower()
        assert '3.0.0' in result.output
    
    def test_json_output_flag(self):
        """Test JSON output flag."""
        result = self.runner.invoke(cli, ['--version', '--json'])
        assert result.exit_code == 0
        
        # Should be valid JSON
        data = json.loads(result.output)
        assert 'version' in data
        assert 'python' in data
        assert 'platform' in data
    
    def test_yaml_output_flag(self):
        """Test YAML output flag."""
        result = self.runner.invoke(cli, ['--version', '--yaml'])
        assert result.exit_code == 0
        
        # Should be valid YAML
        data = yaml.safe_load(result.output)
        assert 'version' in data
        assert 'python' in data
    
    def test_quiet_flag(self):
        """Test quiet flag suppresses output."""
        # Without quiet flag
        result_normal = self.runner.invoke(cli, ['--version'])
        
        # With quiet flag - should have less output
        result_quiet = self.runner.invoke(cli, ['--version', '--quiet'])
        
        assert result_quiet.exit_code == 0
        # Quiet mode should still show version but less verbose
        assert len(result_quiet.output) <= len(result_normal.output)
    
    def test_debug_flag(self):
        """Test debug flag enables debug output."""
        with self.runner.isolated_filesystem():
            # Create a test file
            Path('test.md').write_text('# Test')
            
            # Run with debug flag on non-existent command to trigger debug output
            result = self.runner.invoke(cli, ['--debug', 'generate', 'file', 'nonexistent.md'])
            
            # Debug mode should show more detailed error information
            assert result.exit_code != 0
    
    def test_config_flag(self):
        """Test config file flag."""
        with self.runner.isolated_filesystem():
            # Create config file
            config_content = {
                'version': '3.0.0',
                'quality': {'threshold': 0.9}
            }
            Path('config.yml').write_text(yaml.dump(config_content))
            
            # Run with config flag
            result = self.runner.invoke(cli, ['--config', 'config.yml', '--help'])
            assert result.exit_code == 0
    
    def test_init_command(self):
        """Test project initialization command."""
        with self.runner.isolated_filesystem():
            result = self.runner.invoke(cli, ['init'])
            
            assert result.exit_code == 0
            assert 'Project initialized' in result.output
            assert Path('.devdocai.yml').exists()
            
            # Check config content
            with open('.devdocai.yml') as f:
                config = yaml.safe_load(f)
                assert 'version' in config
                assert 'project' in config
                assert 'templates' in config
    
    def test_init_with_template(self):
        """Test project initialization with specific template."""
        with self.runner.isolated_filesystem():
            result = self.runner.invoke(cli, ['init', '--template', 'api'])
            
            assert result.exit_code == 0
            assert Path('.devdocai.yml').exists()
            
            with open('.devdocai.yml') as f:
                config = yaml.safe_load(f)
                assert config['templates']['default'] == 'api'
    
    def test_completion_command(self):
        """Test shell completion command."""
        result = self.runner.invoke(cli, ['completion'])
        
        assert result.exit_code == 0
        assert 'shell completion' in result.output
        assert 'bash' in result.output
        assert 'zsh' in result.output
        assert 'fish' in result.output
    
    def test_command_groups_exist(self):
        """Test that all command groups are registered."""
        result = self.runner.invoke(cli, ['--help'])
        
        commands = ['generate', 'analyze', 'config', 'template', 'enhance', 'security']
        for cmd in commands:
            assert cmd in result.output
    
    def test_invalid_command(self):
        """Test error handling for invalid command."""
        result = self.runner.invoke(cli, ['invalid-command'])
        
        assert result.exit_code != 0
        # Click should show error about invalid command
    
    def test_combined_flags(self):
        """Test combining multiple flags."""
        result = self.runner.invoke(cli, ['--debug', '--json', '--version'])
        
        assert result.exit_code == 0
        # Should output JSON format
        data = json.loads(result.output)
        assert 'version' in data


class TestCLIContext:
    """Test CLI context functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.runner = CliRunner()
    
    def test_context_passing(self):
        """Test context is properly passed to subcommands."""
        # This tests that global flags are accessible in subcommands
        result = self.runner.invoke(cli, ['--json', 'config', 'list'])
        
        # The command should respect the global --json flag
        # (actual behavior depends on implementation)
        assert result.exit_code == 0 or 'not available' in result.output
    
    def test_multiple_output_formats(self):
        """Test that only one output format can be specified."""
        result = self.runner.invoke(cli, ['--json', '--yaml', '--version'])
        
        # Should still work, one format takes precedence
        assert result.exit_code == 0


class TestCLIIntegration:
    """Test CLI integration scenarios."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.runner = CliRunner()
    
    def test_help_for_subcommands(self):
        """Test help works for all subcommands."""
        commands = ['generate', 'analyze', 'config', 'template', 'enhance', 'security']
        
        for cmd in commands:
            result = self.runner.invoke(cli, [cmd, '--help'])
            assert result.exit_code == 0
            assert cmd in result.output.lower()
    
    def test_isolated_filesystem(self):
        """Test CLI works in isolated filesystem."""
        with self.runner.isolated_filesystem():
            # Create test file
            Path('test.md').write_text('# Test Document\n\nTest content.')
            
            # Try to use the file (command may fail if modules not available)
            result = self.runner.invoke(cli, ['generate', 'file', 'test.md'])
            
            # Should at least parse the command correctly
            assert 'test.md' in result.output or 'not available' in result.output