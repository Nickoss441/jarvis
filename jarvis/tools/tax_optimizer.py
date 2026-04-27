"""Tax optimization and capital gains analyzer module.

Tracks investment transactions, calculates capital gains/losses, identifies
tax-loss harvesting opportunities, and provides tax optimization strategies.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from enum import Enum
from typing import Optional
import uuid


class TransactionType(str, Enum):
    """Types of investment transactions."""
    BUY = "buy"
    SELL = "sell"
    DIVIDEND = "dividend"
    INTEREST = "interest"


class GainType(str, Enum):
    """Types of capital gains."""
    SHORT_TERM = "short_term"  # Less than 1 year
    LONG_TERM = "long_term"    # 1 year or more


class TaxStatus(str, Enum):
    """Tax filing status."""
    SINGLE = "single"
    MARRIED_FILING_JOINTLY = "married_filing_jointly"
    MARRIED_FILING_SEPARATELY = "married_filing_separately"
    HEAD_OF_HOUSEHOLD = "head_of_household"


@dataclass
class InvestmentTransaction:
    """Investment transaction for tax tracking.
    
    Attributes:
        transaction_id: Unique transaction ID
        asset: Asset symbol (e.g., "AAPL", "BTC")
        transaction_type: Type of transaction
        quantity: Number of shares/units
        unit_price: Price per share/unit
        date: Transaction date (UTC)
        fees: Transaction fees
        notes: Additional notes
    """
    transaction_id: str
    asset: str
    transaction_type: TransactionType
    quantity: float
    unit_price: float
    date: datetime
    fees: float = 0.0
    notes: str = ""
    
    def __post_init__(self):
        """Validate transaction."""
        if self.quantity <= 0 and self.transaction_type in [TransactionType.BUY, TransactionType.SELL]:
            raise ValueError("Quantity must be positive for buy/sell")
        if self.unit_price < 0:
            raise ValueError("Unit price cannot be negative")
        if self.fees < 0:
            raise ValueError("Fees cannot be negative")
        if not isinstance(self.date, datetime) or self.date.tzinfo is None:
            raise ValueError("date must be timezone-aware (UTC)")
    
    @property
    def total_cost(self) -> float:
        """Calculate total transaction cost."""
        if self.transaction_type == TransactionType.SELL:
            return self.quantity * self.unit_price - self.fees
        return self.quantity * self.unit_price + self.fees
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "id": self.transaction_id,
            "asset": self.asset,
            "type": self.transaction_type.value,
            "quantity": self.quantity,
            "unit_price": self.unit_price,
            "total": self.total_cost,
            "fees": self.fees,
            "date": self.date.isoformat(),
        }


@dataclass
class CapitalGain:
    """Capital gain/loss record.
    
    Attributes:
        asset: Asset symbol
        gain_type: Type of gain (short or long term)
        quantity: Number of shares sold
        cost_basis: Cost basis per share
        sale_price: Sale price per share
        realized_gain: Total realized gain/loss
        sale_date: When asset was sold
        acquisition_date: When asset was acquired
    """
    asset: str
    gain_type: GainType
    quantity: float
    cost_basis: float
    sale_price: float
    realized_gain: float
    sale_date: datetime
    acquisition_date: datetime
    
    def __post_init__(self):
        """Validate capital gain."""
        if not isinstance(sale_date := self.sale_date, datetime) or sale_date.tzinfo is None:
            raise ValueError("sale_date must be timezone-aware (UTC)")
        if not isinstance(acq_date := self.acquisition_date, datetime) or acq_date.tzinfo is None:
            raise ValueError("acquisition_date must be timezone-aware (UTC)")
    
    @property
    def holding_period_days(self) -> int:
        """Calculate holding period in days."""
        return (self.sale_date - self.acquisition_date).days
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "asset": self.asset,
            "type": self.gain_type.value,
            "quantity": self.quantity,
            "cost_basis": self.cost_basis,
            "sale_price": self.sale_price,
            "realized_gain": self.realized_gain,
            "holding_days": self.holding_period_days,
            "sale_date": self.sale_date.isoformat(),
        }


@dataclass
class LossHarvestingOpportunity:
    """Tax-loss harvesting opportunity.
    
    Attributes:
        asset: Asset symbol
        current_price: Current market price
        cost_basis: Original purchase price
        unrealized_loss: Current loss
        potential_tax_benefit: Estimated tax savings from harvesting
        replacement_asset: Recommended replacement asset (to avoid wash sale)
        wash_sale_risk: Whether position has wash sale risk
    """
    asset: str
    current_price: float
    cost_basis: float
    unrealized_loss: float
    potential_tax_benefit: float
    replacement_asset: Optional[str] = None
    wash_sale_risk: bool = False
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "asset": self.asset,
            "current_price": self.current_price,
            "cost_basis": self.cost_basis,
            "unrealized_loss": self.unrealized_loss,
            "tax_benefit": self.potential_tax_benefit,
            "replacement": self.replacement_asset,
            "wash_sale_risk": self.wash_sale_risk,
        }


@dataclass
class TaxLiability:
    """Tax liability summary.
    
    Attributes:
        short_term_gains: Total short-term capital gains
        long_term_gains: Total long-term capital gains
        total_gains: Total realized gains
        estimated_tax_rate: Marginal tax rate
        estimated_liability: Estimated tax liability
        tax_status: Filer's tax status
        filing_year: Tax year
    """
    short_term_gains: float
    long_term_gains: float
    total_gains: float
    estimated_tax_rate: float
    estimated_liability: float
    tax_status: TaxStatus
    filing_year: int
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "short_term_gains": self.short_term_gains,
            "long_term_gains": self.long_term_gains,
            "total_gains": self.total_gains,
            "tax_rate": self.estimated_tax_rate,
            "estimated_liability": self.estimated_liability,
            "status": self.tax_status.value,
            "year": self.filing_year,
        }


@dataclass
class TaxOptimizationStrategy:
    """Tax optimization recommendation.
    
    Attributes:
        strategy_id: Unique strategy ID
        strategy_type: Type of strategy (harvest, defer, rebalance, etc)
        description: Strategy description
        potential_savings: Estimated tax savings
        implementation_cost: Cost to implement (e.g., trading fees)
        net_benefit: Net benefit after costs
        priority: Implementation priority
        risk_level: Risk level (low, medium, high)
    """
    strategy_id: str
    strategy_type: str
    description: str
    potential_savings: float
    implementation_cost: float
    net_benefit: float
    priority: str
    risk_level: str
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "id": self.strategy_id,
            "type": self.strategy_type,
            "description": self.description,
            "savings": self.potential_savings,
            "cost": self.implementation_cost,
            "net_benefit": self.net_benefit,
            "priority": self.priority,
            "risk": self.risk_level,
        }


class TaxOptimizer:
    """Tax optimization and capital gains analyzer."""
    
    # Tax brackets for 2026 (estimated)
    TAX_BRACKETS = {
        TaxStatus.SINGLE: [
            (11000, 0.10),
            (44725, 0.12),
            (95375, 0.22),
            (182100, 0.24),
            (231250, 0.32),
            (578125, 0.35),
            (float('inf'), 0.37),
        ],
        TaxStatus.MARRIED_FILING_JOINTLY: [
            (22000, 0.10),
            (89075, 0.12),
            (190750, 0.22),
            (364200, 0.24),
            (462500, 0.32),
            (693750, 0.35),
            (float('inf'), 0.37),
        ],
    }
    
    # Long-term capital gains rates
    LTCG_RATES = {
        TaxStatus.SINGLE: [
            (44625, 0.00),
            (492300, 0.15),
            (float('inf'), 0.20),
        ],
        TaxStatus.MARRIED_FILING_JOINTLY: [
            (89250, 0.00),
            (553850, 0.15),
            (float('inf'), 0.20),
        ],
    }
    
    def __init__(self, tax_status: TaxStatus = TaxStatus.SINGLE):
        """Initialize tax optimizer.
        
        Args:
            tax_status: Tax filing status
        """
        self.tax_status = tax_status
        self.transactions: dict[str, InvestmentTransaction] = {}
        self.realized_gains: list[CapitalGain] = []
        self.current_holdings: dict[str, list[InvestmentTransaction]] = {}  # Asset -> buy transactions
    
    def add_transaction(
        self,
        asset: str,
        transaction_type: TransactionType,
        quantity: float,
        unit_price: float,
        date: datetime,
        fees: float = 0.0,
    ) -> InvestmentTransaction:
        """Add investment transaction.
        
        Args:
            asset: Asset symbol
            transaction_type: Type of transaction
            quantity: Number of shares/units
            unit_price: Price per share/unit
            date: Transaction date
            fees: Transaction fees
        
        Returns:
            Created transaction
        """
        txn_id = str(uuid.uuid4())
        transaction = InvestmentTransaction(
            transaction_id=txn_id,
            asset=asset,
            transaction_type=transaction_type,
            quantity=quantity,
            unit_price=unit_price,
            date=date,
            fees=fees,
        )
        self.transactions[txn_id] = transaction
        
        # Track holdings for FIFO calculation
        if transaction_type == TransactionType.BUY:
            if asset not in self.current_holdings:
                self.current_holdings[asset] = []
            self.current_holdings[asset].append(transaction)
        elif transaction_type == TransactionType.SELL:
            # Calculate gain using FIFO
            self._process_fifo_sale(asset, quantity, unit_price, date)
        
        return transaction
    
    def _process_fifo_sale(self, asset: str, quantity: float, sale_price: float, sale_date: datetime):
        """Process sale using FIFO method.
        
        Args:
            asset: Asset symbol
            quantity: Quantity sold
            sale_price: Sale price per unit
            sale_date: Sale date
        """
        if asset not in self.current_holdings:
            return
        
        remaining = quantity
        while remaining > 0 and self.current_holdings[asset]:
            buy_txn = self.current_holdings[asset][0]
            
            # Determine how much of this buy to use
            used = min(remaining, buy_txn.quantity)
            
            # Calculate gain
            holding_days = (sale_date - buy_txn.date).days
            gain_type = GainType.LONG_TERM if holding_days >= 365 else GainType.SHORT_TERM
            
            cost_basis = buy_txn.unit_price
            realized_gain = (sale_price - cost_basis) * used
            
            gain = CapitalGain(
                asset=asset,
                gain_type=gain_type,
                quantity=used,
                cost_basis=cost_basis,
                sale_price=sale_price,
                realized_gain=realized_gain,
                sale_date=sale_date,
                acquisition_date=buy_txn.date,
            )
            self.realized_gains.append(gain)
            
            # Update holdings
            buy_txn.quantity -= used
            if buy_txn.quantity <= 0:
                self.current_holdings[asset].pop(0)
            
            remaining -= used
    
    def calculate_current_positions(self, current_prices: dict[str, float]) -> dict[str, dict]:
        """Calculate current positions and unrealized gains.
        
        Args:
            current_prices: Current prices by asset
        
        Returns:
            Positions with unrealized gains/losses
        """
        positions = {}
        
        for asset, buy_txns in self.current_holdings.items():
            if not buy_txns or asset not in current_prices:
                continue
            
            current_price = current_prices[asset]
            total_quantity = 0
            total_cost = 0
            
            for txn in buy_txns:
                if txn.quantity > 0:
                    total_quantity += txn.quantity
                    total_cost += txn.quantity * txn.unit_price
            
            if total_quantity > 0:
                avg_cost = total_cost / total_quantity
                current_value = total_quantity * current_price
                unrealized_gain = current_value - total_cost
                
                positions[asset] = {
                    "quantity": total_quantity,
                    "avg_cost": avg_cost,
                    "current_price": current_price,
                    "current_value": current_value,
                    "cost_basis": total_cost,
                    "unrealized_gain": unrealized_gain,
                    "gain_percentage": (unrealized_gain / total_cost * 100) if total_cost > 0 else 0,
                }
        
        return positions
    
    def identify_harvesting_opportunities(
        self,
        current_prices: dict[str, float],
        tax_rate: float = 0.24,
    ) -> list[LossHarvestingOpportunity]:
        """Identify tax-loss harvesting opportunities.
        
        Args:
            current_prices: Current prices by asset
            tax_rate: Marginal tax rate for benefit calculation
        
        Returns:
            List of harvesting opportunities
        """
        positions = self.calculate_current_positions(current_prices)
        opportunities = []
        
        for asset, position in positions.items():
            if position["unrealized_gain"] < 0:  # Loss position
                unrealized_loss = abs(position["unrealized_gain"])
                tax_benefit = unrealized_loss * tax_rate
                
                # Determine replacement (similar but not substantially identical)
                replacement = self._get_replacement_asset(asset)
                
                # Check for wash sale risk (sold same asset in last 30 days?)
                wash_sale_risk = self._check_wash_sale_risk(asset)
                
                opportunity = LossHarvestingOpportunity(
                    asset=asset,
                    current_price=position["current_price"],
                    cost_basis=position["avg_cost"],
                    unrealized_loss=unrealized_loss,
                    potential_tax_benefit=tax_benefit,
                    replacement_asset=replacement,
                    wash_sale_risk=wash_sale_risk,
                )
                opportunities.append(opportunity)
        
        return sorted(opportunities, key=lambda x: x.potential_tax_benefit, reverse=True)
    
    def _get_replacement_asset(self, asset: str) -> Optional[str]:
        """Get replacement asset to avoid wash sale.
        
        Args:
            asset: Current asset
        
        Returns:
            Similar asset to replace with
        """
        # Simple mapping of common replacements
        replacements = {
            "AAPL": "MSFT",
            "MSFT": "AAPL",
            "VOO": "VTI",
            "VTI": "VOO",
            "BTC": "ETH",
            "ETH": "BTC",
        }
        return replacements.get(asset)
    
    def _check_wash_sale_risk(self, asset: str) -> bool:
        """Check if asset has wash sale risk.
        
        Args:
            asset: Asset symbol
        
        Returns:
            Whether wash sale risk exists
        """
        # Check for sales of same asset in last 30 days
        now = datetime.now(timezone.utc)
        thirty_days_ago = now - timedelta(days=30)
        
        for txn in self.transactions.values():
            if (txn.asset == asset and
                txn.transaction_type == TransactionType.SELL and
                txn.date > thirty_days_ago):
                return True
        
        return False
    
    def calculate_tax_liability(self, filing_year: int = 2026) -> TaxLiability:
        """Calculate total tax liability.
        
        Args:
            filing_year: Tax year
        
        Returns:
            Tax liability summary
        """
        # Separate short-term and long-term gains
        short_term = sum(g.realized_gain for g in self.realized_gains if g.gain_type == GainType.SHORT_TERM)
        long_term = sum(g.realized_gain for g in self.realized_gains if g.gain_type == GainType.LONG_TERM)
        total = short_term + long_term
        
        # Calculate tax on short-term gains (ordinary income)
        st_tax = short_term * self._get_marginal_tax_rate(short_term)
        
        # Calculate tax on long-term gains (preferential rate)
        lt_tax = long_term * self._get_ltcg_rate(long_term)
        
        total_tax = st_tax + lt_tax
        
        return TaxLiability(
            short_term_gains=short_term,
            long_term_gains=long_term,
            total_gains=total,
            estimated_tax_rate=self._get_marginal_tax_rate(total),
            estimated_liability=total_tax,
            tax_status=self.tax_status,
            filing_year=filing_year,
        )
    
    def _get_marginal_tax_rate(self, income: float) -> float:
        """Get marginal tax rate for income.
        
        Args:
            income: Taxable income
        
        Returns:
            Tax rate
        """
        brackets = self.TAX_BRACKETS.get(self.tax_status, self.TAX_BRACKETS[TaxStatus.SINGLE])
        for threshold, rate in brackets:
            if income <= threshold:
                return rate
        return brackets[-1][1]
    
    def _get_ltcg_rate(self, gain: float) -> float:
        """Get long-term capital gains rate.
        
        Args:
            gain: Capital gain amount
        
        Returns:
            Tax rate
        """
        rates = self.LTCG_RATES.get(self.tax_status, self.LTCG_RATES[TaxStatus.SINGLE])
        for threshold, rate in rates:
            if gain <= threshold:
                return rate
        return rates[-1][1]
    
    def generate_optimization_strategies(self) -> list[TaxOptimizationStrategy]:
        """Generate tax optimization strategies.
        
        Returns:
            List of recommended strategies
        """
        strategies = []
        
        # Get current tax liability
        liability = self.calculate_tax_liability()
        
        # Strategy 1: Tax-loss harvesting
        opportunities = self.identify_harvesting_opportunities({})  # Would need current prices
        if opportunities:
            total_savings = sum(o.potential_tax_benefit for o in opportunities)
            strategy = TaxOptimizationStrategy(
                strategy_id=str(uuid.uuid4()),
                strategy_type="tax_loss_harvesting",
                description="Harvest losses to offset capital gains",
                potential_savings=total_savings,
                implementation_cost=50.0,  # Estimated trading costs
                net_benefit=total_savings - 50.0,
                priority="high",
                risk_level="low",
            )
            strategies.append(strategy)
        
        # Strategy 2: Long-term gain deferral
        if liability.short_term_gains > 0:
            benefit = liability.short_term_gains * 0.12  # Difference between ST and LT rates
            strategy = TaxOptimizationStrategy(
                strategy_id=str(uuid.uuid4()),
                strategy_type="gain_deferral",
                description="Defer short-term gains to long-term by holding",
                potential_savings=benefit,
                implementation_cost=0.0,
                net_benefit=benefit,
                priority="medium",
                risk_level="medium",
            )
            strategies.append(strategy)
        
        return sorted(strategies, key=lambda x: x.net_benefit, reverse=True)
