"""
Mathematical utility functions for the AI Airport Simulation.

This module provides common mathematical operations used throughout
the simulation including distance calculations, vector operations,
and geometric functions.
"""

import math
import random
from typing import Tuple

from models.position import Position


def distance(pos1: Position, pos2: Position) -> float:
    """
    Calculate Euclidean distance between two positions.
    
    Args:
        pos1 (Position): First position
        pos2 (Position): Second position
        
    Returns:
        float: Distance between the positions
    """
    return math.sqrt((pos1.x - pos2.x)**2 + (pos1.y - pos2.y)**2)


def distance_coords(x1: float, y1: float, x2: float, y2: float) -> float:
    """
    Calculate Euclidean distance between two coordinate pairs.
    
    Args:
        x1 (float): X coordinate of first point
        y1 (float): Y coordinate of first point
        x2 (float): X coordinate of second point
        y2 (float): Y coordinate of second point
        
    Returns:
        float: Distance between the points
    """
    return math.sqrt((x1 - x2)**2 + (y1 - y2)**2)


def normalize_vector(x: float, y: float) -> Tuple[float, float]:
    """
    Normalize a vector to unit length.
    
    Args:
        x (float): X component of the vector
        y (float): Y component of the vector
        
    Returns:
        Tuple[float, float]: Normalized vector (unit_x, unit_y)
    """
    length = math.sqrt(x**2 + y**2)
    if length == 0:
        return 0.0, 0.0
    return x / length, y / length


def clamp(value: float, min_value: float, max_value: float) -> float:
    """
    Clamp a value between minimum and maximum bounds.
    
    Args:
        value (float): Value to clamp
        min_value (float): Minimum allowed value
        max_value (float): Maximum allowed value
        
    Returns:
        float: Clamped value
    """
    return max(min_value, min(max_value, value))


def clamp_position(position: Position, width: float, height: float, margin: float = 0) -> Position:
    """
    Clamp a position to stay within bounds with optional margin.
    
    Args:
        position (Position): Position to clamp
        width (float): Maximum width boundary
        height (float): Maximum height boundary  
        margin (float): Margin from edges (default: 0)
        
    Returns:
        Position: Clamped position
    """
    clamped_x = clamp(position.x, margin, width - margin)
    clamped_y = clamp(position.y, margin, height - margin)
    return Position(clamped_x, clamped_y)


def random_position_in_circle(center: Position, radius: float) -> Position:
    """
    Generate a random position within a circle.
    
    Args:
        center (Position): Center of the circle
        radius (float): Radius of the circle
        
    Returns:
        Position: Random position within the circle
    """
    angle = random.uniform(0, 2 * math.pi)
    # Use sqrt for uniform distribution within circle
    distance = random.uniform(0, radius) * math.sqrt(random.random())
    
    x = center.x + distance * math.cos(angle)
    y = center.y + distance * math.sin(angle)
    
    return Position(x, y)


def random_position_on_circle(center: Position, radius: float) -> Position:
    """
    Generate a random position on the circumference of a circle.
    
    Args:
        center (Position): Center of the circle
        radius (float): Radius of the circle
        
    Returns:
        Position: Random position on the circle circumference
    """
    angle = random.uniform(0, 2 * math.pi)
    x = center.x + radius * math.cos(angle)
    y = center.y + radius * math.sin(angle)
    
    return Position(x, y)


def angle_between_positions(pos1: Position, pos2: Position) -> float:
    """
    Calculate the angle between two positions.
    
    Args:
        pos1 (Position): Starting position
        pos2 (Position): Target position
        
    Returns:
        float: Angle in radians from pos1 to pos2
    """
    dx = pos2.x - pos1.x
    dy = pos2.y - pos1.y
    return math.atan2(dy, dx)


def lerp(start: float, end: float, t: float) -> float:
    """
    Linear interpolation between two values.
    
    Args:
        start (float): Starting value
        end (float): Ending value
        t (float): Interpolation factor (0.0 to 1.0)
        
    Returns:
        float: Interpolated value
    """
    return start + t * (end - start)


def lerp_position(start: Position, end: Position, t: float) -> Position:
    """
    Linear interpolation between two positions.
    
    Args:
        start (Position): Starting position
        end (Position): Ending position
        t (float): Interpolation factor (0.0 to 1.0)
        
    Returns:
        Position: Interpolated position
    """
    x = lerp(start.x, end.x, t)
    y = lerp(start.y, end.y, t)
    return Position(x, y)


def degrees_to_radians(degrees: float) -> float:
    """
    Convert degrees to radians.
    
    Args:
        degrees (float): Angle in degrees
        
    Returns:
        float: Angle in radians
    """
    return degrees * math.pi / 180.0


def radians_to_degrees(radians: float) -> float:
    """
    Convert radians to degrees.
    
    Args:
        radians (float): Angle in radians
        
    Returns:
        float: Angle in degrees
    """
    return radians * 180.0 / math.pi 