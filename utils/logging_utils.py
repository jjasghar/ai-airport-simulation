"""
Logging utility functions for the AI Airport Simulation.

This module provides logging utilities that complement the existing
AI decision logging system with additional crash reporting, performance
monitoring, and general system logging capabilities.
"""

import logging
import os
from datetime import datetime
from typing import Dict, Any, Optional

from models.aircraft import Aircraft


def setup_logging(log_level: str = "INFO", log_to_file: bool = True) -> logging.Logger:
    """
    Setup general application logging (separate from AI decision logging).
    
    Args:
        log_level (str): Logging level (DEBUG, INFO, WARNING, ERROR)
        log_to_file (bool): Whether to log to file in addition to console
        
    Returns:
        logging.Logger: Configured logger instance
    """
    # Create logs directory if it doesn't exist
    log_dir = "logs"
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    
    # Create general logger
    logger = logging.getLogger('airport_simulation')
    logger.setLevel(getattr(logging, log_level.upper()))
    
    # Clear any existing handlers
    logger.handlers.clear()
    
    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s | %(name)s | %(levelname)s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(getattr(logging, log_level.upper()))
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # File handler (if enabled)
    if log_to_file:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_filename = os.path.join(log_dir, f"simulation_{timestamp}.log")
        file_handler = logging.FileHandler(log_filename)
        file_handler.setLevel(getattr(logging, log_level.upper()))
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    # Prevent propagation to avoid duplicate logs
    logger.propagate = False
    
    return logger


def log_aircraft_decision(aircraft: Aircraft, decision: Dict[str, Any], reasoning: str, logger: Optional[logging.Logger] = None):
    """
    Log an aircraft decision for debugging and analysis.
    
    Args:
        aircraft (Aircraft): The aircraft the decision applies to
        decision (Dict[str, Any]): The decision details
        reasoning (str): The reasoning behind the decision
        logger (Optional[logging.Logger]): Logger to use (creates default if None)
    """
    if logger is None:
        logger = logging.getLogger('airport_simulation')
    
    decision_info = {
        'aircraft_id': aircraft.id,
        'callsign': aircraft.callsign,
        'state': aircraft.state.value,
        'fuel': f"{aircraft.fuel:.1f}%",
        'position': f"({aircraft.position.x:.0f}, {aircraft.position.y:.0f})",
        'decision': decision,
        'reasoning': reasoning
    }
    
    logger.info(f"AIRCRAFT DECISION: {decision_info}")


def log_crash(aircraft: Aircraft, crash_reason: str, details: Dict[str, Any], logger: Optional[logging.Logger] = None):
    """
    Log aircraft crash information for analysis.
    
    Args:
        aircraft (Aircraft): The crashed aircraft
        crash_reason (str): Primary cause of the crash
        details (Dict[str, Any]): Additional crash details
        logger (Optional[logging.Logger]): Logger to use (creates default if None)
    """
    if logger is None:
        logger = logging.getLogger('airport_simulation')
    
    crash_info = {
        'aircraft_id': aircraft.id,
        'callsign': aircraft.callsign,
        'aircraft_type': aircraft.aircraft_type.value,
        'crash_reason': crash_reason,
        'final_fuel': f"{aircraft.fuel:.1f}%",
        'final_position': f"({aircraft.position.x:.0f}, {aircraft.position.y:.0f})",
        'final_state': aircraft.state.value,
        'assigned_runway': aircraft.assigned_runway,
        'assigned_gate': aircraft.assigned_gate,
        **details
    }
    
    logger.error(f"AIRCRAFT CRASH: {crash_info}")


def log_performance_metrics(metrics: Dict[str, Any], logger: Optional[logging.Logger] = None):
    """
    Log performance metrics for system monitoring.
    
    Args:
        metrics (Dict[str, Any]): Performance metrics to log
        logger (Optional[logging.Logger]): Logger to use (creates default if None)
    """
    if logger is None:
        logger = logging.getLogger('airport_simulation')
    
    logger.info(f"PERFORMANCE METRICS: {metrics}")


def log_system_event(event_type: str, message: str, details: Optional[Dict[str, Any]] = None, logger: Optional[logging.Logger] = None):
    """
    Log a general system event.
    
    Args:
        event_type (str): Type of event (e.g., "STARTUP", "SHUTDOWN", "ERROR")
        message (str): Event message
        details (Optional[Dict[str, Any]]): Additional event details
        logger (Optional[logging.Logger]): Logger to use (creates default if None)
    """
    if logger is None:
        logger = logging.getLogger('airport_simulation')
    
    log_message = f"{event_type}: {message}"
    if details:
        log_message += f" | Details: {details}"
    
    logger.info(log_message)


def log_fuel_emergency(aircraft: Aircraft, emergency_level: str, logger: Optional[logging.Logger] = None):
    """
    Log fuel emergency events for analysis.
    
    Args:
        aircraft (Aircraft): Aircraft with fuel emergency
        emergency_level (str): Level of emergency ("LOW", "CRITICAL")
        logger (Optional[logging.Logger]): Logger to use (creates default if None)
    """
    if logger is None:
        logger = logging.getLogger('airport_simulation')
    
    emergency_info = {
        'aircraft_id': aircraft.id,
        'callsign': aircraft.callsign,
        'fuel_level': f"{aircraft.fuel:.1f}%",
        'emergency_level': emergency_level,
        'state': aircraft.state.value,
        'position': f"({aircraft.position.x:.0f}, {aircraft.position.y:.0f})",
        'assigned_runway': aircraft.assigned_runway,
        'assigned_gate': aircraft.assigned_gate
    }
    
    logger.warning(f"FUEL EMERGENCY: {emergency_info}")


def log_collision_event(aircraft1: Aircraft, aircraft2: Aircraft, event_type: str, logger: Optional[logging.Logger] = None):
    """
    Log collision-related events (warnings, avoidance, actual collisions).
    
    Args:
        aircraft1 (Aircraft): First aircraft involved
        aircraft2 (Aircraft): Second aircraft involved
        event_type (str): Type of event ("WARNING", "AVOIDANCE", "COLLISION")
        logger (Optional[logging.Logger]): Logger to use (creates default if None)
    """
    if logger is None:
        logger = logging.getLogger('airport_simulation')
    
    distance = aircraft1.distance_to(aircraft2)
    collision_info = {
        'event_type': event_type,
        'aircraft1': {
            'id': aircraft1.id,
            'callsign': aircraft1.callsign,
            'state': aircraft1.state.value,
            'fuel': f"{aircraft1.fuel:.1f}%"
        },
        'aircraft2': {
            'id': aircraft2.id,
            'callsign': aircraft2.callsign,
            'state': aircraft2.state.value,
            'fuel': f"{aircraft2.fuel:.1f}%"
        },
        'distance': f"{distance:.1f}px"
    }
    
    if event_type == "COLLISION":
        logger.error(f"COLLISION EVENT: {collision_info}")
    else:
        logger.warning(f"COLLISION {event_type}: {collision_info}")


def get_log_summary(log_file_path: str) -> Dict[str, Any]:
    """
    Generate a summary of events from a log file.
    
    Args:
        log_file_path (str): Path to the log file to analyze
        
    Returns:
        Dict[str, Any]: Summary statistics from the log
    """
    if not os.path.exists(log_file_path):
        return {"error": "Log file not found"}
    
    summary = {
        "total_lines": 0,
        "error_count": 0,
        "warning_count": 0,
        "info_count": 0,
        "crash_count": 0,
        "fuel_emergency_count": 0,
        "collision_count": 0
    }
    
    try:
        with open(log_file_path, 'r') as f:
            for line in f:
                summary["total_lines"] += 1
                
                if "ERROR" in line:
                    summary["error_count"] += 1
                elif "WARNING" in line:
                    summary["warning_count"] += 1
                elif "INFO" in line:
                    summary["info_count"] += 1
                
                if "AIRCRAFT CRASH" in line:
                    summary["crash_count"] += 1
                elif "FUEL EMERGENCY" in line:
                    summary["fuel_emergency_count"] += 1
                elif "COLLISION" in line:
                    summary["collision_count"] += 1
    
    except Exception as e:
        summary["error"] = f"Failed to read log file: {e}"
    
    return summary 