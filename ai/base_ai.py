"""
Base AI interface for the AI Airport Simulation.

This module defines the abstract base class and data structures that all
AI implementations must follow for consistent air traffic control decisions.
"""

import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, Any, Optional


@dataclass
class AIResponse:
    """
    Standardized response from AI decision making.
    
    This data structure ensures all AI implementations return consistent
    information about their decisions for logging and processing.
    
    Attributes:
        decision (str): The decision made (e.g., 'land', 'takeoff', 'hold')
        target (Optional[str]): Target runway/gate ID or position if applicable
        reasoning (str): Human-readable explanation of the decision
        confidence (float): Confidence level (0.0 to 1.0) in the decision
        decision_time (float): Timestamp when decision was made
        processing_time (float): How long the AI took to make the decision
    """
    decision: str
    target: Optional[str] = None
    reasoning: str = ""
    confidence: float = 1.0
    decision_time: float = 0.0
    processing_time: float = 0.0


class BaseAI(ABC):
    """
    Abstract base class for all AI traffic control implementations.
    
    This class defines the interface that all AI implementations must follow,
    ensuring consistent behavior and allowing easy swapping between different
    AI approaches (rule-based, LLM-based, etc.).
    
    Attributes:
        name (str): Human-readable name of the AI implementation
        is_connected (bool): Whether the AI is ready to make decisions
    """
    
    def __init__(self, name: str):
        """
        Initialize the AI implementation.
        
        Args:
            name (str): Human-readable name for this AI implementation
        """
        self.name = name
        self.is_connected = False
    
    @abstractmethod
    def make_decision(self, aircraft: Dict[str, Any], airport_state: Dict[str, Any], 
                     config: Any) -> AIResponse:
        """
        Make an air traffic control decision for a given aircraft.
        
        This is the core method that all AI implementations must provide.
        It receives the current state of an aircraft and the airport, then
        returns a decision about what action the aircraft should take.
        
        Args:
            aircraft (Dict[str, Any]): Current aircraft state and properties
            airport_state (Dict[str, Any]): Current airport state and other aircraft
            config (Any): Configuration object with simulation settings
            
        Returns:
            AIResponse: The decision and related information
            
        Raises:
            NotImplementedError: If the subclass doesn't implement this method
        """
        raise NotImplementedError("Subclasses must implement make_decision method")
    
    @abstractmethod
    def connect(self) -> bool:
        """
        Establish connection to the AI service (if applicable).
        
        For local implementations like rule-based AI, this might just
        validate configuration. For remote APIs, this establishes the
        connection and verifies authentication.
        
        Returns:
            bool: True if connection successful, False otherwise
        """
        raise NotImplementedError("Subclasses must implement connect method")
    
    @abstractmethod
    def disconnect(self) -> None:
        """
        Clean up and disconnect from the AI service.
        
        This method should clean up any resources, close connections,
        and prepare for shutdown.
        """
        raise NotImplementedError("Subclasses must implement disconnect method")
    
    def is_available(self) -> bool:
        """
        Check if the AI is available to make decisions.
        
        Returns:
            bool: True if AI is connected and ready to make decisions
        """
        return self.is_connected
    
    def get_status(self) -> Dict[str, Any]:
        """
        Get current status information about the AI.
        
        Returns:
            Dict[str, Any]: Status information including connection state
        """
        return {
            'name': self.name,
            'connected': self.is_connected,
            'available': self.is_available()
        }
    
    def _create_response(self, decision: str, target: Optional[str] = None, 
                        reasoning: str = "", confidence: float = 1.0) -> AIResponse:
        """
        Helper method to create standardized AI responses.
        
        Args:
            decision (str): The decision made
            target (Optional[str]): Target ID or position if applicable
            reasoning (str): Explanation of the decision
            confidence (float): Confidence level (0.0 to 1.0)
            
        Returns:
            AIResponse: Standardized response object
        """
        return AIResponse(
            decision=decision,
            target=target,
            reasoning=reasoning,
            confidence=confidence,
            decision_time=time.time(),
            processing_time=0.0  # Will be calculated by caller
        )
    
    def _extract_aircraft_info(self, aircraft: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract relevant aircraft information for decision making.
        
        Args:
            aircraft (Dict[str, Any]): Raw aircraft data
            
        Returns:
            Dict[str, Any]: Cleaned aircraft information
        """
        return {
            'id': aircraft.get('id'),
            'callsign': aircraft.get('callsign'),
            'state': aircraft.get('state'),
            'position': aircraft.get('position', {}),
            'aircraft_type': aircraft.get('aircraft_type'),
            'fuel': aircraft.get('fuel', 0.0),
            'is_low_fuel': aircraft.get('is_low_fuel', False),
            'is_critical_fuel': aircraft.get('is_critical_fuel', False),
            'assigned_runway': aircraft.get('assigned_runway'),
            'assigned_gate': aircraft.get('assigned_gate')
        }
    
    def _extract_airport_info(self, airport_state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract relevant airport information for decision making.
        
        Args:
            airport_state (Dict[str, Any]): Raw airport state data
            
        Returns:
            Dict[str, Any]: Cleaned airport information
        """
        return {
            'runways': airport_state.get('runways', []),
            'gates': airport_state.get('gates', []),
            'aircraft': airport_state.get('aircraft', []),
            'total_crashes': airport_state.get('total_crashes', 0),
            'weather': airport_state.get('weather', 'clear'),
            'time': airport_state.get('current_time', 0.0)
        }
    
    def __str__(self) -> str:
        """String representation of the AI."""
        status = "connected" if self.is_connected else "disconnected"
        return f"{self.name} ({status})"
    
    def __repr__(self) -> str:
        """Detailed string representation for debugging."""
        return f"{self.__class__.__name__}(name='{self.name}', connected={self.is_connected})" 