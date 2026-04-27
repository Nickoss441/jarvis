"""College savings planning and education funding projection utilities.

Provides education-cost inflation modeling, savings growth projections,
required contribution estimates, and college funding readiness snapshots.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from math import isfinite
from typing import Optional
import uuid


class EducationStage(str, Enum):
    """Supported education cost profiles."""

    COMMUNITY_COLLEGE = "community_college"
    IN_STATE_PUBLIC = "in_state_public"
    OUT_OF_STATE_PUBLIC = "out_of_state_public"
    PRIVATE = "private"


class SavingsAccountType(str, Enum):
    """Supported college savings account types."""

    PLAN_529 = "529"
    COVERDELL = "coverdell"
    TAXABLE = "taxable"
    SAVINGS = "savings"
    OTHER = "other"


class ReadinessStatus(str, Enum):
    """Funding readiness based on projected coverage ratio."""

    UNDERFUNDED = "underfunded"
    ON_TRACK = "on_track"
    FULLY_FUNDED = "fully_funded"
    OVERFUNDED = "overfunded"


@dataclass
class StudentProfile:
    """Student and education timing assumptions."""

    student_name: str
    current_age: int
    college_start_age: int
    years_of_college: int
    education_stage: EducationStage
    education_inflation_pct: float
    created_at: datetime

    def __post_init__(self):
        if self.current_age < 0:
            raise ValueError("current_age cannot be negative")
        if self.college_start_age < 0:
            raise ValueError("college_start_age cannot be negative")
        if self.college_start_age < self.current_age:
            raise ValueError("college_start_age cannot be earlier than current_age")
        if self.years_of_college <= 0:
            raise ValueError("years_of_college must be positive")
        if self.education_inflation_pct < 0 or not isfinite(self.education_inflation_pct):
            raise ValueError("education_inflation_pct must be a non-negative finite number")
        if not isinstance(self.created_at, datetime) or self.created_at.tzinfo is None:
            raise ValueError("created_at must be timezone-aware (UTC)")

    @property
    def years_until_college(self) -> int:
        """Years remaining until college starts."""
        return max(0, self.college_start_age - self.current_age)

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "student_name": self.student_name,
            "current_age": self.current_age,
            "college_start_age": self.college_start_age,
            "years_until_college": self.years_until_college,
            "years_of_college": self.years_of_college,
            "education_stage": self.education_stage.value,
            "education_inflation_pct": self.education_inflation_pct,
            "created_at": self.created_at.isoformat(),
        }


@dataclass
class CollegeSavingsAccount:
    """Current college savings account and return assumptions."""

    account_type: SavingsAccountType
    current_balance: float
    annual_contribution: float
    expected_return_pct: float
    created_at: datetime

    def __post_init__(self):
        if self.current_balance < 0:
            raise ValueError("current_balance cannot be negative")
        if self.annual_contribution < 0:
            raise ValueError("annual_contribution cannot be negative")
        if not isfinite(self.expected_return_pct):
            raise ValueError("expected_return_pct must be finite")
        if not isinstance(self.created_at, datetime) or self.created_at.tzinfo is None:
            raise ValueError("created_at must be timezone-aware (UTC)")

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "account_type": self.account_type.value,
            "current_balance": self.current_balance,
            "annual_contribution": self.annual_contribution,
            "expected_return_pct": self.expected_return_pct,
            "created_at": self.created_at.isoformat(),
        }


@dataclass
class SavingsProjection:
    """Projected savings growth until or through a target horizon."""

    projection_id: str
    years: int
    starting_balance: float
    ending_balance: float
    total_contributions: float
    total_growth: float
    timeline: list[dict]
    generated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "id": self.projection_id,
            "years": self.years,
            "starting_balance": self.starting_balance,
            "ending_balance": self.ending_balance,
            "total_contributions": self.total_contributions,
            "total_growth": self.total_growth,
            "timeline": self.timeline,
            "generated_at": self.generated_at.isoformat(),
        }


@dataclass
class ContributionPlan:
    """Required contribution plan to fully fund projected college costs."""

    plan_id: str
    target_amount: float
    years_until_college: int
    monthly_contribution_required: float
    projected_shortfall_without_change: float
    generated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "id": self.plan_id,
            "target_amount": self.target_amount,
            "years_until_college": self.years_until_college,
            "monthly_contribution_required": self.monthly_contribution_required,
            "projected_shortfall_without_change": self.projected_shortfall_without_change,
            "generated_at": self.generated_at.isoformat(),
        }


@dataclass
class FundingSnapshot:
    """Current college funding readiness summary."""

    projected_total_cost: float
    projected_savings_at_start: float
    funding_gap: float
    funding_ratio_pct: float
    readiness_status: ReadinessStatus
    years_until_college: int
    generated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "projected_total_cost": self.projected_total_cost,
            "projected_savings_at_start": self.projected_savings_at_start,
            "funding_gap": self.funding_gap,
            "funding_ratio_pct": self.funding_ratio_pct,
            "readiness_status": self.readiness_status.value,
            "years_until_college": self.years_until_college,
            "generated_at": self.generated_at.isoformat(),
        }


class CollegeSavingsPlanner:
    """Planner for college savings growth and education funding readiness."""

    DEFAULT_ANNUAL_COSTS = {
        EducationStage.COMMUNITY_COLLEGE: 6000.0,
        EducationStage.IN_STATE_PUBLIC: 25000.0,
        EducationStage.OUT_OF_STATE_PUBLIC: 42000.0,
        EducationStage.PRIVATE: 58000.0,
    }

    def __init__(self):
        self.student_profile: Optional[StudentProfile] = None
        self.savings_account: Optional[CollegeSavingsAccount] = None

    def set_student_profile(
        self,
        student_name: str,
        current_age: int,
        college_start_age: int,
        years_of_college: int,
        education_stage: EducationStage,
        education_inflation_pct: float,
        created_at: datetime,
    ) -> StudentProfile:
        """Set or replace the student profile."""
        profile = StudentProfile(
            student_name=student_name,
            current_age=current_age,
            college_start_age=college_start_age,
            years_of_college=years_of_college,
            education_stage=education_stage,
            education_inflation_pct=education_inflation_pct,
            created_at=created_at,
        )
        self.student_profile = profile
        return profile

    def set_savings_account(
        self,
        account_type: SavingsAccountType,
        current_balance: float,
        annual_contribution: float,
        expected_return_pct: float,
        created_at: datetime,
    ) -> CollegeSavingsAccount:
        """Set or replace the college savings account."""
        account = CollegeSavingsAccount(
            account_type=account_type,
            current_balance=current_balance,
            annual_contribution=annual_contribution,
            expected_return_pct=expected_return_pct,
            created_at=created_at,
        )
        self.savings_account = account
        return account

    def calculate_projected_total_cost(self, current_annual_cost: Optional[float] = None) -> float:
        """Project total college cost at enrollment and across all study years."""
        profile = self._require_student_profile()
        annual_cost = self._resolve_annual_cost(current_annual_cost)

        total_cost = 0.0
        for year_index in range(profile.years_of_college):
            inflated = annual_cost * (
                (1 + (profile.education_inflation_pct / 100.0))
                ** (profile.years_until_college + year_index)
            )
            total_cost += inflated
        return round(total_cost, 2)

    def project_savings_growth(self, years: Optional[int] = None) -> SavingsProjection:
        """Project savings growth over a target horizon."""
        profile = self._require_student_profile()
        account = self._require_savings_account()
        if years is None:
            years = profile.years_until_college
        if years < 0:
            raise ValueError("years cannot be negative")

        balance = account.current_balance
        starting_balance = balance
        total_contributions = 0.0
        timeline: list[dict] = []
        now = datetime.now(timezone.utc)

        for year_index in range(1, years + 1):
            balance += account.annual_contribution
            total_contributions += account.annual_contribution
            balance *= 1 + (account.expected_return_pct / 100.0)
            timeline.append(
                {
                    "year_index": year_index,
                    "as_of": (now + timedelta(days=365 * year_index)).isoformat(),
                    "student_age": profile.current_age + year_index,
                    "projected_balance": round(balance, 2),
                }
            )

        return SavingsProjection(
            projection_id=str(uuid.uuid4()),
            years=years,
            starting_balance=round(starting_balance, 2),
            ending_balance=round(balance, 2),
            total_contributions=round(total_contributions, 2),
            total_growth=round(balance - starting_balance - total_contributions, 2),
            timeline=timeline,
        )

    def estimate_required_monthly_contribution(
        self,
        current_annual_cost: Optional[float] = None,
    ) -> ContributionPlan:
        """Estimate monthly contribution required to fully fund projected costs."""
        profile = self._require_student_profile()
        account = self._require_savings_account()
        target_amount = self.calculate_projected_total_cost(current_annual_cost=current_annual_cost)
        baseline_projection = self.project_savings_growth(profile.years_until_college)
        shortfall = max(0.0, target_amount - baseline_projection.ending_balance)

        months = profile.years_until_college * 12
        monthly_rate = (account.expected_return_pct / 100.0) / 12.0
        if shortfall == 0:
            required = 0.0
        elif months == 0:
            required = shortfall
        elif monthly_rate == 0:
            required = shortfall / months
        else:
            annuity_factor = (((1 + monthly_rate) ** months) - 1) / monthly_rate
            required = shortfall / annuity_factor

        return ContributionPlan(
            plan_id=str(uuid.uuid4()),
            target_amount=target_amount,
            years_until_college=profile.years_until_college,
            monthly_contribution_required=round(required, 2),
            projected_shortfall_without_change=round(shortfall, 2),
        )

    def get_funding_snapshot(self, current_annual_cost: Optional[float] = None) -> FundingSnapshot:
        """Return projected funding readiness at the start of college."""
        profile = self._require_student_profile()
        target_amount = self.calculate_projected_total_cost(current_annual_cost=current_annual_cost)
        projection = self.project_savings_growth(profile.years_until_college)
        projected_balance = projection.ending_balance
        gap = max(0.0, target_amount - projected_balance)
        funding_ratio_pct = 100.0 if target_amount == 0 else (projected_balance / target_amount) * 100.0

        if funding_ratio_pct > 105:
            readiness_status = ReadinessStatus.OVERFUNDED
        elif funding_ratio_pct >= 100:
            readiness_status = ReadinessStatus.FULLY_FUNDED
        elif funding_ratio_pct >= 80:
            readiness_status = ReadinessStatus.ON_TRACK
        else:
            readiness_status = ReadinessStatus.UNDERFUNDED

        return FundingSnapshot(
            projected_total_cost=target_amount,
            projected_savings_at_start=projected_balance,
            funding_gap=round(gap, 2),
            funding_ratio_pct=round(funding_ratio_pct, 2),
            readiness_status=readiness_status,
            years_until_college=profile.years_until_college,
        )

    def _resolve_annual_cost(self, current_annual_cost: Optional[float]) -> float:
        """Resolve current annual cost from override or stage default."""
        if current_annual_cost is None:
            profile = self._require_student_profile()
            return self.DEFAULT_ANNUAL_COSTS[profile.education_stage]
        if current_annual_cost < 0:
            raise ValueError("current_annual_cost cannot be negative")
        return current_annual_cost

    def _require_student_profile(self) -> StudentProfile:
        """Return configured student profile or raise."""
        if self.student_profile is None:
            raise ValueError("student_profile is required")
        return self.student_profile

    def _require_savings_account(self) -> CollegeSavingsAccount:
        """Return configured savings account or raise."""
        if self.savings_account is None:
            raise ValueError("savings_account is required")
        return self.savings_account