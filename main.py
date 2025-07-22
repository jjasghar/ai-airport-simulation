#!/usr/bin/env python3
"""
Airport Control Tower Simulation
Main application entry point.

A comprehensive airport simulation that allows AI systems (including ollama)
to control air traffic, with real-time graphical visualization and manual override capabilities.
"""
import sys
import argparse
import threading
import time
from typing import Optional

from config import get_config, Config
from simulation import SimulationEngine
from ai_interface import AIManager

# Graphics import is conditional to avoid pygame dependency for headless/config modes

class AirportSimulation:
    """Main application class that coordinates all components."""
    
    def __init__(self, headless: bool = False):
        self.headless = headless
        self.simulation_engine = SimulationEngine()
        self.ai_manager = AIManager()
        self.renderer: Optional[AirportRenderer] = None
        self.running = False
        
        # Replace default ATC with AI manager
        self.simulation_engine.atc = self
    
    def make_decision(self, aircraft) -> dict:
        """AI-powered decision making for ATC."""
        if self.simulation_engine.manual_mode:
            # In manual mode, return empty decision (let manual commands handle it)
            return {'action': None}
        
        # Get current airport state
        airport_state = self.simulation_engine.get_simulation_state()
        
        # Use AI manager to make decision
        return self.ai_manager.make_atc_decision(aircraft, airport_state)
    
    def setup_graphics(self):
        """Initialize graphics system."""
        if not self.headless:
            from graphics import AirportRenderer
            self.renderer = AirportRenderer(self.simulation_engine)
            # AI switching buttons are now handled directly in the graphics.py setup_ui method
    
    def switch_ai(self, ai_name: str):
        """Switch AI implementation."""
        if self.ai_manager.switch_ai(ai_name):
            print(f"Switched to {ai_name} AI")
    
    def switch_ollama_model(self, model_name: str):
        """Switch ollama model."""
        if self.ai_manager.switch_ollama_model(model_name):
            print(f"Switched ollama model to {model_name}")
        else:
            print(f"Failed to switch to model {model_name}")
    
    def list_ollama_models(self):
        """List available ollama models."""
        models = self.ai_manager.get_ollama_models()
        if models:
            print(f"Available ollama models: {', '.join(models)}")
        else:
            print("No ollama models available or ollama not connected")
    
    def run_headless(self, duration: float = None):
        """Run simulation without graphics."""
        print("Starting headless simulation...")
        print(f"Current AI: {self.ai_manager.current_ai.name}")
        config = get_config()
        print(f"Airport configuration: {config.airport.runways.count} runways, {config.airport.gates.count} gates")
        
        self.simulation_engine.start()
        start_time = time.time()
        
        try:
            while True:
                dt = 0.016  # ~60 FPS equivalent
                self.simulation_engine.update(dt)
                
                # Print status every 10 seconds
                if int(time.time() - start_time) % 10 == 0:
                    state = self.simulation_engine.get_simulation_state()
                    print(f"Time: {state['current_time']:.1f}s, Aircraft: {len(state['aircraft'])}")
                
                # Check duration limit
                if duration and (time.time() - start_time) >= duration:
                    break
                
                time.sleep(dt)
                
        except KeyboardInterrupt:
            print("\nSimulation interrupted by user")
        finally:
            self.simulation_engine.stop()
            # Log session end
            from ai_interface import log_session_end, get_log_file_path
            log_session_end()
            print("Simulation stopped")
            print(f"AI decision log saved to: {get_log_file_path()}")
    
    def run_with_graphics(self):
        """Run simulation with graphics."""
        if not self.renderer:
            self.setup_graphics()
        
        print("Starting airport simulation with graphics...")
        print(f"Current AI: {self.ai_manager.current_ai.name}")
        print("Use the UI buttons to control the simulation")
        print("Manual mode controls:")
        print("  - Click aircraft to select")
        print("  - L: Assign landing")
        print("  - G: Assign gate")
        print("  - T: Assign takeoff")
        print("  - H: Hold pattern")
        
        # Start the simulation engine
        self.simulation_engine.start()
        
        try:
            self.renderer.run()
        except Exception as e:
            print(f"Graphics error: {e}")
            import traceback
            traceback.print_exc()
        finally:
            self.simulation_engine.stop()
            # Log session end
            from ai_interface import log_session_end, get_log_file_path
            log_session_end()
            print(f"AI decision log saved to: {get_log_file_path()}")
    
    def run(self):
        """Run the simulation."""
        if self.headless:
            self.run_headless()
        else:
            self.run_with_graphics()
    
    def get_stats(self):
        """Get simulation statistics."""
        state = self.simulation_engine.get_simulation_state()
        ai_stats = self.ai_manager.get_performance_stats()
        
        return {
            'simulation': {
                'current_time': state['current_time'],
                'total_aircraft': len(state['aircraft']),
                'runways_occupied': len([r for r in state['runways'] if r['state'] != 'available']),
                'gates_occupied': len([g for g in state['gates'] if not g['available']])
            },
            'ai_performance': ai_stats
        }

def create_config_file():
    """Create a default configuration file."""
    default_config = Config()
    # Note: Config saving is now handled by config manager
    # For now, just inform the user about the YAML config
    print("Default config.yaml already exists or will be created automatically")
    print("Edit config.yaml to customize airport layout, simulation parameters, and AI settings")

def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Airport Control Tower Simulation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py                    # Run with graphics (default)
  python main.py --headless         # Run without graphics
  python main.py --duration 60     # Run for 60 seconds then exit
  python main.py --config          # Create default config file
  python main.py --ai ollama        # Use ollama AI (if available)
  python main.py --ai ollama --ollama-model codellama  # Use specific model
  
Configuration:
          Edit config.yaml to customize airport layout, simulation parameters,
  and AI settings. The file will be created automatically if it doesn't exist.
        """
    )
    
    parser.add_argument(
        '--headless',
        action='store_true',
        help='Run without graphics (headless mode)'
    )
    
    parser.add_argument(
        '--duration',
        type=float,
        help='Run for specified duration in seconds (headless only)'
    )
    
    parser.add_argument(
        '--config',
        action='store_true',
        help='Create default configuration file and exit'
    )
    
    parser.add_argument(
        '--ai',
        choices=['rule_based', 'ollama', 'remote'],
        help='Choose AI implementation to use'
    )
    
    parser.add_argument(
        '--runways',
        type=int,
        help='Number of runways (overrides config)'
    )
    
    parser.add_argument(
        '--gates',
        type=int,
        help='Number of gates (overrides config)'
    )
    
    parser.add_argument(
        '--ollama-model',
        type=str,
        help='Ollama model to use (overrides config, e.g., llama2, codellama, mistral)'
    )
    
    args = parser.parse_args()
    
    # Handle config creation
    if args.config:
        create_config_file()
        return
    
    # Load configuration
    config = get_config()
    
    # Override config with command line arguments
    if args.runways:
        config.airport.runways.count = args.runways
    if args.gates:
        config.airport.gates.count = args.gates
    if hasattr(args, 'ollama_model') and args.ollama_model:
        config.ai.ollama.model = args.ollama_model
    
    # Check for pygame in headless mode
    if not args.headless:
        try:
            import pygame
        except ImportError:
            print("ERROR: pygame is required for graphics mode.")
            print("Install with: pip install pygame")
            print("Or run with --headless flag")
            return 1
    
    # Create and run simulation
    try:
        simulation = AirportSimulation(headless=args.headless)
        
        # Switch AI if specified
        if args.ai:
            simulation.switch_ai(args.ai)
        
        # Run headless with duration if specified
        if args.headless and args.duration:
            simulation.run_headless(args.duration)
        else:
            simulation.run()
        
        # Print final stats
        if args.headless:
            try:
                stats = simulation.get_stats()
                print("\n=== Final Statistics ===")
                print(f"Simulation time: {stats['simulation']['current_time']:.1f}s")
                print(f"Total aircraft processed: {stats['simulation']['total_aircraft']}")
                print(f"AI decisions made: {stats['ai_performance']['total_decisions']}")
            except Exception as e:
                print(f"Error getting final stats: {e}")
            
    except KeyboardInterrupt:
        print("\nSimulation interrupted by user")
        return 0
    except Exception as e:
        import traceback
        print(f"ERROR: {e}")
        print("Traceback:")
        traceback.print_exc()
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main()) 