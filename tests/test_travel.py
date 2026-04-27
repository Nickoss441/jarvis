"""Tests for travel itinerary and reservation management."""

import pytest
from datetime import datetime, timezone, timedelta
from pathlib import Path
from jarvis.tools.travel import (
    ReservationType,
    Reservation,
    Leg,
    Itinerary,
    ItineraryManager,
    get_itinerary_summary,
)


class TestReservationType:
    """Test reservation type enum."""
    
    def test_all_types_defined(self):
        """All expected types are defined."""
        assert ReservationType.FLIGHT.value == "flight"
        assert ReservationType.HOTEL.value == "hotel"
        assert ReservationType.CAR_RENTAL.value == "car_rental"
        assert ReservationType.TRAIN.value == "train"
        assert ReservationType.ACTIVITY.value == "activity"
        assert ReservationType.DINING.value == "dining"


class TestReservation:
    """Test individual reservation."""
    
    def test_flight_reservation_creation(self):
        """Create a flight reservation."""
        res = Reservation(
            id="flight-001",
            type=ReservationType.FLIGHT,
            supplier="United",
            confirmation_number="ABC123",
            start_date="2026-05-15",
            start_time="14:00:00",
            location_from="SFO",
            location_to="JFK",
            cost=450.00,
        )
        
        assert res.type == ReservationType.FLIGHT
        assert res.supplier == "United"
        assert res.cost == 450.00
    
    def test_hotel_reservation_creation(self):
        """Create a hotel reservation."""
        res = Reservation(
            id="hotel-001",
            type=ReservationType.HOTEL,
            supplier="Marriott",
            confirmation_number="MAR789",
            start_date="2026-05-15",
            end_date="2026-05-18",
            location_to="New York",
            cost=1200.00,
            details={"nights": 3, "rooms": 1, "rating": 4.5},
        )
        
        assert res.type == ReservationType.HOTEL
        assert res.details["nights"] == 3
    
    def test_reservation_to_dict(self):
        """Reservation serializes to dict."""
        res = Reservation(
            id="res-001",
            type=ReservationType.FLIGHT,
            supplier="Delta",
            confirmation_number="DLT456",
            start_date="2026-05-15",
            cost=500.00,
        )
        
        result = res.to_dict()
        assert result["id"] == "res-001"
        assert result["type"] == "flight"
        assert result["cost"] == 500.00


class TestLeg:
    """Test itinerary leg."""
    
    def test_leg_creation(self):
        """Create a journey leg."""
        leg = Leg(
            id="leg-1",
            sequence=1,
            destination="New York",
            start_date="2026-05-15",
            end_date="2026-05-18",
        )
        
        assert leg.sequence == 1
        assert leg.destination == "New York"
    
    def test_leg_with_reservations(self):
        """Leg can track multiple reservations."""
        leg = Leg(
            id="leg-1",
            sequence=1,
            destination="New York",
            start_date="2026-05-15",
            end_date="2026-05-18",
            reservations=["flight-001", "hotel-001"],
        )
        
        assert len(leg.reservations) == 2
    
    def test_leg_to_dict(self):
        """Leg serializes to dict."""
        leg = Leg(
            id="leg-1",
            sequence=1,
            destination="Paris",
            start_date="2026-05-18",
            end_date="2026-05-22",
        )
        
        result = leg.to_dict()
        assert result["sequence"] == 1
        assert result["destination"] == "Paris"


class TestItinerary:
    """Test complete itinerary."""
    
    def test_itinerary_creation(self):
        """Create an itinerary."""
        itin = Itinerary(
            id="trip-001",
            title="Summer European Tour",
            start_date="2026-05-15",
            end_date="2026-06-15",
            origin="San Francisco",
            travelers=["Alice", "Bob"],
            budget=5000.00,
        )
        
        assert itin.title == "Summer European Tour"
        assert len(itin.travelers) == 2
        assert itin.budget == 5000.00
    
    def test_add_leg(self):
        """Add leg to itinerary."""
        itin = Itinerary(
            id="trip-001",
            title="Trip",
            start_date="2026-05-15",
            end_date="2026-06-15",
            origin="Home",
        )
        
        leg = Leg(
            id="leg-1",
            sequence=1,
            destination="New York",
            start_date="2026-05-15",
            end_date="2026-05-18",
        )
        
        itin.add_leg(leg)
        
        assert len(itin.legs) == 1
        assert itin.legs["leg-1"].destination == "New York"
    
    def test_add_reservation(self):
        """Add reservation to itinerary and link to leg."""
        itin = Itinerary(
            id="trip-001",
            title="Trip",
            start_date="2026-05-15",
            end_date="2026-06-15",
            origin="Home",
        )
        
        leg = Leg(
            id="leg-1",
            sequence=1,
            destination="New York",
            start_date="2026-05-15",
            end_date="2026-05-18",
        )
        itin.add_leg(leg)
        
        res = Reservation(
            id="flight-001",
            type=ReservationType.FLIGHT,
            supplier="United",
            confirmation_number="ABC123",
            start_date="2026-05-15",
            cost=450.00,
        )
        
        itin.add_reservation(res, "leg-1")
        
        assert len(itin.reservations) == 1
        assert res.id in itin.legs["leg-1"].reservations
    
    def test_total_cost(self):
        """Calculate total cost of all reservations."""
        itin = Itinerary(
            id="trip-001",
            title="Trip",
            start_date="2026-05-15",
            end_date="2026-06-15",
            origin="Home",
        )
        
        res1 = Reservation(
            id="res-1",
            type=ReservationType.FLIGHT,
            supplier="Airline",
            confirmation_number="ABC",
            start_date="2026-05-15",
            cost=450.00,
        )
        res2 = Reservation(
            id="res-2",
            type=ReservationType.HOTEL,
            supplier="Hotel",
            confirmation_number="DEF",
            start_date="2026-05-15",
            cost=1200.00,
        )
        
        itin.add_reservation(res1, "leg-1")
        itin.add_reservation(res2, "leg-1")
        
        assert itin.total_cost() == 1650.00
    
    def test_remaining_budget(self):
        """Calculate remaining budget."""
        itin = Itinerary(
            id="trip-001",
            title="Trip",
            start_date="2026-05-15",
            end_date="2026-06-15",
            origin="Home",
            budget=2000.00,
        )
        
        res = Reservation(
            id="res-1",
            type=ReservationType.FLIGHT,
            supplier="Airline",
            confirmation_number="ABC",
            start_date="2026-05-15",
            cost=450.00,
        )
        itin.add_reservation(res, "leg-1")
        
        assert itin.remaining_budget() == 1550.00
    
    def test_is_budget_exceeded(self):
        """Check if budget is exceeded."""
        itin = Itinerary(
            id="trip-001",
            title="Trip",
            start_date="2026-05-15",
            end_date="2026-06-15",
            origin="Home",
            budget=500.00,
        )
        
        res = Reservation(
            id="res-1",
            type=ReservationType.FLIGHT,
            supplier="Airline",
            confirmation_number="ABC",
            start_date="2026-05-15",
            cost=600.00,
        )
        itin.add_reservation(res, "leg-1")
        
        assert itin.is_budget_exceeded() is True
    
    def test_upcoming_reservations(self):
        """Get upcoming reservations."""
        now = datetime.now(timezone.utc)
        future = (now + timedelta(days=5)).isoformat()
        past = (now - timedelta(days=5)).isoformat()
        
        itin = Itinerary(
            id="trip-001",
            title="Trip",
            start_date=future,
            end_date=future,
            origin="Home",
        )
        
        res_future = Reservation(
            id="res-future",
            type=ReservationType.FLIGHT,
            supplier="Airline",
            confirmation_number="ABC",
            start_date=future,
            cost=450.00,
        )
        res_past = Reservation(
            id="res-past",
            type=ReservationType.HOTEL,
            supplier="Hotel",
            confirmation_number="DEF",
            start_date=past,
            cost=1200.00,
        )
        
        itin.add_reservation(res_future, "leg-1")
        itin.add_reservation(res_past, "leg-1")
        
        upcoming = itin.upcoming_reservations(now=now)
        assert len(upcoming) == 1
        assert upcoming[0].id == "res-future"
    
    def test_itinerary_to_dict(self):
        """Itinerary serializes to dict."""
        itin = Itinerary(
            id="trip-001",
            title="Trip",
            start_date="2026-05-15",
            end_date="2026-06-15",
            origin="Home",
            budget=2000.00,
        )
        
        result = itin.to_dict()
        assert result["title"] == "Trip"
        assert result["budget"] == 2000.00


class TestItineraryManager:
    """Test itinerary manager."""
    
    def test_manager_creation(self, tmp_path):
        """Create itinerary manager."""
        manager = ItineraryManager(tmp_path / "itineraries.json")
        assert len(manager.list_itineraries()) == 0
    
    def test_create_itinerary(self, tmp_path):
        """Create and store itinerary."""
        manager = ItineraryManager(tmp_path / "itineraries.json")
        
        itin = manager.create_itinerary(
            id="trip-001",
            title="Summer Trip",
            start_date="2026-05-15",
            end_date="2026-06-15",
            origin="Home",
        )
        
        assert len(manager.list_itineraries()) == 1
        assert manager.get_itinerary("trip-001") is not None
    
    def test_get_itinerary(self, tmp_path):
        """Retrieve itinerary by ID."""
        manager = ItineraryManager(tmp_path / "itineraries.json")
        
        manager.create_itinerary(
            id="trip-001",
            title="Trip",
            start_date="2026-05-15",
            end_date="2026-06-15",
            origin="Home",
        )
        
        retrieved = manager.get_itinerary("trip-001")
        assert retrieved is not None
        assert retrieved.title == "Trip"
    
    def test_active_itineraries(self, tmp_path):
        """Get active itineraries."""
        manager = ItineraryManager(tmp_path / "itineraries.json")
        
        now = datetime.now(timezone.utc)
        future = (now + timedelta(days=5)).isoformat()
        past = (now - timedelta(days=5)).isoformat()
        
        manager.create_itinerary(
            id="trip-future",
            title="Future Trip",
            start_date=future,
            end_date=future,
            origin="Home",
        )
        manager.create_itinerary(
            id="trip-past",
            title="Past Trip",
            start_date=past,
            end_date=past,
            origin="Home",
        )
        
        active = manager.active_itineraries(now=now)
        assert len(active) == 1
        assert active[0].id == "trip-future"
    
    def test_save_to_file(self, tmp_path):
        """Save itineraries to file."""
        filepath = tmp_path / "itineraries.json"
        manager = ItineraryManager(filepath)
        
        manager.create_itinerary(
            id="trip-001",
            title="Trip",
            start_date="2026-05-15",
            end_date="2026-06-15",
            origin="Home",
        )
        
        manager.save_to_file()
        
        assert filepath.exists()
    
    def test_load_from_file(self, tmp_path):
        """Load itineraries from file."""
        filepath = tmp_path / "itineraries.json"
        
        # Create and save
        manager1 = ItineraryManager(filepath)
        manager1.create_itinerary(
            id="trip-001",
            title="Trip",
            start_date="2026-05-15",
            end_date="2026-06-15",
            origin="Home",
        )
        manager1.save_to_file()
        
        # Load in new manager
        manager2 = ItineraryManager(filepath)
        manager2.load_from_file()
        
        assert len(manager2.list_itineraries()) == 1
        assert manager2.get_itinerary("trip-001") is not None


class TestItinerarySummary:
    """Test itinerary summary generation."""
    
    def test_summary_generation(self):
        """Generate summary of itinerary."""
        itin = Itinerary(
            id="trip-001",
            title="Trip",
            start_date="2026-05-15",
            end_date="2026-06-15",
            origin="Home",
            travelers=["Alice", "Bob"],
            budget=2000.00,
        )
        
        leg = Leg(
            id="leg-1",
            sequence=1,
            destination="NYC",
            start_date="2026-05-15",
            end_date="2026-05-18",
        )
        itin.add_leg(leg)
        
        res = Reservation(
            id="res-1",
            type=ReservationType.FLIGHT,
            supplier="Airline",
            confirmation_number="ABC",
            start_date="2026-05-15",
            cost=450.00,
        )
        itin.add_reservation(res, "leg-1")
        
        summary = get_itinerary_summary(itin)
        
        assert summary["title"] == "Trip"
        assert summary["leg_count"] == 1
        assert summary["reservation_count"] == 1
        assert summary["total_cost"] == 450.00
        assert summary["budget"] == 2000.00
        assert summary["budget_exceeded"] is False
