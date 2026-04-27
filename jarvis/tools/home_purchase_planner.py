"""Home purchase affordability and mortgage planning utilities.

Provides deterministic purchase-budget estimation, mortgage payment helpers,
cash-to-close planning, and down payment timeline projections.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from math import ceil, isfinite
from typing import Optional
import uuid


class PropertyType(str, Enum):
    """Supported property categories."""

    SINGLE_FAMILY = "single_family"
    CONDO = "condo"
    TOWNHOME = "townhome"
    MULTI_FAMILY = "multi_family"


class AffordabilityBand(str, Enum):
    """Simple affordability labeling based on price-to-income ratio."""

    COMFORTABLE = "comfortable"
    BALANCED = "balanced"
    STRETCH = "stretch"


@dataclass
class PurchaseProfile:
    """Income, debt, and cash assumptions for a home purchase."""

    gross_annual_income: float
    monthly_debt_payments: float
    available_cash: float
    desired_down_payment_pct: float
    target_housing_ratio_pct: float
    created_at: datetime

    def __post_init__(self):
        if self.gross_annual_income < 0:
            raise ValueError("gross_annual_income cannot be negative")
        if self.monthly_debt_payments < 0:
            raise ValueError("monthly_debt_payments cannot be negative")
        if self.available_cash < 0:
            raise ValueError("available_cash cannot be negative")
        if self.desired_down_payment_pct < 0 or self.desired_down_payment_pct > 100:
            raise ValueError("desired_down_payment_pct must be between 0 and 100")
        if self.target_housing_ratio_pct < 0 or self.target_housing_ratio_pct > 100:
            raise ValueError("target_housing_ratio_pct must be between 0 and 100")
        if not isinstance(self.created_at, datetime) or self.created_at.tzinfo is None:
            raise ValueError("created_at must be timezone-aware (UTC)")

    @property
    def gross_monthly_income(self) -> float:
        """Monthly gross income."""
        return self.gross_annual_income / 12.0

    @property
    def monthly_housing_budget(self) -> float:
        """Target monthly budget available for housing costs."""
        return round(
            max(
                0.0,
                (self.gross_monthly_income * (self.target_housing_ratio_pct / 100.0))
                - self.monthly_debt_payments,
            ),
            2,
        )

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "gross_annual_income": self.gross_annual_income,
            "gross_monthly_income": self.gross_monthly_income,
            "monthly_debt_payments": self.monthly_debt_payments,
            "available_cash": self.available_cash,
            "desired_down_payment_pct": self.desired_down_payment_pct,
            "target_housing_ratio_pct": self.target_housing_ratio_pct,
            "monthly_housing_budget": self.monthly_housing_budget,
            "created_at": self.created_at.isoformat(),
        }


@dataclass
class MortgageScenario:
    """Mortgage and ownership-cost scenario for a given purchase price."""

    scenario_id: str
    property_price: float
    property_type: PropertyType
    down_payment: float
    loan_amount: float
    annual_interest_rate_pct: float
    loan_term_years: int
    property_tax_rate_pct: float
    annual_home_insurance: float
    monthly_hoa: float
    private_mortgage_insurance_pct: float
    created_at: datetime

    def __post_init__(self):
        if self.property_price < 0:
            raise ValueError("property_price cannot be negative")
        if self.down_payment < 0:
            raise ValueError("down_payment cannot be negative")
        if self.loan_amount < 0:
            raise ValueError("loan_amount cannot be negative")
        if self.down_payment > self.property_price:
            raise ValueError("down_payment cannot exceed property_price")
        if self.loan_amount > self.property_price:
            raise ValueError("loan_amount cannot exceed property_price")
        if self.annual_interest_rate_pct < 0 or not isfinite(self.annual_interest_rate_pct):
            raise ValueError("annual_interest_rate_pct must be a non-negative finite number")
        if self.loan_term_years <= 0:
            raise ValueError("loan_term_years must be positive")
        if self.property_tax_rate_pct < 0 or not isfinite(self.property_tax_rate_pct):
            raise ValueError("property_tax_rate_pct must be a non-negative finite number")
        if self.annual_home_insurance < 0:
            raise ValueError("annual_home_insurance cannot be negative")
        if self.monthly_hoa < 0:
            raise ValueError("monthly_hoa cannot be negative")
        if self.private_mortgage_insurance_pct < 0 or self.private_mortgage_insurance_pct > 100:
            raise ValueError("private_mortgage_insurance_pct must be between 0 and 100")
        if not isinstance(self.created_at, datetime) or self.created_at.tzinfo is None:
            raise ValueError("created_at must be timezone-aware (UTC)")

    @property
    def down_payment_pct(self) -> float:
        """Down payment percentage of the purchase price."""
        if self.property_price == 0:
            return 0.0
        return (self.down_payment / self.property_price) * 100.0

    @property
    def monthly_principal_interest(self) -> float:
        """Monthly mortgage principal and interest payment."""
        if self.loan_amount == 0:
            return 0.0
        monthly_rate = (self.annual_interest_rate_pct / 100.0) / 12.0
        periods = self.loan_term_years * 12
        if monthly_rate == 0:
            return self.loan_amount / periods
        growth_factor = (1 + monthly_rate) ** periods
        return self.loan_amount * ((monthly_rate * growth_factor) / (growth_factor - 1))

    @property
    def monthly_property_tax(self) -> float:
        """Monthly property tax estimate."""
        return (self.property_price * (self.property_tax_rate_pct / 100.0)) / 12.0

    @property
    def monthly_home_insurance(self) -> float:
        """Monthly insurance estimate."""
        return self.annual_home_insurance / 12.0

    @property
    def monthly_pmi(self) -> float:
        """Monthly PMI estimate based on the loan amount."""
        if self.down_payment_pct >= 20:
            return 0.0
        return (self.loan_amount * (self.private_mortgage_insurance_pct / 100.0)) / 12.0

    @property
    def total_monthly_housing_cost(self) -> float:
        """Total estimated monthly ownership cost."""
        return (
            self.monthly_principal_interest
            + self.monthly_property_tax
            + self.monthly_home_insurance
            + self.monthly_hoa
            + self.monthly_pmi
        )

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "id": self.scenario_id,
            "property_price": self.property_price,
            "property_type": self.property_type.value,
            "down_payment": self.down_payment,
            "down_payment_pct": self.down_payment_pct,
            "loan_amount": self.loan_amount,
            "annual_interest_rate_pct": self.annual_interest_rate_pct,
            "loan_term_years": self.loan_term_years,
            "property_tax_rate_pct": self.property_tax_rate_pct,
            "annual_home_insurance": self.annual_home_insurance,
            "monthly_hoa": self.monthly_hoa,
            "private_mortgage_insurance_pct": self.private_mortgage_insurance_pct,
            "monthly_principal_interest": round(self.monthly_principal_interest, 2),
            "monthly_property_tax": round(self.monthly_property_tax, 2),
            "monthly_home_insurance": round(self.monthly_home_insurance, 2),
            "monthly_pmi": round(self.monthly_pmi, 2),
            "total_monthly_housing_cost": round(self.total_monthly_housing_cost, 2),
            "created_at": self.created_at.isoformat(),
        }


@dataclass
class ClosingCostEstimate:
    """Estimated closing costs and total cash required."""

    estimate_id: str
    purchase_price: float
    down_payment: float
    closing_cost_pct: float
    estimated_closing_costs: float
    total_cash_required: float
    generated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "id": self.estimate_id,
            "purchase_price": self.purchase_price,
            "down_payment": self.down_payment,
            "closing_cost_pct": self.closing_cost_pct,
            "estimated_closing_costs": self.estimated_closing_costs,
            "total_cash_required": self.total_cash_required,
            "generated_at": self.generated_at.isoformat(),
        }


@dataclass
class DownPaymentPlan:
    """Cash accumulation plan for down payment and closing costs."""

    plan_id: str
    target_home_price: float
    required_down_payment: float
    estimated_closing_costs: float
    total_cash_needed: float
    current_cash: float
    cash_gap: float
    monthly_savings: float
    months_to_target: Optional[int]
    target_date: Optional[datetime]
    generated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "id": self.plan_id,
            "target_home_price": self.target_home_price,
            "required_down_payment": self.required_down_payment,
            "estimated_closing_costs": self.estimated_closing_costs,
            "total_cash_needed": self.total_cash_needed,
            "current_cash": self.current_cash,
            "cash_gap": self.cash_gap,
            "monthly_savings": self.monthly_savings,
            "months_to_target": self.months_to_target,
            "target_date": self.target_date.isoformat() if self.target_date else None,
            "generated_at": self.generated_at.isoformat(),
        }


@dataclass
class AffordabilitySnapshot:
    """Affordability summary combining income and cash constraints."""

    monthly_housing_budget: float
    income_limited_price: float
    cash_limited_price: float
    recommended_budget: float
    affordability_band: AffordabilityBand
    down_payment_pct: float
    generated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "monthly_housing_budget": self.monthly_housing_budget,
            "income_limited_price": self.income_limited_price,
            "cash_limited_price": self.cash_limited_price,
            "recommended_budget": self.recommended_budget,
            "affordability_band": self.affordability_band.value,
            "down_payment_pct": self.down_payment_pct,
            "generated_at": self.generated_at.isoformat(),
        }


class HomePurchasePlanner:
    """Planner for home affordability, mortgage scenarios, and cash goals."""

    def __init__(self):
        self.purchase_profile: Optional[PurchaseProfile] = None

    def set_purchase_profile(
        self,
        gross_annual_income: float,
        monthly_debt_payments: float,
        available_cash: float,
        desired_down_payment_pct: float,
        target_housing_ratio_pct: float,
        created_at: datetime,
    ) -> PurchaseProfile:
        """Set or replace the purchase profile."""
        profile = PurchaseProfile(
            gross_annual_income=gross_annual_income,
            monthly_debt_payments=monthly_debt_payments,
            available_cash=available_cash,
            desired_down_payment_pct=desired_down_payment_pct,
            target_housing_ratio_pct=target_housing_ratio_pct,
            created_at=created_at,
        )
        self.purchase_profile = profile
        return profile

    def build_mortgage_scenario(
        self,
        property_price: float,
        annual_interest_rate_pct: float,
        loan_term_years: int,
        property_tax_rate_pct: float,
        annual_home_insurance: float,
        property_type: PropertyType = PropertyType.SINGLE_FAMILY,
        monthly_hoa: float = 0.0,
        private_mortgage_insurance_pct: float = 0.0,
        down_payment_pct: Optional[float] = None,
        created_at: Optional[datetime] = None,
    ) -> MortgageScenario:
        """Build a mortgage scenario using configured or explicit down payment assumptions."""
        if property_price < 0:
            raise ValueError("property_price cannot be negative")
        if down_payment_pct is None:
            down_payment_pct = self.purchase_profile.desired_down_payment_pct if self.purchase_profile else 20.0
        if down_payment_pct < 0 or down_payment_pct > 100:
            raise ValueError("down_payment_pct must be between 0 and 100")

        down_payment = property_price * (down_payment_pct / 100.0)
        loan_amount = property_price - down_payment

        return MortgageScenario(
            scenario_id=str(uuid.uuid4()),
            property_price=property_price,
            property_type=property_type,
            down_payment=down_payment,
            loan_amount=loan_amount,
            annual_interest_rate_pct=annual_interest_rate_pct,
            loan_term_years=loan_term_years,
            property_tax_rate_pct=property_tax_rate_pct,
            annual_home_insurance=annual_home_insurance,
            monthly_hoa=monthly_hoa,
            private_mortgage_insurance_pct=private_mortgage_insurance_pct,
            created_at=created_at or datetime.now(timezone.utc),
        )

    def estimate_closing_costs(
        self,
        purchase_price: float,
        closing_cost_pct: float = 3.0,
        down_payment_pct: Optional[float] = None,
    ) -> ClosingCostEstimate:
        """Estimate closing costs and total upfront cash requirement."""
        if purchase_price < 0:
            raise ValueError("purchase_price cannot be negative")
        if closing_cost_pct < 0 or closing_cost_pct > 100:
            raise ValueError("closing_cost_pct must be between 0 and 100")
        if down_payment_pct is None:
            down_payment_pct = self.purchase_profile.desired_down_payment_pct if self.purchase_profile else 20.0
        if down_payment_pct < 0 or down_payment_pct > 100:
            raise ValueError("down_payment_pct must be between 0 and 100")

        down_payment = purchase_price * (down_payment_pct / 100.0)
        closing_costs = purchase_price * (closing_cost_pct / 100.0)
        return ClosingCostEstimate(
            estimate_id=str(uuid.uuid4()),
            purchase_price=round(purchase_price, 2),
            down_payment=round(down_payment, 2),
            closing_cost_pct=closing_cost_pct,
            estimated_closing_costs=round(closing_costs, 2),
            total_cash_required=round(down_payment + closing_costs, 2),
        )

    def _monthly_cost_for_price(
        self,
        property_price: float,
        annual_interest_rate_pct: float,
        loan_term_years: int,
        property_tax_rate_pct: float,
        annual_home_insurance: float,
        monthly_hoa: float,
        private_mortgage_insurance_pct: float,
    ) -> float:
        """Internal helper to compute all-in monthly ownership cost."""
        scenario = self.build_mortgage_scenario(
            property_price=property_price,
            annual_interest_rate_pct=annual_interest_rate_pct,
            loan_term_years=loan_term_years,
            property_tax_rate_pct=property_tax_rate_pct,
            annual_home_insurance=annual_home_insurance,
            monthly_hoa=monthly_hoa,
            private_mortgage_insurance_pct=private_mortgage_insurance_pct,
        )
        return scenario.total_monthly_housing_cost

    def estimate_max_home_price(
        self,
        annual_interest_rate_pct: float,
        loan_term_years: int,
        property_tax_rate_pct: float,
        annual_home_insurance: float,
        monthly_hoa: float = 0.0,
        private_mortgage_insurance_pct: float = 0.0,
        closing_cost_pct: float = 3.0,
    ) -> float:
        """Estimate a max purchase price constrained by both income and cash."""
        if self.purchase_profile is None:
            raise ValueError("purchase_profile is required")
        if closing_cost_pct < 0 or closing_cost_pct > 100:
            raise ValueError("closing_cost_pct must be between 0 and 100")

        down_payment_pct = self.purchase_profile.desired_down_payment_pct / 100.0
        upfront_pct = down_payment_pct + (closing_cost_pct / 100.0)
        if upfront_pct == 0:
            cash_limited_price = float("inf")
        else:
            cash_limited_price = self.purchase_profile.available_cash / upfront_pct

        monthly_budget = self.purchase_profile.monthly_housing_budget
        low = 0.0
        high = max(cash_limited_price if isfinite(cash_limited_price) else 0.0, self.purchase_profile.gross_annual_income * 10, 100000.0)

        for _ in range(60):
            midpoint = (low + high) / 2.0
            cost = self._monthly_cost_for_price(
                property_price=midpoint,
                annual_interest_rate_pct=annual_interest_rate_pct,
                loan_term_years=loan_term_years,
                property_tax_rate_pct=property_tax_rate_pct,
                annual_home_insurance=annual_home_insurance,
                monthly_hoa=monthly_hoa,
                private_mortgage_insurance_pct=private_mortgage_insurance_pct,
            )
            if cost <= monthly_budget:
                low = midpoint
            else:
                high = midpoint

        income_limited_price = low
        return round(min(income_limited_price, cash_limited_price), 2)

    def project_down_payment_timeline(
        self,
        target_home_price: float,
        monthly_savings: float,
        closing_cost_pct: float = 3.0,
    ) -> DownPaymentPlan:
        """Project how long it will take to accumulate cash to close."""
        if self.purchase_profile is None:
            raise ValueError("purchase_profile is required")
        if target_home_price < 0:
            raise ValueError("target_home_price cannot be negative")
        if monthly_savings < 0:
            raise ValueError("monthly_savings cannot be negative")
        if closing_cost_pct < 0 or closing_cost_pct > 100:
            raise ValueError("closing_cost_pct must be between 0 and 100")

        estimate = self.estimate_closing_costs(
            purchase_price=target_home_price,
            closing_cost_pct=closing_cost_pct,
        )
        current_cash = self.purchase_profile.available_cash
        cash_gap = max(0.0, estimate.total_cash_required - current_cash)

        if cash_gap == 0:
            months_to_target = 0
            target_date = datetime.now(timezone.utc)
        elif monthly_savings == 0:
            months_to_target = None
            target_date = None
        else:
            months_to_target = ceil(cash_gap / monthly_savings)
            target_date = datetime.now(timezone.utc) + timedelta(days=30 * months_to_target)

        return DownPaymentPlan(
            plan_id=str(uuid.uuid4()),
            target_home_price=round(target_home_price, 2),
            required_down_payment=estimate.down_payment,
            estimated_closing_costs=estimate.estimated_closing_costs,
            total_cash_needed=estimate.total_cash_required,
            current_cash=round(current_cash, 2),
            cash_gap=round(cash_gap, 2),
            monthly_savings=round(monthly_savings, 2),
            months_to_target=months_to_target,
            target_date=target_date,
        )

    def get_affordability_snapshot(
        self,
        annual_interest_rate_pct: float,
        loan_term_years: int,
        property_tax_rate_pct: float,
        annual_home_insurance: float,
        monthly_hoa: float = 0.0,
        private_mortgage_insurance_pct: float = 0.0,
        closing_cost_pct: float = 3.0,
    ) -> AffordabilitySnapshot:
        """Summarize affordability based on both income and cash constraints."""
        if self.purchase_profile is None:
            raise ValueError("purchase_profile is required")

        recommended_budget = self.estimate_max_home_price(
            annual_interest_rate_pct=annual_interest_rate_pct,
            loan_term_years=loan_term_years,
            property_tax_rate_pct=property_tax_rate_pct,
            annual_home_insurance=annual_home_insurance,
            monthly_hoa=monthly_hoa,
            private_mortgage_insurance_pct=private_mortgage_insurance_pct,
            closing_cost_pct=closing_cost_pct,
        )

        down_payment_pct = self.purchase_profile.desired_down_payment_pct / 100.0
        upfront_pct = down_payment_pct + (closing_cost_pct / 100.0)
        cash_limited_price = (
            self.purchase_profile.available_cash / upfront_pct if upfront_pct else float("inf")
        )

        income_limited_price = recommended_budget if recommended_budget < cash_limited_price else self.estimate_max_home_price(
            annual_interest_rate_pct=annual_interest_rate_pct,
            loan_term_years=loan_term_years,
            property_tax_rate_pct=property_tax_rate_pct,
            annual_home_insurance=annual_home_insurance,
            monthly_hoa=monthly_hoa,
            private_mortgage_insurance_pct=private_mortgage_insurance_pct,
            closing_cost_pct=0.0,
        )

        if self.purchase_profile.gross_annual_income == 0:
            price_to_income = 0.0
        else:
            price_to_income = recommended_budget / self.purchase_profile.gross_annual_income

        if price_to_income <= 3.0:
            band = AffordabilityBand.COMFORTABLE
        elif price_to_income <= 4.0:
            band = AffordabilityBand.BALANCED
        else:
            band = AffordabilityBand.STRETCH

        return AffordabilitySnapshot(
            monthly_housing_budget=round(self.purchase_profile.monthly_housing_budget, 2),
            income_limited_price=round(income_limited_price, 2),
            cash_limited_price=round(cash_limited_price, 2),
            recommended_budget=round(recommended_budget, 2),
            affordability_band=band,
            down_payment_pct=round(self.purchase_profile.desired_down_payment_pct, 2),
        )