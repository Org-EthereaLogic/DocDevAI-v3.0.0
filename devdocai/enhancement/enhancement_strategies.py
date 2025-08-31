"""
Enhancement strategies for document improvement.

Provides various strategies for iterative document enhancement including
clarity, completeness, consistency, accuracy, and readability improvements.
"""

import re
import logging
from typing import Dict, List, Optional, Any, Tuple
from abc import ABC, abstractmethod
from dataclasses import dataclass
import asyncio

# Try to import textstat for readability calculations
try:
    from textstat import flesch_reading_ease, flesch_kincaid_grade, syllable_count
    TEXTSTAT_AVAILABLE = True
except ImportError:
    TEXTSTAT_AVAILABLE = False
    logging.warning("textstat library not available, using fallback readability calculations")

# Import configuration
from .config import EnhancementType, StrategyConfig, EnhancementSettings

# Import LLM adapter for enhancements
try:
    from devdocai.llm_adapter.adapter_unified import UnifiedLLMAdapter
    LLM_AVAILABLE = True
except ImportError:
    LLM_AVAILABLE = False
    logging.warning("LLM adapter not available, using fallback strategies")

logger = logging.getLogger(__name__)


@dataclass
class StrategyResult:
    """Result from applying an enhancement strategy."""
    
    enhanced_content: str
    changes_made: List[str]
    confidence: float
    metrics: Dict[str, Any]


class EnhancementStrategy(ABC):
    """Base class for enhancement strategies."""
    
    def __init__(self, config: StrategyConfig, llm_adapter: Optional[Any] = None):
        """Initialize strategy with configuration."""
        self.config = config
        self.llm_adapter = llm_adapter
        self.name = self.__class__.__name__.replace("Strategy", "")
        self.applied_count = 0
        
    @abstractmethod
    async def enhance(self, content: str, metadata: Dict[str, Any]) -> str:
        """
        Apply enhancement strategy to content.
        
        Args:
            content: Document content to enhance
            metadata: Document metadata
            
        Returns:
            Enhanced content
        """
        pass
    
    @abstractmethod
    def analyze(self, content: str) -> Dict[str, Any]:
        """
        Analyze content for potential improvements.
        
        Args:
            content: Content to analyze
            
        Returns:
            Analysis results
        """
        pass
    
    def _split_into_sections(self, content: str) -> List[Tuple[str, str]]:
        """Split content into sections for processing."""
        sections = []
        current_section = []
        current_header = "Introduction"
        
        for line in content.split('\n'):
            if line.startswith('#'):
                if current_section:
                    sections.append((current_header, '\n'.join(current_section)))
                current_header = line.strip('#').strip()
                current_section = [line]
            else:
                current_section.append(line)
        
        if current_section:
            sections.append((current_header, '\n'.join(current_section)))
        
        return sections
    
    async def _apply_llm_enhancement(
        self,
        content: str,
        prompt: str,
        temperature: float = 0.7
    ) -> str:
        """Apply LLM-based enhancement."""
        if self.llm_adapter and LLM_AVAILABLE:
            try:
                response = await self.llm_adapter.generate(
                    prompt=f"{prompt}\n\nContent:\n{content}",
                    temperature=temperature,
                    max_tokens=len(content) * 2  # Allow for expansion
                )
                return response.get("content", content)
            except Exception as e:
                logger.warning(f"LLM enhancement failed: {e}")
                return content
        else:
            # Fallback to rule-based enhancement
            return self._apply_rule_based_enhancement(content, prompt)
    
    def _apply_rule_based_enhancement(self, content: str, enhancement_type: str) -> str:
        """Apply rule-based enhancement as fallback."""
        # This is a simplified fallback - real implementation would be more sophisticated
        return content


class ClarityStrategy(EnhancementStrategy):
    """Strategy for improving document clarity."""
    
    async def enhance(self, content: str, metadata: Dict[str, Any]) -> str:
        """Enhance clarity by simplifying complex sentences and reducing jargon."""
        logger.info("Applying clarity enhancement strategy")
        
        enhanced = content
        
        if self.config.clarity_settings.get("simplify_sentences", True):
            enhanced = await self._simplify_sentences(enhanced)
        
        if self.config.clarity_settings.get("reduce_jargon", True):
            enhanced = await self._reduce_jargon(enhanced)
        
        if self.config.clarity_settings.get("improve_transitions", True):
            enhanced = await self._improve_transitions(enhanced)
        
        self.applied_count += 1
        return enhanced
    
    def analyze(self, content: str) -> Dict[str, Any]:
        """Analyze content for clarity issues."""
        sentences = content.split('.')
        long_sentences = [s for s in sentences if len(s.split()) > 25]
        
        # Find complex words (more than 3 syllables)
        words = re.findall(r'\b\w+\b', content.lower())
        if TEXTSTAT_AVAILABLE:
            complex_words = [w for w in words if syllable_count(w) > 3]
        else:
            # Simple heuristic: words longer than 10 characters are complex
            complex_words = [w for w in words if len(w) > 10]
        
        return {
            "average_sentence_length": sum(len(s.split()) for s in sentences) / max(len(sentences), 1),
            "long_sentences_count": len(long_sentences),
            "complex_words_ratio": len(complex_words) / max(len(words), 1),
            "readability_score": flesch_reading_ease(content) if TEXTSTAT_AVAILABLE and len(content) > 100 else 50
        }
    
    async def _simplify_sentences(self, content: str) -> str:
        """Simplify long and complex sentences."""
        max_length = self.config.clarity_settings.get("max_sentence_length", 25)
        
        if self.llm_adapter:
            prompt = f"""Simplify the following text by breaking long sentences (over {max_length} words) 
            into shorter, clearer ones. Maintain the original meaning and technical accuracy.
            Do not add new information or remove important details."""
            return await self._apply_llm_enhancement(content, prompt, temperature=0.5)
        else:
            # Rule-based simplification
            sentences = content.split('. ')
            simplified = []
            
            for sentence in sentences:
                words = sentence.split()
                if len(words) > max_length:
                    # Find conjunctions to split on
                    if ' and ' in sentence:
                        parts = sentence.split(' and ', 1)
                        simplified.extend(parts)
                    elif ' but ' in sentence:
                        parts = sentence.split(' but ', 1)
                        simplified.append(parts[0])
                        simplified.append(f"However, {parts[1]}" if len(parts) > 1 else "")
                    else:
                        simplified.append(sentence)
                else:
                    simplified.append(sentence)
            
            return '. '.join(s for s in simplified if s) + '.'
    
    async def _reduce_jargon(self, content: str) -> str:
        """Replace jargon with simpler alternatives."""
        if self.llm_adapter:
            prompt = """Replace technical jargon and complex terminology with simpler, 
            more accessible language while maintaining technical accuracy. 
            Add brief explanations for necessary technical terms."""
            return await self._apply_llm_enhancement(content, prompt, temperature=0.6)
        else:
            # Simple jargon replacement dictionary
            jargon_replacements = {
                "utilize": "use",
                "implement": "create",
                "leverage": "use",
                "facilitate": "help",
                "optimize": "improve",
                "paradigm": "approach",
                "synergy": "cooperation",
                "scalable": "able to grow",
                "robust": "strong",
                "cutting-edge": "advanced"
            }
            
            enhanced = content
            for jargon, simple in jargon_replacements.items():
                enhanced = re.sub(rf'\b{jargon}\b', simple, enhanced, flags=re.IGNORECASE)
            
            return enhanced
    
    async def _improve_transitions(self, content: str) -> str:
        """Improve transitions between paragraphs and sections."""
        if self.llm_adapter:
            prompt = """Improve the flow and transitions between paragraphs and sections.
            Add connecting phrases and transition words where appropriate to create
            better continuity. Do not change the core content."""
            return await self._apply_llm_enhancement(content, prompt, temperature=0.6)
        else:
            # Add simple transitions
            paragraphs = content.split('\n\n')
            if len(paragraphs) <= 1:
                return content
            
            transitions = [
                "Furthermore, ",
                "Additionally, ",
                "In addition, ",
                "Moreover, ",
                "Subsequently, ",
                "As a result, ",
                "Therefore, ",
                "However, ",
                "Nevertheless, ",
                "On the other hand, "
            ]
            
            enhanced_paragraphs = [paragraphs[0]]
            for i, para in enumerate(paragraphs[1:], 1):
                if para and not para[0].isupper():
                    # Add a transition if the paragraph doesn't start with one
                    transition = transitions[i % len(transitions)]
                    enhanced_paragraphs.append(transition + para)
                else:
                    enhanced_paragraphs.append(para)
            
            return '\n\n'.join(enhanced_paragraphs)


class CompletenessStrategy(EnhancementStrategy):
    """Strategy for improving document completeness."""
    
    async def enhance(self, content: str, metadata: Dict[str, Any]) -> str:
        """Enhance completeness by filling gaps and adding missing information."""
        logger.info("Applying completeness enhancement strategy")
        
        enhanced = content
        
        if self.config.completeness_settings.get("fill_gaps", True):
            enhanced = await self._fill_content_gaps(enhanced)
        
        if self.config.completeness_settings.get("add_examples", True):
            enhanced = await self._add_examples(enhanced)
        
        if self.config.completeness_settings.get("expand_sections", True):
            enhanced = await self._expand_sections(enhanced)
        
        self.applied_count += 1
        return enhanced
    
    def analyze(self, content: str) -> Dict[str, Any]:
        """Analyze content for completeness issues."""
        sections = self._split_into_sections(content)
        short_sections = [s for s in sections if len(s[1]) < 100]
        
        # Check for common missing elements
        has_introduction = any('intro' in s[0].lower() for s in sections)
        has_conclusion = any('conclu' in s[0].lower() for s in sections)
        has_examples = 'example' in content.lower() or 'e.g.' in content
        
        return {
            "section_count": len(sections),
            "short_sections": len(short_sections),
            "average_section_length": sum(len(s[1]) for s in sections) / max(len(sections), 1),
            "has_introduction": has_introduction,
            "has_conclusion": has_conclusion,
            "has_examples": has_examples
        }
    
    async def _fill_content_gaps(self, content: str) -> str:
        """Identify and fill content gaps."""
        if self.llm_adapter:
            prompt = """Identify any gaps or missing information in the following content.
            Add relevant details to make the document more complete and comprehensive.
            Focus on filling logical gaps and adding important context that may be missing."""
            return await self._apply_llm_enhancement(content, prompt, temperature=0.7)
        else:
            # Simple gap filling - add introduction/conclusion if missing
            sections = self._split_into_sections(content)
            
            if not any('intro' in s[0].lower() for s in sections):
                intro = "## Introduction\n\nThis document provides comprehensive information on the topic at hand.\n\n"
                content = intro + content
            
            if not any('conclu' in s[0].lower() for s in sections):
                conclusion = "\n\n## Conclusion\n\nIn summary, this document has covered the key aspects of the topic, providing detailed information and insights."
                content = content + conclusion
            
            return content
    
    async def _add_examples(self, content: str) -> str:
        """Add relevant examples to illustrate concepts."""
        if self.llm_adapter:
            prompt = """Add relevant examples to illustrate the concepts discussed in the content.
            Examples should be practical, clear, and directly related to the main points.
            Use 'For example', 'For instance', or 'Consider' to introduce examples."""
            return await self._apply_llm_enhancement(content, prompt, temperature=0.7)
        else:
            # Add placeholder examples where appropriate
            enhanced = content
            sections = self._split_into_sections(enhanced)
            
            for i, (header, section_content) in enumerate(sections):
                if 'example' not in section_content.lower() and len(section_content) > 200:
                    # Add a generic example placeholder
                    example = "\n\nFor example, this concept can be applied in practical scenarios where specific implementation details matter."
                    sections[i] = (header, section_content + example)
            
            return '\n\n'.join(s[1] for s in sections)
    
    async def _expand_sections(self, content: str) -> str:
        """Expand short sections with more detail."""
        min_length = self.config.completeness_settings.get("min_section_length", 100)
        
        if self.llm_adapter:
            prompt = f"""Expand any sections that are shorter than {min_length} characters.
            Add relevant details, explanations, and context to make each section comprehensive.
            Maintain consistency with the existing content style and tone."""
            return await self._apply_llm_enhancement(content, prompt, temperature=0.7)
        else:
            # Simple expansion for short sections
            sections = self._split_into_sections(content)
            expanded = []
            
            for header, section_content in sections:
                if len(section_content) < min_length and header:
                    expansion = f"\n\nThis section provides important information about {header.lower()}. "
                    expansion += "Further details and considerations are outlined below to ensure comprehensive coverage of this topic."
                    expanded.append(section_content + expansion)
                else:
                    expanded.append(section_content)
            
            return '\n\n'.join(expanded)


class ConsistencyStrategy(EnhancementStrategy):
    """Strategy for improving document consistency."""
    
    async def enhance(self, content: str, metadata: Dict[str, Any]) -> str:
        """Enhance consistency in terminology, formatting, and tone."""
        logger.info("Applying consistency enhancement strategy")
        
        enhanced = content
        
        if self.config.consistency_settings.get("standardize_terminology", True):
            enhanced = await self._standardize_terminology(enhanced)
        
        if self.config.consistency_settings.get("unify_formatting", True):
            enhanced = await self._unify_formatting(enhanced)
        
        if self.config.consistency_settings.get("align_tone", True):
            enhanced = await self._align_tone(enhanced)
        
        self.applied_count += 1
        return enhanced
    
    def analyze(self, content: str) -> Dict[str, Any]:
        """Analyze content for consistency issues."""
        # Find term variations
        term_patterns = [
            (r'\bAPI\b', r'\bapi\b', r'\bApi\b'),
            (r'\bURL\b', r'\burl\b', r'\bUrl\b'),
            (r'\bdatabase\b', r'\bDB\b', r'\bdb\b')
        ]
        
        inconsistencies = 0
        for patterns in term_patterns:
            variants = [len(re.findall(p, content, re.IGNORECASE)) for p in patterns]
            if sum(v > 0 for v in variants) > 1:
                inconsistencies += 1
        
        # Check heading consistency
        headings = re.findall(r'^#+\s+(.+)$', content, re.MULTILINE)
        heading_styles = set()
        for h in headings:
            if h[0].isupper():
                heading_styles.add('title')
            else:
                heading_styles.add('sentence')
        
        return {
            "terminology_inconsistencies": inconsistencies,
            "heading_style_variations": len(heading_styles),
            "has_mixed_formatting": bool(re.search(r'\*\*.*\*\*', content)) and bool(re.search(r'__.*__', content))
        }
    
    async def _standardize_terminology(self, content: str) -> str:
        """Standardize technical terminology throughout the document."""
        if self.llm_adapter:
            prompt = """Standardize all technical terminology throughout the document.
            Ensure consistent use of abbreviations, acronyms, and technical terms.
            Use the most common or first occurrence as the standard."""
            return await self._apply_llm_enhancement(content, prompt, temperature=0.3)
        else:
            # Simple term standardization
            replacements = {
                r'\bapi\b': 'API',
                r'\burl\b': 'URL',
                r'\bhttp\b': 'HTTP',
                r'\bjson\b': 'JSON',
                r'\bxml\b': 'XML',
                r'\bsql\b': 'SQL',
                r'\brest\b': 'REST',
                r'\bcrud\b': 'CRUD'
            }
            
            enhanced = content
            for pattern, replacement in replacements.items():
                enhanced = re.sub(pattern, replacement, enhanced, flags=re.IGNORECASE)
            
            return enhanced
    
    async def _unify_formatting(self, content: str) -> str:
        """Unify formatting styles throughout the document."""
        if self.llm_adapter:
            prompt = """Unify all formatting throughout the document.
            Use consistent markdown formatting for emphasis, lists, and code blocks.
            Standardize heading levels and list styles."""
            return await self._apply_llm_enhancement(content, prompt, temperature=0.3)
        else:
            # Standardize emphasis markers
            enhanced = re.sub(r'__(.+?)__', r'**\1**', content)  # Convert __ to **
            enhanced = re.sub(r'_(.+?)_', r'*\1*', enhanced)     # Convert _ to *
            
            # Standardize list markers
            lines = enhanced.split('\n')
            for i, line in enumerate(lines):
                if re.match(r'^\s*[-+]\s+', line):
                    lines[i] = re.sub(r'^(\s*)[-+]\s+', r'\1- ', line)
            
            return '\n'.join(lines)
    
    async def _align_tone(self, content: str) -> str:
        """Align tone and voice throughout the document."""
        if self.llm_adapter:
            prompt = """Align the tone and voice throughout the document.
            Ensure consistent use of active/passive voice, person (first/third),
            and formality level. Maintain professional technical documentation style."""
            return await self._apply_llm_enhancement(content, prompt, temperature=0.5)
        else:
            # Simple tone alignment - convert to active voice where possible
            enhanced = content
            
            # Common passive to active conversions
            passive_patterns = [
                (r'was (\w+ed) by', r''),  # "was created by" -> active form
                (r'is being (\w+ed)', r''),  # "is being processed" -> active form
                (r'has been (\w+ed)', r'')   # "has been updated" -> active form
            ]
            
            # This is simplified - real implementation would be more sophisticated
            return enhanced


class AccuracyStrategy(EnhancementStrategy):
    """Strategy for improving document accuracy."""
    
    async def enhance(self, content: str, metadata: Dict[str, Any]) -> str:
        """Enhance accuracy through fact-checking and validation."""
        logger.info("Applying accuracy enhancement strategy")
        
        enhanced = content
        
        if self.config.accuracy_settings.get("fact_checking", True):
            enhanced = await self._fact_check(enhanced)
        
        if self.config.accuracy_settings.get("technical_review", True):
            enhanced = await self._technical_review(enhanced)
        
        if self.config.accuracy_settings.get("citation_validation", True):
            enhanced = await self._validate_citations(enhanced)
        
        self.applied_count += 1
        return enhanced
    
    def analyze(self, content: str) -> Dict[str, Any]:
        """Analyze content for accuracy issues."""
        # Find potential inaccuracies
        numbers = re.findall(r'\b\d+\.?\d*\b', content)
        dates = re.findall(r'\b\d{4}[-/]\d{2}[-/]\d{2}\b', content)
        citations = re.findall(r'\[[\d,\s]+\]', content)
        
        # Check for hedge words that might indicate uncertainty
        hedge_words = ['might', 'possibly', 'perhaps', 'maybe', 'could be', 'seems']
        uncertainty_count = sum(content.lower().count(word) for word in hedge_words)
        
        return {
            "numeric_claims": len(numbers),
            "date_references": len(dates),
            "citations_count": len(citations),
            "uncertainty_indicators": uncertainty_count
        }
    
    async def _fact_check(self, content: str) -> str:
        """Perform fact-checking on claims and statements."""
        if self.llm_adapter:
            prompt = """Review the following content for factual accuracy.
            Correct any inaccurate statements, outdated information, or misleading claims.
            Add qualifiers where statements need clarification.
            Mark uncertain claims with appropriate hedging language."""
            return await self._apply_llm_enhancement(content, prompt, temperature=0.3)
        else:
            # Simple fact-checking markers
            enhanced = content
            
            # Add markers for claims that need verification
            claim_patterns = [
                r'(\d+%)',  # Percentage claims
                r'(always|never|all|none)',  # Absolute claims
                r'(studies show|research indicates|experts say)'  # Unsourced claims
            ]
            
            for pattern in claim_patterns:
                enhanced = re.sub(
                    pattern,
                    r'\1 [citation needed]',
                    enhanced,
                    flags=re.IGNORECASE
                )
            
            return enhanced
    
    async def _technical_review(self, content: str) -> str:
        """Review technical accuracy of code and configurations."""
        if self.llm_adapter:
            prompt = """Review the technical accuracy of any code snippets, configurations,
            commands, or technical instructions in the content.
            Correct any syntax errors, outdated practices, or security issues.
            Ensure all technical content follows current best practices."""
            return await self._apply_llm_enhancement(content, prompt, temperature=0.2)
        else:
            # Basic technical validation
            enhanced = content
            
            # Check for common issues in code blocks
            code_blocks = re.findall(r'```[\s\S]*?```', enhanced)
            for block in code_blocks:
                # Add warning for potentially insecure patterns
                if 'eval(' in block or 'exec(' in block:
                    enhanced = enhanced.replace(
                        block,
                        f"{block}\n⚠️ Security Warning: Use of eval/exec detected"
                    )
            
            return enhanced
    
    async def _validate_citations(self, content: str) -> str:
        """Validate and standardize citations."""
        if self.llm_adapter:
            prompt = """Review and standardize all citations and references in the content.
            Ensure citations are properly formatted and consistently styled.
            Add missing citations where claims need support."""
            return await self._apply_llm_enhancement(content, prompt, temperature=0.3)
        else:
            # Simple citation standardization
            enhanced = content
            
            # Convert various citation styles to a standard format
            enhanced = re.sub(r'\(([^)]+, \d{4})\)', r'[\1]', enhanced)  # (Author, Year) -> [Author, Year]
            
            # Add citation placeholders for unsourced claims
            if 'according to' in enhanced.lower() and '[' not in enhanced:
                enhanced = re.sub(
                    r'according to ([^,.\n]+)',
                    r'according to \1 [citation needed]',
                    enhanced,
                    flags=re.IGNORECASE
                )
            
            return enhanced


class ReadabilityStrategy(EnhancementStrategy):
    """Strategy for improving document readability."""
    
    async def enhance(self, content: str, metadata: Dict[str, Any]) -> str:
        """Enhance readability through structure and flow improvements."""
        logger.info("Applying readability enhancement strategy")
        
        enhanced = content
        
        if self.config.readability_settings.get("optimize_structure", True):
            enhanced = await self._optimize_structure(enhanced)
        
        if self.config.readability_settings.get("improve_flow", True):
            enhanced = await self._improve_flow(enhanced)
        
        if self.config.readability_settings.get("add_summaries", True):
            enhanced = await self._add_summaries(enhanced)
        
        self.applied_count += 1
        return enhanced
    
    def analyze(self, content: str) -> Dict[str, Any]:
        """Analyze content for readability issues."""
        if TEXTSTAT_AVAILABLE:
            try:
                reading_ease = flesch_reading_ease(content) if len(content) > 100 else 50
                grade_level = flesch_kincaid_grade(content) if len(content) > 100 else 10
            except:
                reading_ease = 50
                grade_level = 10
        else:
            # Fallback values when textstat is not available
            reading_ease = 50
            grade_level = 10
        
        # Structure analysis
        has_toc = '## Table of Contents' in content or '## TOC' in content
        sections = self._split_into_sections(content)
        has_headers = len(sections) > 1
        
        # Visual elements
        has_lists = bool(re.search(r'^\s*[-*+]\s+', content, re.MULTILINE))
        has_code_blocks = '```' in content
        
        return {
            "flesch_reading_ease": reading_ease,
            "flesch_kincaid_grade": grade_level,
            "has_toc": has_toc,
            "has_headers": has_headers,
            "has_lists": has_lists,
            "has_code_blocks": has_code_blocks,
            "section_count": len(sections)
        }
    
    async def _optimize_structure(self, content: str) -> str:
        """Optimize document structure for better readability."""
        if self.llm_adapter:
            prompt = """Optimize the document structure for better readability.
            Ensure logical flow of sections, appropriate heading hierarchy,
            and clear organization. Add or reorganize sections as needed."""
            return await self._apply_llm_enhancement(content, prompt, temperature=0.5)
        else:
            # Add table of contents if missing and document is long enough
            if len(content) > 1000 and '## Table of Contents' not in content:
                sections = self._split_into_sections(content)
                if len(sections) > 3:
                    toc = "## Table of Contents\n\n"
                    for header, _ in sections:
                        if header and header != "Introduction":
                            toc += f"- {header}\n"
                    toc += "\n"
                    
                    # Insert TOC after first paragraph
                    paragraphs = content.split('\n\n')
                    if len(paragraphs) > 1:
                        content = paragraphs[0] + '\n\n' + toc + '\n\n'.join(paragraphs[1:])
            
            return content
    
    async def _improve_flow(self, content: str) -> str:
        """Improve the flow and rhythm of the text."""
        target_grade = self.config.readability_settings.get("target_grade_level", 10)
        
        if self.llm_adapter:
            prompt = f"""Improve the flow and readability of the text.
            Target a reading grade level of approximately {target_grade}.
            Vary sentence length for better rhythm. Use active voice.
            Break up dense paragraphs and add white space where appropriate."""
            return await self._apply_llm_enhancement(content, prompt, temperature=0.6)
        else:
            # Simple flow improvements
            enhanced = content
            
            # Break up long paragraphs
            paragraphs = enhanced.split('\n\n')
            improved_paragraphs = []
            
            for para in paragraphs:
                sentences = para.split('. ')
                if len(sentences) > 5:
                    # Split into two paragraphs
                    mid = len(sentences) // 2
                    para1 = '. '.join(sentences[:mid]) + '.'
                    para2 = '. '.join(sentences[mid:])
                    improved_paragraphs.extend([para1, para2])
                else:
                    improved_paragraphs.append(para)
            
            return '\n\n'.join(improved_paragraphs)
    
    async def _add_summaries(self, content: str) -> str:
        """Add summaries to improve scannability."""
        if self.llm_adapter:
            prompt = """Add brief summaries or key takeaways to major sections.
            Use bullet points for easy scanning. Add an executive summary
            at the beginning if the document is long.
            Highlight important points with appropriate formatting."""
            return await self._apply_llm_enhancement(content, prompt, temperature=0.6)
        else:
            # Add simple summaries
            sections = self._split_into_sections(content)
            
            if len(sections) > 3 and not any('summary' in s[0].lower() for s in sections):
                # Add executive summary at the beginning
                summary = "## Executive Summary\n\n"
                summary += "This document covers the following key points:\n\n"
                for header, _ in sections[:5]:  # First 5 sections
                    if header and header != "Introduction":
                        summary += f"- {header}\n"
                summary += "\n"
                
                content = summary + content
            
            return content


class StrategyFactory:
    """Factory for creating enhancement strategies."""
    
    def __init__(self, settings: EnhancementSettings):
        """Initialize factory with settings."""
        self.settings = settings
        self.strategies: Dict[EnhancementType, EnhancementStrategy] = {}
        self.usage_stats: Dict[str, int] = {}
        
    def create_strategy(
        self,
        strategy_type: EnhancementType,
        llm_adapter: Optional[Any] = None
    ) -> EnhancementStrategy:
        """
        Create an enhancement strategy.
        
        Args:
            strategy_type: Type of strategy to create
            llm_adapter: Optional LLM adapter for AI-powered enhancements
            
        Returns:
            Enhancement strategy instance
        """
        if strategy_type in self.strategies:
            return self.strategies[strategy_type]
        
        config = self.settings.strategies.get(
            strategy_type,
            StrategyConfig()
        )
        
        strategy_class = {
            EnhancementType.CLARITY: ClarityStrategy,
            EnhancementType.COMPLETENESS: CompletenessStrategy,
            EnhancementType.CONSISTENCY: ConsistencyStrategy,
            EnhancementType.ACCURACY: AccuracyStrategy,
            EnhancementType.READABILITY: ReadabilityStrategy
        }.get(strategy_type)
        
        if strategy_class:
            strategy = strategy_class(config, llm_adapter)
            self.strategies[strategy_type] = strategy
            self.usage_stats[strategy.name] = 0
            return strategy
        else:
            raise ValueError(f"Unknown strategy type: {strategy_type}")
    
    def get_all_strategies(
        self,
        llm_adapter: Optional[Any] = None
    ) -> List[EnhancementStrategy]:
        """Get all enabled strategies."""
        strategies = []
        for strategy_type, config in self.settings.strategies.items():
            if config.enabled:
                strategies.append(self.create_strategy(strategy_type, llm_adapter))
        return strategies
    
    def get_usage_stats(self) -> Dict[str, int]:
        """Get usage statistics for strategies."""
        for strategy in self.strategies.values():
            self.usage_stats[strategy.name] = strategy.applied_count
        return self.usage_stats