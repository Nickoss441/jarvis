"""Tests for financial alerts and notifications system."""

import pytest
from datetime import datetime, timezone, timedelta

from jarvis.tools.alert_manager import (
    AlertType, AlertSeverity, AlertStatus, NotificationChannel,
    AlertRule, Alert, AlertHistory, AlertSummary,
    AlertManager
)


class TestAlertType:
    """Tests for alert types."""
    
    def test_all_types(self):
        """Verify all alert types are defined."""
        types = [t.value for t in AlertType]
        assert "budget_exceeded" in types
        assert "goal_achieved" in types
        assert "low_balance" in types


class TestAlertSeverity:
    """Tests for alert severity."""
    
    def test_all_severities(self):
        """Verify all severities are defined."""
        severities = [s.value for s in AlertSeverity]
        assert "info" in severities
        assert "warning" in severities
        assert "critical" in severities


class TestAlertStatus:
    """Tests for alert status."""
    
    def test_all_statuses(self):
        """Verify all statuses are defined."""
        statuses = [s.value for s in AlertStatus]
        assert "active" in statuses
        assert "acknowledged" in statuses
        assert "resolved" in statuses


class TestNotificationChannel:
    """Tests for notification channels."""
    
    def test_all_channels(self):
        """Verify all channels are defined."""
        channels = [c.value for c in NotificationChannel]
        assert "in_app" in channels
        assert "email" in channels
        assert "sms" in channels


class TestAlertRule:
    """Tests for alert rules."""
    
    def test_rule_creation(self):
        """Test creating an alert rule."""
        rule = AlertRule(
            rule_id="r-1",
            name="Budget Alert",
            alert_type=AlertType.BUDGET_EXCEEDED,
            condition="spending > budget",
            threshold=1000.0,
            notification_channels=[NotificationChannel.EMAIL],
        )
        assert rule.name == "Budget Alert"
        assert rule.enabled
    
    def test_rule_to_dict(self):
        """Test rule serialization."""
        rule = AlertRule(
            rule_id="r-1",
            name="Test Rule",
            alert_type=AlertType.BUDGET_EXCEEDED,
            condition="test",
            threshold=500.0,
        )
        data = rule.to_dict()
        
        assert data["name"] == "Test Rule"
        assert data["threshold"] == 500.0


class TestAlert:
    """Tests for alerts."""
    
    def test_alert_creation(self):
        """Test creating an alert."""
        now = datetime.now(timezone.utc)
        alert = Alert(
            alert_id="a-1",
            alert_type=AlertType.BUDGET_EXCEEDED,
            severity=AlertSeverity.WARNING,
            title="Budget Exceeded",
            message="You exceeded your budget",
            triggered_at=now,
            value=1500.0,
            threshold=1000.0,
        )
        assert alert.status == AlertStatus.ACTIVE
        assert alert.severity == AlertSeverity.WARNING
    
    def test_alert_naive_datetime_raises(self):
        """Test that naive datetime raises error."""
        naive = datetime(2026, 5, 27, 10, 0, 0)
        with pytest.raises(ValueError, match="timezone-aware"):
            Alert(
                alert_id="a-1",
                alert_type=AlertType.BUDGET_EXCEEDED,
                severity=AlertSeverity.WARNING,
                title="Test",
                message="Test",
                triggered_at=naive,
                value=100.0,
                threshold=50.0,
            )
    
    def test_alert_acknowledge(self):
        """Test acknowledging an alert."""
        now = datetime.now(timezone.utc)
        alert = Alert(
            alert_id="a-1",
            alert_type=AlertType.BUDGET_EXCEEDED,
            severity=AlertSeverity.WARNING,
            title="Test",
            message="Test",
            triggered_at=now,
            value=100.0,
            threshold=50.0,
        )
        
        alert.acknowledge()
        
        assert alert.status == AlertStatus.ACKNOWLEDGED
        assert alert.acknowledged_at is not None
    
    def test_alert_resolve(self):
        """Test resolving an alert."""
        now = datetime.now(timezone.utc)
        alert = Alert(
            alert_id="a-1",
            alert_type=AlertType.BUDGET_EXCEEDED,
            severity=AlertSeverity.WARNING,
            title="Test",
            message="Test",
            triggered_at=now,
            value=100.0,
            threshold=50.0,
        )
        
        alert.resolve()
        
        assert alert.status == AlertStatus.RESOLVED
        assert alert.resolved_at is not None
    
    def test_alert_dismiss(self):
        """Test dismissing an alert."""
        now = datetime.now(timezone.utc)
        alert = Alert(
            alert_id="a-1",
            alert_type=AlertType.BUDGET_EXCEEDED,
            severity=AlertSeverity.WARNING,
            title="Test",
            message="Test",
            triggered_at=now,
            value=100.0,
            threshold=50.0,
        )
        
        alert.dismiss()
        
        assert alert.status == AlertStatus.DISMISSED


class TestAlertHistory:
    """Tests for alert history."""
    
    def test_history_creation(self):
        """Test creating alert history."""
        now = datetime.now(timezone.utc)
        history = AlertHistory(
            history_id="h-1",
            alert_id="a-1",
            action="created",
            timestamp=now,
            details="Alert created",
        )
        assert history.action == "created"
    
    def test_history_naive_datetime_raises(self):
        """Test that naive datetime raises error."""
        naive = datetime(2026, 5, 27, 10, 0, 0)
        with pytest.raises(ValueError, match="timezone-aware"):
            AlertHistory(
                history_id="h-1",
                alert_id="a-1",
                action="test",
                timestamp=naive,
            )


class TestAlertSummary:
    """Tests for alert summary."""
    
    def test_summary_creation(self):
        """Test creating alert summary."""
        summary = AlertSummary(
            summary_id="s-1",
            total_alerts=5,
            active_alerts=2,
            critical_alerts=1,
            acknowledged_alerts=1,
            by_type={"budget_exceeded": 3, "low_balance": 2},
        )
        assert summary.total_alerts == 5
        assert summary.active_alerts == 2


class TestAlertManager:
    """Tests for alert manager."""
    
    def test_manager_creation(self):
        """Test creating alert manager."""
        manager = AlertManager()
        assert len(manager.rules) == 0
        assert len(manager.alerts) == 0
    
    def test_add_rule(self):
        """Test adding an alert rule."""
        manager = AlertManager()
        
        rule = manager.add_rule(
            name="Budget Alert",
            alert_type=AlertType.BUDGET_EXCEEDED,
            condition="spending > budget",
            threshold=1000.0,
            channels=[NotificationChannel.EMAIL],
        )
        
        assert len(manager.rules) == 1
        assert rule.name == "Budget Alert"
    
    def test_disable_rule(self):
        """Test disabling a rule."""
        manager = AlertManager()
        rule = manager.add_rule(
            name="Test",
            alert_type=AlertType.BUDGET_EXCEEDED,
            condition="test",
            threshold=100.0,
        )
        
        manager.disable_rule(rule.rule_id)
        
        assert not manager.rules[rule.rule_id].enabled
    
    def test_enable_rule(self):
        """Test enabling a rule."""
        manager = AlertManager()
        rule = manager.add_rule(
            name="Test",
            alert_type=AlertType.BUDGET_EXCEEDED,
            condition="test",
            threshold=100.0,
        )
        
        manager.disable_rule(rule.rule_id)
        manager.enable_rule(rule.rule_id)
        
        assert manager.rules[rule.rule_id].enabled
    
    def test_create_alert(self):
        """Test creating an alert."""
        manager = AlertManager()
        now = datetime.now(timezone.utc)
        
        alert = manager.create_alert(
            alert_type=AlertType.BUDGET_EXCEEDED,
            severity=AlertSeverity.WARNING,
            title="Budget Alert",
            message="Budget exceeded",
            value=1500.0,
            threshold=1000.0,
        )
        
        assert len(manager.alerts) == 1
        assert alert.status == AlertStatus.ACTIVE
    
    def test_acknowledge_alert(self):
        """Test acknowledging an alert."""
        manager = AlertManager()
        
        alert = manager.create_alert(
            alert_type=AlertType.BUDGET_EXCEEDED,
            severity=AlertSeverity.WARNING,
            title="Test",
            message="Test",
            value=100.0,
            threshold=50.0,
        )
        
        manager.acknowledge_alert(alert.alert_id)
        
        assert manager.alerts[alert.alert_id].status == AlertStatus.ACKNOWLEDGED
    
    def test_resolve_alert(self):
        """Test resolving an alert."""
        manager = AlertManager()
        
        alert = manager.create_alert(
            alert_type=AlertType.BUDGET_EXCEEDED,
            severity=AlertSeverity.WARNING,
            title="Test",
            message="Test",
            value=100.0,
            threshold=50.0,
        )
        
        manager.resolve_alert(alert.alert_id)
        
        assert manager.alerts[alert.alert_id].status == AlertStatus.RESOLVED
    
    def test_dismiss_alert(self):
        """Test dismissing an alert."""
        manager = AlertManager()
        
        alert = manager.create_alert(
            alert_type=AlertType.BUDGET_EXCEEDED,
            severity=AlertSeverity.WARNING,
            title="Test",
            message="Test",
            value=100.0,
            threshold=50.0,
        )
        
        manager.dismiss_alert(alert.alert_id)
        
        assert manager.alerts[alert.alert_id].status == AlertStatus.DISMISSED
    
    def test_get_active_alerts(self):
        """Test getting active alerts."""
        manager = AlertManager()
        
        alert1 = manager.create_alert(
            alert_type=AlertType.BUDGET_EXCEEDED,
            severity=AlertSeverity.WARNING,
            title="Alert 1",
            message="Test",
            value=100.0,
            threshold=50.0,
        )
        
        alert2 = manager.create_alert(
            alert_type=AlertType.LOW_BALANCE,
            severity=AlertSeverity.CRITICAL,
            title="Alert 2",
            message="Test",
            value=100.0,
            threshold=500.0,
        )
        
        manager.acknowledge_alert(alert1.alert_id)
        
        active = manager.get_active_alerts()
        
        assert len(active) == 1
        assert active[0].alert_id == alert2.alert_id
    
    def test_get_critical_alerts(self):
        """Test getting critical alerts."""
        manager = AlertManager()
        
        manager.create_alert(
            alert_type=AlertType.BUDGET_EXCEEDED,
            severity=AlertSeverity.WARNING,
            title="Warning",
            message="Test",
            value=100.0,
            threshold=50.0,
        )
        
        manager.create_alert(
            alert_type=AlertType.LOW_BALANCE,
            severity=AlertSeverity.CRITICAL,
            title="Critical",
            message="Test",
            value=100.0,
            threshold=500.0,
        )
        
        critical = manager.get_critical_alerts()
        
        assert len(critical) == 1
        assert critical[0].severity == AlertSeverity.CRITICAL
    
    def test_get_alerts_by_type(self):
        """Test getting alerts by type."""
        manager = AlertManager()
        
        manager.create_alert(
            alert_type=AlertType.BUDGET_EXCEEDED,
            severity=AlertSeverity.WARNING,
            title="Budget",
            message="Test",
            value=100.0,
            threshold=50.0,
        )
        
        manager.create_alert(
            alert_type=AlertType.LOW_BALANCE,
            severity=AlertSeverity.WARNING,
            title="Balance",
            message="Test",
            value=100.0,
            threshold=500.0,
        )
        
        budget_alerts = manager.get_alerts_by_type(AlertType.BUDGET_EXCEEDED)
        
        assert len(budget_alerts) == 1
    
    def test_get_alerts_for_entity(self):
        """Test getting alerts for specific entity."""
        manager = AlertManager()
        
        manager.create_alert(
            alert_type=AlertType.BUDGET_EXCEEDED,
            severity=AlertSeverity.WARNING,
            title="Alert 1",
            message="Test",
            value=100.0,
            threshold=50.0,
            affected_entity="budget-1",
        )
        
        manager.create_alert(
            alert_type=AlertType.BUDGET_EXCEEDED,
            severity=AlertSeverity.WARNING,
            title="Alert 2",
            message="Test",
            value=100.0,
            threshold=50.0,
            affected_entity="budget-2",
        )
        
        alerts = manager.get_alerts_for_entity("budget-1")
        
        assert len(alerts) == 1
    
    def test_get_alert_history(self):
        """Test getting alert history."""
        manager = AlertManager()
        
        alert = manager.create_alert(
            alert_type=AlertType.BUDGET_EXCEEDED,
            severity=AlertSeverity.WARNING,
            title="Test",
            message="Test",
            value=100.0,
            threshold=50.0,
        )
        
        manager.acknowledge_alert(alert.alert_id)
        
        history = manager.get_alert_history(alert.alert_id)
        
        assert len(history) >= 2  # Created + acknowledged
    
    def test_generate_summary(self):
        """Test generating alert summary."""
        manager = AlertManager()
        
        manager.create_alert(
            alert_type=AlertType.BUDGET_EXCEEDED,
            severity=AlertSeverity.WARNING,
            title="Alert 1",
            message="Test",
            value=100.0,
            threshold=50.0,
        )
        
        manager.create_alert(
            alert_type=AlertType.LOW_BALANCE,
            severity=AlertSeverity.CRITICAL,
            title="Alert 2",
            message="Test",
            value=100.0,
            threshold=500.0,
        )
        
        summary = manager.generate_summary()
        
        assert summary.total_alerts == 2
        assert summary.critical_alerts == 1
        assert summary.active_alerts == 2
    
    def test_check_budget_exceeded(self):
        """Test budget exceeded check."""
        manager = AlertManager()
        
        alert = manager.check_budget_exceeded(
            budget_id="b-1",
            budget_limit=1000.0,
            current_spending=1500.0,
        )
        
        assert alert is not None
        assert alert.alert_type == AlertType.BUDGET_EXCEEDED
    
    def test_check_budget_not_exceeded(self):
        """Test budget not exceeded."""
        manager = AlertManager()
        
        alert = manager.check_budget_exceeded(
            budget_id="b-1",
            budget_limit=1000.0,
            current_spending=800.0,
        )
        
        assert alert is None
    
    def test_check_low_balance(self):
        """Test low balance check."""
        manager = AlertManager()
        
        alert = manager.check_low_balance(
            balance=100.0,
            minimum_threshold=500.0,
        )
        
        assert alert is not None
        assert alert.alert_type == AlertType.LOW_BALANCE
    
    def test_check_balance_sufficient(self):
        """Test balance check with sufficient balance."""
        manager = AlertManager()
        
        alert = manager.check_low_balance(
            balance=1000.0,
            minimum_threshold=500.0,
        )
        
        assert alert is None


class TestAlertManagerEdgeCases:
    """Edge case tests for alert manager."""
    
    def test_multiple_rules_same_type(self):
        """Test multiple rules of same type."""
        manager = AlertManager()
        
        rule1 = manager.add_rule(
            name="Rule 1",
            alert_type=AlertType.BUDGET_EXCEEDED,
            condition="cond1",
            threshold=100.0,
        )
        
        rule2 = manager.add_rule(
            name="Rule 2",
            alert_type=AlertType.BUDGET_EXCEEDED,
            condition="cond2",
            threshold=200.0,
        )
        
        assert len(manager.rules) == 2
    
    def test_alert_workflow(self):
        """Test full alert workflow."""
        manager = AlertManager()
        
        alert = manager.create_alert(
            alert_type=AlertType.BUDGET_EXCEEDED,
            severity=AlertSeverity.WARNING,
            title="Test",
            message="Test",
            value=100.0,
            threshold=50.0,
        )
        
        manager.acknowledge_alert(alert.alert_id)
        manager.resolve_alert(alert.alert_id)
        
        assert manager.alerts[alert.alert_id].status == AlertStatus.RESOLVED
