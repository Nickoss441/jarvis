"""Personal wallet and expense tracking module.

Provides account management, transaction logging, budget tracking,
category-based expense analysis, and spending alerts with integration
to travel itineraries and payment governance.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Optional
import json
import uuid


class TransactionType(str, Enum):
    """Transaction type enumeration."""
    DEBIT = "debit"
    CREDIT = "credit"
    TRANSFER = "transfer"
    REVERSAL = "reversal"


class ExpenseCategory(str, Enum):
    """Expense category enumeration for spending analysis."""
    FOOD = "food"
    TRANSPORT = "transport"
    ACCOMMODATION = "accommodation"
    ENTERTAINMENT = "entertainment"
    SHOPPING = "shopping"
    UTILITIES = "utilities"
    HEALTHCARE = "healthcare"
    EDUCATION = "education"
    TRAVEL = "travel"
    SUBSCRIPTIONS = "subscriptions"
    OTHER = "other"


@dataclass
class Transaction:
    """A single financial transaction.
    
    Attributes:
        transaction_id: Unique transaction identifier (UUID)
        account_id: Associated account ID
        timestamp: When transaction occurred (UTC)
        transaction_type: Type of transaction (debit/credit/transfer/reversal)
        amount: Transaction amount (positive decimal)
        currency: Currency code (e.g., "USD", "EUR")
        category: Expense category for analysis
        merchant: Merchant or payee name
        description: Transaction description/memo
        balance_after: Account balance after transaction
        reference_number: External reference (check number, confirmation, etc.)
        tags: Custom tags for transaction grouping
    """
    account_id: str
    timestamp: datetime
    transaction_type: TransactionType
    amount: float
    currency: str
    category: ExpenseCategory
    merchant: str
    description: str
    balance_after: float
    transaction_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    reference_number: Optional[str] = None
    tags: list[str] = field(default_factory=list)
    
    def __post_init__(self):
        """Validate transaction data."""
        if self.amount < 0:
            raise ValueError(f"Amount must be positive, got {self.amount}")
        if not isinstance(self.timestamp, datetime):
            raise ValueError("timestamp must be a datetime object")
        if self.timestamp.tzinfo is None:
            raise ValueError("timestamp must be timezone-aware (UTC)")
    
    def to_dict(self) -> dict:
        """Convert transaction to dictionary."""
        return {
            "transaction_id": self.transaction_id,
            "account_id": self.account_id,
            "timestamp": self.timestamp.isoformat(),
            "transaction_type": self.transaction_type.value,
            "amount": self.amount,
            "currency": self.currency,
            "category": self.category.value,
            "merchant": self.merchant,
            "description": self.description,
            "balance_after": self.balance_after,
            "reference_number": self.reference_number,
            "tags": self.tags,
        }


@dataclass
class Account:
    """A financial account (checking, savings, card, etc.).
    
    Attributes:
        account_id: Unique account identifier
        name: Display name (e.g., "Checking", "Amex", "Emergency Fund")
        account_type: Type of account (checking, savings, credit_card, investment)
        currency: Primary currency for the account
        balance: Current balance
        is_active: Whether account is active
        created_at: Account creation timestamp (UTC)
        monthly_budget: Optional monthly spending limit
        alert_threshold: Alert when balance falls below this value
        transactions: List of all transactions on this account
    """
    account_id: str
    name: str
    account_type: str
    currency: str
    balance: float
    created_at: datetime
    is_active: bool = True
    monthly_budget: Optional[float] = None
    alert_threshold: Optional[float] = None
    transactions: list[Transaction] = field(default_factory=list)
    
    def __post_init__(self):
        """Validate account data."""
        if not isinstance(self.created_at, datetime):
            raise ValueError("created_at must be a datetime object")
        if self.created_at.tzinfo is None:
            raise ValueError("created_at must be timezone-aware (UTC)")
        if self.balance < 0 and self.account_type != "credit_card":
            raise ValueError(f"Balance cannot be negative for {self.account_type}")
        if self.monthly_budget is not None and self.monthly_budget < 0:
            raise ValueError(f"Monthly budget must be positive, got {self.monthly_budget}")
    
    def add_transaction(self, transaction: Transaction) -> None:
        """Add a transaction to the account and update balance."""
        if transaction.account_id != self.account_id:
            raise ValueError(f"Transaction account_id {transaction.account_id} doesn't match account {self.account_id}")
        
        # Update balance based on transaction type
        if transaction.transaction_type == TransactionType.DEBIT:
            self.balance -= transaction.amount
        elif transaction.transaction_type == TransactionType.CREDIT:
            self.balance += transaction.amount
        elif transaction.transaction_type == TransactionType.TRANSFER:
            # Transfers can be debit or credit depending on direction; balance_after is authoritative
            self.balance = transaction.balance_after
        elif transaction.transaction_type == TransactionType.REVERSAL:
            # Reversal: reverse the sign
            self.balance = transaction.balance_after
        
        self.transactions.append(transaction)
    
    def get_monthly_spending(self, year: int, month: int) -> float:
        """Get total spending for a specific month."""
        total = 0.0
        for tx in self.transactions:
            if (tx.timestamp.year == year and tx.timestamp.month == month and
                tx.transaction_type == TransactionType.DEBIT):
                total += tx.amount
        return total
    
    def spending_by_category(self, year: int = None, month: int = None) -> dict[str, float]:
        """Get spending breakdown by category."""
        breakdown: dict[str, float] = {}
        for tx in self.transactions:
            if tx.transaction_type != TransactionType.DEBIT:
                continue
            
            # Filter by month if specified
            if year is not None and month is not None:
                if tx.timestamp.year != year or tx.timestamp.month != month:
                    continue
            elif year is not None:
                if tx.timestamp.year != year:
                    continue
            
            category = tx.category.value
            breakdown[category] = breakdown.get(category, 0.0) + tx.amount
        
        return breakdown
    
    def is_budget_exceeded(self, year: int, month: int) -> bool:
        """Check if monthly budget has been exceeded."""
        if self.monthly_budget is None:
            return False
        return self.get_monthly_spending(year, month) > self.monthly_budget
    
    def to_dict(self) -> dict:
        """Convert account to dictionary."""
        return {
            "account_id": self.account_id,
            "name": self.name,
            "account_type": self.account_type,
            "currency": self.currency,
            "balance": self.balance,
            "created_at": self.created_at.isoformat(),
            "is_active": self.is_active,
            "monthly_budget": self.monthly_budget,
            "alert_threshold": self.alert_threshold,
            "transaction_count": len(self.transactions),
        }


@dataclass
class Wallet:
    """Multi-account financial wallet with consolidated tracking.
    
    Attributes:
        wallet_id: Unique wallet identifier
        owner_name: Wallet owner name
        created_at: Wallet creation timestamp (UTC)
        accounts: Dictionary of account_id -> Account
        recurring_expenses: Dict of recurring transaction patterns (for budgeting)
        alerts: List of recent alerts (budget exceeded, low balance, etc.)
    """
    wallet_id: str
    owner_name: str
    created_at: datetime
    accounts: dict[str, Account] = field(default_factory=dict)
    recurring_expenses: dict[str, float] = field(default_factory=dict)
    alerts: list[dict] = field(default_factory=list)
    
    def __post_init__(self):
        """Validate wallet data."""
        if not isinstance(self.created_at, datetime):
            raise ValueError("created_at must be a datetime object")
        if self.created_at.tzinfo is None:
            raise ValueError("created_at must be timezone-aware (UTC)")
    
    def add_account(self, account: Account) -> None:
        """Add an account to the wallet."""
        if account.account_id in self.accounts:
            raise ValueError(f"Account {account.account_id} already exists")
        self.accounts[account.account_id] = account
    
    def get_account(self, account_id: str) -> Optional[Account]:
        """Retrieve an account by ID."""
        return self.accounts.get(account_id)
    
    def total_balance(self, include_inactive: bool = False) -> float:
        """Get total balance across all accounts."""
        total = 0.0
        for account in self.accounts.values():
            if include_inactive or account.is_active:
                total += account.balance
        return total
    
    def add_transaction(self, account_id: str, transaction: Transaction) -> None:
        """Add a transaction to an account."""
        account = self.get_account(account_id)
        if account is None:
            raise ValueError(f"Account {account_id} not found")
        account.add_transaction(transaction)
        
        # Check for alerts
        if account.monthly_budget and account.is_budget_exceeded(transaction.timestamp.year, transaction.timestamp.month):
            self._add_alert(
                "budget_exceeded",
                f"Monthly budget of {account.monthly_budget} {account.currency} exceeded on account {account.name}"
            )
        
        if account.alert_threshold and account.balance < account.alert_threshold:
            self._add_alert(
                "low_balance",
                f"Balance on {account.name} ({account.balance}) below threshold ({account.alert_threshold})"
            )
    
    def get_net_worth(self, exclude_debts: bool = False) -> float:
        """Calculate net worth (sum of assets)."""
        if exclude_debts:
            # Exclude credit cards and debt accounts
            total = 0.0
            for account in self.accounts.values():
                if account.account_type not in ["credit_card", "loan"]:
                    total += account.balance
            return total
        return self.total_balance()
    
    def spending_summary(self, year: int = None, month: int = None) -> dict:
        """Get consolidated spending summary across all accounts."""
        summary = {
            "total_spending": 0.0,
            "by_category": {},
            "by_account": {},
            "accounts": {}
        }
        
        for account_id, account in self.accounts.items():
            if not account.is_active:
                continue
            
            monthly_spending = account.get_monthly_spending(year or datetime.now(timezone.utc).year,
                                                          month or datetime.now(timezone.utc).month)
            summary["total_spending"] += monthly_spending
            summary["by_account"][account.name] = monthly_spending
            summary["accounts"][account_id] = {
                "name": account.name,
                "spending": monthly_spending,
                "budget": account.monthly_budget,
            }
            
            # Aggregate categories
            cat_breakdown = account.spending_by_category(year, month)
            for category, amount in cat_breakdown.items():
                summary["by_category"][category] = summary["by_category"].get(category, 0.0) + amount
        
        return summary
    
    def _add_alert(self, alert_type: str, message: str) -> None:
        """Internal method to add an alert."""
        self.alerts.append({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "type": alert_type,
            "message": message,
        })
    
    def to_dict(self) -> dict:
        """Convert wallet to dictionary."""
        return {
            "wallet_id": self.wallet_id,
            "owner_name": self.owner_name,
            "created_at": self.created_at.isoformat(),
            "account_count": len(self.accounts),
            "total_balance": self.total_balance(),
            "net_worth": self.get_net_worth(),
            "active_accounts": sum(1 for a in self.accounts.values() if a.is_active),
        }


class WalletManager:
    """Manager for persistent wallet storage and retrieval."""
    
    def __init__(self, data_dir: Optional[Path] = None):
        """Initialize wallet manager.
        
        Args:
            data_dir: Directory for wallet persistence (defaults to D:/jarvis-data/wallets/)
        """
        if data_dir is None:
            data_dir = Path("D:/jarvis-data/wallets")
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.wallets: dict[str, Wallet] = {}
    
    def create_wallet(self, owner_name: str) -> Wallet:
        """Create a new wallet."""
        wallet_id = str(uuid.uuid4())
        wallet = Wallet(
            wallet_id=wallet_id,
            owner_name=owner_name,
            created_at=datetime.now(timezone.utc),
        )
        self.wallets[wallet_id] = wallet
        self.save_wallet(wallet)
        return wallet
    
    def get_wallet(self, wallet_id: str) -> Optional[Wallet]:
        """Retrieve a wallet by ID."""
        if wallet_id in self.wallets:
            return self.wallets[wallet_id]
        
        # Try to load from disk
        return self.load_wallet(wallet_id)
    
    def list_wallets(self) -> list[Wallet]:
        """List all wallets."""
        return list(self.wallets.values())
    
    def save_wallet(self, wallet: Wallet) -> Path:
        """Persist wallet to JSON file."""
        wallet_file = self.data_dir / f"{wallet.wallet_id}.json"
        
        # Serialize wallet with all accounts and transactions
        data = {
            "wallet_id": wallet.wallet_id,
            "owner_name": wallet.owner_name,
            "created_at": wallet.created_at.isoformat(),
            "recurring_expenses": wallet.recurring_expenses,
            "alerts": wallet.alerts,
            "accounts": {
                account_id: {
                    "account_id": account.account_id,
                    "name": account.name,
                    "account_type": account.account_type,
                    "currency": account.currency,
                    "balance": account.balance,
                    "created_at": account.created_at.isoformat(),
                    "is_active": account.is_active,
                    "monthly_budget": account.monthly_budget,
                    "alert_threshold": account.alert_threshold,
                    "transactions": [tx.to_dict() for tx in account.transactions],
                }
                for account_id, account in wallet.accounts.items()
            }
        }
        
        with open(wallet_file, "w") as f:
            json.dump(data, f, indent=2)
        
        return wallet_file
    
    def load_wallet(self, wallet_id: str) -> Optional[Wallet]:
        """Load a wallet from JSON file."""
        wallet_file = self.data_dir / f"{wallet_id}.json"
        
        if not wallet_file.exists():
            return None
        
        with open(wallet_file, "r") as f:
            data = json.load(f)
        
        wallet = Wallet(
            wallet_id=data["wallet_id"],
            owner_name=data["owner_name"],
            created_at=datetime.fromisoformat(data["created_at"]),
            recurring_expenses=data.get("recurring_expenses", {}),
            alerts=data.get("alerts", []),
        )
        
        # Load accounts with transactions
        for account_id, account_data in data.get("accounts", {}).items():
            account = Account(
                account_id=account_data["account_id"],
                name=account_data["name"],
                account_type=account_data["account_type"],
                currency=account_data["currency"],
                balance=account_data["balance"],
                created_at=datetime.fromisoformat(account_data["created_at"]),
                is_active=account_data.get("is_active", True),
                monthly_budget=account_data.get("monthly_budget"),
                alert_threshold=account_data.get("alert_threshold"),
            )
            
            # Load transactions
            for tx_data in account_data.get("transactions", []):
                # Parse timestamp and ensure UTC timezone
                timestamp = datetime.fromisoformat(tx_data["timestamp"])
                if timestamp.tzinfo is None:
                    timestamp = timestamp.replace(tzinfo=timezone.utc)
                
                transaction = Transaction(
                    transaction_id=tx_data["transaction_id"],
                    account_id=tx_data["account_id"],
                    timestamp=timestamp,
                    transaction_type=TransactionType(tx_data["transaction_type"]),
                    amount=tx_data["amount"],
                    currency=tx_data["currency"],
                    category=ExpenseCategory(tx_data["category"]),
                    merchant=tx_data["merchant"],
                    description=tx_data["description"],
                    balance_after=tx_data["balance_after"],
                    reference_number=tx_data.get("reference_number"),
                    tags=tx_data.get("tags", []),
                )
                account.transactions.append(transaction)
            
            wallet.add_account(account)
        
        # Cache in memory
        self.wallets[wallet_id] = wallet
        return wallet


def get_wallet_summary(wallet: Wallet) -> dict:
    """Generate a summary of wallet status and activity."""
    now = datetime.now(timezone.utc)
    
    return {
        "wallet_id": wallet.wallet_id,
        "owner": wallet.owner_name,
        "total_balance": wallet.total_balance(),
        "net_worth": wallet.get_net_worth(),
        "account_count": len(wallet.accounts),
        "active_accounts": sum(1 for a in wallet.accounts.values() if a.is_active),
        "monthly_spending": wallet.spending_summary(now.year, now.month)["total_spending"],
        "alerts": len(wallet.alerts),
        "recent_alerts": wallet.alerts[-3:] if wallet.alerts else [],
    }
