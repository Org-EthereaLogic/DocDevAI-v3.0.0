"""
Template Cache Manager
Local caching system for marketplace templates.
"""

import json
import logging
import os
import shutil
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class TemplateCache:
    """
    Local cache manager for marketplace templates.
    
    Provides offline access to downloaded templates and metadata,
    with expiration and size management.
    """
    
    def __init__(
        self,
        cache_dir: Optional[Path] = None,
        max_size_mb: int = 500,
        expiration_days: int = 30
    ):
        """
        Initialize the template cache.
        
        Args:
            cache_dir: Directory for cache storage
            max_size_mb: Maximum cache size in MB
            expiration_days: Days before cached items expire
        """
        if cache_dir is None:
            # Default to user's cache directory
            home = Path.home()
            cache_dir = home / ".devdocai" / "marketplace_cache"
        
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        self.templates_dir = self.cache_dir / "templates"
        self.templates_dir.mkdir(exist_ok=True)
        
        self.metadata_dir = self.cache_dir / "metadata"
        self.metadata_dir.mkdir(exist_ok=True)
        
        self.max_size_bytes = max_size_mb * 1024 * 1024
        self.expiration_seconds = expiration_days * 24 * 3600
        
        # Initialize cache index
        self.index_file = self.cache_dir / "index.json"
        self.index = self._load_index()
        
        # Statistics
        self.cache_hits = 0
        self.cache_misses = 0
        
        # Clean expired items on initialization
        self._clean_expired()
        
        logger.info(f"Template cache initialized at {self.cache_dir}")
    
    def save_template(
        self,
        template_id: str,
        template_data: Dict[str, Any]
    ) -> bool:
        """
        Save a template to the cache.
        
        Args:
            template_id: Unique template identifier
            template_data: Template data to cache
            
        Returns:
            True if saved successfully
        """
        try:
            # Check cache size limit
            if self._get_cache_size() > self.max_size_bytes:
                self._evict_oldest()
            
            # Save template file
            template_file = self.templates_dir / f"{template_id}.json"
            with open(template_file, 'w') as f:
                json.dump(template_data, f, indent=2)
            
            # Update index
            self.index[template_id] = {
                "cached_at": time.time(),
                "last_accessed": time.time(),
                "size": template_file.stat().st_size,
                "version": template_data.get("version", "unknown")
            }
            self._save_index()
            
            logger.debug(f"Template {template_id} cached successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to cache template {template_id}: {e}")
            return False
    
    def get_template(
        self,
        template_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Retrieve a template from the cache.
        
        Args:
            template_id: Template identifier
            
        Returns:
            Template data or None if not cached/expired
        """
        if template_id not in self.index:
            self.cache_misses += 1
            return None
        
        # Check expiration
        cached_info = self.index[template_id]
        if self._is_expired(cached_info["cached_at"]):
            self._remove_from_cache(template_id)
            self.cache_misses += 1
            return None
        
        try:
            # Load template
            template_file = self.templates_dir / f"{template_id}.json"
            if not template_file.exists():
                self._remove_from_cache(template_id)
                self.cache_misses += 1
                return None
            
            with open(template_file, 'r') as f:
                template_data = json.load(f)
            
            # Update last accessed time
            self.index[template_id]["last_accessed"] = time.time()
            self._save_index()
            
            self.cache_hits += 1
            logger.debug(f"Template {template_id} loaded from cache")
            return template_data
            
        except Exception as e:
            logger.error(f"Failed to load cached template {template_id}: {e}")
            self.cache_misses += 1
            return None
    
    def cache_template_metadata(
        self,
        metadata: Dict[str, Any]
    ) -> bool:
        """
        Cache template metadata for browsing.
        
        Args:
            metadata: Template metadata
            
        Returns:
            True if cached successfully
        """
        try:
            template_id = metadata.get("id")
            if not template_id:
                return False
            
            metadata_file = self.metadata_dir / f"{template_id}.json"
            with open(metadata_file, 'w') as f:
                json.dump(metadata, f, indent=2)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to cache metadata: {e}")
            return False
    
    def get_template_metadata(
        self,
        template_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get cached template metadata.
        
        Args:
            template_id: Template identifier
            
        Returns:
            Metadata or None if not cached
        """
        try:
            metadata_file = self.metadata_dir / f"{template_id}.json"
            if metadata_file.exists():
                with open(metadata_file, 'r') as f:
                    return json.load(f)
            return None
        except Exception as e:
            logger.error(f"Failed to load metadata: {e}")
            return None
    
    def browse_cached_templates(
        self,
        category: Optional[str] = None,
        search: Optional[str] = None,
        sort_by: str = "recent",
        page: int = 1,
        per_page: int = 20
    ) -> Dict[str, Any]:
        """
        Browse templates from cache (offline mode).
        
        Args:
            category: Filter by category
            search: Search query
            sort_by: Sort criteria
            page: Page number
            per_page: Items per page
            
        Returns:
            Cached templates and pagination info
        """
        templates = []
        
        # Load all metadata files
        for metadata_file in self.metadata_dir.glob("*.json"):
            try:
                with open(metadata_file, 'r') as f:
                    metadata = json.load(f)
                    
                    # Apply filters
                    if category and metadata.get("category") != category:
                        continue
                    
                    if search:
                        search_lower = search.lower()
                        if not any(
                            search_lower in str(v).lower()
                            for v in [
                                metadata.get("name", ""),
                                metadata.get("description", ""),
                                metadata.get("tags", [])
                            ]
                        ):
                            continue
                    
                    templates.append(metadata)
                    
            except Exception as e:
                logger.error(f"Failed to load metadata file {metadata_file}: {e}")
        
        # Sort templates
        if sort_by == "recent":
            templates.sort(key=lambda x: x.get("updated_at", ""), reverse=True)
        elif sort_by == "popularity":
            templates.sort(key=lambda x: x.get("downloads", 0), reverse=True)
        elif sort_by == "rating":
            templates.sort(key=lambda x: x.get("rating", 0), reverse=True)
        
        # Paginate
        total = len(templates)
        start = (page - 1) * per_page
        end = start + per_page
        paginated = templates[start:end]
        
        return {
            "templates": paginated,
            "pagination": {
                "page": page,
                "per_page": per_page,
                "total": total,
                "pages": (total + per_page - 1) // per_page
            },
            "cached": True
        }
    
    def clear(self) -> bool:
        """
        Clear all cached templates.
        
        Returns:
            True if cleared successfully
        """
        try:
            # Remove all template files
            shutil.rmtree(self.templates_dir)
            self.templates_dir.mkdir(exist_ok=True)
            
            # Remove all metadata files
            shutil.rmtree(self.metadata_dir)
            self.metadata_dir.mkdir(exist_ok=True)
            
            # Clear index
            self.index = {}
            self._save_index()
            
            logger.info("Cache cleared successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to clear cache: {e}")
            return False
    
    def get_cache_info(self) -> Dict[str, Any]:
        """Get cache statistics and information."""
        size = self._get_cache_size()
        
        return {
            "location": str(self.cache_dir),
            "template_count": len(self.index),
            "metadata_count": len(list(self.metadata_dir.glob("*.json"))),
            "size_mb": size / (1024 * 1024),
            "max_size_mb": self.max_size_bytes / (1024 * 1024),
            "cache_hits": self.cache_hits,
            "cache_misses": self.cache_misses,
            "hit_rate": self.cache_hits / max(1, self.cache_hits + self.cache_misses),
            "expiration_days": self.expiration_seconds / (24 * 3600)
        }
    
    def _load_index(self) -> Dict[str, Any]:
        """Load the cache index."""
        if self.index_file.exists():
            try:
                with open(self.index_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Failed to load index: {e}")
        return {}
    
    def _save_index(self):
        """Save the cache index."""
        try:
            with open(self.index_file, 'w') as f:
                json.dump(self.index, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save index: {e}")
    
    def _get_cache_size(self) -> int:
        """Get total cache size in bytes."""
        total_size = 0
        for file_path in self.cache_dir.rglob("*"):
            if file_path.is_file():
                total_size += file_path.stat().st_size
        return total_size
    
    def _is_expired(self, cached_time: float) -> bool:
        """Check if a cached item is expired."""
        return (time.time() - cached_time) > self.expiration_seconds
    
    def _clean_expired(self):
        """Remove expired items from cache."""
        expired = []
        for template_id, info in self.index.items():
            if self._is_expired(info["cached_at"]):
                expired.append(template_id)
        
        for template_id in expired:
            self._remove_from_cache(template_id)
        
        if expired:
            logger.info(f"Cleaned {len(expired)} expired templates from cache")
    
    def _evict_oldest(self):
        """Evict oldest accessed items to make space."""
        if not self.index:
            return
        
        # Sort by last accessed time
        sorted_items = sorted(
            self.index.items(),
            key=lambda x: x[1]["last_accessed"]
        )
        
        # Remove oldest 20% of items
        to_remove = max(1, len(sorted_items) // 5)
        for template_id, _ in sorted_items[:to_remove]:
            self._remove_from_cache(template_id)
        
        logger.info(f"Evicted {to_remove} templates from cache")
    
    def _remove_from_cache(self, template_id: str):
        """Remove a template from cache."""
        # Remove template file
        template_file = self.templates_dir / f"{template_id}.json"
        if template_file.exists():
            template_file.unlink()
        
        # Remove from index
        if template_id in self.index:
            del self.index[template_id]
            self._save_index()
    
    def __len__(self) -> int:
        """Get number of cached templates."""
        return len(self.index)
    
    def __repr__(self) -> str:
        """String representation."""
        return f"TemplateCache(templates={len(self.index)}, size_mb={self._get_cache_size()/(1024*1024):.1f})"