"""
Unified dimension analyzers for M005 Quality Engine.

Consolidates all dimension implementations with configurable optimization
and security features.
"""

import re
import time
from typing import Dict, List, Optional, Set, Tuple, Any
from functools import lru_cache

from .base_dimension import (
    BaseDimensionAnalyzer, PatternBasedAnalyzer, StructuralAnalyzer,
    MetricsBasedAnalyzer, AnalysisContext
)
from .models import DimensionScore, QualityIssue, SeverityLevel, QualityDimension
from .utils import calculate_readability, extract_code_blocks, count_words


class UnifiedCompletenessAnalyzer(PatternBasedAnalyzer):
    """Unified completeness analyzer with optimizations."""
    
    def __init__(self, performance_mode: bool = False, security_enabled: bool = False):
        """Initialize completeness analyzer."""
        super().__init__("Completeness", QualityDimension.COMPLETENESS)
        self.performance_mode = performance_mode
        self.security_enabled = security_enabled
        
    def _initialize_patterns(self) -> Dict[str, str]:
        """Initialize completeness patterns."""
        return {
            'section_header': r'^#{1,6}\s+(.+)$',
            'todo_marker': r'(?i)\b(todo|fixme|xxx|hack|note)\b:?\s*',
            'placeholder': r'\[(placeholder|tbd|coming soon|wip)\]',
            'empty_section': r'^#{1,6}\s+[^#\n]+\n+(?=#{1,6}|\Z)',
            'code_block': r'```[\s\S]*?```',
            'link': r'\[([^\]]+)\]\(([^)]+)\)',
            'image': r'!\[([^\]]*)\]\(([^)]+)\)',
            'list_item': r'^\s*[-*+]\s+.+$|^\s*\d+\.\s+.+$',
            'table': r'^\|.+\|$',
            'reference': r'\[([^\]]+)\]:\s*(.+)$'
        }
        
    def analyze(self, context: AnalysisContext) -> DimensionScore:
        """Analyze document completeness."""
        if self.security_enabled:
            self.validate_input(context)
            
        # Check cache if enabled
        if context.cache_enabled and self.performance_mode:
            cache_key = f"completeness:{context.content_hash}"
            cached = self._get_cached_result(cache_key)
            if cached:
                return cached
                
        start_time = time.perf_counter()
        
        # Perform checks
        checks = self.get_check_functions()
        issues = []
        passed = 0
        total = len(checks)
        
        for check_name, check_func in checks.items():
            try:
                result = check_func(context.content)
                if result['passed']:
                    passed += 1
                else:
                    issues.extend(result.get('issues', []))
            except Exception as e:
                # Log but don't fail
                issues.append(self._create_issue(
                    f"Check {check_name} failed: {str(e)}",
                    SeverityLevel.MINOR
                ))
                
        # Calculate score
        score = self._calculate_score(passed, total)
        
        # Create result
        result = DimensionScore(
            dimension=self.dimension,
            score=score,
            issues=issues,
            metadata={
                'checks_passed': passed,
                'total_checks': total,
                'analysis_time_ms': (time.perf_counter() - start_time) * 1000
            }
        )
        
        # Cache if enabled
        if context.cache_enabled and self.performance_mode:
            self._cache_result(cache_key, result)
            
        return result
        
    def get_check_functions(self) -> Dict[str, callable]:
        """Get completeness check functions."""
        return {
            'has_sections': self._check_sections,
            'no_todos': self._check_todos,
            'no_placeholders': self._check_placeholders,
            'sections_have_content': self._check_section_content,
            'has_examples': self._check_examples,
            'has_references': self._check_references,
            'metadata_complete': self._check_metadata
        }
        
    def _check_sections(self, content: str) -> Dict[str, Any]:
        """Check for required sections."""
        pattern = self._compile_pattern(self._patterns['section_header'], re.MULTILINE)
        sections = pattern.findall(content)
        
        required = ['Introduction', 'Usage', 'API', 'Examples']
        found = [s for s in required if any(r in h for h in sections for r in [s])]
        
        issues = []
        for section in required:
            if section not in found:
                issues.append(self._create_issue(
                    f"Missing required section: {section}",
                    SeverityLevel.MAJOR
                ))
                
        return {
            'passed': len(found) >= len(required) * 0.75,
            'issues': issues
        }
        
    def _check_todos(self, content: str) -> Dict[str, Any]:
        """Check for TODO markers."""
        pattern = self._compile_pattern(self._patterns['todo_marker'], re.MULTILINE)
        todos = pattern.findall(content)
        
        issues = []
        for todo in todos[:5]:  # Limit to first 5
            issues.append(self._create_issue(
                f"Incomplete TODO found: {todo}",
                SeverityLevel.MINOR
            ))
            
        return {
            'passed': len(todos) == 0,
            'issues': issues
        }
        
    def _check_placeholders(self, content: str) -> Dict[str, Any]:
        """Check for placeholder content."""
        pattern = self._compile_pattern(self._patterns['placeholder'], re.IGNORECASE)
        placeholders = pattern.findall(content)
        
        issues = []
        for placeholder in placeholders[:3]:
            issues.append(self._create_issue(
                f"Placeholder content found: {placeholder}",
                SeverityLevel.MAJOR
            ))
            
        return {
            'passed': len(placeholders) == 0,
            'issues': issues
        }
        
    def _check_section_content(self, content: str) -> Dict[str, Any]:
        """Check that sections have content."""
        lines = content.split('\n')
        issues = []
        empty_sections = 0
        
        for i, line in enumerate(lines):
            if line.startswith('#'):
                # Check if next non-empty line is another header
                j = i + 1
                while j < len(lines) and not lines[j].strip():
                    j += 1
                if j < len(lines) and lines[j].startswith('#'):
                    empty_sections += 1
                    issues.append(self._create_issue(
                        f"Empty section at line {i+1}: {line}",
                        SeverityLevel.MAJOR,
                        line=i+1
                    ))
                    
        return {
            'passed': empty_sections == 0,
            'issues': issues[:3]  # Limit issues
        }
        
    def _check_examples(self, content: str) -> Dict[str, Any]:
        """Check for code examples."""
        pattern = self._compile_pattern(self._patterns['code_block'])
        examples = pattern.findall(content)
        
        issues = []
        if len(examples) < 2:
            issues.append(self._create_issue(
                "Insufficient code examples (minimum 2 recommended)",
                SeverityLevel.MINOR
            ))
            
        return {
            'passed': len(examples) >= 2,
            'issues': issues
        }
        
    def _check_references(self, content: str) -> Dict[str, Any]:
        """Check for references and links."""
        link_pattern = self._compile_pattern(self._patterns['link'])
        ref_pattern = self._compile_pattern(self._patterns['reference'])
        
        links = link_pattern.findall(content)
        refs = ref_pattern.findall(content)
        
        total_references = len(links) + len(refs)
        
        issues = []
        if total_references < 1:
            issues.append(self._create_issue(
                "No references or links found",
                SeverityLevel.MINOR
            ))
            
        return {
            'passed': total_references >= 1,
            'issues': issues
        }
        
    def _check_metadata(self, content: str) -> Dict[str, Any]:
        """Check for document metadata."""
        # Simple check for common metadata patterns
        has_title = bool(re.search(r'^#\s+\S', content, re.MULTILINE))
        has_description = len(content.split('\n')[0:5]) > 2
        
        issues = []
        if not has_title:
            issues.append(self._create_issue(
                "Missing document title",
                SeverityLevel.MAJOR
            ))
            
        return {
            'passed': has_title and has_description,
            'issues': issues
        }


class UnifiedClarityAnalyzer(MetricsBasedAnalyzer):
    """Unified clarity analyzer with optimizations."""
    
    def __init__(self, performance_mode: bool = False, security_enabled: bool = False):
        """Initialize clarity analyzer."""
        super().__init__("Clarity", QualityDimension.CLARITY)
        self.performance_mode = performance_mode
        self.security_enabled = security_enabled
        
    def _initialize_thresholds(self) -> Dict[str, Tuple[float, float]]:
        """Initialize clarity thresholds."""
        return {
            'readability_score': (60, 100),  # Flesch reading ease
            'avg_sentence_length': (10, 25),
            'avg_word_length': (3, 7),
            'passive_voice_ratio': (0, 0.2),
            'complex_word_ratio': (0, 0.3)
        }
        
    def analyze(self, context: AnalysisContext) -> DimensionScore:
        """Analyze document clarity."""
        if self.security_enabled:
            self.validate_input(context)
            
        # Calculate metrics
        metrics = self.calculate_metrics(context.content)
        
        # Evaluate against thresholds
        score, issues = self.evaluate_metrics(metrics)
        
        # Additional clarity checks
        additional_issues = self._check_clarity_issues(context.content)
        issues.extend(additional_issues)
        
        return DimensionScore(
            dimension=self.dimension,
            score=score,
            issues=issues,
            metadata={'metrics': metrics}
        )
        
    def _calculate_specific_metrics(self, content: str) -> Dict[str, float]:
        """Calculate clarity-specific metrics."""
        metrics = {}
        
        # Readability score
        metrics['readability_score'] = calculate_readability(content)
        
        # Sentence metrics
        sentences = re.split(r'[.!?]+', content)
        sentences = [s.strip() for s in sentences if s.strip()]
        
        if sentences:
            words_per_sentence = [len(s.split()) for s in sentences]
            metrics['avg_sentence_length'] = sum(words_per_sentence) / len(sentences)
        else:
            metrics['avg_sentence_length'] = 0
            
        # Word metrics
        words = content.split()
        if words:
            metrics['avg_word_length'] = sum(len(w) for w in words) / len(words)
            
            # Complex words (3+ syllables)
            complex_words = sum(1 for w in words if self._count_syllables(w) >= 3)
            metrics['complex_word_ratio'] = complex_words / len(words)
        else:
            metrics['avg_word_length'] = 0
            metrics['complex_word_ratio'] = 0
            
        # Passive voice detection (simplified)
        passive_patterns = [
            r'\b(is|are|was|were|been|being)\s+\w+ed\b',
            r'\b(is|are|was|were|been|being)\s+\w+en\b'
        ]
        passive_count = 0
        for pattern in passive_patterns:
            passive_count += len(re.findall(pattern, content, re.IGNORECASE))
            
        total_sentences = len(sentences) if sentences else 1
        metrics['passive_voice_ratio'] = passive_count / total_sentences
        
        return metrics
        
    @lru_cache(maxsize=1000)
    def _count_syllables(self, word: str) -> int:
        """Count syllables in a word (simplified)."""
        word = word.lower()
        vowels = 'aeiou'
        syllables = 0
        previous_was_vowel = False
        
        for char in word:
            is_vowel = char in vowels
            if is_vowel and not previous_was_vowel:
                syllables += 1
            previous_was_vowel = is_vowel
            
        # Adjust for silent e
        if word.endswith('e'):
            syllables -= 1
            
        return max(1, syllables)
        
    def _check_clarity_issues(self, content: str) -> List[QualityIssue]:
        """Check for additional clarity issues."""
        issues = []
        
        # Check for jargon without explanation
        jargon_pattern = r'\b[A-Z]{3,}\b'  # Simple acronym detection
        acronyms = re.findall(jargon_pattern, content)
        undefined_acronyms = []
        
        for acronym in set(acronyms):
            # Check if acronym is defined
            definition_pattern = rf'{acronym}\s*\([^)]+\)|{acronym}.*?stands for'
            if not re.search(definition_pattern, content):
                undefined_acronyms.append(acronym)
                
        if undefined_acronyms:
            issues.append(self._create_issue(
                f"Undefined acronyms: {', '.join(undefined_acronyms[:3])}",
                SeverityLevel.MINOR
            ))
            
        # Check for ambiguous pronouns
        ambiguous_pattern = r'\b(it|this|that|these|those)\b(?!\s+(is|are|was|were))'
        ambiguous = re.findall(ambiguous_pattern, content, re.IGNORECASE)
        
        if len(ambiguous) > 10:
            issues.append(self._create_issue(
                "Excessive use of ambiguous pronouns",
                SeverityLevel.MINOR
            ))
            
        return issues
        
    def get_check_functions(self) -> Dict[str, callable]:
        """Get clarity check functions."""
        return {
            'readability': lambda c: self._check_readability(c),
            'sentence_structure': lambda c: self._check_sentences(c),
            'word_choice': lambda c: self._check_word_choice(c)
        }
        
    def _check_readability(self, content: str) -> Dict[str, Any]:
        """Check readability score."""
        score = calculate_readability(content)
        passed = 60 <= score <= 100
        
        issues = []
        if score < 60:
            issues.append(self._create_issue(
                f"Low readability score: {score:.1f} (target: 60-100)",
                SeverityLevel.MAJOR
            ))
            
        return {'passed': passed, 'issues': issues}
        
    def _check_sentences(self, content: str) -> Dict[str, Any]:
        """Check sentence structure."""
        sentences = re.split(r'[.!?]+', content)
        sentences = [s.strip() for s in sentences if s.strip()]
        
        issues = []
        long_sentences = [s for s in sentences if len(s.split()) > 30]
        
        if long_sentences:
            issues.append(self._create_issue(
                f"Found {len(long_sentences)} overly long sentences (>30 words)",
                SeverityLevel.MINOR
            ))
            
        return {'passed': len(long_sentences) < 3, 'issues': issues}
        
    def _check_word_choice(self, content: str) -> Dict[str, Any]:
        """Check word choice and complexity."""
        words = content.split()
        complex_words = [w for w in words if self._count_syllables(w) >= 4]
        
        ratio = len(complex_words) / max(1, len(words))
        
        issues = []
        if ratio > 0.2:
            issues.append(self._create_issue(
                f"High complex word ratio: {ratio:.2%} (target: <20%)",
                SeverityLevel.MINOR
            ))
            
        return {'passed': ratio <= 0.2, 'issues': issues}


class UnifiedStructureAnalyzer(StructuralAnalyzer):
    """Unified structure analyzer with optimizations."""
    
    def __init__(self, performance_mode: bool = False, security_enabled: bool = False):
        """Initialize structure analyzer."""
        super().__init__("Structure", QualityDimension.STRUCTURE)
        self.performance_mode = performance_mode
        self.security_enabled = security_enabled
        
    def analyze(self, context: AnalysisContext) -> DimensionScore:
        """Analyze document structure."""
        if self.security_enabled:
            self.validate_input(context)
            
        # Analyze structure
        structure = self.analyze_structure(context.content)
        
        # Evaluate structure
        issues = []
        score = 1.0
        
        # Check hierarchy
        if not self._check_hierarchy(structure['sections']):
            issues.append(self._create_issue(
                "Inconsistent heading hierarchy",
                SeverityLevel.MAJOR
            ))
            score -= 0.2
            
        # Check balance
        if not self._check_balance(structure['sections']):
            issues.append(self._create_issue(
                "Unbalanced section lengths",
                SeverityLevel.MINOR
            ))
            score -= 0.1
            
        # Check organization
        if structure['consistency'] < 0.7:
            issues.append(self._create_issue(
                "Inconsistent document organization",
                SeverityLevel.MINOR
            ))
            score -= 0.1
            
        return DimensionScore(
            dimension=self.dimension,
            score=max(0, score),
            issues=issues,
            metadata={'structure': structure}
        )
        
    def _identify_sections(self, lines: List[str]) -> List[Dict[str, Any]]:
        """Identify document sections."""
        sections = []
        current_section = None
        
        for i, line in enumerate(lines):
            if line.startswith('#'):
                level = len(line.split()[0])
                title = line[level:].strip()
                
                if current_section:
                    current_section['end_line'] = i - 1
                    sections.append(current_section)
                    
                current_section = {
                    'level': level,
                    'title': title,
                    'start_line': i,
                    'end_line': None
                }
                
        if current_section:
            current_section['end_line'] = len(lines) - 1
            sections.append(current_section)
            
        return sections
        
    def _calculate_nesting(self, lines: List[str]) -> Dict[str, int]:
        """Calculate nesting levels."""
        nesting = {
            'max_depth': 0,
            'avg_depth': 0,
            'total_nested': 0
        }
        
        current_depth = 0
        depths = []
        
        for line in lines:
            # Simple nesting based on indentation
            indent = len(line) - len(line.lstrip())
            depth = indent // 2  # Assuming 2-space indentation
            
            depths.append(depth)
            nesting['max_depth'] = max(nesting['max_depth'], depth)
            
            if depth > 0:
                nesting['total_nested'] += 1
                
        if depths:
            nesting['avg_depth'] = sum(depths) / len(depths)
            
        return nesting
        
    def _check_consistency(self, lines: List[str]) -> float:
        """Check structural consistency."""
        consistency_score = 1.0
        
        # Check indentation consistency
        indents = set()
        for line in lines:
            if line.strip():
                indent = len(line) - len(line.lstrip())
                if indent > 0:
                    indents.add(indent)
                    
        # Penalty for inconsistent indentation
        if len(indents) > 3:
            consistency_score -= 0.2
            
        # Check list formatting consistency
        list_styles = set()
        for line in lines:
            if re.match(r'^\s*[-*+]\s', line):
                list_styles.add(line.strip()[0])
            elif re.match(r'^\s*\d+\.\s', line):
                list_styles.add('numbered')
                
        # Penalty for mixed list styles
        if len(list_styles) > 2:
            consistency_score -= 0.1
            
        return max(0, consistency_score)
        
    def _check_hierarchy(self, sections: List[Dict[str, Any]]) -> bool:
        """Check heading hierarchy."""
        if not sections:
            return True
            
        prev_level = 0
        for section in sections:
            level = section['level']
            
            # Check for skipped levels
            if level > prev_level + 1:
                return False
                
            prev_level = level
            
        return True
        
    def _check_balance(self, sections: List[Dict[str, Any]]) -> bool:
        """Check section balance."""
        if len(sections) < 2:
            return True
            
        lengths = []
        for section in sections:
            if section['end_line'] is not None:
                length = section['end_line'] - section['start_line']
                lengths.append(length)
                
        if not lengths:
            return True
            
        avg_length = sum(lengths) / len(lengths)
        
        # Check for extreme outliers
        for length in lengths:
            if length > avg_length * 5 or length < avg_length * 0.1:
                return False
                
        return True
        
    def get_check_functions(self) -> Dict[str, callable]:
        """Get structure check functions."""
        return {
            'hierarchy': lambda c: self._validate_hierarchy(c),
            'organization': lambda c: self._validate_organization(c),
            'flow': lambda c: self._validate_flow(c)
        }
        
    def _validate_hierarchy(self, content: str) -> Dict[str, Any]:
        """Validate heading hierarchy."""
        lines = content.split('\n')
        sections = self._identify_sections(lines)
        
        passed = self._check_hierarchy(sections)
        issues = []
        
        if not passed:
            issues.append(self._create_issue(
                "Invalid heading hierarchy detected",
                SeverityLevel.MAJOR
            ))
            
        return {'passed': passed, 'issues': issues}
        
    def _validate_organization(self, content: str) -> Dict[str, Any]:
        """Validate document organization."""
        lines = content.split('\n')
        consistency = self._check_consistency(lines)
        
        passed = consistency >= 0.7
        issues = []
        
        if not passed:
            issues.append(self._create_issue(
                f"Poor organization consistency: {consistency:.2f}",
                SeverityLevel.MINOR
            ))
            
        return {'passed': passed, 'issues': issues}
        
    def _validate_flow(self, content: str) -> Dict[str, Any]:
        """Validate document flow."""
        # Check for logical flow indicators
        transition_words = [
            'however', 'therefore', 'furthermore', 'additionally',
            'consequently', 'meanwhile', 'subsequently', 'finally'
        ]
        
        found_transitions = 0
        for word in transition_words:
            pattern = rf'\b{word}\b'
            found_transitions += len(re.findall(pattern, content, re.IGNORECASE))
            
        # Expect at least some transitions in longer documents
        word_count = len(content.split())
        expected_transitions = word_count // 200  # Roughly 1 per 200 words
        
        passed = found_transitions >= expected_transitions
        issues = []
        
        if not passed:
            issues.append(self._create_issue(
                "Insufficient transition words for document flow",
                SeverityLevel.MINOR
            ))
            
        return {'passed': passed, 'issues': issues}


class UnifiedAccuracyAnalyzer(PatternBasedAnalyzer):
    """Unified accuracy analyzer with optimizations."""
    
    def __init__(self, performance_mode: bool = False, security_enabled: bool = False):
        """Initialize accuracy analyzer."""
        super().__init__("Accuracy", QualityDimension.ACCURACY)
        self.performance_mode = performance_mode
        self.security_enabled = security_enabled
        
    def _initialize_patterns(self) -> Dict[str, str]:
        """Initialize accuracy patterns."""
        return {
            'broken_link': r'\[([^\]]+)\]\(((?!http|https|#|/|mailto:)[^)]*)\)',
            'invalid_url': r'https?://[^\s<>"{}|\\^`\[\]]+(?:\.[^\s<>"{}|\\^`\[\]]+)*',
            'code_error': r'```[\s\S]*?(SyntaxError|TypeError|ValueError|ImportError)[\s\S]*?```',
            'version_mismatch': r'v?\d+\.\d+(?:\.\d+)?',
            'date_format': r'\b\d{1,2}[-/]\d{1,2}[-/]\d{2,4}\b',
            'typo_pattern': r'\b(teh|thier|recieve|occured|seperate)\b',
            'duplicate_word': r'\b(\w+)\s+\1\b'
        }
        
    def analyze(self, context: AnalysisContext) -> DimensionScore:
        """Analyze document accuracy."""
        if self.security_enabled:
            self.validate_input(context)
            
        issues = []
        checks_passed = 0
        total_checks = 6
        
        # Check for broken links
        if self._check_links(context.content):
            checks_passed += 1
        else:
            issues.append(self._create_issue(
                "Potential broken links detected",
                SeverityLevel.MAJOR
            ))
            
        # Check for code errors
        if self._check_code_accuracy(context.content):
            checks_passed += 1
        else:
            issues.append(self._create_issue(
                "Code examples may contain errors",
                SeverityLevel.MAJOR
            ))
            
        # Check for typos
        typos = self._find_typos(context.content)
        if not typos:
            checks_passed += 1
        else:
            for typo in typos[:3]:
                issues.append(self._create_issue(
                    f"Possible typo: '{typo}'",
                    SeverityLevel.MINOR
                ))
                
        # Check for duplicate words
        duplicates = self._find_duplicates(context.content)
        if not duplicates:
            checks_passed += 1
        else:
            for dup in duplicates[:3]:
                issues.append(self._create_issue(
                    f"Duplicate word: '{dup}'",
                    SeverityLevel.MINOR
                ))
                
        # Check date formats
        if self._check_date_formats(context.content):
            checks_passed += 1
            
        # Check version consistency
        if self._check_version_consistency(context.content):
            checks_passed += 1
        else:
            issues.append(self._create_issue(
                "Inconsistent version references",
                SeverityLevel.MINOR
            ))
            
        score = self._calculate_score(checks_passed, total_checks)
        
        return DimensionScore(
            dimension=self.dimension,
            score=score,
            issues=issues,
            metadata={
                'checks_passed': checks_passed,
                'total_checks': total_checks
            }
        )
        
    def _check_links(self, content: str) -> bool:
        """Check for broken links."""
        pattern = self._compile_pattern(self._patterns['broken_link'])
        potential_broken = pattern.findall(content)
        
        # Simple heuristic: relative links should exist
        broken_count = 0
        for text, url in potential_broken:
            if url and not url.startswith(('http', '#', '/')):
                # Potentially broken relative link
                broken_count += 1
                
        return broken_count < 3
        
    def _check_code_accuracy(self, content: str) -> bool:
        """Check code examples for errors."""
        pattern = self._compile_pattern(self._patterns['code_error'])
        errors = pattern.findall(content)
        return len(errors) == 0
        
    def _find_typos(self, content: str) -> List[str]:
        """Find common typos."""
        pattern = self._compile_pattern(self._patterns['typo_pattern'], re.IGNORECASE)
        return pattern.findall(content)
        
    def _find_duplicates(self, content: str) -> List[str]:
        """Find duplicate words."""
        pattern = self._compile_pattern(self._patterns['duplicate_word'], re.IGNORECASE)
        matches = pattern.findall(content)
        # Filter out intentional duplicates
        return [m for m in matches if m.lower() not in ['that', 'had', 'very']]
        
    def _check_date_formats(self, content: str) -> bool:
        """Check date format consistency."""
        pattern = self._compile_pattern(self._patterns['date_format'])
        dates = pattern.findall(content)
        
        if not dates:
            return True
            
        # Check for consistent format
        formats = set()
        for date in dates:
            if '-' in date:
                formats.add('dash')
            if '/' in date:
                formats.add('slash')
                
        return len(formats) <= 1
        
    def _check_version_consistency(self, content: str) -> bool:
        """Check version reference consistency."""
        pattern = self._compile_pattern(self._patterns['version_mismatch'])
        versions = pattern.findall(content)
        
        if len(versions) < 2:
            return True
            
        # Group by major version
        major_versions = {}
        for version in versions:
            parts = version.lstrip('v').split('.')
            if parts:
                major = parts[0]
                if major not in major_versions:
                    major_versions[major] = []
                major_versions[major].append(version)
                
        # Check for inconsistencies within same major version
        for major, version_list in major_versions.items():
            if len(set(version_list)) > 3:
                return False
                
        return True
        
    def get_check_functions(self) -> Dict[str, callable]:
        """Get accuracy check functions."""
        return {
            'links_valid': lambda c: {'passed': self._check_links(c), 'issues': []},
            'code_accurate': lambda c: {'passed': self._check_code_accuracy(c), 'issues': []},
            'no_typos': lambda c: {'passed': not self._find_typos(c), 'issues': []},
            'no_duplicates': lambda c: {'passed': not self._find_duplicates(c), 'issues': []},
            'dates_consistent': lambda c: {'passed': self._check_date_formats(c), 'issues': []},
            'versions_consistent': lambda c: {'passed': self._check_version_consistency(c), 'issues': []}
        }


class UnifiedFormattingAnalyzer(PatternBasedAnalyzer):
    """Unified formatting analyzer with optimizations."""
    
    def __init__(self, performance_mode: bool = False, security_enabled: bool = False):
        """Initialize formatting analyzer."""
        super().__init__("Formatting", QualityDimension.FORMATTING)
        self.performance_mode = performance_mode
        self.security_enabled = security_enabled
        
    def _initialize_patterns(self) -> Dict[str, str]:
        """Initialize formatting patterns."""
        return {
            'heading_format': r'^#{1,6}\s+\S',
            'list_format': r'^\s*[-*+]\s+\S|^\s*\d+\.\s+\S',
            'code_fence': r'^```[\w]*$',
            'trailing_whitespace': r'\s+$',
            'multiple_blank_lines': r'\n{3,}',
            'inconsistent_indent': r'^( {2}| {4}|\t)',
            'line_length': r'^.{120,}$',
            'table_format': r'^\|.*\|$'
        }
        
    def analyze(self, context: AnalysisContext) -> DimensionScore:
        """Analyze document formatting."""
        if self.security_enabled:
            self.validate_input(context)
            
        lines = context.content.split('\n')
        issues = []
        score = 1.0
        
        # Check line length
        long_lines = self._check_line_length(lines)
        if long_lines:
            issues.append(self._create_issue(
                f"Found {len(long_lines)} lines exceeding 120 characters",
                SeverityLevel.MINOR
            ))
            score -= 0.1
            
        # Check whitespace issues
        whitespace_issues = self._check_whitespace(lines)
        if whitespace_issues:
            issues.extend(whitespace_issues)
            score -= 0.1 * len(whitespace_issues)
            
        # Check indentation consistency
        if not self._check_indentation(lines):
            issues.append(self._create_issue(
                "Inconsistent indentation detected",
                SeverityLevel.MINOR
            ))
            score -= 0.1
            
        # Check markdown formatting
        md_issues = self._check_markdown_format(context.content)
        if md_issues:
            issues.extend(md_issues)
            score -= 0.05 * len(md_issues)
            
        # Check code block formatting
        if not self._check_code_blocks(context.content):
            issues.append(self._create_issue(
                "Improperly formatted code blocks",
                SeverityLevel.MINOR
            ))
            score -= 0.1
            
        return DimensionScore(
            dimension=self.dimension,
            score=max(0, score),
            issues=issues[:10],  # Limit issues
            metadata={'lines_checked': len(lines)}
        )
        
    def _check_line_length(self, lines: List[str]) -> List[int]:
        """Check for lines exceeding length limit."""
        long_lines = []
        for i, line in enumerate(lines):
            if len(line) > 120:
                long_lines.append(i + 1)
        return long_lines[:5]  # Return first 5
        
    def _check_whitespace(self, lines: List[str]) -> List[QualityIssue]:
        """Check for whitespace issues."""
        issues = []
        
        # Trailing whitespace
        pattern = self._compile_pattern(self._patterns['trailing_whitespace'])
        for i, line in enumerate(lines):
            if pattern.search(line):
                issues.append(self._create_issue(
                    f"Trailing whitespace at line {i+1}",
                    SeverityLevel.MINOR,
                    line=i+1
                ))
                if len(issues) >= 3:
                    break
                    
        # Multiple blank lines
        content = '\n'.join(lines)
        multiple_blanks = self._compile_pattern(self._patterns['multiple_blank_lines'])
        if multiple_blanks.search(content):
            issues.append(self._create_issue(
                "Multiple consecutive blank lines found",
                SeverityLevel.MINOR
            ))
            
        return issues
        
    def _check_indentation(self, lines: List[str]) -> bool:
        """Check indentation consistency."""
        indent_types = set()
        
        for line in lines:
            if line and line[0] in ' \t':
                # Detect indent type
                if line.startswith('    '):
                    indent_types.add('spaces-4')
                elif line.startswith('  '):
                    indent_types.add('spaces-2')
                elif line.startswith('\t'):
                    indent_types.add('tabs')
                    
        # Should use consistent indentation
        return len(indent_types) <= 1
        
    def _check_markdown_format(self, content: str) -> List[QualityIssue]:
        """Check markdown formatting."""
        issues = []
        lines = content.split('\n')
        
        for i, line in enumerate(lines):
            # Check heading format
            if line.startswith('#'):
                if not re.match(r'^#{1,6}\s+\S', line):
                    issues.append(self._create_issue(
                        f"Improper heading format at line {i+1}",
                        SeverityLevel.MINOR,
                        line=i+1
                    ))
                    
            # Check list format
            if re.match(r'^\s*[-*+]', line):
                if not re.match(r'^\s*[-*+]\s+\S', line):
                    issues.append(self._create_issue(
                        f"Improper list format at line {i+1}",
                        SeverityLevel.MINOR,
                        line=i+1
                    ))
                    
        return issues[:5]  # Limit issues
        
    def _check_code_blocks(self, content: str) -> bool:
        """Check code block formatting."""
        # Check for properly closed code blocks
        fence_count = content.count('```')
        return fence_count % 2 == 0
        
    def get_check_functions(self) -> Dict[str, callable]:
        """Get formatting check functions."""
        return {
            'line_length': lambda c: self._validate_line_length(c),
            'whitespace': lambda c: self._validate_whitespace(c),
            'indentation': lambda c: self._validate_indentation(c),
            'markdown': lambda c: self._validate_markdown(c),
            'code_blocks': lambda c: {'passed': self._check_code_blocks(c), 'issues': []}
        }
        
    def _validate_line_length(self, content: str) -> Dict[str, Any]:
        """Validate line length."""
        lines = content.split('\n')
        long_lines = self._check_line_length(lines)
        
        return {
            'passed': len(long_lines) < 5,
            'issues': []
        }
        
    def _validate_whitespace(self, content: str) -> Dict[str, Any]:
        """Validate whitespace."""
        lines = content.split('\n')
        issues = self._check_whitespace(lines)
        
        return {
            'passed': len(issues) == 0,
            'issues': issues
        }
        
    def _validate_indentation(self, content: str) -> Dict[str, Any]:
        """Validate indentation."""
        lines = content.split('\n')
        consistent = self._check_indentation(lines)
        
        return {
            'passed': consistent,
            'issues': []
        }
        
    def _validate_markdown(self, content: str) -> Dict[str, Any]:
        """Validate markdown formatting."""
        issues = self._check_markdown_format(content)
        
        return {
            'passed': len(issues) == 0,
            'issues': issues
        }