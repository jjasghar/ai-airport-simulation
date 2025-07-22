"""
Main simulation engine for the airport control tower simulation.
"""
import time
import random
import math
from typing import List, Dict, Optional, Callable
from models import *
from config import get_config
from ai_interface import AI_LOGGER

class AirTrafficController:
    """AI or manual air traffic controller interface."""
    
    def __init__(self, airport: Airport):
        self.airport = airport
        self.decision_history: List[Dict] = []
    
    def make_decision(self, aircraft: Aircraft) -> Dict[str, any]:
        """
        Make a control decision for an aircraft.
        Returns a dictionary with the decision details.
        """
        decision = {
            'aircraft_id': aircraft.id,
            'timestamp': time.time(),
            'action': None,
            'target': None,
            'reasoning': ''
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

class FlightScheduler:
    """Manages flight arrivals and departures."""
    
    def __init__(self, airport: Airport):
        self.airport = airport
        self.scheduled_flights: List[Flight] = []
        self.last_spawn_time = 0
        
    def generate_flight(self, flight_type: str = "arrival") -> Flight:
        """Generate a new flight."""
        origins = ["JFK", "LAX", "ORD", "DFW", "DEN", "SFO", "SEA", "MIA"]
        destinations = ["ATL", "BOS", "LAS", "PHX", "IAH", "CLT", "MSP", "DTW"]
        aircraft_types = ["Boeing 737", "Airbus A320", "Boeing 777", "Airbus A380"]
        
        flight = Flight(
            origin=random.choice(origins) if flight_type == "arrival" else "HOME",
            destination=random.choice(destinations) if flight_type == "departure" else "HOME",
            scheduled_time=self.airport.current_time,
            flight_type=flight_type,
            aircraft_type=random.choice(aircraft_types)
        )
        return flight
    
    def spawn_aircraft(self, flight: Flight) -> Aircraft:
        """Spawn an aircraft for a flight."""
        # Convert string aircraft type to enum
        from models.aircraft import AircraftType
        aircraft_type_enum = AircraftType(flight.aircraft_type)
        
        aircraft = Aircraft(
            callsign=flight.callsign,
            aircraft_type=aircraft_type_enum
        )
        
        if flight.flight_type == "arrival":
            # Spawn approaching from random direction, ensuring visibility
            angle = random.uniform(0, 2 * math.pi)
            spawn_distance = 400
            spawn_x = self.airport.config.airport.airport_width / 2 + math.cos(angle) * spawn_distance
            spawn_y = self.airport.config.airport.airport_height / 2 + math.sin(angle) * spawn_distance
            
            # Clamp aircraft position to ensure they stay visible on screen
            margin = 50  # Keep aircraft at least 50 pixels from screen edge
            spawn_x = max(margin, min(self.airport.config.airport.airport_width - margin, spawn_x))
            spawn_y = max(margin, min(self.airport.config.airport.airport_height - margin, spawn_y))
            
            aircraft.position = Position(spawn_x, spawn_y)
            aircraft.state = AircraftState.APPROACHING
            
            # Arriving aircraft have sufficient fuel for safe landing (25-35%)
            # This allows for some maneuvering without immediate crash risk
            aircraft.fuel = random.uniform(25.0, 35.0)
        else:
            # Spawn at a gate for departure
            gate = self.airport.get_available_gate()
            if gate:
                aircraft.position = Position(gate.position.x, gate.position.y)
                aircraft.assigned_gate = gate.id
                aircraft.state = AircraftState.AT_GATE
                gate.occupied_by = aircraft.id
                
                # Departing aircraft start with full fuel
                aircraft.fuel = 100.0
        
        return aircraft
    
    def update(self, dt: float):
        """Update flight scheduling."""
        config = get_config()
        # Spawn new aircraft based on dynamic spawn rate  
        dynamic_spawn_rate = config.get_dynamic_spawn_rate() if hasattr(config, 'get_dynamic_spawn_rate') else 1.0
        if (self.airport.current_time - self.last_spawn_time) > (1.0 / dynamic_spawn_rate):
            max_aircraft = getattr(config.simulation, 'max_aircraft', 20) if hasattr(config, 'simulation') else 20
            if len(self.airport.aircraft) < max_aircraft:
                # 70% arrivals, 30% departures
                flight_type = "arrival" if random.random() < 0.7 else "departure"
                flight = self.generate_flight(flight_type)
                aircraft = self.spawn_aircraft(flight)
                self.airport.add_aircraft(aircraft)
                self.last_spawn_time = self.airport.current_time

class SimulationEngine:
    """Main simulation engine."""
    
    def __init__(self):
        config = get_config()
        self.airport = Airport(config)
        self.atc = AirTrafficController(self.airport)
        self.scheduler = FlightScheduler(self.airport)
        self.running = False
        self.last_ai_decision = 0
        self.manual_mode = False
        self.pending_manual_commands: List[Dict] = []
        
        # Crash tracking
        self.total_crashes = 0
        self.crashed_aircraft: List[str] = []  # List of crashed aircraft callsigns
        
        # Fuel emergency logging throttling (callsign -> last_log_time)
        self.fuel_emergency_last_logged: Dict[str, float] = {}
        self.fuel_emergency_log_interval = 10.0  # Log at most once every 10 seconds
        
        # Collision avoidance throttling (aircraft_pair -> last_avoid_time)
        self.collision_avoidance_last_triggered: Dict[str, float] = {}
        self.collision_avoidance_interval = 2.0  # Avoid same pair at most once every 2 seconds (reduced)
        
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
            if 0 <= target < len(self.airport.runways):
                runway = self.airport.runways[target]
                if runway.state == RunwayState.AVAILABLE or aircraft.is_critical_fuel():
                    # For critical fuel aircraft, preempt runway even if occupied
                    if runway.state != RunwayState.AVAILABLE and aircraft.is_critical_fuel():
                        # Clear current occupant if it's not also critical fuel
                        if runway.occupied_by:
                            current_occupant = self.airport.get_aircraft(runway.occupied_by)
                            if current_occupant and not current_occupant.is_critical_fuel():
                                # Move current occupant to holding pattern
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
                    
                    # Assign runway to the aircraft
                    aircraft.assigned_runway = target
                    aircraft.target_position = runway.center_position
                    aircraft.state = AircraftState.LANDING
                    runway.state = RunwayState.OCCUPIED_LANDING
                    runway.occupied_by = aircraft.id
        
        elif action == 'assign_gate' and target is not None:
            if 0 <= target < len(self.airport.gates):
                gate = self.airport.gates[target]
                if gate.is_available:
                    # Free up runway
                    if aircraft.assigned_runway is not None:
                        runway = self.airport.runways[aircraft.assigned_runway]
                        runway.state = RunwayState.AVAILABLE
                        runway.occupied_by = None
                    
                    aircraft.assigned_gate = target
                    aircraft.target_position = gate.position
                    aircraft.state = AircraftState.TAXIING_TO_GATE
                    gate.occupied_by = aircraft.id
        
        elif action == 'assign_takeoff' and target is not None:
            if 0 <= target < len(self.airport.runways):
                runway = self.airport.runways[target]
                if runway.state == RunwayState.AVAILABLE:
                    # Free up gate
                    if aircraft.assigned_gate is not None:
                        gate = self.airport.gates[aircraft.assigned_gate]
                        gate.occupied_by = None
                    
                    aircraft.assigned_runway = target
                    aircraft.target_position = runway.center_position
                    aircraft.state = AircraftState.TAXIING_TO_RUNWAY
                    runway.state = RunwayState.OCCUPIED_TAKEOFF
                    runway.occupied_by = aircraft.id
        
        elif action == 'assign_runway' and target is not None:
            # Assign a runway to approaching aircraft (similar to assign_landing but doesn't change state immediately)
            if 0 <= target < len(self.airport.runways):
                runway = self.airport.runways[target]
                if runway.state == RunwayState.AVAILABLE or aircraft.is_critical_fuel():
                    # For critical fuel aircraft, preempt runway even if occupied
                    if runway.state != RunwayState.AVAILABLE and aircraft.is_critical_fuel():
                        # Clear current occupant if it's not also critical fuel
                        if runway.occupied_by:
                            current_occupant = self.airport.get_aircraft(runway.occupied_by)
                            if current_occupant and not current_occupant.is_critical_fuel():
                                # Move current occupant to holding pattern
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
                    
                    # Assign runway to the aircraft
                    aircraft.assigned_runway = target
                    aircraft.target_position = runway.center_position
                    aircraft.state = AircraftState.LANDING
                    runway.state = RunwayState.OCCUPIED_LANDING
                    runway.occupied_by = aircraft.id
        
        elif action == 'hold_pattern':
            # Create a circular holding pattern and set state to HOLDING
            center_x = self.airport.config.airport.airport_width / 2
            center_y = self.airport.config.airport.airport_height / 2
            hold_radius = 200
            angle = random.uniform(0, 2 * math.pi)
            aircraft.target_position = Position(
                center_x + math.cos(angle) * hold_radius,
                center_y + math.sin(angle) * hold_radius
            )
            aircraft.state = AircraftState.HOLDING
        
        elif action == 'collision_avoidance' and target is not None:
            # Execute collision avoidance maneuver
            self.execute_collision_avoidance(aircraft, target)
    
    def execute_collision_avoidance(self, aircraft: Aircraft, avoidance_position: int):
        """Execute collision avoidance maneuver by moving aircraft to safe position."""
        # Define 8 avoidance positions around the airport center
        center_x = self.airport.config.airport.airport_width / 2
        center_y = self.airport.config.airport.airport_height / 2
        avoidance_radius = 250  # Reduced radius for more responsive avoidance
        
        # Calculate avoidance position (0-7 for 8 positions around circle)
        avoidance_position = max(0, min(7, avoidance_position))  # Clamp to valid range
        angle = (avoidance_position / 8.0) * 2 * math.pi  # Convert to radians
        
        # Set new target position for avoidance
        avoid_x = center_x + math.cos(angle) * avoidance_radius
        avoid_y = center_y + math.sin(angle) * avoidance_radius
        
        # Ensure avoidance position is within screen bounds with margin
        margin = 50
        avoid_x = max(margin, min(self.airport.config.airport.airport_width - margin, avoid_x))
        avoid_y = max(margin, min(self.airport.config.airport.airport_height - margin, avoid_y))
        
        aircraft.target_position = Position(avoid_x, avoid_y)
        
        # Set to holding state during avoidance
        aircraft.state = AircraftState.HOLDING
        
        print(f"COLLISION AVOIDANCE: {aircraft.callsign} moving to avoidance position {avoidance_position}")
    
    def execute_emergency_avoidance(self, aircraft1: Aircraft, aircraft2: Aircraft):
        """Execute immediate emergency avoidance for both aircraft to prevent collision."""
        # Calculate direction away from each other
        diff_x = aircraft1.position.x - aircraft2.position.x
        diff_y = aircraft1.position.y - aircraft2.position.y
        
        # Normalize and amplify the separation
        import math
        distance = math.sqrt(diff_x**2 + diff_y**2)
        if distance > 0:
            # Unit vector pointing from aircraft2 to aircraft1
            unit_x = diff_x / distance
            unit_y = diff_y / distance
            
            # Move aircraft1 away from aircraft2
            separation_distance = 200  # Move 200 pixels away
            new_x1 = aircraft1.position.x + unit_x * separation_distance
            new_y1 = aircraft1.position.y + unit_y * separation_distance
            
            # Move aircraft2 away from aircraft1
            new_x2 = aircraft2.position.x - unit_x * separation_distance
            new_y2 = aircraft2.position.y - unit_y * separation_distance
            
            # Ensure positions stay within bounds
            margin = 50
            config = self.airport.config
            new_x1 = max(margin, min(config.airport.airport_width - margin, new_x1))
            new_y1 = max(margin, min(config.airport.airport_height - margin, new_y1))
            new_x2 = max(margin, min(config.airport.airport_width - margin, new_x2))
            new_y2 = max(margin, min(config.airport.airport_height - margin, new_y2))
            
            # Set new target positions
            aircraft1.target_position = Position(new_x1, new_y1)
            aircraft2.target_position = Position(new_x2, new_y2)
            
            # Set both to holding state
            aircraft1.state = AircraftState.HOLDING
            aircraft2.state = AircraftState.HOLDING
            
            print(f"EMERGENCY SEPARATION: {aircraft1.callsign} → ({new_x1:.0f},{new_y1:.0f}), {aircraft2.callsign} → ({new_x2:.0f},{new_y2:.0f})")
    
    def update_aircraft_states(self, dt: float):
        """Update aircraft states based on their positions and targets."""
        for aircraft in self.airport.aircraft:
            # Check if aircraft reached their target
            distance_to_target = aircraft.position.distance_to(aircraft.target_position)
            

            if distance_to_target < 10:  # Close enough to target
                if aircraft.state == AircraftState.LANDING:
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
                
                elif aircraft.state == AircraftState.TAXIING_TO_GATE:
                    aircraft.state = AircraftState.BOARDING_DEBOARDING
                    print(f"ARRIVAL: {aircraft.callsign} arrived at gate {aircraft.assigned_gate} - starting boarding/deboarding")
                
                elif aircraft.state == AircraftState.TAXIING_TO_RUNWAY:
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
                
                elif aircraft.state == AircraftState.TAKING_OFF:
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
                
                elif aircraft.state == AircraftState.GO_AROUND:
                    # Aircraft completed go-around, transition back to holding for another landing attempt
                    aircraft.state = AircraftState.HOLDING
                    print(f"🔄 GO-AROUND COMPLETE: {aircraft.callsign} now holding, ready for another landing attempt")
        
        # Check for landed aircraft waiting for gates
        self.assign_gates_to_waiting_aircraft()
        
        # Handle aircraft departures
        self.schedule_departures()
        
        # Handle aircraft in holding patterns waiting for runways
        self.process_holding_aircraft()
    
    def process_holding_aircraft(self):
        """Process aircraft in holding patterns waiting for runway assignments."""
        holding_aircraft = [a for a in self.airport.aircraft 
                           if a.state == AircraftState.HOLDING and 
                           hasattr(a, 'waiting_for_runway') and 
                           a.waiting_for_runway]
        
        for aircraft in holding_aircraft:
            runway = self.airport.get_available_runway()
            if runway:
                # Assign runway for takeoff
                aircraft.assigned_runway = runway.id
                aircraft.target_position = runway.center_position
                aircraft.state = AircraftState.TAXIING_TO_RUNWAY
                runway.state = RunwayState.OCCUPIED_TAKEOFF
                runway.occupied_by = aircraft.id
                aircraft.waiting_for_runway = False
                print(f"RUNWAY-AVAILABLE: {aircraft.callsign} assigned runway {runway.id} from holding")
                break  # Only assign one aircraft per update to avoid race conditions
    
    def assign_gates_to_waiting_aircraft(self):
        """Assign gates to aircraft that have landed but are waiting for gate availability."""
        # Find aircraft that have landed but haven't been assigned gates yet
        waiting_aircraft = [a for a in self.airport.aircraft 
                          if a.state == AircraftState.LANDING and 
                          a.assigned_runway is not None and
                          a.assigned_gate is None and
                          a.position.distance_to(a.target_position) < 10]
        
        for aircraft in waiting_aircraft:
            gate = self.airport.get_available_gate()
            if gate:
                # Free up runway
                runway = self.airport.runways[aircraft.assigned_runway]
                runway.state = RunwayState.AVAILABLE
                runway.occupied_by = None
                
                # Assign gate and start taxiing
                aircraft.assigned_gate = gate.id
                aircraft.target_position = gate.position
                aircraft.state = AircraftState.TAXIING_TO_GATE
                gate.occupied_by = aircraft.id
                aircraft.assigned_runway = None
                print(f"GATE-AVAILABLE: {aircraft.callsign} now assigned to gate {gate.id}")
                         # Only assign one aircraft per update cycle to avoid race conditions
            break
    
    def schedule_departures(self):
        """Automatically schedule departures for aircraft that have been at gates long enough."""
        # Add timestamps to aircraft if they don't have them
        current_time = self.airport.current_time
        
        for aircraft in self.airport.aircraft:
            if aircraft.state == AircraftState.BOARDING_DEBOARDING:
                # Add arrival time if not set
                if aircraft.gate_arrival_time is None:
                    aircraft.gate_arrival_time = current_time
                
                # Calculate realistic boarding/deboarding time based on passenger count
                boarding_time = aircraft.get_boarding_time()
                gate_time = current_time - aircraft.gate_arrival_time
                
                # Check if aircraft has been at gate long enough for boarding/deboarding
                if gate_time > boarding_time:
                    # Boarding/deboarding complete - transition to AT_GATE state
                    aircraft.state = AircraftState.AT_GATE
                    print(f"BOARDING-COMPLETE: {aircraft.callsign} finished boarding/deboarding ({aircraft.passenger_count} passengers)")
        
        # Handle departures for aircraft that have completed boarding
        for aircraft in self.airport.aircraft:
            if aircraft.state == AircraftState.AT_GATE:
                # Check if ready for departure (small random chance to simulate departure scheduling)
                if random.random() < 0.1:  # 10% chance per update
                    runway = self.airport.get_available_runway()
                    if runway:
                        # Free up gate
                        if aircraft.assigned_gate is not None:
                            gate = self.airport.gates[aircraft.assigned_gate]
                            gate.occupied_by = None
                        
                        # Assign runway for takeoff
                        aircraft.assigned_runway = runway.id
                        aircraft.target_position = runway.center_position
                        aircraft.state = AircraftState.TAXIING_TO_RUNWAY
                        runway.state = RunwayState.OCCUPIED_TAKEOFF
                        runway.occupied_by = aircraft.id
                        aircraft.assigned_gate = None
                        boarding_time = aircraft.get_boarding_time()
                        print(f"DEPARTURE: {aircraft.callsign} cleared for takeoff on runway {runway.id} (boarded {aircraft.passenger_count} passengers in {boarding_time:.1f}s)")
                        break  # Only one departure per update
                    else:
                        # No runway available - move to holding area
                        # Only move to holding if not already attempted
                        if not hasattr(aircraft, 'waiting_for_runway'):
                            aircraft.waiting_for_runway = True
                            center_x = self.airport.config.airport.airport_width / 2
                            center_y = self.airport.config.airport.airport_height / 2
                            hold_radius = 150
                            angle = random.uniform(0, 2 * math.pi)
                            
                            # Free up gate for other aircraft
                            if aircraft.assigned_gate is not None:
                                gate = self.airport.gates[aircraft.assigned_gate]
                                gate.occupied_by = None
                                aircraft.assigned_gate = None
                            
                            # Move to holding pattern
                            aircraft.target_position = Position(
                                center_x + math.cos(angle) * hold_radius,
                                center_y + math.sin(angle) * hold_radius
                            )
                            aircraft.state = AircraftState.HOLDING
                            print(f"HOLDING: {aircraft.callsign} moved to holding area (no runway available)")
                            break
    
    def update(self, dt: float):
        """Main simulation update."""
        if not self.running:
            return
        
        # Update airport and aircraft
        self.airport.update(dt)
        
        # Update flight scheduling
        self.scheduler.update(dt)
        
        # Update aircraft states
        self.update_aircraft_states(dt)
        
        # Monitor fuel emergencies
        self.monitor_fuel_emergencies()
        
        # Check for imminent collisions and trigger avoidance
        self.check_imminent_collisions()
        
        # Handle critical fuel emergencies and runway clearing
        self.handle_critical_fuel_emergencies()
        
        # Check for collisions and crashes
        self.check_collisions()
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
        ai_interval = getattr(config.simulation, 'ai_decision_interval', 0.5) if hasattr(config, 'simulation') else 0.5
        if (not self.manual_mode and 
            ai_enabled and 
            (self.airport.current_time - self.last_ai_decision) >= ai_interval):
            
            for aircraft in self.airport.aircraft:
                # Only make AI decisions for aircraft that need them
                # Don't interfere with aircraft already in progress of landing/taxiing
                if aircraft.state in [AircraftState.APPROACHING, AircraftState.AT_GATE, AircraftState.BOARDING_DEBOARDING]:
                    # Skip aircraft that are close to completing their current task
                    if (aircraft.state == AircraftState.LANDING and 
                        aircraft.position.distance_to(aircraft.target_position) < 100):
                        continue  # Let them complete landing
                    
                    decision = self.atc.make_decision(aircraft)
                    if decision.get('action'):
                        self.process_atc_decision(aircraft, decision)
            
            self.last_ai_decision = self.airport.current_time
    
    def monitor_fuel_emergencies(self):
        """Monitor aircraft fuel levels and log warnings for potential emergencies (throttled to once per 10 seconds per aircraft)."""
        current_time = time.time()
        
        # Clean up old entries from throttling dictionary to prevent memory buildup
        active_callsigns = {aircraft.callsign for aircraft in self.airport.aircraft}
        self.fuel_emergency_last_logged = {
            callsign: timestamp for callsign, timestamp in self.fuel_emergency_last_logged.items()
            if callsign in active_callsigns or (current_time - timestamp) < 60  # Keep recent entries
        }
        
        for aircraft in self.airport.aircraft:
            if aircraft.state in [AircraftState.CRASHED, AircraftState.DEPARTED]:
                continue
            
            # Check if enough time has passed since last log for this aircraft
            last_logged = self.fuel_emergency_last_logged.get(aircraft.callsign, 0)
            time_since_last_log = current_time - last_logged
            
            # Only log if enough time has passed (throttling)
            should_log = time_since_last_log >= self.fuel_emergency_log_interval
            
            # Log fuel emergency warnings (throttled)
            if aircraft.is_critical_fuel() and aircraft.state in [AircraftState.APPROACHING, AircraftState.HOLDING]:
                if should_log:
                    AI_LOGGER.warning(f"🔥 FUEL EMERGENCY: {aircraft.callsign} has {aircraft.fuel:.1f}% fuel and is {aircraft.state.value}")
                    AI_LOGGER.warning(f"├─ REQUIRES IMMEDIATE LANDING! Clear any runway for emergency landing!")
                    AI_LOGGER.warning(f"└─ Position: ({aircraft.position.x:.0f}, {aircraft.position.y:.0f})")
                    self.fuel_emergency_last_logged[aircraft.callsign] = current_time
                    
            elif aircraft.is_low_fuel() and aircraft.state in [AircraftState.APPROACHING, AircraftState.HOLDING]:
                if should_log:
                    AI_LOGGER.warning(f"⚠️  LOW FUEL WARNING: {aircraft.callsign} has {aircraft.fuel:.1f}% fuel and is {aircraft.state.value}")
                    AI_LOGGER.warning(f"├─ Needs priority landing - do NOT put on hold!")
                    AI_LOGGER.warning(f"└─ Position: ({aircraft.position.x:.0f}, {aircraft.position.y:.0f})")
                    self.fuel_emergency_last_logged[aircraft.callsign] = current_time
    
    def check_imminent_collisions(self):
        """Check for imminent collisions and trigger avoidance."""
        aircraft_list = [a for a in self.airport.aircraft if a.state != AircraftState.CRASHED 
                        and a.state != AircraftState.DEPARTED]
        
        for i in range(len(aircraft_list)):
            for j in range(i + 1, len(aircraft_list)):
                aircraft1 = aircraft_list[i]
                aircraft2 = aircraft_list[j]
                
                distance = aircraft1.distance_to(aircraft2)
                
                # IMMEDIATE EMERGENCY AVOIDANCE - if very close, don't wait for AI
                if distance <= 100.0:  # Emergency distance - act immediately!
                    pair_key = f"{min(aircraft1.id, aircraft2.id)}_{max(aircraft1.id, aircraft2.id)}"
                    current_time = self.airport.current_time
                    
                    if (pair_key not in self.collision_avoidance_last_triggered or 
                        current_time - self.collision_avoidance_last_triggered[pair_key] >= 1.0):  # Only 1 second throttle for emergency
                        
                        self.collision_avoidance_last_triggered[pair_key] = current_time
                        
                        print(f"🚨 EMERGENCY COLLISION AVOIDANCE: {aircraft1.callsign} and {aircraft2.callsign} only {distance:.0f}px apart!")
                        
                        # Execute immediate avoidance for both aircraft
                        self.execute_emergency_avoidance(aircraft1, aircraft2)
                        continue  # Skip normal collision avoidance for this pair
                
                # Normal collision avoidance for longer distances  
                if aircraft1.is_collision_imminent(aircraft2, warning_distance=400.0):
                    # Check throttling to avoid repeated avoidance for same pair
                    pair_key = f"{min(aircraft1.id, aircraft2.id)}_{max(aircraft1.id, aircraft2.id)}"
                    current_time = self.airport.current_time
                    
                    if (pair_key not in self.collision_avoidance_last_triggered or 
                        current_time - self.collision_avoidance_last_triggered[pair_key] >= self.collision_avoidance_interval):
                        
                        # Update throttling timestamp
                        self.collision_avoidance_last_triggered[pair_key] = current_time
                        
                        # Trigger collision avoidance for one of the aircraft
                        # Priority: avoid for non-critical fuel aircraft first
                        if not aircraft1.is_critical_fuel() and not aircraft2.is_critical_fuel():
                            # Neither critical, choose aircraft with higher fuel
                            avoid_aircraft = aircraft1 if aircraft1.fuel >= aircraft2.fuel else aircraft2
                        elif aircraft1.is_critical_fuel() and not aircraft2.is_critical_fuel():
                            # aircraft1 is critical, avoid with aircraft2
                            avoid_aircraft = aircraft2
                        elif not aircraft1.is_critical_fuel() and aircraft2.is_critical_fuel():
                            # aircraft2 is critical, avoid with aircraft1
                            avoid_aircraft = aircraft1
                        else:
                            # Both critical, choose aircraft with higher fuel
                            avoid_aircraft = aircraft1 if aircraft1.fuel >= aircraft2.fuel else aircraft2
                        
                        # Create collision avoidance decision
                        self.request_collision_avoidance(avoid_aircraft, aircraft1 if avoid_aircraft == aircraft2 else aircraft2)
    
    def request_collision_avoidance(self, avoid_aircraft: Aircraft, conflicting_aircraft: Aircraft):
        """Request AI to make collision avoidance decision."""
        if hasattr(self, 'atc') and hasattr(self.atc, 'ai_manager'):
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
            decision = self.atc.ai_manager.make_atc_decision(avoid_aircraft, airport_state)
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
                self.execute_collision_avoidance(avoid_aircraft, avoidance_pos)
    
    def check_collisions(self):
        """Check for collisions between aircraft."""
        aircraft_list = [a for a in self.airport.aircraft if a.state != AircraftState.CRASHED 
                        and a.state != AircraftState.DEPARTED]
        
        for i in range(len(aircraft_list)):
            for j in range(i + 1, len(aircraft_list)):
                aircraft1 = aircraft_list[i]
                aircraft2 = aircraft_list[j]
                
                if aircraft1.check_collision(aircraft2):
                    # Both aircraft crash
                    aircraft1.state = AircraftState.CRASHED
                    aircraft2.state = AircraftState.CRASHED
                    print(f"COLLISION! {aircraft1.callsign} and {aircraft2.callsign} crashed!")
    
    def handle_critical_fuel_emergencies(self):
        """Handle critical fuel emergencies by clearing runways if necessary."""
        # Find critical fuel aircraft that need immediate landing
        critical_aircraft = [
            a for a in self.airport.aircraft 
            if a.is_critical_fuel() and a.state in [AircraftState.APPROACHING, AircraftState.HOLDING]
        ]
        
        if not critical_aircraft:
            return  # No critical fuel emergencies
        
        # Sort by fuel level (most critical first)
        critical_aircraft.sort(key=lambda a: a.fuel)
        
        for critical_plane in critical_aircraft:
            print(f"🚨 CRITICAL FUEL EMERGENCY: {critical_plane.callsign} has {critical_plane.fuel:.1f}% fuel!")
            
            # Find best available runway or clear one if needed
            available_runway = self.airport.get_available_runway()
            
            if available_runway:
                # Assign critical aircraft to available runway immediately
                self.assign_emergency_landing(critical_plane, available_runway)
            else:
                # All runways occupied - find the least critical aircraft to abort
                runway_to_clear = self.find_runway_to_clear()
                if runway_to_clear:
                    self.execute_emergency_go_around(runway_to_clear)
                    # Assign critical aircraft to cleared runway
                    self.assign_emergency_landing(critical_plane, runway_to_clear)
    
    def find_runway_to_clear(self):
        """Find the best runway to clear for a critical fuel emergency."""
        for runway in self.airport.runways:
            if runway.occupied_by and runway.state == RunwayState.OCCUPIED_LANDING:
                # Find the aircraft using this runway
                landing_aircraft = self.airport.get_aircraft(runway.occupied_by)
                if landing_aircraft and not landing_aircraft.is_critical_fuel():
                    # This runway has a non-critical aircraft landing - can be cleared
                    return runway
        return None
    
    def execute_emergency_go_around(self, runway):
        """Force aircraft on runway to abort landing and go around."""
        if runway.occupied_by:
            aircraft = self.airport.get_aircraft(runway.occupied_by)
            if aircraft and aircraft.state == AircraftState.LANDING:
                # Clear runway
                runway.state = RunwayState.AVAILABLE
                runway.occupied_by = None
                aircraft.assigned_runway = None
                
                # Set aircraft to go-around state and move to holding pattern
                aircraft.state = AircraftState.GO_AROUND
                
                # Set target position for go-around (climb out and circle)
                center_x = self.airport.config.airport.airport_width / 2
                center_y = self.airport.config.airport.airport_height / 2
                go_around_radius = 300
                angle = random.uniform(0, 2 * math.pi)
                aircraft.target_position = Position(
                    center_x + math.cos(angle) * go_around_radius,
                    center_y + math.sin(angle) * go_around_radius
                )
                
                print(f"🔄 EMERGENCY GO-AROUND: {aircraft.callsign} aborted landing on runway {runway.id} for critical fuel emergency")
    
    def assign_emergency_landing(self, aircraft, runway):
        """Assign critical fuel aircraft to runway with emergency priority."""
        aircraft.assigned_runway = runway.id
        aircraft.target_position = runway.center_position
        aircraft.state = AircraftState.LANDING
        runway.state = RunwayState.OCCUPIED_LANDING
        runway.occupied_by = aircraft.id
        print(f"🚨 EMERGENCY LANDING: {aircraft.callsign} cleared for immediate landing on runway {runway.id} (CRITICAL FUEL: {aircraft.fuel:.1f}%)")
    
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
                    crash_details = f"Aircraft ran out of fuel (0.0%) while in state: {aircraft.state.value}"
                    if aircraft.state in [AircraftState.APPROACHING, AircraftState.HOLDING]:
                        crash_details += f" - CRITICAL: Aircraft needed immediate landing priority!"
                    elif aircraft.state == AircraftState.LANDING:
                        crash_details += f" - Aircraft was landing but fuel depleted during approach"
                else:
                    crash_reason = "MID-AIR COLLISION"
                    crash_details = f"Aircraft collided with another aircraft"
                
                # Store crash reason on aircraft for UI display
                aircraft.crash_reason = crash_reason
                
                # Log detailed crash information to AI decision log
                AI_LOGGER.error(f"🚨 AIRCRAFT CRASH - {aircraft.callsign} [{aircraft.aircraft_type}]")
                AI_LOGGER.error(f"├─ CRASH CAUSE: {crash_reason}")
                AI_LOGGER.error(f"├─ DETAILS: {crash_details}")
                AI_LOGGER.error(f"├─ Final Position: ({aircraft.position.x:.0f}, {aircraft.position.y:.0f})")
                AI_LOGGER.error(f"├─ Final State: {aircraft.state.value}")
                AI_LOGGER.error(f"├─ Final Fuel: {aircraft.fuel:.1f}%")
                AI_LOGGER.error(f"├─ Assigned Runway: {aircraft.assigned_runway}")
                AI_LOGGER.error(f"├─ Assigned Gate: {aircraft.assigned_gate}")
                
                # Add safety analysis
                if aircraft.fuel <= 0:
                    AI_LOGGER.error(f"├─ SAFETY ANALYSIS: This crash could have been prevented!")
                    if aircraft.state in [AircraftState.APPROACHING, AircraftState.HOLDING]:
                        AI_LOGGER.error(f"├─ PREVENTION: Aircraft with critical fuel should get IMMEDIATE landing priority")
                        AI_LOGGER.error(f"├─ PREVENTION: Never put fuel-critical aircraft on HOLD - find any available runway!")
                    AI_LOGGER.error(f"└─ AI GOAL: Prioritize fuel emergencies above all other considerations!")
                
                # Free up any assigned resources
                if aircraft.assigned_runway is not None:
                    runway = self.airport.runways[aircraft.assigned_runway]
                    runway.state = RunwayState.AVAILABLE
                    runway.occupied_by = None
                    aircraft.assigned_runway = None
                
                if aircraft.assigned_gate is not None:
                    gate = self.airport.gates[aircraft.assigned_gate]
                    gate.occupied_by = None
                    aircraft.assigned_gate = None
                
                # Console log for immediate visibility
                print(f"CRASH: {aircraft.callsign} - {crash_reason} (Fuel: {aircraft.fuel:.1f}%)")
        
        # Remove crashed aircraft after a delay (so they can be seen)
        # For now, keep them in the simulation for visualization
    
    def start(self):
        """Start the simulation."""
        self.running = True
        
        # Log dynamic spawn rate calculation
        config = get_config()
        dynamic_rate = config.get_dynamic_spawn_rate() if hasattr(config, 'get_dynamic_spawn_rate') else 1.0
        runways_count = config.airport.runways.count if hasattr(config, 'airport') and hasattr(config.airport, 'runways') else 2
        gates_count = config.airport.gates.count if hasattr(config, 'airport') and hasattr(config.airport, 'gates') else 4
        total_capacity = runways_count + gates_count
        print(f"Airport capacity: {runways_count} runways + {gates_count} gates = {total_capacity} total")
        print(f"Dynamic spawn rate: {dynamic_rate:.2f} aircraft/second (spawn interval: {1.0/dynamic_rate:.1f}s)")
    
    def stop(self):
        """Stop the simulation."""
        self.running = False
    
    def get_simulation_state(self) -> Dict:
        """Get current simulation state for display/AI interface."""
        return {
            'current_time': self.airport.current_time,
            'total_crashes': self.total_crashes,
            'crashed_aircraft': self.crashed_aircraft.copy(),
            'aircraft': [
                {
                    'id': a.id,
                    'callsign': a.callsign,
                    'position': {'x': a.position.x, 'y': a.position.y},
                    'state': a.state.value,
                    'assigned_runway': a.assigned_runway,
                    'assigned_gate': a.assigned_gate,
                    'aircraft_type': a.aircraft_type,
                    'fuel': a.fuel,
                    'is_low_fuel': a.is_low_fuel(),
                    'is_critical_fuel': a.is_critical_fuel(),
                    'fuel_priority': a.get_fuel_priority()
                }
                for a in self.airport.aircraft
            ],
            'runways': [
                {
                    'id': r.id,
                    'state': r.state.value,
                    'occupied_by': r.occupied_by,
                    'start_pos': {'x': r.start_position.x, 'y': r.start_position.y},
                    'end_pos': {'x': r.end_position.x, 'y': r.end_position.y}
                }
                for r in self.airport.runways
            ],
            'gates': [
                {
                    'id': g.id,
                    'position': {'x': g.position.x, 'y': g.position.y},
                    'occupied_by': g.occupied_by,
                    'available': g.is_available
                }
                for g in self.airport.gates
            ]
        } 