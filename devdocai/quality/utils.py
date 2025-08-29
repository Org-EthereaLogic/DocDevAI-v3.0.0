"""
Utility functions for M005 Quality Engine.

Consolidates common functionality used across analyzers.
"""

import re
import hashlib
from typing import List, Dict, Any, Optional, Tuple
from functools import lru_cache


@lru_cache(maxsize=1000)
def calculate_readability(text: str) -> float:
    """
    Calculate Flesch Reading Ease score.
    
    Score interpretation:
    - 90-100: Very easy
    - 80-90: Easy
    - 70-80: Fairly easy
    - 60-70: Standard
    - 50-60: Fairly difficult
    - 30-50: Difficult
    - 0-30: Very difficult
    
    Args:
        text: Text to analyze
        
    Returns:
        Flesch Reading Ease score
    """
    sentences = count_sentences(text)
    words = count_words(text)
    syllables = count_syllables_in_text(text)
    
    if sentences == 0 or words == 0:
        return 0.0
        
    avg_sentence_length = words / sentences
    avg_syllables_per_word = syllables / words
    
    # Flesch Reading Ease formula
    score = 206.835 - 1.015 * avg_sentence_length - 84.6 * avg_syllables_per_word
    
    # Clamp to 0-100 range
    return max(0, min(100, score))


def count_sentences(text: str) -> int:
    """Count sentences in text."""
    # Simple sentence detection
    sentences = re.split(r'[.!?]+', text)
    return len([s for s in sentences if s.strip()])


def count_words(text: str) -> int:
    """Count words in text."""
    words = re.findall(r'\b\w+\b', text)
    return len(words)


def count_syllables_in_text(text: str) -> int:
    """Count total syllables in text."""
    words = re.findall(r'\b\w+\b', text)
    return sum(count_syllables(word) for word in words)


@lru_cache(maxsize=10000)
def count_syllables(word: str) -> int:
    """
    Count syllables in a single word (approximation).
    
    Args:
        word: Word to analyze
        
    Returns:
        Estimated syllable count
    """
    word = word.lower()
    
    # Special cases
    if len(word) <= 3:
        return 1
        
    # Count vowel groups
    vowels = 'aeiouy'
    syllables = 0
    previous_was_vowel = False
    
    for char in word:
        is_vowel = char in vowels
        if is_vowel and not previous_was_vowel:
            syllables += 1
        previous_was_vowel = is_vowel
        
    # Adjust for silent e
    if word.endswith('e') and syllables > 1:
        syllables -= 1
        
    # Adjust for common endings
    if word.endswith(('le', 'les')) and syllables > 1:
        syllables += 1
        
    return max(1, syllables)


def extract_code_blocks(content: str) -> List[Dict[str, str]]:
    """
    Extract code blocks from markdown content.
    
    Args:
        content: Markdown content
        
    Returns:
        List of code blocks with language and content
    """
    pattern = r'```(\w*)\n([\s\S]*?)```'
    matches = re.findall(pattern, content)
    
    blocks = []
    for language, code in matches:
        blocks.append({
            'language': language or 'plaintext',
            'content': code.strip()
        })
        
    return blocks


def extract_sections(content: str) -> List[Dict[str, Any]]:
    """
    Extract sections from markdown content.
    
    Args:
        content: Markdown content
        
    Returns:
        List of sections with metadata
    """
    lines = content.split('\n')
    sections = []
    current_section = None
    
    for i, line in enumerate(lines):
        if line.startswith('#'):
            # Save previous section
            if current_section:
                current_section['end_line'] = i - 1
                current_section['content'] = '\n'.join(
                    lines[current_section['start_line']:current_section['end_line']+1]
                )
                sections.append(current_section)
                
            # Start new section
            level = len(line.split()[0])
            title = line[level:].strip()
            
            current_section = {
                'level': level,
                'title': title,
                'start_line': i,
                'end_line': None,
                'content': ''
            }
            
    # Save last section
    if current_section:
        current_section['end_line'] = len(lines) - 1
        current_section['content'] = '\n'.join(
            lines[current_section['start_line']:current_section['end_line']+1]
        )
        sections.append(current_section)
        
    return sections


def find_urls(content: str) -> List[str]:
    """
    Find all URLs in content.
    
    Args:
        content: Text content
        
    Returns:
        List of URLs
    """
    # Match common URL patterns
    url_pattern = r'https?://[^\s<>"{}|\\^`\[\]]+'
    urls = re.findall(url_pattern, content)
    
    # Also find markdown links
    md_link_pattern = r'\[([^\]]+)\]\(([^)]+)\)'
    md_links = re.findall(md_link_pattern, content)
    urls.extend([url for _, url in md_links if url.startswith('http')])
    
    return list(set(urls))


def find_images(content: str) -> List[Tuple[str, str]]:
    """
    Find all images in markdown content.
    
    Args:
        content: Markdown content
        
    Returns:
        List of (alt_text, url) tuples
    """
    pattern = r'!\[([^\]]*)\]\(([^)]+)\)'
    return re.findall(pattern, content)


def calculate_hash(content: str) -> str:
    """
    Calculate hash of content for caching.
    
    Args:
        content: Content to hash
        
    Returns:
        MD5 hash hex digest
    """
    return hashlib.md5(content.encode('utf-8')).hexdigest()


def sanitize_regex(pattern: str, max_complexity: int = 100) -> Optional[str]:
    """
    Sanitize regex pattern to prevent ReDoS attacks.
    
    Args:
        pattern: Regex pattern to sanitize
        max_complexity: Maximum allowed complexity
        
    Returns:
        Sanitized pattern or None if too complex
    """
    # Check for dangerous patterns
    dangerous = [
        r'(\w+)*',  # Exponential backtracking
        r'(\d+)+',  # Nested quantifiers
        r'(.*)*',   # Catastrophic backtracking
        r'(.+)+',   # Nested quantifiers with greedy matching
    ]
    
    for danger in dangerous:
        if danger in pattern:
            return None
            
    # Check complexity (simplified)
    complexity = 0
    complexity += pattern.count('*') * 10
    complexity += pattern.count('+') * 10
    complexity += pattern.count('{') * 15
    complexity += pattern.count('|') * 5
    complexity += pattern.count('(') * 5
    
    if complexity > max_complexity:
        return None
        
    return pattern


def truncate_text(text: str, max_length: int = 100, suffix: str = '...') -> str:
    """
    Truncate text to maximum length.
    
    Args:
        text: Text to truncate
        max_length: Maximum length
        suffix: Suffix to add if truncated
        
    Returns:
        Truncated text
    """
    if len(text) <= max_length:
        return text
        
    return text[:max_length - len(suffix)] + suffix


def normalize_whitespace(text: str) -> str:
    """
    Normalize whitespace in text.
    
    Args:
        text: Text to normalize
        
    Returns:
        Text with normalized whitespace
    """
    # Replace multiple spaces with single space
    text = re.sub(r' +', ' ', text)
    
    # Replace multiple newlines with double newline
    text = re.sub(r'\n{3,}', '\n\n', text)
    
    # Remove trailing whitespace
    lines = text.split('\n')
    lines = [line.rstrip() for line in lines]
    
    return '\n'.join(lines)


def detect_language(code: str) -> str:
    """
    Detect programming language from code snippet.
    
    Args:
        code: Code snippet
        
    Returns:
        Detected language or 'unknown'
    """
    # Simple heuristic-based detection
    patterns = {
        'python': [r'def\s+\w+\(', r'import\s+\w+', r'if\s+__name__'],
        'javascript': [r'function\s+\w+\(', r'const\s+\w+', r'=>', r'console\.log'],
        'typescript': [r'interface\s+\w+', r'type\s+\w+', r':\s*string'],
        'java': [r'public\s+class', r'private\s+\w+', r'public\s+static\s+void'],
        'c++': [r'#include\s*<', r'using\s+namespace', r'cout\s*<<'],
        'rust': [r'fn\s+\w+\(', r'let\s+mut', r'impl\s+\w+'],
        'go': [r'func\s+\w+\(', r'package\s+\w+', r'fmt\.Println'],
    }
    
    for language, lang_patterns in patterns.items():
        for pattern in lang_patterns:
            if re.search(pattern, code):
                return language
                
    return 'unknown'


def calculate_complexity(code: str) -> int:
    """
    Calculate cyclomatic complexity (simplified).
    
    Args:
        code: Code to analyze
        
    Returns:
        Complexity score
    """
    complexity = 1  # Base complexity
    
    # Count decision points
    decision_keywords = [
        r'\bif\b', r'\belif\b', r'\belse\b', r'\bfor\b', r'\bwhile\b',
        r'\btry\b', r'\bcatch\b', r'\bexcept\b', r'\bswitch\b', r'\bcase\b'
    ]
    
    for keyword in decision_keywords:
        complexity += len(re.findall(keyword, code))
        
    # Count logical operators
    logical_operators = [r'&&', r'\|\|', r'\band\b', r'\bor\b']
    for operator in logical_operators:
        complexity += len(re.findall(operator, code))
        
    return complexity


def chunk_text(text: str, chunk_size: int = 1000, overlap: int = 100) -> List[str]:
    """
    Split text into chunks with overlap.
    
    Args:
        text: Text to chunk
        chunk_size: Size of each chunk
        overlap: Overlap between chunks
        
    Returns:
        List of text chunks
    """
    if len(text) <= chunk_size:
        return [text]
        
    chunks = []
    start = 0
    
    while start < len(text):
        end = min(start + chunk_size, len(text))
        
        # Try to break at sentence boundary
        if end < len(text):
            # Look for sentence end
            last_period = text.rfind('.', start, end)
            if last_period > start + chunk_size // 2:
                end = last_period + 1
                
        chunks.append(text[start:end])
        start = end - overlap if end < len(text) else end
        
    return chunks


def merge_issues(issues_list: List[List[Any]]) -> List[Any]:
    """
    Merge and deduplicate issues from multiple sources.
    
    Args:
        issues_list: List of issue lists
        
    Returns:
        Merged and deduplicated issues
    """
    seen = set()
    merged = []
    
    for issues in issues_list:
        for issue in issues:
            # Create unique key for issue
            key = (issue.dimension, issue.severity, issue.message)
            
            if key not in seen:
                seen.add(key)
                merged.append(issue)
                
    return merged


# Export common patterns for reuse
COMMON_PATTERNS = {
    'email': r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
    'url': r'https?://[^\s<>"{}|\\^`\[\]]+',
    'ip_address': r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b',
    'phone': r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b',
    'date': r'\b\d{1,2}[-/]\d{1,2}[-/]\d{2,4}\b',
    'time': r'\b\d{1,2}:\d{2}(?::\d{2})?\s*(?:AM|PM|am|pm)?\b',
    'version': r'v?\d+\.\d+(?:\.\d+)?',
    'hex_color': r'#[0-9A-Fa-f]{6}\b',
    'uuid': r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}',
}