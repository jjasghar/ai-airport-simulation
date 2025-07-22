"""
Ollama AI integration for the AI Airport Simulation.

This module provides integration with Ollama for local large language model
inference. It maintains compatibility with the existing Ollama setup while
fitting into the new modular AI architecture.
"""

import json
import time
import logging
import requests
from typing import Dict, Any, Optional

from .base_ai import BaseAI, AIResponse


class OllamaAI(BaseAI):
    """
    Ollama local AI implementation for air traffic control.
    
    This class integrates with Ollama to provide local large language model
    inference for air traffic control decisions. It supports various models
    like Llama, Mistral, and others available through Ollama.
    
    Attributes:
        base_url (str): Ollama server base URL
        model (str): Model name to use (e.g., 'llama2', 'mistral')
        timeout (float): Request timeout in seconds
        max_retries (int): Maximum number of retry attempts
    """
    
    def __init__(self, base_url: str = "http://localhost:11434", 
                 model: str = "llama2"):
        """
        Initialize the Ollama AI implementation.
        
        Args:
            base_url (str): Ollama server URL
            model (str): Model name to use for decisions
        """
        super().__init__(f"Ollama-{model}")
        
        self.base_url = base_url.rstrip('/')
        self.model = model
        self.timeout = 30.0
        self.max_retries = 3
        
        # Set up logging
        self.logger = logging.getLogger(__name__)
    
    def connect(self) -> bool:
        """
        Establish connection to Ollama server.
        
        Returns:
            bool: True if connection successful, False otherwise
        """
        try:
            # Test connection by listing available models
            response = requests.get(
                f"{self.base_url}/api/tags",
                timeout=self.timeout
            )
            response.raise_for_status()
            
            # Check if our model is available
            models_data = response.json()
            available_models = [model['name'] for model in models_data.get('models', [])]
            
            if self.model not in available_models:
                self.logger.warning(f"Model {self.model} not found in available models: {available_models}")
                
                # Try to pull the model if it's not available
                self.logger.info(f"Attempting to pull model: {self.model}")
                pull_response = requests.post(
                    f"{self.base_url}/api/pull",
                    json={"name": self.model},
                    timeout=300  # Longer timeout for model pulling
                )
                
                if pull_response.status_code != 200:
                    self.logger.error(f"Failed to pull model {self.model}")
                    return False
            
            self.is_connected = True
            self.logger.info(f"Ollama connected successfully using model: {self.model}")
            return True
            
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Failed to connect to Ollama: {e}")
            self.is_connected = False
            return False
        except Exception as e:
            self.logger.error(f"Unexpected error connecting to Ollama: {e}")
            self.is_connected = False
            return False
    
    def disconnect(self) -> None:
        """Clean up Ollama connection."""
        self.is_connected = False
        self.logger.info("Ollama disconnected")
    
    def make_decision(self, aircraft: Dict[str, Any], airport_state: Dict[str, Any], 
                     config: Any) -> AIResponse:
        """
        Make an air traffic control decision using Ollama.
        
        Args:
            aircraft (Dict[str, Any]): Current aircraft state
            airport_state (Dict[str, Any]): Current airport state
            config (Any): Configuration object
            
        Returns:
            AIResponse: AI decision and reasoning
        """
        start_time = time.time()
        
        if not self.is_connected:
            return self._create_response(
                "wait", 
                reasoning="Ollama not connected"
            )
        
        try:
            # Extract and format information for the AI
            aircraft_info = self._extract_aircraft_info(aircraft)
            airport_info = self._extract_airport_info(airport_state)
            
            # Build the prompt with current situation
            prompt = self._build_prompt(aircraft_info, airport_info, config)
            
            # Make API call to Ollama
            response = self._call_ollama_api(prompt)
            
            # Parse the response
            ai_response = self._parse_response(response)
            
            # Set processing time
            ai_response.processing_time = time.time() - start_time
            
            return ai_response
            
        except Exception as e:
            self.logger.error(f"Error making Ollama decision: {e}")
            return self._create_response(
                "wait",
                reasoning=f"Ollama error: {str(e)}"
            )
    
    def _build_prompt(self, aircraft: Dict[str, Any], airport: Dict[str, Any], 
                     config: Any) -> str:
        """
        Build the prompt for Ollama based on current situation.
        
        Args:
            aircraft (Dict[str, Any]): Aircraft information
            airport (Dict[str, Any]): Airport state information
            config (Any): Configuration object
            
        Returns:
            str: Formatted prompt for the AI
        """
        # Use the system prompt from configuration if available
        if hasattr(config, 'prompts') and hasattr(config.prompts, 'system_prompt'):
            base_prompt = config.prompts.system_prompt
        else:
            base_prompt = self._get_default_prompt()
        
        # Format the prompt with current situation
        situation_context = self._format_situation_context(aircraft, airport)
        
        # Combine base prompt with current situation
        full_prompt = f"{base_prompt}\n\nCURRENT SITUATION:\n{situation_context}\n\nProvide your decision:"
        
        return full_prompt
    
    def _get_default_prompt(self) -> str:
        """
        Get a default system prompt if none is configured.
        
        Returns:
            str: Default system prompt for air traffic control
        """
        return """You are an AI Air Traffic Controller managing aircraft at a busy airport.

AVAILABLE DECISIONS:
- "land" (specify runway ID) - Direct aircraft to land on specified runway
- "gate" (specify gate ID) - Direct aircraft to taxi to specified gate  
- "takeoff" (specify runway ID) - Clear aircraft for takeoff from specified runway
- "hold" - Put aircraft in holding pattern (NEVER for low/critical fuel!)
- "wait" - No action, wait for better conditions (NEVER for low/critical fuel!)
- "assign_runway" (specify runway ID) - Assign a runway to approaching aircraft
- "avoid" (specify position 0-7) - Execute collision avoidance maneuver

DECISION PRIORITY ORDER:
1. COLLISION AVOIDANCE - If collision warning active, execute immediate avoidance
2. FUEL EMERGENCIES (Critical fuel < 15%) - Immediate landing on ANY available runway
3. LOW FUEL AIRCRAFT (< 25%) - Priority landing, avoid holding patterns
4. Aircraft safety and separation
5. Normal traffic flow and efficiency
6. Airport capacity optimization

Respond with a JSON object containing:
{
  "decision": "land|gate|takeoff|hold|wait|assign_runway|avoid",
  "target": runway_or_gate_id_or_avoidance_position_if_applicable,
  "reasoning": "brief explanation emphasizing SAFETY considerations"
}"""
    
    def _format_situation_context(self, aircraft: Dict[str, Any], 
                                 airport: Dict[str, Any]) -> str:
        """
        Format the current situation for the AI prompt.
        
        Args:
            aircraft (Dict[str, Any]): Aircraft information
            airport (Dict[str, Any]): Airport information
            
        Returns:
            str: Formatted situation context
        """
        # Format aircraft info
        aircraft_context = f"""Aircraft: {aircraft['callsign']} [{aircraft['aircraft_type']}]
State: {aircraft['state']}
Position: ({aircraft['position'].get('x', 0)}, {aircraft['position'].get('y', 0)})
Fuel: {aircraft['fuel']:.1f}%
Assigned Runway: {aircraft['assigned_runway']}
Assigned Gate: {aircraft['assigned_gate']}
Low Fuel: {aircraft['is_low_fuel']}
Critical Fuel: {aircraft['is_critical_fuel']}"""
        
        # Format airport info
        runway_info = []
        for i, runway in enumerate(airport['runways']):
            status = "occupied" if runway.get('occupied_by') else "available"
            runway_info.append(f"Runway {i}: {status}")
        
        gate_info = []
        for i, gate in enumerate(airport['gates']):
            status = "occupied" if gate.get('occupied_by') else "available"
            gate_info.append(f"Gate {i}: {status}")
        
        airport_context = f"""Airport Status:
Runways: {', '.join(runway_info)}
Gates: {', '.join(gate_info)}
Total Aircraft: {len(airport['aircraft'])}
Total Crashes: {airport['total_crashes']}"""
        
        return f"{aircraft_context}\n\n{airport_context}"
    
    def _call_ollama_api(self, prompt: str) -> str:
        """
        Make API call to Ollama with retry logic.
        
        Args:
            prompt (str): Formatted prompt for the AI
            
        Returns:
            str: Response text from Ollama
            
        Raises:
            Exception: If all retry attempts fail
        """
        last_exception = None
        
        for attempt in range(self.max_retries):
            try:
                response = requests.post(
                    f"{self.base_url}/api/generate",
                    json={
                        "model": self.model,
                        "prompt": prompt,
                        "stream": False,
                        "options": {
                            "temperature": 0.1,  # Low temperature for consistent decisions
                            "top_p": 0.9,
                            "top_k": 40
                        }
                    },
                    timeout=self.timeout
                )
                
                response.raise_for_status()
                response_data = response.json()
                
                return response_data.get('response', '')
                
            except Exception as e:
                last_exception = e
                self.logger.warning(f"Ollama API attempt {attempt + 1} failed: {e}")
                if attempt < self.max_retries - 1:
                    time.sleep(1)  # Brief delay before retry
        
        # All attempts failed
        raise last_exception
    
    def _parse_response(self, response: str) -> AIResponse:
        """
        Parse Ollama response into standardized AIResponse.
        
        Args:
            response (str): Raw response text from Ollama
            
        Returns:
            AIResponse: Parsed and validated response
        """
        try:
            # Try to parse as JSON
            response_data = json.loads(response)
            
            decision = response_data.get('decision', 'wait')
            target = response_data.get('target')
            reasoning = response_data.get('reasoning', 'No reasoning provided')
            
            # Convert target to string if it's a number
            if target is not None:
                target = str(target)
            
            return self._create_response(
                decision=decision,
                target=target,
                reasoning=reasoning,
                confidence=0.8  # Good confidence for valid JSON responses
            )
            
        except json.JSONDecodeError:
            # If JSON parsing fails, try to extract decision from text
            self.logger.warning(f"Failed to parse JSON response: {response}")
            
            # Simple text-based parsing as fallback
            decision = 'wait'
            target = None
            reasoning = "Failed to parse response"
            
            # Look for key decision words
            response_lower = response.lower()
            if 'land' in response_lower:
                decision = 'land'
            elif 'takeoff' in response_lower:
                decision = 'takeoff'
            elif 'gate' in response_lower:
                decision = 'gate'
            elif 'hold' in response_lower:
                decision = 'hold'
            elif 'avoid' in response_lower:
                decision = 'avoid'
            
            return self._create_response(
                decision=decision,
                target=target,
                reasoning=f"Fallback parsing: {response[:100]}...",
                confidence=0.3  # Lower confidence for fallback parsing
            )
    
    def get_status(self) -> Dict[str, Any]:
        """
        Get current status information about the Ollama connection.
        
        Returns:
            Dict[str, Any]: Extended status information
        """
        base_status = super().get_status()
        base_status.update({
            'model': self.model,
            'base_url': self.base_url,
            'timeout': self.timeout,
            'max_retries': self.max_retries
        })
        return base_status 