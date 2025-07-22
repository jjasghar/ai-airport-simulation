"""
Fuel management and emergency system for the AI Airport Simulation.

This module handles all fuel-related functionality including:
- Fuel emergency detection and monitoring
- Emergency runway clearing for critical fuel aircraft
- Go-around procedures for non-critical aircraft
- Fuel priority management
"""

import math
import random
from typing import Dict, List

from models.aircraft import Aircraft, AircraftState
from models.airport import Airport, RunwayState
from models.position import Position


class FuelSystem:
    """
    Manages fuel emergencies and critical fuel prioritization for aircraft.
    
    The FuelSystem ensures aircraft safety by:
    - Monitoring fuel levels continuously
    - Detecting critical fuel emergencies
    - Clearing runways for emergency landings
    - Managing go-around procedures
    """
    
    def __init__(self, airport: Airport):
        """
        Initialize the fuel management system.
        
        Args:
            airport (Airport): The airport instance to monitor for fuel emergencies
        """
        self.airport = airport
        
        # Fuel emergency logging throttling (callsign -> last_log_time)
        self.fuel_emergency_last_logged: Dict[str, float] = {}
        self.fuel_emergency_log_interval = 10.0  # Log at most once every 10 seconds
        
        # New throttling system for improved monitoring
        self.fuel_emergency_log_throttle: Dict[str, float] = {}
        self.fuel_log_throttle_interval = 10.0  # Log at most once every 10 seconds
        
    def monitor_fuel_levels(self, dt: float):
        """
        Monitor fuel levels and trigger appropriate responses for low/critical fuel aircraft.
        
        This method handles:
        - Fuel emergency logging
        - Critical fuel aircraft priority
        - Fuel status notifications
        - Holding pattern fuel monitoring
        
        Args:
            dt (float): Time step in seconds since last update
        """
        current_time = self.airport.current_time
        
        for aircraft in self.airport.aircraft:
            if aircraft.state in [AircraftState.CRASHED, AircraftState.DEPARTED]:
                continue
            
            # Monitor fuel emergencies (throttled logging)
            if aircraft.is_critical_fuel():
                throttle_key = f"critical_{aircraft.id}"
                if (throttle_key not in self.fuel_emergency_log_throttle or 
                    current_time - self.fuel_emergency_log_throttle[throttle_key] >= self.fuel_log_throttle_interval):
                    
                    self.fuel_emergency_log_throttle[throttle_key] = current_time
                    if aircraft.state in [AircraftState.APPROACHING, AircraftState.HOLDING]:
                        print(f"⛽ CRITICAL FUEL: {aircraft.callsign} has {aircraft.fuel:.1f}% fuel - IMMEDIATE LANDING REQUIRED!")
                        
                        # For holding aircraft, check if they should exit holding immediately
                        if aircraft.state == AircraftState.HOLDING:
                            safe_time = aircraft.get_safe_holding_time()
                            print(f"⚠️  HOLDING ALERT: {aircraft.callsign} in critical fuel state with {safe_time:.1f} minutes safe holding time")
            
            elif aircraft.is_low_fuel():
                throttle_key = f"low_{aircraft.id}"
                if (throttle_key not in self.fuel_emergency_log_throttle or 
                    current_time - self.fuel_emergency_log_throttle[throttle_key] >= self.fuel_log_throttle_interval):
                    
                    self.fuel_emergency_log_throttle[throttle_key] = current_time
                    if aircraft.state in [AircraftState.APPROACHING, AircraftState.HOLDING]:
                        if aircraft.state == AircraftState.HOLDING:
                            safe_time = aircraft.get_safe_holding_time()
                            print(f"⚠️  LOW FUEL HOLDING: {aircraft.callsign} has {aircraft.fuel:.1f}% fuel, {safe_time:.1f} minutes safe holding time")
                        else:
                            print(f"⚠️  LOW FUEL: {aircraft.callsign} has {aircraft.fuel:.1f}% fuel - priority landing needed")
            
            # Special monitoring for aircraft in holding patterns
            if aircraft.state == AircraftState.HOLDING:
                self._monitor_holding_aircraft_fuel(aircraft, current_time)
            
            # Check for aircraft running out of fuel
            if aircraft.fuel <= 0.0 and aircraft.state != AircraftState.CRASHED:
                aircraft.state = AircraftState.CRASHED
                aircraft.crash_reason = "FUEL EXHAUSTION"
                print(f"💥 FUEL CRASH: {aircraft.callsign} crashed due to fuel exhaustion!")
    
    def _monitor_holding_aircraft_fuel(self, aircraft: Aircraft, current_time: float):
        """
        Monitor fuel levels for aircraft in holding patterns with special attention.
        
        Args:
            aircraft (Aircraft): Aircraft in holding pattern
            current_time (float): Current simulation time
        """
        # Check if this is airborne or ground holding
        is_airborne = not (hasattr(aircraft, 'waiting_for_runway') and aircraft.waiting_for_runway)
        
        safe_holding_time = aircraft.get_safe_holding_time()
        
        # Create holding-specific throttle key
        throttle_key = f"holding_{aircraft.id}"
        
        # Different warning thresholds for airborne vs ground holding
        if is_airborne:
            # Airborne holding - more urgent fuel monitoring
            if safe_holding_time < 5.0 and aircraft.fuel > 15.0:  # Warning when < 5 minutes left
                if (throttle_key not in self.fuel_emergency_log_throttle or 
                    current_time - self.fuel_emergency_log_throttle[throttle_key] >= 30.0):  # Every 30 seconds
                    
                    self.fuel_emergency_log_throttle[throttle_key] = current_time
                    print(f"⏰ HOLDING TIME WARNING: {aircraft.callsign} airborne holding - only {safe_holding_time:.1f} minutes fuel remaining")
            
            elif safe_holding_time < 2.0:  # Critical - less than 2 minutes
                if (throttle_key not in self.fuel_emergency_log_throttle or 
                    current_time - self.fuel_emergency_log_throttle[throttle_key] >= 10.0):  # Every 10 seconds
                    
                    self.fuel_emergency_log_throttle[throttle_key] = current_time
                    print(f"🚨 HOLDING EMERGENCY: {aircraft.callsign} MUST EXIT HOLDING NOW - {safe_holding_time:.1f} minutes fuel left!")
        
        else:
            # Ground holding - less critical but still monitor
            if safe_holding_time < 10.0 and aircraft.fuel > 5.0:
                if (throttle_key not in self.fuel_emergency_log_throttle or 
                    current_time - self.fuel_emergency_log_throttle[throttle_key] >= 60.0):  # Every minute
                    
                    self.fuel_emergency_log_throttle[throttle_key] = current_time
                    print(f"⏳ GROUND HOLDING: {aircraft.callsign} ground holding - {safe_holding_time:.1f} minutes fuel remaining")
    
    def get_holding_fuel_status(self, aircraft: Aircraft) -> str:
        """
        Get fuel status description for aircraft in holding patterns.
        
        Args:
            aircraft (Aircraft): Aircraft to check
            
        Returns:
            str: Fuel status description
        """
        if aircraft.state != AircraftState.HOLDING:
            return "Not in holding"
        
        safe_time = aircraft.get_safe_holding_time()
        is_airborne = not (hasattr(aircraft, 'waiting_for_runway') and aircraft.waiting_for_runway)
        
        holding_type = "Airborne" if is_airborne else "Ground"
        
        if aircraft.is_critical_fuel():
            return f"{holding_type} holding - CRITICAL fuel ({aircraft.fuel:.1f}%, {safe_time:.1f}min left)"
        elif aircraft.is_low_fuel():
            return f"{holding_type} holding - LOW fuel ({aircraft.fuel:.1f}%, {safe_time:.1f}min left)"
        elif safe_time < 5.0:
            return f"{holding_type} holding - WARNING ({aircraft.fuel:.1f}%, {safe_time:.1f}min left)"
        else:
            return f"{holding_type} holding - OK ({aircraft.fuel:.1f}%, {safe_time:.1f}min left)"
    
    def handle_critical_fuel_emergencies(self):
        """
        Handle critical fuel emergencies by clearing runways if necessary.
        
        This method implements emergency procedures for aircraft with critical fuel:
        1. Identifies aircraft needing immediate landing
        2. Assigns available runways immediately
        3. Clears occupied runways by forcing go-arounds
        4. Prioritizes by fuel level (most critical first)
        """
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
        """
        Find the best runway to clear for a critical fuel emergency.
        
        Returns:
            Runway: The runway that should be cleared, or None if no suitable runway
        """
        for runway in self.airport.runways:
            if runway.occupied_by and runway.state == RunwayState.OCCUPIED_LANDING:
                # Find the aircraft using this runway
                landing_aircraft = self.airport.get_aircraft(runway.occupied_by)
                if landing_aircraft and not landing_aircraft.is_critical_fuel():
                    # This runway has a non-critical aircraft landing - can be cleared
                    return runway
        return None
    
    def execute_emergency_go_around(self, runway):
        """
        Force aircraft on runway to abort landing and go around.
        
        Args:
            runway: The runway to clear by forcing a go-around
        """
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
        """
        Assign critical fuel aircraft to runway with emergency priority.
        
        Args:
            aircraft: The critical fuel aircraft needing immediate landing
            runway: The runway to assign for emergency landing
        """
        aircraft.assigned_runway = runway.id
        aircraft.target_position = runway.center_position
        aircraft.state = AircraftState.LANDING
        runway.state = RunwayState.OCCUPIED_LANDING
        runway.occupied_by = aircraft.id
        print(f"🚨 EMERGENCY LANDING: {aircraft.callsign} cleared for immediate landing on runway {runway.id} (CRITICAL FUEL: {aircraft.fuel:.1f}%)")
    
    def get_fuel_priority_aircraft(self) -> List[Aircraft]:
        """
        Get list of aircraft sorted by fuel priority (most critical first).
        
        Returns:
            List[Aircraft]: Aircraft sorted by fuel priority level
        """
        active_aircraft = [a for a in self.airport.aircraft 
                          if a.state not in [AircraftState.CRASHED, AircraftState.DEPARTED]]
        
        # Sort by fuel priority (higher priority first, then by fuel level)
        return sorted(active_aircraft, 
                     key=lambda a: (a.get_fuel_priority(), -a.fuel), 
                     reverse=True)
    
    def get_fuel_emergency_count(self) -> tuple:
        """
        Get count of aircraft in various fuel emergency states.
        
        Returns:
            tuple: (critical_fuel_count, low_fuel_count)
        """
        critical_count = 0
        low_fuel_count = 0
        
        for aircraft in self.airport.aircraft:
            if aircraft.state not in [AircraftState.CRASHED, AircraftState.DEPARTED]:
                if aircraft.is_critical_fuel():
                    critical_count += 1
                elif aircraft.is_low_fuel():
                    low_fuel_count += 1
        
        return critical_count, low_fuel_count 