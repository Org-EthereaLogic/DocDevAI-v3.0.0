"""
Pattern recognition for identifying documentation improvement opportunities.

Analyzes text patterns to identify areas requiring refinement and tracks
improvement patterns over time for learning.
"""

import re
import json
from typing import Dict, List, Optional, Tuple, Set, Any
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from enum import Enum
import numpy as np


class PatternType(Enum):
    """Types of patterns to recognize."""
    STRUCTURAL = "structural"
    LINGUISTIC = "linguistic"
    TECHNICAL = "technical"
    FORMATTING = "formatting"
    SEMANTIC = "semantic"


@dataclass
class Pattern:
    """Represents a recognized pattern in documentation."""
    type: PatternType
    name: str
    description: str
    occurrences: List[Dict[str, Any]]
    severity: float  # 0.0 to 1.0
    improvement_priority: int  # 1 (highest) to 5 (lowest)
    suggested_action: str
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert pattern to dictionary."""
        return {
            'type': self.type.value,
            'name': self.name,
            'description': self.description,
            'occurrences': self.occurrences,
            'severity': self.severity,
            'improvement_priority': self.improvement_priority,
            'suggested_action': self.suggested_action
        }


@dataclass
class PatternAnalysis:
    """Complete pattern analysis results."""
    patterns: List[Pattern]
    summary: Dict[str, Any]
    improvement_map: Dict[str, List[str]]
    learning_insights: List[str]
    
    def get_high_priority_patterns(self) -> List[Pattern]:
        """Get patterns with high improvement priority."""
        return [p for p in self.patterns if p.improvement_priority <= 2]
    
    def get_patterns_by_type(self, pattern_type: PatternType) -> List[Pattern]:
        """Get patterns of specific type."""
        return [p for p in self.patterns if p.type == pattern_type]


class PatternRecognizer:
    """
    Identifies patterns in documentation that indicate improvement opportunities.
    
    Recognizes structural, linguistic, technical, and formatting patterns
    that can be improved through optimization.
    """
    
    def __init__(self, learning_enabled: bool = True):
        """
        Initialize pattern recognizer.
        
        Args:
            learning_enabled: Enable pattern learning from improvements
        """
        self.learning_enabled = learning_enabled
        self._init_pattern_definitions()
        self._init_pattern_matchers()
        self.learned_patterns = defaultdict(list) if learning_enabled else None
    
    def _init_pattern_definitions(self):
        """Initialize pattern definitions and rules."""
        self.pattern_definitions = {
            PatternType.STRUCTURAL: {
                'missing_introduction': {
                    'regex': None,  # Custom check
                    'description': 'Document lacks proper introduction',
                    'severity': 0.8,
                    'priority': 1,
                    'action': 'Add comprehensive introduction section'
                },
                'unbalanced_sections': {
                    'regex': None,  # Custom check
                    'description': 'Section lengths are highly imbalanced',
                    'severity': 0.6,
                    'priority': 3,
                    'action': 'Balance content across sections'
                },
                'no_conclusion': {
                    'regex': None,  # Custom check
                    'description': 'Missing conclusion or summary',
                    'severity': 0.5,
                    'priority': 3,
                    'action': 'Add conclusion summarizing key points'
                }
            },
            PatternType.LINGUISTIC: {
                'passive_voice_overuse': {
                    'regex': r'\b(was|were|been|being|is|are|am)\s+\w+ed\b',
                    'description': 'Excessive use of passive voice',
                    'severity': 0.4,
                    'priority': 4,
                    'action': 'Convert to active voice for clarity'
                },
                'complex_sentences': {
                    'regex': r'[^.!?]{150,}[.!?]',
                    'description': 'Overly complex sentences',
                    'severity': 0.6,
                    'priority': 2,
                    'action': 'Break into shorter, clearer sentences'
                },
                'redundant_phrases': {
                    'regex': r'\b(in order to|at this point in time|due to the fact that|in the event that)\b',
                    'description': 'Redundant or wordy phrases',
                    'severity': 0.3,
                    'priority': 5,
                    'action': 'Simplify to concise expressions'
                }
            },
            PatternType.TECHNICAL: {
                'undefined_acronyms': {
                    'regex': r'\b[A-Z]{2,}(?![a-z])\b',
                    'description': 'Undefined acronyms or abbreviations',
                    'severity': 0.7,
                    'priority': 2,
                    'action': 'Define acronyms on first use'
                },
                'missing_code_examples': {
                    'regex': None,  # Custom check
                    'description': 'Technical concepts without code examples',
                    'severity': 0.6,
                    'priority': 2,
                    'action': 'Add illustrative code examples'
                },
                'outdated_references': {
                    'regex': r'\b(deprecated|obsolete|outdated|legacy)\b',
                    'description': 'References to outdated technology',
                    'severity': 0.8,
                    'priority': 1,
                    'action': 'Update to current best practices'
                }
            },
            PatternType.FORMATTING: {
                'inconsistent_headers': {
                    'regex': None,  # Custom check
                    'description': 'Inconsistent header formatting',
                    'severity': 0.4,
                    'priority': 4,
                    'action': 'Standardize header formatting'
                },
                'missing_lists': {
                    'regex': r'(?:First|Second|Third|1\)|2\)|3\))',
                    'description': 'Sequential items not in list format',
                    'severity': 0.3,
                    'priority': 5,
                    'action': 'Convert to proper list formatting'
                },
                'code_without_language': {
                    'regex': r'```\n[^`]',
                    'description': 'Code blocks without language specification',
                    'severity': 0.5,
                    'priority': 3,
                    'action': 'Add language identifiers to code blocks'
                }
            },
            PatternType.SEMANTIC: {
                'vague_language': {
                    'regex': r'\b(some|many|various|certain|several)\b',
                    'description': 'Vague quantifiers without specifics',
                    'severity': 0.4,
                    'priority': 4,
                    'action': 'Replace with specific quantities or examples'
                },
                'missing_context': {
                    'regex': r'\b(this|that|these|those)\b(?!\s+\w+)',
                    'description': 'Unclear references lacking context',
                    'severity': 0.5,
                    'priority': 3,
                    'action': 'Add explicit context to references'
                },
                'assumption_language': {
                    'regex': r'\b(obviously|clearly|simply|just|everyone knows)\b',
                    'description': 'Assumptions about reader knowledge',
                    'severity': 0.6,
                    'priority': 2,
                    'action': 'Remove assumptions, provide context'
                }
            }
        }
    
    def _init_pattern_matchers(self):
        """Initialize compiled regex patterns for efficiency."""
        self.matchers = {}
        
        for pattern_type, patterns in self.pattern_definitions.items():
            self.matchers[pattern_type] = {}
            for pattern_name, pattern_def in patterns.items():
                if pattern_def['regex']:
                    self.matchers[pattern_type][pattern_name] = re.compile(
                        pattern_def['regex'],
                        re.IGNORECASE | re.MULTILINE
                    )
    
    def analyze(self, content: str, metadata: Optional[Dict] = None) -> PatternAnalysis:
        """
        Analyze document for improvement patterns.
        
        Args:
            content: Document content to analyze
            metadata: Optional metadata for context
            
        Returns:
            PatternAnalysis with identified patterns and recommendations
        """
        if not content:
            return PatternAnalysis([], {}, {}, [])
        
        patterns = []
        
        # Analyze each pattern type
        for pattern_type in PatternType:
            type_patterns = self._analyze_pattern_type(content, pattern_type, metadata)
            patterns.extend(type_patterns)
        
        # Generate summary
        summary = self._generate_summary(patterns, content)
        
        # Create improvement map
        improvement_map = self._create_improvement_map(patterns)
        
        # Generate learning insights
        insights = self._generate_insights(patterns, content)
        
        return PatternAnalysis(
            patterns=patterns,
            summary=summary,
            improvement_map=improvement_map,
            learning_insights=insights
        )
    
    def _analyze_pattern_type(self,
                             content: str,
                             pattern_type: PatternType,
                             metadata: Optional[Dict]) -> List[Pattern]:
        """Analyze specific pattern type in content."""
        patterns = []
        pattern_defs = self.pattern_definitions.get(pattern_type, {})
        
        for pattern_name, pattern_def in pattern_defs.items():
            if pattern_def['regex']:
                # Regex-based pattern matching
                matcher = self.matchers[pattern_type].get(pattern_name)
                if matcher:
                    matches = matcher.finditer(content)
                    occurrences = []
                    
                    for match in matches:
                        occurrences.append({
                            'text': match.group(),
                            'start': match.start(),
                            'end': match.end(),
                            'line': content[:match.start()].count('\n') + 1
                        })
                    
                    if occurrences:
                        pattern = Pattern(
                            type=pattern_type,
                            name=pattern_name,
                            description=pattern_def['description'],
                            occurrences=occurrences,
                            severity=pattern_def['severity'],
                            improvement_priority=pattern_def['priority'],
                            suggested_action=pattern_def['action']
                        )
                        patterns.append(pattern)
            else:
                # Custom pattern checks
                pattern = self._check_custom_pattern(
                    content, pattern_type, pattern_name, pattern_def, metadata
                )
                if pattern:
                    patterns.append(pattern)
        
        return patterns
    
    def _check_custom_pattern(self,
                             content: str,
                             pattern_type: PatternType,
                             pattern_name: str,
                             pattern_def: Dict,
                             metadata: Optional[Dict]) -> Optional[Pattern]:
        """Check for custom patterns requiring special logic."""
        occurrences = []
        
        if pattern_name == 'missing_introduction':
            # Check if document has proper introduction
            lower_content = content.lower()
            has_intro = any(marker in lower_content[:500] for marker in 
                          ['introduction', 'overview', 'getting started', 'about'])
            
            if not has_intro:
                occurrences.append({
                    'text': 'Missing introduction section',
                    'start': 0,
                    'end': 0,
                    'line': 1
                })
        
        elif pattern_name == 'unbalanced_sections':
            # Check section balance
            sections = re.split(r'^#{1,3}\s+', content, flags=re.MULTILINE)
            if len(sections) > 2:
                section_lengths = [len(s) for s in sections[1:]]  # Skip content before first header
                if section_lengths:
                    avg_length = np.mean(section_lengths)
                    std_length = np.std(section_lengths)
                    
                    # High standard deviation indicates imbalance
                    if std_length > avg_length * 0.7:
                        occurrences.append({
                            'text': f'Section imbalance detected (std: {std_length:.0f}, avg: {avg_length:.0f})',
                            'start': 0,
                            'end': 0,
                            'line': 1
                        })
        
        elif pattern_name == 'no_conclusion':
            # Check for conclusion/summary
            lower_content = content.lower()
            last_section = lower_content[-1000:] if len(lower_content) > 1000 else lower_content
            
            has_conclusion = any(marker in last_section for marker in 
                               ['conclusion', 'summary', 'recap', 'final thoughts'])
            
            if not has_conclusion:
                occurrences.append({
                    'text': 'Missing conclusion or summary',
                    'start': len(content) - 1,
                    'end': len(content),
                    'line': content.count('\n')
                })
        
        elif pattern_name == 'missing_code_examples':
            # Check if technical document lacks code examples
            is_technical = any(term in content.lower() for term in 
                             ['function', 'method', 'class', 'api', 'code', 'implementation'])
            
            has_code = '```' in content
            
            if is_technical and not has_code:
                occurrences.append({
                    'text': 'Technical documentation without code examples',
                    'start': 0,
                    'end': 0,
                    'line': 1
                })
        
        elif pattern_name == 'inconsistent_headers':
            # Check header consistency
            headers = re.findall(r'^(#{1,6})\s+(.+)$', content, re.MULTILINE)
            if headers:
                # Check for consistent capitalization
                capitalizations = []
                for level, text in headers:
                    if text[0].isupper():
                        # Count title case vs sentence case
                        title_case = sum(1 for word in text.split() if word[0].isupper())
                        capitalizations.append(title_case / len(text.split()))
                
                if capitalizations and np.std(capitalizations) > 0.3:
                    occurrences.append({
                        'text': 'Inconsistent header capitalization',
                        'start': 0,
                        'end': 0,
                        'line': 1
                    })
        
        if occurrences:
            return Pattern(
                type=pattern_type,
                name=pattern_name,
                description=pattern_def['description'],
                occurrences=occurrences,
                severity=pattern_def['severity'],
                improvement_priority=pattern_def['priority'],
                suggested_action=pattern_def['action']
            )
        
        return None
    
    def _generate_summary(self, patterns: List[Pattern], content: str) -> Dict[str, Any]:
        """Generate summary of pattern analysis."""
        if not patterns:
            return {
                'total_patterns': 0,
                'high_priority': 0,
                'by_type': {},
                'overall_severity': 0.0
            }
        
        type_counts = defaultdict(int)
        total_severity = 0.0
        
        for pattern in patterns:
            type_counts[pattern.type.value] += 1
            total_severity += pattern.severity
        
        high_priority = len([p for p in patterns if p.improvement_priority <= 2])
        
        return {
            'total_patterns': len(patterns),
            'high_priority': high_priority,
            'by_type': dict(type_counts),
            'overall_severity': total_severity / len(patterns) if patterns else 0.0,
            'document_length': len(content),
            'pattern_density': len(patterns) / (len(content) / 1000) if content else 0.0
        }
    
    def _create_improvement_map(self, patterns: List[Pattern]) -> Dict[str, List[str]]:
        """Create map of improvements organized by priority."""
        improvement_map = defaultdict(list)
        
        for pattern in sorted(patterns, key=lambda p: p.improvement_priority):
            priority_key = f"priority_{pattern.improvement_priority}"
            improvement = {
                'pattern': pattern.name,
                'action': pattern.suggested_action,
                'severity': pattern.severity,
                'occurrences': len(pattern.occurrences)
            }
            improvement_map[priority_key].append(improvement)
        
        return dict(improvement_map)
    
    def _generate_insights(self, patterns: List[Pattern], content: str) -> List[str]:
        """Generate learning insights from pattern analysis."""
        insights = []
        
        if not patterns:
            insights.append("Document shows good quality with minimal improvement patterns")
            return insights
        
        # Analyze pattern distribution
        type_counts = defaultdict(int)
        for pattern in patterns:
            type_counts[pattern.type] += 1
        
        dominant_type = max(type_counts, key=type_counts.get) if type_counts else None
        
        if dominant_type:
            insights.append(f"Primary improvement area: {dominant_type.value} patterns")
        
        # Check severity distribution
        high_severity = [p for p in patterns if p.severity >= 0.7]
        if high_severity:
            insights.append(f"Found {len(high_severity)} high-severity issues requiring immediate attention")
        
        # Analyze pattern clustering
        if len(patterns) > 5:
            # Check if patterns are concentrated in specific areas
            line_numbers = []
            for pattern in patterns:
                for occurrence in pattern.occurrences:
                    line_numbers.append(occurrence.get('line', 0))
            
            if line_numbers:
                line_array = np.array(line_numbers)
                if np.std(line_array) < np.mean(line_array) * 0.5:
                    insights.append("Patterns are concentrated in specific document sections")
                else:
                    insights.append("Patterns are distributed throughout the document")
        
        # Learning from improvements (if enabled)
        if self.learning_enabled and self.learned_patterns:
            common_patterns = self._identify_common_patterns()
            if common_patterns:
                insights.append(f"Recurring pattern detected: {common_patterns[0]}")
        
        return insights
    
    def _identify_common_patterns(self) -> List[str]:
        """Identify commonly occurring patterns from learning history."""
        if not self.learned_patterns:
            return []
        
        pattern_counts = Counter()
        for patterns in self.learned_patterns.values():
            for pattern in patterns:
                pattern_counts[pattern] += 1
        
        # Return most common patterns
        return [pattern for pattern, count in pattern_counts.most_common(3)]
    
    def learn_from_improvement(self,
                              original_content: str,
                              improved_content: str,
                              patterns_addressed: List[Pattern]):
        """
        Learn from successful improvements for future pattern recognition.
        
        Args:
            original_content: Original document content
            improved_content: Improved document content
            patterns_addressed: Patterns that were successfully addressed
        """
        if not self.learning_enabled or not self.learned_patterns:
            return
        
        # Extract improvement transformations
        for pattern in patterns_addressed:
            transformation = {
                'pattern_type': pattern.type.value,
                'pattern_name': pattern.name,
                'severity': pattern.severity,
                'success': True
            }
            
            # Store learning
            key = f"{pattern.type.value}_{pattern.name}"
            self.learned_patterns[key].append(transformation)
            
            # Limit history size
            if len(self.learned_patterns[key]) > 100:
                self.learned_patterns[key] = self.learned_patterns[key][-100:]
    
    def get_pattern_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about recognized patterns.
        
        Returns:
            Dictionary with pattern recognition statistics
        """
        stats = {
            'total_pattern_types': len(self.pattern_definitions),
            'patterns_by_type': {}
        }
        
        for pattern_type, patterns in self.pattern_definitions.items():
            stats['patterns_by_type'][pattern_type.value] = {
                'count': len(patterns),
                'patterns': list(patterns.keys())
            }
        
        if self.learning_enabled and self.learned_patterns:
            stats['learned_patterns'] = len(self.learned_patterns)
            stats['total_learning_samples'] = sum(
                len(patterns) for patterns in self.learned_patterns.values()
            )
        
        return stats