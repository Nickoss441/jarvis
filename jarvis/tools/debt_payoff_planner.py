"""Debt payoff planning and optimization.

Provides debt account tracking, payment recording, payoff ordering strategies,
and deterministic payoff projections.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Optional
import uuid


class DebtType(str, Enum):
    """Supported debt categories."""

    CREDIT_CARD = "credit_card"
    MORTGAGE = "mortgage"
    STUDENT_LOAN = "student_loan"
    AUTO_LOAN = "auto_loan"
    PERSONAL_LOAN = "personal_loan"
    MEDICAL = "medical"
    TAX = "tax"
    OTHER = "other"


class DebtStatus(str, Enum):
    """Lifecycle state for a debt account."""

    ACTIVE = "active"
    PAID_OFF = "paid_off"
    IN_COLLECTIONS = "in_collections"
    DEFERRED = "deferred"


class PayoffStrategy(str, Enum):
    """Debt payoff ordering strategies."""

    SNOWBALL = "snowball"  # smallest balance first
    AVALANCHE = "avalanche"  # highest APR first
    HYBRID = "hybrid"  # weighted blend of balance and APR
    CUSTOM = "custom"  # reserved for future user-defined ordering


@dataclass
class DebtAccount:
    """A debt account with terms and current balance."""

    debt_id: str
    name: str
    debt_type: DebtType
    principal_balance: float
    interest_rate: float
    minimum_payment: float
    due_day: int
    opened_at: datetime
    status: DebtStatus = DebtStatus.ACTIVE

    def __post_init__(self):
        if self.principal_balance < 0:
            raise ValueError("principal_balance cannot be negative")
        if self.interest_rate < 0 or self.interest_rate > 100:
            raise ValueError("interest_rate must be between 0 and 100")
        if self.minimum_payment < 0:
            raise ValueError("minimum_payment cannot be negative")
        if self.due_day < 1 or self.due_day > 31:
            raise ValueError("due_day must be between 1 and 31")
        if not isinstance(self.opened_at, datetime) or self.opened_at.tzinfo is None:
            raise ValueError("opened_at must be timezone-aware (UTC)")

    @property
    def monthly_interest_rate(self) -> float:
        """Monthly decimal rate derived from annual percentage rate."""
        return (self.interest_rate / 100.0) / 12.0

    @property
    def estimated_monthly_interest(self) -> float:
        """Approximate next-month interest at current balance."""
        return self.principal_balance * self.monthly_interest_rate

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "id": self.debt_id,
            "name": self.name,
            "type": self.debt_type.value,
            "balance": self.principal_balance,
            "apr": self.interest_rate,
            "minimum_payment": self.minimum_payment,
            "due_day": self.due_day,
            "opened_at": self.opened_at.isoformat(),
            "status": self.status.value,
        }


@dataclass
class PaymentRecord:
    """A payment event recorded against a debt account."""

    payment_id: str
    debt_id: str
    amount: float
    paid_at: datetime
    principal_paid: float
    interest_paid: float
    note: str = ""

    def __post_init__(self):
        if self.amount < 0:
            raise ValueError("amount cannot be negative")
        if self.principal_paid < 0 or self.interest_paid < 0:
            raise ValueError("principal_paid and interest_paid cannot be negative")
        if not isinstance(self.paid_at, datetime) or self.paid_at.tzinfo is None:
            raise ValueError("paid_at must be timezone-aware (UTC)")

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "id": self.payment_id,
            "debt_id": self.debt_id,
            "amount": self.amount,
            "principal_paid": self.principal_paid,
            "interest_paid": self.interest_paid,
            "paid_at": self.paid_at.isoformat(),
            "note": self.note,
        }


@dataclass
class PayoffProjection:
    """Projected payoff summary for a strategy and budget."""

    months_to_debt_free: int
    total_interest_paid: float
    total_paid: float
    estimated_payoff_date: Optional[datetime]

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "months_to_debt_free": self.months_to_debt_free,
            "total_interest_paid": self.total_interest_paid,
            "total_paid": self.total_paid,
            "estimated_payoff_date": (
                self.estimated_payoff_date.isoformat() if self.estimated_payoff_date else None
            ),
        }


@dataclass
class PayoffPlan:
    """Strategy recommendation and projection."""

    plan_id: str
    strategy: PayoffStrategy
    ordered_debt_ids: list[str]
    monthly_budget: float
    total_minimum_required: float
    extra_payment: float
    projection: PayoffProjection
    generated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "id": self.plan_id,
            "strategy": self.strategy.value,
            "ordered_debt_ids": self.ordered_debt_ids,
            "monthly_budget": self.monthly_budget,
            "total_minimum_required": self.total_minimum_required,
            "extra_payment": self.extra_payment,
            "projection": self.projection.to_dict(),
            "generated_at": self.generated_at.isoformat(),
        }


class DebtPayoffPlanner:
    """Debt payoff planner with configurable ordering strategies."""

    def __init__(self):
        self.debts: dict[str, DebtAccount] = {}
        self.payments: list[PaymentRecord] = []

    def add_debt_account(
        self,
        name: str,
        debt_type: DebtType,
        principal_balance: float,
        interest_rate: float,
        minimum_payment: float,
        due_day: int,
        opened_at: datetime,
    ) -> DebtAccount:
        """Create and register a debt account."""
        debt_id = str(uuid.uuid4())
        debt = DebtAccount(
            debt_id=debt_id,
            name=name,
            debt_type=debt_type,
            principal_balance=principal_balance,
            interest_rate=interest_rate,
            minimum_payment=minimum_payment,
            due_day=due_day,
            opened_at=opened_at,
        )
        if debt.principal_balance == 0:
            debt.status = DebtStatus.PAID_OFF
        self.debts[debt_id] = debt
        return debt

    def record_payment(
        self,
        debt_id: str,
        amount: float,
        paid_at: datetime,
        principal_paid: Optional[float] = None,
        interest_paid: float = 0.0,
        note: str = "",
    ) -> PaymentRecord:
        """Record a debt payment and apply principal reduction."""
        debt = self.debts.get(debt_id)
        if debt is None:
            raise KeyError(f"debt not found: {debt_id}")
        if amount < 0:
            raise ValueError("amount cannot be negative")
        if principal_paid is None:
            principal_paid = max(0.0, amount - interest_paid)
        applied_principal = min(principal_paid, debt.principal_balance)
        debt.principal_balance = max(0.0, debt.principal_balance - applied_principal)
        if debt.principal_balance == 0:
            debt.status = DebtStatus.PAID_OFF

        payment = PaymentRecord(
            payment_id=str(uuid.uuid4()),
            debt_id=debt_id,
            amount=amount,
            paid_at=paid_at,
            principal_paid=applied_principal,
            interest_paid=max(0.0, interest_paid),
            note=note,
        )
        self.payments.append(payment)
        return payment

    def get_active_debts(self) -> list[DebtAccount]:
        """Return active debts with remaining balance."""
        return [
            debt
            for debt in self.debts.values()
            if debt.status == DebtStatus.ACTIVE and debt.principal_balance > 0
        ]

    def get_total_debt_balance(self) -> float:
        """Total outstanding balance across active debts."""
        return sum(debt.principal_balance for debt in self.get_active_debts())

    def get_monthly_minimum_obligation(self) -> float:
        """Total monthly minimum payment requirement."""
        return sum(debt.minimum_payment for debt in self.get_active_debts())

    def get_weighted_average_interest_rate(self) -> float:
        """Balance-weighted APR across active debts."""
        active = self.get_active_debts()
        total_balance = sum(debt.principal_balance for debt in active)
        if total_balance == 0:
            return 0.0
        weighted = sum(debt.principal_balance * debt.interest_rate for debt in active)
        return weighted / total_balance

    def suggest_payoff_order(self, strategy: PayoffStrategy) -> list[str]:
        """Return debt IDs ordered by strategy priority."""
        active = self.get_active_debts()
        if strategy == PayoffStrategy.SNOWBALL:
            ordered = sorted(active, key=lambda d: (d.principal_balance, -d.interest_rate, d.name))
        elif strategy == PayoffStrategy.AVALANCHE:
            ordered = sorted(active, key=lambda d: (-d.interest_rate, d.principal_balance, d.name))
        elif strategy == PayoffStrategy.HYBRID:
            max_balance = max((d.principal_balance for d in active), default=1.0)

            def _score(debt: DebtAccount) -> float:
                balance_component = debt.principal_balance / max_balance
                rate_component = debt.interest_rate / 100.0
                return 0.7 * rate_component + 0.3 * balance_component

            ordered = sorted(active, key=lambda d: (-_score(d), d.principal_balance, d.name))
        else:
            # CUSTOM falls back to avalanche until user-defined ordering is introduced.
            ordered = sorted(active, key=lambda d: (-d.interest_rate, d.principal_balance, d.name))
        return [debt.debt_id for debt in ordered]

    def simulate_payoff(
        self,
        strategy: PayoffStrategy,
        monthly_budget: float,
        extra_payment: float = 0.0,
        max_months: int = 600,
    ) -> PayoffProjection:
        """Simulate monthly payoff until all debts are paid or max months is reached."""
        if monthly_budget < 0 or extra_payment < 0:
            raise ValueError("monthly_budget and extra_payment must be non-negative")

        active = self.get_active_debts()
        min_required = self.get_monthly_minimum_obligation()
        monthly_capacity = monthly_budget + extra_payment
        if active and monthly_capacity < min_required:
            raise ValueError("monthly budget is below minimum required payments")

        balances = {debt.debt_id: debt.principal_balance for debt in active}
        rates = {debt.debt_id: debt.monthly_interest_rate for debt in active}
        minimums = {debt.debt_id: debt.minimum_payment for debt in active}

        months = 0
        total_interest = 0.0
        total_paid = 0.0

        while months < max_months and any(balance > 0 for balance in balances.values()):
            months += 1

            # Interest accrual phase.
            for debt_id, balance in list(balances.items()):
                if balance <= 0:
                    continue
                interest = balance * rates[debt_id]
                balances[debt_id] += interest
                total_interest += interest

            payment_pool = monthly_capacity

            # Minimum payment phase.
            for debt_id in list(balances.keys()):
                if balances[debt_id] <= 0:
                    continue
                minimum = min(minimums[debt_id], balances[debt_id], payment_pool)
                balances[debt_id] -= minimum
                payment_pool -= minimum
                total_paid += minimum

            # Extra payment phase in strategy order.
            if payment_pool > 0:
                ordered_ids = self._ordered_ids_from_balances(strategy, balances)
                for debt_id in ordered_ids:
                    if payment_pool <= 0:
                        break
                    if balances[debt_id] <= 0:
                        continue
                    extra = min(payment_pool, balances[debt_id])
                    balances[debt_id] -= extra
                    payment_pool -= extra
                    total_paid += extra

        payoff_date: Optional[datetime]
        if any(balance > 0 for balance in balances.values()):
            payoff_date = None
        else:
            payoff_date = datetime.now(timezone.utc) + timedelta(days=months * 30)

        return PayoffProjection(
            months_to_debt_free=months,
            total_interest_paid=round(total_interest, 2),
            total_paid=round(total_paid, 2),
            estimated_payoff_date=payoff_date,
        )

    def generate_payoff_plan(
        self,
        strategy: PayoffStrategy,
        monthly_budget: float,
        extra_payment: float = 0.0,
    ) -> PayoffPlan:
        """Generate strategy-backed debt payoff plan."""
        ordered_ids = self.suggest_payoff_order(strategy)
        projection = self.simulate_payoff(strategy, monthly_budget, extra_payment)
        minimum_required = self.get_monthly_minimum_obligation()
        return PayoffPlan(
            plan_id=str(uuid.uuid4()),
            strategy=strategy,
            ordered_debt_ids=ordered_ids,
            monthly_budget=monthly_budget,
            total_minimum_required=minimum_required,
            extra_payment=extra_payment,
            projection=projection,
        )

    def _ordered_ids_from_balances(
        self,
        strategy: PayoffStrategy,
        balances: dict[str, float],
    ) -> list[str]:
        """Internal ordering helper using simulated balances."""
        candidates = [
            self.debts[debt_id]
            for debt_id, balance in balances.items()
            if balance > 0 and debt_id in self.debts
        ]
        if strategy == PayoffStrategy.SNOWBALL:
            candidates.sort(key=lambda d: (balances[d.debt_id], -d.interest_rate, d.name))
        elif strategy == PayoffStrategy.AVALANCHE:
            candidates.sort(key=lambda d: (-d.interest_rate, balances[d.debt_id], d.name))
        elif strategy == PayoffStrategy.HYBRID:
            max_balance = max((balances[d.debt_id] for d in candidates), default=1.0)

            def _score(debt: DebtAccount) -> float:
                balance_component = balances[debt.debt_id] / max_balance
                rate_component = debt.interest_rate / 100.0
                return 0.7 * rate_component + 0.3 * balance_component

            candidates.sort(key=lambda d: (-_score(d), balances[d.debt_id], d.name))
        else:
            candidates.sort(key=lambda d: (-d.interest_rate, balances[d.debt_id], d.name))
        return [debt.debt_id for debt in candidates]
