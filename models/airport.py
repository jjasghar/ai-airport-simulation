"""
Airport infrastructure models for the AI Airport Simulation.

This module defines the Airport, Runway, and Gate classes that represent
the physical infrastructure and operational components of the airport
in the simulation.
"""

import random
import uuid
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from enum import Enum

from .position import Position
from .aircraft import Aircraft, AircraftState, AircraftType


class RunwayState(Enum):
    """
    States a runway can be in.
    
    Runways transition between these states based on aircraft operations.
    """
    AVAILABLE = "available"
    OCCUPIED_LANDING = "occupied_landing"  
    OCCUPIED_TAKEOFF = "occupied_takeoff"


@dataclass
class Flight:
    """
    Represents a scheduled flight.
    
    This class contains information about flights arriving at or departing
    from the airport, including scheduling and aircraft type details.
    
    Attributes:
        id (str): Unique identifier for the flight
        callsign (str): Flight callsign (auto-generated if not provided)
        origin (str): Origin airport code
        destination (str): Destination airport code
        scheduled_time (float): Scheduled time in simulation time
        flight_type (str): Type of flight ('arrival' or 'departure')
        aircraft_type (str): Type of aircraft for this flight
    """
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    callsign: str = ""
    origin: str = ""
    destination: str = ""
    scheduled_time: float = 0.0
    flight_type: str = "arrival"  # arrival or departure
    aircraft_type: str = "Boeing 737"
    
    def __post_init__(self):
        """Initialize callsign if not provided."""
        if not self.callsign:
            self.callsign = f"FL{self.id}"


@dataclass
class Runway:
    """
    Represents a runway in the airport.
    
    Runways are used for aircraft takeoffs and landings. Each runway has
    a unique identifier, position coordinates, and state tracking for operations.
    
    Attributes:
        id (int): Unique identifier for the runway
        start_position (Position): Start position of the runway
        end_position (Position): End position of the runway
        width (float): Width of the runway in pixels
        state (RunwayState): Current operational state
        occupied_by (Optional[str]): ID of aircraft currently using the runway
    """
    id: int
    start_position: Position
    end_position: Position
    width: float = 40.0
    state: RunwayState = RunwayState.AVAILABLE
    occupied_by: Optional[str] = None
    
    @property
    def is_available(self) -> bool:
        """Check if the runway is available for aircraft operations."""
        return self.state == RunwayState.AVAILABLE and self.occupied_by is None
    
    @property
    def center_position(self) -> Position:
        """Get the center position of the runway."""
        return Position(
            (self.start_position.x + self.end_position.x) / 2,
            (self.start_position.y + self.end_position.y) / 2
        )
    
    @property
    def length(self) -> float:
        """Get the length of the runway."""
        return self.start_position.distance_to(self.end_position)
    
    @property
    def position(self) -> Position:
        """Get the center position for backward compatibility."""
        return self.center_position
    
    def assign_aircraft(self, aircraft_id: str) -> bool:
        """
        Assign an aircraft to this runway.
        
        Args:
            aircraft_id (str): ID of the aircraft to assign
            
        Returns:
            bool: True if assignment was successful, False if runway occupied
        """
        if self.is_available:
            self.occupied_by = aircraft_id
            return True
        return False
    
    def clear_aircraft(self) -> Optional[str]:
        """
        Clear the aircraft from this runway.
        
        Returns:
            Optional[str]: ID of the aircraft that was cleared, None if runway was empty
        """
        cleared_aircraft = self.occupied_by
        self.occupied_by = None
        return cleared_aircraft
    
    def __str__(self) -> str:
        """String representation of the runway."""
        status = f"occupied by {self.occupied_by}" if self.occupied_by else "available"
        return f"Runway {self.id} ({status})"


@dataclass
class Gate:
    """
    Represents a gate in the airport.
    
    Gates are parking positions where aircraft load/unload passengers and cargo.
    Each gate tracks occupancy and can handle aircraft boarding operations.
    
    Attributes:
        id (int): Unique identifier for the gate
        position (Position): Location of the gate in simulation space
        occupied_by (Optional[str]): ID of aircraft currently at the gate
        is_available (bool): Whether the gate is available for aircraft
    """
    id: int
    position: Position
    occupied_by: Optional[str] = None
    
    @property
    def is_available(self) -> bool:
        """Check if the gate is available for aircraft operations."""
        return self.occupied_by is None
    
    def assign_aircraft(self, aircraft_id: str) -> bool:
        """
        Assign an aircraft to this gate.
        
        Args:
            aircraft_id (str): ID of the aircraft to assign
            
        Returns:
            bool: True if assignment was successful, False if gate occupied
        """
        if self.is_available:
            self.occupied_by = aircraft_id
            return True
        return False
    
    def clear_aircraft(self) -> Optional[str]:
        """
        Clear the aircraft from this gate.
        
        Returns:
            Optional[str]: ID of the aircraft that was cleared, None if gate was empty
        """
        cleared_aircraft = self.occupied_by
        self.occupied_by = None
        return cleared_aircraft
    
    def __str__(self) -> str:
        """String representation of the gate."""
        status = f"occupied by {self.occupied_by}" if self.occupied_by else "available"
        return f"Gate {self.id} ({status})"


class Airport:
    """
    Represents the complete airport facility.
    
    The Airport class manages all airport infrastructure including runways,
    gates, and aircraft. It provides methods for aircraft operations, resource
    allocation, and status monitoring.
    
    Attributes:
        config: Configuration object containing airport settings
        runways (List[Runway]): List of available runways
        gates (List[Gate]): List of available gates
        aircraft (List[Aircraft]): List of all aircraft in the airport
        current_time (float): Current simulation time in seconds
        total_crashes (int): Total number of crashes this session
        crashed_aircraft (List[str]): List of crashed aircraft callsigns
    """
    
    def __init__(self, config):
        """
        Initialize the airport with configuration settings.
        
        Args:
            config: Configuration object containing airport settings
        """
        self.config = config
        self.current_time = 0.0
        self.total_crashes = 0
        self.crashed_aircraft: List[str] = []
        
        # Initialize runways based on configuration
        self.runways: List[Runway] = []
        self._initialize_runways()
        
        # Initialize gates based on configuration  
        self.gates: List[Gate] = []
        self._initialize_gates()
        
        # Initialize aircraft list
        self.aircraft: List[Aircraft] = []
    
    def _initialize_runways(self) -> None:
        """Initialize runways based on configuration settings."""
        runway_config = self.config.airport.runways
        runway_length = getattr(runway_config, 'length', 300) if hasattr(runway_config, 'length') else 300
        runway_width = getattr(runway_config, 'width', 40) if hasattr(runway_config, 'width') else 40
        
        for i in range(runway_config.count):
            # Position runways vertically along the left side
            runway_y = (i + 1) * (self.config.airport.airport_height / (runway_config.count + 1))
            
            # Create runway with start and end positions
            start_x = 50
            end_x = start_x + runway_length
            
            start_position = Position(start_x, runway_y)
            end_position = Position(end_x, runway_y)
            
            runway = Runway(
                id=i, 
                start_position=start_position,
                end_position=end_position,
                width=runway_width
            )
            self.runways.append(runway)
    
    def _initialize_gates(self) -> None:
        """Initialize gates based on configuration settings."""
        gate_config = self.config.airport.gates
        for i in range(gate_config.count):
            # Position gates horizontally along the top
            gate_x = (i + 1) * (self.config.airport.airport_width / (gate_config.count + 1))
            gate_position = Position(gate_x, 100)
            
            gate = Gate(id=i, position=gate_position)
            self.gates.append(gate)
    
    def get_available_runway(self) -> Optional[Runway]:
        """
        Get the first available runway.
        
        Returns:
            Optional[Runway]: Available runway, or None if all are occupied
        """
        for runway in self.runways:
            if runway.is_available:
                return runway
        return None
    
    def get_available_gate(self) -> Optional[Gate]:
        """
        Get the first available gate.
        
        Returns:
            Optional[Gate]: Available gate, or None if all are occupied
        """
        for gate in self.gates:
            if gate.is_available:
                return gate
        return None
    
    def get_runway_by_id(self, runway_id: int) -> Optional[Runway]:
        """
        Get a runway by its ID.
        
        Args:
            runway_id (int): ID of the runway to retrieve
            
        Returns:
            Optional[Runway]: The runway if found, None otherwise
        """
        for runway in self.runways:
            if runway.id == runway_id:
                return runway
        return None
    
    def get_gate_by_id(self, gate_id: int) -> Optional[Gate]:
        """
        Get a gate by its ID.
        
        Args:
            gate_id (int): ID of the gate to retrieve
            
        Returns:
            Optional[Gate]: The gate if found, None otherwise
        """
        for gate in self.gates:
            if gate.id == gate_id:
                return gate
        return None
    
    def add_aircraft(self, aircraft: Aircraft) -> None:
        """
        Add a new aircraft to the airport.
        
        Args:
            aircraft (Aircraft): The aircraft to add to the simulation
        """
        self.aircraft.append(aircraft)
    
    def remove_aircraft(self, aircraft: Aircraft) -> None:
        """
        Remove an aircraft from the airport.
        
        Args:
            aircraft (Aircraft): The aircraft to remove from the simulation
        """
        if aircraft in self.aircraft:
            self.aircraft.remove(aircraft)
    
    def spawn_aircraft(self, is_arrival: bool = True) -> Aircraft:
        """
        Spawn a new aircraft in the simulation.
        
        Args:
            is_arrival (bool): Whether the aircraft is arriving (True) or departing (False)
            
        Returns:
            Aircraft: The newly spawned aircraft
        """
        aircraft = Aircraft()
        
        if is_arrival:
            # Spawn arriving aircraft at random edge positions
            edge = random.choice(['top', 'bottom', 'left', 'right'])
            if edge == 'top':
                aircraft.position = Position(random.randint(0, self.config.airport.airport_width), 0)
            elif edge == 'bottom':
                aircraft.position = Position(random.randint(0, self.config.airport.airport_width), 
                                           self.config.airport.airport_height)
            elif edge == 'left':
                aircraft.position = Position(0, random.randint(0, self.config.airport.airport_height))
            else:  # right
                aircraft.position = Position(self.config.airport.airport_width, 
                                           random.randint(0, self.config.airport.airport_height))
            
            # Set initial target to airport center for approaching aircraft
            aircraft.target_position = Position(
                self.config.airport.airport_width / 2,
                self.config.airport.airport_height / 2
            )
            aircraft.state = AircraftState.APPROACHING
            aircraft.fuel = random.uniform(10.0, 12.0)  # Landing fuel level
        
        else:
            # Spawn departing aircraft at an available gate
            gate = self.get_available_gate()
            if gate:
                aircraft.position = Position(gate.position.x, gate.position.y)
                aircraft.target_position = Position(gate.position.x, gate.position.y)
                aircraft.state = AircraftState.AT_GATE
                aircraft.assigned_gate = gate.id
                aircraft.fuel = 100.0  # Full fuel for departure
                gate.assign_aircraft(aircraft.id)
        
        self.add_aircraft(aircraft)
        return aircraft
    
    def record_crash(self, aircraft: Aircraft, crash_cause: str) -> None:
        """
        Record an aircraft crash in the airport statistics.
        
        Args:
            aircraft (Aircraft): The crashed aircraft
            crash_cause (str): Description of the crash cause
        """
        self.total_crashes += 1
        self.crashed_aircraft.append(aircraft.callsign)
        
        # Clear aircraft from any assigned resources
        if aircraft.assigned_runway is not None:
            runway = self.get_runway_by_id(aircraft.assigned_runway)
            if runway and runway.occupied_by == aircraft.id:
                runway.clear_aircraft()
        
        if aircraft.assigned_gate is not None:
            gate = self.get_gate_by_id(aircraft.assigned_gate)
            if gate and gate.occupied_by == aircraft.id:
                gate.clear_aircraft()
    
    def get_airport_status(self) -> Dict[str, Any]:
        """
        Get comprehensive airport status information.
        
        Returns:
            Dict[str, Any]: Dictionary containing airport status data
        """
        # Count aircraft by state
        aircraft_by_state = {}
        for state in AircraftState:
            aircraft_by_state[state.value] = len([a for a in self.aircraft if a.state == state])
        
        # Count fuel emergency aircraft
        critical_fuel_count = len([a for a in self.aircraft if a.is_critical_fuel()])
        low_fuel_count = len([a for a in self.aircraft if a.is_low_fuel()])
        
        # Runway and gate availability
        available_runways = len([r for r in self.runways if r.is_available])
        available_gates = len([g for g in self.gates if g.is_available])
        
        return {
            'current_time': self.current_time,
            'total_aircraft': len(self.aircraft),
            'aircraft_by_state': aircraft_by_state,
            'runways': {
                'total': len(self.runways),
                'available': available_runways,
                'occupied': len(self.runways) - available_runways
            },
            'gates': {
                'total': len(self.gates),
                'available': available_gates,
                'occupied': len(self.gates) - available_gates
            },
            'fuel_status': {
                'critical_fuel_count': critical_fuel_count,
                'low_fuel_count': low_fuel_count
            },
            'safety': {
                'total_crashes': self.total_crashes,
                'crashed_aircraft': self.crashed_aircraft[-5:]  # Last 5 crashes
            }
        }
    
    def update(self, dt: float) -> None:
        """
        Update airport state for one simulation frame.
        
        Args:
            dt (float): Time step in seconds since last update
        """
        self.current_time += dt
        
        # Update all aircraft
        for aircraft in self.aircraft:
            aircraft.update(dt)
    
    def get_aircraft(self, aircraft_id: str) -> Optional['Aircraft']:
        """
        Get aircraft by ID.
        
        Args:
            aircraft_id (str): The ID of the aircraft to find
            
        Returns:
            Optional[Aircraft]: The aircraft if found, None otherwise
        """
        for aircraft in self.aircraft:
            if aircraft.id == aircraft_id:
                return aircraft
        return None
    
    def __str__(self) -> str:
        """String representation of the airport."""
        status = self.get_airport_status()
        return (f"Airport: {status['total_aircraft']} aircraft, "
                f"{status['runways']['available']}/{status['runways']['total']} runways available, "
                f"{status['gates']['available']}/{status['gates']['total']} gates available")
    
    def __repr__(self) -> str:
        """Detailed string representation for debugging."""
        return (f"Airport(runways={len(self.runways)}, gates={len(self.gates)}, "
                f"aircraft={len(self.aircraft)}, crashes={self.total_crashes})") 