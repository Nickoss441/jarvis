"""Tests for financial goal tracker."""

import pytest
from datetime import datetime, timezone, timedelta

from jarvis.tools.goal_tracker import (
    GoalCategory, GoalStatus, TimeHorizon,
    MilestoneTarget, ProgressSnapshot, FinancialGoal,
    GoalProgressReport, GoalTracker
)


class TestGoalCategory:
    """Tests for goal categories."""
    
    def test_all_categories(self):
        """Verify all categories are defined."""
        cats = [c.value for c in GoalCategory]
        assert "saving" in cats
        assert "debt_payoff" in cats
        assert "investment" in cats


class TestGoalStatus:
    """Tests for goal status."""
    
    def test_all_statuses(self):
        """Verify all statuses are defined."""
        statuses = [s.value for s in GoalStatus]
        assert "not_started" in statuses
        assert "in_progress" in statuses
        assert "completed" in statuses


class TestTimeHorizon:
    """Tests for time horizons."""
    
    def test_all_horizons(self):
        """Verify all horizons are defined."""
        horizons = [h.value for h in TimeHorizon]
        assert "short_term" in horizons
        assert "medium_term" in horizons
        assert "long_term" in horizons


class TestMilestoneTarget:
    """Tests for milestones."""
    
    def test_milestone_creation(self):
        """Test creating a milestone."""
        target = datetime.now(timezone.utc) + timedelta(days=90)
        milestone = MilestoneTarget(
            milestone_id="m-1",
            label="25% Progress",
            target_value=2500.0,
            target_date=target,
            description="First quarter checkpoint",
        )
        assert milestone.label == "25% Progress"
        assert milestone.target_value == 2500.0
    
    def test_milestone_naive_datetime_raises(self):
        """Test that naive datetime raises error."""
        naive = datetime(2026, 6, 27, 10, 0, 0)
        with pytest.raises(ValueError, match="timezone-aware"):
            MilestoneTarget(
                milestone_id="m-1",
                label="Test",
                target_value=1000.0,
                target_date=naive,
            )
    
    def test_milestone_to_dict(self):
        """Test milestone serialization."""
        target = datetime.now(timezone.utc) + timedelta(days=90)
        milestone = MilestoneTarget(
            milestone_id="m-1",
            label="Halfway",
            target_value=5000.0,
            target_date=target,
        )
        data = milestone.to_dict()
        
        assert data["label"] == "Halfway"
        assert data["target"] == 5000.0


class TestProgressSnapshot:
    """Tests for progress snapshots."""
    
    def test_snapshot_creation(self):
        """Test creating a progress snapshot."""
        now = datetime.now(timezone.utc)
        snapshot = ProgressSnapshot(
            snapshot_id="snap-1",
            current_value=1500.0,
            recorded_at=now,
            note="Monthly contribution",
        )
        assert snapshot.current_value == 1500.0
    
    def test_snapshot_naive_datetime_raises(self):
        """Test that naive datetime raises error."""
        naive = datetime(2026, 5, 27, 10, 0, 0)
        with pytest.raises(ValueError, match="timezone-aware"):
            ProgressSnapshot(
                snapshot_id="snap-1",
                current_value=100.0,
                recorded_at=naive,
            )


class TestFinancialGoal:
    """Tests for financial goals."""
    
    def test_goal_creation(self):
        """Test creating a financial goal."""
        now = datetime.now(timezone.utc)
        target = now + timedelta(days=365)
        
        goal = FinancialGoal(
            goal_id="goal-1",
            title="Save $10,000",
            category=GoalCategory.SAVING,
            description="Build emergency fund",
            target_amount=10000.0,
            current_amount=0.0,
            start_date=now,
            target_date=target,
            time_horizon=TimeHorizon.MEDIUM_TERM,
            priority=8,
        )
        assert goal.title == "Save $10,000"
        assert goal.status == GoalStatus.NOT_STARTED
    
    def test_goal_progress_percentage(self):
        """Test progress percentage calculation."""
        now = datetime.now(timezone.utc)
        goal = FinancialGoal(
            goal_id="goal-1",
            title="Save $10,000",
            category=GoalCategory.SAVING,
            description="Test",
            target_amount=10000.0,
            current_amount=5000.0,
            start_date=now,
            target_date=now + timedelta(days=365),
            time_horizon=TimeHorizon.MEDIUM_TERM,
            priority=5,
        )
        assert goal.progress_percentage == pytest.approx(50.0)
    
    def test_goal_amount_remaining(self):
        """Test remaining amount calculation."""
        now = datetime.now(timezone.utc)
        goal = FinancialGoal(
            goal_id="goal-1",
            title="Test",
            category=GoalCategory.SAVING,
            description="Test",
            target_amount=10000.0,
            current_amount=3000.0,
            start_date=now,
            target_date=now + timedelta(days=365),
            time_horizon=TimeHorizon.MEDIUM_TERM,
            priority=5,
        )
        assert goal.amount_remaining == pytest.approx(7000.0)
    
    def test_goal_on_track_ahead(self):
        """Test on-track status when ahead of schedule."""
        now = datetime.now(timezone.utc)
        goal = FinancialGoal(
            goal_id="goal-1",
            title="Save $12,000",
            category=GoalCategory.SAVING,
            description="Test",
            target_amount=12000.0,
            current_amount=10000.0,  # 83% done
            start_date=now - timedelta(days=180),  # 6 months in
            target_date=now + timedelta(days=180),  # 6 months left
            time_horizon=TimeHorizon.MEDIUM_TERM,
            priority=5,
        )
        # Should be on track (ahead of schedule)
        assert goal.on_track
    
    def test_goal_off_track_behind(self):
        """Test off-track status when behind schedule."""
        now = datetime.now(timezone.utc)
        goal = FinancialGoal(
            goal_id="goal-1",
            title="Save $12,000",
            category=GoalCategory.SAVING,
            description="Test",
            target_amount=12000.0,
            current_amount=1000.0,  # Only 8% done
            start_date=now - timedelta(days=180),  # 6 months in
            target_date=now + timedelta(days=180),  # 6 months left
            time_horizon=TimeHorizon.MEDIUM_TERM,
            priority=5,
        )
        # Should be off track
        assert not goal.on_track
    
    def test_goal_record_progress(self):
        """Test recording progress."""
        now = datetime.now(timezone.utc)
        goal = FinancialGoal(
            goal_id="goal-1",
            title="Test",
            category=GoalCategory.SAVING,
            description="Test",
            target_amount=10000.0,
            current_amount=0.0,
            start_date=now,
            target_date=now + timedelta(days=365),
            time_horizon=TimeHorizon.MEDIUM_TERM,
            priority=5,
        )
        
        snapshot = goal.record_progress(2000.0, "First month savings")
        
        assert goal.current_amount == 2000.0
        assert snapshot.current_value == 2000.0
        assert len(goal.progress_history) == 1
    
    def test_goal_to_dict(self):
        """Test goal serialization."""
        now = datetime.now(timezone.utc)
        goal = FinancialGoal(
            goal_id="goal-1",
            title="Save $5,000",
            category=GoalCategory.SAVING,
            description="Emergency fund",
            target_amount=5000.0,
            current_amount=2000.0,
            start_date=now,
            target_date=now + timedelta(days=180),
            time_horizon=TimeHorizon.SHORT_TERM,
            priority=8,
        )
        data = goal.to_dict()
        
        assert data["title"] == "Save $5,000"
        assert data["target"] == 5000.0
        assert data["current"] == 2000.0


class TestGoalTracker:
    """Tests for goal tracker."""
    
    def test_tracker_creation(self):
        """Test creating goal tracker."""
        tracker = GoalTracker()
        assert len(tracker.goals) == 0
    
    def test_add_goal(self):
        """Test adding a goal."""
        tracker = GoalTracker()
        now = datetime.now(timezone.utc)
        
        goal = tracker.add_goal(
            title="Save $5,000",
            category=GoalCategory.SAVING,
            description="Emergency fund",
            target_amount=5000.0,
            target_date=now + timedelta(days=180),
            time_horizon=TimeHorizon.SHORT_TERM,
            priority=8,
        )
        
        assert len(tracker.goals) == 1
        assert goal.title == "Save $5,000"
    
    def test_add_multiple_goals(self):
        """Test adding multiple goals."""
        tracker = GoalTracker()
        now = datetime.now(timezone.utc)
        
        tracker.add_goal(
            title="Save $5,000",
            category=GoalCategory.SAVING,
            description="Test",
            target_amount=5000.0,
            target_date=now + timedelta(days=180),
            time_horizon=TimeHorizon.SHORT_TERM,
        )
        
        tracker.add_goal(
            title="Pay off debt",
            category=GoalCategory.DEBT_PAYOFF,
            description="Test",
            target_amount=10000.0,
            target_date=now + timedelta(days=365),
            time_horizon=TimeHorizon.MEDIUM_TERM,
        )
        
        assert len(tracker.goals) == 2
    
    def test_record_progress(self):
        """Test recording progress on a goal."""
        tracker = GoalTracker()
        now = datetime.now(timezone.utc)
        
        goal = tracker.add_goal(
            title="Test",
            category=GoalCategory.SAVING,
            description="Test",
            target_amount=10000.0,
            target_date=now + timedelta(days=365),
            time_horizon=TimeHorizon.MEDIUM_TERM,
        )
        
        tracker.record_progress(goal.goal_id, 3000.0, "First contribution")
        
        assert goal.current_amount == 3000.0
        assert goal.status == GoalStatus.IN_PROGRESS
    
    def test_record_progress_nonexistent_raises(self):
        """Test recording progress on nonexistent goal raises error."""
        tracker = GoalTracker()
        with pytest.raises(ValueError, match="not found"):
            tracker.record_progress("fake-id", 1000.0)
    
    def test_get_goals_by_category(self):
        """Test getting goals by category."""
        tracker = GoalTracker()
        now = datetime.now(timezone.utc)
        
        tracker.add_goal(
            title="Save",
            category=GoalCategory.SAVING,
            description="Test",
            target_amount=5000.0,
            target_date=now + timedelta(days=180),
            time_horizon=TimeHorizon.SHORT_TERM,
        )
        
        tracker.add_goal(
            title="Invest",
            category=GoalCategory.INVESTMENT,
            description="Test",
            target_amount=10000.0,
            target_date=now + timedelta(days=365),
            time_horizon=TimeHorizon.MEDIUM_TERM,
        )
        
        saving_goals = tracker.get_goals_by_category(GoalCategory.SAVING)
        assert len(saving_goals) == 1
    
    def test_get_on_track_goals(self):
        """Test getting on-track goals."""
        tracker = GoalTracker()
        now = datetime.now(timezone.utc)
        
        # Create goal that was started 90 days ago (halfway through 180-day goal)
        goal = tracker.add_goal(
            title="Save $12,000",
            category=GoalCategory.SAVING,
            description="Test",
            target_amount=12000.0,
            target_date=now + timedelta(days=180),
            time_horizon=TimeHorizon.MEDIUM_TERM,
        )
        # Manually set start date to 90 days ago for testing
        goal.start_date = now - timedelta(days=90)
        
        # Record good progress
        tracker.record_progress(goal.goal_id, 10000.0)
        
        on_track = tracker.get_on_track_goals()
        assert len(on_track) >= 1
    
    def test_get_next_milestone(self):
        """Test getting next upcoming milestone."""
        tracker = GoalTracker()
        now = datetime.now(timezone.utc)
        
        goal = tracker.add_goal(
            title="Save",
            category=GoalCategory.SAVING,
            description="Test",
            target_amount=10000.0,
            target_date=now + timedelta(days=365),
            time_horizon=TimeHorizon.MEDIUM_TERM,
        )
        
        # Add milestone
        milestone = MilestoneTarget(
            milestone_id="m-1",
            label="50%",
            target_value=5000.0,
            target_date=now + timedelta(days=90),
        )
        goal.milestones.append(milestone)
        
        next_milestone = tracker.get_next_milestone()
        assert next_milestone is not None
        assert next_milestone.label == "50%"
    
    def test_generate_progress_report(self):
        """Test generating progress report."""
        tracker = GoalTracker()
        now = datetime.now(timezone.utc)
        
        # Add a goal and record progress to make it active
        goal = tracker.add_goal(
            title="Goal 1",
            category=GoalCategory.SAVING,
            description="Test",
            target_amount=5000.0,
            target_date=now + timedelta(days=180),
            time_horizon=TimeHorizon.SHORT_TERM,
        )
        tracker.record_progress(goal.goal_id, 1000.0)
        
        report = tracker.generate_progress_report()
        
        assert isinstance(report, GoalProgressReport)


class TestGoalTrackerEdgeCases:
    """Edge case tests for goal tracker."""
    
    def test_completed_goal(self):
        """Test completed goal tracking."""
        tracker = GoalTracker()
        now = datetime.now(timezone.utc)
        
        goal = tracker.add_goal(
            title="Save $1,000",
            category=GoalCategory.SAVING,
            description="Test",
            target_amount=1000.0,
            target_date=now + timedelta(days=30),
            time_horizon=TimeHorizon.SHORT_TERM,
        )
        
        # Record full amount
        tracker.record_progress(goal.goal_id, 1000.0)
        
        assert goal.status == GoalStatus.COMPLETED
        assert goal.progress_percentage == 100.0
    
    def test_multiple_progress_records(self):
        """Test multiple progress updates."""
        tracker = GoalTracker()
        now = datetime.now(timezone.utc)
        
        goal = tracker.add_goal(
            title="Save",
            category=GoalCategory.SAVING,
            description="Test",
            target_amount=10000.0,
            target_date=now + timedelta(days=365),
            time_horizon=TimeHorizon.MEDIUM_TERM,
        )
        
        # Record progress multiple times
        tracker.record_progress(goal.goal_id, 2000.0, "Month 1")
        tracker.record_progress(goal.goal_id, 4000.0, "Month 2")
        tracker.record_progress(goal.goal_id, 6000.0, "Month 3")
        
        assert len(goal.progress_history) == 3
        assert goal.current_amount == 6000.0
    
    def test_overachieving_goal(self):
        """Test goal exceeding target."""
        tracker = GoalTracker()
        now = datetime.now(timezone.utc)
        
        goal = tracker.add_goal(
            title="Save $5,000",
            category=GoalCategory.SAVING,
            description="Test",
            target_amount=5000.0,
            target_date=now + timedelta(days=180),
            time_horizon=TimeHorizon.SHORT_TERM,
        )
        
        # Record more than target
        tracker.record_progress(goal.goal_id, 6000.0)
        
        assert goal.progress_percentage == 100.0
        assert goal.amount_remaining == 0.0
