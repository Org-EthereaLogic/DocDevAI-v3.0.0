"""
M008: Integration interfaces with other DevDocAI modules.

Provides integration points for M003 MIAIR Engine, M004 Document Generator,
and other modules that need AI-powered capabilities.
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any, Union
from datetime import datetime
from decimal import Decimal

# Try to import MIAIR Engine (M003)
try:
    from devdocai.miair.engine_unified import UnifiedMIAIREngine, UnifiedMIAIRConfig
    from devdocai.miair.scorer import QualityMetrics, QualityScorer
    MIAIR_AVAILABLE = True
except ImportError:
    MIAIR_AVAILABLE = False
    UnifiedMIAIREngine = None
    UnifiedMIAIRConfig = None
    QualityMetrics = None
    QualityScorer = None

# Try to import Configuration Manager (M001) for API key decryption
try:
    from devdocai.core.config import ConfigurationManager
    CONFIG_AVAILABLE = True
except ImportError:
    CONFIG_AVAILABLE = False
    ConfigurationManager = None

from .providers.base import LLMRequest, LLMResponse
from .config import ProviderConfig

logger = logging.getLogger(__name__)


class MIAIRIntegration:
    """
    Integration layer for M003 MIAIR Engine.
    
    Enables AI-powered document refinement and quality analysis
    using the MIAIR engine's optimization capabilities.
    """
    
    def __init__(
        self, 
        llm_adapter: 'LLMAdapter',
        miair_config: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize MIAIR integration.
        
        Args:
            llm_adapter: Reference to the main LLM adapter
            miair_config: Configuration for MIAIR engine
        """
        self.llm_adapter = llm_adapter
        self.miair_engine = None
        
        if MIAIR_AVAILABLE and miair_config:
            try:
                config = UnifiedMIAIRConfig(**miair_config)
                self.miair_engine = UnifiedMIAIREngine(config)
                logger.info("MIAIR integration initialized successfully")
            except Exception as e:
                logger.warning(f"Failed to initialize MIAIR engine: {e}")
                self.miair_engine = None
        elif not MIAIR_AVAILABLE:
            logger.warning("MIAIR engine not available - install M003 module")
    
    async def enhance_document(
        self,
        content: str,
        target_quality: float = 0.85,
        max_iterations: int = 3,
        preferred_provider: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Enhance document content using MIAIR optimization.
        
        Args:
            content: Original document content
            target_quality: Target quality score (0.0-1.0)
            max_iterations: Maximum optimization iterations
            preferred_provider: Preferred LLM provider for enhancement
            
        Returns:
            Dictionary with enhanced content and quality metrics
        """
        if not self.miair_engine:
            logger.warning("MIAIR engine not available for enhancement")
            return {
                "enhanced_content": content,
                "quality_score": 0.0,
                "iterations": 0,
                "improvements": [],
                "error": "MIAIR engine not available"
            }
        
        try:
            # Initial quality analysis
            initial_quality = await self._analyze_quality(content)
            
            if initial_quality.overall_score >= target_quality:
                return {
                    "enhanced_content": content,
                    "quality_score": initial_quality.overall_score,
                    "iterations": 0,
                    "improvements": [],
                    "message": "Content already meets target quality"
                }
            
            # Iterative enhancement
            current_content = content
            improvements = []
            
            for iteration in range(max_iterations):
                # Analyze current content
                quality_metrics = await self._analyze_quality(current_content)
                
                if quality_metrics.overall_score >= target_quality:
                    break
                
                # Generate improvement suggestions using MIAIR
                suggestions = await self._generate_improvements(
                    current_content, quality_metrics, preferred_provider
                )
                
                if not suggestions:
                    break
                
                # Apply improvements using LLM
                enhanced_content = await self._apply_improvements(
                    current_content, suggestions, preferred_provider
                )
                
                if enhanced_content and enhanced_content != current_content:
                    # Verify improvement
                    new_quality = await self._analyze_quality(enhanced_content)
                    
                    if new_quality.overall_score > quality_metrics.overall_score:
                        improvements.append({
                            "iteration": iteration + 1,
                            "old_quality": quality_metrics.overall_score,
                            "new_quality": new_quality.overall_score,
                            "improvements": suggestions,
                            "content_length_change": len(enhanced_content) - len(current_content)
                        })
                        current_content = enhanced_content
                    else:
                        logger.debug(f"Iteration {iteration + 1} did not improve quality")
                        break
                else:
                    logger.debug(f"No content changes in iteration {iteration + 1}")
                    break
            
            # Final quality analysis
            final_quality = await self._analyze_quality(current_content)
            
            return {
                "enhanced_content": current_content,
                "quality_score": final_quality.overall_score,
                "initial_quality": initial_quality.overall_score,
                "improvement": final_quality.overall_score - initial_quality.overall_score,
                "iterations": len(improvements),
                "improvements": improvements,
                "target_reached": final_quality.overall_score >= target_quality
            }
            
        except Exception as e:
            logger.error(f"Document enhancement failed: {e}")
            return {
                "enhanced_content": content,
                "quality_score": 0.0,
                "iterations": 0,
                "improvements": [],
                "error": str(e)
            }
    
    async def analyze_content_quality(self, content: str) -> Dict[str, Any]:
        """
        Analyze content quality using MIAIR engine.
        
        Args:
            content: Content to analyze
            
        Returns:
            Quality analysis results
        """
        if not self.miair_engine:
            return {"error": "MIAIR engine not available"}
        
        try:
            quality_metrics = await self._analyze_quality(content)
            
            return {
                "overall_score": quality_metrics.overall_score,
                "readability": quality_metrics.readability,
                "completeness": quality_metrics.completeness,
                "accuracy": quality_metrics.accuracy,
                "structure": quality_metrics.structure,
                "clarity": quality_metrics.clarity,
                "metadata": {
                    "word_count": len(content.split()),
                    "character_count": len(content),
                    "analysis_timestamp": datetime.utcnow().isoformat()
                }
            }
            
        except Exception as e:
            logger.error(f"Quality analysis failed: {e}")
            return {"error": str(e)}
    
    async def _analyze_quality(self, content: str) -> 'QualityMetrics':
        """Analyze content quality using MIAIR engine."""
        if not self.miair_engine:
            # Return dummy metrics if MIAIR not available
            return type('QualityMetrics', (), {
                'overall_score': 0.5,
                'readability': 0.5,
                'completeness': 0.5,
                'accuracy': 0.5,
                'structure': 0.5,
                'clarity': 0.5
            })()
        
        # Use MIAIR engine to analyze quality
        result = await self.miair_engine.analyze_document({
            "content": content,
            "type": "documentation"
        })
        
        return result.get("quality_metrics", {})
    
    async def _generate_improvements(
        self,
        content: str,
        quality_metrics: 'QualityMetrics',
        preferred_provider: Optional[str] = None
    ) -> List[str]:
        """Generate improvement suggestions using LLM."""
        
        # Create improvement prompt based on quality analysis
        weak_areas = []
        if hasattr(quality_metrics, 'readability') and quality_metrics.readability < 0.7:
            weak_areas.append("readability (improve sentence structure and word choice)")
        if hasattr(quality_metrics, 'completeness') and quality_metrics.completeness < 0.7:
            weak_areas.append("completeness (add missing information or sections)")
        if hasattr(quality_metrics, 'structure') and quality_metrics.structure < 0.7:
            weak_areas.append("structure (improve organization and flow)")
        if hasattr(quality_metrics, 'clarity') and quality_metrics.clarity < 0.7:
            weak_areas.append("clarity (make explanations clearer)")
        
        if not weak_areas:
            return []
        
        prompt = f"""Analyze this document and suggest specific improvements for: {', '.join(weak_areas)}

Document:
{content[:2000]}{'...' if len(content) > 2000 else ''}

Please provide 3-5 specific, actionable improvement suggestions focused on the weak areas identified. Each suggestion should be concrete and implementable."""
        
        request = LLMRequest(
            messages=[
                {"role": "system", "content": "You are a technical writing expert helping improve document quality."},
                {"role": "user", "content": prompt}
            ],
            model="gpt-3.5-turbo",  # Use efficient model for analysis
            max_tokens=500,
            temperature=0.3  # Lower temperature for consistent suggestions
        )
        
        try:
            response, _ = await self.llm_adapter.generate_with_fallback(
                request, preferred_provider
            )
            
            # Parse suggestions from response
            suggestions = []
            for line in response.content.split('\n'):
                line = line.strip()
                if line and (line.startswith('- ') or line.startswith('• ') or 
                           any(line.startswith(f'{i}.') for i in range(1, 10))):
                    suggestions.append(line.lstrip('- •').lstrip('123456789. ').strip())
            
            return suggestions[:5]  # Limit to 5 suggestions
            
        except Exception as e:
            logger.error(f"Failed to generate improvements: {e}")
            return []
    
    async def _apply_improvements(
        self,
        content: str,
        improvements: List[str],
        preferred_provider: Optional[str] = None
    ) -> Optional[str]:
        """Apply improvements to content using LLM."""
        
        improvements_text = '\n'.join(f"- {imp}" for imp in improvements)
        
        prompt = f"""Please improve this document by applying the following suggestions:

{improvements_text}

Original document:
{content}

Please return the improved document that incorporates these suggestions while maintaining the original structure and key information."""
        
        request = LLMRequest(
            messages=[
                {"role": "system", "content": "You are a technical writing expert. Improve the document while preserving its core content and structure."},
                {"role": "user", "content": prompt}
            ],
            model="gpt-4",  # Use higher quality model for improvements
            max_tokens=len(content.split()) * 2,  # Allow for expansion
            temperature=0.2  # Low temperature for consistent improvements
        )
        
        try:
            response, _ = await self.llm_adapter.generate_with_fallback(
                request, preferred_provider
            )
            return response.content
            
        except Exception as e:
            logger.error(f"Failed to apply improvements: {e}")
            return None


class ConfigIntegration:
    """
    Integration with M001 Configuration Manager.
    
    Handles secure API key management and configuration loading.
    """
    
    def __init__(self):
        """Initialize configuration integration."""
        self.config_manager = None
        
        if CONFIG_AVAILABLE:
            try:
                self.config_manager = ConfigurationManager()
                logger.info("Configuration integration initialized")
            except Exception as e:
                logger.warning(f"Failed to initialize config manager: {e}")
        else:
            logger.warning("Configuration manager not available")
    
    def decrypt_provider_keys(
        self, 
        providers_config: Dict[str, ProviderConfig]
    ) -> Dict[str, ProviderConfig]:
        """
        Decrypt API keys for provider configurations.
        
        Args:
            providers_config: Provider configurations with encrypted keys
            
        Returns:
            Provider configurations with decrypted keys
        """
        if not self.config_manager:
            return providers_config
        
        decrypted_configs = {}
        
        for name, config in providers_config.items():
            new_config = config.model_copy()
            
            if config.api_key_encrypted:
                try:
                    # Use M001's decryption method
                    decrypted_keys = self.config_manager.decrypt_api_keys({
                        name: config.api_key_encrypted
                    })
                    new_config.api_key = decrypted_keys.get(name)
                    logger.debug(f"Decrypted API key for {name}")
                except Exception as e:
                    logger.error(f"Failed to decrypt API key for {name}: {e}")
            
            decrypted_configs[name] = new_config
        
        return decrypted_configs
    
    def encrypt_provider_keys(
        self,
        providers_config: Dict[str, ProviderConfig]
    ) -> Dict[str, ProviderConfig]:
        """
        Encrypt API keys for provider configurations.
        
        Args:
            providers_config: Provider configurations with plain text keys
            
        Returns:
            Provider configurations with encrypted keys
        """
        if not self.config_manager:
            return providers_config
        
        encrypted_configs = {}
        
        for name, config in providers_config.items():
            new_config = config.model_copy()
            
            if config.api_key:
                try:
                    # Use M001's encryption method
                    encrypted_keys = self.config_manager.encrypt_api_keys({
                        name: config.api_key
                    })
                    new_config.api_key_encrypted = encrypted_keys.get(name)
                    new_config.api_key = None  # Clear plain text
                    logger.debug(f"Encrypted API key for {name}")
                except Exception as e:
                    logger.error(f"Failed to encrypt API key for {name}: {e}")
            
            encrypted_configs[name] = new_config
        
        return encrypted_configs


class QualityAnalyzer:
    """
    Standalone quality analysis using LLM providers.
    
    Provides quality analysis when MIAIR engine is not available.
    """
    
    def __init__(self, llm_adapter: 'LLMAdapter'):
        """Initialize quality analyzer."""
        self.llm_adapter = llm_adapter
    
    async def analyze_quality(
        self,
        content: str,
        content_type: str = "documentation",
        preferred_provider: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Analyze content quality using LLM.
        
        Args:
            content: Content to analyze
            content_type: Type of content (documentation, code, etc.)
            preferred_provider: Preferred LLM provider
            
        Returns:
            Quality analysis results
        """
        prompt = f"""Analyze the quality of this {content_type} content and provide scores (0.0-1.0) for each dimension:

Content:
{content[:3000]}{'...' if len(content) > 3000 else ''}

Please analyze and score the following dimensions:
- Readability: How easy is it to read and understand?
- Completeness: Is all necessary information included?
- Accuracy: Is the information correct and reliable?
- Structure: Is the content well-organized and logical?
- Clarity: Are concepts explained clearly?

Provide your response in this format:
Readability: 0.X
Completeness: 0.X
Accuracy: 0.X
Structure: 0.X
Clarity: 0.X
Overall: 0.X

Brief explanation of the scores and key areas for improvement."""
        
        request = LLMRequest(
            messages=[
                {"role": "system", "content": "You are a content quality expert. Provide objective, numerical quality assessments."},
                {"role": "user", "content": prompt}
            ],
            model="gpt-3.5-turbo",
            max_tokens=400,
            temperature=0.1  # Very low temperature for consistent scoring
        )
        
        try:
            response, _ = await self.llm_adapter.generate_with_fallback(
                request, preferred_provider
            )
            
            # Parse quality scores from response
            scores = {}
            lines = response.content.split('\n')
            
            for line in lines:
                line = line.strip()
                if ':' in line and any(dim in line.lower() for dim in 
                                     ['readability', 'completeness', 'accuracy', 'structure', 'clarity', 'overall']):
                    parts = line.split(':', 1)
                    if len(parts) == 2:
                        dim_name = parts[0].strip().lower()
                        try:
                            score = float(parts[1].strip())
                            scores[dim_name] = min(max(score, 0.0), 1.0)  # Clamp to 0-1
                        except ValueError:
                            continue
            
            return {
                "readability": scores.get("readability", 0.5),
                "completeness": scores.get("completeness", 0.5),
                "accuracy": scores.get("accuracy", 0.5),
                "structure": scores.get("structure", 0.5),
                "clarity": scores.get("clarity", 0.5),
                "overall_score": scores.get("overall", 0.5),
                "analysis_text": response.content,
                "word_count": len(content.split()),
                "character_count": len(content)
            }
            
        except Exception as e:
            logger.error(f"Quality analysis failed: {e}")
            return {
                "error": str(e),
                "readability": 0.0,
                "completeness": 0.0,
                "accuracy": 0.0,
                "structure": 0.0,
                "clarity": 0.0,
                "overall_score": 0.0
            }