"""
Cost optimization system for LLM usage in document enhancements.

Tracks and optimizes costs associated with LLM-based enhancements.
"""

import logging
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import json
from pathlib import Path

from .config import PipelineConfig, EnhancementType

logger = logging.getLogger(__name__)


@dataclass
class CostMetrics:
    """Metrics for enhancement costs."""
    
    total_cost: float
    token_count: int
    api_calls: int
    
    # Per-provider breakdown
    provider_costs: Dict[str, float] = field(default_factory=dict)
    provider_tokens: Dict[str, int] = field(default_factory=dict)
    provider_calls: Dict[str, int] = field(default_factory=dict)
    
    # Per-strategy breakdown
    strategy_costs: Dict[str, float] = field(default_factory=dict)
    strategy_tokens: Dict[str, int] = field(default_factory=dict)
    strategy_calls: Dict[str, int] = field(default_factory=dict)
    
    # Time-based metrics
    hourly_cost: float = 0.0
    daily_cost: float = 0.0
    monthly_projection: float = 0.0
    
    # Efficiency metrics
    cost_per_document: float = 0.0
    cost_per_token: float = 0.0
    cost_per_improvement_point: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert metrics to dictionary."""
        return {
            "total_cost": self.total_cost,
            "token_count": self.token_count,
            "api_calls": self.api_calls,
            "provider_costs": self.provider_costs,
            "provider_tokens": self.provider_tokens,
            "provider_calls": self.provider_calls,
            "strategy_costs": self.strategy_costs,
            "strategy_tokens": self.strategy_tokens,
            "strategy_calls": self.strategy_calls,
            "hourly_cost": self.hourly_cost,
            "daily_cost": self.daily_cost,
            "monthly_projection": self.monthly_projection,
            "cost_per_document": self.cost_per_document,
            "cost_per_token": self.cost_per_token,
            "cost_per_improvement_point": self.cost_per_improvement_point
        }


@dataclass
class OptimizationResult:
    """Result from cost optimization."""
    
    optimized: bool
    original_cost: float
    optimized_cost: float
    savings: float
    savings_percentage: float
    optimization_strategy: str
    recommendations: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary."""
        return {
            "optimized": self.optimized,
            "original_cost": self.original_cost,
            "optimized_cost": self.optimized_cost,
            "savings": self.savings,
            "savings_percentage": self.savings_percentage,
            "optimization_strategy": self.optimization_strategy,
            "recommendations": self.recommendations
        }


class CostOptimizer:
    """
    Optimizes LLM usage costs for document enhancements.
    
    Tracks costs, provides optimization strategies, and manages budgets.
    """
    
    # Provider pricing (per 1K tokens)
    PROVIDER_PRICING = {
        "openai": {
            "gpt-4": {"input": 0.03, "output": 0.06},
            "gpt-3.5-turbo": {"input": 0.001, "output": 0.002},
            "gpt-4-turbo": {"input": 0.01, "output": 0.03}
        },
        "anthropic": {
            "claude-3-opus": {"input": 0.015, "output": 0.075},
            "claude-3-sonnet": {"input": 0.003, "output": 0.015},
            "claude-3-haiku": {"input": 0.00025, "output": 0.00125}
        },
        "google": {
            "gemini-pro": {"input": 0.00025, "output": 0.0005},
            "gemini-pro-vision": {"input": 0.00025, "output": 0.0005}
        },
        "local": {
            "default": {"input": 0.0, "output": 0.0}  # No cost for local models
        }
    }
    
    # Strategy cost multipliers
    STRATEGY_MULTIPLIERS = {
        EnhancementType.CLARITY: 1.0,
        EnhancementType.COMPLETENESS: 1.5,  # More tokens needed
        EnhancementType.CONSISTENCY: 0.8,
        EnhancementType.ACCURACY: 1.2,
        EnhancementType.READABILITY: 0.9
    }
    
    def __init__(self, config: Optional[PipelineConfig] = None):
        """
        Initialize cost optimizer.
        
        Args:
            config: Pipeline configuration
        """
        self.config = config or PipelineConfig()
        
        # Cost tracking
        self.total_cost = 0.0
        self.total_tokens = 0
        self.total_calls = 0
        self.documents_processed = 0
        
        # Detailed tracking
        self.provider_usage: Dict[str, Dict[str, float]] = {}
        self.strategy_usage: Dict[str, Dict[str, float]] = {}
        self.hourly_costs: List[Tuple[datetime, float]] = []
        
        # Budget management
        self.daily_budget = 10.0  # Default daily budget
        self.monthly_budget = 200.0  # Default monthly budget
        self.daily_spent = 0.0
        self.monthly_spent = 0.0
        self.budget_reset_time = datetime.now()
        
        # Optimization cache
        self._optimization_cache: Dict[str, OptimizationResult] = {}
        
        logger.info("Cost Optimizer initialized")
    
    def calculate_cost(
        self,
        content_length: int,
        strategy_name: Optional[str] = None,
        provider: str = "openai",
        model: str = "gpt-3.5-turbo"
    ) -> float:
        """
        Calculate estimated cost for enhancement.
        
        Args:
            content_length: Length of content in characters
            strategy_name: Enhancement strategy being used
            provider: LLM provider
            model: Specific model
            
        Returns:
            Estimated cost in dollars
        """
        # Estimate tokens (rough approximation: 4 chars = 1 token)
        estimated_tokens = content_length / 4
        
        # Get base pricing
        if provider in self.PROVIDER_PRICING and model in self.PROVIDER_PRICING[provider]:
            pricing = self.PROVIDER_PRICING[provider][model]
        else:
            # Default pricing if not found
            pricing = {"input": 0.001, "output": 0.002}
        
        # Calculate base cost (assume equal input/output for simplicity)
        base_cost = (estimated_tokens / 1000) * (pricing["input"] + pricing["output"])
        
        # Apply strategy multiplier
        if strategy_name:
            strategy_type = self._get_strategy_type(strategy_name)
            if strategy_type in self.STRATEGY_MULTIPLIERS:
                base_cost *= self.STRATEGY_MULTIPLIERS[strategy_type]
        
        # Apply optimization if enabled
        if self.config.cost_optimization:
            base_cost *= 0.8  # 20% reduction through optimization
        
        return base_cost
    
    def track_usage(
        self,
        cost: float,
        tokens: int,
        provider: str,
        model: str,
        strategy: Optional[str] = None
    ) -> None:
        """
        Track LLM usage and costs.
        
        Args:
            cost: Cost in dollars
            tokens: Number of tokens used
            provider: LLM provider
            model: Model used
            strategy: Enhancement strategy
        """
        # Update totals
        self.total_cost += cost
        self.total_tokens += tokens
        self.total_calls += 1
        
        # Track by provider
        if provider not in self.provider_usage:
            self.provider_usage[provider] = {
                "cost": 0.0,
                "tokens": 0,
                "calls": 0
            }
        self.provider_usage[provider]["cost"] += cost
        self.provider_usage[provider]["tokens"] += tokens
        self.provider_usage[provider]["calls"] += 1
        
        # Track by strategy
        if strategy:
            if strategy not in self.strategy_usage:
                self.strategy_usage[strategy] = {
                    "cost": 0.0,
                    "tokens": 0,
                    "calls": 0
                }
            self.strategy_usage[strategy]["cost"] += cost
            self.strategy_usage[strategy]["tokens"] += tokens
            self.strategy_usage[strategy]["calls"] += 1
        
        # Update hourly tracking
        current_hour = datetime.now().replace(minute=0, second=0, microsecond=0)
        if self.hourly_costs and self.hourly_costs[-1][0] == current_hour:
            self.hourly_costs[-1] = (current_hour, self.hourly_costs[-1][1] + cost)
        else:
            self.hourly_costs.append((current_hour, cost))
        
        # Update budget tracking
        self.daily_spent += cost
        self.monthly_spent += cost
        
        # Check budget resets
        self._check_budget_resets()
        
        # Log if approaching limits
        if self.daily_spent > self.daily_budget * 0.8:
            logger.warning(f"Approaching daily budget limit: ${self.daily_spent:.2f}/${self.daily_budget:.2f}")
        if self.monthly_spent > self.monthly_budget * 0.8:
            logger.warning(f"Approaching monthly budget limit: ${self.monthly_spent:.2f}/${self.monthly_budget:.2f}")
    
    def optimize_cost(
        self,
        content: str,
        strategies: List[str],
        quality_threshold: float = 0.8
    ) -> OptimizationResult:
        """
        Optimize enhancement costs while maintaining quality.
        
        Args:
            content: Content to enhance
            strategies: List of strategies to apply
            quality_threshold: Minimum quality requirement
            
        Returns:
            OptimizationResult with recommendations
        """
        # Check cache
        cache_key = f"{len(content)}_{','.join(strategies)}_{quality_threshold}"
        if cache_key in self._optimization_cache:
            return self._optimization_cache[cache_key]
        
        # Calculate original cost
        original_cost = sum(
            self.calculate_cost(len(content), strategy)
            for strategy in strategies
        )
        
        # Optimization strategies
        optimized_cost = original_cost
        optimization_strategy = "none"
        recommendations = []
        
        # Strategy 1: Use cheaper models for simple tasks
        if quality_threshold < 0.7:
            optimized_cost *= 0.5  # Use cheaper models
            optimization_strategy = "cheaper_models"
            recommendations.append("Use GPT-3.5-turbo instead of GPT-4 for basic enhancements")
        
        # Strategy 2: Reduce redundant strategies
        essential_strategies = self._identify_essential_strategies(strategies, quality_threshold)
        if len(essential_strategies) < len(strategies):
            optimized_cost *= len(essential_strategies) / len(strategies)
            optimization_strategy = "reduce_strategies"
            recommendations.append(f"Focus on essential strategies: {', '.join(essential_strategies)}")
        
        # Strategy 3: Batch processing
        if len(content) > 5000:
            optimized_cost *= 0.85  # 15% discount for batch processing
            if optimization_strategy != "none":
                optimization_strategy += "+batch"
            else:
                optimization_strategy = "batch_processing"
            recommendations.append("Use batch processing for large documents")
        
        # Strategy 4: Caching and reuse
        if self.config.use_cache:
            optimized_cost *= 0.9  # 10% reduction through caching
            if optimization_strategy != "none":
                optimization_strategy += "+cache"
            else:
                optimization_strategy = "caching"
            recommendations.append("Enable caching to reduce redundant API calls")
        
        # Strategy 5: Progressive enhancement
        if quality_threshold >= 0.9:
            recommendations.append("Consider progressive enhancement: start with basic improvements")
            recommendations.append("Only apply expensive strategies if quality is still below threshold")
        
        # Create result
        result = OptimizationResult(
            optimized=optimized_cost < original_cost,
            original_cost=original_cost,
            optimized_cost=optimized_cost,
            savings=original_cost - optimized_cost,
            savings_percentage=((original_cost - optimized_cost) / original_cost) * 100 if original_cost > 0 else 0,
            optimization_strategy=optimization_strategy,
            recommendations=recommendations
        )
        
        # Cache result
        self._optimization_cache[cache_key] = result
        
        return result
    
    def get_metrics(self) -> CostMetrics:
        """
        Get comprehensive cost metrics.
        
        Returns:
            CostMetrics object
        """
        # Calculate time-based metrics
        hourly_cost = self._calculate_hourly_average()
        daily_cost = self._calculate_daily_average()
        monthly_projection = daily_cost * 30
        
        # Calculate efficiency metrics
        cost_per_document = self.total_cost / max(self.documents_processed, 1)
        cost_per_token = self.total_cost / max(self.total_tokens, 1)
        
        # Estimate cost per improvement point (simplified)
        avg_improvement = 0.1  # Assume 10% average improvement
        cost_per_improvement_point = self.total_cost / (max(self.documents_processed, 1) * avg_improvement * 100)
        
        return CostMetrics(
            total_cost=self.total_cost,
            token_count=self.total_tokens,
            api_calls=self.total_calls,
            provider_costs={p: d["cost"] for p, d in self.provider_usage.items()},
            provider_tokens={p: d["tokens"] for p, d in self.provider_usage.items()},
            provider_calls={p: d["calls"] for p, d in self.provider_usage.items()},
            strategy_costs={s: d["cost"] for s, d in self.strategy_usage.items()},
            strategy_tokens={s: d["tokens"] for s, d in self.strategy_usage.items()},
            strategy_calls={s: d["calls"] for s, d in self.strategy_usage.items()},
            hourly_cost=hourly_cost,
            daily_cost=daily_cost,
            monthly_projection=monthly_projection,
            cost_per_document=cost_per_document,
            cost_per_token=cost_per_token,
            cost_per_improvement_point=cost_per_improvement_point
        )
    
    def check_budget(self, estimated_cost: float) -> bool:
        """
        Check if estimated cost is within budget.
        
        Args:
            estimated_cost: Estimated cost for operation
            
        Returns:
            True if within budget, False otherwise
        """
        self._check_budget_resets()
        
        # Check daily budget
        if self.daily_spent + estimated_cost > self.daily_budget:
            logger.warning(f"Daily budget would be exceeded: ${self.daily_spent + estimated_cost:.2f} > ${self.daily_budget:.2f}")
            return False
        
        # Check monthly budget
        if self.monthly_spent + estimated_cost > self.monthly_budget:
            logger.warning(f"Monthly budget would be exceeded: ${self.monthly_spent + estimated_cost:.2f} > ${self.monthly_budget:.2f}")
            return False
        
        # Check per-document limit
        if estimated_cost > self.config.max_cost_per_document:
            logger.warning(f"Per-document cost limit exceeded: ${estimated_cost:.2f} > ${self.config.max_cost_per_document:.2f}")
            return False
        
        return True
    
    def get_cost_breakdown(self) -> Dict[str, Any]:
        """
        Get detailed cost breakdown.
        
        Returns:
            Dictionary with cost breakdown by provider and strategy
        """
        return {
            "total": {
                "cost": self.total_cost,
                "tokens": self.total_tokens,
                "calls": self.total_calls,
                "documents": self.documents_processed
            },
            "by_provider": self.provider_usage,
            "by_strategy": self.strategy_usage,
            "budget": {
                "daily": {
                    "spent": self.daily_spent,
                    "limit": self.daily_budget,
                    "remaining": self.daily_budget - self.daily_spent
                },
                "monthly": {
                    "spent": self.monthly_spent,
                    "limit": self.monthly_budget,
                    "remaining": self.monthly_budget - self.monthly_spent
                }
            },
            "averages": {
                "per_document": self.total_cost / max(self.documents_processed, 1),
                "per_call": self.total_cost / max(self.total_calls, 1),
                "per_1k_tokens": (self.total_cost / max(self.total_tokens, 1)) * 1000
            }
        }
    
    def suggest_optimizations(self) -> List[str]:
        """
        Suggest cost optimization strategies based on usage patterns.
        
        Returns:
            List of optimization suggestions
        """
        suggestions = []
        
        # Analyze provider usage
        if self.provider_usage:
            most_expensive = max(
                self.provider_usage.items(),
                key=lambda x: x[1]["cost"]
            )
            if most_expensive[0] == "openai" and "gpt-4" in str(most_expensive):
                suggestions.append("Consider using GPT-3.5-turbo for non-critical enhancements")
        
        # Analyze strategy usage
        if self.strategy_usage:
            expensive_strategies = [
                s for s, data in self.strategy_usage.items()
                if data["cost"] / max(data["calls"], 1) > 0.10
            ]
            if expensive_strategies:
                suggestions.append(f"Optimize expensive strategies: {', '.join(expensive_strategies)}")
        
        # Check token efficiency
        avg_tokens_per_call = self.total_tokens / max(self.total_calls, 1)
        if avg_tokens_per_call > 2000:
            suggestions.append("Consider breaking large documents into smaller chunks")
        
        # Cache utilization
        if not self.config.use_cache:
            suggestions.append("Enable caching to reduce redundant API calls")
        
        # Batch processing
        if self.documents_processed > 10 and not self.config.parallel_processing:
            suggestions.append("Enable batch processing for multiple documents")
        
        # Model selection
        if self.total_cost > 1.0:
            suggestions.append("Implement dynamic model selection based on task complexity")
        
        # Time-based optimization
        hourly_pattern = self._analyze_hourly_pattern()
        if hourly_pattern:
            suggestions.append(f"Schedule non-urgent enhancements during off-peak hours: {hourly_pattern}")
        
        return suggestions
    
    def _get_strategy_type(self, strategy_name: str) -> Optional[EnhancementType]:
        """Map strategy name to EnhancementType."""
        mapping = {
            "clarity": EnhancementType.CLARITY,
            "completeness": EnhancementType.COMPLETENESS,
            "consistency": EnhancementType.CONSISTENCY,
            "accuracy": EnhancementType.ACCURACY,
            "readability": EnhancementType.READABILITY
        }
        
        strategy_lower = strategy_name.lower()
        for key, value in mapping.items():
            if key in strategy_lower:
                return value
        
        return None
    
    def _identify_essential_strategies(
        self,
        strategies: List[str],
        quality_threshold: float
    ) -> List[str]:
        """Identify essential strategies for quality threshold."""
        # Simplified logic - in production, this would use historical data
        if quality_threshold >= 0.9:
            return strategies  # Need all strategies for high quality
        elif quality_threshold >= 0.8:
            # Skip consistency for medium quality
            return [s for s in strategies if "consistency" not in s.lower()]
        else:
            # Only clarity and readability for basic quality
            return [s for s in strategies if any(
                x in s.lower() for x in ["clarity", "readability"]
            )]
    
    def _calculate_hourly_average(self) -> float:
        """Calculate average hourly cost."""
        if not self.hourly_costs:
            return 0.0
        
        # Get costs from last 24 hours
        cutoff = datetime.now() - timedelta(hours=24)
        recent_costs = [
            cost for timestamp, cost in self.hourly_costs
            if timestamp >= cutoff
        ]
        
        if not recent_costs:
            return 0.0
        
        return sum(recent_costs) / len(recent_costs)
    
    def _calculate_daily_average(self) -> float:
        """Calculate average daily cost."""
        if not self.hourly_costs:
            return 0.0
        
        # Group by day
        daily_costs = {}
        for timestamp, cost in self.hourly_costs:
            day = timestamp.date()
            if day not in daily_costs:
                daily_costs[day] = 0.0
            daily_costs[day] += cost
        
        if not daily_costs:
            return 0.0
        
        return sum(daily_costs.values()) / len(daily_costs)
    
    def _analyze_hourly_pattern(self) -> Optional[str]:
        """Analyze hourly cost patterns."""
        if len(self.hourly_costs) < 24:
            return None
        
        # Find cheapest hours
        hourly_averages = {}
        for timestamp, cost in self.hourly_costs:
            hour = timestamp.hour
            if hour not in hourly_averages:
                hourly_averages[hour] = []
            hourly_averages[hour].append(cost)
        
        if not hourly_averages:
            return None
        
        # Calculate average for each hour
        avg_by_hour = {
            hour: sum(costs) / len(costs)
            for hour, costs in hourly_averages.items()
        }
        
        # Find cheapest hours
        sorted_hours = sorted(avg_by_hour.items(), key=lambda x: x[1])
        cheapest_hours = [str(h) for h, _ in sorted_hours[:3]]
        
        return f"{', '.join(cheapest_hours)}:00"
    
    def _check_budget_resets(self) -> None:
        """Check and reset budgets if needed."""
        now = datetime.now()
        
        # Daily reset
        if now.date() > self.budget_reset_time.date():
            self.daily_spent = 0.0
            self.budget_reset_time = now
            logger.info("Daily budget reset")
        
        # Monthly reset
        if now.month != self.budget_reset_time.month:
            self.monthly_spent = 0.0
            logger.info("Monthly budget reset")
    
    def export_cost_report(self, output_path: Path) -> None:
        """
        Export cost report to file.
        
        Args:
            output_path: Path to output file
        """
        report = {
            "summary": self.get_cost_breakdown(),
            "metrics": self.get_metrics().to_dict(),
            "optimizations": self.suggest_optimizations(),
            "timestamp": datetime.now().isoformat()
        }
        
        with open(output_path, 'w') as f:
            json.dump(report, f, indent=2)
        
        logger.info(f"Exported cost report to {output_path}")
    
    def get_total_cost(self) -> float:
        """Get total cost incurred."""
        return self.total_cost
    
    def reset_metrics(self) -> None:
        """Reset all cost metrics."""
        self.total_cost = 0.0
        self.total_tokens = 0
        self.total_calls = 0
        self.documents_processed = 0
        self.provider_usage.clear()
        self.strategy_usage.clear()
        self.hourly_costs.clear()
        self._optimization_cache.clear()
        logger.info("Cost metrics reset")