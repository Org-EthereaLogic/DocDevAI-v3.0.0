"""
Memory Detection Utilities - DevDocAI v3.0.0
Pass 4: Simplified memory detection
"""

from typing import Literal

import psutil

MemoryMode = Literal["baseline", "standard", "enhanced", "performance"]


class MemoryDetector:
    """System memory detection and mode configuration."""

    THRESHOLDS = {"baseline": 2, "standard": 4, "enhanced": 8}
    WORKER_CONFIG = {"baseline": 1, "standard": 2, "enhanced": 4, "performance": 8}
    CACHE_CONFIG = {
        "baseline": "50MB",
        "standard": "100MB",
        "enhanced": "250MB",
        "performance": "500MB",
    }

    @classmethod
    def detect_memory_mode(cls) -> MemoryMode:
        """Determine memory mode based on available RAM."""
        ram_gb = psutil.virtual_memory().total / (1024**3)

        if ram_gb < cls.THRESHOLDS["baseline"]:
            return "baseline"
        elif ram_gb < cls.THRESHOLDS["standard"]:
            return "standard"
        elif ram_gb < cls.THRESHOLDS["enhanced"]:
            return "enhanced"
        else:
            return "performance"

    @classmethod
    def get_worker_count(cls, mode: MemoryMode) -> int:
        """Get recommended worker count for mode."""
        return cls.WORKER_CONFIG.get(mode, 4)

    @classmethod
    def get_cache_size(cls, mode: MemoryMode) -> str:
        """Get recommended cache size for mode."""
        return cls.CACHE_CONFIG.get(mode, "100MB")

    @classmethod
    def parse_cache_size(cls, cache_size: str) -> int:
        """Parse cache size string to bytes."""
        size_str = cache_size.upper().strip()
        multipliers = {"KB": 1024, "MB": 1024**2, "GB": 1024**3}

        for suffix, mult in multipliers.items():
            if size_str.endswith(suffix):
                try:
                    return int(size_str[: -len(suffix)]) * mult
                except ValueError:
                    pass

        return 100 * 1024 * 1024  # Default 100MB
