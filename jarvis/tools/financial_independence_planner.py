"""Financial independence planning and FIRE-style projection utilities.

Provides income and expense profiling, FI-number estimation, savings rate
analysis, coast-FI modeling, and deterministic time-to-independence
projections.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from math import isfinite, log
from typing import Optional
import uuid


class LifestyleProfile(str, Enum):
    """High-level spending posture for FI planning."""

    LEAN = "lean"
    STANDARD = "standard"
    FAT = "fat"


@dataclass
class IncomeProfile:
    """After-tax income inputs for FI analysis."""

    monthly_income: float
    annual_bonus: float
    created_at: datetime

    def __post_init__(self):
        if self.monthly_income < 0:
            raise ValueError("monthly_income cannot be negative")
        if self.annual_bonus < 0:
            raise ValueError("annual_bonus cannot be negative")
        if not isinstance(self.created_at, datetime) or self.created_at.tzinfo is None:
            raise ValueError("created_at must be timezone-aware (UTC)")

    @property
    def annual_income(self) -> float:
        """Annualized after-tax income."""
        return self.monthly_income * 12 + self.annual_bonus

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "monthly_income": self.monthly_income,
            "annual_bonus": self.annual_bonus,
            "annual_income": self.annual_income,
            "created_at": self.created_at.isoformat(),
        }


@dataclass
class ExpenseProfile:
    """Expense inputs for FI analysis."""

    essential_monthly: float
    discretionary_monthly: float
    annual_irregular: float
    lifestyle_profile: LifestyleProfile
    created_at: datetime

    def __post_init__(self):
        if self.essential_monthly < 0:
            raise ValueError("essential_monthly cannot be negative")
        if self.discretionary_monthly < 0:
            raise ValueError("discretionary_monthly cannot be negative")
        if self.annual_irregular < 0:
            raise ValueError("annual_irregular cannot be negative")
        if not isinstance(self.created_at, datetime) or self.created_at.tzinfo is None:
            raise ValueError("created_at must be timezone-aware (UTC)")

    @property
    def annual_expenses(self) -> float:
        """Annualized total expenses."""
        return (self.essential_monthly + self.discretionary_monthly) * 12 + self.annual_irregular

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "essential_monthly": self.essential_monthly,
            "discretionary_monthly": self.discretionary_monthly,
            "annual_irregular": self.annual_irregular,
            "lifestyle_profile": self.lifestyle_profile.value,
            "annual_expenses": self.annual_expenses,
            "created_at": self.created_at.isoformat(),
        }


@dataclass
class InvestmentPortfolio:
    """Current invested asset base and core assumptions."""

    invested_assets: float
    annual_return_pct: float
    safe_withdrawal_rate_pct: float
    created_at: datetime

    def __post_init__(self):
        if self.invested_assets < 0:
            raise ValueError("invested_assets cannot be negative")
        if not isfinite(self.annual_return_pct):
            raise ValueError("annual_return_pct must be finite")
        if self.safe_withdrawal_rate_pct <= 0 or self.safe_withdrawal_rate_pct > 100:
            raise ValueError("safe_withdrawal_rate_pct must be between 0 and 100")
        if not isinstance(self.created_at, datetime) or self.created_at.tzinfo is None:
            raise ValueError("created_at must be timezone-aware (UTC)")

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "invested_assets": self.invested_assets,
            "annual_return_pct": self.annual_return_pct,
            "safe_withdrawal_rate_pct": self.safe_withdrawal_rate_pct,
            "created_at": self.created_at.isoformat(),
        }


@dataclass
class IndependenceSnapshot:
    """Current FI positioning snapshot."""

    annual_income: float
    annual_expenses: float
    annual_savings: float
    savings_rate_pct: float
    fi_number: float
    portfolio_balance: float
    fi_progress_pct: float
    coast_fi_number: float
    as_of: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "annual_income": self.annual_income,
            "annual_expenses": self.annual_expenses,
            "annual_savings": self.annual_savings,
            "savings_rate_pct": self.savings_rate_pct,
            "fi_number": self.fi_number,
            "portfolio_balance": self.portfolio_balance,
            "fi_progress_pct": self.fi_progress_pct,
            "coast_fi_number": self.coast_fi_number,
            "as_of": self.as_of.isoformat(),
        }


@dataclass
class IndependenceProjection:
    """Projection to financial independence."""

    projection_id: str
    monthly_investment: float
    years_to_fi: int
    fi_number: float
    projected_balance: float
    target_reached: bool
    projected_fi_date: Optional[datetime]
    timeline: list[dict]
    generated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "id": self.projection_id,
            "monthly_investment": self.monthly_investment,
            "years_to_fi": self.years_to_fi,
            "fi_number": self.fi_number,
            "projected_balance": self.projected_balance,
            "target_reached": self.target_reached,
            "projected_fi_date": self.projected_fi_date.isoformat() if self.projected_fi_date else None,
            "timeline": self.timeline,
            "generated_at": self.generated_at.isoformat(),
        }


class FinancialIndependencePlanner:
    """Planner for financial independence targets and projection."""

    def __init__(self):
        self.income_profile: Optional[IncomeProfile] = None
        self.expense_profile: Optional[ExpenseProfile] = None
        self.portfolio: Optional[InvestmentPortfolio] = None

    def set_income_profile(
        self,
        monthly_income: float,
        annual_bonus: float,
        created_at: datetime,
    ) -> IncomeProfile:
        """Set or replace income profile."""
        profile = IncomeProfile(
            monthly_income=monthly_income,
            annual_bonus=annual_bonus,
            created_at=created_at,
        )
        self.income_profile = profile
        return profile

    def set_expense_profile(
        self,
        essential_monthly: float,
        discretionary_monthly: float,
        annual_irregular: float,
        lifestyle_profile: LifestyleProfile,
        created_at: datetime,
    ) -> ExpenseProfile:
        """Set or replace expense profile."""
        profile = ExpenseProfile(
            essential_monthly=essential_monthly,
            discretionary_monthly=discretionary_monthly,
            annual_irregular=annual_irregular,
            lifestyle_profile=lifestyle_profile,
            created_at=created_at,
        )
        self.expense_profile = profile
        return profile

    def set_portfolio(
        self,
        invested_assets: float,
        annual_return_pct: float,
        safe_withdrawal_rate_pct: float,
        created_at: datetime,
    ) -> InvestmentPortfolio:
        """Set or replace portfolio assumptions."""
        portfolio = InvestmentPortfolio(
            invested_assets=invested_assets,
            annual_return_pct=annual_return_pct,
            safe_withdrawal_rate_pct=safe_withdrawal_rate_pct,
            created_at=created_at,
        )
        self.portfolio = portfolio
        return portfolio

    def get_annual_income(self) -> float:
        """Get annual income or zero if unset."""
        return self.income_profile.annual_income if self.income_profile else 0.0

    def get_annual_expenses(self) -> float:
        """Get annual expenses or zero if unset."""
        return self.expense_profile.annual_expenses if self.expense_profile else 0.0

    def get_annual_savings_capacity(self) -> float:
        """Annual income minus annual expenses."""
        return self.get_annual_income() - self.get_annual_expenses()

    def get_savings_rate(self) -> float:
        """Savings rate as a percentage of annual income."""
        annual_income = self.get_annual_income()
        if annual_income == 0:
            return 0.0
        return (self.get_annual_savings_capacity() / annual_income) * 100.0

    def calculate_fi_number(
        self,
        annual_expenses_override: Optional[float] = None,
        withdrawal_rate_override_pct: Optional[float] = None,
    ) -> float:
        """Calculate FI number from expenses and safe withdrawal rate."""
        annual_expenses = self.get_annual_expenses() if annual_expenses_override is None else annual_expenses_override
        if annual_expenses < 0:
            raise ValueError("annual_expenses cannot be negative")

        if withdrawal_rate_override_pct is None:
            withdrawal_rate = self.portfolio.safe_withdrawal_rate_pct if self.portfolio else 4.0
        else:
            withdrawal_rate = withdrawal_rate_override_pct
        if withdrawal_rate <= 0 or withdrawal_rate > 100:
            raise ValueError("withdrawal_rate must be between 0 and 100")

        return round(annual_expenses / (withdrawal_rate / 100.0), 2) if annual_expenses else 0.0

    def calculate_coast_fi_number(
        self,
        current_age: int,
        retirement_age: int,
        annual_expenses_override: Optional[float] = None,
    ) -> float:
        """Current portfolio needed such that no more contributions are required."""
        if current_age < 0 or retirement_age < 0:
            raise ValueError("ages cannot be negative")
        if retirement_age < current_age:
            raise ValueError("retirement_age cannot be earlier than current_age")

        years = retirement_age - current_age
        fi_number = self.calculate_fi_number(annual_expenses_override=annual_expenses_override)
        if years == 0:
            return fi_number

        annual_return_pct = self.portfolio.annual_return_pct if self.portfolio else 7.0
        if not isfinite(annual_return_pct):
            raise ValueError("annual_return_pct must be finite")

        return round(fi_number / ((1 + (annual_return_pct / 100.0)) ** years), 2)

    def get_independence_snapshot(
        self,
        current_age: int = 35,
        retirement_age: int = 60,
    ) -> IndependenceSnapshot:
        """Return a snapshot of current FI progress."""
        annual_income = self.get_annual_income()
        annual_expenses = self.get_annual_expenses()
        annual_savings = self.get_annual_savings_capacity()
        savings_rate_pct = round(self.get_savings_rate(), 2)
        fi_number = self.calculate_fi_number()
        portfolio_balance = self.portfolio.invested_assets if self.portfolio else 0.0
        fi_progress_pct = 100.0 if fi_number == 0 else min(100.0, (portfolio_balance / fi_number) * 100.0)
        coast_fi_number = self.calculate_coast_fi_number(current_age=current_age, retirement_age=retirement_age)

        return IndependenceSnapshot(
            annual_income=round(annual_income, 2),
            annual_expenses=round(annual_expenses, 2),
            annual_savings=round(annual_savings, 2),
            savings_rate_pct=savings_rate_pct,
            fi_number=fi_number,
            portfolio_balance=round(portfolio_balance, 2),
            fi_progress_pct=round(fi_progress_pct, 2),
            coast_fi_number=coast_fi_number,
        )

    def estimate_required_monthly_investment(self, target_years: int) -> float:
        """Estimate monthly investment needed to reach FI in target years."""
        if target_years < 0:
            raise ValueError("target_years cannot be negative")

        fi_number = self.calculate_fi_number()
        current_balance = self.portfolio.invested_assets if self.portfolio else 0.0
        annual_return_pct = self.portfolio.annual_return_pct if self.portfolio else 7.0
        if not isfinite(annual_return_pct):
            raise ValueError("annual_return_pct must be finite")

        periods = target_years * 12
        monthly_rate = (annual_return_pct / 100.0) / 12.0

        if periods == 0:
            return round(max(0.0, fi_number - current_balance), 2)

        future_value_current = current_balance * ((1 + monthly_rate) ** periods)
        gap = max(0.0, fi_number - future_value_current)
        if gap == 0:
            return 0.0

        if monthly_rate == 0:
            return round(gap / periods, 2)

        annuity_factor = (((1 + monthly_rate) ** periods) - 1) / monthly_rate
        return round(gap / annuity_factor, 2)

    def project_to_financial_independence(
        self,
        monthly_investment: float,
        max_years: int = 60,
    ) -> IndependenceProjection:
        """Project annual portfolio growth until FI target is reached or capped."""
        if monthly_investment < 0:
            raise ValueError("monthly_investment cannot be negative")
        if max_years < 0:
            raise ValueError("max_years cannot be negative")

        fi_number = self.calculate_fi_number()
        balance = self.portfolio.invested_assets if self.portfolio else 0.0
        annual_return_pct = self.portfolio.annual_return_pct if self.portfolio else 7.0
        annual_contribution = monthly_investment * 12.0
        years = 0
        timeline: list[dict] = []
        now = datetime.now(timezone.utc)

        while years < max_years and balance < fi_number:
            years += 1
            balance += annual_contribution
            balance *= 1 + (annual_return_pct / 100.0)
            timeline.append(
                {
                    "year_index": years,
                    "as_of": (now + timedelta(days=365 * years)).isoformat(),
                    "balance": round(balance, 2),
                }
            )

        target_reached = balance >= fi_number
        fi_date = now + timedelta(days=365 * years) if target_reached else None

        return IndependenceProjection(
            projection_id=str(uuid.uuid4()),
            monthly_investment=monthly_investment,
            years_to_fi=years,
            fi_number=fi_number,
            projected_balance=round(balance, 2),
            target_reached=target_reached,
            projected_fi_date=fi_date,
            timeline=timeline,
        )
