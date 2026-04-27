"""Rent versus buy analysis and housing cost projection utilities.

Provides deterministic rent-versus-buy comparisons, mortgage amortization,
equity tracking, and break-even analysis over a fixed time horizon.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from math import isfinite
from typing import Optional
import uuid


class Recommendation(str, Enum):
    """High-level recommendation outcome."""

    BUY = "buy"
    RENT = "rent"
    NEUTRAL = "neutral"


@dataclass
class RentScenario:
    """Assumptions for renting a comparable property."""

    monthly_rent: float
    annual_rent_increase_pct: float
    annual_renters_insurance: float
    upfront_move_in_cost: float
    created_at: datetime

    def __post_init__(self):
        if self.monthly_rent < 0:
            raise ValueError("monthly_rent cannot be negative")
        if self.annual_rent_increase_pct < 0 or not isfinite(self.annual_rent_increase_pct):
            raise ValueError("annual_rent_increase_pct must be a non-negative finite number")
        if self.annual_renters_insurance < 0:
            raise ValueError("annual_renters_insurance cannot be negative")
        if self.upfront_move_in_cost < 0:
            raise ValueError("upfront_move_in_cost cannot be negative")
        if not isinstance(self.created_at, datetime) or self.created_at.tzinfo is None:
            raise ValueError("created_at must be timezone-aware (UTC)")

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "monthly_rent": self.monthly_rent,
            "annual_rent_increase_pct": self.annual_rent_increase_pct,
            "annual_renters_insurance": self.annual_renters_insurance,
            "upfront_move_in_cost": self.upfront_move_in_cost,
            "created_at": self.created_at.isoformat(),
        }


@dataclass
class BuyScenario:
    """Assumptions for purchasing a comparable property."""

    home_price: float
    down_payment_pct: float
    mortgage_rate_pct: float
    mortgage_term_years: int
    property_tax_rate_pct: float
    annual_home_insurance: float
    annual_maintenance_pct: float
    monthly_hoa: float
    closing_cost_pct: float
    expected_appreciation_pct: float
    selling_cost_pct: float
    created_at: datetime

    def __post_init__(self):
        if self.home_price < 0:
            raise ValueError("home_price cannot be negative")
        for field_name in (
            "down_payment_pct",
            "mortgage_rate_pct",
            "property_tax_rate_pct",
            "annual_maintenance_pct",
            "closing_cost_pct",
            "expected_appreciation_pct",
            "selling_cost_pct",
        ):
            value = getattr(self, field_name)
            if not isfinite(value):
                raise ValueError(f"{field_name} must be finite")
        if self.down_payment_pct < 0 or self.down_payment_pct > 100:
            raise ValueError("down_payment_pct must be between 0 and 100")
        if self.mortgage_rate_pct < 0:
            raise ValueError("mortgage_rate_pct cannot be negative")
        if self.mortgage_term_years <= 0:
            raise ValueError("mortgage_term_years must be positive")
        if self.property_tax_rate_pct < 0:
            raise ValueError("property_tax_rate_pct cannot be negative")
        if self.annual_home_insurance < 0:
            raise ValueError("annual_home_insurance cannot be negative")
        if self.annual_maintenance_pct < 0:
            raise ValueError("annual_maintenance_pct cannot be negative")
        if self.monthly_hoa < 0:
            raise ValueError("monthly_hoa cannot be negative")
        if self.closing_cost_pct < 0 or self.closing_cost_pct > 100:
            raise ValueError("closing_cost_pct must be between 0 and 100")
        if self.selling_cost_pct < 0 or self.selling_cost_pct > 100:
            raise ValueError("selling_cost_pct must be between 0 and 100")
        if not isinstance(self.created_at, datetime) or self.created_at.tzinfo is None:
            raise ValueError("created_at must be timezone-aware (UTC)")

    @property
    def down_payment_amount(self) -> float:
        """Cash down payment in dollars."""
        return self.home_price * (self.down_payment_pct / 100.0)

    @property
    def loan_amount(self) -> float:
        """Mortgage principal after down payment."""
        return self.home_price - self.down_payment_amount

    @property
    def closing_cost_amount(self) -> float:
        """Estimated closing costs in dollars."""
        return self.home_price * (self.closing_cost_pct / 100.0)

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "home_price": self.home_price,
            "down_payment_pct": self.down_payment_pct,
            "down_payment_amount": self.down_payment_amount,
            "loan_amount": self.loan_amount,
            "mortgage_rate_pct": self.mortgage_rate_pct,
            "mortgage_term_years": self.mortgage_term_years,
            "property_tax_rate_pct": self.property_tax_rate_pct,
            "annual_home_insurance": self.annual_home_insurance,
            "annual_maintenance_pct": self.annual_maintenance_pct,
            "monthly_hoa": self.monthly_hoa,
            "closing_cost_pct": self.closing_cost_pct,
            "closing_cost_amount": self.closing_cost_amount,
            "expected_appreciation_pct": self.expected_appreciation_pct,
            "selling_cost_pct": self.selling_cost_pct,
            "created_at": self.created_at.isoformat(),
        }


@dataclass
class ComparisonYear:
    """Per-year rent-versus-buy comparison snapshot."""

    year_index: int
    as_of: datetime
    cumulative_rent_cost: float
    cumulative_buy_outflow: float
    remaining_mortgage_balance: float
    estimated_home_value: float
    estimated_equity: float
    net_sale_proceeds: float
    effective_buy_cost: float

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "year_index": self.year_index,
            "as_of": self.as_of.isoformat(),
            "cumulative_rent_cost": self.cumulative_rent_cost,
            "cumulative_buy_outflow": self.cumulative_buy_outflow,
            "remaining_mortgage_balance": self.remaining_mortgage_balance,
            "estimated_home_value": self.estimated_home_value,
            "estimated_equity": self.estimated_equity,
            "net_sale_proceeds": self.net_sale_proceeds,
            "effective_buy_cost": self.effective_buy_cost,
        }


@dataclass
class RentBuyAnalysis:
    """Summary output for a rent-versus-buy comparison."""

    analysis_id: str
    years: int
    recommendation: Recommendation
    break_even_year: Optional[int]
    initial_cash_required: float
    total_rent_cost: float
    total_buy_outflow: float
    ending_home_value: float
    ending_mortgage_balance: float
    ending_equity: float
    ending_net_sale_proceeds: float
    ending_effective_buy_cost: float
    timeline: list[ComparisonYear]
    generated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "id": self.analysis_id,
            "years": self.years,
            "recommendation": self.recommendation.value,
            "break_even_year": self.break_even_year,
            "initial_cash_required": self.initial_cash_required,
            "total_rent_cost": self.total_rent_cost,
            "total_buy_outflow": self.total_buy_outflow,
            "ending_home_value": self.ending_home_value,
            "ending_mortgage_balance": self.ending_mortgage_balance,
            "ending_equity": self.ending_equity,
            "ending_net_sale_proceeds": self.ending_net_sale_proceeds,
            "ending_effective_buy_cost": self.ending_effective_buy_cost,
            "timeline": [point.to_dict() for point in self.timeline],
            "generated_at": self.generated_at.isoformat(),
        }


class RentVsBuyAnalyzer:
    """Analyzer for comparing renting against purchasing a home."""

    def __init__(self):
        self.rent_scenario: Optional[RentScenario] = None
        self.buy_scenario: Optional[BuyScenario] = None

    def set_rent_scenario(
        self,
        monthly_rent: float,
        annual_rent_increase_pct: float,
        annual_renters_insurance: float,
        upfront_move_in_cost: float,
        created_at: datetime,
    ) -> RentScenario:
        """Set or replace the rent scenario."""
        scenario = RentScenario(
            monthly_rent=monthly_rent,
            annual_rent_increase_pct=annual_rent_increase_pct,
            annual_renters_insurance=annual_renters_insurance,
            upfront_move_in_cost=upfront_move_in_cost,
            created_at=created_at,
        )
        self.rent_scenario = scenario
        return scenario

    def set_buy_scenario(
        self,
        home_price: float,
        down_payment_pct: float,
        mortgage_rate_pct: float,
        mortgage_term_years: int,
        property_tax_rate_pct: float,
        annual_home_insurance: float,
        annual_maintenance_pct: float,
        monthly_hoa: float,
        closing_cost_pct: float,
        expected_appreciation_pct: float,
        selling_cost_pct: float,
        created_at: datetime,
    ) -> BuyScenario:
        """Set or replace the buy scenario."""
        scenario = BuyScenario(
            home_price=home_price,
            down_payment_pct=down_payment_pct,
            mortgage_rate_pct=mortgage_rate_pct,
            mortgage_term_years=mortgage_term_years,
            property_tax_rate_pct=property_tax_rate_pct,
            annual_home_insurance=annual_home_insurance,
            annual_maintenance_pct=annual_maintenance_pct,
            monthly_hoa=monthly_hoa,
            closing_cost_pct=closing_cost_pct,
            expected_appreciation_pct=expected_appreciation_pct,
            selling_cost_pct=selling_cost_pct,
            created_at=created_at,
        )
        self.buy_scenario = scenario
        return scenario

    def calculate_monthly_mortgage_payment(self) -> float:
        """Calculate monthly principal and interest for the buy scenario."""
        if self.buy_scenario is None:
            raise ValueError("buy_scenario is required")
        loan_amount = self.buy_scenario.loan_amount
        if loan_amount == 0:
            return 0.0
        monthly_rate = (self.buy_scenario.mortgage_rate_pct / 100.0) / 12.0
        periods = self.buy_scenario.mortgage_term_years * 12
        if monthly_rate == 0:
            return round(loan_amount / periods, 2)
        factor = (1 + monthly_rate) ** periods
        payment = loan_amount * ((monthly_rate * factor) / (factor - 1))
        return round(payment, 2)

    def estimate_initial_cash_required(self) -> float:
        """Estimate upfront cash needed to close on the purchase."""
        if self.buy_scenario is None:
            raise ValueError("buy_scenario is required")
        return round(
            self.buy_scenario.down_payment_amount + self.buy_scenario.closing_cost_amount,
            2,
        )

    def analyze(self, years: int) -> RentBuyAnalysis:
        """Run a deterministic rent-versus-buy comparison over a fixed horizon."""
        if self.rent_scenario is None:
            raise ValueError("rent_scenario is required")
        if self.buy_scenario is None:
            raise ValueError("buy_scenario is required")
        if years < 0:
            raise ValueError("years cannot be negative")

        monthly_payment = self.calculate_monthly_mortgage_payment()
        loan_balance = self.buy_scenario.loan_amount
        monthly_rate = (self.buy_scenario.mortgage_rate_pct / 100.0) / 12.0

        cumulative_rent_cost = self.rent_scenario.upfront_move_in_cost
        cumulative_buy_outflow = self.estimate_initial_cash_required()
        current_rent = self.rent_scenario.monthly_rent
        home_value = self.buy_scenario.home_price
        break_even_year: Optional[int] = None
        timeline: list[ComparisonYear] = []
        now = datetime.now(timezone.utc)

        for year_index in range(1, years + 1):
            cumulative_rent_cost += (current_rent * 12.0) + self.rent_scenario.annual_renters_insurance

            annual_interest_paid = 0.0
            annual_principal_paid = 0.0
            for _ in range(12):
                if loan_balance <= 0:
                    break
                interest = loan_balance * monthly_rate
                principal = min(loan_balance, monthly_payment - interest)
                if principal < 0:
                    principal = 0.0
                loan_balance = max(0.0, loan_balance - principal)
                annual_interest_paid += interest
                annual_principal_paid += principal

            annual_property_tax = self.buy_scenario.home_price * (
                self.buy_scenario.property_tax_rate_pct / 100.0
            )
            annual_maintenance = home_value * (self.buy_scenario.annual_maintenance_pct / 100.0)
            annual_hoa = self.buy_scenario.monthly_hoa * 12.0
            annual_owner_cost = (
                (monthly_payment * 12.0)
                + annual_property_tax
                + self.buy_scenario.annual_home_insurance
                + annual_maintenance
                + annual_hoa
            )
            cumulative_buy_outflow += annual_owner_cost

            home_value *= 1 + (self.buy_scenario.expected_appreciation_pct / 100.0)
            equity = max(0.0, home_value - loan_balance)
            net_sale_proceeds = max(
                0.0,
                home_value * (1 - (self.buy_scenario.selling_cost_pct / 100.0)) - loan_balance,
            )
            effective_buy_cost = cumulative_buy_outflow - net_sale_proceeds

            point = ComparisonYear(
                year_index=year_index,
                as_of=now + timedelta(days=365 * year_index),
                cumulative_rent_cost=round(cumulative_rent_cost, 2),
                cumulative_buy_outflow=round(cumulative_buy_outflow, 2),
                remaining_mortgage_balance=round(loan_balance, 2),
                estimated_home_value=round(home_value, 2),
                estimated_equity=round(equity, 2),
                net_sale_proceeds=round(net_sale_proceeds, 2),
                effective_buy_cost=round(effective_buy_cost, 2),
            )
            timeline.append(point)

            if break_even_year is None and effective_buy_cost <= cumulative_rent_cost:
                break_even_year = year_index

            current_rent *= 1 + (self.rent_scenario.annual_rent_increase_pct / 100.0)

        if years == 0:
            ending_home_value = self.buy_scenario.home_price
            ending_mortgage_balance = self.buy_scenario.loan_amount
            ending_equity = self.buy_scenario.down_payment_amount
            ending_net_sale_proceeds = max(
                0.0,
                ending_home_value * (1 - (self.buy_scenario.selling_cost_pct / 100.0))
                - ending_mortgage_balance,
            )
            ending_effective_buy_cost = cumulative_buy_outflow - ending_net_sale_proceeds
        else:
            last = timeline[-1]
            ending_home_value = last.estimated_home_value
            ending_mortgage_balance = last.remaining_mortgage_balance
            ending_equity = last.estimated_equity
            ending_net_sale_proceeds = last.net_sale_proceeds
            ending_effective_buy_cost = last.effective_buy_cost

        if abs(ending_effective_buy_cost - cumulative_rent_cost) <= 1000:
            recommendation = Recommendation.NEUTRAL
        elif ending_effective_buy_cost < cumulative_rent_cost:
            recommendation = Recommendation.BUY
        else:
            recommendation = Recommendation.RENT

        return RentBuyAnalysis(
            analysis_id=str(uuid.uuid4()),
            years=years,
            recommendation=recommendation,
            break_even_year=break_even_year,
            initial_cash_required=self.estimate_initial_cash_required(),
            total_rent_cost=round(cumulative_rent_cost, 2),
            total_buy_outflow=round(cumulative_buy_outflow, 2),
            ending_home_value=round(ending_home_value, 2),
            ending_mortgage_balance=round(ending_mortgage_balance, 2),
            ending_equity=round(ending_equity, 2),
            ending_net_sale_proceeds=round(ending_net_sale_proceeds, 2),
            ending_effective_buy_cost=round(ending_effective_buy_cost, 2),
            timeline=timeline,
        )