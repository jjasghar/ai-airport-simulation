"""
Flight scheduling system for the AI Airport Simulation.

This module handles the generation of new flights, aircraft spawning,
and manages the timing and distribution of airport traffic with advanced
traffic flow management to prevent collision scenarios.
"""

import math
import random
from typing import List

from config import get_config
from models.aircraft import Aircraft, AircraftType, AircraftState
from models.airport import Airport, Flight
from models.position import Position


class FlightScheduler:
    """
    Manages flight arrivals and departures for the airport simulation.
    
    The FlightScheduler is responsible for:
    - Generating realistic flight schedules
    - Spawning aircraft with appropriate positioning and spacing
    - Managing spawn rates based on airport capacity
    - Balancing arrival and departure traffic
    - Traffic flow management to prevent collision scenarios
    """
    
    def __init__(self, airport: Airport):
        """
        Initialize the flight scheduler.
        
        Args:
            airport (Airport): The airport instance to schedule flights for
        """
        self.airport = airport
        self.scheduled_flights: List[Flight] = []
        self.last_spawn_time = 0
        
        # Traffic flow management
        self.last_spawn_sectors: List[int] = []  # Track last spawn sectors to avoid clustering
        self.min_spawn_separation = 300.0  # Minimum distance between new spawns and existing aircraft
        self.spawn_attempt_limit = 10  # Maximum attempts to find safe spawn position
        
        # Airport codes for realistic flight generation
        self.origins = ["JFK", "LAX", "ORD", "DFW", "DEN", "SFO", "SEA", "MIA"]
        self.destinations = ["ATL", "BOS", "LAS", "PHX", "IAH", "CLT", "MSP", "DTW"]
        self.aircraft_types = ["Boeing 737", "Airbus A320", "Boeing 777", "Airbus A380"]
        
    def generate_flight(self, flight_type: str = "arrival") -> Flight:
        """
        Generate a new flight with realistic details.
        
        Args:
            flight_type (str): Either "arrival" or "departure"
            
        Returns:
            Flight: A newly generated flight object
        """
        flight = Flight(
            origin=random.choice(self.origins) if flight_type == "arrival" else "HOME",
            destination=random.choice(self.destinations) if flight_type == "departure" else "HOME",
            scheduled_time=self.airport.current_time,
            flight_type=flight_type,
            aircraft_type=random.choice(self.aircraft_types)
        )
        return flight
    
    def spawn_aircraft(self, flight: Flight) -> Aircraft:
        """
        Spawn an aircraft for a given flight with appropriate positioning and state.
        
        Args:
            flight (Flight): The flight to create an aircraft for
            
        Returns:
            Aircraft: The spawned aircraft ready for simulation
        """
        # Convert string aircraft type to enum
        aircraft_type_enum = AircraftType(flight.aircraft_type)
        
        aircraft = Aircraft(
            callsign=flight.callsign,
            aircraft_type=aircraft_type_enum
        )
        
        if flight.flight_type == "arrival":
            aircraft = self._spawn_arrival_aircraft_safe(aircraft)
        else:
            aircraft = self._spawn_departure_aircraft(aircraft)
            
        return aircraft
    
    def _spawn_arrival_aircraft_safe(self, aircraft: Aircraft) -> Aircraft:
        """
        Configure aircraft for arrival with safe positioning to prevent clustering.
        
        Args:
            aircraft (Aircraft): The aircraft to configure
            
        Returns:
            Aircraft: The configured arrival aircraft
        """
        # Get list of existing aircraft for conflict checking
        existing_aircraft = [a for a in self.airport.aircraft 
                           if a.state not in [AircraftState.CRASHED, AircraftState.DEPARTED]]
        
        # Try multiple spawn attempts to find safe position
        for attempt in range(self.spawn_attempt_limit):
            # Use sector-based spawning to distribute aircraft evenly
            spawn_position = self._get_safe_spawn_position(existing_aircraft, attempt)
            
            if spawn_position:
                aircraft.position = spawn_position
                aircraft.state = AircraftState.APPROACHING
                
                # Set target to airport center with some randomization
                center_x = self.airport.config.airport.airport_width / 2
                center_y = self.airport.config.airport.airport_height / 2
                
                # Add slight offset to target to spread approach patterns
                target_offset_x = random.randint(-50, 50)
                target_offset_y = random.randint(-50, 50)
                
                aircraft.target_position = Position(
                    center_x + target_offset_x,
                    center_y + target_offset_y
                )
                
                # Arriving aircraft have sufficient fuel for safe landing (25-35%)
                # This allows for some maneuvering without immediate crash risk
                aircraft.fuel = random.uniform(25.0, 35.0)
                
                print(f"SAFE SPAWN: {aircraft.callsign} at ({spawn_position.x:.0f},{spawn_position.y:.0f}) attempt {attempt + 1}")
                return aircraft
        
        # If no safe position found after all attempts, use emergency spawn
        print(f"WARNING: Emergency spawn for {aircraft.callsign} - no safe position found")
        return self._emergency_spawn_arrival(aircraft)
    
    def _get_safe_spawn_position(self, existing_aircraft: List[Aircraft], attempt: int) -> Position:
        """
        Get a safe spawn position that maintains separation from existing aircraft.
        
        Args:
            existing_aircraft: List of existing aircraft to avoid
            attempt: Current spawn attempt number
            
        Returns:
            Position: Safe spawn position or None if no safe position found
        """
        center_x = self.airport.config.airport.airport_width / 2
        center_y = self.airport.config.airport.airport_height / 2
        
        # Define spawn sectors around the airport (8 sectors)
        total_sectors = 8
        sector_angle = 2 * math.pi / total_sectors
        
        # Choose sector based on attempt and recent spawn history
        available_sectors = list(range(total_sectors))
        
        # Remove recently used sectors to encourage distribution
        for recent_sector in self.last_spawn_sectors[-3:]:  # Avoid last 3 sectors
            if recent_sector in available_sectors:
                available_sectors.remove(recent_sector)
        
        # If no sectors available, use all sectors
        if not available_sectors:
            available_sectors = list(range(total_sectors))
        
        # Choose sector (with some randomness but prefer less used sectors)
        if attempt < 3:
            # First few attempts: use preferred sectors
            sector = random.choice(available_sectors)
        else:
            # Later attempts: try any sector
            sector = random.randint(0, total_sectors - 1)
        
        # Calculate spawn position in chosen sector
        base_angle = sector * sector_angle
        angle_variation = random.uniform(-sector_angle/4, sector_angle/4)  # Add some randomness within sector
        spawn_angle = base_angle + angle_variation
        
        # Vary spawn distance based on attempt
        base_distance = 450
        distance_variation = random.uniform(-50, 100) + (attempt * 20)  # Increase distance on later attempts
        spawn_distance = base_distance + distance_variation
        
        spawn_x = center_x + math.cos(spawn_angle) * spawn_distance
        spawn_y = center_y + math.sin(spawn_angle) * spawn_distance
        
        # Clamp to screen bounds
        margin = 50
        spawn_x = max(margin, min(self.airport.config.airport.airport_width - margin, spawn_x))
        spawn_y = max(margin, min(self.airport.config.airport.airport_height - margin, spawn_y))
        
        spawn_position = Position(spawn_x, spawn_y)
        
        # Check if position is safe from existing aircraft
        if self._is_spawn_position_safe(spawn_position, existing_aircraft):
            # Update spawn sector history
            self.last_spawn_sectors.append(sector)
            if len(self.last_spawn_sectors) > 5:  # Keep history of last 5 spawns
                self.last_spawn_sectors.pop(0)
            
            return spawn_position
        
        return None
    
    def _is_spawn_position_safe(self, position: Position, existing_aircraft: List[Aircraft]) -> bool:
        """
        Check if spawn position is safe from existing aircraft.
        
        Args:
            position: Position to check
            existing_aircraft: List of existing aircraft
            
        Returns:
            bool: True if position is safe
        """
        for aircraft in existing_aircraft:
            # Check distance to current position
            if position.distance_to(aircraft.position) < self.min_spawn_separation:
                return False
            
            # Check distance to target position (where aircraft is heading)
            if hasattr(aircraft, 'target_position'):
                if position.distance_to(aircraft.target_position) < self.min_spawn_separation * 0.7:
                    return False
        
        return True
    
    def _emergency_spawn_arrival(self, aircraft: Aircraft) -> Aircraft:
        """
        Emergency spawn for arrival aircraft when no safe position is found.
        
        Args:
            aircraft: Aircraft to spawn
            
        Returns:
            Aircraft: Configured aircraft with emergency spawn position
        """
        # Find the position with maximum distance from all other aircraft
        center_x = self.airport.config.airport.airport_width / 2
        center_y = self.airport.config.airport.airport_height / 2
        
        best_position = Position(center_x + 400, center_y)  # Default far position
        best_min_distance = 0
        
        # Sample positions around the perimeter
        for angle in [0, math.pi/4, math.pi/2, 3*math.pi/4, math.pi, 5*math.pi/4, 3*math.pi/2, 7*math.pi/4]:
            for distance in [400, 500, 600]:
                x = center_x + math.cos(angle) * distance
                y = center_y + math.sin(angle) * distance
                
                # Clamp to bounds
                margin = 30
                x = max(margin, min(self.airport.config.airport.airport_width - margin, x))
                y = max(margin, min(self.airport.config.airport.airport_height - margin, y))
                
                candidate_pos = Position(x, y)
                
                # Find minimum distance to any existing aircraft
                min_distance = float('inf')
                for other_aircraft in self.airport.aircraft:
                    if other_aircraft.state not in [AircraftState.CRASHED, AircraftState.DEPARTED]:
                        dist = candidate_pos.distance_to(other_aircraft.position)
                        min_distance = min(min_distance, dist)
                
                # Update best position if this has better separation
                if min_distance > best_min_distance:
                    best_min_distance = min_distance
                    best_position = candidate_pos
        
        aircraft.position = best_position
        aircraft.state = AircraftState.APPROACHING
        aircraft.target_position = Position(center_x, center_y)
        aircraft.fuel = random.uniform(25.0, 35.0)
        
        return aircraft
    
    def _spawn_departure_aircraft(self, aircraft: Aircraft) -> Aircraft:
        """
        Configure aircraft for departure by placing at an available gate.
        
        Args:
            aircraft (Aircraft): The aircraft to configure
            
        Returns:
            Aircraft: The configured departure aircraft
        """
        gate = self.airport.get_available_gate()
        if gate:
            aircraft.position = Position(gate.position.x, gate.position.y)
            aircraft.assigned_gate = gate.id
            aircraft.state = AircraftState.BOARDING_DEBOARDING  # Start in boarding state for refueling
            gate.occupied_by = aircraft.id
            
            # Departing aircraft start with partial fuel (need refueling)
            # This simulates aircraft arriving from previous flight needing refuel
            aircraft.fuel = random.uniform(15.0, 40.0)  # 15-40% fuel remaining from previous flight
            
            # Start gate operations immediately for departure aircraft
            aircraft.start_gate_operations(self.airport.current_time)
        
        return aircraft
    
    def update(self, dt: float):
        """
        Update flight scheduling and spawn new aircraft as needed.
        
        This method manages the timing of new aircraft spawns based on:
        - Dynamic spawn rate configuration
        - Current airport capacity
        - Traffic balance (70% arrivals, 30% departures)
        - Traffic flow management to prevent clustering
        
        Args:
            dt (float): Time step in seconds since last update
        """
        config = get_config()
        
        # Get spawn rate from configuration
        dynamic_spawn_rate = getattr(config.simulation, 'spawn_rate', 1.0) if hasattr(config, 'simulation') else 1.0
        
        # Adjust spawn rate based on current traffic density to prevent overcrowding
        active_aircraft = [a for a in self.airport.aircraft 
                         if a.state not in [AircraftState.CRASHED, AircraftState.DEPARTED]]
        
        # Reduce spawn rate if airspace is crowded
        airspace_density = len(active_aircraft) / 20.0  # Normalize to typical max aircraft
        if airspace_density > 0.7:  # If more than 70% full
            dynamic_spawn_rate *= 0.5  # Reduce spawn rate by half
            print(f"TRAFFIC CONTROL: Reducing spawn rate due to high density ({len(active_aircraft)} aircraft)")
        elif airspace_density > 0.5:  # If more than 50% full
            dynamic_spawn_rate *= 0.75  # Reduce spawn rate by 25%
        
        spawn_interval = 1.0 / dynamic_spawn_rate
        
        # Check if it's time to spawn a new aircraft
        if (self.airport.current_time - self.last_spawn_time) > spawn_interval:
            max_aircraft = getattr(config.simulation, 'max_aircraft', 20) if hasattr(config, 'simulation') else 20
            
            if len(self.airport.aircraft) < max_aircraft:
                # Balance traffic: 70% arrivals, 30% departures
                flight_type = "arrival" if random.random() < 0.7 else "departure"
                
                # Generate and spawn the aircraft
                flight = self.generate_flight(flight_type)
                aircraft = self.spawn_aircraft(flight)
                self.airport.add_aircraft(aircraft)
                
                # Update spawn timing
                self.last_spawn_time = self.airport.current_time
                
                print(f"SPAWN: {aircraft.callsign} [{aircraft.aircraft_type.value}] - {flight_type.upper()}")
    
    def get_traffic_density(self) -> float:
        """
        Calculate current traffic density in the airspace.
        
        Returns:
            float: Traffic density ratio (0.0 to 1.0+)
        """
        active_aircraft = [a for a in self.airport.aircraft 
                         if a.state not in [AircraftState.CRASHED, AircraftState.DEPARTED]]
        
        max_safe_aircraft = 15  # Safe capacity for the airspace size
        return len(active_aircraft) / max_safe_aircraft
    
    def get_airspace_congestion_zones(self) -> List[tuple]:
        """
        Identify congested areas in the airspace.
        
        Returns:
            List[tuple]: List of (position, aircraft_count) for congested zones
        """
        # Divide airspace into grid zones and count aircraft per zone
        zone_size = 200  # 200x200 pixel zones
        zones = {}
        
        for aircraft in self.airport.aircraft:
            if aircraft.state not in [AircraftState.CRASHED, AircraftState.DEPARTED]:
                zone_x = int(aircraft.position.x // zone_size)
                zone_y = int(aircraft.position.y // zone_size)
                zone_key = (zone_x, zone_y)
                
                if zone_key not in zones:
                    zones[zone_key] = []
                zones[zone_key].append(aircraft)
        
        # Return zones with more than 2 aircraft (congested)
        congested_zones = []
        for (zone_x, zone_y), aircraft_list in zones.items():
            if len(aircraft_list) > 2:
                center_x = (zone_x + 0.5) * zone_size
                center_y = (zone_y + 0.5) * zone_size
                congested_zones.append((Position(center_x, center_y), len(aircraft_list)))
        
        return congested_zones 