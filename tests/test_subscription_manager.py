"""Tests for subscription manager and recurring expense optimizer."""

import pytest
from datetime import datetime, timezone, timedelta
import uuid

from jarvis.tools.subscription_manager import (
    BillingFrequency, SubscriptionCategory, Subscription,
    SubscriptionOptimization, SubscriptionSummary, SubscriptionManager
)


class TestBillingFrequency:
    """Tests for billing frequency enumeration."""
    
    def test_all_frequencies_defined(self):
        """Verify all billing frequencies are defined."""
        freqs = [f.value for f in BillingFrequency]
        assert "daily" in freqs
        assert "monthly" in freqs
        assert "annual" in freqs


class TestSubscriptionCategory:
    """Tests for subscription category enumeration."""
    
    def test_all_categories_defined(self):
        """Verify all categories are defined."""
        cats = [c.value for c in SubscriptionCategory]
        assert "streaming" in cats
        assert "software" in cats
        assert "membership" in cats


class TestSubscription:
    """Tests for subscription objects."""
    
    def test_subscription_creation(self):
        """Test creating a subscription."""
        now = datetime.now(timezone.utc)
        renewal = now + timedelta(days=30)
        
        sub = Subscription(
            subscription_id=str(uuid.uuid4()),
            name="Netflix",
            category=SubscriptionCategory.STREAMING,
            provider="Netflix Inc.",
            amount=15.99,
            currency="USD",
            frequency=BillingFrequency.MONTHLY,
            start_date=now,
            renewal_date=renewal,
        )
        assert sub.name == "Netflix"
        assert sub.is_active
    
    def test_subscription_annual_cost_monthly(self):
        """Test annual cost calculation for monthly subscription."""
        now = datetime.now(timezone.utc)
        sub = Subscription(
            subscription_id=str(uuid.uuid4()),
            name="Test",
            category=SubscriptionCategory.SOFTWARE,
            provider="Provider",
            amount=10.0,
            currency="USD",
            frequency=BillingFrequency.MONTHLY,
            start_date=now,
            renewal_date=now + timedelta(days=30),
        )
        assert sub.annual_cost == pytest.approx(120.0)
    
    def test_subscription_annual_cost_annual(self):
        """Test annual cost calculation for annual subscription."""
        now = datetime.now(timezone.utc)
        sub = Subscription(
            subscription_id=str(uuid.uuid4()),
            name="Test",
            category=SubscriptionCategory.SOFTWARE,
            provider="Provider",
            amount=100.0,
            currency="USD",
            frequency=BillingFrequency.ANNUAL,
            start_date=now,
            renewal_date=now + timedelta(days=365),
        )
        assert sub.annual_cost == 100.0
    
    def test_subscription_active_status(self):
        """Test subscription active status."""
        now = datetime.now(timezone.utc)
        sub = Subscription(
            subscription_id=str(uuid.uuid4()),
            name="Test",
            category=SubscriptionCategory.STREAMING,
            provider="Provider",
            amount=10.0,
            currency="USD",
            frequency=BillingFrequency.MONTHLY,
            start_date=now,
            renewal_date=now + timedelta(days=30),
            cancellation_date=now + timedelta(days=60),
        )
        assert sub.is_active
    
    def test_subscription_cancelled_status(self):
        """Test cancelled subscription status."""
        now = datetime.now(timezone.utc)
        past = now - timedelta(days=5)
        sub = Subscription(
            subscription_id=str(uuid.uuid4()),
            name="Test",
            category=SubscriptionCategory.STREAMING,
            provider="Provider",
            amount=10.0,
            currency="USD",
            frequency=BillingFrequency.MONTHLY,
            start_date=now,
            renewal_date=now + timedelta(days=30),
            cancellation_date=past,
        )
        assert not sub.is_active
    
    def test_subscription_naive_datetime_raises(self):
        """Test that naive datetime raises error."""
        naive = datetime(2026, 4, 27, 10, 0, 0)
        with pytest.raises(ValueError, match="timezone-aware"):
            Subscription(
                subscription_id=str(uuid.uuid4()),
                name="Test",
                category=SubscriptionCategory.SOFTWARE,
                provider="Provider",
                amount=10.0,
                currency="USD",
                frequency=BillingFrequency.MONTHLY,
                start_date=naive,
                renewal_date=naive + timedelta(days=30),
            )
    
    def test_subscription_negative_amount_raises(self):
        """Test that negative amount raises error."""
        now = datetime.now(timezone.utc)
        with pytest.raises(ValueError, match="non-negative"):
            Subscription(
                subscription_id=str(uuid.uuid4()),
                name="Test",
                category=SubscriptionCategory.SOFTWARE,
                provider="Provider",
                amount=-10.0,
                currency="USD",
                frequency=BillingFrequency.MONTHLY,
                start_date=now,
                renewal_date=now + timedelta(days=30),
            )
    
    def test_subscription_to_dict(self):
        """Test subscription serialization."""
        now = datetime.now(timezone.utc)
        renewal = now + timedelta(days=30)
        sub = Subscription(
            subscription_id="sub-123",
            name="Test Service",
            category=SubscriptionCategory.STREAMING,
            provider="Test Provider",
            amount=9.99,
            currency="USD",
            frequency=BillingFrequency.MONTHLY,
            start_date=now,
            renewal_date=renewal,
        )
        data = sub.to_dict()
        assert data["name"] == "Test Service"
        assert data["amount"] == 9.99


class TestSubscriptionOptimization:
    """Tests for subscription optimizations."""
    
    def test_optimization_creation(self):
        """Test creating optimization recommendation."""
        opt = SubscriptionOptimization(
            subscription_id=str(uuid.uuid4()),
            subscription_name="Unused Subscription",
            optimization_type="cancel",
            potential_savings=100.0,
            rationale="No activity in 60+ days",
            action="Cancel subscription",
            priority="high",
        )
        assert opt.potential_savings == 100.0
        assert opt.priority == "high"


class TestSubscriptionSummary:
    """Tests for subscription summaries."""
    
    def test_summary_creation(self):
        """Test creating subscription summary."""
        ts = datetime.now(timezone.utc)
        summary = SubscriptionSummary(
            report_id=str(uuid.uuid4()),
            generated_at=ts,
            active_subscriptions=5,
            total_active_cost=500.0,
            inactive_subscriptions=1,
            subscriptions_by_category={},
            upcoming_renewals=[],
            total_potential_savings=100.0,
            optimizations=[],
            monthly_avg_spending=41.67,
        )
        assert summary.active_subscriptions == 5
        assert summary.total_potential_savings == 100.0
    
    def test_summary_naive_datetime_raises(self):
        """Test that naive datetime raises error."""
        naive = datetime(2026, 4, 27, 10, 0, 0)
        with pytest.raises(ValueError, match="timezone-aware"):
            SubscriptionSummary(
                report_id=str(uuid.uuid4()),
                generated_at=naive,
                active_subscriptions=0,
                total_active_cost=0.0,
                inactive_subscriptions=0,
                subscriptions_by_category={},
                upcoming_renewals=[],
                total_potential_savings=0.0,
                optimizations=[],
                monthly_avg_spending=0.0,
            )
    
    def test_summary_to_dict(self):
        """Test summary serialization."""
        ts = datetime.now(timezone.utc)
        summary = SubscriptionSummary(
            report_id="report-123",
            generated_at=ts,
            active_subscriptions=3,
            total_active_cost=300.0,
            inactive_subscriptions=2,
            subscriptions_by_category={"streaming": 2, "software": 1},
            upcoming_renewals=[],
            total_potential_savings=50.0,
            optimizations=[],
            monthly_avg_spending=25.0,
        )
        data = summary.to_dict()
        assert data["active_subscriptions"] == 3
        assert data["monthly_avg"] == 25.0


class TestSubscriptionManager:
    """Tests for subscription manager."""
    
    def test_manager_creation(self):
        """Test creating subscription manager."""
        manager = SubscriptionManager()
        assert len(manager.subscriptions) == 0
    
    def test_add_subscription(self):
        """Test adding a subscription."""
        manager = SubscriptionManager()
        now = datetime.now(timezone.utc)
        
        sub = manager.add_subscription(
            name="Spotify",
            category=SubscriptionCategory.STREAMING,
            provider="Spotify AB",
            amount=12.99,
            currency="USD",
            frequency=BillingFrequency.MONTHLY,
            start_date=now,
            renewal_date=now + timedelta(days=30),
        )
        
        assert len(manager.subscriptions) == 1
        assert sub.name == "Spotify"
    
    def test_add_multiple_subscriptions(self):
        """Test adding multiple subscriptions."""
        manager = SubscriptionManager()
        now = datetime.now(timezone.utc)
        
        manager.add_subscription(
            name="Netflix",
            category=SubscriptionCategory.STREAMING,
            provider="Netflix",
            amount=15.99,
            currency="USD",
            frequency=BillingFrequency.MONTHLY,
            start_date=now,
            renewal_date=now + timedelta(days=30),
        )
        
        manager.add_subscription(
            name="Adobe CC",
            category=SubscriptionCategory.SOFTWARE,
            provider="Adobe",
            amount=54.99,
            currency="USD",
            frequency=BillingFrequency.MONTHLY,
            start_date=now,
            renewal_date=now + timedelta(days=30),
        )
        
        assert len(manager.subscriptions) == 2
    
    def test_cancel_subscription(self):
        """Test cancelling a subscription."""
        manager = SubscriptionManager()
        now = datetime.now(timezone.utc)
        
        sub = manager.add_subscription(
            name="Test",
            category=SubscriptionCategory.STREAMING,
            provider="Provider",
            amount=10.0,
            currency="USD",
            frequency=BillingFrequency.MONTHLY,
            start_date=now,
            renewal_date=now + timedelta(days=30),
        )
        
        manager.cancel_subscription(sub.subscription_id)
        assert not sub.is_active
    
    def test_cancel_nonexistent_raises(self):
        """Test cancelling nonexistent subscription raises error."""
        manager = SubscriptionManager()
        with pytest.raises(ValueError, match="not found"):
            manager.cancel_subscription("fake-id")
    
    def test_get_active_subscriptions(self):
        """Test getting active subscriptions."""
        manager = SubscriptionManager()
        now = datetime.now(timezone.utc)
        
        sub1 = manager.add_subscription(
            name="Netflix",
            category=SubscriptionCategory.STREAMING,
            provider="Netflix",
            amount=15.99,
            currency="USD",
            frequency=BillingFrequency.MONTHLY,
            start_date=now,
            renewal_date=now + timedelta(days=30),
        )
        
        sub2_temp = manager.add_subscription(
            name="Old Service",
            category=SubscriptionCategory.OTHER,
            provider="Provider",
            amount=5.0,
            currency="USD",
            frequency=BillingFrequency.MONTHLY,
            start_date=now,
            renewal_date=now + timedelta(days=30),
        )
        manager.cancel_subscription(sub2_temp.subscription_id, now - timedelta(days=5))
        
        active = manager.get_active_subscriptions()
        assert len(active) == 1
        assert active[0].name == "Netflix"
    
    def test_get_subscriptions_by_category(self):
        """Test getting subscriptions by category."""
        manager = SubscriptionManager()
        now = datetime.now(timezone.utc)
        
        manager.add_subscription(
            name="Netflix",
            category=SubscriptionCategory.STREAMING,
            provider="Netflix",
            amount=15.99,
            currency="USD",
            frequency=BillingFrequency.MONTHLY,
            start_date=now,
            renewal_date=now + timedelta(days=30),
        )
        
        manager.add_subscription(
            name="Hulu",
            category=SubscriptionCategory.STREAMING,
            provider="Disney",
            amount=14.99,
            currency="USD",
            frequency=BillingFrequency.MONTHLY,
            start_date=now,
            renewal_date=now + timedelta(days=30),
        )
        
        streaming = manager.get_subscriptions_by_category(SubscriptionCategory.STREAMING)
        assert len(streaming) == 2
    
    def test_get_upcoming_renewals(self):
        """Test getting upcoming renewals."""
        manager = SubscriptionManager()
        now = datetime.now(timezone.utc)
        
        # Renewal in 10 days
        manager.add_subscription(
            name="Soon",
            category=SubscriptionCategory.STREAMING,
            provider="Provider",
            amount=10.0,
            currency="USD",
            frequency=BillingFrequency.MONTHLY,
            start_date=now,
            renewal_date=now + timedelta(days=10),
        )
        
        # Renewal in 60 days
        manager.add_subscription(
            name="Later",
            category=SubscriptionCategory.SOFTWARE,
            provider="Provider",
            amount=20.0,
            currency="USD",
            frequency=BillingFrequency.MONTHLY,
            start_date=now,
            renewal_date=now + timedelta(days=60),
        )
        
        upcoming = manager.get_upcoming_renewals(30)
        assert len(upcoming) == 1
        assert upcoming[0].name == "Soon"
    
    def test_calculate_total_cost(self):
        """Test calculating total costs."""
        manager = SubscriptionManager()
        now = datetime.now(timezone.utc)
        
        manager.add_subscription(
            name="Test1",
            category=SubscriptionCategory.STREAMING,
            provider="Provider",
            amount=10.0,
            currency="USD",
            frequency=BillingFrequency.MONTHLY,
            start_date=now,
            renewal_date=now + timedelta(days=30),
        )
        
        manager.add_subscription(
            name="Test2",
            category=SubscriptionCategory.SOFTWARE,
            provider="Provider",
            amount=5.0,
            currency="USD",
            frequency=BillingFrequency.MONTHLY,
            start_date=now,
            renewal_date=now + timedelta(days=30),
        )
        
        costs = manager.calculate_total_cost()
        assert costs["monthly"] == pytest.approx(15.0)
        assert costs["annual"] == pytest.approx(180.0)
    
    def test_analyze_subscriptions_basic(self):
        """Test analyzing subscriptions."""
        manager = SubscriptionManager()
        now = datetime.now(timezone.utc)
        
        manager.add_subscription(
            name="Netflix",
            category=SubscriptionCategory.STREAMING,
            provider="Netflix",
            amount=15.99,
            currency="USD",
            frequency=BillingFrequency.MONTHLY,
            start_date=now,
            renewal_date=now + timedelta(days=30),
        )
        
        summary = manager.analyze_subscriptions()
        
        assert summary.active_subscriptions == 1
        assert summary.total_active_cost == pytest.approx(191.88)
        assert isinstance(summary, SubscriptionSummary)
    
    def test_analyze_detects_duplicates(self):
        """Test that analysis detects duplicate categories."""
        manager = SubscriptionManager()
        now = datetime.now(timezone.utc)
        
        # Two streaming services
        manager.add_subscription(
            name="Netflix",
            category=SubscriptionCategory.STREAMING,
            provider="Netflix",
            amount=15.99,
            currency="USD",
            frequency=BillingFrequency.MONTHLY,
            start_date=now,
            renewal_date=now + timedelta(days=30),
        )
        
        manager.add_subscription(
            name="Hulu",
            category=SubscriptionCategory.STREAMING,
            provider="Disney",
            amount=14.99,
            currency="USD",
            frequency=BillingFrequency.MONTHLY,
            start_date=now,
            renewal_date=now + timedelta(days=30),
        )
        
        summary = manager.analyze_subscriptions()
        
        # Should detect consolidation opportunity
        assert len(summary.optimizations) > 0
        assert any(opt.optimization_type == "consolidate" for opt in summary.optimizations)


class TestSubscriptionManagerEdgeCases:
    """Edge case tests for subscription manager."""
    
    def test_empty_manager_analysis(self):
        """Test analyzing empty subscription portfolio."""
        manager = SubscriptionManager()
        summary = manager.analyze_subscriptions()
        
        assert summary.active_subscriptions == 0
        assert summary.total_active_cost == 0.0
    
    def test_zero_amount_subscription(self):
        """Test adding zero-amount subscription (free tier)."""
        manager = SubscriptionManager()
        now = datetime.now(timezone.utc)
        
        sub = manager.add_subscription(
            name="Free Service",
            category=SubscriptionCategory.SOFTWARE,
            provider="Provider",
            amount=0.0,
            currency="USD",
            frequency=BillingFrequency.MONTHLY,
            start_date=now,
            renewal_date=now + timedelta(days=30),
        )
        
        assert sub.annual_cost == 0.0
    
    def test_different_billing_frequencies(self):
        """Test subscriptions with different billing frequencies."""
        manager = SubscriptionManager()
        now = datetime.now(timezone.utc)
        
        # Monthly at $10
        monthly = manager.add_subscription(
            name="Monthly Service",
            category=SubscriptionCategory.SOFTWARE,
            provider="Provider",
            amount=10.0,
            currency="USD",
            frequency=BillingFrequency.MONTHLY,
            start_date=now,
            renewal_date=now + timedelta(days=30),
        )
        
        # Annual at $100
        annual = manager.add_subscription(
            name="Annual Service",
            category=SubscriptionCategory.MEMBERSHIP,
            provider="Provider",
            amount=100.0,
            currency="USD",
            frequency=BillingFrequency.ANNUAL,
            start_date=now,
            renewal_date=now + timedelta(days=365),
        )
        
        costs = manager.calculate_total_cost()
        # (10 * 12) + 100 = 220 annual
        assert costs["annual"] == pytest.approx(220.0, 1)
