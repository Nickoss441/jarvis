"""Sinking fund planning and projection utilities.

Provides bucket-based savings goal tracking, contribution scheduling, progress
analysis, and deterministic funding projections for planned expenses.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from math import isfinite
from typing import Optional
import uuid


class FundCategory(str, Enum):
    """Supported sinking fund categories."""

    TRAVEL = "travel"
    AUTO = "auto"
    HOME = "home"
    MEDICAL = "medical"
    HOLIDAY = "holiday"
    EDUCATION = "education"
    TAX = "tax"
    INSURANCE = "insurance"
    TECHNOLOGY = "technology"
    OTHER = "other"


class ContributionFrequency(str, Enum):
    """Contribution cadence for sinking fund plans."""

    WEEKLY = "weekly"
    BIWEEKLY = "biweekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"


class FundStatus(str, Enum):
    """Funding state for a sinking fund goal."""

    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    FUNDED = "funded"
    OVERFUNDED = "overfunded"


@dataclass
class SinkingFundGoal:
    """Target savings bucket for a planned future expense."""

    fund_id: str
    name: str
    category: FundCategory
    target_amount: float
    current_balance: float
    target_date: datetime
    created_at: datetime
    notes: str = ""

    def __post_init__(self):
        if self.target_amount < 0:
            raise ValueError("target_amount cannot be negative")
        if self.current_balance < 0:
            raise ValueError("current_balance cannot be negative")
        if not isinstance(self.target_date, datetime) or self.target_date.tzinfo is None:
            raise ValueError("target_date must be timezone-aware (UTC)")
        if not isinstance(self.created_at, datetime) or self.created_at.tzinfo is None:
            raise ValueError("created_at must be timezone-aware (UTC)")

    @property
    def amount_remaining(self) -> float:
        """Remaining amount required to hit the target."""
        return max(0.0, self.target_amount - self.current_balance)

    @property
    def progress_percentage(self) -> float:
        """Funding progress percentage."""
        if self.target_amount == 0:
            return 100.0
        return min(100.0, (self.current_balance / self.target_amount) * 100.0)

    @property
    def status(self) -> FundStatus:
        """Current status of the fund."""
        if self.current_balance == 0:
            return FundStatus.NOT_STARTED
        if self.current_balance < self.target_amount:
            return FundStatus.IN_PROGRESS
        if self.current_balance == self.target_amount:
            return FundStatus.FUNDED
        return FundStatus.OVERFUNDED

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "id": self.fund_id,
            "name": self.name,
            "category": self.category.value,
            "target_amount": self.target_amount,
            "current_balance": self.current_balance,
            "amount_remaining": self.amount_remaining,
            "progress_percentage": self.progress_percentage,
            "status": self.status.value,
            "target_date": self.target_date.isoformat(),
            "created_at": self.created_at.isoformat(),
            "notes": self.notes,
        }


@dataclass
class ContributionRecord:
    """A contribution applied to a sinking fund."""

    contribution_id: str
    fund_id: str
    amount: float
    contributed_at: datetime
    note: str = ""

    def __post_init__(self):
        if self.amount < 0:
            raise ValueError("amount cannot be negative")
        if not isinstance(self.contributed_at, datetime) or self.contributed_at.tzinfo is None:
            raise ValueError("contributed_at must be timezone-aware (UTC)")

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "id": self.contribution_id,
            "fund_id": self.fund_id,
            "amount": self.amount,
            "contributed_at": self.contributed_at.isoformat(),
            "note": self.note,
        }


@dataclass
class FundingProjection:
    """Projection for reaching a sinking fund target."""

    projection_id: str
    fund_id: str
    contribution_frequency: ContributionFrequency
    contribution_per_period: float
    periods_to_target: int
    projected_completion_date: Optional[datetime]
    final_balance: float
    target_reached: bool
    timeline: list[dict]
    generated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "id": self.projection_id,
            "fund_id": self.fund_id,
            "contribution_frequency": self.contribution_frequency.value,
            "contribution_per_period": self.contribution_per_period,
            "periods_to_target": self.periods_to_target,
            "projected_completion_date": (
                self.projected_completion_date.isoformat() if self.projected_completion_date else None
            ),
            "final_balance": self.final_balance,
            "target_reached": self.target_reached,
            "timeline": self.timeline,
            "generated_at": self.generated_at.isoformat(),
        }


class SinkingFundPlanner:
    """Planner for target-based sinking funds."""

    PERIODS_PER_YEAR = {
        ContributionFrequency.WEEKLY: 52,
        ContributionFrequency.BIWEEKLY: 26,
        ContributionFrequency.MONTHLY: 12,
        ContributionFrequency.QUARTERLY: 4,
    }

    DAYS_PER_PERIOD = {
        ContributionFrequency.WEEKLY: 7,
        ContributionFrequency.BIWEEKLY: 14,
        ContributionFrequency.MONTHLY: 30,
        ContributionFrequency.QUARTERLY: 91,
    }

    def __init__(self):
        self.funds: dict[str, SinkingFundGoal] = {}
        self.contributions: list[ContributionRecord] = []

    def add_fund(
        self,
        name: str,
        category: FundCategory,
        target_amount: float,
        current_balance: float,
        target_date: datetime,
        created_at: datetime,
        notes: str = "",
    ) -> SinkingFundGoal:
        """Create and register a sinking fund goal."""
        fund = SinkingFundGoal(
            fund_id=str(uuid.uuid4()),
            name=name,
            category=category,
            target_amount=target_amount,
            current_balance=current_balance,
            target_date=target_date,
            created_at=created_at,
            notes=notes,
        )
        self.funds[fund.fund_id] = fund
        return fund

    def record_contribution(
        self,
        fund_id: str,
        amount: float,
        contributed_at: datetime,
        note: str = "",
    ) -> ContributionRecord:
        """Record a contribution and apply it to the fund balance."""
        fund = self.funds.get(fund_id)
        if fund is None:
            raise KeyError(f"fund not found: {fund_id}")
        if amount < 0:
            raise ValueError("amount cannot be negative")

        fund.current_balance += amount
        record = ContributionRecord(
            contribution_id=str(uuid.uuid4()),
            fund_id=fund_id,
            amount=amount,
            contributed_at=contributed_at,
            note=note,
        )
        self.contributions.append(record)
        return record

    def get_total_target_amount(self) -> float:
        """Total target value across all funds."""
        return sum(fund.target_amount for fund in self.funds.values())

    def get_total_current_balance(self) -> float:
        """Total current balance across all funds."""
        return sum(fund.current_balance for fund in self.funds.values())

    def get_total_remaining_amount(self) -> float:
        """Total unfunded amount across all funds."""
        return sum(fund.amount_remaining for fund in self.funds.values())

    def estimate_required_contribution(
        self,
        fund_id: str,
        frequency: ContributionFrequency,
        as_of: Optional[datetime] = None,
    ) -> float:
        """Estimate contribution per period required to reach target by date."""
        fund = self._get_fund(fund_id)
        if as_of is None:
            as_of = datetime.now(timezone.utc)
        if not isinstance(as_of, datetime) or as_of.tzinfo is None:
            raise ValueError("as_of must be timezone-aware (UTC)")

        if fund.amount_remaining == 0:
            return 0.0

        delta_days = max(0, (fund.target_date - as_of).days)
        periods = self._periods_between(delta_days, frequency)
        if periods == 0:
            return round(fund.amount_remaining, 2)
        return round(fund.amount_remaining / periods, 2)

    def project_funding(
        self,
        fund_id: str,
        frequency: ContributionFrequency,
        contribution_per_period: float,
        max_periods: int = 260,
    ) -> FundingProjection:
        """Project when a fund will reach target with a fixed contribution cadence."""
        fund = self._get_fund(fund_id)
        if contribution_per_period < 0:
            raise ValueError("contribution_per_period cannot be negative")
        if max_periods < 0:
            raise ValueError("max_periods cannot be negative")

        balance = fund.current_balance
        periods = 0
        timeline: list[dict] = []
        now = datetime.now(timezone.utc)
        days_per_period = self.DAYS_PER_PERIOD[frequency]

        while periods < max_periods and balance < fund.target_amount:
            periods += 1
            balance += contribution_per_period
            timeline.append(
                {
                    "period_index": periods,
                    "as_of": (now + timedelta(days=days_per_period * periods)).isoformat(),
                    "balance": round(balance, 2),
                }
            )

        target_reached = balance >= fund.target_amount
        completion_date = now + timedelta(days=days_per_period * periods) if target_reached else None

        return FundingProjection(
            projection_id=str(uuid.uuid4()),
            fund_id=fund_id,
            contribution_frequency=frequency,
            contribution_per_period=contribution_per_period,
            periods_to_target=periods,
            projected_completion_date=completion_date,
            final_balance=round(balance, 2),
            target_reached=target_reached,
            timeline=timeline,
        )

    def get_funds_by_status(self, status: FundStatus) -> list[SinkingFundGoal]:
        """Return all funds matching a specific funding status."""
        return [fund for fund in self.funds.values() if fund.status == status]

    def get_category_breakdown(self) -> dict[str, dict[str, float]]:
        """Summarize fund targets and balances by category."""
        breakdown: dict[str, dict[str, float]] = {}
        for fund in self.funds.values():
            bucket = breakdown.setdefault(
                fund.category.value,
                {"target_amount": 0.0, "current_balance": 0.0, "remaining_amount": 0.0, "count": 0},
            )
            bucket["target_amount"] += fund.target_amount
            bucket["current_balance"] += fund.current_balance
            bucket["remaining_amount"] += fund.amount_remaining
            bucket["count"] += 1
        return breakdown

    def _get_fund(self, fund_id: str) -> SinkingFundGoal:
        fund = self.funds.get(fund_id)
        if fund is None:
            raise KeyError(f"fund not found: {fund_id}")
        return fund

    @classmethod
    def _periods_between(cls, delta_days: int, frequency: ContributionFrequency) -> int:
        """Translate remaining days into cadence periods, rounding up partial periods."""
        if delta_days <= 0:
            return 0
        days_per_period = cls.DAYS_PER_PERIOD[frequency]
        return (delta_days + days_per_period - 1) // days_per_period
