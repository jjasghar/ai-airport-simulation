"""
Button UI component for the AI Airport Simulation.

This module provides a reusable button component with event handling
and customizable appearance for the simulation interface.
"""

import pygame
from typing import Callable, Optional, Tuple


class Button:
    """
    A simple button UI element with click handling and hover effects.
    
    The Button class provides:
    - Mouse hover detection and visual feedback
    - Click event handling with callback support
    - Customizable appearance and positioning
    - Text rendering with automatic centering
    """
    
    def __init__(self, 
                 x: int, 
                 y: int, 
                 width: int, 
                 height: int, 
                 text: str, 
                 callback: Optional[Callable] = None,
                 font_size: int = 24,
                 colors: Optional[dict] = None):
        """
        Initialize a new button.
        
        Args:
            x (int): X position of the button
            y (int): Y position of the button  
            width (int): Width of the button
            height (int): Height of the button
            text (str): Text to display on the button
            callback (Optional[Callable]): Function to call when clicked
            font_size (int): Font size for button text
            colors (Optional[dict]): Custom color scheme for the button
        """
        self.rect = pygame.Rect(x, y, width, height)
        self.text = text
        self.callback = callback
        self.hovered = False
        self.font = pygame.font.Font(None, font_size)
        
        # Default color scheme
        self.colors = colors or {
            'normal': (80, 80, 80),
            'hover': (120, 120, 120),
            'text': (255, 255, 255),
            'border': (255, 255, 255)
        }
    
    def handle_event(self, event) -> bool:
        """
        Handle mouse events for the button.
        
        Args:
            event: Pygame event to handle
            
        Returns:
            bool: True if the event was handled (button was clicked)
        """
        if event.type == pygame.MOUSEMOTION:
            self.hovered = self.rect.collidepoint(event.pos)
            return False
        
        elif event.type == pygame.MOUSEBUTTONDOWN:
            if self.hovered and self.callback:
                self.callback()
                return True
        
        return False
    
    def draw(self, screen):
        """
        Draw the button on the screen.
        
        Args:
            screen: Pygame surface to draw on
        """
        # Choose button color based on hover state
        button_color = self.colors['hover'] if self.hovered else self.colors['normal']
        
        # Draw button background
        pygame.draw.rect(screen, button_color, self.rect)
        
        # Draw button border
        pygame.draw.rect(screen, self.colors['border'], self.rect, 2)
        
        # Render and center text
        text_surface = self.font.render(self.text, True, self.colors['text'])
        text_rect = text_surface.get_rect(center=self.rect.center)
        screen.blit(text_surface, text_rect)
    
    def set_position(self, x: int, y: int):
        """
        Update button position.
        
        Args:
            x (int): New X position
            y (int): New Y position
        """
        self.rect.x = x
        self.rect.y = y
    
    def set_size(self, width: int, height: int):
        """
        Update button size.
        
        Args:
            width (int): New width
            height (int): New height
        """
        self.rect.width = width
        self.rect.height = height
    
    def set_text(self, text: str):
        """
        Update button text.
        
        Args:
            text (str): New text to display
        """
        self.text = text
    
    def is_clicked(self, pos: Tuple[int, int]) -> bool:
        """
        Check if a position is within the button area.
        
        Args:
            pos (Tuple[int, int]): Position to check (x, y)
            
        Returns:
            bool: True if position is within button bounds
        """
        return self.rect.collidepoint(pos) 