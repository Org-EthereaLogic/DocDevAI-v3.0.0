"""
Unit tests for Quality Dimension Analyzers.
"""

import pytest
from devdocai.quality.dimensions import (
    CompletenessAnalyzer, ClarityAnalyzer, StructureAnalyzer,
    AccuracyAnalyzer, FormattingAnalyzer
)
from devdocai.quality.models import QualityDimension, SeverityLevel


class TestCompletenessAnalyzer:
    """Test suite for CompletenessAnalyzer."""
    
    @pytest.fixture
    def analyzer(self):
        return CompletenessAnalyzer()
    
    def test_analyze_complete_document(self, analyzer):
        """Test analysis of complete document."""
        content = """
# README

## Description
This is a complete document with all required sections.

## Installation
```bash
pip install package
```

## Usage
Use it like this:
```python
import package
package.run()
```

## License
MIT License
"""
        result = analyzer.analyze(content, {'document_type': 'readme'})
        
        assert result.dimension == QualityDimension.COMPLETENESS
        assert result.score > 70
        assert isinstance(result.issues, list)
    
    def test_analyze_missing_sections(self, analyzer):
        """Test analysis with missing sections."""
        content = """
# README

## Description
Short description.
"""
        result = analyzer.analyze(content, {'document_type': 'readme'})
        
        assert result.score < 100
        assert len(result.issues) > 0
        
        # Check for missing section issues
        missing_issues = [i for i in result.issues if 'Missing required section' in i.description]
        assert len(missing_issues) > 0
    
    def test_analyze_short_document(self, analyzer):
        """Test analysis of very short document."""
        content = "# Title\n\nVery short."
        
        result = analyzer.analyze(content)
        
        assert result.score < 100
        assert any('too short' in i.description.lower() for i in result.issues)
        assert any(i.severity == SeverityLevel.HIGH for i in result.issues)
    
    def test_extract_sections(self, analyzer):
        """Test section extraction."""
        content = """
# Main Title
## Section 1
### Subsection
## Section 2
"""
        sections = analyzer._extract_sections(content)
        
        assert 'Main Title' in sections
        assert 'Section 1' in sections
        assert 'Subsection' in sections
        assert 'Section 2' in sections


class TestClarityAnalyzer:
    """Test suite for ClarityAnalyzer."""
    
    @pytest.fixture
    def analyzer(self):
        return ClarityAnalyzer()
    
    def test_analyze_clear_document(self, analyzer):
        """Test analysis of clear document."""
        content = """
# Clear Documentation

This document uses simple language. Short sentences are good.
Each paragraph has a clear purpose. The text is easy to read.

## Simple Section

We avoid complex terms. Examples make things clear.
"""
        result = analyzer.analyze(content)
        
        assert result.dimension == QualityDimension.CLARITY
        assert result.score > 60
    
    def test_analyze_complex_document(self, analyzer):
        """Test analysis of complex document."""
        content = """
# Documentation

This extraordinarily comprehensive documentation encompasses multifaceted 
architectural paradigms, leveraging sophisticated methodologies and 
implementing cutting-edge technological solutions through the utilization 
of advanced algorithmic approaches and state-of-the-art frameworks.
"""
        result = analyzer.analyze(content)
        
        assert result.score < 100
        assert len(result.issues) > 0
    
    def test_count_complex_sentences(self, analyzer):
        """Test complex sentence counting."""
        content = """
This is simple. However, this sentence contains multiple clauses, and 
therefore it is more complex, but still readable. Short again.
"""
        count = analyzer._count_complex_sentences(content)
        assert count >= 1
    
    def test_count_jargon(self, analyzer):
        """Test jargon counting."""
        content = "We use API, SDK, ORM, and CRUD operations in our REST API."
        
        count = analyzer._count_jargon(content)
        assert count >= 4
    
    def test_readability_calculation(self, analyzer):
        """Test readability score calculation."""
        content = "This is simple text. Easy to read. Short sentences help."
        
        score = analyzer._calculate_readability(content)
        assert 0 <= score <= 100


class TestStructureAnalyzer:
    """Test suite for StructureAnalyzer."""
    
    @pytest.fixture
    def analyzer(self):
        return StructureAnalyzer()
    
    def test_analyze_well_structured(self, analyzer):
        """Test analysis of well-structured document."""
        content = """
# Main Title

## Section 1
Content for section 1 with proper structure.

### Subsection 1.1
Details here.

## Section 2
Content for section 2.

### Subsection 2.1
More details.
"""
        result = analyzer.analyze(content)
        
        assert result.dimension == QualityDimension.STRUCTURE
        assert result.score > 70
    
    def test_analyze_no_headings(self, analyzer):
        """Test analysis of document without headings."""
        content = """
This document has no headings at all.
Just paragraphs of text.
Without any structure.
"""
        result = analyzer.analyze(content)
        
        assert result.score < 100
        assert any('No headings found' in i.description for i in result.issues)
        assert any(i.severity == SeverityLevel.HIGH for i in result.issues)
    
    def test_heading_hierarchy_check(self, analyzer):
        """Test heading hierarchy validation."""
        headings = [(1, 'Title'), (3, 'Skipped Level'), (2, 'Section')]
        
        issues = analyzer._check_heading_hierarchy(headings)
        assert len(issues) > 0
        assert any('Skipped heading level' in i.description for i in issues)
    
    def test_section_balance_calculation(self, analyzer):
        """Test section balance calculation."""
        sizes = [100, 95, 105, 98]  # Well balanced
        balance = analyzer._calculate_balance(sizes)
        assert balance > 0.8
        
        sizes = [10, 500, 20, 15]  # Poorly balanced
        balance = analyzer._calculate_balance(sizes)
        assert balance < 0.5


class TestAccuracyAnalyzer:
    """Test suite for AccuracyAnalyzer."""
    
    @pytest.fixture
    def analyzer(self):
        return AccuracyAnalyzer()
    
    def test_analyze_accurate_document(self, analyzer):
        """Test analysis of accurate document."""
        content = """
# Documentation

Using Python 3.11 and modern frameworks.

## Links
- [Valid Link](https://github.com/example/repo)

## Code
```python
def hello():
    print("Hello, World!")
```
"""
        result = analyzer.analyze(content)
        
        assert result.dimension == QualityDimension.ACCURACY
        assert result.score > 70
    
    def test_find_outdated_references(self, analyzer):
        """Test detection of outdated references."""
        content = """
This project uses Python 2.7 and AngularJS.
We also support jQuery 1.6.
"""
        outdated = analyzer._find_outdated_references(content)
        
        assert len(outdated) >= 2
        assert any('Python 2' in ref[1] for ref in outdated)
    
    def test_find_broken_links(self, analyzer):
        """Test detection of broken links."""
        content = """
Check [localhost link](http://localhost:3000)
And [example](http://example.com/broken.invalid)
"""
        broken = analyzer._find_broken_links(content)
        
        assert len(broken) >= 1
        assert any('localhost' in link for link in broken)
    
    def test_check_python_syntax(self, analyzer):
        """Test Python syntax checking."""
        code = """
def function_missing_colon
    return True
    
if condition
    do_something()
"""
        errors = analyzer._check_python_syntax(code)
        
        assert len(errors) >= 2
        assert any('Missing colon' in e['error'] for e in errors)


class TestFormattingAnalyzer:
    """Test suite for FormattingAnalyzer."""
    
    @pytest.fixture
    def analyzer(self):
        return FormattingAnalyzer()
    
    def test_analyze_well_formatted(self, analyzer):
        """Test analysis of well-formatted document."""
        content = """
# Title

Properly formatted paragraph with reasonable length.

## Section

- Consistent list style
- Another item
- Third item

Code block with proper formatting:
```python
def example():
    return True
```
"""
        result = analyzer.analyze(content)
        
        assert result.dimension == QualityDimension.FORMATTING
        assert result.score > 70
    
    def test_find_long_lines(self, analyzer):
        """Test detection of long lines."""
        content = """
Short line.
This is an extremely long line that exceeds the maximum character limit and should be detected by the analyzer as a formatting issue that needs to be addressed.
Another short line.
"""
        long_lines = analyzer._find_long_lines(content)
        
        assert len(long_lines) == 1
        assert 2 in long_lines  # Line 2 is long
    
    def test_find_formatting_issues(self, analyzer):
        """Test detection of formatting inconsistencies."""
        content = """
- List item with dash
* List item with asterisk

# Heading 1
## Heading 2
---
Alternative heading style
===
"""
        issues = analyzer._find_formatting_issues(content)
        
        assert len(issues) > 0
        assert any('Mixed list' in issue for issue in issues)
    
    def test_check_whitespace(self, analyzer):
        """Test whitespace issue detection."""
        content = """Line with trailing space  
Normal line


Multiple blank lines above"""
        
        issues = analyzer._check_whitespace(content)
        
        assert len(issues) > 0
        assert any('trailing whitespace' in issue for issue in issues)