"""
Position utilities for the AI Airport Simulation.

This module provides the Position class for handling 2D spatial coordinates
and movement calculations used throughout the simulation.
"""

import math
from dataclasses import dataclass
from typing import Tuple


@dataclass
class Position:
    """
    Represents a 2D position in the simulation space.
    
    The coordinate system uses pixels with (0,0) at the top-left corner.
    Positive X extends to the right, positive Y extends downward.
    
    Attributes:
        x (float): X coordinate in pixels
        y (float): Y coordinate in pixels
    """
    x: float
    y: float

    def distance_to(self, other: 'Position') -> float:
        """
        Calculate the Euclidean distance to another position.
        
        Args:
            other (Position): The target position to measure distance to
            
        Returns:
            float: Distance in pixels between the two positions
        """
        return math.sqrt((self.x - other.x) ** 2 + (self.y - other.y) ** 2)

    def move_towards(self, target: 'Position', speed: float, dt: float) -> 'Position':
        """
        Move this position towards a target position at a given speed.
        
        This method calculates the new position after moving for time dt
        at the specified speed towards the target. If the movement would
        overshoot the target, the position is clamped to the target.
        
        Args:
            target (Position): The destination position to move towards
            speed (float): Movement speed in pixels per second
            dt (float): Time step in seconds
            
        Returns:
            Position: New position after movement
        """
        # Calculate the direction vector to the target
        dx = target.x - self.x
        dy = target.y - self.y
        
        # Calculate the distance to target
        distance = math.sqrt(dx ** 2 + dy ** 2)
        
        # If we're already at the target or very close, return the target
        if distance <= 0.1:
            return Position(target.x, target.y)
        
        # Calculate how far we can move this frame
        max_movement = speed * dt
        
        # If we would overshoot the target, just go to the target
        if max_movement >= distance:
            return Position(target.x, target.y)
        
        # Normalize the direction vector and apply movement
        normalized_dx = dx / distance
        normalized_dy = dy / distance
        
        new_x = self.x + normalized_dx * max_movement
        new_y = self.y + normalized_dy * max_movement
        
        return Position(new_x, new_y)

    def to_tuple(self) -> Tuple[float, float]:
        """
        Convert position to a tuple for compatibility with graphics libraries.
        
        Returns:
            Tuple[float, float]: (x, y) coordinate tuple
        """
        return (self.x, self.y)

    def __str__(self) -> str:
        """String representation of the position."""
        return f"Position({self.x:.1f}, {self.y:.1f})"

    def __repr__(self) -> str:
        """Detailed string representation for debugging."""
        return f"Position(x={self.x}, y={self.y})" 