from datetime import datetime, timedelta, timezone

import pytest

from jarvis.tools.sinking_fund_planner import (
    ContributionFrequency,
    ContributionRecord,
    FundCategory,
    FundStatus,
    FundingProjection,
    SinkingFundGoal,
    SinkingFundPlanner,
)


def _utc(year: int, month: int, day: int) -> datetime:
    return datetime(year, month, day, tzinfo=timezone.utc)


def test_sinking_fund_goal_validation_negative_target_amount():
    with pytest.raises(ValueError, match="target_amount"):
        SinkingFundGoal(
            fund_id="f1",
            name="Vacation",
            category=FundCategory.TRAVEL,
            target_amount=-1,
            current_balance=0,
            target_date=_utc(2026, 12, 1),
            created_at=_utc(2026, 1, 1),
        )


def test_sinking_fund_goal_validation_timezone_required():
    with pytest.raises(ValueError, match="timezone-aware"):
        SinkingFundGoal(
            fund_id="f1",
            name="Vacation",
            category=FundCategory.TRAVEL,
            target_amount=1000,
            current_balance=0,
            target_date=datetime(2026, 12, 1),
            created_at=_utc(2026, 1, 1),
        )


def test_goal_progress_properties_and_statuses():
    goal = SinkingFundGoal(
        fund_id="f1",
        name="Vacation",
        category=FundCategory.TRAVEL,
        target_amount=1000,
        current_balance=0,
        target_date=_utc(2026, 12, 1),
        created_at=_utc(2026, 1, 1),
    )
    assert goal.amount_remaining == pytest.approx(1000)
    assert goal.progress_percentage == pytest.approx(0)
    assert goal.status == FundStatus.NOT_STARTED

    goal.current_balance = 500
    assert goal.amount_remaining == pytest.approx(500)
    assert goal.status == FundStatus.IN_PROGRESS

    goal.current_balance = 1000
    assert goal.status == FundStatus.FUNDED

    goal.current_balance = 1200
    assert goal.status == FundStatus.OVERFUNDED


def test_goal_zero_target_amount_is_fully_funded():
    goal = SinkingFundGoal(
        fund_id="f1",
        name="Fee",
        category=FundCategory.OTHER,
        target_amount=0,
        current_balance=0,
        target_date=_utc(2026, 12, 1),
        created_at=_utc(2026, 1, 1),
    )
    assert goal.progress_percentage == pytest.approx(100)


def test_contribution_record_validation_negative_amount():
    with pytest.raises(ValueError, match="amount"):
        ContributionRecord(
            contribution_id="c1",
            fund_id="f1",
            amount=-1,
            contributed_at=_utc(2026, 1, 1),
        )


def test_add_fund_registers_goal():
    planner = SinkingFundPlanner()
    goal = planner.add_fund(
        name="Vacation",
        category=FundCategory.TRAVEL,
        target_amount=2000,
        current_balance=200,
        target_date=_utc(2026, 12, 1),
        created_at=_utc(2026, 1, 1),
    )

    assert goal.fund_id in planner.funds
    assert planner.funds[goal.fund_id].name == "Vacation"


def test_record_contribution_updates_balance_and_history():
    planner = SinkingFundPlanner()
    goal = planner.add_fund(
        name="Vacation",
        category=FundCategory.TRAVEL,
        target_amount=2000,
        current_balance=200,
        target_date=_utc(2026, 12, 1),
        created_at=_utc(2026, 1, 1),
    )

    record = planner.record_contribution(goal.fund_id, 300, _utc(2026, 2, 1), note="bonus")

    assert isinstance(record, ContributionRecord)
    assert planner.funds[goal.fund_id].current_balance == pytest.approx(500)
    assert len(planner.contributions) == 1


def test_record_contribution_unknown_fund_raises():
    planner = SinkingFundPlanner()
    with pytest.raises(KeyError, match="fund not found"):
        planner.record_contribution("missing", 100, _utc(2026, 1, 1))


def test_record_contribution_negative_amount_raises():
    planner = SinkingFundPlanner()
    goal = planner.add_fund(
        name="Vacation",
        category=FundCategory.TRAVEL,
        target_amount=2000,
        current_balance=200,
        target_date=_utc(2026, 12, 1),
        created_at=_utc(2026, 1, 1),
    )
    with pytest.raises(ValueError, match="amount"):
        planner.record_contribution(goal.fund_id, -1, _utc(2026, 2, 1))


def test_total_target_current_and_remaining_amounts():
    planner = SinkingFundPlanner()
    planner.add_fund("A", FundCategory.TRAVEL, 1000, 200, _utc(2026, 12, 1), _utc(2026, 1, 1))
    planner.add_fund("B", FundCategory.HOME, 500, 600, _utc(2026, 6, 1), _utc(2026, 1, 1))

    assert planner.get_total_target_amount() == pytest.approx(1500)
    assert planner.get_total_current_balance() == pytest.approx(800)
    assert planner.get_total_remaining_amount() == pytest.approx(800)


def test_estimate_required_contribution_monthly_rounds_up_periods():
    planner = SinkingFundPlanner()
    goal = planner.add_fund(
        name="Vacation",
        category=FundCategory.TRAVEL,
        target_amount=1200,
        current_balance=0,
        target_date=_utc(2026, 4, 10),
        created_at=_utc(2026, 1, 1),
    )

    as_of = _utc(2026, 1, 1)
    required = planner.estimate_required_contribution(
        goal.fund_id,
        ContributionFrequency.MONTHLY,
        as_of=as_of,
    )
    assert required == pytest.approx(300)


def test_estimate_required_contribution_zero_when_already_funded():
    planner = SinkingFundPlanner()
    goal = planner.add_fund(
        name="Vacation",
        category=FundCategory.TRAVEL,
        target_amount=1200,
        current_balance=1300,
        target_date=_utc(2026, 4, 10),
        created_at=_utc(2026, 1, 1),
    )
    required = planner.estimate_required_contribution(goal.fund_id, ContributionFrequency.MONTHLY, as_of=_utc(2026, 1, 1))
    assert required == pytest.approx(0)


def test_estimate_required_contribution_due_now_uses_full_remaining():
    planner = SinkingFundPlanner()
    goal = planner.add_fund(
        name="Vacation",
        category=FundCategory.TRAVEL,
        target_amount=1000,
        current_balance=250,
        target_date=_utc(2026, 1, 1),
        created_at=_utc(2025, 1, 1),
    )
    required = planner.estimate_required_contribution(goal.fund_id, ContributionFrequency.WEEKLY, as_of=_utc(2026, 1, 1))
    assert required == pytest.approx(750)


def test_estimate_required_contribution_requires_timezone_aware_as_of():
    planner = SinkingFundPlanner()
    goal = planner.add_fund(
        name="Vacation",
        category=FundCategory.TRAVEL,
        target_amount=1000,
        current_balance=250,
        target_date=_utc(2026, 4, 1),
        created_at=_utc(2025, 1, 1),
    )
    with pytest.raises(ValueError, match="timezone-aware"):
        planner.estimate_required_contribution(goal.fund_id, ContributionFrequency.WEEKLY, as_of=datetime(2026, 1, 1))


def test_project_funding_rejects_invalid_inputs():
    planner = SinkingFundPlanner()
    goal = planner.add_fund(
        name="Vacation",
        category=FundCategory.TRAVEL,
        target_amount=1000,
        current_balance=250,
        target_date=_utc(2026, 4, 1),
        created_at=_utc(2025, 1, 1),
    )
    with pytest.raises(ValueError, match="contribution_per_period"):
        planner.project_funding(goal.fund_id, ContributionFrequency.MONTHLY, -1)
    with pytest.raises(ValueError, match="max_periods"):
        planner.project_funding(goal.fund_id, ContributionFrequency.MONTHLY, 100, max_periods=-1)


def test_project_funding_reaches_target():
    planner = SinkingFundPlanner()
    goal = planner.add_fund(
        name="Vacation",
        category=FundCategory.TRAVEL,
        target_amount=1000,
        current_balance=100,
        target_date=_utc(2026, 12, 1),
        created_at=_utc(2026, 1, 1),
    )
    projection = planner.project_funding(goal.fund_id, ContributionFrequency.MONTHLY, 300)

    assert isinstance(projection, FundingProjection)
    assert projection.target_reached is True
    assert projection.periods_to_target == 3
    assert projection.final_balance == pytest.approx(1000)
    assert len(projection.timeline) == 3


def test_project_funding_returns_none_when_not_reached():
    planner = SinkingFundPlanner()
    goal = planner.add_fund(
        name="Vacation",
        category=FundCategory.TRAVEL,
        target_amount=1000,
        current_balance=100,
        target_date=_utc(2026, 12, 1),
        created_at=_utc(2026, 1, 1),
    )
    projection = planner.project_funding(goal.fund_id, ContributionFrequency.MONTHLY, 100, max_periods=2)

    assert projection.target_reached is False
    assert projection.projected_completion_date is None
    assert projection.final_balance == pytest.approx(300)


def test_get_funds_by_status_filters_correctly():
    planner = SinkingFundPlanner()
    a = planner.add_fund("A", FundCategory.TRAVEL, 1000, 0, _utc(2026, 12, 1), _utc(2026, 1, 1))
    b = planner.add_fund("B", FundCategory.HOME, 1000, 400, _utc(2026, 12, 1), _utc(2026, 1, 1))
    c = planner.add_fund("C", FundCategory.AUTO, 1000, 1000, _utc(2026, 12, 1), _utc(2026, 1, 1))

    assert [fund.fund_id for fund in planner.get_funds_by_status(FundStatus.NOT_STARTED)] == [a.fund_id]
    assert [fund.fund_id for fund in planner.get_funds_by_status(FundStatus.IN_PROGRESS)] == [b.fund_id]
    assert [fund.fund_id for fund in planner.get_funds_by_status(FundStatus.FUNDED)] == [c.fund_id]


def test_get_category_breakdown_aggregates_totals():
    planner = SinkingFundPlanner()
    planner.add_fund("Trip", FundCategory.TRAVEL, 1000, 200, _utc(2026, 12, 1), _utc(2026, 1, 1))
    planner.add_fund("Hotel", FundCategory.TRAVEL, 500, 100, _utc(2026, 10, 1), _utc(2026, 1, 1))
    planner.add_fund("Repair", FundCategory.HOME, 700, 300, _utc(2026, 11, 1), _utc(2026, 1, 1))

    breakdown = planner.get_category_breakdown()
    assert breakdown[FundCategory.TRAVEL.value]["target_amount"] == pytest.approx(1500)
    assert breakdown[FundCategory.TRAVEL.value]["current_balance"] == pytest.approx(300)
    assert breakdown[FundCategory.TRAVEL.value]["remaining_amount"] == pytest.approx(1200)
    assert breakdown[FundCategory.TRAVEL.value]["count"] == 2


def test_periods_between_round_up_partial_periods():
    assert SinkingFundPlanner._periods_between(1, ContributionFrequency.WEEKLY) == 1
    assert SinkingFundPlanner._periods_between(8, ContributionFrequency.WEEKLY) == 2
    assert SinkingFundPlanner._periods_between(31, ContributionFrequency.MONTHLY) == 2
    assert SinkingFundPlanner._periods_between(0, ContributionFrequency.MONTHLY) == 0


def test_goal_to_dict_shape():
    goal = SinkingFundGoal(
        fund_id="f1",
        name="Trip",
        category=FundCategory.TRAVEL,
        target_amount=1000,
        current_balance=250,
        target_date=_utc(2026, 12, 1),
        created_at=_utc(2026, 1, 1),
    )
    data = goal.to_dict()
    assert data["id"] == "f1"
    assert data["status"] == FundStatus.IN_PROGRESS.value


def test_contribution_record_to_dict_shape():
    record = ContributionRecord(
        contribution_id="c1",
        fund_id="f1",
        amount=100,
        contributed_at=_utc(2026, 1, 1),
        note="bonus",
    )
    data = record.to_dict()
    assert data["id"] == "c1"
    assert data["amount"] == pytest.approx(100)


def test_funding_projection_to_dict_shape():
    planner = SinkingFundPlanner()
    goal = planner.add_fund("Trip", FundCategory.TRAVEL, 1000, 100, _utc(2026, 12, 1), _utc(2026, 1, 1))
    projection = planner.project_funding(goal.fund_id, ContributionFrequency.MONTHLY, 300)
    data = projection.to_dict()
    assert data["fund_id"] == goal.fund_id
    assert data["target_reached"] is True


def test_project_funding_unknown_fund_raises():
    planner = SinkingFundPlanner()
    with pytest.raises(KeyError, match="fund not found"):
        planner.project_funding("missing", ContributionFrequency.MONTHLY, 100)


def test_estimate_required_contribution_unknown_fund_raises():
    planner = SinkingFundPlanner()
    with pytest.raises(KeyError, match="fund not found"):
        planner.estimate_required_contribution("missing", ContributionFrequency.MONTHLY)


def test_status_overfunded_returned_from_filter():
    planner = SinkingFundPlanner()
    goal = planner.add_fund("Trip", FundCategory.TRAVEL, 1000, 1200, _utc(2026, 12, 1), _utc(2026, 1, 1))
    overfunded = planner.get_funds_by_status(FundStatus.OVERFUNDED)
    assert [fund.fund_id for fund in overfunded] == [goal.fund_id]


def test_goal_created_with_notes():
    planner = SinkingFundPlanner()
    goal = planner.add_fund(
        "Conference",
        FundCategory.EDUCATION,
        1800,
        300,
        _utc(2026, 9, 1),
        _utc(2026, 1, 1),
        notes="Flights and hotel",
    )
    assert goal.notes == "Flights and hotel"
