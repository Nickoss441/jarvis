"""Emergency fund planning and replenishment utilities.

Provides emergency expense tracking, fund coverage analysis, target sizing,
withdrawal recording, and deterministic replenishment projections.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from math import isfinite
from typing import Optional
import uuid


class ExpenseType(str, Enum):
    """Supported emergency expense categories."""

    HOUSING = "housing"
    UTILITIES = "utilities"
    FOOD = "food"
    TRANSPORTATION = "transportation"
    INSURANCE = "insurance"
    MEDICAL = "medical"
    CHILDCARE = "childcare"
    DEBT = "debt"
    OTHER = "other"


class FundHealth(str, Enum):
    """Emergency fund health status based on months of coverage."""

    CRITICAL = "critical"
    UNDERFUNDED = "underfunded"
    ADEQUATE = "adequate"
    STRONG = "strong"


@dataclass
class EmergencyExpense:
    """Tracked recurring expense for emergency fund planning."""

    expense_id: str
    name: str
    expense_type: ExpenseType
    monthly_amount: float
    essential: bool
    created_at: datetime

    def __post_init__(self):
        if self.monthly_amount < 0:
            raise ValueError("monthly_amount cannot be negative")
        if not isinstance(self.created_at, datetime) or self.created_at.tzinfo is None:
            raise ValueError("created_at must be timezone-aware (UTC)")

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "id": self.expense_id,
            "name": self.name,
            "type": self.expense_type.value,
            "monthly_amount": self.monthly_amount,
            "essential": self.essential,
            "created_at": self.created_at.isoformat(),
        }


@dataclass
class EmergencyFundAccount:
    """Emergency fund account settings and current balance."""

    account_id: str
    name: str
    current_balance: float
    annual_yield_pct: float
    created_at: datetime

    def __post_init__(self):
        if self.current_balance < 0:
            raise ValueError("current_balance cannot be negative")
        if self.annual_yield_pct < 0 or not isfinite(self.annual_yield_pct):
            raise ValueError("annual_yield_pct must be a non-negative finite number")
        if not isinstance(self.created_at, datetime) or self.created_at.tzinfo is None:
            raise ValueError("created_at must be timezone-aware (UTC)")

    @property
    def monthly_yield_rate(self) -> float:
        """Monthly decimal yield rate."""
        return (self.annual_yield_pct / 100.0) / 12.0

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "id": self.account_id,
            "name": self.name,
            "current_balance": self.current_balance,
            "annual_yield_pct": self.annual_yield_pct,
            "created_at": self.created_at.isoformat(),
        }


@dataclass
class WithdrawalRecord:
    """Recorded emergency fund withdrawal."""

    withdrawal_id: str
    amount: float
    reason: str
    withdrawn_at: datetime

    def __post_init__(self):
        if self.amount < 0:
            raise ValueError("amount cannot be negative")
        if not isinstance(self.withdrawn_at, datetime) or self.withdrawn_at.tzinfo is None:
            raise ValueError("withdrawn_at must be timezone-aware (UTC)")

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "id": self.withdrawal_id,
            "amount": self.amount,
            "reason": self.reason,
            "withdrawn_at": self.withdrawn_at.isoformat(),
        }


@dataclass
class CoverageSnapshot:
    """Emergency fund coverage and target analysis snapshot."""

    current_balance: float
    monthly_burn: float
    months_covered: float
    target_months: int
    target_amount: float
    buffer_pct: float
    gap_amount: float
    health: FundHealth
    as_of: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "current_balance": self.current_balance,
            "monthly_burn": self.monthly_burn,
            "months_covered": self.months_covered,
            "target_months": self.target_months,
            "target_amount": self.target_amount,
            "buffer_pct": self.buffer_pct,
            "gap_amount": self.gap_amount,
            "health": self.health.value,
            "as_of": self.as_of.isoformat(),
        }


@dataclass
class ReplenishmentPlan:
    """Projected replenishment plan to restore target fund level."""

    plan_id: str
    monthly_contribution: float
    months_to_target: int
    target_amount: float
    projected_balance: float
    contribution_total: float
    yield_earned: float
    target_reached: bool
    projected_target_date: Optional[datetime]
    timeline: list[dict]
    generated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "id": self.plan_id,
            "monthly_contribution": self.monthly_contribution,
            "months_to_target": self.months_to_target,
            "target_amount": self.target_amount,
            "projected_balance": self.projected_balance,
            "contribution_total": self.contribution_total,
            "yield_earned": self.yield_earned,
            "target_reached": self.target_reached,
            "projected_target_date": (
                self.projected_target_date.isoformat() if self.projected_target_date else None
            ),
            "timeline": self.timeline,
            "generated_at": self.generated_at.isoformat(),
        }


class EmergencyFundPlanner:
    """Planner for emergency fund sizing and replenishment."""

    def __init__(self):
        self.expenses: dict[str, EmergencyExpense] = {}
        self.fund_account: Optional[EmergencyFundAccount] = None
        self.withdrawals: list[WithdrawalRecord] = []

    def set_fund_account(
        self,
        name: str,
        current_balance: float,
        annual_yield_pct: float,
        created_at: datetime,
    ) -> EmergencyFundAccount:
        """Create or replace the active emergency fund account."""
        account = EmergencyFundAccount(
            account_id=str(uuid.uuid4()),
            name=name,
            current_balance=current_balance,
            annual_yield_pct=annual_yield_pct,
            created_at=created_at,
        )
        self.fund_account = account
        return account

    def add_expense(
        self,
        name: str,
        expense_type: ExpenseType,
        monthly_amount: float,
        essential: bool,
        created_at: datetime,
    ) -> EmergencyExpense:
        """Add a tracked monthly expense."""
        expense = EmergencyExpense(
            expense_id=str(uuid.uuid4()),
            name=name,
            expense_type=expense_type,
            monthly_amount=monthly_amount,
            essential=essential,
            created_at=created_at,
        )
        self.expenses[expense.expense_id] = expense
        return expense

    def get_total_monthly_expenses(self, include_nonessential: bool = False) -> float:
        """Calculate total monthly burn rate."""
        return sum(
            expense.monthly_amount
            for expense in self.expenses.values()
            if include_nonessential or expense.essential
        )

    def calculate_target_amount(
        self,
        target_months: int = 6,
        buffer_pct: float = 0.0,
        include_nonessential: bool = False,
    ) -> float:
        """Calculate recommended emergency fund target amount."""
        if target_months < 0:
            raise ValueError("target_months cannot be negative")
        if buffer_pct < 0 or not isfinite(buffer_pct):
            raise ValueError("buffer_pct must be a non-negative finite number")

        monthly_burn = self.get_total_monthly_expenses(include_nonessential=include_nonessential)
        base_target = monthly_burn * target_months
        return round(base_target * (1 + (buffer_pct / 100.0)), 2)

    def get_coverage_snapshot(
        self,
        target_months: int = 6,
        buffer_pct: float = 0.0,
        include_nonessential: bool = False,
    ) -> CoverageSnapshot:
        """Return current fund coverage vs target."""
        monthly_burn = self.get_total_monthly_expenses(include_nonessential=include_nonessential)
        current_balance = self.fund_account.current_balance if self.fund_account else 0.0
        months_covered = 0.0 if monthly_burn == 0 else current_balance / monthly_burn
        target_amount = self.calculate_target_amount(
            target_months=target_months,
            buffer_pct=buffer_pct,
            include_nonessential=include_nonessential,
        )
        gap_amount = max(0.0, target_amount - current_balance)
        health = self._classify_health(months_covered, target_months)

        return CoverageSnapshot(
            current_balance=round(current_balance, 2),
            monthly_burn=round(monthly_burn, 2),
            months_covered=round(months_covered, 2),
            target_months=target_months,
            target_amount=target_amount,
            buffer_pct=buffer_pct,
            gap_amount=round(gap_amount, 2),
            health=health,
        )

    def estimate_required_monthly_contribution(
        self,
        months_to_goal: int,
        target_months: int = 6,
        buffer_pct: float = 0.0,
        include_nonessential: bool = False,
    ) -> float:
        """Estimate fixed monthly contribution required to reach target in time."""
        if months_to_goal < 0:
            raise ValueError("months_to_goal cannot be negative")

        target_amount = self.calculate_target_amount(
            target_months=target_months,
            buffer_pct=buffer_pct,
            include_nonessential=include_nonessential,
        )
        current_balance = self.fund_account.current_balance if self.fund_account else 0.0
        monthly_rate = self.fund_account.monthly_yield_rate if self.fund_account else 0.0

        if months_to_goal == 0:
            return round(max(0.0, target_amount - current_balance), 2)

        future_value_current = current_balance * ((1 + monthly_rate) ** months_to_goal)
        gap = max(0.0, target_amount - future_value_current)
        if gap == 0:
            return 0.0

        if monthly_rate == 0:
            return round(gap / months_to_goal, 2)

        annuity_factor = (((1 + monthly_rate) ** months_to_goal) - 1) / monthly_rate
        return round(gap / annuity_factor, 2)

    def project_replenishment(
        self,
        monthly_contribution: float,
        target_months: int = 6,
        buffer_pct: float = 0.0,
        include_nonessential: bool = False,
        max_months: int = 120,
    ) -> ReplenishmentPlan:
        """Project monthly replenishment until target is met or max months is reached."""
        if monthly_contribution < 0:
            raise ValueError("monthly_contribution cannot be negative")
        if max_months < 0:
            raise ValueError("max_months cannot be negative")

        target_amount = self.calculate_target_amount(
            target_months=target_months,
            buffer_pct=buffer_pct,
            include_nonessential=include_nonessential,
        )
        balance = self.fund_account.current_balance if self.fund_account else 0.0
        monthly_rate = self.fund_account.monthly_yield_rate if self.fund_account else 0.0

        contribution_total = 0.0
        timeline: list[dict] = []
        months = 0
        now = datetime.now(timezone.utc)

        while months < max_months and balance < target_amount:
            months += 1
            balance += monthly_contribution
            contribution_total += monthly_contribution
            balance *= 1 + monthly_rate

            timeline.append(
                {
                    "month_index": months,
                    "as_of": (now + timedelta(days=30 * months)).isoformat(),
                    "balance": round(balance, 2),
                    "contribution_total": round(contribution_total, 2),
                }
            )

        target_reached = balance >= target_amount
        projected_date = now + timedelta(days=30 * months) if target_reached else None
        starting_balance = self.fund_account.current_balance if self.fund_account else 0.0
        yield_earned = balance - starting_balance - contribution_total

        return ReplenishmentPlan(
            plan_id=str(uuid.uuid4()),
            monthly_contribution=monthly_contribution,
            months_to_target=months,
            target_amount=target_amount,
            projected_balance=round(balance, 2),
            contribution_total=round(contribution_total, 2),
            yield_earned=round(yield_earned, 2),
            target_reached=target_reached,
            projected_target_date=projected_date,
            timeline=timeline,
        )

    def record_withdrawal(
        self,
        amount: float,
        reason: str,
        withdrawn_at: datetime,
    ) -> WithdrawalRecord:
        """Record an emergency fund withdrawal and reduce current balance."""
        if self.fund_account is None:
            raise ValueError("fund account is not configured")
        if amount < 0:
            raise ValueError("amount cannot be negative")

        applied_amount = min(amount, self.fund_account.current_balance)
        self.fund_account.current_balance = max(0.0, self.fund_account.current_balance - applied_amount)

        record = WithdrawalRecord(
            withdrawal_id=str(uuid.uuid4()),
            amount=applied_amount,
            reason=reason,
            withdrawn_at=withdrawn_at,
        )
        self.withdrawals.append(record)
        return record

    @staticmethod
    def _classify_health(months_covered: float, target_months: int) -> FundHealth:
        """Classify emergency fund health based on months covered."""
        if months_covered < 1:
            return FundHealth.CRITICAL
        if months_covered < target_months:
            return FundHealth.UNDERFUNDED
        if months_covered < target_months * 1.5:
            return FundHealth.ADEQUATE
        return FundHealth.STRONG
