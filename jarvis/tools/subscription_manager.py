"""Subscription manager and recurring expense optimizer.

Tracks subscriptions, memberships, and recurring bills with optimization
insights and spending analysis.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from enum import Enum
from typing import Optional
import uuid


class BillingFrequency(str, Enum):
    """Billing frequency for subscriptions."""
    DAILY = "daily"
    WEEKLY = "weekly"
    BIWEEKLY = "biweekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    SEMIANNUAL = "semiannual"
    ANNUAL = "annual"


class SubscriptionCategory(str, Enum):
    """Categories of subscriptions."""
    STREAMING = "streaming"
    SOFTWARE = "software"
    CLOUD = "cloud"
    MEMBERSHIP = "membership"
    UTILITIES = "utilities"
    INSURANCE = "insurance"
    TELECOMMUNICATIONS = "telecommunications"
    TRANSPORTATION = "transportation"
    HEALTHCARE = "healthcare"
    EDUCATION = "education"
    FINANCE = "finance"
    OTHER = "other"


@dataclass
class Subscription:
    """Individual subscription or recurring expense.
    
    Attributes:
        subscription_id: Unique identifier
        name: Service name
        category: Subscription category
        provider: Service provider
        amount: Cost per billing period
        currency: Currency code (e.g., "USD")
        frequency: Billing frequency
        start_date: When subscription started (UTC)
        renewal_date: Next renewal date (UTC)
        cancellation_date: Cancellation date if active (UTC, None if active)
        auto_renew: Whether subscription auto-renews
        notes: Additional notes or features
        is_active: Whether subscription is currently active
    """
    subscription_id: str
    name: str
    category: SubscriptionCategory
    provider: str
    amount: float
    currency: str
    frequency: BillingFrequency
    start_date: datetime
    renewal_date: datetime
    auto_renew: bool = True
    cancellation_date: Optional[datetime] = None
    notes: str = ""
    
    def __post_init__(self):
        """Validate subscription."""
        if self.amount < 0:
            raise ValueError("Amount must be non-negative")
        if not isinstance(self.start_date, datetime) or self.start_date.tzinfo is None:
            raise ValueError("start_date must be timezone-aware (UTC)")
        if not isinstance(self.renewal_date, datetime) or self.renewal_date.tzinfo is None:
            raise ValueError("renewal_date must be timezone-aware (UTC)")
        if self.cancellation_date and (not isinstance(self.cancellation_date, datetime) or self.cancellation_date.tzinfo is None):
            raise ValueError("cancellation_date must be timezone-aware (UTC)")
    
    @property
    def is_active(self) -> bool:
        """Whether subscription is currently active."""
        if self.cancellation_date:
            return datetime.now(timezone.utc) < self.cancellation_date
        return True
    
    @property
    def annual_cost(self) -> float:
        """Calculate annualized cost."""
        multiplier = {
            BillingFrequency.DAILY: 365,
            BillingFrequency.WEEKLY: 52,
            BillingFrequency.BIWEEKLY: 26,
            BillingFrequency.MONTHLY: 12,
            BillingFrequency.QUARTERLY: 4,
            BillingFrequency.SEMIANNUAL: 2,
            BillingFrequency.ANNUAL: 1,
        }
        return self.amount * multiplier[self.frequency]
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "id": self.subscription_id,
            "name": self.name,
            "category": self.category.value,
            "provider": self.provider,
            "amount": self.amount,
            "currency": self.currency,
            "frequency": self.frequency.value,
            "start_date": self.start_date.isoformat(),
            "renewal_date": self.renewal_date.isoformat(),
            "auto_renew": self.auto_renew,
            "cancellation_date": self.cancellation_date.isoformat() if self.cancellation_date else None,
            "active": self.is_active,
            "annual_cost": self.annual_cost,
        }


@dataclass
class SubscriptionOptimization:
    """Optimization recommendation for subscription.
    
    Attributes:
        subscription_id: Subscription ID
        subscription_name: Name of subscription
        optimization_type: Type of optimization (cancel, upgrade, consolidate, negotiate)
        potential_savings: Estimated annual savings
        rationale: Explanation of recommendation
        action: Specific action to take
        priority: Priority level (high, medium, low)
    """
    subscription_id: str
    subscription_name: str
    optimization_type: str
    potential_savings: float
    rationale: str
    action: str
    priority: str


@dataclass
class SubscriptionSummary:
    """Summary of subscription portfolio.
    
    Attributes:
        report_id: Unique report identifier
        generated_at: When report was generated (UTC)
        active_subscriptions: Count of active subscriptions
        total_active_cost: Total annual cost of active subscriptions
        inactive_subscriptions: Count of cancelled subscriptions
        subscriptions_by_category: Count by category
        upcoming_renewals: Subscriptions renewing in next 30 days
        total_potential_savings: Total potential savings from optimizations
        optimizations: List of optimization recommendations
        monthly_avg_spending: Average monthly spending on subscriptions
    """
    report_id: str
    generated_at: datetime
    active_subscriptions: int
    total_active_cost: float
    inactive_subscriptions: int
    subscriptions_by_category: dict[str, int]
    upcoming_renewals: list[Subscription]
    total_potential_savings: float
    optimizations: list[SubscriptionOptimization]
    monthly_avg_spending: float
    
    def __post_init__(self):
        """Validate summary."""
        if not isinstance(self.generated_at, datetime):
            raise ValueError("generated_at must be a datetime object")
        if self.generated_at.tzinfo is None:
            raise ValueError("generated_at must be timezone-aware (UTC)")
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "report_id": self.report_id,
            "generated_at": self.generated_at.isoformat(),
            "active_subscriptions": self.active_subscriptions,
            "total_annual_cost": self.total_active_cost,
            "monthly_avg": self.monthly_avg_spending,
            "inactive_subscriptions": self.inactive_subscriptions,
            "by_category": self.subscriptions_by_category,
            "upcoming_renewals": [s.to_dict() for s in self.upcoming_renewals],
            "potential_savings": self.total_potential_savings,
            "optimizations": [
                {
                    "subscription": o.subscription_name,
                    "type": o.optimization_type,
                    "savings": o.potential_savings,
                    "priority": o.priority,
                    "action": o.action,
                }
                for o in self.optimizations
            ],
        }


class SubscriptionManager:
    """Manager for subscriptions and recurring expenses."""
    
    def __init__(self):
        """Initialize subscription manager."""
        self.subscriptions: dict[str, Subscription] = {}
    
    def add_subscription(
        self,
        name: str,
        category: SubscriptionCategory,
        provider: str,
        amount: float,
        currency: str,
        frequency: BillingFrequency,
        start_date: datetime,
        renewal_date: datetime,
        auto_renew: bool = True,
        notes: str = "",
    ) -> Subscription:
        """Add a new subscription.
        
        Args:
            name: Service name
            category: Subscription category
            provider: Service provider
            amount: Cost per billing period
            currency: Currency code
            frequency: Billing frequency
            start_date: When subscription started
            renewal_date: Next renewal date
            auto_renew: Whether subscription auto-renews
            notes: Additional notes
        
        Returns:
            Created Subscription object
        """
        sub_id = str(uuid.uuid4())
        subscription = Subscription(
            subscription_id=sub_id,
            name=name,
            category=category,
            provider=provider,
            amount=amount,
            currency=currency,
            frequency=frequency,
            start_date=start_date,
            renewal_date=renewal_date,
            auto_renew=auto_renew,
            notes=notes,
        )
        self.subscriptions[sub_id] = subscription
        return subscription
    
    def cancel_subscription(self, subscription_id: str, cancellation_date: Optional[datetime] = None):
        """Cancel a subscription.
        
        Args:
            subscription_id: ID of subscription to cancel
            cancellation_date: When to cancel (default: now)
        """
        if subscription_id not in self.subscriptions:
            raise ValueError(f"Subscription {subscription_id} not found")
        
        if cancellation_date is None:
            cancellation_date = datetime.now(timezone.utc)
        
        self.subscriptions[subscription_id].cancellation_date = cancellation_date
    
    def get_active_subscriptions(self) -> list[Subscription]:
        """Get list of active subscriptions.
        
        Returns:
            List of active Subscription objects
        """
        return [sub for sub in self.subscriptions.values() if sub.is_active]
    
    def get_subscriptions_by_category(self, category: SubscriptionCategory) -> list[Subscription]:
        """Get subscriptions by category.
        
        Args:
            category: Subscription category
        
        Returns:
            List of subscriptions in category
        """
        return [sub for sub in self.subscriptions.values() if sub.category == category and sub.is_active]
    
    def get_upcoming_renewals(self, days: int = 30) -> list[Subscription]:
        """Get subscriptions renewing in next N days.
        
        Args:
            days: Number of days to look ahead
        
        Returns:
            List of subscriptions renewing soon
        """
        now = datetime.now(timezone.utc)
        future = now + timedelta(days=days)
        
        return [
            sub for sub in self.subscriptions.values()
            if sub.is_active and now <= sub.renewal_date <= future
        ]
    
    def calculate_total_cost(self) -> dict[str, float]:
        """Calculate total subscription costs.
        
        Returns:
            Dict with monthly, annual, and daily costs
        """
        active_subs = self.get_active_subscriptions()
        
        monthly_costs = {}
        for sub in active_subs:
            multiplier = {
                BillingFrequency.DAILY: 30,
                BillingFrequency.WEEKLY: 4.33,
                BillingFrequency.BIWEEKLY: 2.17,
                BillingFrequency.MONTHLY: 1,
                BillingFrequency.QUARTERLY: 1/3,
                BillingFrequency.SEMIANNUAL: 1/6,
                BillingFrequency.ANNUAL: 1/12,
            }
            monthly_costs[sub.subscription_id] = sub.amount * multiplier[sub.frequency]
        
        total_monthly = sum(monthly_costs.values())
        total_annual = total_monthly * 12
        total_daily = total_monthly / 30
        
        return {
            "daily": total_daily,
            "monthly": total_monthly,
            "annual": total_annual,
        }
    
    def analyze_subscriptions(self) -> SubscriptionSummary:
        """Analyze subscription portfolio and generate recommendations.
        
        Returns:
            SubscriptionSummary with analysis and optimizations
        """
        active_subs = self.get_active_subscriptions()
        inactive_subs = [s for s in self.subscriptions.values() if not s.is_active]
        upcoming = self.get_upcoming_renewals(30)
        
        # Count by category
        by_category = {}
        for sub in active_subs:
            cat = sub.category.value
            by_category[cat] = by_category.get(cat, 0) + 1
        
        # Calculate costs
        costs = self.calculate_total_cost()
        total_annual = costs["annual"]
        
        # Identify optimizations
        optimizations = []
        total_savings = 0.0
        
        # Check for duplicate categories
        for category in SubscriptionCategory:
            cat_subs = self.get_subscriptions_by_category(category)
            if len(cat_subs) > 1:
                # Consolidation opportunity
                lowest_cost = min(cat_subs, key=lambda s: s.annual_cost)
                for sub in cat_subs:
                    if sub != lowest_cost:
                        savings = sub.annual_cost
                        optimizations.append(SubscriptionOptimization(
                            subscription_id=sub.subscription_id,
                            subscription_name=sub.name,
                            optimization_type="consolidate",
                            potential_savings=savings,
                            rationale=f"Duplicate {category.value} subscription - consolidate to {lowest_cost.name}",
                            action=f"Cancel {sub.name}, keep {lowest_cost.name}",
                            priority="high",
                        ))
                        total_savings += savings
        
        # Check for unused subscriptions (last renewal 60+ days ago)
        now = datetime.now(timezone.utc)
        for sub in active_subs:
            days_since_renewal = (now - sub.renewal_date).days
            if days_since_renewal > 60 and sub.renewal_date < now:
                optimizations.append(SubscriptionOptimization(
                    subscription_id=sub.subscription_id,
                    subscription_name=sub.name,
                    optimization_type="cancel",
                    potential_savings=sub.annual_cost,
                    rationale="No renewal activity in 60+ days - likely unused",
                    action=f"Cancel {sub.name}",
                    priority="medium",
                ))
                total_savings += sub.annual_cost
        
        # Sort optimizations by savings (highest first)
        optimizations.sort(key=lambda x: x.potential_savings, reverse=True)
        
        return SubscriptionSummary(
            report_id=str(uuid.uuid4()),
            generated_at=datetime.now(timezone.utc),
            active_subscriptions=len(active_subs),
            total_active_cost=total_annual,
            inactive_subscriptions=len(inactive_subs),
            subscriptions_by_category=by_category,
            upcoming_renewals=upcoming,
            total_potential_savings=total_savings,
            optimizations=optimizations,
            monthly_avg_spending=costs["monthly"],
        )
