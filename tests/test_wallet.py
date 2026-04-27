"""Tests for wallet and expense tracking module."""

import pytest
from datetime import datetime, timezone, timedelta
from pathlib import Path
import tempfile
import json

from jarvis.tools.wallet import (
    Transaction, TransactionType, Account, ExpenseCategory,
    Wallet, WalletManager, get_wallet_summary
)


class TestTransactionType:
    """Tests for transaction type enumeration."""
    
    def test_all_types_defined(self):
        """Verify all transaction types are defined."""
        assert TransactionType.DEBIT.value == "debit"
        assert TransactionType.CREDIT.value == "credit"
        assert TransactionType.TRANSFER.value == "transfer"
        assert TransactionType.REVERSAL.value == "reversal"


class TestExpenseCategory:
    """Tests for expense category enumeration."""
    
    def test_all_categories_defined(self):
        """Verify all expense categories are defined."""
        categories = [cat.value for cat in ExpenseCategory]
        assert "food" in categories
        assert "transport" in categories
        assert "accommodation" in categories
        assert "travel" in categories
        assert "other" in categories


class TestTransaction:
    """Tests for transaction creation and validation."""
    
    def test_transaction_creation(self):
        """Test creating a valid transaction."""
        ts = datetime(2026, 4, 27, 10, 30, 0, tzinfo=timezone.utc)
        tx = Transaction(
            account_id="acct1",
            timestamp=ts,
            transaction_type=TransactionType.DEBIT,
            amount=50.00,
            currency="USD",
            category=ExpenseCategory.FOOD,
            merchant="Coffee Shop",
            description="Morning coffee",
            balance_after=450.00,
        )
        assert tx.amount == 50.00
        assert tx.merchant == "Coffee Shop"
        assert tx.transaction_id is not None
    
    def test_transaction_with_negative_amount_raises(self):
        """Test that negative amounts raise validation error."""
        ts = datetime.now(timezone.utc)
        with pytest.raises(ValueError, match="Amount must be positive"):
            Transaction(
                account_id="acct1",
                timestamp=ts,
                transaction_type=TransactionType.DEBIT,
                amount=-50.00,
                currency="USD",
                category=ExpenseCategory.FOOD,
                merchant="Shop",
                description="Test",
                balance_after=0.0,
            )
    
    def test_transaction_with_naive_datetime_raises(self):
        """Test that naive datetime raises validation error."""
        ts = datetime(2026, 4, 27, 10, 30, 0)  # No timezone
        with pytest.raises(ValueError, match="timezone-aware"):
            Transaction(
                account_id="acct1",
                timestamp=ts,
                transaction_type=TransactionType.DEBIT,
                amount=50.00,
                currency="USD",
                category=ExpenseCategory.FOOD,
                merchant="Shop",
                description="Test",
                balance_after=0.0,
            )
    
    def test_transaction_to_dict(self):
        """Test transaction serialization."""
        ts = datetime(2026, 4, 27, 10, 30, 0, tzinfo=timezone.utc)
        tx = Transaction(
            account_id="acct1",
            timestamp=ts,
            transaction_type=TransactionType.CREDIT,
            amount=1000.00,
            currency="USD",
            category=ExpenseCategory.OTHER,
            merchant="Employer",
            description="Salary",
            balance_after=1500.00,
            reference_number="PAY123",
            tags=["recurring", "payroll"],
        )
        data = tx.to_dict()
        assert data["amount"] == 1000.00
        assert data["transaction_type"] == "credit"
        assert "reference_number" in data
        assert "tags" in data


class TestAccount:
    """Tests for account creation and transaction management."""
    
    def test_account_creation(self):
        """Test creating a valid account."""
        ts = datetime(2026, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        account = Account(
            account_id="acct1",
            name="Checking",
            account_type="checking",
            currency="USD",
            balance=1000.00,
            created_at=ts,
        )
        assert account.balance == 1000.00
        assert account.is_active is True
        assert len(account.transactions) == 0
    
    def test_account_with_monthly_budget(self):
        """Test account with spending budget."""
        ts = datetime(2026, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        account = Account(
            account_id="acct1",
            name="Checking",
            account_type="checking",
            currency="USD",
            balance=1000.00,
            created_at=ts,
            monthly_budget=500.00,
        )
        assert account.monthly_budget == 500.00
    
    def test_add_debit_transaction(self):
        """Test adding a debit transaction."""
        ts = datetime(2026, 4, 27, 10, 0, 0, tzinfo=timezone.utc)
        account = Account(
            account_id="acct1",
            name="Checking",
            account_type="checking",
            currency="USD",
            balance=1000.00,
            created_at=ts,
        )
        
        tx = Transaction(
            account_id="acct1",
            timestamp=ts,
            transaction_type=TransactionType.DEBIT,
            amount=100.00,
            currency="USD",
            category=ExpenseCategory.FOOD,
            merchant="Restaurant",
            description="Dinner",
            balance_after=900.00,
        )
        account.add_transaction(tx)
        
        assert account.balance == 900.00
        assert len(account.transactions) == 1
    
    def test_add_credit_transaction(self):
        """Test adding a credit transaction."""
        ts = datetime(2026, 4, 27, 10, 0, 0, tzinfo=timezone.utc)
        account = Account(
            account_id="acct1",
            name="Checking",
            account_type="checking",
            currency="USD",
            balance=1000.00,
            created_at=ts,
        )
        
        tx = Transaction(
            account_id="acct1",
            timestamp=ts,
            transaction_type=TransactionType.CREDIT,
            amount=500.00,
            currency="USD",
            category=ExpenseCategory.OTHER,
            merchant="Employer",
            description="Bonus",
            balance_after=1500.00,
        )
        account.add_transaction(tx)
        
        assert account.balance == 1500.00
    
    def test_get_monthly_spending(self):
        """Test calculating monthly spending."""
        ts1 = datetime(2026, 4, 1, 10, 0, 0, tzinfo=timezone.utc)
        ts2 = datetime(2026, 4, 15, 10, 0, 0, tzinfo=timezone.utc)
        ts3 = datetime(2026, 5, 1, 10, 0, 0, tzinfo=timezone.utc)
        
        account = Account(
            account_id="acct1",
            name="Checking",
            account_type="checking",
            currency="USD",
            balance=1000.00,
            created_at=ts1,
        )
        
        # April transactions
        account.add_transaction(Transaction(
            account_id="acct1", timestamp=ts1, transaction_type=TransactionType.DEBIT,
            amount=50.00, currency="USD", category=ExpenseCategory.FOOD,
            merchant="Shop1", description="Food", balance_after=950.00,
        ))
        account.add_transaction(Transaction(
            account_id="acct1", timestamp=ts2, transaction_type=TransactionType.DEBIT,
            amount=30.00, currency="USD", category=ExpenseCategory.FOOD,
            merchant="Shop2", description="Food", balance_after=920.00,
        ))
        
        # May transaction
        account.add_transaction(Transaction(
            account_id="acct1", timestamp=ts3, transaction_type=TransactionType.DEBIT,
            amount=20.00, currency="USD", category=ExpenseCategory.FOOD,
            merchant="Shop3", description="Food", balance_after=900.00,
        ))
        
        april_spending = account.get_monthly_spending(2026, 4)
        may_spending = account.get_monthly_spending(2026, 5)
        
        assert april_spending == 80.00
        assert may_spending == 20.00
    
    def test_spending_by_category(self):
        """Test spending breakdown by category."""
        ts = datetime(2026, 4, 27, 10, 0, 0, tzinfo=timezone.utc)
        account = Account(
            account_id="acct1",
            name="Checking",
            account_type="checking",
            currency="USD",
            balance=1000.00,
            created_at=ts,
        )
        
        account.add_transaction(Transaction(
            account_id="acct1", timestamp=ts, transaction_type=TransactionType.DEBIT,
            amount=50.00, currency="USD", category=ExpenseCategory.FOOD,
            merchant="Shop", description="Food", balance_after=950.00,
        ))
        account.add_transaction(Transaction(
            account_id="acct1", timestamp=ts, transaction_type=TransactionType.DEBIT,
            amount=100.00, currency="USD", category=ExpenseCategory.TRANSPORT,
            merchant="Uber", description="Ride", balance_after=850.00,
        ))
        
        breakdown = account.spending_by_category(2026, 4)
        assert breakdown["food"] == 50.00
        assert breakdown["transport"] == 100.00
    
    def test_is_budget_exceeded(self):
        """Test budget exceeded detection."""
        ts = datetime(2026, 4, 27, 10, 0, 0, tzinfo=timezone.utc)
        account = Account(
            account_id="acct1",
            name="Checking",
            account_type="checking",
            currency="USD",
            balance=1000.00,
            created_at=ts,
            monthly_budget=100.00,
        )
        
        # Spend 80 (within budget)
        account.add_transaction(Transaction(
            account_id="acct1", timestamp=ts, transaction_type=TransactionType.DEBIT,
            amount=80.00, currency="USD", category=ExpenseCategory.FOOD,
            merchant="Shop", description="Food", balance_after=920.00,
        ))
        assert not account.is_budget_exceeded(2026, 4)
        
        # Spend 30 more (total 110, exceeds 100 budget)
        account.add_transaction(Transaction(
            account_id="acct1", timestamp=ts, transaction_type=TransactionType.DEBIT,
            amount=30.00, currency="USD", category=ExpenseCategory.FOOD,
            merchant="Shop2", description="Food", balance_after=890.00,
        ))
        assert account.is_budget_exceeded(2026, 4)


class TestWallet:
    """Tests for wallet multi-account management."""
    
    def test_wallet_creation(self):
        """Test creating a wallet."""
        ts = datetime.now(timezone.utc)
        wallet = Wallet(
            wallet_id="wallet1",
            owner_name="John Doe",
            created_at=ts,
        )
        assert wallet.wallet_id == "wallet1"
        assert wallet.owner_name == "John Doe"
        assert len(wallet.accounts) == 0
    
    def test_add_account(self):
        """Test adding an account to wallet."""
        ts = datetime.now(timezone.utc)
        wallet = Wallet(
            wallet_id="wallet1",
            owner_name="John Doe",
            created_at=ts,
        )
        
        account = Account(
            account_id="acct1",
            name="Checking",
            account_type="checking",
            currency="USD",
            balance=1000.00,
            created_at=ts,
        )
        wallet.add_account(account)
        
        assert len(wallet.accounts) == 1
        assert wallet.get_account("acct1") is not None
    
    def test_add_duplicate_account_raises(self):
        """Test that duplicate account IDs raise error."""
        ts = datetime.now(timezone.utc)
        wallet = Wallet(
            wallet_id="wallet1",
            owner_name="John Doe",
            created_at=ts,
        )
        
        account1 = Account(
            account_id="acct1",
            name="Checking",
            account_type="checking",
            currency="USD",
            balance=1000.00,
            created_at=ts,
        )
        wallet.add_account(account1)
        
        account2 = Account(
            account_id="acct1",
            name="Savings",
            account_type="savings",
            currency="USD",
            balance=5000.00,
            created_at=ts,
        )
        with pytest.raises(ValueError, match="already exists"):
            wallet.add_account(account2)
    
    def test_total_balance(self):
        """Test calculating total wallet balance."""
        ts = datetime.now(timezone.utc)
        wallet = Wallet(
            wallet_id="wallet1",
            owner_name="John Doe",
            created_at=ts,
        )
        
        wallet.add_account(Account(
            account_id="acct1",
            name="Checking",
            account_type="checking",
            currency="USD",
            balance=1000.00,
            created_at=ts,
        ))
        wallet.add_account(Account(
            account_id="acct2",
            name="Savings",
            account_type="savings",
            currency="USD",
            balance=5000.00,
            created_at=ts,
        ))
        
        assert wallet.total_balance() == 6000.00
    
    def test_spending_summary(self):
        """Test consolidated spending summary."""
        ts = datetime(2026, 4, 27, 10, 0, 0, tzinfo=timezone.utc)
        wallet = Wallet(
            wallet_id="wallet1",
            owner_name="John Doe",
            created_at=ts,
        )
        
        account = Account(
            account_id="acct1",
            name="Checking",
            account_type="checking",
            currency="USD",
            balance=1000.00,
            created_at=ts,
        )
        account.add_transaction(Transaction(
            account_id="acct1", timestamp=ts, transaction_type=TransactionType.DEBIT,
            amount=50.00, currency="USD", category=ExpenseCategory.FOOD,
            merchant="Shop", description="Food", balance_after=950.00,
        ))
        wallet.add_account(account)
        
        summary = wallet.spending_summary(2026, 4)
        assert summary["total_spending"] == 50.00
        assert summary["by_category"]["food"] == 50.00
    
    def test_net_worth(self):
        """Test net worth calculation."""
        ts = datetime.now(timezone.utc)
        wallet = Wallet(
            wallet_id="wallet1",
            owner_name="John Doe",
            created_at=ts,
        )
        
        wallet.add_account(Account(
            account_id="acct1",
            name="Checking",
            account_type="checking",
            currency="USD",
            balance=1000.00,
            created_at=ts,
        ))
        wallet.add_account(Account(
            account_id="acct2",
            name="Credit Card",
            account_type="credit_card",
            currency="USD",
            balance=-500.00,
            created_at=ts,
        ))
        
        # Total balance includes credit card debt
        assert wallet.total_balance() == 500.00
        
        # Net worth excludes credit cards
        assert wallet.get_net_worth(exclude_debts=True) == 1000.00


class TestWalletManager:
    """Tests for wallet persistence and retrieval."""
    
    def test_manager_creation(self):
        """Test creating a wallet manager."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = WalletManager(Path(tmpdir))
            assert manager.data_dir == Path(tmpdir)
    
    def test_create_wallet(self):
        """Test creating a wallet through manager."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = WalletManager(Path(tmpdir))
            wallet = manager.create_wallet("John Doe")
            
            assert wallet.wallet_id is not None
            assert wallet.owner_name == "John Doe"
            assert wallet in manager.list_wallets()
    
    def test_save_and_load_wallet(self):
        """Test wallet persistence and loading."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = WalletManager(Path(tmpdir))
            
            # Create and populate wallet
            wallet = manager.create_wallet("John Doe")
            ts = datetime.now(timezone.utc)
            account = Account(
                account_id="acct1",
                name="Checking",
                account_type="checking",
                currency="USD",
                balance=1000.00,
                created_at=ts,
            )
            account.add_transaction(Transaction(
                account_id="acct1", timestamp=ts, transaction_type=TransactionType.DEBIT,
                amount=100.00, currency="USD", category=ExpenseCategory.FOOD,
                merchant="Shop", description="Food", balance_after=900.00,
            ))
            wallet.add_account(account)
            
            # Save wallet to disk
            manager.save_wallet(wallet)
            
            # Load from disk
            loaded_wallet = manager.load_wallet(wallet.wallet_id)
            
            assert loaded_wallet is not None
            assert loaded_wallet.owner_name == "John Doe"
            assert len(loaded_wallet.accounts) == 1
            assert loaded_wallet.get_account("acct1").balance == 900.00
            assert len(loaded_wallet.get_account("acct1").transactions) == 1
    
    def test_load_nonexistent_wallet(self):
        """Test loading a wallet that doesn't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = WalletManager(Path(tmpdir))
            loaded = manager.load_wallet("nonexistent")
            assert loaded is None


class TestWalletSummary:
    """Tests for wallet summary generation."""
    
    def test_wallet_summary(self):
        """Test generating a wallet summary."""
        ts = datetime.now(timezone.utc)
        wallet = Wallet(
            wallet_id="wallet1",
            owner_name="John Doe",
            created_at=ts,
        )
        
        account = Account(
            account_id="acct1",
            name="Checking",
            account_type="checking",
            currency="USD",
            balance=1000.00,
            created_at=ts,
        )
        account.add_transaction(Transaction(
            account_id="acct1", timestamp=ts, transaction_type=TransactionType.DEBIT,
            amount=100.00, currency="USD", category=ExpenseCategory.FOOD,
            merchant="Shop", description="Food", balance_after=900.00,
        ))
        wallet.add_account(account)
        
        summary = get_wallet_summary(wallet)
        assert summary["owner"] == "John Doe"
        assert summary["total_balance"] == 900.00
        assert summary["account_count"] == 1
        assert summary["monthly_spending"] == 100.00
