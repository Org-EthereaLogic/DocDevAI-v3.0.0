"""
Tests for cost optimization system.
"""

import pytest
import json
from pathlib import Path
import tempfile
from datetime import datetime, timedelta

from devdocai.enhancement.cost_optimizer import (
    CostMetrics,
    OptimizationResult,
    CostOptimizer
)
from devdocai.enhancement.config import PipelineConfig, EnhancementType


class TestCostMetrics:
    """Test CostMetrics dataclass."""
    
    def test_initialization(self):
        """Test cost metrics initialization."""
        metrics = CostMetrics(
            total_cost=10.50,
            token_count=50000,
            api_calls=100,
            provider_costs={"openai": 8.0, "anthropic": 2.5},
            provider_tokens={"openai": 40000, "anthropic": 10000},
            provider_calls={"openai": 75, "anthropic": 25},
            strategy_costs={"clarity": 5.0, "completeness": 5.5},
            strategy_tokens={"clarity": 25000, "completeness": 25000},
            strategy_calls={"clarity": 50, "completeness": 50},
            hourly_cost=0.44,
            daily_cost=10.50,
            monthly_projection=315.0,
            cost_per_document=0.105,
            cost_per_token=0.00021,
            cost_per_improvement_point=1.05
        )
        
        assert metrics.total_cost == 10.50
        assert metrics.token_count == 50000
        assert metrics.api_calls == 100
        assert metrics.provider_costs["openai"] == 8.0
        assert metrics.monthly_projection == 315.0
        
    def test_to_dict(self):
        """Test converting metrics to dictionary."""
        metrics = CostMetrics(
            total_cost=5.0,
            token_count=10000,
            api_calls=50
        )
        
        data = metrics.to_dict()
        
        assert data["total_cost"] == 5.0
        assert data["token_count"] == 10000
        assert data["api_calls"] == 50
        assert "provider_costs" in data
        assert "strategy_costs" in data
        assert "hourly_cost" in data


class TestOptimizationResult:
    """Test OptimizationResult dataclass."""
    
    def test_initialization(self):
        """Test optimization result initialization."""
        result = OptimizationResult(
            optimized=True,
            original_cost=1.0,
            optimized_cost=0.7,
            savings=0.3,
            savings_percentage=30.0,
            optimization_strategy="cheaper_models+batch",
            recommendations=["Use GPT-3.5 instead of GPT-4", "Enable batching"]
        )
        
        assert result.optimized is True
        assert result.original_cost == 1.0
        assert result.optimized_cost == 0.7
        assert result.savings == 0.3
        assert result.savings_percentage == 30.0
        assert len(result.recommendations) == 2
        
    def test_to_dict(self):
        """Test converting result to dictionary."""
        result = OptimizationResult(
            optimized=True,
            original_cost=1.0,
            optimized_cost=0.8,
            savings=0.2,
            savings_percentage=20.0,
            optimization_strategy="caching",
            recommendations=["Enable caching"]
        )
        
        data = result.to_dict()
        
        assert data["optimized"] is True
        assert data["savings"] == 0.2
        assert data["optimization_strategy"] == "caching"
        assert len(data["recommendations"]) == 1


class TestCostOptimizer:
    """Test CostOptimizer class."""
    
    @pytest.fixture
    def optimizer(self):
        """Create cost optimizer instance."""
        config = PipelineConfig()
        return CostOptimizer(config)
        
    def test_initialization(self, optimizer):
        """Test optimizer initialization."""
        assert optimizer.total_cost == 0.0
        assert optimizer.total_tokens == 0
        assert optimizer.total_calls == 0
        assert optimizer.documents_processed == 0
        assert optimizer.daily_budget == 10.0
        assert optimizer.monthly_budget == 200.0
        
    def test_calculate_cost_basic(self, optimizer):
        """Test basic cost calculation."""
        # 1000 characters = ~250 tokens
        cost = optimizer.calculate_cost(
            content_length=1000,
            provider="openai",
            model="gpt-3.5-turbo"
        )
        
        assert cost > 0
        assert cost < 0.01  # Should be small for GPT-3.5
        
    def test_calculate_cost_with_strategy(self, optimizer):
        """Test cost calculation with strategy multiplier."""
        base_cost = optimizer.calculate_cost(
            content_length=1000,
            provider="openai",
            model="gpt-3.5-turbo"
        )
        
        # Completeness strategy has 1.5x multiplier
        strategy_cost = optimizer.calculate_cost(
            content_length=1000,
            strategy_name="completeness",
            provider="openai",
            model="gpt-3.5-turbo"
        )
        
        assert strategy_cost > base_cost
        
    def test_calculate_cost_expensive_model(self, optimizer):
        """Test cost calculation for expensive models."""
        cheap_cost = optimizer.calculate_cost(
            content_length=1000,
            provider="openai",
            model="gpt-3.5-turbo"
        )
        
        expensive_cost = optimizer.calculate_cost(
            content_length=1000,
            provider="openai",
            model="gpt-4"
        )
        
        assert expensive_cost > cheap_cost * 5  # GPT-4 is much more expensive
        
    def test_calculate_cost_local_model(self, optimizer):
        """Test cost calculation for local models."""
        cost = optimizer.calculate_cost(
            content_length=10000,
            provider="local",
            model="default"
        )
        
        assert cost == 0.0  # Local models have no cost
        
    def test_track_usage(self, optimizer):
        """Test tracking LLM usage."""
        optimizer.track_usage(
            cost=0.05,
            tokens=1000,
            provider="openai",
            model="gpt-3.5-turbo",
            strategy="clarity"
        )
        
        assert optimizer.total_cost == 0.05
        assert optimizer.total_tokens == 1000
        assert optimizer.total_calls == 1
        assert "openai" in optimizer.provider_usage
        assert optimizer.provider_usage["openai"]["cost"] == 0.05
        assert "clarity" in optimizer.strategy_usage
        assert optimizer.strategy_usage["clarity"]["cost"] == 0.05
        
    def test_track_usage_multiple(self, optimizer):
        """Test tracking multiple usage events."""
        optimizer.track_usage(0.05, 1000, "openai", "gpt-3.5", "clarity")
        optimizer.track_usage(0.10, 2000, "anthropic", "claude", "completeness")
        optimizer.track_usage(0.03, 500, "openai", "gpt-3.5", "clarity")
        
        assert optimizer.total_cost == 0.18
        assert optimizer.total_tokens == 3500
        assert optimizer.total_calls == 3
        
        assert optimizer.provider_usage["openai"]["cost"] == 0.08
        assert optimizer.provider_usage["anthropic"]["cost"] == 0.10
        assert optimizer.strategy_usage["clarity"]["cost"] == 0.08
        assert optimizer.strategy_usage["completeness"]["cost"] == 0.10
        
    def test_budget_tracking(self, optimizer):
        """Test budget tracking and warnings."""
        optimizer.daily_budget = 1.0
        optimizer.monthly_budget = 10.0
        
        # Track usage approaching daily limit
        optimizer.track_usage(0.85, 10000, "openai", "gpt-4", "clarity")
        
        assert optimizer.daily_spent == 0.85
        assert optimizer.monthly_spent == 0.85
        
    def test_optimize_cost_low_quality(self, optimizer):
        """Test cost optimization for low quality threshold."""
        content = "Test content " * 100
        strategies = ["clarity", "completeness", "readability"]
        
        result = optimizer.optimize_cost(
            content=content,
            strategies=strategies,
            quality_threshold=0.6
        )
        
        assert isinstance(result, OptimizationResult)
        assert result.optimized is True
        assert result.optimized_cost < result.original_cost
        assert "cheaper_models" in result.optimization_strategy
        assert len(result.recommendations) > 0
        
    def test_optimize_cost_high_quality(self, optimizer):
        """Test cost optimization for high quality threshold."""
        content = "Test content " * 100
        strategies = ["clarity", "completeness", "accuracy"]
        
        result = optimizer.optimize_cost(
            content=content,
            strategies=strategies,
            quality_threshold=0.95
        )
        
        assert isinstance(result, OptimizationResult)
        # High quality may not allow much optimization
        assert "progressive enhancement" in " ".join(result.recommendations)
        
    def test_optimize_cost_batch_processing(self, optimizer):
        """Test optimization with batch processing."""
        content = "Long content " * 500  # >5000 chars
        strategies = ["clarity"]
        
        result = optimizer.optimize_cost(
            content=content,
            strategies=strategies,
            quality_threshold=0.8
        )
        
        assert result.optimized is True
        assert "batch" in result.optimization_strategy or result.optimized_cost < result.original_cost
        
    def test_optimize_cost_caching(self, optimizer):
        """Test optimization result caching."""
        content = "Test content"
        strategies = ["clarity"]
        
        # First call
        result1 = optimizer.optimize_cost(content, strategies, 0.8)
        
        # Second call (should use cache)
        result2 = optimizer.optimize_cost(content, strategies, 0.8)
        
        assert result1.optimized_cost == result2.optimized_cost
        assert result1.optimization_strategy == result2.optimization_strategy
        
    def test_get_metrics(self, optimizer):
        """Test getting comprehensive metrics."""
        # Add some usage data
        optimizer.track_usage(0.05, 1000, "openai", "gpt-3.5", "clarity")
        optimizer.track_usage(0.10, 2000, "anthropic", "claude", "completeness")
        optimizer.documents_processed = 2
        
        metrics = optimizer.get_metrics()
        
        assert isinstance(metrics, CostMetrics)
        assert metrics.total_cost == 0.15
        assert metrics.token_count == 3000
        assert metrics.api_calls == 2
        assert metrics.cost_per_document == 0.075
        assert "openai" in metrics.provider_costs
        assert "clarity" in metrics.strategy_costs
        
    def test_check_budget_within_limits(self, optimizer):
        """Test budget checking within limits."""
        optimizer.daily_budget = 10.0
        optimizer.monthly_budget = 200.0
        optimizer.daily_spent = 5.0
        optimizer.monthly_spent = 100.0
        
        # Should pass
        assert optimizer.check_budget(2.0) is True
        
    def test_check_budget_exceeds_daily(self, optimizer):
        """Test budget checking exceeding daily limit."""
        optimizer.daily_budget = 10.0
        optimizer.daily_spent = 9.0
        
        # Should fail
        assert optimizer.check_budget(2.0) is False
        
    def test_check_budget_exceeds_monthly(self, optimizer):
        """Test budget checking exceeding monthly limit."""
        optimizer.monthly_budget = 200.0
        optimizer.monthly_spent = 195.0
        
        # Should fail
        assert optimizer.check_budget(10.0) is False
        
    def test_check_budget_per_document(self, optimizer):
        """Test per-document budget limit."""
        optimizer.config.max_cost_per_document = 0.50
        
        # Should fail
        assert optimizer.check_budget(0.75) is False
        
    def test_get_cost_breakdown(self, optimizer):
        """Test getting cost breakdown."""
        # Add usage data
        optimizer.track_usage(0.05, 1000, "openai", "gpt-3.5", "clarity")
        optimizer.track_usage(0.10, 2000, "anthropic", "claude", "completeness")
        optimizer.documents_processed = 2
        
        breakdown = optimizer.get_cost_breakdown()
        
        assert breakdown["total"]["cost"] == 0.15
        assert breakdown["total"]["tokens"] == 3000
        assert breakdown["total"]["documents"] == 2
        assert "openai" in breakdown["by_provider"]
        assert "clarity" in breakdown["by_strategy"]
        assert "daily" in breakdown["budget"]
        assert "monthly" in breakdown["budget"]
        assert breakdown["averages"]["per_document"] == 0.075
        
    def test_suggest_optimizations_no_data(self, optimizer):
        """Test optimization suggestions with no data."""
        suggestions = optimizer.suggest_optimizations()
        
        assert isinstance(suggestions, list)
        # Should suggest enabling features
        assert any("caching" in s.lower() for s in suggestions)
        
    def test_suggest_optimizations_with_usage(self, optimizer):
        """Test optimization suggestions with usage data."""
        # Simulate expensive usage
        optimizer.provider_usage["openai"] = {"cost": 10.0, "tokens": 50000, "calls": 100}
        optimizer.strategy_usage["completeness"] = {"cost": 5.0, "tokens": 25000, "calls": 20}
        optimizer.total_tokens = 50000
        optimizer.total_calls = 100
        optimizer.total_cost = 10.0
        optimizer.documents_processed = 20
        
        suggestions = optimizer.suggest_optimizations()
        
        assert isinstance(suggestions, list)
        assert len(suggestions) > 0
        # Should suggest various optimizations
        
    def test_identify_essential_strategies(self, optimizer):
        """Test identifying essential strategies."""
        strategies = ["clarity", "completeness", "consistency", "accuracy", "readability"]
        
        # High quality - need all
        essential_high = optimizer._identify_essential_strategies(strategies, 0.95)
        assert len(essential_high) == len(strategies)
        
        # Medium quality - skip some
        essential_medium = optimizer._identify_essential_strategies(strategies, 0.85)
        assert len(essential_medium) < len(strategies)
        assert "consistency" not in [s.lower() for s in essential_medium]
        
        # Low quality - only basics
        essential_low = optimizer._identify_essential_strategies(strategies, 0.6)
        assert len(essential_low) < 3
        
    def test_calculate_hourly_average(self, optimizer):
        """Test calculating hourly average cost."""
        # Add hourly data
        now = datetime.now()
        optimizer.hourly_costs = [
            (now - timedelta(hours=2), 0.5),
            (now - timedelta(hours=1), 0.3),
            (now, 0.4)
        ]
        
        avg = optimizer._calculate_hourly_average()
        assert avg == 0.4  # Average of recent costs
        
    def test_calculate_daily_average(self, optimizer):
        """Test calculating daily average cost."""
        # Add daily data
        today = datetime.now()
        yesterday = today - timedelta(days=1)
        
        optimizer.hourly_costs = [
            (yesterday.replace(hour=10), 1.0),
            (yesterday.replace(hour=14), 2.0),
            (today.replace(hour=9), 0.5),
            (today.replace(hour=15), 1.5)
        ]
        
        avg = optimizer._calculate_daily_average()
        assert avg > 0  # Should calculate average per day
        
    def test_export_cost_report(self, optimizer):
        """Test exporting cost report."""
        # Add some data
        optimizer.track_usage(0.05, 1000, "openai", "gpt-3.5", "clarity")
        optimizer.documents_processed = 1
        
        with tempfile.TemporaryDirectory() as tmpdir:
            report_path = Path(tmpdir) / "cost_report.json"
            optimizer.export_cost_report(report_path)
            
            assert report_path.exists()
            
            with open(report_path) as f:
                data = json.load(f)
            
            assert "summary" in data
            assert "metrics" in data
            assert "optimizations" in data
            assert "timestamp" in data
            
    def test_get_total_cost(self, optimizer):
        """Test getting total cost."""
        optimizer.track_usage(0.05, 1000, "openai", "gpt-3.5", "clarity")
        optimizer.track_usage(0.10, 2000, "anthropic", "claude", "completeness")
        
        assert optimizer.get_total_cost() == 0.15
        
    def test_reset_metrics(self, optimizer):
        """Test resetting metrics."""
        # Add data
        optimizer.track_usage(0.05, 1000, "openai", "gpt-3.5", "clarity")
        optimizer.documents_processed = 5
        
        # Reset
        optimizer.reset_metrics()
        
        assert optimizer.total_cost == 0.0
        assert optimizer.total_tokens == 0
        assert optimizer.total_calls == 0
        assert optimizer.documents_processed == 0
        assert len(optimizer.provider_usage) == 0
        assert len(optimizer.strategy_usage) == 0
        
    def test_budget_reset_daily(self, optimizer):
        """Test daily budget reset."""
        optimizer.daily_spent = 5.0
        optimizer.budget_reset_time = datetime.now() - timedelta(days=1)
        
        # Check budget should trigger reset
        optimizer._check_budget_resets()
        
        assert optimizer.daily_spent == 0.0
        
    def test_budget_reset_monthly(self, optimizer):
        """Test monthly budget reset."""
        optimizer.monthly_spent = 150.0
        # Set to last month
        last_month = datetime.now().replace(day=1) - timedelta(days=1)
        optimizer.budget_reset_time = last_month
        
        # Check budget should trigger reset
        optimizer._check_budget_resets()
        
        assert optimizer.monthly_spent == 0.0