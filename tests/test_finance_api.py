"""Tests for personal finance REST API."""

import pytest
from datetime import datetime, timezone
import json

from jarvis.tools.finance_api import (
    APIError, APIResponse, WalletEndpoint, CryptoEndpoint,
    BudgetEndpoint, FinancialDashboardEndpoint, ExpenseAnalyticsEndpoint,
    PortfolioOptimizationEndpoint, SubscriptionEndpoint, FinanceAPI
)


class TestAPIError:
    """Tests for API errors."""
    
    def test_api_error_creation(self):
        """Test creating API error."""
        error = APIError("Test error", 400)
        assert error.message == "Test error"
        assert error.status_code == 400
    
    def test_api_error_default_status(self):
        """Test default status code."""
        error = APIError("Test")
        assert error.status_code == 400


class TestAPIResponse:
    """Tests for API responses."""
    
    def test_response_creation_success(self):
        """Test creating success response."""
        response = APIResponse(
            status="success",
            message="Operation successful",
            data={"result": "test"},
        )
        assert response.status == "success"
        assert response.data == {"result": "test"}
    
    def test_response_auto_timestamp(self):
        """Test automatic timestamp assignment."""
        response = APIResponse(
            status="success",
            message="Test",
        )
        assert response.timestamp is not None
        assert isinstance(response.timestamp, datetime)
    
    def test_response_auto_request_id(self):
        """Test automatic request ID generation."""
        response = APIResponse(
            status="success",
            message="Test",
        )
        assert response.request_id is not None
        assert len(response.request_id) == 36  # UUID length
    
    def test_response_to_dict(self):
        """Test response serialization."""
        response = APIResponse(
            status="success",
            message="Test message",
            data={"key": "value"},
        )
        data = response.to_dict()
        
        assert data["status"] == "success"
        assert data["message"] == "Test message"
        assert data["data"] == {"key": "value"}
        assert "timestamp" in data
        assert "request_id" in data
    
    def test_response_without_data(self):
        """Test response without data field."""
        response = APIResponse(
            status="success",
            message="Done",
        )
        data = response.to_dict()
        
        assert "data" not in data or data["data"] is None


class TestWalletEndpoint:
    """Tests for wallet endpoints."""
    
    def test_list_wallets_structure(self):
        """Test list wallets endpoint structure."""
        result = WalletEndpoint.list_wallets()
        
        assert result["endpoint"] == "/api/wallet/list"
        assert result["method"] == "GET"
        assert "description" in result
        assert "params" in result
        assert "response_example" in result
    
    def test_add_transaction_structure(self):
        """Test add transaction endpoint structure."""
        result = WalletEndpoint.add_transaction("wallet-1", 100.0, "test")
        
        assert result["endpoint"] == "/api/wallet/transaction"
        assert result["method"] == "POST"
        assert "body" in result
        assert "response_example" in result


class TestCryptoEndpoint:
    """Tests for crypto endpoints."""
    
    def test_portfolio_summary_structure(self):
        """Test portfolio summary endpoint structure."""
        result = CryptoEndpoint.get_portfolio_summary()
        
        assert result["endpoint"] == "/api/crypto/summary"
        assert result["method"] == "GET"
        assert "description" in result
        assert "response_example" in result
    
    def test_add_position_structure(self):
        """Test add position endpoint structure."""
        result = CryptoEndpoint.add_position("BTC", 1.0, 50000.0)
        
        assert result["endpoint"] == "/api/crypto/position"
        assert result["method"] == "POST"
        assert "body" in result
        assert "response_example" in result


class TestBudgetEndpoint:
    """Tests for budget endpoints."""
    
    def test_budget_status_structure(self):
        """Test budget status endpoint structure."""
        result = BudgetEndpoint.get_budget_status()
        
        assert result["endpoint"] == "/api/budget/status"
        assert result["method"] == "GET"
        assert "params" in result
        assert "response_example" in result
    
    def test_forecast_structure(self):
        """Test forecast endpoint structure."""
        result = BudgetEndpoint.get_forecast(12)
        
        assert result["endpoint"] == "/api/budget/forecast"
        assert result["method"] == "GET"
        assert "params" in result
        assert "response_example" in result


class TestFinancialDashboardEndpoint:
    """Tests for financial dashboard endpoints."""
    
    def test_net_worth_structure(self):
        """Test net worth endpoint structure."""
        result = FinancialDashboardEndpoint.get_net_worth()
        
        assert result["endpoint"] == "/api/dashboard/net-worth"
        assert result["method"] == "GET"
        assert "response_example" in result
    
    def test_financial_health_structure(self):
        """Test financial health endpoint structure."""
        result = FinancialDashboardEndpoint.get_financial_health()
        
        assert result["endpoint"] == "/api/dashboard/health"
        assert result["method"] == "GET"
        assert "response_example" in result
    
    def test_recommendations_structure(self):
        """Test recommendations endpoint structure."""
        result = FinancialDashboardEndpoint.get_recommendations()
        
        assert result["endpoint"] == "/api/dashboard/recommendations"
        assert result["method"] == "GET"
        assert "response_example" in result


class TestExpenseAnalyticsEndpoint:
    """Tests for expense analytics endpoints."""
    
    def test_spending_patterns_structure(self):
        """Test spending patterns endpoint structure."""
        result = ExpenseAnalyticsEndpoint.get_spending_patterns()
        
        assert result["endpoint"] == "/api/analytics/patterns"
        assert result["method"] == "GET"
        assert "params" in result
        assert "response_example" in result
    
    def test_anomalies_structure(self):
        """Test anomalies endpoint structure."""
        result = ExpenseAnalyticsEndpoint.get_anomalies()
        
        assert result["endpoint"] == "/api/analytics/anomalies"
        assert result["method"] == "GET"
        assert "params" in result
        assert "response_example" in result


class TestPortfolioOptimizationEndpoint:
    """Tests for portfolio optimization endpoints."""
    
    def test_target_allocation_structure(self):
        """Test target allocation endpoint structure."""
        result = PortfolioOptimizationEndpoint.get_target_allocation("moderate")
        
        assert result["endpoint"] == "/api/portfolio/allocation"
        assert result["method"] == "GET"
        assert "params" in result
        assert "response_example" in result
    
    def test_rebalancing_plan_structure(self):
        """Test rebalancing plan endpoint structure."""
        result = PortfolioOptimizationEndpoint.get_rebalancing_plan(100000.0)
        
        assert result["endpoint"] == "/api/portfolio/rebalance"
        assert result["method"] == "POST"
        assert "body" in result
        assert "response_example" in result


class TestSubscriptionEndpoint:
    """Tests for subscription endpoints."""
    
    def test_list_subscriptions_structure(self):
        """Test list subscriptions endpoint structure."""
        result = SubscriptionEndpoint.list_subscriptions()
        
        assert result["endpoint"] == "/api/subscriptions/list"
        assert result["method"] == "GET"
        assert "params" in result
        assert "response_example" in result
    
    def test_add_subscription_structure(self):
        """Test add subscription endpoint structure."""
        result = SubscriptionEndpoint.add_subscription("Test", 10.0)
        
        assert result["endpoint"] == "/api/subscriptions/add"
        assert result["method"] == "POST"
        assert "body" in result
        assert "response_example" in result
    
    def test_optimization_recommendations_structure(self):
        """Test optimization recommendations endpoint structure."""
        result = SubscriptionEndpoint.get_optimization_recommendations()
        
        assert result["endpoint"] == "/api/subscriptions/optimize"
        assert result["method"] == "GET"
        assert "response_example" in result


class TestFinanceAPI:
    """Tests for finance API."""
    
    def test_api_creation(self):
        """Test creating API instance."""
        api = FinanceAPI()
        assert api.endpoints is not None
        assert "wallet" in api.endpoints
        assert "crypto" in api.endpoints
        assert "budget" in api.endpoints
    
    def test_all_modules_available(self):
        """Test all modules are available."""
        api = FinanceAPI()
        modules = ["wallet", "crypto", "budget", "dashboard", "analytics", "portfolio", "subscriptions"]
        
        for module in modules:
            assert module in api.endpoints
    
    def test_get_api_documentation(self):
        """Test getting API documentation."""
        api = FinanceAPI()
        docs = api.get_api_documentation()
        
        assert docs["api"] == "Personal Finance API"
        assert docs["version"] == "1.0.0"
        assert docs["base_url"] == "/api"
        assert "documentation" in docs
        assert "auth" in docs
        assert "rate_limiting" in docs
        assert "response_format" in docs
    
    def test_documentation_includes_all_modules(self):
        """Test documentation includes all modules."""
        api = FinanceAPI()
        docs = api.get_api_documentation()
        
        modules = ["wallet", "crypto", "budget", "dashboard", "analytics", "portfolio", "subscriptions"]
        for module in modules:
            assert module in docs["documentation"]
    
    def test_health_check_response(self):
        """Test health check response."""
        api = FinanceAPI()
        response = api.health_check()
        
        assert isinstance(response, APIResponse)
        assert response.status == "success"
        assert "data" in response.to_dict()
    
    def test_health_check_all_modules(self):
        """Test health check includes all modules."""
        api = FinanceAPI()
        response = api.health_check()
        data = response.to_dict()
        
        modules = ["wallet", "crypto", "budget", "dashboard", "analytics", "portfolio", "subscriptions"]
        module_names = [m["module"] for m in data["data"]["modules"]]
        
        for module in modules:
            assert module in module_names


class TestAPIIntegration:
    """Integration tests for API."""
    
    def test_full_api_workflow(self):
        """Test complete API workflow."""
        api = FinanceAPI()
        
        # Get documentation
        docs = api.get_api_documentation()
        assert docs is not None
        
        # Check health
        health = api.health_check()
        assert health.status == "success"
        
        # Access all module endpoints
        wallet_doc = docs["documentation"]["wallet"]["endpoints"]["list"]
        crypto_doc = docs["documentation"]["crypto"]["endpoints"]["summary"]
        budget_doc = docs["documentation"]["budget"]["endpoints"]["status"]
        dashboard_doc = docs["documentation"]["dashboard"]["endpoints"]["net_worth"]
        analytics_doc = docs["documentation"]["analytics"]["endpoints"]["patterns"]
        portfolio_doc = docs["documentation"]["portfolio"]["endpoints"]["allocation"]
        subscriptions_doc = docs["documentation"]["subscriptions"]["endpoints"]["list"]
        
        assert all([
            wallet_doc, crypto_doc, budget_doc, dashboard_doc,
            analytics_doc, portfolio_doc, subscriptions_doc
        ])
    
    def test_response_serialization(self):
        """Test API response can be serialized to JSON."""
        api = FinanceAPI()
        response = api.health_check()
        data = response.to_dict()
        
        # Should be serializable to JSON
        json_str = json.dumps(data, default=str)
        assert json_str is not None
        
        # Should deserialize back
        parsed = json.loads(json_str)
        assert parsed["status"] == "success"


class TestAPIEdgeCases:
    """Edge case tests for API."""
    
    def test_response_with_none_data(self):
        """Test response with None data."""
        response = APIResponse(status="success", message="Test")
        data = response.to_dict()
        
        # None data should not appear in response
        assert "data" not in data or data["data"] is None
    
    def test_response_with_complex_data(self):
        """Test response with complex nested data."""
        response = APIResponse(
            status="success",
            message="Test",
            data={
                "nested": {
                    "deeply": {
                        "complex": ["data", "structure"]
                    }
                }
            }
        )
        data = response.to_dict()
        
        assert data["data"]["nested"]["deeply"]["complex"] == ["data", "structure"]
    
    def test_api_documentation_completeness(self):
        """Test API documentation is complete."""
        api = FinanceAPI()
        docs = api.get_api_documentation()
        
        # Every module should have description
        for module, module_doc in docs["documentation"].items():
            assert "endpoints" in module_doc
            assert len(module_doc["endpoints"]) > 0
            
            # Every endpoint should have required fields
            for endpoint_name, endpoint_doc in module_doc["endpoints"].items():
                if isinstance(endpoint_doc, dict):
                    assert "endpoint" in endpoint_doc
                    assert "method" in endpoint_doc
                    assert "description" in endpoint_doc
