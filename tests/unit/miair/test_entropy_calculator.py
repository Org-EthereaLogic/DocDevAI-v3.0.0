"""
M003 MIAIR Engine - Entropy Calculator Tests

Mathematical validation tests for Shannon entropy calculation with fractal-time scaling.

Test Coverage:
- Shannon entropy calculation accuracy
- Probability distribution calculation
- Fractal-time scaling function
- Edge cases (empty documents, single elements)
- Mathematical bounds validation
- Semantic element extraction
- Performance characteristics

Formula: S = -Σ[p(xi) × log2(p(xi))] × f(Tx)
"""

import unittest
import math
from unittest.mock import patch, MagicMock

import pytest

from devdocai.miair.entropy_calculator import EntropyCalculator
from devdocai.miair.models import Document, SemanticElement, ElementType, DocumentType


class TestEntropyCalculator(unittest.TestCase):
    """Test cases for EntropyCalculator class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.calculator = EntropyCalculator()
    
    def test_initialization(self):
        """Test EntropyCalculator initialization."""
        self.assertIsNotNone(self.calculator)
        self.assertEqual(self.calculator.min_probability, 1e-10)
        self.assertEqual(self.calculator.max_content_length, 1_000_000)
        self.assertIn('headers', self.calculator._patterns)
        self.assertIn('code_blocks', self.calculator._patterns)
    
    def test_calculate_entropy_empty_document(self):
        """Test entropy calculation for empty documents."""
        empty_doc = Document(
            id="test-empty",
            content="",
            type=DocumentType.GENERAL
        )
        
        entropy = self.calculator.calculate_entropy(empty_doc)
        
        # Empty documents should have maximum entropy (1.0)
        self.assertEqual(entropy, 1.0)
    
    def test_calculate_entropy_whitespace_only(self):
        """Test entropy calculation for whitespace-only documents."""
        whitespace_doc = Document(
            id="test-whitespace",
            content="   \n\t  \n  ",
            type=DocumentType.GENERAL
        )
        
        entropy = self.calculator.calculate_entropy(whitespace_doc)
        
        # Whitespace-only documents should have maximum entropy
        self.assertEqual(entropy, 1.0)
    
    def test_calculate_entropy_single_element_type(self):
        """Test entropy calculation for documents with single element type."""
        # Create document with only paragraphs
        single_type_doc = Document(
            id="test-single",
            content="This is a paragraph.\n\nThis is another paragraph.",
            type=DocumentType.GENERAL
        )
        
        entropy = self.calculator.calculate_entropy(single_type_doc)
        
        # Single element type should result in low entropy (perfect order)
        self.assertGreaterEqual(entropy, 0.0)
        self.assertLess(entropy, 0.5)  # Should be relatively low
    
    def test_calculate_entropy_mixed_elements(self):
        """Test entropy calculation for documents with mixed element types."""
        mixed_doc = Document(
            id="test-mixed",
            content="""# Header 1
            
This is a paragraph with some content.

## Header 2

- List item 1
- List item 2

```python
def example_function():
    return "Hello World"
```

Another paragraph with [a link](http://example.com).

**Bold text** and *italic text*.
""",
            type=DocumentType.TECHNICAL_SPEC
        )
        
        entropy = self.calculator.calculate_entropy(mixed_doc)
        
        # Mixed elements should result in moderate to high entropy
        self.assertGreaterEqual(entropy, 0.0)
        self.assertLessEqual(entropy, 1.0)
        self.assertGreater(entropy, 0.3)  # Should be higher than single type
    
    def test_calculate_entropy_bounds(self):
        """Test that entropy calculations always stay within bounds."""
        test_documents = [
            Document(id="1", content="", type=DocumentType.GENERAL),
            Document(id="2", content="Simple text", type=DocumentType.GENERAL),
            Document(id="3", content="# Header\n\nParagraph\n\n```code```", type=DocumentType.GENERAL),
            Document(id="4", content="A" * 10000, type=DocumentType.GENERAL),  # Very repetitive
        ]
        
        for doc in test_documents:
            entropy = self.calculator.calculate_entropy(doc)
            
            # Entropy must always be in [0, 1] range
            self.assertGreaterEqual(entropy, 0.0, f"Entropy below 0 for document {doc.id}")
            self.assertLessEqual(entropy, 1.0, f"Entropy above 1 for document {doc.id}")
    
    def test_fractal_time_scaling(self):
        """Test fractal-time scaling function."""
        base_entropy = 0.8
        
        # Test with different iterations
        scaled_0 = self.calculator.fractal_time_scaling(base_entropy, 0)
        scaled_1 = self.calculator.fractal_time_scaling(base_entropy, 1)
        scaled_5 = self.calculator.fractal_time_scaling(base_entropy, 5)
        
        # Scaling should reduce entropy as iterations increase
        self.assertEqual(scaled_0, base_entropy)  # Iteration 0 should be unchanged
        self.assertLess(scaled_1, base_entropy)   # Iteration 1 should be reduced
        self.assertLess(scaled_5, scaled_1)      # Iteration 5 should be more reduced
        
        # All results should be positive
        self.assertGreater(scaled_1, 0)
        self.assertGreater(scaled_5, 0)
    
    def test_fractal_time_scaling_edge_cases(self):
        """Test fractal-time scaling with edge cases."""
        # Test with negative iteration (should be treated as 0)
        scaled_negative = self.calculator.fractal_time_scaling(0.5, -1)
        scaled_zero = self.calculator.fractal_time_scaling(0.5, 0)
        self.assertEqual(scaled_negative, scaled_zero)
        
        # Test with very high iteration
        scaled_high = self.calculator.fractal_time_scaling(1.0, 1000)
        self.assertGreater(scaled_high, 0)
        self.assertLess(scaled_high, 0.1)  # Should be very small but positive
    
    def test_calculate_probability_distribution(self):
        """Test probability distribution calculation."""
        # Create test semantic elements
        elements = [
            SemanticElement(ElementType.HEADER, "Header 1", 0),
            SemanticElement(ElementType.HEADER, "Header 2", 50),
            SemanticElement(ElementType.PARAGRAPH, "Paragraph 1", 100),
            SemanticElement(ElementType.PARAGRAPH, "Paragraph 2", 150),
            SemanticElement(ElementType.CODE_BLOCK, "print('hello')", 200),
        ]
        
        prob_dist = self.calculator.calculate_probability_distribution(elements)
        
        # Check that probabilities sum to 1.0
        total_prob = sum(prob_dist.values())
        self.assertAlmostEqual(total_prob, 1.0, places=10)
        
        # Check expected probabilities
        expected = {
            'header': 2/5,      # 2 headers out of 5 elements
            'paragraph': 2/5,   # 2 paragraphs out of 5 elements  
            'code_block': 1/5   # 1 code block out of 5 elements
        }
        
        self.assertAlmostEqual(prob_dist.get('header', 0), expected['header'])
        self.assertAlmostEqual(prob_dist.get('paragraph', 0), expected['paragraph'])
        self.assertAlmostEqual(prob_dist.get('code_block', 0), expected['code_block'])
    
    def test_calculate_probability_distribution_empty(self):
        """Test probability distribution with empty element list."""
        prob_dist = self.calculator.calculate_probability_distribution([])
        
        self.assertEqual(prob_dist, {})
    
    def test_calculate_probability_distribution_single_type(self):
        """Test probability distribution with single element type."""
        elements = [
            SemanticElement(ElementType.PARAGRAPH, "Para 1", 0),
            SemanticElement(ElementType.PARAGRAPH, "Para 2", 50),
            SemanticElement(ElementType.PARAGRAPH, "Para 3", 100),
        ]
        
        prob_dist = self.calculator.calculate_probability_distribution(elements)
        
        # Should have only one entry with probability 1.0
        self.assertEqual(len(prob_dist), 1)
        self.assertAlmostEqual(list(prob_dist.values())[0], 1.0)
        self.assertIn('paragraph', prob_dist)
    
    def test_calculate_entropy_with_iteration(self):
        """Test entropy calculation with iteration parameter."""
        doc = Document(
            id="test-iteration",
            content="# Header\n\nParagraph\n\n- List item",
            type=DocumentType.GENERAL
        )
        
        entropy_0 = self.calculator.calculate_entropy(doc, iteration=0)
        entropy_3 = self.calculator.calculate_entropy(doc, iteration=3)
        entropy_10 = self.calculator.calculate_entropy(doc, iteration=10)
        
        # Higher iterations should result in lower entropy due to scaling
        self.assertGreaterEqual(entropy_0, entropy_3)
        self.assertGreaterEqual(entropy_3, entropy_10)
        
        # All should be in valid range
        for entropy in [entropy_0, entropy_3, entropy_10]:
            self.assertGreaterEqual(entropy, 0.0)
            self.assertLessEqual(entropy, 1.0)
    
    def test_extract_semantic_elements_basic(self):
        """Test basic semantic element extraction."""
        doc = Document(
            id="test-extraction",
            content="""# Main Header

This is a paragraph with some content.

## Sub Header

- First item
- Second item

```python
print("Hello")
```

[Link text](http://example.com)

**Bold text** and *italic*.
""",
            type=DocumentType.GENERAL
        )
        
        elements = self.calculator._extract_semantic_elements(doc.content)
        
        # Should find different types of elements
        element_types = {elem.type for elem in elements}
        
        self.assertIn(ElementType.HEADER, element_types)
        self.assertIn(ElementType.PARAGRAPH, element_types)
        self.assertIn(ElementType.LIST_ITEM, element_types)
        self.assertIn(ElementType.CODE_BLOCK, element_types)
        self.assertIn(ElementType.LINK, element_types)
        self.assertIn(ElementType.EMPHASIS, element_types)
        
        # Elements should be sorted by position
        positions = [elem.position for elem in elements]
        self.assertEqual(positions, sorted(positions))
    
    def test_get_entropy_analysis(self):
        """Test detailed entropy analysis."""
        doc = Document(
            id="test-analysis",
            content="""# Technical Documentation

This document describes the API functionality.

## Overview

The API provides the following features:
- Data retrieval
- Data modification  
- User authentication

```python
import requests
response = requests.get('/api/data')
```

### Implementation Details

Further implementation details are provided here.
""",
            type=DocumentType.API_DOCUMENTATION
        )
        
        analysis = self.calculator.get_entropy_analysis(doc)
        
        # Check that analysis contains expected keys
        expected_keys = [
            'entropy', 'total_elements', 'unique_element_types',
            'diversity_ratio', 'probability_distribution', 'element_type_counts',
            'content_length', 'content_lines'
        ]
        
        for key in expected_keys:
            self.assertIn(key, analysis)
        
        # Validate some values
        self.assertIsInstance(analysis['entropy'], float)
        self.assertGreaterEqual(analysis['entropy'], 0.0)
        self.assertLessEqual(analysis['entropy'], 1.0)
        
        self.assertIsInstance(analysis['total_elements'], int)
        self.assertGreater(analysis['total_elements'], 0)
        
        self.assertIsInstance(analysis['unique_element_types'], int)
        self.assertGreater(analysis['unique_element_types'], 0)
        
        self.assertIsInstance(analysis['diversity_ratio'], float)
        self.assertGreaterEqual(analysis['diversity_ratio'], 0.0)
        self.assertLessEqual(analysis['diversity_ratio'], 1.0)
    
    def test_content_size_limit(self):
        """Test content size limit validation."""
        # Create document that exceeds size limit
        large_content = "A" * (self.calculator.max_content_length + 1)
        large_doc = Document(
            id="test-large",
            content=large_content,
            type=DocumentType.GENERAL
        )
        
        # Should raise ValueError for oversized content
        with self.assertRaises(ValueError) as context:
            self.calculator.calculate_entropy(large_doc)
        
        self.assertIn("too large", str(context.exception))
    
    def test_mathematical_accuracy_known_values(self):
        """Test mathematical accuracy with known entropy values."""
        # Test case: Two equal elements should give entropy of 1.0 (before normalization)
        # After normalization with max entropy = log2(2) = 1.0, result should be 1.0
        
        # Create document with exactly two different element types in equal proportions
        balanced_doc = Document(
            id="test-balanced",
            content="# Header\n\nParagraph text here.",  # 1 header, 1 paragraph
            type=DocumentType.GENERAL
        )
        
        entropy = self.calculator.calculate_entropy(balanced_doc, iteration=0)  # No scaling
        
        # Should be high entropy due to balanced distribution
        self.assertGreater(entropy, 0.8)
        
        # Test case: Single element type should give very low entropy
        single_type_doc = Document(
            id="test-single-type", 
            content="Paragraph one.\n\nParagraph two.\n\nParagraph three.",
            type=DocumentType.GENERAL
        )
        
        entropy_single = self.calculator.calculate_entropy(single_type_doc, iteration=0)
        
        # Should be low entropy due to uniform distribution
        self.assertLess(entropy_single, 0.2)
    
    def test_pattern_compilation(self):
        """Test that regex patterns compile correctly."""
        patterns = self.calculator._compile_patterns()
        
        # Check that all expected patterns exist
        expected_patterns = [
            'headers', 'code_blocks', 'list_items', 'links', 
            'technical_terms', 'emphasis'
        ]
        
        for pattern_name in expected_patterns:
            self.assertIn(pattern_name, patterns)
            # Verify pattern is compiled regex
            self.assertTrue(hasattr(patterns[pattern_name], 'search'))
    
    def test_semantic_element_extraction_edge_cases(self):
        """Test semantic element extraction with edge cases."""
        # Test with no matching patterns
        simple_doc = Document(
            id="test-simple",
            content="Just plain text with no special formatting.",
            type=DocumentType.GENERAL
        )
        
        elements = self.calculator._extract_semantic_elements(simple_doc.content)
        
        # Should at least extract paragraphs
        self.assertGreater(len(elements), 0)
        paragraph_elements = [e for e in elements if e.type == ElementType.PARAGRAPH]
        self.assertGreater(len(paragraph_elements), 0)
        
        # Test with malformed markdown
        malformed_doc = Document(
            id="test-malformed",
            content="## Header without H1\n\n```unclosed code block\ncode here",
            type=DocumentType.GENERAL
        )
        
        elements_malformed = self.calculator._extract_semantic_elements(malformed_doc.content)
        
        # Should still extract what it can
        self.assertGreater(len(elements_malformed), 0)


class TestEntropyCalculatorIntegration(unittest.TestCase):
    """Integration tests for EntropyCalculator with real document scenarios."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.calculator = EntropyCalculator()
    
    def test_readme_document(self):
        """Test with README-style document."""
        readme_content = """# Project Name

A brief description of the project.

## Installation

```bash
pip install project-name
```

## Usage

Here's how to use the project:

```python
from project import main
main()
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## License

MIT License - see LICENSE file for details.
"""
        
        readme_doc = Document(
            id="test-readme",
            content=readme_content,
            type=DocumentType.README
        )
        
        entropy = self.calculator.calculate_entropy(readme_doc)
        analysis = self.calculator.get_entropy_analysis(readme_doc)
        
        # README should have moderate entropy due to good structure
        self.assertGreaterEqual(entropy, 0.3)
        self.assertLessEqual(entropy, 0.8)
        
        # Should have good element diversity
        self.assertGreaterEqual(analysis['unique_element_types'], 4)
        self.assertGreater(analysis['diversity_ratio'], 0.2)
    
    def test_api_documentation(self):
        """Test with API documentation."""
        api_content = """# API Documentation

## Authentication

All requests require authentication via API key.

### Headers

```
Authorization: Bearer <your-api-key>
Content-Type: application/json
```

## Endpoints

### GET /users

Retrieve list of users.

**Parameters:**
- `page` (integer): Page number
- `limit` (integer): Items per page

**Response:**

```json
{
  "users": [...],
  "pagination": {...}
}
```

### POST /users

Create a new user.

**Request Body:**

```json
{
  "name": "string",
  "email": "string"
}
```

**Response:**

```json
{
  "id": "string",
  "name": "string", 
  "email": "string"
}
```

## Error Handling

The API returns standard HTTP status codes:

- `200`: Success
- `400`: Bad Request
- `401`: Unauthorized
- `404`: Not Found
- `500`: Internal Server Error
"""
        
        api_doc = Document(
            id="test-api",
            content=api_content,
            type=DocumentType.API_DOCUMENTATION
        )
        
        entropy = self.calculator.calculate_entropy(api_doc)
        analysis = self.calculator.get_entropy_analysis(api_doc)
        
        # API docs should have high element diversity
        self.assertGreaterEqual(analysis['unique_element_types'], 5)
        self.assertGreater(analysis['code_block_count'], 3)
        
        # Should have reasonable entropy
        self.assertGreaterEqual(entropy, 0.4)
        self.assertLessEqual(entropy, 0.9)


if __name__ == '__main__':
    unittest.main()