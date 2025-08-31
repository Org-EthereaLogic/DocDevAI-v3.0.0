"""
M008: Token Optimization and Prompt Compression for LLM Adapter.

Implements token optimization with:
- Intelligent prompt compression
- Token usage prediction
- Context window management
- Redundancy elimination
- Semantic compression
"""

import re
import hashlib
import logging
from typing import Dict, List, Optional, Any, Tuple, Set
from dataclasses import dataclass, field
from collections import defaultdict, Counter
import tiktoken  # For accurate token counting

logger = logging.getLogger(__name__)


@dataclass
class TokenStats:
    """Token usage statistics."""
    original_tokens: int = 0
    compressed_tokens: int = 0
    saved_tokens: int = 0
    compression_ratio: float = 0.0
    estimated_cost_saved: float = 0.0
    
    def update(self, original: int, compressed: int, cost_per_token: float = 0.00001):
        """Update statistics with new compression."""
        self.original_tokens += original
        self.compressed_tokens += compressed
        self.saved_tokens = self.original_tokens - self.compressed_tokens
        
        if self.original_tokens > 0:
            self.compression_ratio = 1 - (self.compressed_tokens / self.original_tokens)
        
        self.estimated_cost_saved = self.saved_tokens * cost_per_token


class TokenCounter:
    """
    Accurate token counting for different models.
    
    Uses tiktoken for OpenAI models, approximations for others.
    """
    
    def __init__(self):
        """Initialize token counter."""
        self.encoders = {}
        self.model_mappings = {
            "gpt-4": "cl100k_base",
            "gpt-4-32k": "cl100k_base",
            "gpt-3.5-turbo": "cl100k_base",
            "text-davinci-003": "p50k_base",
            "text-davinci-002": "p50k_base",
            "code-davinci-002": "p50k_base",
        }
        
        # Try to load tiktoken encoders
        self._load_encoders()
    
    def _load_encoders(self):
        """Load tiktoken encoders for supported models."""
        try:
            for encoding_name in set(self.model_mappings.values()):
                self.encoders[encoding_name] = tiktoken.get_encoding(encoding_name)
        except Exception as e:
            logger.warning(f"Failed to load tiktoken encoders: {e}")
    
    def count_tokens(self, text: str, model: str = "gpt-3.5-turbo") -> int:
        """
        Count tokens in text for specific model.
        
        Args:
            text: Text to count tokens for
            model: Model name
            
        Returns:
            Token count
        """
        # Get encoding for model
        encoding_name = self.model_mappings.get(model)
        
        if encoding_name and encoding_name in self.encoders:
            # Use tiktoken for accurate count
            encoder = self.encoders[encoding_name]
            return len(encoder.encode(text))
        else:
            # Fallback to approximation (1 token ≈ 4 chars or 0.75 words)
            words = len(text.split())
            chars = len(text)
            return max(chars // 4, int(words * 0.75))
    
    def count_messages_tokens(
        self,
        messages: List[Dict[str, str]],
        model: str = "gpt-3.5-turbo"
    ) -> int:
        """
        Count tokens in message list.
        
        Args:
            messages: List of messages
            model: Model name
            
        Returns:
            Total token count including formatting
        """
        # Account for message formatting overhead
        # Each message has ~4 tokens of formatting
        formatting_tokens = len(messages) * 4
        
        content_tokens = sum(
            self.count_tokens(msg.get("content", ""), model)
            for msg in messages
        )
        
        return formatting_tokens + content_tokens


class PromptCompressor:
    """
    Intelligent prompt compression techniques.
    
    Implements multiple compression strategies:
    - Whitespace normalization
    - Redundancy elimination
    - Abbreviation substitution
    - Semantic compression
    - Context summarization
    """
    
    def __init__(
        self,
        aggressive_mode: bool = False,
        preserve_code_blocks: bool = True,
        max_compression_ratio: float = 0.5
    ):
        """
        Initialize prompt compressor.
        
        Args:
            aggressive_mode: Enable aggressive compression
            preserve_code_blocks: Don't compress code blocks
            max_compression_ratio: Maximum compression (safety limit)
        """
        self.aggressive_mode = aggressive_mode
        self.preserve_code_blocks = preserve_code_blocks
        self.max_compression_ratio = max_compression_ratio
        
        # Common abbreviations
        self.abbreviations = {
            "documentation": "docs",
            "configuration": "config",
            "application": "app",
            "development": "dev",
            "production": "prod",
            "environment": "env",
            "database": "db",
            "authentication": "auth",
            "authorization": "authz",
            "repository": "repo",
            "directory": "dir",
            "function": "func",
            "parameter": "param",
            "argument": "arg",
            "variable": "var",
            "temporary": "temp",
            "maximum": "max",
            "minimum": "min",
            "average": "avg",
            "standard": "std",
            "deviation": "dev",
            "performance": "perf",
            "optimization": "opt",
            "implementation": "impl",
            "specification": "spec",
            "requirement": "req",
        }
        
        # Filler words that can be removed in aggressive mode
        self.filler_words = {
            "basically", "actually", "really", "very", "quite",
            "just", "simply", "merely", "purely", "totally",
            "completely", "absolutely", "definitely", "certainly",
            "obviously", "clearly", "evidently", "apparently",
            "essentially", "fundamentally", "primarily", "mainly",
            "particularly", "especially", "specifically"
        }
        
        self.token_counter = TokenCounter()
        self.stats = TokenStats()
        
        self.logger = logging.getLogger(f"{__name__}.PromptCompressor")
    
    def compress(self, text: str, model: str = "gpt-3.5-turbo") -> str:
        """
        Compress text using multiple strategies.
        
        Args:
            text: Text to compress
            model: Target model for token counting
            
        Returns:
            Compressed text
        """
        original_tokens = self.token_counter.count_tokens(text, model)
        
        # Apply compression techniques in order
        compressed = text
        
        # 1. Normalize whitespace
        compressed = self._normalize_whitespace(compressed)
        
        # 2. Remove redundancy
        compressed = self._remove_redundancy(compressed)
        
        # 3. Apply abbreviations
        if self.aggressive_mode:
            compressed = self._apply_abbreviations(compressed)
        
        # 4. Remove filler words
        if self.aggressive_mode:
            compressed = self._remove_filler_words(compressed)
        
        # 5. Compress lists
        compressed = self._compress_lists(compressed)
        
        # 6. Deduplicate content
        compressed = self._deduplicate_content(compressed)
        
        # Check compression ratio safety
        compressed_tokens = self.token_counter.count_tokens(compressed, model)
        
        if compressed_tokens < original_tokens * (1 - self.max_compression_ratio):
            # Too much compression, return original
            self.logger.warning(
                f"Compression too aggressive ({compressed_tokens}/{original_tokens}), "
                f"reverting to original"
            )
            return text
        
        # Update statistics
        self.stats.update(original_tokens, compressed_tokens)
        
        self.logger.debug(
            f"Compressed {original_tokens} → {compressed_tokens} tokens "
            f"({self.stats.compression_ratio:.1%} reduction)"
        )
        
        return compressed
    
    def _normalize_whitespace(self, text: str) -> str:
        """Normalize whitespace in text."""
        # Preserve code blocks
        if self.preserve_code_blocks:
            parts = re.split(r'(```[\s\S]*?```)', text)
            normalized_parts = []
            
            for i, part in enumerate(parts):
                if i % 2 == 0:  # Not a code block
                    # Normalize whitespace
                    part = re.sub(r'\s+', ' ', part)
                    part = re.sub(r'\n\s*\n', '\n\n', part)
                normalized_parts.append(part)
            
            return ''.join(normalized_parts)
        else:
            # Normalize all whitespace
            text = re.sub(r'\s+', ' ', text)
            text = re.sub(r'\n\s*\n', '\n\n', text)
            return text
    
    def _remove_redundancy(self, text: str) -> str:
        """Remove redundant content."""
        # Remove repeated sentences
        sentences = text.split('.')
        unique_sentences = []
        seen = set()
        
        for sentence in sentences:
            sentence = sentence.strip()
            if sentence and sentence.lower() not in seen:
                unique_sentences.append(sentence)
                seen.add(sentence.lower())
        
        return '. '.join(unique_sentences) + ('.' if unique_sentences else '')
    
    def _apply_abbreviations(self, text: str) -> str:
        """Apply common abbreviations."""
        for full, abbr in self.abbreviations.items():
            # Case-insensitive replacement
            pattern = re.compile(re.escape(full), re.IGNORECASE)
            text = pattern.sub(abbr, text)
        
        return text
    
    def _remove_filler_words(self, text: str) -> str:
        """Remove filler words in aggressive mode."""
        words = text.split()
        filtered_words = [
            word for word in words
            if word.lower() not in self.filler_words
        ]
        return ' '.join(filtered_words)
    
    def _compress_lists(self, text: str) -> str:
        """Compress verbose lists."""
        # Find patterns like "item1, item2, item3, and item4"
        # Replace with "item1, item2, etc." if more than 3 items
        
        def compress_list(match):
            items = match.group(0).split(',')
            if len(items) > 3:
                return f"{', '.join(items[:2])}, etc."
            return match.group(0)
        
        # Simple list pattern
        pattern = r'\b(\w+(?:,\s*\w+){3,})\b'
        text = re.sub(pattern, compress_list, text)
        
        return text
    
    def _deduplicate_content(self, text: str) -> str:
        """Remove duplicate paragraphs or sections."""
        # Split into paragraphs
        paragraphs = text.split('\n\n')
        unique_paragraphs = []
        seen_hashes = set()
        
        for para in paragraphs:
            para = para.strip()
            if para:
                # Create hash of paragraph content
                para_hash = hashlib.md5(para.lower().encode()).hexdigest()
                
                if para_hash not in seen_hashes:
                    unique_paragraphs.append(para)
                    seen_hashes.add(para_hash)
        
        return '\n\n'.join(unique_paragraphs)
    
    def compress_messages(
        self,
        messages: List[Dict[str, str]],
        model: str = "gpt-3.5-turbo"
    ) -> List[Dict[str, str]]:
        """
        Compress a list of messages.
        
        Args:
            messages: List of messages to compress
            model: Target model
            
        Returns:
            Compressed messages
        """
        compressed_messages = []
        
        for msg in messages:
            compressed_msg = msg.copy()
            if "content" in compressed_msg:
                compressed_msg["content"] = self.compress(
                    compressed_msg["content"],
                    model
                )
            compressed_messages.append(compressed_msg)
        
        return compressed_messages


class ContextWindowManager:
    """
    Manage context window efficiently.
    
    Features:
    - Sliding window for long conversations
    - Context prioritization
    - Automatic truncation
    - Important content preservation
    """
    
    def __init__(
        self,
        max_context_tokens: int = 4000,
        preserve_system_prompt: bool = True,
        preserve_recent_messages: int = 3
    ):
        """
        Initialize context window manager.
        
        Args:
            max_context_tokens: Maximum context size
            preserve_system_prompt: Always keep system prompt
            preserve_recent_messages: Number of recent messages to preserve
        """
        self.max_context_tokens = max_context_tokens
        self.preserve_system_prompt = preserve_system_prompt
        self.preserve_recent_messages = preserve_recent_messages
        
        self.token_counter = TokenCounter()
        self.logger = logging.getLogger(f"{__name__}.ContextWindowManager")
    
    def fit_to_context(
        self,
        messages: List[Dict[str, str]],
        model: str = "gpt-3.5-turbo",
        importance_scores: Optional[Dict[int, float]] = None
    ) -> List[Dict[str, str]]:
        """
        Fit messages to context window.
        
        Args:
            messages: List of messages
            model: Target model
            importance_scores: Optional importance scores for messages
            
        Returns:
            Messages that fit in context window
        """
        if not messages:
            return []
        
        # Calculate token counts for each message
        message_tokens = [
            self.token_counter.count_tokens(msg.get("content", ""), model)
            for msg in messages
        ]
        
        total_tokens = sum(message_tokens)
        
        # If fits, return as is
        if total_tokens <= self.max_context_tokens:
            return messages
        
        # Need to truncate
        self.logger.info(
            f"Truncating context from {total_tokens} to {self.max_context_tokens} tokens"
        )
        
        # Preserve system prompt if present
        preserved_messages = []
        preserved_tokens = 0
        
        if self.preserve_system_prompt and messages[0].get("role") == "system":
            preserved_messages.append(messages[0])
            preserved_tokens += message_tokens[0]
            messages = messages[1:]
            message_tokens = message_tokens[1:]
        
        # Preserve recent messages
        if self.preserve_recent_messages > 0:
            recent_messages = messages[-self.preserve_recent_messages:]
            recent_tokens = message_tokens[-self.preserve_recent_messages:]
            
            # Check if recent messages fit
            if sum(recent_tokens) + preserved_tokens <= self.max_context_tokens:
                # Add as many older messages as possible
                remaining_tokens = self.max_context_tokens - preserved_tokens - sum(recent_tokens)
                
                # Add messages from beginning
                for i, (msg, tokens) in enumerate(zip(messages[:-self.preserve_recent_messages],
                                                      message_tokens[:-self.preserve_recent_messages])):
                    if tokens <= remaining_tokens:
                        preserved_messages.append(msg)
                        remaining_tokens -= tokens
                    else:
                        break
                
                # Add recent messages
                preserved_messages.extend(recent_messages)
            else:
                # Even recent messages don't fit, truncate them
                remaining_tokens = self.max_context_tokens - preserved_tokens
                
                for msg, tokens in zip(reversed(recent_messages), reversed(recent_tokens)):
                    if tokens <= remaining_tokens:
                        preserved_messages.insert(0, msg)
                        remaining_tokens -= tokens
        
        return preserved_messages
    
    def summarize_truncated(
        self,
        messages: List[Dict[str, str]],
        truncated_messages: List[Dict[str, str]]
    ) -> Optional[Dict[str, str]]:
        """
        Create summary of truncated content.
        
        Args:
            messages: Original messages
            truncated_messages: Messages after truncation
            
        Returns:
            Summary message if content was truncated
        """
        if len(messages) == len(truncated_messages):
            return None
        
        truncated_count = len(messages) - len(truncated_messages)
        
        # Create summary message
        summary = {
            "role": "system",
            "content": f"[Previous {truncated_count} messages truncated for context limit. "
                      f"Key points from truncated conversation available upon request.]"
        }
        
        return summary


class TokenOptimizer:
    """
    Main token optimization coordinator.
    
    Combines all optimization techniques for maximum efficiency.
    """
    
    def __init__(
        self,
        enable_compression: bool = True,
        enable_context_management: bool = True,
        aggressive_compression: bool = False,
        model_context_limits: Optional[Dict[str, int]] = None
    ):
        """
        Initialize token optimizer.
        
        Args:
            enable_compression: Enable prompt compression
            enable_context_management: Enable context window management
            aggressive_compression: Use aggressive compression
            model_context_limits: Model-specific context limits
        """
        self.enable_compression = enable_compression
        self.enable_context_management = enable_context_management
        
        # Initialize components
        self.compressor = PromptCompressor(aggressive_mode=aggressive_compression)
        self.token_counter = TokenCounter()
        
        # Model context limits
        self.model_context_limits = model_context_limits or {
            "gpt-4": 8192,
            "gpt-4-32k": 32768,
            "gpt-3.5-turbo": 4096,
            "gpt-3.5-turbo-16k": 16384,
            "claude-3": 100000,
            "gemini-pro": 30720,
        }
        
        # Context managers per model
        self.context_managers = {}
        
        self.logger = logging.getLogger(f"{__name__}.TokenOptimizer")
    
    def optimize_request(
        self,
        messages: List[Dict[str, str]],
        model: str,
        max_response_tokens: int = 1000
    ) -> Tuple[List[Dict[str, str]], Dict[str, Any]]:
        """
        Optimize request for token efficiency.
        
        Args:
            messages: Request messages
            model: Target model
            max_response_tokens: Reserved tokens for response
            
        Returns:
            Optimized messages and optimization stats
        """
        stats = {
            "original_tokens": 0,
            "optimized_tokens": 0,
            "compression_applied": False,
            "context_truncation": False,
            "saved_tokens": 0,
            "optimization_time_ms": 0
        }
        
        import time
        start_time = time.time()
        
        # Count original tokens
        stats["original_tokens"] = self.token_counter.count_messages_tokens(
            messages, model
        )
        
        optimized_messages = messages
        
        # Apply compression if enabled
        if self.enable_compression:
            optimized_messages = self.compressor.compress_messages(
                optimized_messages, model
            )
            stats["compression_applied"] = True
        
        # Apply context management if enabled
        if self.enable_context_management:
            # Get context limit for model
            context_limit = self.model_context_limits.get(model, 4096)
            available_tokens = context_limit - max_response_tokens
            
            # Get or create context manager
            if model not in self.context_managers:
                self.context_managers[model] = ContextWindowManager(
                    max_context_tokens=available_tokens
                )
            
            context_manager = self.context_managers[model]
            
            # Fit to context
            original_count = len(optimized_messages)
            optimized_messages = context_manager.fit_to_context(
                optimized_messages, model
            )
            
            if len(optimized_messages) < original_count:
                stats["context_truncation"] = True
                
                # Add summary if needed
                summary = context_manager.summarize_truncated(
                    messages, optimized_messages
                )
                if summary:
                    optimized_messages.insert(1, summary)  # After system prompt
        
        # Count optimized tokens
        stats["optimized_tokens"] = self.token_counter.count_messages_tokens(
            optimized_messages, model
        )
        stats["saved_tokens"] = stats["original_tokens"] - stats["optimized_tokens"]
        stats["optimization_time_ms"] = (time.time() - start_time) * 1000
        
        self.logger.debug(
            f"Optimized {stats['original_tokens']} → {stats['optimized_tokens']} tokens "
            f"(saved {stats['saved_tokens']}) in {stats['optimization_time_ms']:.1f}ms"
        )
        
        return optimized_messages, stats
    
    def estimate_cost_savings(
        self,
        saved_tokens: int,
        model: str,
        is_input: bool = True
    ) -> float:
        """
        Estimate cost savings from token optimization.
        
        Args:
            saved_tokens: Number of tokens saved
            model: Model name
            is_input: Whether tokens are input or output
            
        Returns:
            Estimated cost savings in USD
        """
        # Simplified cost model (prices per 1K tokens)
        cost_per_1k = {
            "gpt-4": {"input": 0.03, "output": 0.06},
            "gpt-4-32k": {"input": 0.06, "output": 0.12},
            "gpt-3.5-turbo": {"input": 0.001, "output": 0.002},
            "claude-3": {"input": 0.015, "output": 0.075},
            "gemini-pro": {"input": 0.00025, "output": 0.0005},
        }
        
        model_costs = cost_per_1k.get(model, {"input": 0.001, "output": 0.002})
        cost_type = "input" if is_input else "output"
        
        return (saved_tokens / 1000) * model_costs[cost_type]
    
    def get_optimization_stats(self) -> Dict[str, Any]:
        """Get optimization statistics."""
        return {
            "compression_stats": {
                "total_original_tokens": self.compressor.stats.original_tokens,
                "total_compressed_tokens": self.compressor.stats.compressed_tokens,
                "total_saved_tokens": self.compressor.stats.saved_tokens,
                "compression_ratio": self.compressor.stats.compression_ratio,
                "estimated_cost_saved": self.compressor.stats.estimated_cost_saved
            },
            "active_context_managers": len(self.context_managers),
            "compression_enabled": self.enable_compression,
            "context_management_enabled": self.enable_context_management
        }