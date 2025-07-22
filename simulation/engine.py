"""
Main simulation engine for the AI Airport Simulation.

This module contains the SimulationEngine class that coordinates all
simulation components and manages the main simulation loop.
"""

import math
import random
from typing import Dict, List, Optional

from config import get_config
from models.aircraft import Aircraft, AircraftState
from models.airport import Airport
from models.position import Position
from ai_interface import AIManager

from .flight_scheduler import FlightScheduler
from .collision_system import CollisionSystem
from .fuel_system import FuelSystem
from .state_manager import StateManager


class AirTrafficController:
    """Simple rule-based ATC for basic decisions."""
    
    def __init__(self, airport: Airport):
        self.airport = airport
        
    def make_decision(self, aircraft: Aircraft) -> Dict[str, any]:
        """Make a basic ATC decision."""
        decision = {
            'action': None,
            'target': None,
            'reasoning': 'No action needed'
        }
        
        if aircraft.state == AircraftState.APPROACHING:
            # Find available runway for landing
            runway = self.airport.get_available_runway()
            if runway:
                decision['action'] = 'assign_landing'
                decision['target'] = runway.id
                decision['reasoning'] = f'Assigned runway {runway.id} for landing'
                return decision
            else:
                decision['action'] = 'hold_pattern'
                decision['reasoning'] = 'No runways available, entering hold pattern'
                return decision
        
        elif aircraft.state == AircraftState.LANDING and aircraft.assigned_runway is not None:
            # Check if aircraft reached runway
            runway = self.airport.runways[aircraft.assigned_runway]
            if aircraft.position.distance_to(runway.center_position) < 20:
                gate = self.airport.get_available_gate()
                if gate:
                    decision['action'] = 'assign_gate'
                    decision['target'] = gate.id
                    decision['reasoning'] = f'Landing complete, assigned gate {gate.id}'
                    return decision
        
        elif aircraft.state == AircraftState.AT_GATE:
            # Random departure time simulation
            if random.random() < 0.01:  # 1% chance per decision cycle
                runway = self.airport.get_available_runway()
                if runway:
                    decision['action'] = 'assign_takeoff'
                    decision['target'] = runway.id
                    decision['reasoning'] = f'Departure cleared, assigned runway {runway.id}'
                    return decision
        
        return decision


class SimulationEngine:
    """
    Main simulation engine that coordinates all airport simulation components.
    
    The SimulationEngine brings together all modular components:
    - FlightScheduler: Manages aircraft spawning and flight generation
    - CollisionSystem: Handles collision detection and avoidance
    - FuelSystem: Manages fuel emergencies and runway clearing
    - StateManager: Handles aircraft state transitions and lifecycle
    """
    
    def __init__(self):
        """Initialize the simulation engine with all required components."""
        config = get_config()
        self.airport = Airport(config)
        self.atc = AirTrafficController(self.airport)
        self.running = False
        self.last_ai_decision = 0
        self.manual_mode = False
        self.pending_manual_commands: List[Dict] = []
        
        # Initialize modular components
        self.scheduler = FlightScheduler(self.airport)
        self.collision_system = CollisionSystem(self.airport)
        self.fuel_system = FuelSystem(self.airport)
        self.state_manager = StateManager(self.airport)
        
        # Crash tracking
        self.total_crashes = 0
        self.crashed_aircraft: List[str] = []  # List of crashed aircraft callsigns
        
        # Initialize AI manager if available
        try:
            self.ai_manager = AIManager()
            self.atc.ai_manager = self.ai_manager  # Connect AI to ATC
        except Exception as e:
            print(f"Warning: Could not initialize AI manager: {e}")
            self.ai_manager = None
        
    def add_manual_command(self, command: Dict):
        """Add a manual control command."""
        self.pending_manual_commands.append(command)
    
    def process_atc_decision(self, aircraft: Aircraft, decision: Dict):
        """Process and execute an ATC decision."""
        action = decision.get('action')
        target = decision.get('target')
        
        # Convert target to integer if it's a string
        if target is not None:
            try:
                if isinstance(target, str):
                    # Extract numbers from strings like "Runway 0", "Gate 2", etc.
                    import re
                    numbers = re.findall(r'\d+', target)
                    if numbers:
                        target = int(numbers[0])
                    else:
                        raise ValueError(f"No number found in '{target}'")
                else:
                    target = int(target)
            except (ValueError, TypeError) as e:
                print(f"Warning: Invalid target value '{target}' ({e}), ignoring decision")
                return
        
        if action == 'assign_landing' and target is not None:
            runway = self.airport.runways[target]
            aircraft.assigned_runway = target
            aircraft.target_position = runway.center_position
            aircraft.state = AircraftState.LANDING
            runway.state = runway.state  # Keep current state for now
            
        elif action == 'assign_gate' and target is not None:
            gate = self.airport.gates[target]
            aircraft.assigned_gate = target
            aircraft.target_position = gate.position
            aircraft.state = AircraftState.TAXIING_TO_GATE
            gate.occupied_by = aircraft.id
            
        elif action == 'assign_takeoff' and target is not None:
            runway = self.airport.runways[target]
            aircraft.assigned_runway = target
            aircraft.target_position = runway.center_position
            aircraft.state = AircraftState.TAXIING_TO_RUNWAY
            
        elif action == 'hold_pattern':
            # Check if aircraft can safely enter holding pattern
            if aircraft.can_safely_hold(10.0):  # Check if can hold for 10 minutes
                # Create a circular holding pattern
                center_x = self.airport.config.airport.airport_width / 2
                center_y = self.airport.config.airport.airport_height / 2
                hold_radius = 200
                angle = random.uniform(0, 2 * math.pi)
                aircraft.target_position = Position(
                    center_x + math.cos(angle) * hold_radius,
                    center_y + math.sin(angle) * hold_radius
                )
                aircraft.state = AircraftState.HOLDING
                safe_time = aircraft.get_safe_holding_time()
                print(f"HOLD PATTERN: {aircraft.callsign} entering holding (fuel: {aircraft.fuel:.1f}%, safe for {safe_time:.1f} minutes)")
            else:
                # Aircraft doesn't have enough fuel for holding - force immediate landing
                runway = self.airport.get_available_runway()
                if not runway:
                    # No runway available but must land - use first runway regardless
                    runway = self.airport.runways[0]
                    # Clear current occupant if necessary for fuel emergency
                    if runway.occupied_by:
                        current_occupant = self.airport.get_aircraft(runway.occupied_by)
                        if current_occupant and not current_occupant.is_critical_fuel():
                            # Move to holding if they have fuel, otherwise crash scenario
                            if current_occupant.can_safely_hold(5.0):
                                center_x = self.airport.config.airport.airport_width / 2
                                center_y = self.airport.config.airport.airport_height / 2
                                hold_radius = 200
                                angle = random.uniform(0, 2 * math.pi)
                                current_occupant.target_position = Position(
                                    center_x + math.cos(angle) * hold_radius,
                                    center_y + math.sin(angle) * hold_radius
                                )
                                current_occupant.state = AircraftState.HOLDING
                                current_occupant.assigned_runway = None
                
                aircraft.assigned_runway = runway.id
                aircraft.target_position = runway.center_position
                aircraft.state = AircraftState.LANDING
                runway.state = RunwayState.OCCUPIED_LANDING
                runway.occupied_by = aircraft.id
                print(f"FUEL EMERGENCY: {aircraft.callsign} cannot hold (fuel: {aircraft.fuel:.1f}%) - forced immediate landing on runway {runway.id}")
        
        elif action == 'collision_avoidance' and target is not None:
            # Execute collision avoidance maneuver
            self.collision_system.execute_collision_avoidance(aircraft, target)
    
    def request_collision_avoidance(self, avoid_aircraft: Aircraft, conflicting_aircraft: Aircraft):
        """Request AI to make collision avoidance decision."""
        if hasattr(self, 'ai_manager') and self.ai_manager:
            # Get current airport state
            airport_state = self.get_simulation_state()
            
            # Add collision context
            distance = avoid_aircraft.distance_to(conflicting_aircraft)
            airport_state['collision_warning'] = {
                'avoid_aircraft_id': avoid_aircraft.id,
                'conflicting_aircraft_id': conflicting_aircraft.id,
                'distance': distance,
                'warning': f"COLLISION WARNING: {avoid_aircraft.callsign} and {conflicting_aircraft.callsign} are {distance:.0f} pixels apart!"
            }
            
            # Make AI decision for collision avoidance
            decision = self.ai_manager.make_atc_decision(avoid_aircraft, airport_state)
            if decision.get('action'):
                self.process_atc_decision(avoid_aircraft, decision)
            else:
                # AI failed to provide collision avoidance - execute emergency avoidance
                print(f"EMERGENCY AVOIDANCE: AI failed to respond for {avoid_aircraft.callsign}, executing automatic avoidance")
                # Choose avoidance position based on aircraft position relative to conflicting aircraft
                diff_x = avoid_aircraft.position.x - conflicting_aircraft.position.x
                diff_y = avoid_aircraft.position.y - conflicting_aircraft.position.y
                # Move away from conflicting aircraft
                if abs(diff_x) > abs(diff_y):
                    avoidance_pos = 2 if diff_x > 0 else 6  # East or West
                else:
                    avoidance_pos = 0 if diff_y < 0 else 4  # North or South
                self.collision_system.execute_collision_avoidance(avoid_aircraft, avoidance_pos)
    
    def update(self, dt: float):
        """Main simulation update loop."""
        if not self.running:
            return
        
        # Update airport and aircraft
        self.airport.update(dt)
        
        # Update flight scheduling
        self.scheduler.update(dt)
        
        # Update aircraft states
        self.state_manager.update_aircraft_states(dt)
        
                # Monitor fuel levels and emergencies
        self.fuel_system.monitor_fuel_levels(dt)
        
        # Handle critical fuel emergencies and runway clearing
        self.fuel_system.handle_critical_fuel_emergencies()
        
        # Check for imminent collisions and trigger avoidance
        collision_pairs = self.collision_system.check_imminent_collisions()
        for avoid_aircraft, conflicting_aircraft in collision_pairs:
            self.request_collision_avoidance(avoid_aircraft, conflicting_aircraft)
        
        # Check for collisions and crashes
        collisions = self.collision_system.check_collisions()
        self.collision_system.handle_collisions(collisions)
        self.handle_crashes()
        
        # Process manual commands first
        while self.pending_manual_commands:
            command = self.pending_manual_commands.pop(0)
            aircraft_id = command.get('aircraft_id')
            aircraft = self.airport.get_aircraft(aircraft_id)
            if aircraft:
                self.process_atc_decision(aircraft, command)
        
        # AI decision making (if not in manual mode and enough time passed)
        config = get_config()
        ai_enabled = getattr(config.ai, 'ai_enabled', True) if hasattr(config, 'ai') else True
        
        # Check if we have collision warnings - use faster AI response
        has_collision_warnings = len(collision_pairs) > 0
        if has_collision_warnings:
            ai_interval = getattr(config.simulation, 'ai_collision_interval', 0.25) if hasattr(config, 'simulation') else 0.25
        else:
            ai_interval = getattr(config.simulation, 'ai_decision_interval', 0.5) if hasattr(config, 'simulation') else 0.5
        
        if (not self.manual_mode and 
            ai_enabled and 
            (self.airport.current_time - self.last_ai_decision) >= ai_interval):
            
            for aircraft in self.airport.aircraft:
                # Only make AI decisions for aircraft that need them
                if aircraft.state in [AircraftState.APPROACHING, AircraftState.AT_GATE, AircraftState.BOARDING_DEBOARDING]:
                    # Skip aircraft that are close to completing their current task
                    if (aircraft.state == AircraftState.LANDING and 
                        aircraft.position.distance_to(aircraft.target_position) < 100):
                        continue  # Let them complete landing
                    
                    decision = self.atc.make_decision(aircraft)
                    if decision.get('action'):
                        self.process_atc_decision(aircraft, decision)
            
            self.last_ai_decision = self.airport.current_time
        
        # Check for landed aircraft waiting for gates
        self.state_manager.assign_gates_to_waiting_aircraft()
        
        # Handle aircraft departures
        self.state_manager.schedule_departures()
        
        # Handle aircraft in holding patterns waiting for runways
        self.state_manager.process_holding_aircraft()
    
    def handle_crashes(self):
        """Handle crashed aircraft and update crash statistics."""
        crashed_aircraft = [a for a in self.airport.aircraft if a.state == AircraftState.CRASHED]
        
        for aircraft in crashed_aircraft:
            if aircraft.callsign not in self.crashed_aircraft:
                # New crash
                self.crashed_aircraft.append(aircraft.callsign)
                self.total_crashes += 1
                
                # Determine crash cause and context
                if aircraft.fuel <= 0:
                    crash_reason = "FUEL DEPLETION"
                    aircraft.crash_reason = crash_reason
                    crash_details = f"Aircraft ran out of fuel (0.0%) while in state: {aircraft.state.value}"
                    if aircraft.state in [AircraftState.APPROACHING, AircraftState.HOLDING]:
                        crash_details += f" - CRITICAL: Aircraft needed immediate landing priority!"
                    elif aircraft.state == AircraftState.LANDING:
                        crash_details += f" - Aircraft was landing but fuel depleted during approach"
                else:
                    crash_reason = "MID-AIR COLLISION"
                    crash_details = f"Aircraft collided with another aircraft"
                
                print(f"CRASH: {aircraft.callsign} - {crash_reason} (Fuel: {aircraft.fuel:.1f}%)")
                
                # Log detailed crash information to AI decision log
                if hasattr(self, 'ai_manager') and self.ai_manager:
                    from ai_interface import AI_LOGGER
                    AI_LOGGER.error(f"🚨 AIRCRAFT CRASH - {aircraft.callsign} [{aircraft.aircraft_type}]")
                    AI_LOGGER.error(f"├─ CRASH CAUSE: {crash_reason}")
                    AI_LOGGER.error(f"├─ DETAILS: {crash_details}")
                    AI_LOGGER.error(f"├─ Final Position: ({aircraft.position.x:.0f}, {aircraft.position.y:.0f})")
                    AI_LOGGER.error(f"├─ Final State: {aircraft.state.value}")
                    AI_LOGGER.error(f"├─ Final Fuel: {aircraft.fuel:.1f}%")
                    AI_LOGGER.error(f"├─ Assigned Runway: {aircraft.assigned_runway}")
                    AI_LOGGER.error(f"├─ Assigned Gate: {aircraft.assigned_gate}")
                    
                    # Add safety analysis
                    if crash_reason == "FUEL DEPLETION":
                        AI_LOGGER.error(f"├─ SAFETY ANALYSIS: This crash could have been prevented!")
                        AI_LOGGER.error(f"└─ AI GOAL: Prioritize fuel emergencies above all other considerations!")
    
    def get_simulation_state(self) -> Dict:
        """Get current simulation state for AI decision making."""
        state = {
            'current_time': self.airport.current_time,
            'runways': [
                {
                    'id': runway.id,
                    'state': runway.state.value,
                    'occupied_by': runway.occupied_by
                }
                for runway in self.airport.runways
            ],
            'gates': [
                {
                    'id': gate.id,
                    'occupied_by': gate.occupied_by,
                    'available': gate.is_available
                }
                for gate in self.airport.gates
            ],
            'aircraft': [
                {
                    'id': aircraft.id,
                    'callsign': aircraft.callsign,
                    'state': aircraft.state.value,
                    'fuel': aircraft.fuel,
                    'is_low_fuel': aircraft.is_low_fuel(),
                    'is_critical_fuel': aircraft.is_critical_fuel(),
                    'position': {'x': aircraft.position.x, 'y': aircraft.position.y},
                    'assigned_runway': aircraft.assigned_runway,
                    'assigned_gate': aircraft.assigned_gate
                }
                for aircraft in self.airport.aircraft
                if aircraft.state not in [AircraftState.CRASHED, AircraftState.DEPARTED]
            ],
            'total_crashes': self.total_crashes,
            'crashed_aircraft': self.crashed_aircraft.copy()
        }
        return state
    
    def start(self):
        """Start the simulation."""
        config = get_config()
        runways_count = getattr(config.airport.runways, 'count', 2) if hasattr(config.airport, 'runways') else 2
        gates_count = getattr(config.airport.gates, 'count', 4) if hasattr(config.airport, 'gates') else 4
        
        print(f"Airport capacity: {runways_count} runways + {gates_count} gates = {runways_count + gates_count} total")
        
        # Calculate and display dynamic spawn rate
        total_capacity = runways_count + gates_count
        base_spawn_rate = 1.0  # Base rate: 1 aircraft per second
        capacity_multiplier = total_capacity / 6.0  # Scale based on capacity (6 is baseline)
        dynamic_spawn_rate = base_spawn_rate * capacity_multiplier
        spawn_interval = 1.0 / dynamic_spawn_rate
        
        print(f"Dynamic spawn rate: {dynamic_spawn_rate:.2f} aircraft/second (spawn interval: {spawn_interval:.1f}s)")
        
        self.running = True
    
    def stop(self):
        """Stop the simulation."""
        self.running = False
    
    def toggle_pause(self):
        """Toggle simulation pause state."""
        self.running = not self.running
    
    def set_manual_mode(self, manual: bool):
        """Set manual control mode."""
        self.manual_mode = manual 