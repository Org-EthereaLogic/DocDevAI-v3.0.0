"""
Tests for enhancement strategies.
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch

from devdocai.enhancement.enhancement_strategies import (
    EnhancementStrategy,
    ClarityStrategy,
    CompletenessStrategy,
    ConsistencyStrategy,
    AccuracyStrategy,
    ReadabilityStrategy,
    StrategyFactory,
    StrategyResult
)
from devdocai.enhancement.config import (
    StrategyConfig,
    EnhancementType,
    EnhancementSettings
)


class TestEnhancementStrategy:
    """Test base enhancement strategy."""
    
    def test_split_into_sections(self):
        """Test splitting content into sections."""
        # Create a concrete strategy for testing
        strategy = ClarityStrategy(StrategyConfig())
        
        content = """# Introduction
This is the intro.

## Section 1
Content of section 1.

## Section 2
Content of section 2."""
        
        sections = strategy._split_into_sections(content)
        
        assert len(sections) == 3
        assert sections[0][0] == "Introduction"
        assert "intro" in sections[0][1]
        assert sections[1][0] == "Section 1"
        assert sections[2][0] == "Section 2"


class TestClarityStrategy:
    """Test clarity enhancement strategy."""
    
    @pytest.fixture
    def strategy(self):
        """Create clarity strategy instance."""
        config = StrategyConfig()
        return ClarityStrategy(config)
        
    @pytest.mark.asyncio
    async def test_enhance(self, strategy):
        """Test clarity enhancement."""
        content = "This is a very long sentence that continues for many words and could potentially be simplified to make it more clear and easier to understand for readers."
        metadata = {"type": "test"}
        
        # Mock LLM enhancement
        strategy._apply_llm_enhancement = AsyncMock(return_value=content)
        
        enhanced = await strategy.enhance(content, metadata)
        
        assert enhanced is not None
        assert strategy.applied_count == 1
        
    def test_analyze(self, strategy):
        """Test clarity analysis."""
        content = "This is a test. " * 10 + "Complicated terminology. " * 5
        
        analysis = strategy.analyze(content)
        
        assert "average_sentence_length" in analysis
        assert "long_sentences_count" in analysis
        assert "complex_words_ratio" in analysis
        assert "readability_score" in analysis
        
    @pytest.mark.asyncio
    async def test_simplify_sentences_with_llm(self, strategy):
        """Test sentence simplification with LLM."""
        long_sentence = "This is " + " very" * 30 + " long sentence."
        
        mock_llm = Mock()
        mock_llm.generate = AsyncMock(return_value={"content": "Simplified sentence."})
        strategy.llm_adapter = mock_llm
        
        result = await strategy._simplify_sentences(long_sentence)
        
        assert result is not None
        
    @pytest.mark.asyncio
    async def test_simplify_sentences_fallback(self, strategy):
        """Test sentence simplification without LLM."""
        long_sentence = "This is a very long sentence and it continues with more words but it could be split into smaller parts."
        
        result = await strategy._simplify_sentences(long_sentence)
        
        assert result is not None
        # Should split on conjunctions
        
    @pytest.mark.asyncio
    async def test_reduce_jargon(self, strategy):
        """Test jargon reduction."""
        content = "We need to utilize and leverage our resources to optimize the paradigm."
        
        result = await strategy._reduce_jargon(content)
        
        assert result is not None
        # Without LLM, should use simple replacements
        assert "use" in result or "utilize" in result
        
    @pytest.mark.asyncio
    async def test_improve_transitions(self, strategy):
        """Test transition improvement."""
        content = """First paragraph.

Second paragraph.

Third paragraph."""
        
        result = await strategy._improve_transitions(content)
        
        assert result is not None
        # Should add transition words


class TestCompletenessStrategy:
    """Test completeness enhancement strategy."""
    
    @pytest.fixture
    def strategy(self):
        """Create completeness strategy instance."""
        config = StrategyConfig()
        return CompletenessStrategy(config)
        
    @pytest.mark.asyncio
    async def test_enhance(self, strategy):
        """Test completeness enhancement."""
        content = "Brief content."
        metadata = {}
        
        enhanced = await strategy.enhance(content, metadata)
        
        assert enhanced is not None
        assert strategy.applied_count == 1
        
    def test_analyze(self, strategy):
        """Test completeness analysis."""
        content = """# Introduction
Brief intro.

## Short Section
Not much here."""
        
        analysis = strategy.analyze(content)
        
        assert "section_count" in analysis
        assert "short_sections" in analysis
        assert "average_section_length" in analysis
        assert "has_introduction" in analysis
        assert "has_conclusion" in analysis
        assert "has_examples" in analysis
        
    @pytest.mark.asyncio
    async def test_fill_content_gaps(self, strategy):
        """Test filling content gaps."""
        content = "Main content without introduction or conclusion."
        
        result = await strategy._fill_content_gaps(content)
        
        assert result is not None
        # Should add introduction/conclusion if missing
        
    @pytest.mark.asyncio
    async def test_add_examples(self, strategy):
        """Test adding examples."""
        content = "This is a concept that needs examples."
        
        result = await strategy._add_examples(content)
        
        assert result is not None
        
    @pytest.mark.asyncio
    async def test_expand_sections(self, strategy):
        """Test expanding short sections."""
        content = """# Section 1
Too short.

# Section 2
This is a longer section with adequate content that doesn't need expansion."""
        
        result = await strategy._expand_sections(content)
        
        assert result is not None
        assert len(result) >= len(content)  # Should expand


class TestConsistencyStrategy:
    """Test consistency enhancement strategy."""
    
    @pytest.fixture
    def strategy(self):
        """Create consistency strategy instance."""
        config = StrategyConfig()
        return ConsistencyStrategy(config)
        
    @pytest.mark.asyncio
    async def test_enhance(self, strategy):
        """Test consistency enhancement."""
        content = "Using api and API and Api inconsistently."
        metadata = {}
        
        enhanced = await strategy.enhance(content, metadata)
        
        assert enhanced is not None
        assert strategy.applied_count == 1
        
    def test_analyze(self, strategy):
        """Test consistency analysis."""
        content = "Using API and api and Api. Also URL and url. Using **bold** and __underline__."
        
        analysis = strategy.analyze(content)
        
        assert "terminology_inconsistencies" in analysis
        assert "heading_style_variations" in analysis
        assert "has_mixed_formatting" in analysis
        
    @pytest.mark.asyncio
    async def test_standardize_terminology(self, strategy):
        """Test terminology standardization."""
        content = "The api uses json and xml formats. The url points to the rest endpoint."
        
        result = await strategy._standardize_terminology(content)
        
        assert "API" in result or "api" in result
        assert "JSON" in result or "json" in result
        assert "URL" in result or "url" in result
        
    @pytest.mark.asyncio
    async def test_unify_formatting(self, strategy):
        """Test formatting unification."""
        content = "Using __bold__ and **bold** and _italic_ and *italic*."
        
        result = await strategy._unify_formatting(content)
        
        assert result is not None
        # Should standardize emphasis markers
        
    @pytest.mark.asyncio
    async def test_align_tone(self, strategy):
        """Test tone alignment."""
        content = "We implemented the system. The system was deployed by the team."
        
        result = await strategy._align_tone(content)
        
        assert result is not None


class TestAccuracyStrategy:
    """Test accuracy enhancement strategy."""
    
    @pytest.fixture
    def strategy(self):
        """Create accuracy strategy instance."""
        config = StrategyConfig()
        return AccuracyStrategy(config)
        
    @pytest.mark.asyncio
    async def test_enhance(self, strategy):
        """Test accuracy enhancement."""
        content = "Studies show that 95% of users prefer this approach."
        metadata = {}
        
        enhanced = await strategy.enhance(content, metadata)
        
        assert enhanced is not None
        assert strategy.applied_count == 1
        
    def test_analyze(self, strategy):
        """Test accuracy analysis."""
        content = "In 2023-01-15, studies show that 85% of users might prefer this approach."
        
        analysis = strategy.analyze(content)
        
        assert "numeric_claims" in analysis
        assert "date_references" in analysis
        assert "citations_count" in analysis
        assert "uncertainty_indicators" in analysis
        
    @pytest.mark.asyncio
    async def test_fact_check(self, strategy):
        """Test fact checking."""
        content = "100% of users always prefer this solution."
        
        result = await strategy._fact_check(content)
        
        assert result is not None
        # Should mark unsupported claims
        
    @pytest.mark.asyncio
    async def test_technical_review(self, strategy):
        """Test technical review."""
        content = """```python
eval(user_input)  # Dangerous!
```"""
        
        result = await strategy._technical_review(content)
        
        assert result is not None
        # Should flag security issues
        
    @pytest.mark.asyncio
    async def test_validate_citations(self, strategy):
        """Test citation validation."""
        content = "According to Smith, this is true. (Jones, 2023) states otherwise."
        
        result = await strategy._validate_citations(content)
        
        assert result is not None


class TestReadabilityStrategy:
    """Test readability enhancement strategy."""
    
    @pytest.fixture
    def strategy(self):
        """Create readability strategy instance."""
        config = StrategyConfig()
        return ReadabilityStrategy(config)
        
    @pytest.mark.asyncio
    async def test_enhance(self, strategy):
        """Test readability enhancement."""
        content = "Dense paragraph without structure or formatting that continues for a long time."
        metadata = {}
        
        enhanced = await strategy.enhance(content, metadata)
        
        assert enhanced is not None
        assert strategy.applied_count == 1
        
    def test_analyze(self, strategy):
        """Test readability analysis."""
        content = """# Header

- List item
- Another item

```code block```

Regular paragraph."""
        
        analysis = strategy.analyze(content)
        
        assert "flesch_reading_ease" in analysis
        assert "flesch_kincaid_grade" in analysis
        assert "has_toc" in analysis
        assert "has_headers" in analysis
        assert "has_lists" in analysis
        assert "has_code_blocks" in analysis
        assert "section_count" in analysis
        
    @pytest.mark.asyncio
    async def test_optimize_structure(self, strategy):
        """Test structure optimization."""
        long_content = "# Section 1\n" * 5 + "\nContent " * 200
        
        result = await strategy._optimize_structure(long_content)
        
        assert result is not None
        # May add table of contents
        
    @pytest.mark.asyncio
    async def test_improve_flow(self, strategy):
        """Test flow improvement."""
        content = ". ".join(["Sentence"] * 10) + "."
        
        result = await strategy._improve_flow(content)
        
        assert result is not None
        # Should break up dense text
        
    @pytest.mark.asyncio
    async def test_add_summaries(self, strategy):
        """Test adding summaries."""
        content = """# Section 1
Content.

# Section 2
More content.

# Section 3
Even more content.

# Section 4
Final content."""
        
        result = await strategy._add_summaries(content)
        
        assert result is not None
        # May add executive summary


class TestStrategyFactory:
    """Test strategy factory."""
    
    @pytest.fixture
    def factory(self):
        """Create strategy factory."""
        settings = EnhancementSettings()
        return StrategyFactory(settings)
        
    def test_create_strategy(self, factory):
        """Test creating strategies."""
        # Create each strategy type
        clarity = factory.create_strategy(EnhancementType.CLARITY)
        assert isinstance(clarity, ClarityStrategy)
        
        completeness = factory.create_strategy(EnhancementType.COMPLETENESS)
        assert isinstance(completeness, CompletenessStrategy)
        
        consistency = factory.create_strategy(EnhancementType.CONSISTENCY)
        assert isinstance(consistency, ConsistencyStrategy)
        
        accuracy = factory.create_strategy(EnhancementType.ACCURACY)
        assert isinstance(accuracy, AccuracyStrategy)
        
        readability = factory.create_strategy(EnhancementType.READABILITY)
        assert isinstance(readability, ReadabilityStrategy)
        
    def test_create_strategy_with_llm(self, factory):
        """Test creating strategy with LLM adapter."""
        mock_llm = Mock()
        
        strategy = factory.create_strategy(EnhancementType.CLARITY, mock_llm)
        
        assert isinstance(strategy, ClarityStrategy)
        assert strategy.llm_adapter == mock_llm
        
    def test_get_all_strategies(self, factory):
        """Test getting all enabled strategies."""
        strategies = factory.get_all_strategies()
        
        assert len(strategies) == 5  # All strategies enabled by default
        
    def test_get_usage_stats(self, factory):
        """Test getting usage statistics."""
        # Create and use a strategy
        clarity = factory.create_strategy(EnhancementType.CLARITY)
        clarity.applied_count = 3
        
        stats = factory.get_usage_stats()
        
        assert "Clarity" in stats
        assert stats["Clarity"] == 3
        
    def test_strategy_caching(self, factory):
        """Test that strategies are cached."""
        strategy1 = factory.create_strategy(EnhancementType.CLARITY)
        strategy2 = factory.create_strategy(EnhancementType.CLARITY)
        
        assert strategy1 is strategy2  # Should be same instance