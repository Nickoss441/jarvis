"""Travel itinerary and reservation management."""

from datetime import datetime, date, timezone, timedelta
from typing import Optional
from enum import Enum
from dataclasses import dataclass, field
import json
from pathlib import Path


class ReservationType(str, Enum):
    """Types of travel reservations."""
    FLIGHT = "flight"
    HOTEL = "hotel"
    CAR_RENTAL = "car_rental"
    TRAIN = "train"
    ACTIVITY = "activity"
    DINING = "dining"


@dataclass
class Reservation:
    """Single travel reservation."""
    
    id: str  # Unique reservation ID
    type: ReservationType
    supplier: str  # Airline, hotel brand, rental company
    confirmation_number: str
    start_date: str  # ISO8601 date
    end_date: Optional[str] = None  # ISO8601 date for multi-day reservations
    start_time: Optional[str] = None  # ISO8601 time
    end_time: Optional[str] = None
    location_from: Optional[str] = None  # Origin (for flights/trains)
    location_to: Optional[str] = None  # Destination
    details: dict = field(default_factory=dict)  # Type-specific details
    cost: Optional[float] = None  # Total cost in USD
    currency: str = "USD"
    notes: str = ""
    
    def to_dict(self) -> dict:
        """Serialize to dict."""
        return {
            "id": self.id,
            "type": self.type.value,
            "supplier": self.supplier,
            "confirmation_number": self.confirmation_number,
            "start_date": self.start_date,
            "end_date": self.end_date,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "location_from": self.location_from,
            "location_to": self.location_to,
            "details": self.details,
            "cost": self.cost,
            "currency": self.currency,
            "notes": self.notes,
        }


@dataclass
class Leg:
    """Single leg of a journey (e.g., destination in multi-city trip)."""
    
    id: str  # Unique leg ID
    sequence: int  # Order in itinerary (1-indexed)
    destination: str  # City/airport code
    start_date: str  # ISO8601 date
    end_date: str  # ISO8601 date
    reservations: list[str] = field(default_factory=list)  # Reservation IDs for this leg
    notes: str = ""
    
    def to_dict(self) -> dict:
        """Serialize to dict."""
        return {
            "id": self.id,
            "sequence": self.sequence,
            "destination": self.destination,
            "start_date": self.start_date,
            "end_date": self.end_date,
            "reservations": self.reservations,
            "notes": self.notes,
        }


@dataclass
class Itinerary:
    """Complete travel itinerary with multiple legs and reservations."""
    
    id: str  # Unique itinerary ID
    title: str
    start_date: str  # ISO8601 date
    end_date: str  # ISO8601 date
    origin: str  # Home/base location
    travelers: list[str] = field(default_factory=list)  # Names of travelers
    legs: dict[str, Leg] = field(default_factory=dict)  # Keyed by leg ID
    reservations: dict[str, Reservation] = field(default_factory=dict)  # Keyed by reservation ID
    budget: Optional[float] = None  # Total trip budget in USD
    budget_spent: float = 0.0  # Amount spent
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    notes: str = ""
    
    def add_leg(self, leg: Leg) -> None:
        """Add leg to itinerary."""
        self.legs[leg.id] = leg
        self.updated_at = datetime.now(timezone.utc).isoformat()
    
    def add_reservation(self, reservation: Reservation, leg_id: str) -> None:
        """Add reservation to itinerary and link to leg."""
        self.reservations[reservation.id] = reservation
        if leg_id in self.legs:
            if reservation.id not in self.legs[leg_id].reservations:
                self.legs[leg_id].reservations.append(reservation.id)
        self.updated_at = datetime.now(timezone.utc).isoformat()
        if reservation.cost:
            self.budget_spent += reservation.cost
    
    def total_cost(self) -> float:
        """Calculate total cost of all reservations."""
        return sum(r.cost or 0.0 for r in self.reservations.values())
    
    def remaining_budget(self) -> Optional[float]:
        """Calculate remaining budget."""
        if self.budget is None:
            return None
        return self.budget - self.total_cost()
    
    def is_budget_exceeded(self) -> bool:
        """Check if budget is exceeded."""
        if self.budget is None:
            return False
        return self.total_cost() > self.budget
    
    def upcoming_reservations(self, now: Optional[datetime] = None) -> list[Reservation]:
        """Get reservations happening from now onwards."""
        now = now or datetime.now(timezone.utc)
        upcoming = []
        
        for res in self.reservations.values():
            try:
                # Parse date, ensuring it has timezone info
                date_str = res.start_date.replace('Z', '+00:00')
                res_date = datetime.fromisoformat(date_str)
                
                # If parsed date is naive, assume UTC
                if res_date.tzinfo is None:
                    res_date = res_date.replace(tzinfo=timezone.utc)
                
                if res_date >= now:
                    upcoming.append(res)
            except (ValueError, AttributeError):
                pass
        
        return sorted(upcoming, key=lambda r: r.start_date)
    
    def to_dict(self) -> dict:
        """Serialize to dict."""
        return {
            "id": self.id,
            "title": self.title,
            "start_date": self.start_date,
            "end_date": self.end_date,
            "origin": self.origin,
            "travelers": self.travelers,
            "legs": {lid: leg.to_dict() for lid, leg in self.legs.items()},
            "reservations": {rid: res.to_dict() for rid, res in self.reservations.items()},
            "budget": self.budget,
            "budget_spent": round(self.total_cost(), 2),
            "budget_remaining": round(self.remaining_budget(), 2) if self.remaining_budget() is not None else None,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "notes": self.notes,
        }


class ItineraryManager:
    """Manage multiple itineraries and persistence."""
    
    def __init__(self, storage_path: Path):
        self.storage_path = Path(storage_path)
        self.itineraries: dict[str, Itinerary] = {}
    
    def create_itinerary(
        self,
        id: str,
        title: str,
        start_date: str,
        end_date: str,
        origin: str,
        travelers: list[str] = None,
        budget: Optional[float] = None,
    ) -> Itinerary:
        """Create and store new itinerary."""
        itinerary = Itinerary(
            id=id,
            title=title,
            start_date=start_date,
            end_date=end_date,
            origin=origin,
            travelers=travelers or [],
            budget=budget,
        )
        self.itineraries[id] = itinerary
        return itinerary
    
    def get_itinerary(self, itinerary_id: str) -> Optional[Itinerary]:
        """Retrieve itinerary by ID."""
        return self.itineraries.get(itinerary_id)
    
    def list_itineraries(self) -> list[Itinerary]:
        """List all itineraries."""
        return list(self.itineraries.values())
    
    def active_itineraries(self, now: Optional[datetime] = None) -> list[Itinerary]:
        """Get itineraries that are currently active (happening today or in future)."""
        now = now or datetime.now(timezone.utc)
        active = []
        
        for itin in self.itineraries.values():
            try:
                # Parse date, ensuring it has timezone info
                date_str = itin.end_date.replace('Z', '+00:00')
                end = datetime.fromisoformat(date_str)
                
                # If parsed date is naive, assume UTC
                if end.tzinfo is None:
                    end = end.replace(tzinfo=timezone.utc)
                
                if end >= now:
                    active.append(itin)
            except (ValueError, AttributeError):
                pass
        
        return sorted(active, key=lambda i: i.start_date)
    
    def save_to_file(self) -> None:
        """Save all itineraries to file."""
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        
        data = {
            "itineraries": {id: itin.to_dict() for id, itin in self.itineraries.items()},
            "saved_at": datetime.now(timezone.utc).isoformat(),
        }
        
        with self.storage_path.open("w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    
    def load_from_file(self) -> None:
        """Load itineraries from file."""
        if not self.storage_path.exists():
            return
        
        with self.storage_path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        
        # Parse itineraries (simplified - in production would handle nested structures)
        for itin_id, itin_data in data.get("itineraries", {}).items():
            itin = Itinerary(
                id=itin_id,
                title=itin_data.get("title", ""),
                start_date=itin_data.get("start_date", ""),
                end_date=itin_data.get("end_date", ""),
                origin=itin_data.get("origin", ""),
                travelers=itin_data.get("travelers", []),
                budget=itin_data.get("budget"),
                created_at=itin_data.get("created_at", ""),
                updated_at=itin_data.get("updated_at", ""),
                notes=itin_data.get("notes", ""),
            )
            self.itineraries[itin_id] = itin


def get_itinerary_summary(itinerary: Itinerary) -> dict:
    """Generate a concise summary of itinerary for quick reference."""
    return {
        "title": itinerary.title,
        "duration": f"{itinerary.start_date} to {itinerary.end_date}",
        "leg_count": len(itinerary.legs),
        "reservation_count": len(itinerary.reservations),
        "total_cost": round(itinerary.total_cost(), 2),
        "budget": itinerary.budget,
        "budget_remaining": round(itinerary.remaining_budget(), 2) if itinerary.remaining_budget() is not None else None,
        "budget_exceeded": itinerary.is_budget_exceeded(),
        "travelers": len(itinerary.travelers),
        "upcoming_count": len(itinerary.upcoming_reservations()),
    }
