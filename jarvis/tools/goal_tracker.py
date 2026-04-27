"""Financial goal tracker and milestone monitor.

Tracks financial goals, monitors progress, identifies milestones,
and provides actionable insights on goal achievement.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from enum import Enum
from typing import Optional
import uuid


class GoalCategory(str, Enum):
    """Categories of financial goals."""
    SAVING = "saving"           # Save a specific amount
    DEBT_PAYOFF = "debt_payoff" # Pay off debt
    INVESTMENT = "investment"   # Reach investment target
    INCOME = "income"           # Increase income
    EXPENSE = "expense"         # Reduce expenses
    PURCHASE = "purchase"       # Save for purchase
    RETIREMENT = "retirement"   # Retirement savings
    EDUCATION = "education"     # Education savings
    HOME = "home"               # Home purchase/equity
    WEALTH = "wealth"           # Net worth target


class GoalStatus(str, Enum):
    """Status of financial goal."""
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    PAUSED = "paused"
    COMPLETED = "completed"
    ABANDONED = "abandoned"


class TimeHorizon(str, Enum):
    """Time horizons for goals."""
    SHORT_TERM = "short_term"      # 1 year or less
    MEDIUM_TERM = "medium_term"    # 1-5 years
    LONG_TERM = "long_term"        # 5+ years


@dataclass
class MilestoneTarget:
    """Target milestone for a goal.
    
    Attributes:
        milestone_id: Unique milestone ID
        label: Milestone label (e.g., "50%", "Checkpoint 1")
        target_value: Target value for this milestone
        target_date: Target date to achieve milestone
        description: Milestone description
    """
    milestone_id: str
    label: str
    target_value: float
    target_date: datetime
    description: str = ""
    
    def __post_init__(self):
        """Validate milestone."""
        if not isinstance(self.target_date, datetime) or self.target_date.tzinfo is None:
            raise ValueError("target_date must be timezone-aware (UTC)")
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "id": self.milestone_id,
            "label": self.label,
            "target": self.target_value,
            "date": self.target_date.isoformat(),
            "description": self.description,
        }


@dataclass
class ProgressSnapshot:
    """Progress snapshot at a point in time.
    
    Attributes:
        snapshot_id: Unique snapshot ID
        current_value: Current progress value
        recorded_at: When snapshot was recorded
        note: Optional note about progress
    """
    snapshot_id: str
    current_value: float
    recorded_at: datetime
    note: str = ""
    
    def __post_init__(self):
        """Validate snapshot."""
        if not isinstance(self.recorded_at, datetime) or self.recorded_at.tzinfo is None:
            raise ValueError("recorded_at must be timezone-aware (UTC)")
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "value": self.current_value,
            "date": self.recorded_at.isoformat(),
            "note": self.note,
        }


@dataclass
class FinancialGoal:
    """A financial goal with progress tracking.
    
    Attributes:
        goal_id: Unique goal ID
        title: Goal title
        category: Goal category
        description: Goal description
        target_amount: Target value to achieve
        current_amount: Current progress toward target
        start_date: When goal was created
        target_date: Target completion date
        time_horizon: Short/medium/long term
        priority: Priority level (1-10, higher = more important)
        status: Current goal status
        milestones: List of milestone targets
        progress_history: History of progress snapshots
        created_at: When goal was created
    """
    goal_id: str
    title: str
    category: GoalCategory
    description: str
    target_amount: float
    current_amount: float
    start_date: datetime
    target_date: datetime
    time_horizon: TimeHorizon
    priority: int
    status: GoalStatus = GoalStatus.NOT_STARTED
    milestones: list[MilestoneTarget] = field(default_factory=list)
    progress_history: list[ProgressSnapshot] = field(default_factory=list)
    created_at: datetime = None
    
    def __post_init__(self):
        """Validate goal."""
        if self.target_amount <= 0:
            raise ValueError("Target amount must be positive")
        if self.current_amount < 0:
            raise ValueError("Current amount cannot be negative")
        if not isinstance(self.start_date, datetime) or self.start_date.tzinfo is None:
            raise ValueError("start_date must be timezone-aware (UTC)")
        if not isinstance(self.target_date, datetime) or self.target_date.tzinfo is None:
            raise ValueError("target_date must be timezone-aware (UTC)")
        if self.priority < 1 or self.priority > 10:
            raise ValueError("Priority must be between 1 and 10")
        if self.created_at is None:
            self.created_at = datetime.now(timezone.utc)
    
    @property
    def progress_percentage(self) -> float:
        """Calculate progress as percentage."""
        if self.target_amount == 0:
            return 0
        return min(100, (self.current_amount / self.target_amount) * 100)
    
    @property
    def amount_remaining(self) -> float:
        """Calculate amount remaining to goal."""
        return max(0, self.target_amount - self.current_amount)
    
    @property
    def days_remaining(self) -> int:
        """Calculate days remaining to target date."""
        now = datetime.now(timezone.utc)
        return max(0, (self.target_date - now).days)
    
    @property
    def days_elapsed(self) -> int:
        """Calculate days since goal creation."""
        now = datetime.now(timezone.utc)
        return (now - self.start_date).days
    
    @property
    def monthly_progress_needed(self) -> float:
        """Calculate monthly progress needed to reach goal on time."""
        if self.days_remaining <= 0:
            return 0
        months_left = self.days_remaining / 30.44
        if months_left <= 0:
            return 0
        return self.amount_remaining / months_left
    
    @property
    def current_rate(self) -> float:
        """Calculate current monthly progress rate."""
        if self.days_elapsed <= 0:
            return 0
        months_elapsed = self.days_elapsed / 30.44
        if months_elapsed == 0:
            return 0
        return self.current_amount / months_elapsed
    
    @property
    def on_track(self) -> bool:
        """Whether goal is on track to be completed on time."""
        if self.progress_percentage >= 100:
            return True
        if self.days_remaining <= 0:
            return False
        # On track if current rate >= required rate
        return self.current_rate >= self.monthly_progress_needed
    
    def record_progress(self, current_amount: float, note: str = "") -> ProgressSnapshot:
        """Record progress update.
        
        Args:
            current_amount: Current amount toward goal
            note: Optional note about progress
        
        Returns:
            Created progress snapshot
        """
        snapshot = ProgressSnapshot(
            snapshot_id=str(uuid.uuid4()),
            current_value=current_amount,
            recorded_at=datetime.now(timezone.utc),
            note=note,
        )
        self.progress_history.append(snapshot)
        self.current_amount = current_amount
        return snapshot
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "id": self.goal_id,
            "title": self.title,
            "category": self.category.value,
            "description": self.description,
            "target": self.target_amount,
            "current": self.current_amount,
            "remaining": self.amount_remaining,
            "progress_pct": self.progress_percentage,
            "status": self.status.value,
            "target_date": self.target_date.isoformat(),
            "on_track": self.on_track,
            "milestones": [m.to_dict() for m in self.milestones],
        }


@dataclass
class GoalProgressReport:
    """Report on goal progress.
    
    Attributes:
        report_id: Unique report ID
        goals: List of all goals
        on_track_count: Number of goals on track
        off_track_count: Number of goals off track
        completed_count: Number of completed goals
        total_progress: Average progress across goals
        next_milestone: Upcoming milestone
        recommendations: Actionable recommendations
        generated_at: When report was generated
    """
    report_id: str
    goals: list[FinancialGoal]
    on_track_count: int
    off_track_count: int
    completed_count: int
    total_progress: float
    next_milestone: Optional[MilestoneTarget]
    recommendations: list[str]
    generated_at: datetime = None
    
    def __post_init__(self):
        """Set defaults."""
        if self.generated_at is None:
            self.generated_at = datetime.now(timezone.utc)
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "id": self.report_id,
            "goals_count": len(self.goals),
            "on_track": self.on_track_count,
            "off_track": self.off_track_count,
            "completed": self.completed_count,
            "avg_progress": self.total_progress,
            "next_milestone": self.next_milestone.to_dict() if self.next_milestone else None,
            "recommendations": self.recommendations,
            "generated": self.generated_at.isoformat(),
        }


class GoalTracker:
    """Financial goal tracker and monitor."""
    
    def __init__(self):
        """Initialize goal tracker."""
        self.goals: dict[str, FinancialGoal] = {}
    
    def add_goal(
        self,
        title: str,
        category: GoalCategory,
        description: str,
        target_amount: float,
        target_date: datetime,
        time_horizon: TimeHorizon,
        priority: int = 5,
    ) -> FinancialGoal:
        """Add a new financial goal.
        
        Args:
            title: Goal title
            category: Goal category
            description: Goal description
            target_amount: Target value to achieve
            target_date: Target completion date
            time_horizon: Short/medium/long term
            priority: Priority level (1-10)
        
        Returns:
            Created goal
        """
        goal_id = str(uuid.uuid4())
        goal = FinancialGoal(
            goal_id=goal_id,
            title=title,
            category=category,
            description=description,
            target_amount=target_amount,
            current_amount=0.0,
            start_date=datetime.now(timezone.utc),
            target_date=target_date,
            time_horizon=time_horizon,
            priority=priority,
        )
        self.goals[goal_id] = goal
        return goal
    
    def record_progress(self, goal_id: str, current_amount: float, note: str = ""):
        """Record progress on a goal.
        
        Args:
            goal_id: Goal ID
            current_amount: Current amount toward goal
            note: Optional note about progress
        """
        if goal_id not in self.goals:
            raise ValueError(f"Goal {goal_id} not found")
        
        goal = self.goals[goal_id]
        goal.record_progress(current_amount, note)
        
        # Update status based on progress
        if current_amount >= goal.target_amount:
            goal.status = GoalStatus.COMPLETED
        elif goal.status == GoalStatus.NOT_STARTED:
            goal.status = GoalStatus.IN_PROGRESS
    
    def get_goals_by_category(self, category: GoalCategory) -> list[FinancialGoal]:
        """Get all goals in a category.
        
        Args:
            category: Goal category
        
        Returns:
            List of goals in category
        """
        return [g for g in self.goals.values() if g.category == category]
    
    def get_on_track_goals(self) -> list[FinancialGoal]:
        """Get all on-track goals.
        
        Returns:
            List of on-track goals
        """
        return [g for g in self.goals.values() if g.on_track and g.status == GoalStatus.IN_PROGRESS]
    
    def get_off_track_goals(self) -> list[FinancialGoal]:
        """Get all off-track goals.
        
        Returns:
            List of off-track goals
        """
        return [g for g in self.goals.values() if not g.on_track and g.status == GoalStatus.IN_PROGRESS]
    
    def get_next_milestone(self) -> Optional[MilestoneTarget]:
        """Get next upcoming milestone across all goals.
        
        Returns:
            Next milestone or None
        """
        now = datetime.now(timezone.utc)
        upcoming = []
        
        for goal in self.goals.values():
            if goal.status != GoalStatus.COMPLETED:
                for milestone in goal.milestones:
                    if milestone.target_date > now:
                        upcoming.append(milestone)
        
        if not upcoming:
            return None
        
        # Sort by target date and return soonest
        upcoming.sort(key=lambda m: m.target_date)
        return upcoming[0]
    
    def generate_progress_report(self) -> GoalProgressReport:
        """Generate comprehensive progress report.
        
        Returns:
            Goal progress report
        """
        on_track = self.get_on_track_goals()
        off_track = self.get_off_track_goals()
        completed = [g for g in self.goals.values() if g.status == GoalStatus.COMPLETED]
        
        # Calculate average progress
        active_goals = [g for g in self.goals.values() if g.status == GoalStatus.IN_PROGRESS]
        avg_progress = (
            sum(g.progress_percentage for g in active_goals) / len(active_goals)
            if active_goals else 0
        )
        
        # Generate recommendations
        recommendations = []
        
        if off_track:
            recommendations.append(f"⚠️ {len(off_track)} goal(s) off track - review and adjust plans")
        
        if not on_track and active_goals:
            recommendations.append("Increase monthly savings to get back on track")
        
        # Check for priority goals off track
        priority_off_track = [g for g in off_track if g.priority >= 8]
        if priority_off_track:
            recommendations.append("Focus on high-priority goals that are off track")
        
        if on_track:
            recommendations.append(f"✓ {len(on_track)} goal(s) on track - maintain current pace")
        
        if completed:
            recommendations.append(f"🎉 {len(completed)} goal(s) completed - congratulations!")
        
        return GoalProgressReport(
            report_id=str(uuid.uuid4()),
            goals=list(self.goals.values()),
            on_track_count=len(on_track),
            off_track_count=len(off_track),
            completed_count=len(completed),
            total_progress=avg_progress,
            next_milestone=self.get_next_milestone(),
            recommendations=recommendations,
        )
