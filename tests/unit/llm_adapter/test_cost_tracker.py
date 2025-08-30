"""
Tests for M008 LLM Adapter cost tracking functionality.

Tests cost limits enforcement, usage recording, budget alerts,
and usage statistics generation.
"""

import pytest
import asyncio
from decimal import Decimal
from datetime import datetime, date, timedelta
from pathlib import Path
import tempfile
import json

from devdocai.llm_adapter.config import CostLimits, UsageRecord
from devdocai.llm_adapter.cost_tracker import CostTracker, CostAlert, UsageStats


class TestCostTracker:
    """Test cost tracking functionality."""
    
    @pytest.fixture
    def temp_storage(self):
        """Create temporary storage file."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
            yield Path(f.name)
        # Cleanup handled by tempfile
    
    @pytest.fixture
    def cost_limits(self):
        """Create test cost limits."""
        return CostLimits(
            daily_limit_usd=Decimal("5.00"),
            monthly_limit_usd=Decimal("100.00"),
            per_request_limit_usd=Decimal("1.00"),
            daily_warning_threshold=0.8,
            monthly_warning_threshold=0.9,
            emergency_stop_enabled=True,
            emergency_threshold=0.95
        )
    
    @pytest.fixture
    def tracker(self, cost_limits, temp_storage):
        """Create cost tracker with temporary storage."""
        return CostTracker(cost_limits, temp_storage)
    
    def test_tracker_initialization(self, tracker, cost_limits):
        """Test cost tracker initialization."""
        assert tracker.cost_limits == cost_limits
        assert tracker.storage_path.exists()
        assert len(tracker._usage_records) == 0
    
    @pytest.mark.asyncio
    async def test_record_usage_basic(self, tracker):
        """Test basic usage recording."""
        usage_record = UsageRecord(
            timestamp=datetime.utcnow(),
            provider="openai",
            model="gpt-3.5-turbo",
            input_tokens=100,
            output_tokens=50,
            input_cost=Decimal("0.0005"),
            output_cost=Decimal("0.0008"),
            total_cost=Decimal("0.0013"),
            request_id="test-001",
            response_time_seconds=1.2,
            success=True
        )
        
        alerts = await tracker.record_usage(usage_record)
        
        assert len(tracker._usage_records) == 1
        assert tracker._usage_records[0] == usage_record
        assert len(alerts) == 0  # No alerts for small amount
        
        # Check daily total
        today = date.today()
        daily_cost = tracker.get_daily_cost(today)
        assert daily_cost == Decimal("0.0013")
    
    @pytest.mark.asyncio
    async def test_record_multiple_usage(self, tracker):
        """Test recording multiple usage records."""
        records = []
        total_cost = Decimal("0")
        
        for i in range(5):
            cost = Decimal("0.10")
            record = UsageRecord(
                timestamp=datetime.utcnow(),
                provider="openai",
                model="gpt-3.5-turbo",
                input_tokens=50,
                output_tokens=25,
                input_cost=cost / 2,
                output_cost=cost / 2,
                total_cost=cost,
                request_id=f"test-{i:03d}",
                response_time_seconds=1.0,
                success=True
            )
            records.append(record)
            total_cost += cost
            await tracker.record_usage(record)
        
        assert len(tracker._usage_records) == 5
        
        # Check daily total
        daily_cost = tracker.get_daily_cost()
        assert daily_cost == total_cost
        
        # Check monthly total
        monthly_cost = tracker.get_monthly_cost()
        assert monthly_cost == total_cost
    
    @pytest.mark.asyncio
    async def test_daily_warning_alert(self, tracker):
        """Test daily warning threshold alert."""
        # Daily limit is $5.00, warning at 80% = $4.00
        usage_record = UsageRecord(
            timestamp=datetime.utcnow(),
            provider="openai",
            model="gpt-4",
            input_tokens=1000,
            output_tokens=500,
            input_cost=Decimal("2.00"),
            output_cost=Decimal("2.10"),
            total_cost=Decimal("4.10"),  # Exceeds 80% of $5.00
            request_id="warning-test",
            response_time_seconds=2.0,
            success=True
        )
        
        alerts = await tracker.record_usage(usage_record)
        
        assert len(alerts) == 1
        alert = alerts[0]
        assert alert.alert_type == "warning"
        assert alert.threshold_type == "daily"
        assert alert.current_amount == Decimal("4.10")
        assert alert.percentage >= 0.8
    
    @pytest.mark.asyncio
    async def test_daily_emergency_alert(self, tracker):
        """Test daily emergency threshold alert."""
        # Daily limit is $5.00, emergency at 95% = $4.75
        usage_record = UsageRecord(
            timestamp=datetime.utcnow(),
            provider="openai",
            model="gpt-4",
            input_tokens=2000,
            output_tokens=1000,
            input_cost=Decimal("2.40"),
            output_cost=Decimal("2.40"),
            total_cost=Decimal("4.80"),  # Exceeds 95% of $5.00
            request_id="emergency-test",
            response_time_seconds=3.0,
            success=True
        )
        
        alerts = await tracker.record_usage(usage_record)
        
        # Should get both warning and emergency alerts
        assert len(alerts) >= 1
        emergency_alerts = [a for a in alerts if a.alert_type == "emergency"]
        assert len(emergency_alerts) == 1
        
        alert = emergency_alerts[0]
        assert alert.threshold_type == "daily"
        assert alert.percentage >= 0.95
    
    @pytest.mark.asyncio
    async def test_monthly_alert(self, tracker):
        """Test monthly alert threshold."""
        # Add usage to reach monthly warning (90% of $100 = $90)
        usage_record = UsageRecord(
            timestamp=datetime.utcnow(),
            provider="anthropic",
            model="claude-3-opus",
            input_tokens=10000,
            output_tokens=5000,
            input_cost=Decimal("45.00"),
            output_cost=Decimal("45.50"),
            total_cost=Decimal("90.50"),
            request_id="monthly-test",
            response_time_seconds=5.0,
            success=True
        )
        
        alerts = await tracker.record_usage(usage_record)
        
        monthly_alerts = [a for a in alerts if a.threshold_type == "monthly"]
        assert len(monthly_alerts) >= 1
        
        alert = monthly_alerts[0]
        assert alert.alert_type in ["warning", "emergency"]
        assert alert.current_amount == Decimal("90.50")
    
    def test_can_afford_request(self, tracker):
        """Test request affordability checking."""
        # Small request should be affordable
        can_afford, reason = tracker.can_afford_request(Decimal("0.01"))
        assert can_afford is True
        assert reason is None
        
        # Request exceeding per-request limit
        can_afford, reason = tracker.can_afford_request(Decimal("2.00"))  # Limit is $1.00
        assert can_afford is False
        assert "per-request limit" in reason
        
        # Request that would exceed daily limit
        can_afford, reason = tracker.can_afford_request(Decimal("6.00"))  # Daily limit is $5.00
        assert can_afford is False
        assert "daily limit" in reason
        
        # Request that would exceed monthly limit
        can_afford, reason = tracker.can_afford_request(Decimal("101.00"))  # Monthly limit is $100.00
        assert can_afford is False
        assert "monthly limit" in reason
    
    @pytest.mark.asyncio
    async def test_can_afford_with_existing_usage(self, tracker):
        """Test affordability with existing usage."""
        # Add some existing usage
        usage_record = UsageRecord(
            timestamp=datetime.utcnow(),
            provider="openai",
            model="gpt-3.5-turbo",
            input_tokens=500,
            output_tokens=250,
            input_cost=Decimal("1.50"),
            output_cost=Decimal("1.50"),
            total_cost=Decimal("3.00"),
            request_id="existing-usage",
            response_time_seconds=2.0,
            success=True
        )
        await tracker.record_usage(usage_record)
        
        # Now check if we can afford another $2.50 (would total $5.50 > $5.00 limit)
        can_afford, reason = tracker.can_afford_request(Decimal("2.50"))
        assert can_afford is False
        assert "daily limit" in reason
        
        # But we should be able to afford $1.50 (would total $4.50 < $5.00 limit)
        can_afford, reason = tracker.can_afford_request(Decimal("1.50"))
        assert can_afford is True
        assert reason is None
    
    def test_emergency_brake(self, tracker):
        """Test emergency brake functionality."""
        # Add usage close to emergency threshold
        tracker._daily_costs[date.today().isoformat()] = Decimal("4.70")  # 94% of $5.00
        
        # Request that would push over emergency threshold
        can_afford, reason = tracker.can_afford_request(Decimal("0.10"))  # Would be 96%
        assert can_afford is False
        assert "Emergency brake" in reason
    
    def test_get_usage_stats(self, tracker):
        """Test usage statistics generation."""
        # Add some test records
        today = datetime.utcnow()
        yesterday = today - timedelta(days=1)
        
        records = [
            UsageRecord(
                timestamp=today,
                provider="openai",
                model="gpt-3.5-turbo",
                input_tokens=100,
                output_tokens=50,
                input_cost=Decimal("0.05"),
                output_cost=Decimal("0.08"),
                total_cost=Decimal("0.13"),
                request_id="stats-1",
                response_time_seconds=1.0,
                success=True
            ),
            UsageRecord(
                timestamp=today,
                provider="anthropic",
                model="claude-3-sonnet",
                input_tokens=200,
                output_tokens=100,
                input_cost=Decimal("0.60"),
                output_cost=Decimal("1.50"),
                total_cost=Decimal("2.10"),
                request_id="stats-2",
                response_time_seconds=2.0,
                success=True
            ),
            UsageRecord(
                timestamp=yesterday,
                provider="openai",
                model="gpt-4",
                input_tokens=150,
                output_tokens=75,
                input_cost=Decimal("4.50"),
                output_cost=Decimal("9.00"),
                total_cost=Decimal("13.50"),
                request_id="stats-3",
                response_time_seconds=3.0,
                success=True
            )
        ]
        
        tracker._usage_records = records
        
        # Get stats for last 30 days
        stats = tracker.get_usage_stats(days=30)
        
        assert stats.total_requests == 3
        assert stats.total_tokens == (100+50) + (200+100) + (150+75)  # 675
        assert stats.total_cost == Decimal("0.13") + Decimal("2.10") + Decimal("13.50")
        
        # Check provider breakdown
        assert "openai" in stats.provider_breakdown
        assert "anthropic" in stats.provider_breakdown
        assert stats.provider_breakdown["openai"]["requests"] == 2
        assert stats.provider_breakdown["anthropic"]["requests"] == 1
        
        # Check model breakdown
        assert "gpt-3.5-turbo" in stats.model_breakdown
        assert "claude-3-sonnet" in stats.model_breakdown
        assert "gpt-4" in stats.model_breakdown
    
    def test_get_usage_stats_with_filter(self, tracker):
        """Test usage statistics with provider filter."""
        # Add mixed provider records
        records = [
            UsageRecord(
                timestamp=datetime.utcnow(),
                provider="openai",
                model="gpt-3.5-turbo",
                input_tokens=100,
                output_tokens=50,
                input_cost=Decimal("0.05"),
                output_cost=Decimal("0.08"),
                total_cost=Decimal("0.13"),
                request_id="filter-1",
                response_time_seconds=1.0,
                success=True
            ),
            UsageRecord(
                timestamp=datetime.utcnow(),
                provider="anthropic",
                model="claude-3-sonnet",
                input_tokens=200,
                output_tokens=100,
                input_cost=Decimal("0.60"),
                output_cost=Decimal("1.50"),
                total_cost=Decimal("2.10"),
                request_id="filter-2",
                response_time_seconds=2.0,
                success=True
            )
        ]
        
        tracker._usage_records = records
        
        # Filter to only OpenAI
        stats = tracker.get_usage_stats(days=30, provider_filter="openai")
        
        assert stats.total_requests == 1
        assert stats.total_cost == Decimal("0.13")
        assert "openai" in stats.provider_breakdown
        assert "anthropic" not in stats.provider_breakdown
    
    @pytest.mark.asyncio
    async def test_storage_persistence(self, cost_limits, temp_storage):
        """Test data persistence to storage."""
        # Create tracker and add data
        tracker1 = CostTracker(cost_limits, temp_storage)
        
        usage_record = UsageRecord(
            timestamp=datetime.utcnow(),
            provider="openai",
            model="gpt-3.5-turbo",
            input_tokens=100,
            output_tokens=50,
            input_cost=Decimal("0.05"),
            output_cost=Decimal("0.08"),
            total_cost=Decimal("0.13"),
            request_id="persist-test",
            response_time_seconds=1.0,
            success=True
        )
        
        await tracker1.record_usage(usage_record)
        
        # Create new tracker with same storage
        tracker2 = CostTracker(cost_limits, temp_storage)
        
        # Should load previous data
        assert len(tracker2._usage_records) == 1
        assert tracker2._usage_records[0].request_id == "persist-test"
        assert tracker2.get_daily_cost() == Decimal("0.13")
    
    def test_cleanup_old_data(self, tracker):
        """Test cleanup of old data."""
        # Add old records (95 days ago)
        old_date = datetime.utcnow() - timedelta(days=95)
        old_record = UsageRecord(
            timestamp=old_date,
            provider="openai",
            model="gpt-3.5-turbo",
            input_tokens=100,
            output_tokens=50,
            input_cost=Decimal("0.05"),
            output_cost=Decimal("0.08"),
            total_cost=Decimal("0.13"),
            request_id="old-record",
            response_time_seconds=1.0,
            success=True
        )
        
        # Add recent record
        recent_record = UsageRecord(
            timestamp=datetime.utcnow(),
            provider="openai",
            model="gpt-3.5-turbo",
            input_tokens=100,
            output_tokens=50,
            input_cost=Decimal("0.05"),
            output_cost=Decimal("0.08"),
            total_cost=Decimal("0.13"),
            request_id="recent-record",
            response_time_seconds=1.0,
            success=True
        )
        
        tracker._usage_records = [old_record, recent_record]
        
        # Trigger cleanup
        tracker._cleanup_old_data()
        
        # Only recent record should remain
        assert len(tracker._usage_records) == 1
        assert tracker._usage_records[0].request_id == "recent-record"
    
    def test_alert_deduplication(self, tracker):
        """Test that duplicate alerts are not sent frequently."""
        alert_key = "daily_warning_2024-01-01"
        
        # First check should allow alert
        assert tracker._should_send_alert(alert_key) is True
        
        # Mark as sent
        tracker._alerts_sent[alert_key] = datetime.utcnow()
        
        # Immediate check should not allow duplicate
        assert tracker._should_send_alert(alert_key) is False
        
        # Check with old timestamp should allow
        old_time = datetime.utcnow() - timedelta(hours=2)
        tracker._alerts_sent[alert_key] = old_time
        assert tracker._should_send_alert(alert_key) is True


class TestUsageStats:
    """Test usage statistics functionality."""
    
    def test_usage_stats_initialization(self):
        """Test usage stats initialization."""
        stats = UsageStats()
        
        assert stats.total_requests == 0
        assert stats.total_tokens == 0
        assert stats.total_cost == Decimal("0")
        assert len(stats.provider_breakdown) == 0
        assert len(stats.model_breakdown) == 0
        assert len(stats.daily_costs) == 0


class TestCostAlert:
    """Test cost alert functionality."""
    
    def test_cost_alert_creation(self):
        """Test creating cost alerts."""
        alert = CostAlert(
            alert_type="warning",
            threshold_type="daily",
            current_amount=Decimal("4.00"),
            limit=Decimal("5.00"),
            percentage=0.8,
            message="Daily spending warning"
        )
        
        assert alert.alert_type == "warning"
        assert alert.threshold_type == "daily"
        assert alert.current_amount == Decimal("4.00")
        assert alert.limit == Decimal("5.00")
        assert alert.percentage == 0.8
        assert alert.message == "Daily spending warning"
        assert alert.timestamp is not None