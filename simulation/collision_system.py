"""
Collision detection and avoidance system for the AI Airport Simulation.

This module handles all aspects of collision prevention including:
- Imminent collision detection
- Emergency avoidance maneuvers
- Collision response and recovery
- Dynamic avoidance positioning to prevent cascade scenarios
"""

import math
import random
from typing import Dict, List, Tuple, Optional

from models.aircraft import Aircraft, AircraftState
from models.airport import Airport
from models.position import Position


class CollisionSystem:
    """
    Manages collision detection and avoidance for aircraft in the simulation.
    
    The CollisionSystem provides multiple layers of collision protection:
    1. Long-range collision warning (500px) - AI-guided avoidance
    2. Medium-range automatic avoidance (200px) - Smart positioning
    3. Emergency collision avoidance (100px) - Automatic separation
    4. Collision detection (10px) - Crash handling
    """
    
    def __init__(self, airport: Airport):
        """
        Initialize the collision system.
        
        Args:
            airport (Airport): The airport instance to monitor for collisions
        """
        self.airport = airport
        
        # Collision avoidance throttling (aircraft_pair -> last_avoid_time)
        self.collision_avoidance_last_triggered: Dict[str, float] = {}
        self.collision_avoidance_interval = 1.5  # Faster response: 1.5 seconds instead of 2.0
        
        # Track aircraft in emergency separation to prevent repeated actions
        self.emergency_separation_active: Dict[str, float] = {}
        self.emergency_separation_duration = 5.0  # 5 seconds before aircraft can trigger emergency again
        
        # Collision zones - areas to avoid when placing avoidance positions
        self.collision_zones: List[Tuple[Position, float]] = []
        
    def update_collision_zones(self):
        """Update collision zones around all aircraft to prevent cascade collisions."""
        self.collision_zones.clear()
        
        for aircraft in self.airport.aircraft:
            if aircraft.state not in [AircraftState.CRASHED, AircraftState.DEPARTED]:
                # Create larger exclusion zones around each aircraft
                zone_radius = 150.0  # Larger than emergency distance to prevent clustering
                self.collision_zones.append((aircraft.position, zone_radius))
    
    def check_imminent_collisions(self) -> List[tuple]:
        """
        Check for imminent collisions and trigger avoidance measures.
        
        Returns:
            List[tuple]: List of aircraft pairs that need collision avoidance
        """
        # Update collision zones first
        self.update_collision_zones()
        
        aircraft_list = [a for a in self.airport.aircraft if a.state != AircraftState.CRASHED 
                        and a.state != AircraftState.DEPARTED]
        
        collision_pairs = []
        emergency_groups = []
        
        # Check all aircraft pairs
        for i in range(len(aircraft_list)):
            for j in range(i + 1, len(aircraft_list)):
                aircraft1 = aircraft_list[i]
                aircraft2 = aircraft_list[j]
                
                distance = aircraft1.distance_to(aircraft2)
                
                # IMMEDIATE EMERGENCY AVOIDANCE - if very close, don't wait for AI
                if distance <= 100.0:
                    # Check if either aircraft is already in emergency separation
                    key1 = aircraft1.id
                    key2 = aircraft2.id
                    current_time = self.airport.current_time
                    
                    if (key1 not in self.emergency_separation_active and 
                        key2 not in self.emergency_separation_active):
                        
                        print(f"🚨 EMERGENCY COLLISION AVOIDANCE: {aircraft1.callsign} and {aircraft2.callsign} only {distance:.0f}px apart!")
                        
                        # Mark both aircraft as in emergency separation
                        self.emergency_separation_active[key1] = current_time
                        self.emergency_separation_active[key2] = current_time
                        
                        # Execute immediate avoidance for both aircraft
                        self.execute_emergency_avoidance(aircraft1, aircraft2)
                        continue  # Skip normal collision avoidance for this pair
                
                # SMART AVOIDANCE LAYER - medium range with predictive positioning
                elif distance <= 200.0:
                    pair_key = f"{min(aircraft1.id, aircraft2.id)}_{max(aircraft1.id, aircraft2.id)}"
                    current_time = self.airport.current_time
                    
                    if (pair_key not in self.collision_avoidance_last_triggered or 
                        current_time - self.collision_avoidance_last_triggered[pair_key] >= self.collision_avoidance_interval):
                        
                        # Use smart positioning to avoid cascade collisions
                        avoid_aircraft = self._select_avoidance_aircraft(aircraft1, aircraft2)
                        safe_position = self._find_safe_avoidance_position(avoid_aircraft, aircraft_list)
                        
                        if safe_position:
                            self.collision_avoidance_last_triggered[pair_key] = current_time
                            self._execute_smart_avoidance(avoid_aircraft, safe_position)
                            print(f"🔄 SMART AVOIDANCE: {avoid_aircraft.callsign} moving to safe position")
                            continue
                
                # Normal AI collision avoidance for longer distances (500px instead of 400px)
                if aircraft1.is_collision_imminent(aircraft2, warning_distance=500.0):
                    # Check throttling to avoid repeated avoidance for same pair
                    pair_key = f"{min(aircraft1.id, aircraft2.id)}_{max(aircraft1.id, aircraft2.id)}"
                    current_time = self.airport.current_time
                    
                    if (pair_key not in self.collision_avoidance_last_triggered or 
                        current_time - self.collision_avoidance_last_triggered[pair_key] >= self.collision_avoidance_interval):
                        
                        # Update throttling timestamp
                        self.collision_avoidance_last_triggered[pair_key] = current_time
                        
                        # Determine which aircraft should avoid
                        avoid_aircraft = self._select_avoidance_aircraft(aircraft1, aircraft2)
                        conflicting_aircraft = aircraft1 if avoid_aircraft == aircraft2 else aircraft2
                        
                        collision_pairs.append((avoid_aircraft, conflicting_aircraft))
        
        # Clean up expired emergency separation entries
        current_time = self.airport.current_time
        expired_keys = [k for k, v in self.emergency_separation_active.items() 
                       if current_time - v > self.emergency_separation_duration]
        for key in expired_keys:
            del self.emergency_separation_active[key]
        
        return collision_pairs
    
    def _find_safe_avoidance_position(self, aircraft: Aircraft, all_aircraft: List[Aircraft]) -> Optional[Position]:
        """
        Find a safe avoidance position that doesn't conflict with other aircraft.
        
        Args:
            aircraft: The aircraft needing avoidance position
            all_aircraft: List of all active aircraft
            
        Returns:
            Optional[Position]: Safe position or None if no safe position found
        """
        center_x = self.airport.config.airport.airport_width / 2
        center_y = self.airport.config.airport.airport_height / 2
        
        # Try multiple avoidance radii and positions
        radii = [300, 400, 500]  # Different distances from center
        angles_per_radius = 16   # More positions to try
        
        for radius in radii:
            for i in range(angles_per_radius):
                angle = (i / angles_per_radius) * 2 * math.pi
                
                candidate_x = center_x + math.cos(angle) * radius
                candidate_y = center_y + math.sin(angle) * radius
                
                # Ensure position is within bounds
                margin = 80
                candidate_x = max(margin, min(self.airport.config.airport.airport_width - margin, candidate_x))
                candidate_y = max(margin, min(self.airport.config.airport.airport_height - margin, candidate_y))
                
                candidate_pos = Position(candidate_x, candidate_y)
                
                # Check if this position is safe (far from all other aircraft)
                if self._is_position_safe(candidate_pos, all_aircraft, aircraft, min_distance=180.0):
                    return candidate_pos
        
        # Fallback: find the position with maximum distance to nearest aircraft
        return self._find_maximum_separation_position(aircraft, all_aircraft)
    
    def _is_position_safe(self, position: Position, all_aircraft: List[Aircraft], 
                         exclude_aircraft: Aircraft, min_distance: float = 150.0) -> bool:
        """
        Check if a position is safe from all other aircraft.
        
        Args:
            position: Position to check
            all_aircraft: List of all aircraft
            exclude_aircraft: Aircraft to exclude from check
            min_distance: Minimum safe distance
            
        Returns:
            bool: True if position is safe
        """
        for other_aircraft in all_aircraft:
            if (other_aircraft != exclude_aircraft and 
                other_aircraft.state not in [AircraftState.CRASHED, AircraftState.DEPARTED]):
                
                # Check distance to aircraft current position
                if position.distance_to(other_aircraft.position) < min_distance:
                    return False
                
                # Check distance to aircraft target position (predictive)
                if hasattr(other_aircraft, 'target_position'):
                    if position.distance_to(other_aircraft.target_position) < min_distance:
                        return False
        
        return True
    
    def _find_maximum_separation_position(self, aircraft: Aircraft, all_aircraft: List[Aircraft]) -> Position:
        """
        Find position that maximizes distance to all other aircraft.
        
        Args:
            aircraft: Aircraft needing position
            all_aircraft: All active aircraft
            
        Returns:
            Position: Position with maximum separation
        """
        center_x = self.airport.config.airport.airport_width / 2
        center_y = self.airport.config.airport.airport_height / 2
        
        best_position = Position(center_x, center_y)
        best_min_distance = 0
        
        # Sample positions in a grid pattern
        for x in range(100, self.airport.config.airport.airport_width - 100, 100):
            for y in range(100, self.airport.config.airport.airport_height - 100, 100):
                candidate_pos = Position(x, y)
                
                # Find minimum distance to any other aircraft
                min_distance = float('inf')
                for other_aircraft in all_aircraft:
                    if (other_aircraft != aircraft and 
                        other_aircraft.state not in [AircraftState.CRASHED, AircraftState.DEPARTED]):
                        distance = candidate_pos.distance_to(other_aircraft.position)
                        min_distance = min(min_distance, distance)
                
                # Update best position if this one has better separation
                if min_distance > best_min_distance:
                    best_min_distance = min_distance
                    best_position = candidate_pos
        
        return best_position
    
    def _execute_smart_avoidance(self, aircraft: Aircraft, safe_position: Position):
        """
        Execute smart avoidance maneuver to a calculated safe position.
        
        Args:
            aircraft: Aircraft to move
            safe_position: Pre-calculated safe position
        """
        aircraft.target_position = safe_position
        aircraft.state = AircraftState.HOLDING
        
        print(f"SMART AVOIDANCE: {aircraft.callsign} → ({safe_position.x:.0f},{safe_position.y:.0f})")
    
    def _select_avoidance_aircraft(self, aircraft1: Aircraft, aircraft2: Aircraft) -> Aircraft:
        """
        Select which aircraft should perform collision avoidance based on fuel priority.
        
        Args:
            aircraft1 (Aircraft): First aircraft in potential collision
            aircraft2 (Aircraft): Second aircraft in potential collision
            
        Returns:
            Aircraft: The aircraft that should perform avoidance maneuver
        """
        # Priority: avoid for non-critical fuel aircraft first
        if not aircraft1.is_critical_fuel() and not aircraft2.is_critical_fuel():
            # Neither critical, choose aircraft with higher fuel
            return aircraft1 if aircraft1.fuel >= aircraft2.fuel else aircraft2
        elif aircraft1.is_critical_fuel() and not aircraft2.is_critical_fuel():
            # aircraft1 is critical, avoid with aircraft2
            return aircraft2
        elif not aircraft1.is_critical_fuel() and aircraft2.is_critical_fuel():
            # aircraft2 is critical, avoid with aircraft1
            return aircraft1
        else:
            # Both critical, choose aircraft with higher fuel
            return aircraft1 if aircraft1.fuel >= aircraft2.fuel else aircraft2
    
    def execute_emergency_avoidance(self, aircraft1: Aircraft, aircraft2: Aircraft):
        """
        Execute immediate emergency avoidance for both aircraft to prevent collision.
        
        Args:
            aircraft1 (Aircraft): First aircraft to separate
            aircraft2 (Aircraft): Second aircraft to separate
        """
        # Calculate direction away from each other
        diff_x = aircraft1.position.x - aircraft2.position.x
        diff_y = aircraft1.position.y - aircraft2.position.y
        
        # Normalize and amplify the separation
        distance = math.sqrt(diff_x**2 + diff_y**2)
        if distance > 0:
            # Unit vector pointing from aircraft2 to aircraft1
            unit_x = diff_x / distance
            unit_y = diff_y / distance
            
            # Move aircraft away from each other with larger separation
            separation_distance = 250  # Increased from 200 to 250 pixels
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
            
            # Verify the new positions don't create new conflicts
            all_aircraft = [a for a in self.airport.aircraft 
                           if a.state not in [AircraftState.CRASHED, AircraftState.DEPARTED]]
            
            pos1 = Position(new_x1, new_y1)
            pos2 = Position(new_x2, new_y2)
            
            # If positions conflict with others, use maximum separation strategy
            if not self._is_position_safe(pos1, all_aircraft, aircraft1, min_distance=120.0):
                pos1 = self._find_maximum_separation_position(aircraft1, all_aircraft)
            
            if not self._is_position_safe(pos2, all_aircraft, aircraft2, min_distance=120.0):
                pos2 = self._find_maximum_separation_position(aircraft2, all_aircraft)
            
            # Set new target positions
            aircraft1.target_position = pos1
            aircraft2.target_position = pos2
            
            # Set both to holding state
            aircraft1.state = AircraftState.HOLDING
            aircraft2.state = AircraftState.HOLDING
            
            print(f"EMERGENCY SEPARATION: {aircraft1.callsign} → ({pos1.x:.0f},{pos1.y:.0f}), {aircraft2.callsign} → ({pos2.x:.0f},{pos2.y:.0f})")
    
    def execute_collision_avoidance(self, aircraft: Aircraft, avoidance_position: int):
        """
        Execute collision avoidance maneuver by moving aircraft to safe position.
        
        Args:
            aircraft (Aircraft): The aircraft to move to safety
            avoidance_position (int): Position index (0-7) around airport center
        """
        # Use smart positioning instead of fixed positions
        all_aircraft = [a for a in self.airport.aircraft 
                       if a.state not in [AircraftState.CRASHED, AircraftState.DEPARTED]]
        
        safe_position = self._find_safe_avoidance_position(aircraft, all_aircraft)
        
        if safe_position:
            aircraft.target_position = safe_position
            aircraft.state = AircraftState.HOLDING
            print(f"COLLISION AVOIDANCE: {aircraft.callsign} moving to safe position ({safe_position.x:.0f},{safe_position.y:.0f})")
        else:
            # Fallback to original method if no safe position found
            center_x = self.airport.config.airport.airport_width / 2
            center_y = self.airport.config.airport.airport_height / 2
            avoidance_radius = 350  # Increased radius for better separation
            
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
            aircraft.state = AircraftState.HOLDING
            
            print(f"COLLISION AVOIDANCE: {aircraft.callsign} moving to fallback position {avoidance_position}")
    
    def check_collisions(self) -> List[tuple]:
        """
        Check for actual collisions between aircraft.
        
        Returns:
            List[tuple]: List of aircraft pairs that have collided
        """
        aircraft_list = [a for a in self.airport.aircraft if a.state != AircraftState.CRASHED 
                        and a.state != AircraftState.DEPARTED]
        
        collisions = []
        
        for i in range(len(aircraft_list)):
            for j in range(i + 1, len(aircraft_list)):
                aircraft1 = aircraft_list[i]
                aircraft2 = aircraft_list[j]
                
                if aircraft1.check_collision(aircraft2):
                    collisions.append((aircraft1, aircraft2))
                    
        return collisions
    
    def handle_collisions(self, collisions: List[tuple]):
        """
        Handle aircraft collisions by marking them as crashed.
        
        Args:
            collisions (List[tuple]): List of aircraft pairs that have collided
        """
        for aircraft1, aircraft2 in collisions:
            # Both aircraft crash
            aircraft1.state = AircraftState.CRASHED
            aircraft2.state = AircraftState.CRASHED
            aircraft1.crash_reason = "MID-AIR COLLISION"
            aircraft2.crash_reason = "MID-AIR COLLISION"
            
            print(f"COLLISION! {aircraft1.callsign} and {aircraft2.callsign} crashed!") 