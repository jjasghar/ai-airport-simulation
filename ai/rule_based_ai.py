"""
Rule-based AI implementation for the AI Airport Simulation.

This module provides a deterministic, rule-based approach to air traffic control
that doesn't require external AI services. It uses predefined logic to make
safe and efficient decisions based on current airport conditions.
"""

import time
from typing import Dict, Any, Optional, List

from .base_ai import BaseAI, AIResponse


class RuleBasedAI(BaseAI):
    """
    Rule-based air traffic control implementation.
    
    This AI uses deterministic rules and priority systems to make air traffic
    control decisions. It prioritizes safety above all else, followed by
    efficiency and airport capacity optimization.
    
    Decision Priority:
    1. Fuel emergencies (critical fuel < 15%)
    2. Low fuel aircraft (< 25%) 
    3. Collision avoidance
    4. Normal traffic flow
    5. Airport capacity optimization
    """
    
    def __init__(self):
        """Initialize the rule-based AI implementation."""
        super().__init__("Rule-Based AI")
        
        # Rule-based AI is always "connected" since it's local
        self.is_connected = True
    
    def connect(self) -> bool:
        """
        Rule-based AI doesn't need external connections.
        
        Returns:
            bool: Always True for rule-based AI
        """
        self.is_connected = True
        return True
    
    def disconnect(self) -> None:
        """Rule-based AI doesn't need to disconnect from anything."""
        pass
    
    def make_decision(self, aircraft: Dict[str, Any], airport_state: Dict[str, Any], 
                     config: Any) -> AIResponse:
        """
        Make an air traffic control decision using rule-based logic.
        
        Args:
            aircraft (Dict[str, Any]): Current aircraft state
            airport_state (Dict[str, Any]): Current airport state
            config (Any): Configuration object
            
        Returns:
            AIResponse: AI decision and reasoning
        """
        start_time = time.time()
        
        # Extract information for decision making
        aircraft_info = self._extract_aircraft_info(aircraft)
        airport_info = self._extract_airport_info(airport_state)
        
        # Apply rule-based decision logic
        decision_result = self._apply_decision_rules(aircraft_info, airport_info)
        
        # Create response with processing time
        response = AIResponse(
            decision=decision_result['decision'],
            target=decision_result['target'],
            reasoning=decision_result['reasoning'],
            confidence=1.0,  # Rule-based decisions are deterministic
            decision_time=time.time(),
            processing_time=time.time() - start_time
        )
        
        return response
    
    def _apply_decision_rules(self, aircraft: Dict[str, Any], 
                             airport: Dict[str, Any]) -> Dict[str, Any]:
        """
        Apply rule-based decision logic based on aircraft and airport state.
        
        Args:
            aircraft (Dict[str, Any]): Aircraft information
            airport (Dict[str, Any]): Airport information
            
        Returns:
            Dict[str, Any]: Decision result with decision, target, and reasoning
        """
        state = aircraft['state']
        fuel = aircraft['fuel']
        is_critical_fuel = aircraft['is_critical_fuel']
        is_low_fuel = aircraft['is_low_fuel']
        assigned_runway = aircraft['assigned_runway']
        assigned_gate = aircraft['assigned_gate']
        
        # Rule 1: Handle fuel emergencies first (highest priority)
        if is_critical_fuel:
            return self._handle_fuel_emergency(aircraft, airport)
        
        # Rule 2: Handle low fuel aircraft (high priority)
        if is_low_fuel:
            return self._handle_low_fuel_aircraft(aircraft, airport)
        
        # Rule 3: Handle aircraft based on current state
        if state == 'approaching':
            return self._handle_approaching_aircraft(aircraft, airport)
        elif state == 'landing':
            return self._handle_landing_aircraft(aircraft, airport)
        elif state == 'at_gate':
            return self._handle_aircraft_at_gate(aircraft, airport)
        elif state == 'holding':
            return self._handle_holding_aircraft(aircraft, airport)
        else:
            # Default case - wait for better conditions
            return {
                'decision': 'wait',
                'target': None,
                'reasoning': f"No specific rule for aircraft state: {state}"
            }
    
    def _handle_fuel_emergency(self, aircraft: Dict[str, Any], 
                              airport: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle aircraft with critical fuel levels.
        
        Args:
            aircraft (Dict[str, Any]): Aircraft information
            airport (Dict[str, Any]): Airport information
            
        Returns:
            Dict[str, Any]: Emergency landing decision
        """
        # Find any available runway for emergency landing
        available_runway = self._find_best_runway(airport, prefer_available=True)
        
        if available_runway is not None:
            return {
                'decision': 'land',
                'target': str(available_runway),
                'reasoning': f"FUEL EMERGENCY: {aircraft['callsign']} has {aircraft['fuel']:.1f}% fuel - immediate landing required!"
            }
        else:
            # No runway available - clear the best one for emergency
            best_runway = self._find_best_runway(airport, prefer_available=False)
            return {
                'decision': 'land',
                'target': str(best_runway),
                'reasoning': f"FUEL EMERGENCY: {aircraft['callsign']} has {aircraft['fuel']:.1f}% fuel - clearing runway {best_runway} for emergency landing!"
            }
    
    def _handle_low_fuel_aircraft(self, aircraft: Dict[str, Any], 
                                 airport: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle aircraft with low fuel levels.
        
        Args:
            aircraft (Dict[str, Any]): Aircraft information
            airport (Dict[str, Any]): Airport information
            
        Returns:
            Dict[str, Any]: Priority landing decision
        """
        state = aircraft['state']
        
        if state == 'approaching':
            # Assign to best available runway
            runway = self._find_best_runway(airport, prefer_available=True)
            if runway is not None:
                return {
                    'decision': 'assign_runway',
                    'target': str(runway),
                    'reasoning': f"LOW FUEL: {aircraft['callsign']} has {aircraft['fuel']:.1f}% fuel - priority runway assignment"
                }
            else:
                # If no runway available, wait briefly but don't hold
                return {
                    'decision': 'wait',
                    'target': None,
                    'reasoning': f"LOW FUEL: {aircraft['callsign']} waiting for runway (no holding pattern)"
                }
        
        elif state == 'landing':
            # Continue landing process
            return {
                'decision': 'land',
                'target': str(aircraft['assigned_runway']) if aircraft['assigned_runway'] is not None else '0',
                'reasoning': f"LOW FUEL: {aircraft['callsign']} continuing priority landing"
            }
        
        else:
            # For other states, proceed normally but with priority
            return self._handle_normal_aircraft_state(aircraft, airport, priority=True)
    
    def _handle_approaching_aircraft(self, aircraft: Dict[str, Any], 
                                    airport: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle aircraft that are approaching the airport.
        
        Args:
            aircraft (Dict[str, Any]): Aircraft information
            airport (Dict[str, Any]): Airport information
            
        Returns:
            Dict[str, Any]: Runway assignment or holding decision
        """
        # Try to assign a runway
        runway = self._find_best_runway(airport, prefer_available=True)
        
        if runway is not None:
            return {
                'decision': 'assign_runway',
                'target': str(runway),
                'reasoning': f"Assigning runway {runway} to approaching aircraft {aircraft['callsign']}"
            }
        else:
            # No runway available - check if aircraft can safely hold
            fuel_level = aircraft['fuel']
            
            # Check if aircraft has enough fuel for holding pattern (minimum 10 minutes)
            if fuel_level > 30.0:  # Good fuel level for holding
                return {
                    'decision': 'hold',
                    'target': None,
                    'reasoning': f"No runway available - {aircraft['callsign']} entering holding pattern (fuel: {fuel_level:.1f}%)"
                }
            elif fuel_level > 20.0:  # Marginal fuel - short hold only
                return {
                    'decision': 'hold',
                    'target': None,
                    'reasoning': f"No runway available - {aircraft['callsign']} SHORT holding pattern (fuel: {fuel_level:.1f}% - monitor closely)"
                }
            else:
                # Too low fuel for holding - force landing on any runway
                best_runway = self._find_best_runway(airport, prefer_available=False)
                return {
                    'decision': 'land',
                    'target': str(best_runway),
                    'reasoning': f"FUEL EMERGENCY: {aircraft['callsign']} fuel too low for holding ({fuel_level:.1f}%) - forcing landing on runway {best_runway}"
                }

    def _handle_landing_aircraft(self, aircraft: Dict[str, Any], 
                                airport: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle aircraft that are in landing state.
        
        Args:
            aircraft (Dict[str, Any]): Aircraft information
            airport (Dict[str, Any]): Airport information
            
        Returns:
            Dict[str, Any]: Landing continuation decision
        """
        # Aircraft is already landing - let them continue
        return {
            'decision': 'land',
            'target': str(aircraft['assigned_runway']) if aircraft['assigned_runway'] is not None else '0',
            'reasoning': f"{aircraft['callsign']} continuing landing on runway {aircraft['assigned_runway']}"
        }

    def _handle_aircraft_at_gate(self, aircraft: Dict[str, Any], 
                                airport: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle aircraft at gates that may be ready for departure.
        
        Args:
            aircraft (Dict[str, Any]): Aircraft information
            airport (Dict[str, Any]): Airport information
            
        Returns:
            Dict[str, Any]: Departure or wait decision
        """
        # Simple departure logic - aircraft have a chance to depart
        import random
        if random.random() < 0.1:  # 10% chance per decision cycle
            runway = self._find_best_runway(airport, prefer_available=True)
            if runway is not None:
                return {
                    'decision': 'takeoff',
                    'target': str(runway),
                    'reasoning': f"Clearing {aircraft['callsign']} for departure on runway {runway}"
                }
            else:
                # No runway available - check if aircraft should wait at gate or move to holding
                # Aircraft with full fuel can afford to wait longer at gate
                return {
                    'decision': 'wait',
                    'target': None,
                    'reasoning': f"No runway available - {aircraft['callsign']} waiting at gate"
                }
        else:
            return {
                'decision': 'wait',
                'target': None,
                'reasoning': f"{aircraft['callsign']} completing gate procedures"
            }

    def _handle_holding_aircraft(self, aircraft: Dict[str, Any], 
                                airport: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle aircraft in holding patterns.
        
        Args:
            aircraft (Dict[str, Any]): Aircraft information
            airport (Dict[str, Any]): Airport information
            
        Returns:
            Dict[str, Any]: Landing or continued holding decision
        """
        fuel_level = aircraft['fuel']
        
        # Priority: try to get aircraft out of holding pattern based on fuel level
        if fuel_level < 15.0:
            # Critical fuel - force landing immediately
            best_runway = self._find_best_runway(airport, prefer_available=False)
            return {
                'decision': 'land',
                'target': str(best_runway),
                'reasoning': f"CRITICAL FUEL EMERGENCY: {aircraft['callsign']} ({fuel_level:.1f}% fuel) - immediate landing runway {best_runway}"
            }
        elif fuel_level < 25.0:
            # Low fuel - priority runway assignment
            runway = self._find_best_runway(airport, prefer_available=True)
            if runway is not None:
                return {
                    'decision': 'assign_runway',
                    'target': str(runway),
                    'reasoning': f"LOW FUEL PRIORITY: {aircraft['callsign']} ({fuel_level:.1f}% fuel) - priority runway {runway}"
                }
            else:
                # Still no runway - but continue holding briefly
                return {
                    'decision': 'hold',
                    'target': None,
                    'reasoning': f"LOW FUEL: {aircraft['callsign']} ({fuel_level:.1f}% fuel) - continuing holding briefly"
                }
        else:
            # Normal fuel level - try to assign runway if available
            runway = self._find_best_runway(airport, prefer_available=True)
            if runway is not None:
                return {
                    'decision': 'assign_runway',
                    'target': str(runway),
                    'reasoning': f"Runway {runway} available - bringing {aircraft['callsign']} out of holding"
                }
            else:
                # Continue holding - fuel level is safe
                safe_holding_time = self._calculate_safe_holding_time(fuel_level)
                return {
                    'decision': 'hold',
                    'target': None,
                    'reasoning': f"{aircraft['callsign']} continuing holding pattern ({fuel_level:.1f}% fuel, {safe_holding_time:.1f}min safe holding time)"
                }
    
    def _calculate_safe_holding_time(self, fuel_level: float) -> float:
        """
        Calculate safe holding time based on fuel level.
        
        Args:
            fuel_level (float): Current fuel percentage
            
        Returns:
            float: Safe holding time in minutes
        """
        # Simplified calculation based on airborne holding fuel consumption
        # 0.20% fuel per second = 12% per minute
        safety_margin = 10.0  # Keep 10% fuel as safety margin
        available_fuel = max(0, fuel_level - safety_margin)
        fuel_rate_per_minute = 12.0  # 12% per minute
        
        if fuel_rate_per_minute > 0:
            return available_fuel / fuel_rate_per_minute
        else:
            return 0.0
    
    def _handle_normal_aircraft_state(self, aircraft: Dict[str, Any], 
                                     airport: Dict[str, Any], priority: bool = False) -> Dict[str, Any]:
        """
        Handle aircraft in normal operational states.
        
        Args:
            aircraft (Dict[str, Any]): Aircraft information
            airport (Dict[str, Any]): Airport information
            priority (bool): Whether this aircraft has priority
            
        Returns:
            Dict[str, Any]: Appropriate decision for the aircraft state
        """
        state = aircraft['state']
        priority_text = "PRIORITY: " if priority else ""
        
        return {
            'decision': 'wait',
            'target': None,
            'reasoning': f"{priority_text}Normal handling for {aircraft['callsign']} in state {state}"
        }
    
    def _find_best_runway(self, airport: Dict[str, Any], prefer_available: bool = True) -> Optional[int]:
        """
        Find the best runway for assignment.
        
        Args:
            airport (Dict[str, Any]): Airport information
            prefer_available (bool): Whether to prefer available runways
            
        Returns:
            Optional[int]: Best runway ID, or None if no suitable runway
        """
        runways = airport.get('runways', [])
        
        if not runways:
            return None
        
        # First try to find available runways if preferred
        if prefer_available:
            for i, runway in enumerate(runways):
                if not runway.get('occupied_by'):
                    return i
        
        # If no available runway found or not preferred, return first runway
        return 0 if runways else None
    
    def _find_best_gate(self, airport: Dict[str, Any]) -> Optional[int]:
        """
        Find the best available gate.
        
        Args:
            airport (Dict[str, Any]): Airport information
            
        Returns:
            Optional[int]: Best gate ID, or None if no gates available
        """
        gates = airport.get('gates', [])
        
        # Find first available gate
        for i, gate in enumerate(gates):
            if not gate.get('occupied_by'):
                return i
        
        return None
    
    def get_status(self) -> Dict[str, Any]:
        """
        Get current status information about the rule-based AI.
        
        Returns:
            Dict[str, Any]: Status information
        """
        base_status = super().get_status()
        base_status.update({
            'type': 'rule_based',
            'deterministic': True,
            'requires_external_service': False
        })
        return base_status 