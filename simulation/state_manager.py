"""
Aircraft state management system for the AI Airport Simulation.

This module handles all aircraft state transitions and lifecycle management
including landing, taxiing, gate operations, boarding, and departure procedures.
"""

import math
import random
from typing import List

from models.aircraft import Aircraft, AircraftState
from models.airport import Airport, RunwayState
from models.position import Position


class StateManager:
    """
    Manages aircraft state transitions and lifecycle operations.
    
    The StateManager coordinates the complete aircraft lifecycle:
    - Landing and runway operations
    - Gate assignments and taxiing
    - Boarding and deboarding procedures
    - Departure preparations and takeoffs
    - Holding patterns and waiting states
    """
    
    def __init__(self, airport: Airport):
        """
        Initialize the state management system.
        
        Args:
            airport (Airport): The airport instance to manage aircraft states for
        """
        self.airport = airport
    
    def update_aircraft_states(self, dt: float):
        """
        Update aircraft states based on their positions and targets.
        
        This method handles automatic state transitions when aircraft
        reach their target positions and manages the aircraft lifecycle.
        
        Args:
            dt (float): Time step in seconds since last update
        """
        current_time = self.airport.current_time
        
        # Update refueling for aircraft at gates
        for aircraft in self.airport.aircraft:
            if aircraft.state == AircraftState.BOARDING_DEBOARDING:
                aircraft.update_refueling(current_time, dt)
        
        # Handle position-based state transitions
        for aircraft in self.airport.aircraft:
            # Check if aircraft reached their target
            distance_to_target = aircraft.position.distance_to(aircraft.target_position)
            
            if distance_to_target < 10:  # Close enough to target
                self._handle_state_transition(aircraft)
    
    def _handle_state_transition(self, aircraft: Aircraft):
        """
        Handle state transitions when aircraft reach their targets.
        
        Args:
            aircraft (Aircraft): The aircraft that has reached its target
        """
        if aircraft.state == AircraftState.LANDING:
            self._handle_landing_completion(aircraft)
        
        elif aircraft.state == AircraftState.TAXIING_TO_GATE:
            self._handle_gate_arrival(aircraft)
        
        elif aircraft.state == AircraftState.TAXIING_TO_RUNWAY:
            self._handle_takeoff_start(aircraft)
        
        elif aircraft.state == AircraftState.TAKING_OFF:
            self._handle_takeoff_completion(aircraft)
        
        elif aircraft.state == AircraftState.GO_AROUND:
            self._handle_go_around_completion(aircraft)
    
    def _handle_landing_completion(self, aircraft: Aircraft):
        """
        Handle aircraft completing landing procedure.
        
        Args:
            aircraft (Aircraft): The aircraft that has completed landing
        """
        # Aircraft has landed - automatically assign gate if available
        gate = self.airport.get_available_gate()
        if gate:
            # Free up runway
            if aircraft.assigned_runway is not None:
                runway = self.airport.runways[aircraft.assigned_runway]
                runway.state = RunwayState.AVAILABLE
                runway.occupied_by = None
            
            # Assign gate and start taxiing
            aircraft.assigned_gate = gate.id
            aircraft.target_position = gate.position
            aircraft.state = AircraftState.TAXIING_TO_GATE
            gate.occupied_by = aircraft.id
            aircraft.assigned_runway = None
            print(f"AUTO-GATE: {aircraft.callsign} assigned to gate {gate.id}")
        else:
            # No gate available - aircraft must wait on runway
            print(f"WAITING: {aircraft.callsign} waiting for gate (runway {aircraft.assigned_runway})")
    
    def _handle_gate_arrival(self, aircraft: Aircraft):
        """
        Handle aircraft arriving at gate and starting boarding/deboarding.
        
        Args:
            aircraft (Aircraft): The aircraft that arrived at the gate
        """
        aircraft.state = AircraftState.BOARDING_DEBOARDING
        
        # Start gate operations (boarding/deboarding and refueling)
        current_time = self.airport.current_time
        aircraft.start_gate_operations(current_time)
        
        print(f"ARRIVAL: {aircraft.callsign} arrived at gate {aircraft.assigned_gate} - starting boarding/deboarding and refueling")
    
    def _handle_takeoff_start(self, aircraft: Aircraft):
        """
        Handle aircraft starting takeoff procedure.
        
        Args:
            aircraft (Aircraft): The aircraft starting takeoff
        """
        aircraft.state = AircraftState.TAKING_OFF
        # Set takeoff target (off the screen)
        runway = self.airport.runways[aircraft.assigned_runway]
        direction_x = runway.end_position.x - runway.start_position.x
        direction_y = runway.end_position.y - runway.start_position.y
        length = math.sqrt(direction_x**2 + direction_y**2)
        direction_x /= length
        direction_y /= length
        
        aircraft.target_position = Position(
            runway.end_position.x + direction_x * 500,
            runway.end_position.y + direction_y * 500
        )
        print(f"TAKEOFF: {aircraft.callsign} taking off from runway {aircraft.assigned_runway}")
    
    def _handle_takeoff_completion(self, aircraft: Aircraft):
        """
        Handle aircraft completing takeoff and departing.
        
        Args:
            aircraft (Aircraft): The aircraft completing takeoff
        """
        # Check if aircraft is off screen
        if (aircraft.position.x < -100 or aircraft.position.x > self.airport.config.airport.airport_width + 100 or
            aircraft.position.y < -100 or aircraft.position.y > self.airport.config.airport.airport_height + 100):
            aircraft.state = AircraftState.DEPARTED
            # Free up runway
            if aircraft.assigned_runway is not None:
                runway = self.airport.runways[aircraft.assigned_runway]
                runway.state = RunwayState.AVAILABLE
                runway.occupied_by = None
            print(f"DEPARTED: {aircraft.callsign} has departed")
    
    def _handle_go_around_completion(self, aircraft: Aircraft):
        """
        Handle aircraft completing go-around procedure.
        
        Args:
            aircraft (Aircraft): The aircraft completing go-around
        """
        # Aircraft completed go-around, transition back to holding for another landing attempt
        aircraft.state = AircraftState.HOLDING
        print(f"🔄 GO-AROUND COMPLETE: {aircraft.callsign} now holding, ready for another landing attempt")
    
    def assign_gates_to_waiting_aircraft(self):
        """
        Assign gates to aircraft waiting after landing.
        
        This method checks for aircraft that landed but are waiting for gates
        and assigns them to available gates as they become free.
        """
        # Find aircraft waiting for gates (landed but still on runway)
        waiting_aircraft = [a for a in self.airport.aircraft 
                          if a.state == AircraftState.LANDING and a.assigned_gate is None]
        
        for aircraft in waiting_aircraft:
            # Check if aircraft is close to runway (has completed landing)
            if aircraft.assigned_runway is not None:
                runway = self.airport.runways[aircraft.assigned_runway]
                if aircraft.position.distance_to(runway.center_position) < 20:
                    # Try to assign a gate
                    gate = self.airport.get_available_gate()
                    if gate:
                        # Assign gate and start taxiing
                        aircraft.assigned_gate = gate.id
                        aircraft.target_position = gate.position
                        aircraft.state = AircraftState.TAXIING_TO_GATE
                        gate.occupied_by = aircraft.id
                        
                        # Free up runway
                        runway.state = RunwayState.AVAILABLE
                        runway.occupied_by = None
                        aircraft.assigned_runway = None
                        
                        print(f"GATE-ASSIGNED: {aircraft.callsign} assigned to gate {gate.id}")
    
    def schedule_departures(self):
        """
        Automatically schedule departures for aircraft that have been at gates long enough.
        
        This method manages the boarding/deboarding process and schedules departures
        when aircraft are ready to leave the gate (both boarding and refueling complete).
        """
        current_time = self.airport.current_time
        
        # Handle boarding/deboarding and refueling completion
        for aircraft in self.airport.aircraft:
            if aircraft.state == AircraftState.BOARDING_DEBOARDING:
                # Check if aircraft is ready for departure (both boarding and refueling complete)
                if aircraft.is_ready_for_departure(current_time):
                    aircraft.state = AircraftState.AT_GATE
                    
                    # Get status information for logging
                    gate_status = aircraft.get_gate_status(current_time)
                    print(f"GATE OPERATIONS COMPLETE: {aircraft.callsign} ready for departure | {gate_status}")
        
        # Schedule departures for aircraft that are ready at gates
        for aircraft in self.airport.aircraft:
            if aircraft.state == AircraftState.AT_GATE:
                # Aircraft ready for departure - try to assign runway
                if random.random() < 0.15:  # 15% chance per update cycle (slightly higher for refueled aircraft)
                    runway = self.airport.get_available_runway()
                    if runway:
                        # Clear gate and assign runway
                        if aircraft.assigned_gate is not None:
                            gate = self.airport.gates[aircraft.assigned_gate]
                            gate.occupied_by = None
                        
                        aircraft.assigned_runway = runway.id
                        aircraft.target_position = runway.center_position
                        aircraft.state = AircraftState.TAXIING_TO_RUNWAY
                        runway.state = RunwayState.OCCUPIED_TAKEOFF
                        runway.occupied_by = aircraft.id
                        aircraft.assigned_gate = None
                        
                        # Log departure with fuel and passenger information
                        total_gate_time = aircraft.get_total_gate_time()
                        print(f"DEPARTURE: {aircraft.callsign} cleared for takeoff on runway {runway.id}")
                        print(f"├─ Fuel: {aircraft.fuel:.1f}% (refueled from {aircraft.fuel_at_arrival:.1f}%)")
                        print(f"├─ Passengers: {aircraft.passenger_count}")
                        print(f"└─ Gate time: {total_gate_time:.1f}s (boarding + refueling)")
                        break
                    else:
                        # No runway available - move to holding area
                        if not hasattr(aircraft, 'waiting_for_runway'):
                            aircraft.waiting_for_runway = True
                            self._move_to_holding_area(aircraft)
                            break
    
    def _move_to_holding_area(self, aircraft: Aircraft):
        """
        Move aircraft to holding area when no runway is available for departure.
        
        Args:
            aircraft (Aircraft): The aircraft to move to holding area
        """
        center_x = self.airport.config.airport.airport_width / 2
        center_y = self.airport.config.airport.airport_height / 2
        hold_radius = 150
        angle = random.uniform(0, 2 * math.pi)
        
        if aircraft.assigned_gate is not None:
            gate = self.airport.gates[aircraft.assigned_gate]
            gate.occupied_by = None
            aircraft.assigned_gate = None
        
        aircraft.target_position = Position(
            center_x + math.cos(angle) * hold_radius,
            center_y + math.sin(angle) * hold_radius
        )
        aircraft.state = AircraftState.HOLDING
        print(f"HOLDING: {aircraft.callsign} moved to holding area (no runway available)")
    
    def process_holding_aircraft(self):
        """
        Process aircraft in holding patterns waiting for runway assignments.
        
        This method manages aircraft that are waiting in holding patterns
        and assigns them runways when they become available.
        """
        holding_aircraft = [a for a in self.airport.aircraft 
                          if a.state == AircraftState.HOLDING and hasattr(a, 'waiting_for_runway')]
        
        for aircraft in holding_aircraft:
            runway = self.airport.get_available_runway()
            if runway:
                # Assign runway for takeoff
                aircraft.assigned_runway = runway.id
                aircraft.target_position = runway.center_position
                aircraft.state = AircraftState.TAXIING_TO_RUNWAY
                runway.state = RunwayState.OCCUPIED_TAKEOFF
                runway.occupied_by = aircraft.id
                
                # Clear waiting flag
                delattr(aircraft, 'waiting_for_runway')
                
                print(f"RUNWAY-CLEARED: {aircraft.callsign} assigned runway {runway.id} from holding")
                break 