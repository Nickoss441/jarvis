"""Retirement planning and projection utilities.

Provides account tracking, deterministic growth projections, and contribution
planning helpers for retirement goals.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from math import isfinite
from typing import Optional
import uuid


class AccountType(str, Enum):
    """Supported retirement account categories."""

    TRADITIONAL_401K = "traditional_401k"
    ROTH_401K = "roth_401k"
    TRADITIONAL_IRA = "traditional_ira"
    ROTH_IRA = "roth_ira"
    TAXABLE_BROKERAGE = "taxable_brokerage"
    PENSION = "pension"
    OTHER = "other"


class ContributionCadence(str, Enum):
    """Contribution timing cadence."""

    MONTHLY = "monthly"
    BIWEEKLY = "biweekly"
    QUARTERLY = "quarterly"
    ANNUAL = "annual"


class RiskProfile(str, Enum):
    """Risk profile presets that map to default annual return assumptions."""

    CONSERVATIVE = "conservative"
    MODERATE = "moderate"
    AGGRESSIVE = "aggressive"


@dataclass
class RetirementAccount:
    """Tracked retirement account with balance and contribution settings."""

    account_id: str
    name: str
    account_type: AccountType
    current_balance: float
    annual_contribution: float
    employer_match_rate: float
    employer_match_cap_pct: float
    created_at: datetime

    def __post_init__(self):
        if self.current_balance < 0:
            raise ValueError("current_balance cannot be negative")
        if self.annual_contribution < 0:
            raise ValueError("annual_contribution cannot be negative")
        if self.employer_match_rate < 0 or self.employer_match_rate > 100:
            raise ValueError("employer_match_rate must be between 0 and 100")
        if self.employer_match_cap_pct < 0 or self.employer_match_cap_pct > 100:
            raise ValueError("employer_match_cap_pct must be between 0 and 100")
        if not isinstance(self.created_at, datetime) or self.created_at.tzinfo is None:
            raise ValueError("created_at must be timezone-aware (UTC)")

    @property
    def estimated_annual_match(self) -> float:
        """Estimated yearly employer match based on configured cap and rate."""
        eligible = self.annual_contribution * (self.employer_match_cap_pct / 100.0)
        return eligible * (self.employer_match_rate / 100.0)

    @property
    def total_annual_addition(self) -> float:
        """Total annual addition from self-contribution and employer match."""
        return self.annual_contribution + self.estimated_annual_match

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "id": self.account_id,
            "name": self.name,
            "type": self.account_type.value,
            "current_balance": self.current_balance,
            "annual_contribution": self.annual_contribution,
            "employer_match_rate": self.employer_match_rate,
            "employer_match_cap_pct": self.employer_match_cap_pct,
            "estimated_annual_match": self.estimated_annual_match,
            "total_annual_addition": self.total_annual_addition,
            "created_at": self.created_at.isoformat(),
        }


@dataclass
class ProjectionPoint:
    """A yearly retirement projection snapshot."""

    year_index: int
    as_of: datetime
    projected_balance: float
    cumulative_contributions: float
    cumulative_growth: float

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "year_index": self.year_index,
            "as_of": self.as_of.isoformat(),
            "projected_balance": self.projected_balance,
            "cumulative_contributions": self.cumulative_contributions,
            "cumulative_growth": self.cumulative_growth,
        }


@dataclass
class RetirementProjection:
    """Summary of retirement growth projection."""

    projection_id: str
    years: int
    annual_return_pct: float
    annual_inflation_pct: float
    starting_balance: float
    ending_balance_nominal: float
    ending_balance_real: float
    total_contributions: float
    total_growth: float
    timeline: list[ProjectionPoint]
    generated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "id": self.projection_id,
            "years": self.years,
            "annual_return_pct": self.annual_return_pct,
            "annual_inflation_pct": self.annual_inflation_pct,
            "starting_balance": self.starting_balance,
            "ending_balance_nominal": self.ending_balance_nominal,
            "ending_balance_real": self.ending_balance_real,
            "total_contributions": self.total_contributions,
            "total_growth": self.total_growth,
            "timeline": [point.to_dict() for point in self.timeline],
            "generated_at": self.generated_at.isoformat(),
        }


@dataclass
class ContributionPlan:
    """Required periodic contribution plan for a target retirement goal."""

    plan_id: str
    target_amount: float
    years_to_target: int
    annual_return_pct: float
    cadence: ContributionCadence
    required_contribution_per_period: float
    periods_per_year: int
    generated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "id": self.plan_id,
            "target_amount": self.target_amount,
            "years_to_target": self.years_to_target,
            "annual_return_pct": self.annual_return_pct,
            "cadence": self.cadence.value,
            "required_contribution_per_period": self.required_contribution_per_period,
            "periods_per_year": self.periods_per_year,
            "generated_at": self.generated_at.isoformat(),
        }


class RetirementPlanner:
    """Planner for retirement growth and contribution strategies."""

    DEFAULT_RETURNS = {
        RiskProfile.CONSERVATIVE: 4.5,
        RiskProfile.MODERATE: 6.5,
        RiskProfile.AGGRESSIVE: 8.5,
    }

    CADENCE_PERIODS_PER_YEAR = {
        ContributionCadence.MONTHLY: 12,
        ContributionCadence.BIWEEKLY: 26,
        ContributionCadence.QUARTERLY: 4,
        ContributionCadence.ANNUAL: 1,
    }

    def __init__(self):
        self.accounts: dict[str, RetirementAccount] = {}

    def add_account(
        self,
        name: str,
        account_type: AccountType,
        current_balance: float,
        annual_contribution: float,
        employer_match_rate: float,
        employer_match_cap_pct: float,
        created_at: datetime,
    ) -> RetirementAccount:
        """Create and register a retirement account."""
        account = RetirementAccount(
            account_id=str(uuid.uuid4()),
            name=name,
            account_type=account_type,
            current_balance=current_balance,
            annual_contribution=annual_contribution,
            employer_match_rate=employer_match_rate,
            employer_match_cap_pct=employer_match_cap_pct,
            created_at=created_at,
        )
        self.accounts[account.account_id] = account
        return account

    def get_total_balance(self) -> float:
        """Return total current balance across tracked accounts."""
        return sum(account.current_balance for account in self.accounts.values())

    def get_total_annual_contributions(self) -> float:
        """Return total annual additions including employer match."""
        return sum(account.total_annual_addition for account in self.accounts.values())

    def get_default_return_assumption(self, risk_profile: RiskProfile) -> float:
        """Resolve annual return assumption by risk profile."""
        return self.DEFAULT_RETURNS[risk_profile]

    def project_retirement_growth(
        self,
        years: int,
        annual_return_pct: Optional[float] = None,
        risk_profile: RiskProfile = RiskProfile.MODERATE,
        annual_inflation_pct: float = 2.5,
    ) -> RetirementProjection:
        """Project retirement portfolio growth over a fixed number of years."""
        if years < 0:
            raise ValueError("years cannot be negative")
        if annual_inflation_pct < 0 or not isfinite(annual_inflation_pct):
            raise ValueError("annual_inflation_pct must be a non-negative finite number")
        if annual_return_pct is None:
            annual_return_pct = self.get_default_return_assumption(risk_profile)
        if not isfinite(annual_return_pct):
            raise ValueError("annual_return_pct must be finite")

        start_balance = self.get_total_balance()
        annual_additions = self.get_total_annual_contributions()

        balance = start_balance
        total_contributions = 0.0
        timeline: list[ProjectionPoint] = []

        now = datetime.now(timezone.utc)
        for year_index in range(1, years + 1):
            balance += annual_additions
            total_contributions += annual_additions
            balance *= 1 + (annual_return_pct / 100.0)

            timeline.append(
                ProjectionPoint(
                    year_index=year_index,
                    as_of=now + timedelta(days=365 * year_index),
                    projected_balance=round(balance, 2),
                    cumulative_contributions=round(total_contributions, 2),
                    cumulative_growth=round(balance - start_balance - total_contributions, 2),
                )
            )

        real_balance = self._to_real_dollars(balance, annual_inflation_pct, years)

        return RetirementProjection(
            projection_id=str(uuid.uuid4()),
            years=years,
            annual_return_pct=annual_return_pct,
            annual_inflation_pct=annual_inflation_pct,
            starting_balance=round(start_balance, 2),
            ending_balance_nominal=round(balance, 2),
            ending_balance_real=round(real_balance, 2),
            total_contributions=round(total_contributions, 2),
            total_growth=round(balance - start_balance - total_contributions, 2),
            timeline=timeline,
        )

    def estimate_required_contribution(
        self,
        target_amount: float,
        years_to_target: int,
        cadence: ContributionCadence,
        annual_return_pct: Optional[float] = None,
        risk_profile: RiskProfile = RiskProfile.MODERATE,
    ) -> ContributionPlan:
        """Estimate required periodic contribution to hit a target amount."""
        if target_amount < 0:
            raise ValueError("target_amount cannot be negative")
        if years_to_target < 0:
            raise ValueError("years_to_target cannot be negative")

        if annual_return_pct is None:
            annual_return_pct = self.get_default_return_assumption(risk_profile)
        if not isfinite(annual_return_pct):
            raise ValueError("annual_return_pct must be finite")

        periods_per_year = self.CADENCE_PERIODS_PER_YEAR[cadence]
        periods = years_to_target * periods_per_year
        periodic_rate = (annual_return_pct / 100.0) / periods_per_year

        current_balance = self.get_total_balance()

        if periods == 0:
            required = max(0.0, target_amount - current_balance)
        else:
            future_value_current = current_balance * ((1 + periodic_rate) ** periods)
            gap = max(0.0, target_amount - future_value_current)

            if periodic_rate == 0:
                required = gap / periods
            else:
                annuity_factor = (((1 + periodic_rate) ** periods) - 1) / periodic_rate
                required = gap / annuity_factor

        return ContributionPlan(
            plan_id=str(uuid.uuid4()),
            target_amount=target_amount,
            years_to_target=years_to_target,
            annual_return_pct=annual_return_pct,
            cadence=cadence,
            required_contribution_per_period=round(required, 2),
            periods_per_year=periods_per_year,
        )

    def estimate_safe_withdrawal_income(
        self,
        withdrawal_rate_pct: float = 4.0,
        annual_tax_drag_pct: float = 0.0,
    ) -> dict:
        """Estimate gross and net annual/monthly income from portfolio."""
        if withdrawal_rate_pct < 0 or withdrawal_rate_pct > 100:
            raise ValueError("withdrawal_rate_pct must be between 0 and 100")
        if annual_tax_drag_pct < 0 or annual_tax_drag_pct > 100:
            raise ValueError("annual_tax_drag_pct must be between 0 and 100")

        balance = self.get_total_balance()
        gross_annual = balance * (withdrawal_rate_pct / 100.0)
        net_annual = gross_annual * (1 - (annual_tax_drag_pct / 100.0))

        return {
            "portfolio_balance": round(balance, 2),
            "withdrawal_rate_pct": withdrawal_rate_pct,
            "annual_tax_drag_pct": annual_tax_drag_pct,
            "gross_annual_income": round(gross_annual, 2),
            "gross_monthly_income": round(gross_annual / 12.0, 2),
            "net_annual_income": round(net_annual, 2),
            "net_monthly_income": round(net_annual / 12.0, 2),
        }

    @staticmethod
    def _to_real_dollars(nominal: float, inflation_pct: float, years: int) -> float:
        """Discount nominal value into present-value dollars."""
        if years <= 0 or inflation_pct == 0:
            return nominal
        return nominal / ((1 + (inflation_pct / 100.0)) ** years)
