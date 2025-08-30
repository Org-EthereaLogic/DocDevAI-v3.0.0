"""
M008: Cost Tracking and Budget Management.

Tracks LLM usage costs across all providers with daily/monthly budget limits,
cost alerts, and usage analytics.
"""

import asyncio
import json
import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime, date, timedelta
from decimal import Decimal
from collections import defaultdict
from pathlib import Path

from .config import CostLimits, UsageRecord

logger = logging.getLogger(__name__)


class UsageStats:
    """Statistics for LLM usage and costs."""
    
    def __init__(self):
        self.total_requests: int = 0
        self.total_tokens: int = 0
        self.total_cost: Decimal = Decimal("0")
        self.provider_breakdown: Dict[str, Dict[str, Decimal]] = defaultdict(
            lambda: {"requests": 0, "tokens": 0, "cost": Decimal("0")}
        )
        self.model_breakdown: Dict[str, Dict[str, Decimal]] = defaultdict(
            lambda: {"requests": 0, "tokens": 0, "cost": Decimal("0")}
        )
        self.daily_costs: Dict[str, Decimal] = defaultdict(lambda: Decimal("0"))
        self.hourly_costs: Dict[str, Decimal] = defaultdict(lambda: Decimal("0"))


class CostAlert:
    """Cost alert information."""
    
    def __init__(
        self, 
        alert_type: str,
        threshold_type: str,
        current_amount: Decimal,
        limit: Decimal,
        percentage: float,
        message: str
    ):
        self.alert_type = alert_type  # warning, emergency, limit_exceeded
        self.threshold_type = threshold_type  # daily, monthly, per_request
        self.current_amount = current_amount
        self.limit = limit
        self.percentage = percentage
        self.message = message
        self.timestamp = datetime.utcnow()


class CostTracker:
    """
    Cost tracking and budget management for LLM usage.
    
    Tracks costs across all providers with configurable daily/monthly limits,
    automated alerts, and detailed usage analytics.
    """
    
    def __init__(self, cost_limits: CostLimits, storage_path: Optional[Path] = None):
        """
        Initialize cost tracker.
        
        Args:
            cost_limits: Cost configuration and limits
            storage_path: Path to store usage data (defaults to ./data/usage.json)
        """
        self.cost_limits = cost_limits
        self.storage_path = storage_path or Path("./data/usage.json")
        
        # Create storage directory if needed
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        
        # In-memory usage tracking
        self._usage_records: List[UsageRecord] = []
        self._daily_costs: Dict[str, Decimal] = defaultdict(lambda: Decimal("0"))  # date -> cost
        self._monthly_costs: Dict[str, Decimal] = defaultdict(lambda: Decimal("0"))  # year-month -> cost
        
        # Alert history
        self._alerts_sent: Dict[str, datetime] = {}  # alert_key -> last_sent_time
        
        # Load existing data
        self._load_usage_data()
        
        # Cleanup old data on startup
        self._cleanup_old_data()
    
    async def record_usage(self, usage_record: UsageRecord) -> List[CostAlert]:
        """
        Record LLM usage and check for budget alerts.
        
        Args:
            usage_record: Usage information to record
            
        Returns:
            List of cost alerts triggered by this usage
        """
        # Add to records
        self._usage_records.append(usage_record)
        
        # Update daily and monthly totals
        usage_date = usage_record.timestamp.date()
        usage_month = usage_date.strftime("%Y-%m")
        
        self._daily_costs[usage_date.isoformat()] += usage_record.total_cost
        self._monthly_costs[usage_month] += usage_record.total_cost
        
        # Check for alerts
        alerts = self._check_cost_alerts()
        
        # Save updated data
        await self._save_usage_data()
        
        return alerts
    
    def get_daily_cost(self, target_date: Optional[date] = None) -> Decimal:
        """Get total cost for a specific day."""
        if target_date is None:
            target_date = date.today()
        
        return self._daily_costs.get(target_date.isoformat(), Decimal("0"))
    
    def get_monthly_cost(self, target_month: Optional[str] = None) -> Decimal:
        """Get total cost for a specific month (YYYY-MM format)."""
        if target_month is None:
            target_month = date.today().strftime("%Y-%m")
        
        return self._monthly_costs.get(target_month, Decimal("0"))
    
    def get_usage_stats(
        self, 
        days: int = 30,
        provider_filter: Optional[str] = None
    ) -> UsageStats:
        """
        Get usage statistics for the specified period.
        
        Args:
            days: Number of days to include (from today)
            provider_filter: Filter to specific provider
            
        Returns:
            Usage statistics
        """
        stats = UsageStats()
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        # Filter records
        filtered_records = [
            record for record in self._usage_records
            if (record.timestamp >= cutoff_date and
                (provider_filter is None or record.provider == provider_filter))
        ]
        
        # Calculate statistics
        for record in filtered_records:
            stats.total_requests += 1
            stats.total_tokens += record.input_tokens + record.output_tokens
            stats.total_cost += record.total_cost
            
            # Provider breakdown
            stats.provider_breakdown[record.provider]["requests"] += 1
            stats.provider_breakdown[record.provider]["tokens"] += (
                record.input_tokens + record.output_tokens
            )
            stats.provider_breakdown[record.provider]["cost"] += record.total_cost
            
            # Model breakdown
            stats.model_breakdown[record.model]["requests"] += 1
            stats.model_breakdown[record.model]["tokens"] += (
                record.input_tokens + record.output_tokens
            )
            stats.model_breakdown[record.model]["cost"] += record.total_cost
            
            # Daily breakdown
            day_key = record.timestamp.date().isoformat()
            stats.daily_costs[day_key] += record.total_cost
            
            # Hourly breakdown
            hour_key = record.timestamp.strftime("%Y-%m-%d %H:00")
            stats.hourly_costs[hour_key] += record.total_cost
        
        return stats
    
    def can_afford_request(self, estimated_cost: Decimal) -> Tuple[bool, Optional[str]]:
        """
        Check if a request can be afforded within current limits.
        
        Args:
            estimated_cost: Estimated cost of the request
            
        Returns:
            Tuple of (can_afford, reason_if_not)
        """
        today = date.today()
        current_month = today.strftime("%Y-%m")
        
        # Check per-request limit
        if estimated_cost > self.cost_limits.per_request_limit_usd:
            return False, f"Request cost ${estimated_cost} exceeds per-request limit ${self.cost_limits.per_request_limit_usd}"
        
        # Check daily limit
        current_daily = self.get_daily_cost(today)
        if current_daily + estimated_cost > self.cost_limits.daily_limit_usd:
            return False, f"Request would exceed daily limit (${current_daily + estimated_cost} > ${self.cost_limits.daily_limit_usd})"
        
        # Check monthly limit
        current_monthly = self.get_monthly_cost(current_month)
        if current_monthly + estimated_cost > self.cost_limits.monthly_limit_usd:
            return False, f"Request would exceed monthly limit (${current_monthly + estimated_cost} > ${self.cost_limits.monthly_limit_usd})"
        
        # Emergency brake check
        if self.cost_limits.emergency_stop_enabled:
            daily_threshold = self.cost_limits.daily_limit_usd * Decimal(str(self.cost_limits.emergency_threshold))
            monthly_threshold = self.cost_limits.monthly_limit_usd * Decimal(str(self.cost_limits.emergency_threshold))
            
            if current_daily + estimated_cost > daily_threshold:
                return False, f"Emergency brake triggered - daily spending approaching limit"
            
            if current_monthly + estimated_cost > monthly_threshold:
                return False, f"Emergency brake triggered - monthly spending approaching limit"
        
        return True, None
    
    def _check_cost_alerts(self) -> List[CostAlert]:
        """Check for cost alert conditions and return new alerts."""
        alerts = []
        today = date.today()
        current_month = today.strftime("%Y-%m")
        
        # Get current costs
        daily_cost = self.get_daily_cost(today)
        monthly_cost = self.get_monthly_cost(current_month)
        
        # Check daily alerts
        daily_percentage = float(daily_cost / self.cost_limits.daily_limit_usd)
        
        # Daily warning threshold
        if daily_percentage >= self.cost_limits.daily_warning_threshold:
            alert_key = f"daily_warning_{today.isoformat()}"
            if self._should_send_alert(alert_key):
                alerts.append(CostAlert(
                    alert_type="warning",
                    threshold_type="daily",
                    current_amount=daily_cost,
                    limit=self.cost_limits.daily_limit_usd,
                    percentage=daily_percentage,
                    message=f"Daily spending is {daily_percentage:.1%} of limit (${daily_cost}/${self.cost_limits.daily_limit_usd})"
                ))
                self._alerts_sent[alert_key] = datetime.utcnow()
        
        # Daily emergency threshold
        if (self.cost_limits.emergency_stop_enabled and 
            daily_percentage >= self.cost_limits.emergency_threshold):
            alert_key = f"daily_emergency_{today.isoformat()}"
            if self._should_send_alert(alert_key):
                alerts.append(CostAlert(
                    alert_type="emergency",
                    threshold_type="daily", 
                    current_amount=daily_cost,
                    limit=self.cost_limits.daily_limit_usd,
                    percentage=daily_percentage,
                    message=f"EMERGENCY: Daily spending at {daily_percentage:.1%} of limit!"
                ))
                self._alerts_sent[alert_key] = datetime.utcnow()
        
        # Check monthly alerts
        monthly_percentage = float(monthly_cost / self.cost_limits.monthly_limit_usd)
        
        # Monthly warning threshold
        if monthly_percentage >= self.cost_limits.monthly_warning_threshold:
            alert_key = f"monthly_warning_{current_month}"
            if self._should_send_alert(alert_key):
                alerts.append(CostAlert(
                    alert_type="warning",
                    threshold_type="monthly",
                    current_amount=monthly_cost,
                    limit=self.cost_limits.monthly_limit_usd,
                    percentage=monthly_percentage,
                    message=f"Monthly spending is {monthly_percentage:.1%} of limit (${monthly_cost}/${self.cost_limits.monthly_limit_usd})"
                ))
                self._alerts_sent[alert_key] = datetime.utcnow()
        
        # Monthly emergency threshold
        if (self.cost_limits.emergency_stop_enabled and
            monthly_percentage >= self.cost_limits.emergency_threshold):
            alert_key = f"monthly_emergency_{current_month}"
            if self._should_send_alert(alert_key):
                alerts.append(CostAlert(
                    alert_type="emergency",
                    threshold_type="monthly",
                    current_amount=monthly_cost,
                    limit=self.cost_limits.monthly_limit_usd,
                    percentage=monthly_percentage,
                    message=f"EMERGENCY: Monthly spending at {monthly_percentage:.1%} of limit!"
                ))
                self._alerts_sent[alert_key] = datetime.utcnow()
        
        return alerts
    
    def _should_send_alert(self, alert_key: str) -> bool:
        """Check if an alert should be sent (not sent recently)."""
        last_sent = self._alerts_sent.get(alert_key)
        if last_sent is None:
            return True
        
        # Don't send same alert more than once per hour
        return (datetime.utcnow() - last_sent).seconds > 3600
    
    def _load_usage_data(self) -> None:
        """Load usage data from storage."""
        try:
            if not self.storage_path.exists():
                return
            
            with open(self.storage_path, 'r') as f:
                data = json.load(f)
            
            # Load usage records
            records_data = data.get('usage_records', [])
            for record_data in records_data:
                # Convert string timestamps back to datetime
                record_data['timestamp'] = datetime.fromisoformat(record_data['timestamp'])
                # Convert string decimals back to Decimal
                for field in ['input_cost', 'output_cost', 'total_cost']:
                    record_data[field] = Decimal(str(record_data[field]))
                
                self._usage_records.append(UsageRecord(**record_data))
            
            # Load aggregated costs
            daily_costs = data.get('daily_costs', {})
            for date_str, cost in daily_costs.items():
                self._daily_costs[date_str] = Decimal(str(cost))
            
            monthly_costs = data.get('monthly_costs', {})
            for month_str, cost in monthly_costs.items():
                self._monthly_costs[month_str] = Decimal(str(cost))
            
            # Load alert history
            alerts_sent = data.get('alerts_sent', {})
            for alert_key, timestamp_str in alerts_sent.items():
                self._alerts_sent[alert_key] = datetime.fromisoformat(timestamp_str)
            
            logger.info(f"Loaded {len(self._usage_records)} usage records from {self.storage_path}")
            
        except Exception as e:
            logger.error(f"Failed to load usage data: {e}")
    
    async def _save_usage_data(self) -> None:
        """Save usage data to storage."""
        try:
            # Prepare data for serialization
            data = {
                'usage_records': [],
                'daily_costs': {},
                'monthly_costs': {},
                'alerts_sent': {}
            }
            
            # Convert usage records
            for record in self._usage_records:
                record_dict = record.model_dump()
                # Convert datetime to string
                record_dict['timestamp'] = record.timestamp.isoformat()
                # Convert Decimal to string for JSON serialization
                for field in ['input_cost', 'output_cost', 'total_cost']:
                    record_dict[field] = str(record_dict[field])
                data['usage_records'].append(record_dict)
            
            # Convert daily costs
            for date_str, cost in self._daily_costs.items():
                data['daily_costs'][date_str] = str(cost)
            
            # Convert monthly costs
            for month_str, cost in self._monthly_costs.items():
                data['monthly_costs'][month_str] = str(cost)
            
            # Convert alert timestamps
            for alert_key, timestamp in self._alerts_sent.items():
                data['alerts_sent'][alert_key] = timestamp.isoformat()
            
            # Write to file atomically
            temp_path = self.storage_path.with_suffix('.tmp')
            with open(temp_path, 'w') as f:
                json.dump(data, f, indent=2)
            
            # Atomic rename
            temp_path.replace(self.storage_path)
            
        except Exception as e:
            logger.error(f"Failed to save usage data: {e}")
    
    def _cleanup_old_data(self) -> None:
        """Remove old usage records to prevent unbounded growth."""
        cutoff_date = datetime.utcnow() - timedelta(days=90)  # Keep 90 days
        
        original_count = len(self._usage_records)
        self._usage_records = [
            record for record in self._usage_records
            if record.timestamp >= cutoff_date
        ]
        
        removed_count = original_count - len(self._usage_records)
        if removed_count > 0:
            logger.info(f"Cleaned up {removed_count} old usage records")
        
        # Clean up old daily costs (keep 90 days)
        cutoff_date_str = (date.today() - timedelta(days=90)).isoformat()
        old_dates = [
            date_str for date_str in self._daily_costs.keys()
            if date_str < cutoff_date_str
        ]
        for old_date in old_dates:
            del self._daily_costs[old_date]
        
        # Clean up old alert history (keep 30 days)
        alert_cutoff = datetime.utcnow() - timedelta(days=30)
        old_alerts = [
            alert_key for alert_key, timestamp in self._alerts_sent.items()
            if timestamp < alert_cutoff
        ]
        for old_alert in old_alerts:
            del self._alerts_sent[old_alert]