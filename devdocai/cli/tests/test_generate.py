"""
Tests for generate command.
"""

import json
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

import pytest
from click.testing import CliRunner

from devdocai.cli.main import cli


class TestGenerateCommand:
    """Test generate command functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.runner = CliRunner()
    
    def test_generate_help(self):
        """Test generate command help."""
        result = self.runner.invoke(cli, ['generate', '--help'])
        assert result.exit_code == 0
        assert 'Generate documentation' in result.output
    
    def test_generate_file_help(self):
        """Test generate file subcommand help."""
        result = self.runner.invoke(cli, ['generate', 'file', '--help'])
        assert result.exit_code == 0
        assert 'Generate documentation for a file' in result.output
        assert '--template' in result.output
        assert '--output' in result.output
    
    @patch('devdocai.cli.commands.generate.DocumentGeneratorUnified')
    @patch('devdocai.cli.commands.generate.TemplateRegistryUnified')
    def test_generate_single_file(self, mock_registry, mock_generator):
        """Test generating documentation for a single file."""
        with self.runner.isolated_filesystem():
            # Create test file
            test_file = Path('test.py')
            test_file.write_text('def hello():\n    return "world"')
            
            # Mock generator and registry
            mock_gen_instance = Mock()
            mock_gen_instance.generate.return_value = '# Documentation\n\nGenerated docs'
            mock_generator.return_value = mock_gen_instance
            
            mock_reg_instance = Mock()
            mock_template = Mock()
            mock_template.content = 'Template content'
            mock_reg_instance.get_template.return_value = mock_template
            mock_registry.return_value = mock_reg_instance
            
            # Run command
            result = self.runner.invoke(cli, [
                'generate', 'file', 'test.py',
                '--template', 'general'
            ])
            
            assert result.exit_code == 0
            assert 'Generated docs' in result.output
            mock_gen_instance.generate.assert_called_once()
    
    @patch('devdocai.cli.commands.generate.DocumentGeneratorUnified')
    @patch('devdocai.cli.commands.generate.TemplateRegistryUnified')
    def test_generate_with_output_file(self, mock_registry, mock_generator):
        """Test generating documentation with output file."""
        with self.runner.isolated_filesystem():
            # Create test file
            test_file = Path('test.py')
            test_file.write_text('def hello():\n    return "world"')
            
            # Mock generator
            mock_gen_instance = Mock()
            mock_gen_instance.generate.return_value = '# Documentation'
            mock_generator.return_value = mock_gen_instance
            
            mock_reg_instance = Mock()
            mock_template = Mock()
            mock_template.content = 'Template'
            mock_reg_instance.get_template.return_value = mock_template
            mock_registry.return_value = mock_reg_instance
            
            # Run command with output
            result = self.runner.invoke(cli, [
                'generate', 'file', 'test.py',
                '--output', 'docs.md'
            ])
            
            assert result.exit_code == 0
            assert Path('docs.md').exists()
            assert 'saved to docs.md' in result.output
    
    @patch('devdocai.cli.commands.generate.DocumentGeneratorUnified')
    @patch('devdocai.cli.commands.generate.TemplateRegistryUnified')
    def test_generate_batch(self, mock_registry, mock_generator):
        """Test batch generation for multiple files."""
        with self.runner.isolated_filesystem():
            # Create test files
            Path('file1.py').write_text('def func1(): pass')
            Path('file2.py').write_text('def func2(): pass')
            Path('file3.py').write_text('def func3(): pass')
            
            # Mock generator
            mock_gen_instance = Mock()
            mock_gen_instance.generate.return_value = '# Docs'
            mock_generator.return_value = mock_gen_instance
            
            mock_reg_instance = Mock()
            mock_template = Mock()
            mock_template.content = 'Template'
            mock_reg_instance.get_template.return_value = mock_template
            mock_registry.return_value = mock_reg_instance
            
            # Run batch generation
            result = self.runner.invoke(cli, [
                'generate', 'file', '.',
                '--batch',
                '--pattern', '*.py'
            ])
            
            assert result.exit_code == 0
            assert '3 files' in result.output or 'Found 3' in result.output
            assert mock_gen_instance.generate.call_count == 3
    
    def test_generate_file_not_found(self):
        """Test error when file not found."""
        result = self.runner.invoke(cli, [
            'generate', 'file', 'nonexistent.py'
        ])
        
        assert result.exit_code != 0
        assert 'does not exist' in result.output
    
    @patch('devdocai.cli.commands.generate.GENERATOR_AVAILABLE', False)
    def test_generate_module_not_available(self):
        """Test error when generator module not available."""
        with self.runner.isolated_filesystem():
            Path('test.py').write_text('code')
            
            result = self.runner.invoke(cli, [
                'generate', 'file', 'test.py'
            ])
            
            assert result.exit_code != 0
            assert 'not available' in result.output
    
    def test_generate_api_help(self):
        """Test generate api subcommand help."""
        result = self.runner.invoke(cli, ['generate', 'api', '--help'])
        assert result.exit_code == 0
        assert 'API documentation' in result.output
    
    def test_generate_database_help(self):
        """Test generate database subcommand help."""
        result = self.runner.invoke(cli, ['generate', 'database', '--help'])
        assert result.exit_code == 0
        assert 'database documentation' in result.output


class TestGenerateFormats:
    """Test different output formats for generate command."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.runner = CliRunner()
    
    @patch('devdocai.cli.commands.generate.DocumentGeneratorUnified')
    @patch('devdocai.cli.commands.generate.TemplateRegistryUnified')
    def test_generate_json_format(self, mock_registry, mock_generator):
        """Test generating documentation in JSON format."""
        with self.runner.isolated_filesystem():
            Path('test.py').write_text('code')
            
            # Mock generator
            mock_gen_instance = Mock()
            mock_gen_instance.generate.return_value = '{"doc": "content"}'
            mock_generator.return_value = mock_gen_instance
            
            mock_reg_instance = Mock()
            mock_template = Mock()
            mock_template.content = 'Template'
            mock_reg_instance.get_template.return_value = mock_template
            mock_registry.return_value = mock_reg_instance
            
            result = self.runner.invoke(cli, [
                'generate', 'file', 'test.py',
                '--format', 'json'
            ])
            
            assert result.exit_code == 0
            mock_gen_instance.generate.assert_called_with(
                source_code='code',
                template='Template',
                context=dict,
                output_format='json'
            )
    
    @patch('devdocai.cli.commands.generate.DocumentGeneratorUnified')
    @patch('devdocai.cli.commands.generate.TemplateRegistryUnified') 
    def test_generate_html_format(self, mock_registry, mock_generator):
        """Test generating documentation in HTML format."""
        with self.runner.isolated_filesystem():
            Path('test.py').write_text('code')
            
            # Mock generator
            mock_gen_instance = Mock()
            mock_gen_instance.generate.return_value = '<html><body>Docs</body></html>'
            mock_generator.return_value = mock_gen_instance
            
            mock_reg_instance = Mock()
            mock_template = Mock()
            mock_template.content = 'Template'
            mock_reg_instance.get_template.return_value = mock_template
            mock_registry.return_value = mock_reg_instance
            
            result = self.runner.invoke(cli, [
                'generate', 'file', 'test.py',
                '--format', 'html',
                '--output', 'docs.html'
            ])
            
            assert result.exit_code == 0
            assert Path('docs.html').exists()


class TestGenerateModes:
    """Test different operation modes for generate command."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.runner = CliRunner()
    
    @patch('devdocai.cli.commands.generate.DocumentGeneratorUnified')
    @patch('devdocai.cli.commands.generate.TemplateRegistryUnified')
    def test_generate_basic_mode(self, mock_registry, mock_generator):
        """Test generation in basic mode."""
        with self.runner.isolated_filesystem():
            Path('test.py').write_text('code')
            
            # Mock will be called with BASIC mode
            mock_generator.return_value = Mock(generate=Mock(return_value='Docs'))
            mock_registry.return_value = Mock(get_template=Mock(return_value=Mock(content='T')))
            
            result = self.runner.invoke(cli, [
                'generate', 'file', 'test.py',
                '--mode', 'basic'
            ])
            
            assert result.exit_code == 0
            # Check that OperationMode.BASIC was used
            mock_generator.assert_called()
    
    @patch('devdocai.cli.commands.generate.DocumentGeneratorUnified')
    @patch('devdocai.cli.commands.generate.TemplateRegistryUnified')
    def test_generate_secure_mode(self, mock_registry, mock_generator):
        """Test generation in secure mode."""
        with self.runner.isolated_filesystem():
            Path('test.py').write_text('code')
            
            mock_generator.return_value = Mock(generate=Mock(return_value='Docs'))
            mock_registry.return_value = Mock(get_template=Mock(return_value=Mock(content='T')))
            
            result = self.runner.invoke(cli, [
                'generate', 'file', 'test.py',
                '--mode', 'secure'
            ])
            
            assert result.exit_code == 0
            mock_generator.assert_called()