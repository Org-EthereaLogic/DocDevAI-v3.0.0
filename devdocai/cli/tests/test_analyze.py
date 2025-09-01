"""
Tests for analyze command.
"""

import json
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from click.testing import CliRunner

from devdocai.cli.main import cli


class TestAnalyzeCommand:
    """Test analyze command functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.runner = CliRunner()
    
    def test_analyze_help(self):
        """Test analyze command help."""
        result = self.runner.invoke(cli, ['analyze', '--help'])
        assert result.exit_code == 0
        assert 'Analyze documentation quality' in result.output
    
    def test_analyze_document_help(self):
        """Test analyze document subcommand help."""
        result = self.runner.invoke(cli, ['analyze', 'document', '--help'])
        assert result.exit_code == 0
        assert 'Analyze documentation quality' in result.output
        assert '--dimensions' in result.output
        assert '--threshold' in result.output
    
    @patch('devdocai.cli.commands.analyze.QualityAnalyzerUnified')
    def test_analyze_single_document(self, mock_analyzer):
        """Test analyzing a single document."""
        with self.runner.isolated_filesystem():
            # Create test document
            Path('README.md').write_text('# Test\n\nTest documentation content.')
            
            # Mock analyzer
            mock_instance = Mock()
            mock_instance.analyze.return_value = {
                'overall_score': 0.85,
                'dimension_scores': {
                    'completeness': 0.8,
                    'clarity': 0.9,
                    'technical_accuracy': 0.85
                }
            }
            mock_instance.get_suggestions.return_value = ['Add more examples']
            mock_analyzer.return_value = mock_instance
            
            # Run analysis
            result = self.runner.invoke(cli, [
                'analyze', 'document', 'README.md'
            ])
            
            assert result.exit_code == 0
            assert 'Overall Score' in result.output or '0.85' in result.output
            mock_instance.analyze.assert_called_once()
    
    @patch('devdocai.cli.commands.analyze.QualityAnalyzerUnified')
    def test_analyze_with_dimensions(self, mock_analyzer):
        """Test analyzing specific dimensions."""
        with self.runner.isolated_filesystem():
            Path('doc.md').write_text('# Doc')
            
            # Mock analyzer
            mock_instance = Mock()
            mock_instance.analyze.return_value = {
                'overall_score': 0.7,
                'dimension_scores': {'clarity': 0.7}
            }
            mock_analyzer.return_value = mock_instance
            
            # Run with specific dimensions
            result = self.runner.invoke(cli, [
                'analyze', 'document', 'doc.md',
                '-d', 'clarity',
                '-d', 'completeness'
            ])
            
            assert result.exit_code == 0
            mock_instance.analyze.assert_called_with(
                content='# Doc',
                dimensions=['clarity', 'completeness']
            )
    
    @patch('devdocai.cli.commands.analyze.QualityAnalyzerUnified')
    def test_analyze_with_threshold(self, mock_analyzer):
        """Test analysis with quality threshold."""
        with self.runner.isolated_filesystem():
            Path('doc.md').write_text('# Doc')
            
            # Mock analyzer - score below threshold
            mock_instance = Mock()
            mock_instance.analyze.return_value = {
                'overall_score': 0.6,
                'dimension_scores': {}
            }
            mock_analyzer.return_value = mock_instance
            
            # Run with threshold
            result = self.runner.invoke(cli, [
                'analyze', 'document', 'doc.md',
                '--threshold', '0.8'
            ])
            
            assert result.exit_code == 0
            # Should indicate failure to meet threshold
            assert 'FAIL' in result.output or 'threshold' in result.output.lower()
    
    @patch('devdocai.cli.commands.analyze.QualityAnalyzerUnified')
    def test_analyze_detailed(self, mock_analyzer):
        """Test detailed analysis with suggestions."""
        with self.runner.isolated_filesystem():
            Path('doc.md').write_text('# Doc')
            
            # Mock analyzer
            mock_instance = Mock()
            mock_instance.analyze.return_value = {
                'overall_score': 0.75,
                'dimension_scores': {'clarity': 0.75}
            }
            mock_instance.get_suggestions.return_value = [
                'Add more examples',
                'Improve introduction',
                'Add API reference'
            ]
            mock_analyzer.return_value = mock_instance
            
            # Run detailed analysis
            result = self.runner.invoke(cli, [
                'analyze', 'document', 'doc.md',
                '--detailed'
            ])
            
            assert result.exit_code == 0
            assert 'Add more examples' in result.output
            mock_instance.get_suggestions.assert_called_once()
    
    @patch('devdocai.cli.commands.analyze.QualityAnalyzerUnified')
    def test_analyze_json_output(self, mock_analyzer):
        """Test JSON output format."""
        with self.runner.isolated_filesystem():
            Path('doc.md').write_text('# Doc')
            
            # Mock analyzer
            mock_instance = Mock()
            mock_instance.analyze.return_value = {
                'overall_score': 0.8,
                'dimension_scores': {'clarity': 0.8}
            }
            mock_analyzer.return_value = mock_instance
            
            # Run with JSON output
            result = self.runner.invoke(cli, [
                'analyze', 'document', 'doc.md',
                '--format', 'json'
            ])
            
            assert result.exit_code == 0
            # Output should be valid JSON
            data = json.loads(result.output)
            assert isinstance(data, list)
            assert data[0]['overall_score'] == 0.8
    
    @patch('devdocai.cli.commands.analyze.QualityAnalyzerUnified')
    def test_analyze_directory(self, mock_analyzer):
        """Test analyzing all documents in a directory."""
        with self.runner.isolated_filesystem():
            # Create directory with documents
            Path('docs').mkdir()
            Path('docs/doc1.md').write_text('# Doc 1')
            Path('docs/doc2.md').write_text('# Doc 2')
            
            # Mock analyzer
            mock_instance = Mock()
            mock_instance.analyze.return_value = {
                'overall_score': 0.8,
                'dimension_scores': {}
            }
            mock_analyzer.return_value = mock_instance
            
            # Analyze directory
            result = self.runner.invoke(cli, [
                'analyze', 'document', 'docs'
            ])
            
            assert result.exit_code == 0
            # Should analyze both files
            assert mock_instance.analyze.call_count == 2
    
    def test_analyze_batch_help(self):
        """Test analyze batch subcommand help."""
        result = self.runner.invoke(cli, ['analyze', 'batch', '--help'])
        assert result.exit_code == 0
        assert 'Batch analyze' in result.output
    
    @patch('devdocai.cli.commands.analyze.QualityAnalyzerUnified')
    def test_analyze_batch_command(self, mock_analyzer):
        """Test batch analysis command."""
        with self.runner.isolated_filesystem():
            # Create test files
            Path('doc1.md').write_text('# Doc 1')
            Path('doc2.md').write_text('# Doc 2')
            Path('readme.txt').write_text('Not markdown')
            
            # Mock analyzer
            mock_instance = Mock()
            mock_instance.analyze.return_value = {
                'overall_score': 0.75,
                'dimension_scores': {
                    'completeness': 0.7,
                    'clarity': 0.8,
                    'technical_accuracy': 0.75
                }
            }
            mock_analyzer.return_value = mock_instance
            
            # Run batch analysis
            result = self.runner.invoke(cli, [
                'analyze', 'batch', '.',
                '--pattern', '*.md'
            ])
            
            assert result.exit_code == 0
            assert '2' in result.output  # Should find 2 markdown files
            assert mock_instance.analyze.call_count == 2
    
    @patch('devdocai.cli.commands.analyze.QualityAnalyzerUnified')
    def test_analyze_batch_recursive(self, mock_analyzer):
        """Test recursive batch analysis."""
        with self.runner.isolated_filesystem():
            # Create nested structure
            Path('docs').mkdir()
            Path('docs/api').mkdir()
            Path('docs/doc1.md').write_text('# Doc 1')
            Path('docs/api/doc2.md').write_text('# Doc 2')
            
            # Mock analyzer
            mock_instance = Mock()
            mock_instance.analyze.return_value = {'overall_score': 0.8, 'dimension_scores': {}}
            mock_analyzer.return_value = mock_instance
            
            # Run recursive batch
            result = self.runner.invoke(cli, [
                'analyze', 'batch', 'docs',
                '--recursive'
            ])
            
            assert result.exit_code == 0
            assert mock_instance.analyze.call_count == 2
    
    @patch('devdocai.cli.commands.analyze.QualityAnalyzerUnified')
    def test_analyze_batch_export_csv(self, mock_analyzer):
        """Test exporting batch results to CSV."""
        with self.runner.isolated_filesystem():
            Path('doc.md').write_text('# Doc')
            
            # Mock analyzer
            mock_instance = Mock()
            mock_instance.analyze.return_value = {
                'overall_score': 0.8,
                'dimension_scores': {
                    'completeness': 0.8,
                    'clarity': 0.8,
                    'technical_accuracy': 0.8
                }
            }
            mock_analyzer.return_value = mock_instance
            
            # Run with CSV export
            result = self.runner.invoke(cli, [
                'analyze', 'batch', '.',
                '--export', 'results.csv'
            ])
            
            assert result.exit_code == 0
            assert Path('results.csv').exists()
            assert 'exported to results.csv' in result.output
    
    @patch('devdocai.cli.commands.analyze.ANALYZER_AVAILABLE', False)
    def test_analyze_module_not_available(self):
        """Test error when analyzer module not available."""
        with self.runner.isolated_filesystem():
            Path('doc.md').write_text('# Doc')
            
            result = self.runner.invoke(cli, [
                'analyze', 'document', 'doc.md'
            ])
            
            assert result.exit_code != 0
            assert 'not available' in result.output