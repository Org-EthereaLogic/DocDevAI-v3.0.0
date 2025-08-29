"""
Unit tests for pattern recognition system.

Tests identification of documentation patterns, improvement opportunities,
and learning capabilities.
"""

import pytest
from devdocai.miair.patterns import (
    PatternRecognizer, Pattern, PatternType, PatternAnalysis
)


class TestPatternRecognizer:
    """Test suite for pattern recognition."""
    
    @pytest.fixture
    def recognizer(self):
        """Create pattern recognizer instance."""
        return PatternRecognizer(learning_enabled=True)
    
    @pytest.fixture
    def recognizer_no_learning(self):
        """Create recognizer without learning."""
        return PatternRecognizer(learning_enabled=False)
    
    @pytest.fixture
    def document_with_issues(self):
        """Document with various pattern issues."""
        return """
        API Documentation
        
        TODO: Add proper introduction
        
        The system was designed by our team. The implementation was completed last year.
        The documentation was written by technical writers.
        
        This is an extremely long sentence that continues on and on without any clear breaks or punctuation to help the reader understand the complex information being presented which makes it very difficult to follow and comprehend especially for non-native speakers or those unfamiliar with the technical domain being discussed in this particular document.
        
        ## first section
        
        Some content here.
        
        ### Second Section
        
        More content with inconsistent formatting.
        
        - First item
        * Second item
        + Third item
        
        We use e-mail for communication. You can also use Email or email.
        
        [placeholder for examples]
        
        FIXME: Add code examples
        
        Obviously, everyone knows how to use this API.
        Simply just follow these steps.
        """
    
    @pytest.fixture
    def well_structured_document(self):
        """Well-structured document with minimal issues."""
        return """
        # API Documentation v2.0
        
        ## Introduction
        
        This documentation provides comprehensive guidance for using our REST API.
        We cover authentication, endpoints, and best practices.
        
        ## Authentication
        
        Our API uses token-based authentication. Request a token using your credentials.
        Store the token securely and include it in request headers.
        
        ## Examples
        
        ```python
        import requests
        
        response = requests.get('https://api.example.com/data')
        print(response.json())
        ```
        
        ## Best Practices
        
        - Use HTTPS for all requests
        - Implement proper error handling
        - Cache responses when appropriate
        
        ## Conclusion
        
        This guide covered the essential aspects of our API.
        For detailed information, consult the reference documentation.
        """
    
    def test_initialization(self, recognizer):
        """Test recognizer initialization."""
        assert recognizer.learning_enabled is True
        assert recognizer.pattern_definitions is not None
        assert len(recognizer.pattern_definitions) == 5  # 5 pattern types
        assert recognizer.learned_patterns is not None
    
    def test_initialization_no_learning(self, recognizer_no_learning):
        """Test initialization without learning."""
        assert recognizer_no_learning.learning_enabled is False
        assert recognizer_no_learning.learned_patterns is None
    
    def test_analyze_empty_document(self, recognizer):
        """Test analysis of empty document."""
        analysis = recognizer.analyze("")
        
        assert isinstance(analysis, PatternAnalysis)
        assert len(analysis.patterns) == 0
        assert analysis.summary == {}
        assert analysis.improvement_map == {}
    
    def test_analyze_document_with_issues(self, recognizer, document_with_issues):
        """Test analysis of document with multiple issues."""
        analysis = recognizer.analyze(document_with_issues)
        
        assert len(analysis.patterns) > 0
        
        # Should detect various issues
        pattern_names = [p.name for p in analysis.patterns]
        
        # Check for expected patterns
        assert any('passive_voice' in name for name in pattern_names)
        assert any('complex_sentences' in name for name in pattern_names)
        assert any('TODO' in doc or 'FIXME' in doc 
                  for doc in [document_with_issues])  # Has TODOs
    
    def test_structural_patterns(self, recognizer):
        """Test structural pattern detection."""
        # Missing introduction
        no_intro = """
        ## First Section
        Content here.
        
        ## Second Section
        More content.
        """
        
        analysis = recognizer.analyze(no_intro)
        patterns = [p for p in analysis.patterns if p.type == PatternType.STRUCTURAL]
        
        assert any(p.name == 'missing_introduction' for p in patterns)
        
        # No conclusion
        no_conclusion = """
        # Title
        
        ## Introduction
        This is the introduction.
        
        ## Main Content
        Main content here.
        """
        
        analysis = recognizer.analyze(no_conclusion)
        patterns = [p for p in analysis.patterns if p.type == PatternType.STRUCTURAL]
        
        assert any(p.name == 'no_conclusion' for p in patterns)
    
    def test_linguistic_patterns(self, recognizer):
        """Test linguistic pattern detection."""
        # Passive voice
        passive_doc = """
        The code was written by developers.
        The tests were created by QA team.
        The deployment was handled by DevOps.
        """
        
        analysis = recognizer.analyze(passive_doc)
        patterns = [p for p in analysis.patterns if p.type == PatternType.LINGUISTIC]
        
        assert any(p.name == 'passive_voice_overuse' for p in patterns)
        
        # Complex sentences
        complex_doc = """
        This extraordinarily long and convoluted sentence, which contains multiple subordinate clauses and parenthetical expressions that interrupt the main flow of thought, making it extremely difficult for readers to follow the logical progression of ideas being presented, especially when combined with technical jargon and specialized terminology that may not be familiar to all members of the intended audience, ultimately serves as a prime example of poor writing that should be simplified.
        """
        
        analysis = recognizer.analyze(complex_doc)
        patterns = [p for p in analysis.patterns if p.type == PatternType.LINGUISTIC]
        
        assert any(p.name == 'complex_sentences' for p in patterns)
    
    def test_technical_patterns(self, recognizer):
        """Test technical pattern detection."""
        # Undefined acronyms
        acronym_doc = """
        Use the API to connect to the DB.
        The REST interface supports JSON and XML.
        Configure the SDK for your IDE.
        """
        
        analysis = recognizer.analyze(acronym_doc)
        patterns = [p for p in analysis.patterns if p.type == PatternType.TECHNICAL]
        
        assert any(p.name == 'undefined_acronyms' for p in patterns)
        
        # Missing code examples
        technical_no_code = """
        # Technical Guide
        
        To use our library, import the main module.
        Create an instance of the client class.
        Call the appropriate methods.
        Handle the responses properly.
        """
        
        analysis = recognizer.analyze(technical_no_code)
        patterns = [p for p in analysis.patterns if p.type == PatternType.TECHNICAL]
        
        assert any(p.name == 'missing_code_examples' for p in patterns)
    
    def test_formatting_patterns(self, recognizer):
        """Test formatting pattern detection."""
        # Inconsistent headers
        inconsistent_headers = """
        # Main Title
        
        ## first section
        
        ### Second Section
        
        ## third section
        """
        
        analysis = recognizer.analyze(inconsistent_headers)
        patterns = [p for p in analysis.patterns if p.type == PatternType.FORMATTING]
        
        # Should detect inconsistency
        assert len(patterns) > 0
        
        # Code without language
        code_no_lang = """
        Here's an example:
        
        ```
        function test() {
            return true;
        }
        ```
        """
        
        analysis = recognizer.analyze(code_no_lang)
        patterns = [p for p in analysis.patterns if p.type == PatternType.FORMATTING]
        
        assert any(p.name == 'code_without_language' for p in patterns)
    
    def test_semantic_patterns(self, recognizer):
        """Test semantic pattern detection."""
        # Vague language
        vague_doc = """
        Some users may experience various issues.
        Many features are available in certain situations.
        Several options can be configured.
        """
        
        analysis = recognizer.analyze(vague_doc)
        patterns = [p for p in analysis.patterns if p.type == PatternType.SEMANTIC]
        
        assert any(p.name == 'vague_language' for p in patterns)
        
        # Assumption language
        assumption_doc = """
        Obviously, this is simple to understand.
        Clearly, everyone knows how to do this.
        Simply follow the steps below.
        """
        
        analysis = recognizer.analyze(assumption_doc)
        patterns = [p for p in analysis.patterns if p.type == PatternType.SEMANTIC]
        
        assert any(p.name == 'assumption_language' for p in patterns)
    
    def test_pattern_severity_and_priority(self, recognizer, document_with_issues):
        """Test pattern severity and priority assignment."""
        analysis = recognizer.analyze(document_with_issues)
        
        for pattern in analysis.patterns:
            # Check severity is in valid range
            assert 0.0 <= pattern.severity <= 1.0
            
            # Check priority is in valid range
            assert 1 <= pattern.improvement_priority <= 5
            
            # High severity should generally have high priority
            if pattern.severity >= 0.7:
                assert pattern.improvement_priority <= 3
    
    def test_get_high_priority_patterns(self, recognizer, document_with_issues):
        """Test getting high priority patterns."""
        analysis = recognizer.analyze(document_with_issues)
        high_priority = analysis.get_high_priority_patterns()
        
        # All returned patterns should have priority <= 2
        for pattern in high_priority:
            assert pattern.improvement_priority <= 2
    
    def test_get_patterns_by_type(self, recognizer, document_with_issues):
        """Test filtering patterns by type."""
        analysis = recognizer.analyze(document_with_issues)
        
        for pattern_type in PatternType:
            type_patterns = analysis.get_patterns_by_type(pattern_type)
            
            # All returned patterns should be of specified type
            for pattern in type_patterns:
                assert pattern.type == pattern_type
    
    def test_pattern_to_dict(self, recognizer):
        """Test pattern to dictionary conversion."""
        pattern = Pattern(
            type=PatternType.LINGUISTIC,
            name='test_pattern',
            description='Test description',
            occurrences=[{'text': 'test', 'line': 1}],
            severity=0.5,
            improvement_priority=3,
            suggested_action='Fix this'
        )
        
        result = pattern.to_dict()
        
        assert result['type'] == 'linguistic'
        assert result['name'] == 'test_pattern'
        assert result['description'] == 'Test description'
        assert result['severity'] == 0.5
        assert result['improvement_priority'] == 3
    
    def test_summary_generation(self, recognizer, document_with_issues):
        """Test summary generation."""
        analysis = recognizer.analyze(document_with_issues)
        summary = analysis.summary
        
        assert 'total_patterns' in summary
        assert 'high_priority' in summary
        assert 'by_type' in summary
        assert 'overall_severity' in summary
        
        assert summary['total_patterns'] == len(analysis.patterns)
        assert summary['overall_severity'] >= 0.0
    
    def test_improvement_map(self, recognizer, document_with_issues):
        """Test improvement map generation."""
        analysis = recognizer.analyze(document_with_issues)
        improvement_map = analysis.improvement_map
        
        # Should be organized by priority
        for key in improvement_map:
            assert 'priority_' in key
            
            improvements = improvement_map[key]
            for improvement in improvements:
                assert 'pattern' in improvement
                assert 'action' in improvement
                assert 'severity' in improvement
    
    def test_learning_insights(self, recognizer, document_with_issues):
        """Test learning insights generation."""
        analysis = recognizer.analyze(document_with_issues)
        insights = analysis.learning_insights
        
        assert isinstance(insights, list)
        assert len(insights) > 0
        
        # Should contain meaningful insights
        assert any(insight for insight in insights if len(insight) > 10)
    
    def test_learn_from_improvement(self, recognizer):
        """Test learning from successful improvements."""
        original = "The document was written poorly."
        improved = "We wrote the document poorly."  # Active voice
        
        pattern = Pattern(
            type=PatternType.LINGUISTIC,
            name='passive_voice',
            description='Passive voice',
            occurrences=[],
            severity=0.5,
            improvement_priority=3,
            suggested_action='Convert to active'
        )
        
        recognizer.learn_from_improvement(original, improved, [pattern])
        
        # Check learning was recorded
        assert len(recognizer.learned_patterns) > 0
        key = f"{pattern.type.value}_{pattern.name}"
        assert key in recognizer.learned_patterns
    
    def test_pattern_statistics(self, recognizer):
        """Test pattern statistics retrieval."""
        stats = recognizer.get_pattern_statistics()
        
        assert 'total_pattern_types' in stats
        assert 'patterns_by_type' in stats
        
        assert stats['total_pattern_types'] == 5
        
        for pattern_type in PatternType:
            assert pattern_type.value in stats['patterns_by_type']
    
    def test_well_structured_document(self, recognizer, well_structured_document):
        """Test analysis of well-structured document."""
        analysis = recognizer.analyze(well_structured_document)
        
        # Should have fewer patterns than problematic document
        assert len(analysis.patterns) < 5
        
        # Should not have high severity issues
        high_severity = [p for p in analysis.patterns if p.severity >= 0.7]
        assert len(high_severity) == 0
    
    def test_metadata_context(self, recognizer):
        """Test pattern recognition with metadata context."""
        doc = "Simple document"
        metadata = {'type': 'technical', 'audience': 'developers'}
        
        analysis = recognizer.analyze(doc, metadata)
        
        # Analysis should complete with metadata
        assert analysis is not None


class TestPatternPerformance:
    """Performance tests for pattern recognition."""
    
    @pytest.fixture
    def recognizer(self):
        """Create recognizer for performance testing."""
        return PatternRecognizer(learning_enabled=False)
    
    @pytest.fixture
    def large_document(self):
        """Generate large document for testing."""
        sections = []
        for i in range(100):
            sections.append(f"""
            ## Section {i}
            
            Content with various patterns. The text was written quickly.
            Some sections have issues. TODO: improve this.
            Obviously, this needs work. Many things could be better.
            
            This is a very long sentence that goes on and on without proper breaks making it hard to read and understand especially for those not familiar with the content.
            """)
        
        return "\n\n".join(sections)
    
    def test_analysis_performance(self, recognizer, large_document):
        """Test pattern analysis performance."""
        import time
        
        start = time.time()
        analysis = recognizer.analyze(large_document)
        elapsed = time.time() - start
        
        # Should complete in reasonable time
        assert elapsed < 2.0  # Less than 2 seconds
        assert len(analysis.patterns) > 0
    
    def test_learning_performance(self):
        """Test learning performance with many patterns."""
        recognizer = PatternRecognizer(learning_enabled=True)
        
        # Learn from many improvements
        for i in range(100):
            pattern = Pattern(
                type=PatternType.LINGUISTIC,
                name=f'pattern_{i}',
                description='Test',
                occurrences=[],
                severity=0.5,
                improvement_priority=3,
                suggested_action='Fix'
            )
            
            recognizer.learn_from_improvement(
                f"original_{i}",
                f"improved_{i}",
                [pattern]
            )
        
        # Should handle large learning history
        stats = recognizer.get_pattern_statistics()
        assert stats['learned_patterns'] > 0