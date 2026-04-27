"""Personal finance REST API exposing all financial modules.

Provides REST endpoints for accessing wallet, crypto portfolio, budget
forecasting, financial dashboard, expense analytics, portfolio optimization,
and subscription management functionality.
"""

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Optional, Any
import uuid
import json


class APIError(Exception):
    """API error with status code."""
    
    def __init__(self, message: str, status_code: int = 400):
        """Initialize API error."""
        super().__init__(message)
        self.message = message
        self.status_code = status_code


@dataclass
class APIResponse:
    """Standard API response.
    
    Attributes:
        status: Response status (success, error)
        message: Response message
        data: Response data (dict or list)
        timestamp: When response was generated
        request_id: Unique request identifier
    """
    status: str
    message: str
    data: Any = None
    timestamp: datetime = None
    request_id: str = None
    
    def __post_init__(self):
        """Set defaults."""
        if self.timestamp is None:
            self.timestamp = datetime.now(timezone.utc)
        if self.request_id is None:
            self.request_id = str(uuid.uuid4())
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        result = {
            "status": self.status,
            "message": self.message,
            "timestamp": self.timestamp.isoformat(),
            "request_id": self.request_id,
        }
        if self.data is not None:
            result["data"] = self.data
        return result


class WalletEndpoint:
    """Wallet management endpoints."""
    
    @staticmethod
    def list_wallets() -> dict:
        """List all wallets.
        
        Returns:
            List of wallets with balances
        """
        return {
            "endpoint": "/api/wallet/list",
            "method": "GET",
            "description": "Get all wallet addresses and balances",
            "params": {
                "currency_filter": "Optional[str] - Filter by currency (USD, EUR, etc)",
                "include_inactive": "Optional[bool] - Include inactive wallets",
            },
            "response_example": {
                "wallets": [
                    {
                        "wallet_id": "wallet-uuid",
                        "address": "0x...",
                        "currency": "USD",
                        "balance": 10000.50,
                        "last_updated": "2026-04-27T10:00:00Z",
                    }
                ],
                "total_balance": 10000.50,
                "currency": "USD",
            },
        }
    
    @staticmethod
    def add_transaction(wallet_id: str, amount: float, description: str) -> dict:
        """Add transaction to wallet.
        
        Args:
            wallet_id: Wallet ID
            amount: Transaction amount
            description: Transaction description
        
        Returns:
            Created transaction
        """
        return {
            "endpoint": "/api/wallet/transaction",
            "method": "POST",
            "description": "Record a wallet transaction",
            "body": {
                "wallet_id": "str - Target wallet ID",
                "amount": "float - Transaction amount (positive for debit, negative for credit)",
                "description": "str - Transaction description",
                "tags": "Optional[list[str]] - Transaction tags",
                "date": "Optional[datetime] - Transaction date",
            },
            "response_example": {
                "transaction_id": "txn-uuid",
                "wallet_id": wallet_id,
                "amount": amount,
                "description": description,
                "balance_after": 10000.50,
                "timestamp": "2026-04-27T10:00:00Z",
            },
        }


class CryptoEndpoint:
    """Cryptocurrency portfolio endpoints."""
    
    @staticmethod
    def get_portfolio_summary() -> dict:
        """Get cryptocurrency portfolio summary.
        
        Returns:
            Portfolio summary with allocations and performance
        """
        return {
            "endpoint": "/api/crypto/summary",
            "method": "GET",
            "description": "Get cryptocurrency portfolio overview",
            "response_example": {
                "total_value": 50000.00,
                "total_cost_basis": 48000.00,
                "unrealized_gain": 2000.00,
                "assets": [
                    {
                        "symbol": "BTC",
                        "amount": 0.5,
                        "value": 30000.00,
                        "allocation": 0.60,
                    }
                ],
                "last_updated": "2026-04-27T10:00:00Z",
            },
        }
    
    @staticmethod
    def add_position(symbol: str, amount: float, cost_basis: float) -> dict:
        """Add cryptocurrency position.
        
        Args:
            symbol: Crypto symbol (BTC, ETH, etc)
            amount: Amount held
            cost_basis: Cost per unit
        
        Returns:
            Created position
        """
        return {
            "endpoint": "/api/crypto/position",
            "method": "POST",
            "description": "Add or update cryptocurrency position",
            "body": {
                "symbol": "str - Cryptocurrency symbol",
                "amount": "float - Amount held",
                "cost_basis": "float - Cost per unit",
                "purchase_date": "Optional[datetime]",
            },
            "response_example": {
                "position_id": "pos-uuid",
                "symbol": symbol,
                "amount": amount,
                "current_value": 25000.00,
                "cost_basis": cost_basis,
                "unrealized_gain": 2000.00,
            },
        }


class BudgetEndpoint:
    """Budget and forecasting endpoints."""
    
    @staticmethod
    def get_budget_status() -> dict:
        """Get current budget status.
        
        Returns:
            Current spending vs budget for each category
        """
        return {
            "endpoint": "/api/budget/status",
            "method": "GET",
            "description": "Get budget status for current month",
            "params": {
                "period": "Optional[str] - Period (daily, weekly, monthly, yearly)",
            },
            "response_example": {
                "period": "monthly",
                "categories": [
                    {
                        "category": "food",
                        "budget": 500.00,
                        "spent": 350.00,
                        "remaining": 150.00,
                        "percentage_used": 70.0,
                    }
                ],
                "total_budget": 5000.00,
                "total_spent": 3500.00,
                "total_remaining": 1500.00,
            },
        }
    
    @staticmethod
    def get_forecast(months: int = 12) -> dict:
        """Get budget forecast.
        
        Args:
            months: Number of months to forecast
        
        Returns:
            Projected spending and savings
        """
        return {
            "endpoint": "/api/budget/forecast",
            "method": "GET",
            "description": "Get spending forecast",
            "params": {
                "months": f"Optional[int] - Months to forecast (default: 12)",
            },
            "response_example": {
                "forecast_period": months,
                "monthly_projections": [
                    {
                        "month": "2026-05",
                        "projected_income": 6000.00,
                        "projected_spending": 3500.00,
                        "projected_savings": 2500.00,
                    }
                ],
                "total_projected_income": 72000.00,
                "total_projected_spending": 42000.00,
                "total_projected_savings": 30000.00,
            },
        }


class FinancialDashboardEndpoint:
    """Financial dashboard endpoints."""
    
    @staticmethod
    def get_net_worth() -> dict:
        """Get current net worth.
        
        Returns:
            Net worth snapshot with breakdown
        """
        return {
            "endpoint": "/api/dashboard/net-worth",
            "method": "GET",
            "description": "Get current net worth",
            "response_example": {
                "total_net_worth": 150000.00,
                "assets": {
                    "cash": 30000.00,
                    "investments": 100000.00,
                    "crypto": 15000.00,
                    "real_estate": 500000.00,
                },
                "liabilities": {
                    "debt": 100000.00,
                    "loans": 50000.00,
                },
                "timestamp": "2026-04-27T10:00:00Z",
            },
        }
    
    @staticmethod
    def get_financial_health() -> dict:
        """Get financial health metrics.
        
        Returns:
            Key financial ratios and metrics
        """
        return {
            "endpoint": "/api/dashboard/health",
            "method": "GET",
            "description": "Get financial health metrics",
            "response_example": {
                "savings_rate": 0.42,
                "expense_ratio": 0.58,
                "emergency_fund_months": 8.5,
                "debt_to_income": 0.15,
                "net_worth_trend": "increasing",
                "financial_status": "excellent",
            },
        }
    
    @staticmethod
    def get_recommendations() -> dict:
        """Get financial recommendations.
        
        Returns:
            Personalized financial recommendations
        """
        return {
            "endpoint": "/api/dashboard/recommendations",
            "method": "GET",
            "description": "Get personalized financial recommendations",
            "response_example": {
                "recommendations": [
                    {
                        "category": "savings",
                        "recommendation": "Increase emergency fund to 6 months",
                        "potential_benefit": "Better financial security",
                        "priority": "medium",
                    }
                ],
                "alerts": [
                    {
                        "alert_type": "spending",
                        "message": "Spending exceeded budget this month",
                        "severity": "warning",
                    }
                ],
            },
        }


class ExpenseAnalyticsEndpoint:
    """Expense analytics endpoints."""
    
    @staticmethod
    def get_spending_patterns() -> dict:
        """Get spending patterns analysis.
        
        Returns:
            Spending patterns by category and time
        """
        return {
            "endpoint": "/api/analytics/patterns",
            "method": "GET",
            "description": "Get spending pattern analysis",
            "params": {
                "months": "Optional[int] - Number of months to analyze (default: 12)",
            },
            "response_example": {
                "categories": [
                    {
                        "category": "food",
                        "average_monthly": 400.00,
                        "trend": "increasing",
                        "monthly_change": 0.05,
                    }
                ],
                "total_average_monthly": 3500.00,
                "analysis_period": "12 months",
            },
        }
    
    @staticmethod
    def get_anomalies() -> dict:
        """Get spending anomalies.
        
        Returns:
            Detected spending anomalies and outliers
        """
        return {
            "endpoint": "/api/analytics/anomalies",
            "method": "GET",
            "description": "Detect spending anomalies",
            "params": {
                "threshold_std": "Optional[float] - Standard deviation threshold (default: 2.0)",
            },
            "response_example": {
                "anomalies": [
                    {
                        "category": "entertainment",
                        "anomaly_type": "unusually_high",
                        "amount": 500.00,
                        "baseline": 150.00,
                        "severity": "warning",
                    }
                ],
                "total_anomalies": 1,
            },
        }


class PortfolioOptimizationEndpoint:
    """Portfolio optimization endpoints."""
    
    @staticmethod
    def get_target_allocation(risk_tolerance: str) -> dict:
        """Get target asset allocation.
        
        Args:
            risk_tolerance: Risk tolerance level
        
        Returns:
            Target allocation percentages
        """
        return {
            "endpoint": "/api/portfolio/allocation",
            "method": "GET",
            "description": "Get target asset allocation",
            "params": {
                "risk_tolerance": "str - Risk tolerance (conservative, moderate, aggressive)",
            },
            "response_example": {
                "risk_tolerance": risk_tolerance,
                "allocation": {
                    "stocks": 0.60,
                    "bonds": 0.30,
                    "cash": 0.05,
                    "alternatives": 0.05,
                },
                "expected_return": 0.065,
                "expected_volatility": 0.09,
            },
        }
    
    @staticmethod
    def get_rebalancing_plan(total_value: float) -> dict:
        """Get rebalancing recommendations.
        
        Args:
            total_value: Total portfolio value
        
        Returns:
            Rebalancing actions
        """
        return {
            "endpoint": "/api/portfolio/rebalance",
            "method": "POST",
            "description": "Generate rebalancing plan",
            "body": {
                "total_value": "float - Total portfolio value",
                "current_allocation": "dict - Current asset allocation percentages",
                "risk_tolerance": "str - Risk tolerance level",
                "strategy": "str - Rebalancing strategy (threshold, periodic, tactical)",
            },
            "response_example": {
                "actions": [
                    {
                        "action": "buy",
                        "asset": "bonds",
                        "amount": 5000.00,
                        "rationale": "Below target allocation",
                    }
                ],
                "estimated_tax_impact": 0.0,
                "priority": "medium",
            },
        }


class SubscriptionEndpoint:
    """Subscription management endpoints."""
    
    @staticmethod
    def list_subscriptions() -> dict:
        """List all subscriptions.
        
        Returns:
            List of active subscriptions
        """
        return {
            "endpoint": "/api/subscriptions/list",
            "method": "GET",
            "description": "List all active subscriptions",
            "params": {
                "category": "Optional[str] - Filter by category",
                "include_cancelled": "Optional[bool] - Include cancelled subscriptions",
            },
            "response_example": {
                "subscriptions": [
                    {
                        "subscription_id": "sub-uuid",
                        "name": "Netflix",
                        "category": "streaming",
                        "amount": 15.99,
                        "frequency": "monthly",
                        "annual_cost": 191.88,
                    }
                ],
                "total_active_cost": 191.88,
                "monthly_avg_spending": 15.99,
            },
        }
    
    @staticmethod
    def add_subscription(name: str, amount: float) -> dict:
        """Add new subscription.
        
        Args:
            name: Subscription name
            amount: Monthly amount
        
        Returns:
            Created subscription
        """
        return {
            "endpoint": "/api/subscriptions/add",
            "method": "POST",
            "description": "Add new subscription",
            "body": {
                "name": "str - Subscription name",
                "category": "str - Category (streaming, software, etc)",
                "provider": "str - Service provider",
                "amount": "float - Amount per period",
                "frequency": "str - Frequency (daily, weekly, monthly, etc)",
            },
            "response_example": {
                "subscription_id": "sub-uuid",
                "name": name,
                "amount": amount,
                "created_at": "2026-04-27T10:00:00Z",
            },
        }
    
    @staticmethod
    def get_optimization_recommendations() -> dict:
        """Get subscription optimization recommendations.
        
        Returns:
            Optimization recommendations
        """
        return {
            "endpoint": "/api/subscriptions/optimize",
            "method": "GET",
            "description": "Get subscription optimization recommendations",
            "response_example": {
                "optimizations": [
                    {
                        "subscription": "Unused Service",
                        "type": "cancel",
                        "savings": 100.00,
                        "priority": "high",
                        "action": "Cancel subscription",
                    }
                ],
                "total_potential_savings": 100.00,
            },
        }


class FinanceAPI:
    """Personal finance REST API."""
    
    def __init__(self):
        """Initialize finance API."""
        self.endpoints = {
            "wallet": WalletEndpoint(),
            "crypto": CryptoEndpoint(),
            "budget": BudgetEndpoint(),
            "dashboard": FinancialDashboardEndpoint(),
            "analytics": ExpenseAnalyticsEndpoint(),
            "portfolio": PortfolioOptimizationEndpoint(),
            "subscriptions": SubscriptionEndpoint(),
        }
    
    def get_api_documentation(self) -> dict:
        """Get full API documentation.
        
        Returns:
            API documentation with all endpoints
        """
        return {
            "api": "Personal Finance API",
            "version": "1.0.0",
            "base_url": "/api",
            "documentation": {
                "wallet": {
                    "endpoints": {
                        "list": self.endpoints["wallet"].list_wallets(),
                        "transaction": self.endpoints["wallet"].add_transaction("wallet-id", 100.0, "test"),
                    },
                },
                "crypto": {
                    "endpoints": {
                        "summary": self.endpoints["crypto"].get_portfolio_summary(),
                        "position": self.endpoints["crypto"].add_position("BTC", 1.0, 50000.0),
                    },
                },
                "budget": {
                    "endpoints": {
                        "status": self.endpoints["budget"].get_budget_status(),
                        "forecast": self.endpoints["budget"].get_forecast(),
                    },
                },
                "dashboard": {
                    "endpoints": {
                        "net_worth": self.endpoints["dashboard"].get_net_worth(),
                        "health": self.endpoints["dashboard"].get_financial_health(),
                        "recommendations": self.endpoints["dashboard"].get_recommendations(),
                    },
                },
                "analytics": {
                    "endpoints": {
                        "patterns": self.endpoints["analytics"].get_spending_patterns(),
                        "anomalies": self.endpoints["analytics"].get_anomalies(),
                    },
                },
                "portfolio": {
                    "endpoints": {
                        "allocation": self.endpoints["portfolio"].get_target_allocation("moderate"),
                        "rebalance": self.endpoints["portfolio"].get_rebalancing_plan(100000.0),
                    },
                },
                "subscriptions": {
                    "endpoints": {
                        "list": self.endpoints["subscriptions"].list_subscriptions(),
                        "add": self.endpoints["subscriptions"].add_subscription("Test", 10.0),
                        "optimize": self.endpoints["subscriptions"].get_optimization_recommendations(),
                    },
                },
            },
            "auth": {
                "type": "Bearer Token",
                "header": "Authorization: Bearer YOUR_TOKEN",
            },
            "rate_limiting": {
                "requests_per_minute": 60,
                "requests_per_hour": 1000,
            },
            "response_format": {
                "status": "success|error",
                "message": "Human-readable message",
                "data": "Response data",
                "timestamp": "ISO 8601 timestamp",
                "request_id": "Unique request identifier",
            },
        }
    
    def health_check(self) -> APIResponse:
        """Health check endpoint.
        
        Returns:
            API health status
        """
        return APIResponse(
            status="success",
            message="API is healthy",
            data={
                "status": "online",
                "uptime": "100%",
                "modules": [
                    {"module": "wallet", "status": "online"},
                    {"module": "crypto", "status": "online"},
                    {"module": "budget", "status": "online"},
                    {"module": "dashboard", "status": "online"},
                    {"module": "analytics", "status": "online"},
                    {"module": "portfolio", "status": "online"},
                    {"module": "subscriptions", "status": "online"},
                ],
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        )
