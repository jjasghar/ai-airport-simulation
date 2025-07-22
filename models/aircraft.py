"""
Aircraft model for the AI Airport Simulation.

This module defines the Aircraft class and related enums that represent
individual aircraft in the simulation, including their state, properties,
and behavior logic.
"""

import math
import random
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Optional

from .position import Position


class AircraftState(Enum):
    """
    Enumeration of possible aircraft states in the simulation.
    
    The aircraft state determines the current phase of operation and
    governs movement, fuel consumption, and available actions.
    """
    APPROACHING = "approaching"        # Aircraft is inbound to the airport
    LANDING = "landing"               # Aircraft is executing landing sequence
    GO_AROUND = "go_around"           # Aircraft aborting landing and climbing out
    TAXIING_TO_GATE = "taxiing_to_gate"  # Aircraft moving from runway to gate
    AT_GATE = "at_gate"              # Aircraft parked at gate
    BOARDING_DEBOARDING = "boarding_deboarding"  # Aircraft boarding/deboarding passengers
    TAXIING_TO_RUNWAY = "taxiing_to_runway"  # Aircraft moving from gate to runway
    TAKING_OFF = "taking_off"        # Aircraft executing takeoff sequence
    HOLDING = "holding"              # Aircraft in holding pattern
    CRASHED = "crashed"              # Aircraft has crashed
    DEPARTED = "departed"            # Aircraft has left the simulation


class AircraftType(Enum):
    """
    Aircraft types with different characteristics and capacities.
    
    Each type has different passenger capacities, fuel consumption rates,
    and operational characteristics that affect simulation behavior.
    """
    BOEING_737 = "Boeing 737"        # 150-180 passengers
    BOEING_777 = "Boeing 777"        # 300-400 passengers  
    AIRBUS_A320 = "Airbus A320"     # 140-180 passengers
    AIRBUS_A380 = "Airbus A380"     # 500-850 passengers


@dataclass
class Aircraft:
    """
    Represents an individual aircraft in the simulation.
    
    Each aircraft has position, state, fuel level, assignments, and behavior
    properties that govern its movement and interactions within the airport
    environment.
    
    Attributes:
        id (str): Unique identifier for the aircraft
        callsign (str): Flight callsign (e.g., "FL12345678")
        aircraft_type (AircraftType): Type of aircraft
        position (Position): Current position in simulation space
        target_position (Position): Where the aircraft is moving towards
        state (AircraftState): Current operational state
        fuel (float): Fuel level as percentage (0-100)
        assigned_runway (Optional[int]): ID of assigned runway
        assigned_gate (Optional[int]): ID of assigned gate
        speed (float): Movement speed in pixels per second
        passenger_count (int): Number of passengers aboard
        gate_arrival_time (Optional[float]): When aircraft arrived at gate
    """
    
    # Core identification
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    callsign: str = field(default_factory=lambda: f"FL{random.randint(10000000, 99999999):08x}")
    aircraft_type: AircraftType = field(default_factory=lambda: random.choice(list(AircraftType)))
    
    # Position and movement
    position: Position = field(default_factory=lambda: Position(0, 0))
    target_position: Position = field(default_factory=lambda: Position(0, 0))
    speed: float = 150.0  # pixels per second
    
    # Operational state
    state: AircraftState = AircraftState.APPROACHING
    fuel: float = field(default_factory=lambda: random.uniform(10.0, 12.0))  # Landing fuel %
    
    # Airport assignments
    assigned_runway: Optional[int] = None
    assigned_gate: Optional[int] = None
    
    # Passenger information
    passenger_count: int = field(default_factory=lambda: 0)
    
    # Timing information
    gate_arrival_time: Optional[float] = None
    
    # Fuel refilling information
    fuel_at_arrival: Optional[float] = None  # Fuel level when aircraft arrived at gate
    target_fuel_level: Optional[float] = None  # Target fuel level for departure
    refuel_start_time: Optional[float] = None  # When refueling started
    refuel_completed: bool = False  # Whether refueling is finished
    
    # Crash information
    crash_reason: Optional[str] = None

    def __post_init__(self):
        """Initialize derived attributes after dataclass creation."""
        # Set passenger count based on aircraft type if not already set
        if self.passenger_count == 0:
            self.passenger_count = self._generate_passenger_count()
    
    def _generate_passenger_count(self) -> int:
        """
        Generate realistic passenger count based on aircraft type.
        
        Returns:
            int: Number of passengers for this aircraft type
        """
        passenger_ranges = {
            AircraftType.BOEING_737: (120, 180),    # Typical 737 capacity
            AircraftType.AIRBUS_A320: (140, 190),   # Typical A320 capacity  
            AircraftType.BOEING_777: (300, 400),    # Typical 777 capacity
            AircraftType.AIRBUS_A380: (500, 850),   # Typical A380 capacity
        }
        
        min_passengers, max_passengers = passenger_ranges.get(
            self.aircraft_type, (100, 200)  # Default range
        )
        return random.randint(min_passengers, max_passengers)
    
    def start_gate_operations(self, current_time: float):
        """
        Start gate operations including boarding/deboarding and refueling.
        
        Args:
            current_time (float): Current simulation time
        """
        self.gate_arrival_time = current_time
        self.fuel_at_arrival = self.fuel
        
        # Determine target fuel level (50-100% as specified)
        # More likely to get higher fuel levels, with some preference for full tanks
        if random.random() < 0.3:  # 30% chance of full fuel
            self.target_fuel_level = 100.0
        elif random.random() < 0.5:  # 50% chance of 80-99%
            self.target_fuel_level = random.uniform(80.0, 99.0)
        else:  # 20% chance of 50-79%
            self.target_fuel_level = random.uniform(50.0, 79.0)
        
        # Refueling starts immediately (parallel with passenger operations)
        self.refuel_start_time = current_time
        self.refuel_completed = False
        
        print(f"GATE OPERATIONS: {self.callsign} starting refuel from {self.fuel:.1f}% to {self.target_fuel_level:.1f}%")
    
    def update_refueling(self, current_time: float, dt: float):
        """
        Update fuel refilling process during gate operations.
        
        Args:
            current_time (float): Current simulation time
            dt (float): Time step in seconds
        """
        if (self.state == AircraftState.BOARDING_DEBOARDING and 
            not self.refuel_completed and 
            self.refuel_start_time is not None and
            self.target_fuel_level is not None):
            
            # Calculate refuel time based on fuel amount needed
            fuel_needed = max(0, self.target_fuel_level - self.fuel_at_arrival)
            
            # Realistic refuel rate: approximately 1% per second for small amounts,
            # slower for large amounts to simulate fuel truck operations
            if fuel_needed <= 20.0:  # Small refuel (top-off)
                refuel_time = fuel_needed / 1.0  # 1% per second
            elif fuel_needed <= 50.0:  # Medium refuel
                refuel_time = fuel_needed / 0.8  # 0.8% per second
            else:  # Large refuel (nearly empty to full)
                refuel_time = fuel_needed / 0.6  # 0.6% per second
            
            # Minimum refuel time of 30 seconds (safety and connection time)
            refuel_time = max(30.0, refuel_time)
            
            time_refueling = current_time - self.refuel_start_time
            
            if time_refueling >= refuel_time:
                # Refueling complete
                self.fuel = self.target_fuel_level
                self.refuel_completed = True
                print(f"REFUEL COMPLETE: {self.callsign} refueled to {self.fuel:.1f}% in {time_refueling:.1f}s")
            else:
                # Refueling in progress - gradually increase fuel
                refuel_progress = time_refueling / refuel_time
                current_fuel_target = self.fuel_at_arrival + (fuel_needed * refuel_progress)
                self.fuel = min(self.target_fuel_level, current_fuel_target)
    
    def get_refuel_time(self) -> float:
        """
        Calculate total time needed for refueling based on target fuel level.
        
        Returns:
            float: Time in seconds required for refueling
        """
        if self.fuel_at_arrival is None or self.target_fuel_level is None:
            return 0.0
        
        fuel_needed = max(0, self.target_fuel_level - self.fuel_at_arrival)
        
        if fuel_needed <= 20.0:
            refuel_time = fuel_needed / 1.0
        elif fuel_needed <= 50.0:
            refuel_time = fuel_needed / 0.8
        else:
            refuel_time = fuel_needed / 0.6
        
        return max(30.0, refuel_time)
    
    def get_total_gate_time(self) -> float:
        """
        Calculate total time needed at gate including boarding and refueling.
        
        Both boarding and refueling happen in parallel, so gate time is the
        maximum of boarding time and refueling time.
        
        Returns:
            float: Total time in seconds required at gate
        """
        boarding_time = self.get_boarding_time()
        refuel_time = self.get_refuel_time()
        
        # Gate operations take the longer of boarding or refueling
        # Plus a 30-second buffer for final preparations
        return max(boarding_time, refuel_time) + 30.0
    
    def is_ready_for_departure(self, current_time: float) -> bool:
        """
        Check if aircraft is ready for departure (both boarding and refueling complete).
        
        Args:
            current_time (float): Current simulation time
            
        Returns:
            bool: True if aircraft is ready to depart
        """
        if self.gate_arrival_time is None:
            return False
        
        total_gate_time = self.get_total_gate_time()
        time_at_gate = current_time - self.gate_arrival_time
        
        # Ready if both time requirements are met and refueling is complete
        return (time_at_gate >= total_gate_time and 
                (self.refuel_completed or self.target_fuel_level is None))
    
    def get_gate_status(self, current_time: float) -> str:
        """
        Get current gate operation status for display.
        
        Args:
            current_time (float): Current simulation time
            
        Returns:
            str: Human-readable status of gate operations
        """
        if self.gate_arrival_time is None:
            return "Not at gate"
        
        time_at_gate = current_time - self.gate_arrival_time
        boarding_time = self.get_boarding_time()
        refuel_time = self.get_refuel_time()
        
        boarding_complete = time_at_gate >= boarding_time
        
        status_parts = []
        
        # Boarding status
        if boarding_complete:
            status_parts.append(f"Boarding: ✓ Complete")
        else:
            remaining_boarding = boarding_time - time_at_gate
            status_parts.append(f"Boarding: {remaining_boarding:.0f}s remaining")
        
        # Refueling status
        if self.refuel_completed:
            status_parts.append(f"Refuel: ✓ Complete ({self.fuel:.1f}%)")
        elif self.target_fuel_level is not None:
            remaining_refuel = refuel_time - (current_time - self.refuel_start_time) if self.refuel_start_time else refuel_time
            status_parts.append(f"Refuel: {remaining_refuel:.0f}s remaining → {self.target_fuel_level:.1f}%")
        else:
            status_parts.append("Refuel: Not started")
        
        return " | ".join(status_parts)

    def update(self, dt: float) -> None:
        """
        Update aircraft position, fuel consumption, and other time-based changes.
        
        Args:
            dt (float): Time step in seconds since last update
        """
        # Move towards target position
        if self.position.distance_to(self.target_position) > 5:
            direction_x = self.target_position.x - self.position.x
            direction_y = self.target_position.y - self.position.y
            distance = math.sqrt(direction_x**2 + direction_y**2)
            
            if distance > 0:
                # Normalize direction and apply speed
                direction_x /= distance
                direction_y /= distance
                
                # Calculate movement distance for this frame
                movement_distance = self.speed * dt
                movement_distance = min(movement_distance, distance)  # Don't overshoot
                
                new_x = self.position.x + direction_x * movement_distance
                new_y = self.position.y + direction_y * movement_distance
                
                new_position = Position(new_x, new_y)
            else:
                new_position = self.position
        else:
            new_position = self.position
        
        # Clamp aircraft to screen bounds (except during takeoff where they may leave)
        if self.state != AircraftState.TAKING_OFF:
            # Import here to avoid circular import
            from config import get_config
            config = get_config()
            margin = 20  # Keep aircraft at least 20 pixels from screen edge
            new_position.x = max(margin, min(config.airport.airport_width - margin, new_position.x))
            new_position.y = max(margin, min(config.airport.airport_height - margin, new_position.y))
        
        self.position = new_position
    
        # Handle fuel consumption and refueling
        if self.state == AircraftState.BOARDING_DEBOARDING:
            # During boarding/deboarding, handle refueling but no fuel consumption (engines off)
            # Note: refueling is handled by the state manager calling update_refueling()
            pass
        else:
            # Normal fuel consumption for other states
            self._consume_fuel(dt)

    def _consume_fuel(self, dt: float) -> None:
        """
        Consume fuel based on current aircraft state and operational phase.
        
        Different states consume fuel at different rates based on real-world
        aircraft fuel consumption patterns.
        
        Args:
            dt (float): Time step in seconds
        """
        # Fuel consumption rates per second as percentage of total fuel
        consumption_rates = {
            AircraftState.APPROACHING: 0.15,      # 15% of fuel during approach phase
            AircraftState.LANDING: 0.10,          # 10% during landing
            AircraftState.GO_AROUND: 0.25,        # 25% during go-around (high power climb)
            AircraftState.TAXIING_TO_GATE: 0.02,  # 2% while taxiing
            AircraftState.AT_GATE: 0.0,           # No fuel consumption at gate
            AircraftState.BOARDING_DEBOARDING: 0.0, # No fuel consumption during boarding
            AircraftState.TAXIING_TO_RUNWAY: 0.02,# 2% while taxiing
            AircraftState.TAKING_OFF: 0.30,       # 30% during takeoff
            AircraftState.CRASHED: 0.0,           # No consumption when crashed
            AircraftState.DEPARTED: 0.0           # No consumption after departure
        }
        
        # Special handling for HOLDING state based on whether aircraft is airborne or ground
        if self.state == AircraftState.HOLDING:
            if hasattr(self, 'waiting_for_runway') and self.waiting_for_runway:
                # Ground holding (waiting for takeoff runway) - minimal fuel consumption
                rate = 0.05  # 0.05% per second (engines idling on ground)
            else:
                # Airborne holding pattern - moderate fuel consumption
                rate = 0.20  # 0.20% per second (reduced from 0.5% - more realistic)
        else:
            rate = consumption_rates.get(self.state, 0.0)
        
        self.fuel = max(0.0, self.fuel - rate * dt)

    def can_safely_hold(self, holding_time_minutes: float = 10.0) -> bool:
        """
        Check if aircraft has enough fuel to safely enter a holding pattern.
        
        Args:
            holding_time_minutes (float): Expected holding time in minutes
            
        Returns:
            bool: True if aircraft can safely hold for the specified time
        """
        if self.state == AircraftState.HOLDING:
            # Aircraft already in holding - check if it can continue
            if hasattr(self, 'waiting_for_runway') and self.waiting_for_runway:
                # Ground holding - very low fuel consumption
                fuel_needed = 0.05 * (holding_time_minutes * 60) + 5.0  # 5% safety margin
            else:
                # Airborne holding - higher fuel consumption
                fuel_needed = 0.20 * (holding_time_minutes * 60) + 10.0  # 10% safety margin
        else:
            # Aircraft considering entering holding
            if hasattr(self, 'waiting_for_runway'):
                # Would be ground holding
                fuel_needed = 0.05 * (holding_time_minutes * 60) + 5.0
            else:
                # Would be airborne holding
                fuel_needed = 0.20 * (holding_time_minutes * 60) + 10.0
        
        return self.fuel >= fuel_needed
    
    def get_safe_holding_time(self) -> float:
        """
        Calculate maximum safe holding time in minutes based on current fuel.
        
        Returns:
            float: Maximum safe holding time in minutes
        """
        if hasattr(self, 'waiting_for_runway') and self.waiting_for_runway:
            # Ground holding calculation
            safety_margin = 5.0  # Keep 5% fuel as safety margin
            available_fuel = max(0, self.fuel - safety_margin)
            fuel_rate_per_minute = 0.05 * 60  # 0.05% per second -> per minute
        else:
            # Airborne holding calculation
            safety_margin = 10.0  # Keep 10% fuel as safety margin
            available_fuel = max(0, self.fuel - safety_margin)
            fuel_rate_per_minute = 0.20 * 60  # 0.20% per second -> per minute
        
        if fuel_rate_per_minute > 0:
            return available_fuel / fuel_rate_per_minute
        else:
            return float('inf')  # Infinite holding time if no fuel consumption
    
    def get_fuel_priority(self) -> int:
        """
        Get fuel priority level for aircraft scheduling decisions.
        
        Returns:
            int: Priority level (higher number = higher priority)
                 5 = Critical fuel emergency (< 10%)
                 4 = Low fuel urgent (< 15%)  
                 3 = Low fuel warning (< 25%)
                 2 = Moderate fuel (25-50%)
                 1 = Good fuel (> 50%)
        """
        if self.fuel < 10.0:
            return 5  # Critical fuel emergency
        elif self.fuel < 15.0:
            return 4  # Low fuel urgent
        elif self.fuel < 25.0:
            return 3  # Low fuel warning
        elif self.fuel < 50.0:
            return 2  # Moderate fuel
        else:
            return 1  # Good fuel

    def is_low_fuel(self) -> bool:
        """
        Check if aircraft has low fuel requiring priority handling.
        
        Returns:
            bool: True if fuel is below 25% (low fuel threshold)
        """
        return self.fuel < 25.0

    def is_critical_fuel(self) -> bool:
        """
        Check if aircraft has critical fuel requiring emergency landing.
        
        Returns:
            bool: True if fuel is below 15% (critical fuel threshold)
        """
        return self.fuel < 15.0

    def distance_to(self, other: 'Aircraft') -> float:
        """
        Calculate distance to another aircraft.
        
        Args:
            other (Aircraft): The other aircraft to measure distance to
            
        Returns:
            float: Distance in pixels between aircraft positions
        """
        return self.position.distance_to(other.position)

    def check_collision(self, other: 'Aircraft', collision_distance: float = 10.0) -> bool:
        """
        Check if this aircraft is colliding with another aircraft.
        
        Args:
            other (Aircraft): The other aircraft to check collision with
            collision_distance (float): Minimum distance considered a collision
            
        Returns:
            bool: True if aircraft are colliding
        """
        # Don't check collisions for crashed or departed aircraft
        if self.state == AircraftState.CRASHED or other.state == AircraftState.CRASHED:
            return False
        if self.state == AircraftState.DEPARTED or other.state == AircraftState.DEPARTED:
            return False
        
        # Aircraft at gates don't collide with each other (including boarding/deboarding)
        gate_states = [AircraftState.AT_GATE, AircraftState.BOARDING_DEBOARDING]
        if self.state in gate_states and other.state in gate_states:
            return False
        
        # Individual aircraft at gates are also protected from any collisions
        if self.state in gate_states or other.state in gate_states:
            # Only allow collision if both are mobile states
            mobile_states = [
                AircraftState.APPROACHING, AircraftState.LANDING, AircraftState.GO_AROUND,
                AircraftState.TAXIING_TO_GATE, AircraftState.TAXIING_TO_RUNWAY, 
                AircraftState.TAKING_OFF, AircraftState.HOLDING
            ]
            if self.state not in mobile_states or other.state not in mobile_states:
                return False
        
        return self.distance_to(other) <= collision_distance

    def is_collision_imminent(self, other: 'Aircraft', warning_distance: float = 500.0) -> bool:
        """
        Check if a collision is imminent with another aircraft.
        
        This method detects potential collisions before they happen, allowing
        for collision avoidance maneuvers.
        
        Args:
            other (Aircraft): The other aircraft to check against
            warning_distance (float): Distance threshold for collision warning
            
        Returns:
            bool: True if collision is imminent
        """
        # Skip checks for non-collision states
        if self.state == AircraftState.CRASHED or other.state == AircraftState.CRASHED:
            return False
        if self.state == AircraftState.DEPARTED or other.state == AircraftState.DEPARTED:
            return False
        if self.state == AircraftState.AT_GATE and other.state == AircraftState.AT_GATE:
            return False
        
        # Don't trigger avoidance for aircraft very close to completing landing sequence
        if self.state == AircraftState.LANDING and self.position.distance_to(self.target_position) < 20:
            return False
        if other.state == AircraftState.LANDING and other.position.distance_to(other.target_position) < 20:
            return False
        
        # Only check for moving aircraft
        moving_states = [
            AircraftState.APPROACHING, AircraftState.HOLDING, AircraftState.LANDING, AircraftState.GO_AROUND,
            AircraftState.TAXIING_TO_GATE, AircraftState.TAXIING_TO_RUNWAY, AircraftState.TAKING_OFF
        ]
        
        if self.state not in moving_states or other.state not in moving_states:
            return False
        
        return self.distance_to(other) <= warning_distance

    def get_boarding_time(self) -> float:
        """
        Calculate boarding/deboarding time based on passenger count.
        
        Larger aircraft with more passengers take longer to board and deboard.
        
        Returns:
            float: Time in seconds required for boarding/deboarding
        """
        # Base time of 30 seconds plus 0.1 seconds per passenger
        return 30.0 + (self.passenger_count * 0.1)

    def get_status_info(self) -> Dict[str, str]:
        """
        Get formatted status information for display purposes.
        
        Returns:
            Dict[str, str]: Dictionary containing formatted status fields
        """
        return {
            'callsign': self.callsign,
            'type': self.aircraft_type.value,
            'state': self.state.value.replace('_', ' ').title(),
            'fuel': f"{self.fuel:.1f}%",
            'position': f"({self.position.x:.0f}, {self.position.y:.0f})",
            'runway': str(self.assigned_runway) if self.assigned_runway is not None else "None",
            'gate': str(self.assigned_gate) if self.assigned_gate is not None else "None",
            'passengers': str(self.passenger_count)
        }

    def __str__(self) -> str:
        """String representation of the aircraft."""
        return f"{self.callsign} [{self.aircraft_type.value}] - {self.state.value} ({self.fuel:.1f}% fuel)"

    def __repr__(self) -> str:
        """Detailed string representation for debugging."""
        return (f"Aircraft(id={self.id}, callsign={self.callsign}, "
                f"type={self.aircraft_type.value}, state={self.state.value}, "
                f"fuel={self.fuel:.1f}%)") 