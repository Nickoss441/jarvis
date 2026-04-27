"""Financial alerts and notifications system.

Monitors financial metrics and sends alerts for budget overages,
goal achievements, risk conditions, and important milestones.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from enum import Enum
import uuid


class AlertType(str, Enum):
    """Types of financial alerts."""
    BUDGET_EXCEEDED = "budget_exceeded"
    GOAL_ACHIEVED = "goal_achieved"
    GOAL_OFF_TRACK = "goal_off_track"
    LOW_BALANCE = "low_balance"
    HIGH_SPENDING = "high_spending"
    SAVINGS_MILESTONE = "savings_milestone"
    DEBT_THRESHOLD = "debt_threshold"
    INVESTMENT_MILESTONE = "investment_milestone"
    INCOME_VARIANCE = "income_variance"
    BILL_DUE = "bill_due"


class AlertSeverity(str, Enum):
    """Severity levels of alerts."""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class AlertStatus(str, Enum):
    """Status of an alert."""
    ACTIVE = "active"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"
    DISMISSED = "dismissed"


class NotificationChannel(str, Enum):
    """Notification channels."""
    IN_APP = "in_app"
    EMAIL = "email"
    SMS = "sms"
    PUSH = "push"
    WEBHOOK = "webhook"


@dataclass
class AlertRule:
    """A rule for generating alerts.
    
    Attributes:
        rule_id: Unique rule ID
        name: Rule name
        alert_type: Type of alert
        condition: Condition that triggers alert
        threshold: Threshold value
        enabled: Whether rule is enabled
        notification_channels: Channels to send notification
    """
    rule_id: str
    name: str
    alert_type: AlertType
    condition: str
    threshold: float
    enabled: bool = True
    notification_channels: list[NotificationChannel] = field(default_factory=list)
    created_at: datetime = None
    
    def __post_init__(self):
        """Set defaults."""
        if self.created_at is None:
            self.created_at = datetime.now(timezone.utc)
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "id": self.rule_id,
            "name": self.name,
            "type": self.alert_type.value,
            "condition": self.condition,
            "threshold": self.threshold,
            "enabled": self.enabled,
            "channels": [c.value for c in self.notification_channels],
        }


@dataclass
class Alert:
    """A financial alert.
    
    Attributes:
        alert_id: Unique alert ID
        alert_type: Type of alert
        severity: Severity level
        status: Current status
        title: Alert title
        message: Alert message
        triggered_at: When alert was triggered
        triggered_by_rule: Rule ID that triggered alert
        value: Current value that triggered alert
        threshold: Threshold value
        affected_entity: Entity affected (e.g., budget ID, goal ID)
        acknowledged_at: When alert was acknowledged
        resolved_at: When alert was resolved
    """
    alert_id: str
    alert_type: AlertType
    severity: AlertSeverity
    title: str
    message: str
    triggered_at: datetime
    value: float
    threshold: float
    affected_entity: str = ""
    triggered_by_rule: str = ""
    status: AlertStatus = AlertStatus.ACTIVE
    acknowledged_at: datetime = None
    resolved_at: datetime = None
    
    def __post_init__(self):
        """Validate alert."""
        if not isinstance(self.triggered_at, datetime) or self.triggered_at.tzinfo is None:
            raise ValueError("triggered_at must be timezone-aware (UTC)")
    
    def acknowledge(self):
        """Acknowledge the alert."""
        self.status = AlertStatus.ACKNOWLEDGED
        self.acknowledged_at = datetime.now(timezone.utc)
    
    def resolve(self):
        """Resolve the alert."""
        self.status = AlertStatus.RESOLVED
        self.resolved_at = datetime.now(timezone.utc)
    
    def dismiss(self):
        """Dismiss the alert."""
        self.status = AlertStatus.DISMISSED
        self.acknowledged_at = datetime.now(timezone.utc)
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "id": self.alert_id,
            "type": self.alert_type.value,
            "severity": self.severity.value,
            "status": self.status.value,
            "title": self.title,
            "message": self.message,
            "triggered": self.triggered_at.isoformat(),
            "value": self.value,
            "threshold": self.threshold,
        }


@dataclass
class AlertHistory:
    """History of alerts.
    
    Attributes:
        history_id: Unique history ID
        alert_id: Alert ID
        action: Action taken
        timestamp: When action occurred
        details: Additional details
    """
    history_id: str
    alert_id: str
    action: str
    timestamp: datetime
    details: str = ""
    
    def __post_init__(self):
        """Validate history."""
        if not isinstance(self.timestamp, datetime) or self.timestamp.tzinfo is None:
            raise ValueError("timestamp must be timezone-aware (UTC)")


@dataclass
class AlertSummary:
    """Summary of alerts.
    
    Attributes:
        summary_id: Unique summary ID
        total_alerts: Total number of alerts
        active_alerts: Number of active alerts
        critical_alerts: Number of critical alerts
        acknowledged_alerts: Number of acknowledged alerts
        by_type: Count by alert type
        generated_at: When summary was generated
    """
    summary_id: str
    total_alerts: int
    active_alerts: int
    critical_alerts: int
    acknowledged_alerts: int
    by_type: dict[str, int]
    generated_at: datetime = None
    
    def __post_init__(self):
        """Set defaults."""
        if self.generated_at is None:
            self.generated_at = datetime.now(timezone.utc)
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "id": self.summary_id,
            "total": self.total_alerts,
            "active": self.active_alerts,
            "critical": self.critical_alerts,
            "acknowledged": self.acknowledged_alerts,
            "by_type": self.by_type,
            "generated": self.generated_at.isoformat(),
        }


class AlertManager:
    """Manages financial alerts and notifications."""
    
    def __init__(self):
        """Initialize alert manager."""
        self.rules: dict[str, AlertRule] = {}
        self.alerts: dict[str, Alert] = {}
        self.history: dict[str, AlertHistory] = {}
    
    def add_rule(
        self,
        name: str,
        alert_type: AlertType,
        condition: str,
        threshold: float,
        channels: list[NotificationChannel] = None,
    ) -> AlertRule:
        """Add an alert rule.
        
        Args:
            name: Rule name
            alert_type: Type of alert
            condition: Condition description
            threshold: Threshold value
            channels: Notification channels
        
        Returns:
            Created rule
        """
        rule_id = str(uuid.uuid4())
        if channels is None:
            channels = [NotificationChannel.IN_APP]
        
        rule = AlertRule(
            rule_id=rule_id,
            name=name,
            alert_type=alert_type,
            condition=condition,
            threshold=threshold,
            notification_channels=channels,
        )
        self.rules[rule_id] = rule
        return rule
    
    def disable_rule(self, rule_id: str):
        """Disable a rule.
        
        Args:
            rule_id: Rule ID
        """
        if rule_id not in self.rules:
            raise ValueError(f"Rule {rule_id} not found")
        self.rules[rule_id].enabled = False
    
    def enable_rule(self, rule_id: str):
        """Enable a rule.
        
        Args:
            rule_id: Rule ID
        """
        if rule_id not in self.rules:
            raise ValueError(f"Rule {rule_id} not found")
        self.rules[rule_id].enabled = True
    
    def create_alert(
        self,
        alert_type: AlertType,
        severity: AlertSeverity,
        title: str,
        message: str,
        value: float,
        threshold: float,
        affected_entity: str = "",
        triggered_by_rule: str = "",
    ) -> Alert:
        """Create an alert.
        
        Args:
            alert_type: Type of alert
            severity: Severity level
            title: Alert title
            message: Alert message
            value: Current value
            threshold: Threshold value
            affected_entity: Entity ID
            triggered_by_rule: Rule ID that triggered alert
        
        Returns:
            Created alert
        """
        alert_id = str(uuid.uuid4())
        alert = Alert(
            alert_id=alert_id,
            alert_type=alert_type,
            severity=severity,
            title=title,
            message=message,
            triggered_at=datetime.now(timezone.utc),
            value=value,
            threshold=threshold,
            affected_entity=affected_entity,
            triggered_by_rule=triggered_by_rule,
        )
        self.alerts[alert_id] = alert
        
        # Record history
        self._record_history(alert_id, "created", f"Alert created with severity {severity.value}")
        
        return alert
    
    def _record_history(self, alert_id: str, action: str, details: str = ""):
        """Record alert history.
        
        Args:
            alert_id: Alert ID
            action: Action taken
            details: Action details
        """
        history_id = str(uuid.uuid4())
        history = AlertHistory(
            history_id=history_id,
            alert_id=alert_id,
            action=action,
            timestamp=datetime.now(timezone.utc),
            details=details,
        )
        self.history[history_id] = history
    
    def acknowledge_alert(self, alert_id: str):
        """Acknowledge an alert.
        
        Args:
            alert_id: Alert ID
        """
        if alert_id not in self.alerts:
            raise ValueError(f"Alert {alert_id} not found")
        
        alert = self.alerts[alert_id]
        alert.acknowledge()
        self._record_history(alert_id, "acknowledged", "User acknowledged alert")
    
    def resolve_alert(self, alert_id: str):
        """Resolve an alert.
        
        Args:
            alert_id: Alert ID
        """
        if alert_id not in self.alerts:
            raise ValueError(f"Alert {alert_id} not found")
        
        alert = self.alerts[alert_id]
        alert.resolve()
        self._record_history(alert_id, "resolved", "Alert condition resolved")
    
    def dismiss_alert(self, alert_id: str):
        """Dismiss an alert.
        
        Args:
            alert_id: Alert ID
        """
        if alert_id not in self.alerts:
            raise ValueError(f"Alert {alert_id} not found")
        
        alert = self.alerts[alert_id]
        alert.dismiss()
        self._record_history(alert_id, "dismissed", "User dismissed alert")
    
    def get_active_alerts(self) -> list[Alert]:
        """Get all active alerts.
        
        Returns:
            List of active alerts
        """
        return [a for a in self.alerts.values() if a.status == AlertStatus.ACTIVE]
    
    def get_critical_alerts(self) -> list[Alert]:
        """Get all critical alerts.
        
        Returns:
            List of critical alerts
        """
        return [a for a in self.alerts.values() if a.severity == AlertSeverity.CRITICAL]
    
    def get_alerts_by_type(self, alert_type: AlertType) -> list[Alert]:
        """Get alerts by type.
        
        Args:
            alert_type: Alert type
        
        Returns:
            List of alerts of that type
        """
        return [a for a in self.alerts.values() if a.alert_type == alert_type]
    
    def get_alerts_for_entity(self, entity_id: str) -> list[Alert]:
        """Get alerts for a specific entity.
        
        Args:
            entity_id: Entity ID
        
        Returns:
            List of alerts for entity
        """
        return [a for a in self.alerts.values() if a.affected_entity == entity_id]
    
    def get_alert_history(self, alert_id: str) -> list[AlertHistory]:
        """Get history for an alert.
        
        Args:
            alert_id: Alert ID
        
        Returns:
            List of history entries
        """
        return [h for h in self.history.values() if h.alert_id == alert_id]
    
    def generate_summary(self) -> AlertSummary:
        """Generate alert summary.
        
        Returns:
            Alert summary
        """
        all_alerts = list(self.alerts.values())
        active = [a for a in all_alerts if a.status == AlertStatus.ACTIVE]
        critical = [a for a in all_alerts if a.severity == AlertSeverity.CRITICAL]
        acknowledged = [a for a in all_alerts if a.status == AlertStatus.ACKNOWLEDGED]
        
        # Count by type
        by_type = {}
        for alert in all_alerts:
            type_val = alert.alert_type.value
            by_type[type_val] = by_type.get(type_val, 0) + 1
        
        return AlertSummary(
            summary_id=str(uuid.uuid4()),
            total_alerts=len(all_alerts),
            active_alerts=len(active),
            critical_alerts=len(critical),
            acknowledged_alerts=len(acknowledged),
            by_type=by_type,
        )
    
    def check_budget_exceeded(
        self,
        budget_id: str,
        budget_limit: float,
        current_spending: float,
    ) -> Alert:
        """Check if budget is exceeded.
        
        Args:
            budget_id: Budget ID
            budget_limit: Budget limit
            current_spending: Current spending
        
        Returns:
            Alert if exceeded, None otherwise
        """
        if current_spending > budget_limit:
            percentage = (current_spending / budget_limit) * 100
            
            # Determine severity
            if percentage > 150:
                severity = AlertSeverity.CRITICAL
            elif percentage > 125:
                severity = AlertSeverity.WARNING
            else:
                severity = AlertSeverity.WARNING
            
            return self.create_alert(
                alert_type=AlertType.BUDGET_EXCEEDED,
                severity=severity,
                title=f"Budget Exceeded: {percentage:.0f}%",
                message=f"Spending ${current_spending:.2f} exceeds budget of ${budget_limit:.2f}",
                value=current_spending,
                threshold=budget_limit,
                affected_entity=budget_id,
            )
        return None
    
    def check_low_balance(
        self,
        balance: float,
        minimum_threshold: float,
    ) -> Alert:
        """Check if balance is low.
        
        Args:
            balance: Current balance
            minimum_threshold: Minimum threshold
        
        Returns:
            Alert if low, None otherwise
        """
        if balance < minimum_threshold:
            # Determine severity based on how low
            if balance < minimum_threshold * 0.25:
                severity = AlertSeverity.CRITICAL
            else:
                severity = AlertSeverity.WARNING
            
            return self.create_alert(
                alert_type=AlertType.LOW_BALANCE,
                severity=severity,
                title="Low Balance Alert",
                message=f"Balance ${balance:.2f} is below recommended minimum of ${minimum_threshold:.2f}",
                value=balance,
                threshold=minimum_threshold,
            )
        return None
