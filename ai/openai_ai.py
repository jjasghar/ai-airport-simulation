"""
OpenAI ChatGPT integration for the AI Airport Simulation.

This module provides integration with OpenAI's ChatGPT API for intelligent
air traffic control decisions. It handles API communication, prompt formatting,
and response parsing.
"""

import json
import time
import logging
from typing import Dict, Any, Optional

try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    openai = None

from .base_ai import BaseAI, AIResponse


class OpenAI(BaseAI):
    """
    OpenAI ChatGPT implementation for air traffic control.
    
    This class integrates with OpenAI's API to provide intelligent decision
    making for air traffic control using large language models like GPT-3.5
    or GPT-4.
    
    Attributes:
        api_key (str): OpenAI API key for authentication
        model (str): Model name to use (e.g., 'gpt-3.5-turbo', 'gpt-4')
        client: OpenAI client instance
        max_retries (int): Maximum number of API retry attempts
        timeout (float): API request timeout in seconds
    """
    
    def __init__(self, api_key: str, model: str = "gpt-3.5-turbo"):
        """
        Initialize the OpenAI AI implementation.
        
        Args:
            api_key (str): OpenAI API key for authentication
            model (str): Model name to use for decisions
        """
        super().__init__(f"OpenAI-{model}")
        
        if not OPENAI_AVAILABLE:
            raise ImportError(
                "OpenAI package not installed. Install with: pip install openai"
            )
        
        self.api_key = api_key
        self.model = model
        self.client = None
        self.max_retries = 3
        self.timeout = 30.0
        
        # Set up logging
        self.logger = logging.getLogger(__name__)
    
    def connect(self) -> bool:
        """
        Establish connection to OpenAI API.
        
        Returns:
            bool: True if connection successful, False otherwise
        """
        try:
            # Initialize OpenAI client
            self.client = openai.OpenAI(
                api_key=self.api_key,
                timeout=self.timeout
            )
            
            # Test connection with a simple API call
            response = self.client.models.list()
            
            # Verify the selected model is available
            available_models = [model.id for model in response.data]
            if self.model not in available_models:
                self.logger.warning(f"Model {self.model} not found in available models")
                # Try to find a suitable fallback
                fallback_models = ['gpt-3.5-turbo', 'gpt-4', 'gpt-4-turbo']
                for fallback in fallback_models:
                    if fallback in available_models:
                        self.logger.info(f"Using fallback model: {fallback}")
                        self.model = fallback
                        break
                else:
                    self.logger.error("No suitable model found")
                    return False
            
            self.is_connected = True
            self.logger.info(f"OpenAI connected successfully using model: {self.model}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to connect to OpenAI: {e}")
            self.is_connected = False
            return False
    
    def disconnect(self) -> None:
        """Clean up OpenAI connection."""
        self.client = None
        self.is_connected = False
        self.logger.info("OpenAI disconnected")
    
    def make_decision(self, aircraft: Dict[str, Any], airport_state: Dict[str, Any], 
                     config: Any) -> AIResponse:
        """
        Make an air traffic control decision using OpenAI ChatGPT.
        
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
                reasoning="OpenAI not connected"
            )
        
        try:
            # Extract and format information for the AI
            aircraft_info = self._extract_aircraft_info(aircraft)
            airport_info = self._extract_airport_info(airport_state)
            
            # Build the prompt with current situation
            prompt = self._build_prompt(aircraft_info, airport_info, config)
            
            # Make API call to OpenAI
            response = self._call_openai_api(prompt)
            
            # Parse the response
            ai_response = self._parse_response(response)
            
            # Set processing time
            ai_response.processing_time = time.time() - start_time
            
            return ai_response
            
        except Exception as e:
            self.logger.error(f"Error making OpenAI decision: {e}")
            return self._create_response(
                "wait",
                reasoning=f"OpenAI error: {str(e)}"
            )
    
    def _build_prompt(self, aircraft: Dict[str, Any], airport: Dict[str, Any], 
                     config: Any) -> str:
        """
        Build the prompt for OpenAI based on current situation.
        
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
    
    def _call_openai_api(self, prompt: str) -> str:
        """
        Make API call to OpenAI with retry logic.
        
        Args:
            prompt (str): Formatted prompt for the AI
            
        Returns:
            str: Response text from OpenAI
            
        Raises:
            Exception: If all retry attempts fail
        """
        last_exception = None
        
        for attempt in range(self.max_retries):
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": "You are an expert air traffic controller."},
                        {"role": "user", "content": prompt}
                    ],
                    max_tokens=500,
                    temperature=0.1,  # Low temperature for consistent decisions
                    timeout=self.timeout
                )
                
                return response.choices[0].message.content
                
            except Exception as e:
                last_exception = e
                self.logger.warning(f"OpenAI API attempt {attempt + 1} failed: {e}")
                if attempt < self.max_retries - 1:
                    time.sleep(1)  # Brief delay before retry
        
        # All attempts failed
        raise last_exception
    
    def _parse_response(self, response: str) -> AIResponse:
        """
        Parse OpenAI response into standardized AIResponse.
        
        Args:
            response (str): Raw response text from OpenAI
            
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
                confidence=0.9  # High confidence for valid JSON responses
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
        Get current status information about the OpenAI connection.
        
        Returns:
            Dict[str, Any]: Extended status information
        """
        base_status = super().get_status()
        base_status.update({
            'model': self.model,
            'api_key_set': bool(self.api_key),
            'max_retries': self.max_retries,
            'timeout': self.timeout
        })
        return base_status 