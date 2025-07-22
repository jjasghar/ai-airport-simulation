"""
Utility functions package for the AI Airport Simulation.

This package contains reusable utility functions for logging,
mathematics, and other common operations used throughout the simulation.
"""

from .logging_utils import setup_logging, log_aircraft_decision, log_crash
from .math_utils import distance, normalize_vector, clamp, random_position_in_circle

__all__ = [
    'setup_logging',
    'log_aircraft_decision', 
    'log_crash',
    'distance',
    'normalize_vector',
    'clamp',
    'random_position_in_circle'
] 