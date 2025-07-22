"""
Configuration management for the airport simulation.
"""
import yaml
from dataclasses import dataclass, asdict
from typing import List, Dict, Any
import os

@dataclass
class AirportConfig:
    """Configuration for airport layout and parameters."""
    num_runways: int = 2
    num_gates: int = 10
    airport_width: int = 1200
    airport_height: int = 800
    runway_length: int = 300
    runway_width: int = 40
    gate_spacing: int = 60
    
@dataclass
class SimulationConfig:
    """Configuration for simulation parameters."""
    time_scale: float = 1.0  # Real-time multiplier
    max_aircraft: int = 20
    spawn_rate: float = 0.1  # Aircraft per second
    ai_decision_interval: float = 0.5  # Seconds between AI decisions (very fast for emergencies)
    
@dataclass
class AIConfig:
    """Configuration for AI integration."""
    ollama_host: str = "http://localhost:11434"
    ollama_model: str = "llama2"
    remote_ai_endpoint: str = ""
    ai_enabled: bool = True
    manual_override: bool = True

@dataclass
class PromptsConfig:
    """Configuration for AI prompts."""
    system_prompt: str = """You are an Air Traffic Controller managing aircraft at an airport.

CURRENT AIRCRAFT:
- Callsign: {callsign}
- State: {state}
- Position: ({x:.0f}, {y:.0f})
- Type: {aircraft_type}
- Assigned Runway: {assigned_runway}
- Assigned Gate: {assigned_gate}
- Fuel: {fuel:.1f}%
- Low Fuel: {is_low_fuel}
- Critical Fuel: {is_critical_fuel}
- Fuel Priority: {fuel_priority}

AIRPORT STATUS:
Runways ({runway_count} total):
{runway_status}

Gates ({gate_count} total):
{gate_status}

OTHER AIRCRAFT: {total_aircraft} total aircraft in system

AVAILABLE DECISIONS:
- "land" (specify runway ID) - Direct aircraft to land on specified runway
- "gate" (specify gate ID) - Direct aircraft to taxi to specified gate
- "takeoff" (specify runway ID) - Clear aircraft for takeoff from specified runway
- "hold" - Put aircraft in holding pattern
- "wait" - No action, wait for better conditions
- "assign_runway" (specify runway ID) - Assign a runway to approaching aircraft

Respond with a JSON object containing:
{{
  "decision": "land|gate|takeoff|hold|wait|assign_runway",
  "target": runway_or_gate_id_if_applicable,
  "reasoning": "brief explanation of your decision"
}}

PRIORITY: Aircraft with low fuel should be prioritized for landing. Consider safety, efficiency, and airport capacity. Make your decision:"""
    
    decision_instructions: str = """Make intelligent ATC decisions considering:
- Aircraft safety and separation
- Runway and gate capacity  
- Traffic flow optimization
- Emergency situations priority
- Fuel levels and fuel emergencies
- Weather conditions if applicable"""

@dataclass
class Config:
    """Main configuration class."""
    airport: AirportConfig
    simulation: SimulationConfig
    ai: AIConfig
    prompts: PromptsConfig
    
    def get_dynamic_spawn_rate(self) -> float:
        """Calculate dynamic spawn rate based on airport capacity.
        
        Higher capacity (more runways + gates) = higher spawn rate
        Lower capacity = lower spawn rate
        
        Base formula: base_rate * (capacity_factor)
        Where capacity_factor = (num_runways + num_gates) / baseline_capacity
        """
        base_rate = 0.5  # Base spawn rate (aircraft per second)
        baseline_capacity = 6  # 2 runways + 4 gates (reference point)
        
        # Calculate total airport capacity
        total_capacity = self.airport.num_runways + self.airport.num_gates
        
        # Calculate capacity factor (minimum 0.2x, maximum 3.0x)
        capacity_factor = max(0.2, min(3.0, total_capacity / baseline_capacity))
        
        # Calculate final spawn rate
        dynamic_rate = base_rate * capacity_factor
        
        return dynamic_rate
    
    def save(self, filepath: str = "config.yaml"):
        """Save configuration to YAML file."""
        with open(filepath, 'w') as f:
            yaml.dump(asdict(self), f, default_flow_style=False, indent=2, sort_keys=False)
    
    @classmethod
    def load(cls, filepath: str = "config.yaml"):
        """Load configuration from YAML file."""
        # Try YAML first, then fall back to JSON for backward compatibility
        if os.path.exists(filepath):
            with open(filepath, 'r') as f:
                data = yaml.safe_load(f)
                return cls(
                    airport=AirportConfig(**data.get('airport', {})),
                    simulation=SimulationConfig(**data.get('simulation', {})),
                    ai=AIConfig(**data.get('ai', {})),
                    prompts=PromptsConfig(**data.get('prompts', {}))
                )
        elif os.path.exists("config.json"):
            # Backward compatibility: load from JSON and convert to YAML
            print("Converting config.json to config.yaml...")
            with open("config.json", 'r') as f:
                import json
                data = json.load(f)
                config_obj = cls(
                    airport=AirportConfig(**data.get('airport', {})),
                    simulation=SimulationConfig(**data.get('simulation', {})),
                    ai=AIConfig(**data.get('ai', {})),
                    prompts=PromptsConfig(**data.get('prompts', {}))
                )
                # Save as YAML
                config_obj.save()
                print("Configuration converted to config.yaml")
                return config_obj
        
        # Create default configuration
        config_obj = cls(
            airport=AirportConfig(),
            simulation=SimulationConfig(),
            ai=AIConfig(),
            prompts=PromptsConfig()
        )
        config_obj.save()  # Save default config as YAML
        return config_obj

# Global configuration instance
config = Config.load() 