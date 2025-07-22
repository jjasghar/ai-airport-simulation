"""
Configuration package for the AI Airport Simulation.

This package handles configuration management, loading settings from
YAML files and providing structured access to configuration data.
"""

from .config_manager import ConfigManager, Config, get_config

__all__ = ['ConfigManager', 'Config', 'get_config']