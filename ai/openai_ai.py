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
    
    def __init__(self, api_key: str, model: str = "gpt-3.5-turbo", 
                 base_url: str = None, local_server: bool = False):
        """
        Initialize the OpenAI AI implementation.
        
        Args:
            api_key (str): OpenAI API key for authentication
            model (str): Model name to use for decisions
            base_url (str): Base URL for local OpenAI-compatible servers
            local_server (bool): Whether this is a local server or official OpenAI API
        """
        server_type = "LocalOpenAI" if local_server else "OpenAI"
        super().__init__(f"{server_type}-{model}")
        
        if not OPENAI_AVAILABLE:
            raise ImportError(
                "OpenAI package not installed. Install with: pip install openai"
            )
        
        self.api_key = api_key
        self.model = model
        self.base_url = base_url
        self.local_server = local_server
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
            client_kwargs = {
                'api_key': self.api_key,
                'timeout': self.timeout
            }
            
            # Add base_url for local servers
            if self.base_url:
                # Ensure we append /v1 for OpenAI compatibility
                base_url = self.base_url.rstrip('/')
                if not base_url.endswith('/v1'):
                    base_url = f"{base_url}/v1"
                client_kwargs['base_url'] = base_url
                self.logger.info(f"Connecting to local server at {base_url} with API key: {self.api_key}")
            else:
                self.logger.info("Connecting to official OpenAI API")
                
            self.client = openai.OpenAI(**client_kwargs)
            
            # Test connection with a simple API call
            if self.local_server:
                # For local servers, try a simple chat completion instead of model listing
                try:
                    test_response = self.client.chat.completions.create(
                        model=self.model,
                        messages=[{"role": "user", "content": "Test connection"}],
                        max_tokens=10,
                        timeout=5
                    )
                    
                    if test_response and test_response.choices:
                        self.logger.info(f"Local OpenAI server connected at {self.base_url}")
                    else:
                        self.logger.error("Test completion failed - no response")
                        return False
                        
                except Exception as test_error:
                    self.logger.error(f"Local server test failed: {test_error}")
                    return False
            else:
                # For official OpenAI API, check model availability
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
            server_info = f"local server at {self.base_url}" if self.local_server else "OpenAI API"
            self.logger.info(f"Connected to {server_info} using model: {self.model}")
            return True
            
        except Exception as e:
            server_info = f"local OpenAI server at {self.base_url}" if self.local_server else "OpenAI API"
            self.logger.error(f"Failed to connect to {server_info}: {e}")
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

CRITICAL: You MUST respond with ONLY a valid JSON object in this exact format:
{
  "decision": "land",
  "target": 0,
  "reasoning": "brief explanation"
}

Valid decisions: land, gate, takeoff, hold, wait, assign_runway, avoid
Do not include any other text or numbers outside the JSON object."""
    
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
        # Format aircraft info with robust error handling
        try:
            if hasattr(aircraft, 'callsign'):
                # Aircraft object format
                pos_x = getattr(aircraft.position, 'x', 0) if hasattr(aircraft, 'position') else 0
                pos_y = getattr(aircraft.position, 'y', 0) if hasattr(aircraft, 'position') else 0
                aircraft_context = f"""Aircraft: {aircraft.callsign} [{aircraft.aircraft_type}]
State: {aircraft.state}
Position: ({pos_x}, {pos_y})
Fuel: {aircraft.fuel:.1f}%
Assigned Runway: {getattr(aircraft, 'assigned_runway', None)}
Assigned Gate: {getattr(aircraft, 'assigned_gate', None)}
Low Fuel: {aircraft.fuel < 25.0}
Critical Fuel: {aircraft.fuel < 15.0}"""
            else:
                # Dictionary format - handle position safely
                position = aircraft.get('position', {})
                if isinstance(position, dict):
                    pos_x = position.get('x', 0)
                    pos_y = position.get('y', 0)
                else:
                    # Position might be an object or other format
                    pos_x = getattr(position, 'x', 0) if hasattr(position, 'x') else 0
                    pos_y = getattr(position, 'y', 0) if hasattr(position, 'y') else 0
                
                # Handle aircraft_type which might be an enum
                aircraft_type = aircraft.get('aircraft_type', 'Unknown')
                if hasattr(aircraft_type, 'value'):
                    aircraft_type = aircraft_type.value
                
                aircraft_context = f"""Aircraft: {aircraft.get('callsign', 'Unknown')} [{aircraft_type}]
State: {aircraft.get('state', 'Unknown')}
Position: ({pos_x}, {pos_y})
Fuel: {aircraft.get('fuel', 0):.1f}%
Assigned Runway: {aircraft.get('assigned_runway', None)}
Assigned Gate: {aircraft.get('assigned_gate', None)}
Low Fuel: {aircraft.get('is_low_fuel', False)}
Critical Fuel: {aircraft.get('is_critical_fuel', False)}"""
        except Exception as e:
            # Fallback to basic info if formatting fails
            aircraft_context = f"Aircraft: Error formatting aircraft data - {str(e)}"
        
        # Format airport info with error handling
        try:
            runway_info = []
            runways = airport.get('runways', [])
            for i, runway in enumerate(runways):
                if isinstance(runway, dict):
                    status = "occupied" if runway.get('occupied_by') else "available"
                else:
                    # Handle runway object format
                    status = "occupied" if getattr(runway, 'occupied_by', None) else "available"
                runway_info.append(f"Runway {i}: {status}")
            
            gate_info = []
            gates = airport.get('gates', [])
            for i, gate in enumerate(gates):
                if isinstance(gate, dict):
                    status = "occupied" if gate.get('occupied_by') else "available"
                else:
                    # Handle gate object format
                    status = "occupied" if getattr(gate, 'occupied_by', None) else "available"
                gate_info.append(f"Gate {i}: {status}")
            
            aircraft_count = len(airport.get('aircraft', []))
            total_crashes = airport.get('total_crashes', 0)
            
            airport_context = f"""Airport Status:
Runways: {', '.join(runway_info) if runway_info else 'No runway info'}
Gates: {', '.join(gate_info) if gate_info else 'No gate info'}
Total Aircraft: {aircraft_count}
Total Crashes: {total_crashes}"""
        except Exception as e:
            # Fallback to basic info if formatting fails
            airport_context = f"Airport Status: Error formatting airport data - {str(e)}"
        
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
            
            # Ensure response_data is a dictionary
            if not isinstance(response_data, dict):
                # Silently handle non-dict responses with minimal logging
                response_type = type(response_data).__name__
                self.logger.debug(f"Model returned {response_type} instead of JSON, using fallback")
                # If it's not a dict, treat as a simple text response
                response_data = {'decision': 'wait', 'reasoning': 'Model returned non-JSON response, using safe default'}
            
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
            self.logger.debug(f"Model response not valid JSON, using text parsing fallback")
            
            # Simple text-based parsing as fallback
            decision = 'wait'
            target = None
            reasoning = "Model response not in JSON format - using safe default"
            
            # Look for key decision words in the response
            response_str = str(response).lower()
            if 'land' in response_str:
                decision = 'assign_runway'
                target = '0'
                reasoning = "Detected landing intent from non-JSON response"
            elif 'takeoff' in response_str:
                decision = 'takeoff'
                target = '0'
                reasoning = "Detected takeoff intent from non-JSON response"
            elif 'gate' in response_str:
                decision = 'gate'
                target = '0'
                reasoning = "Detected gate assignment intent from non-JSON response"
            elif 'hold' in response_str:
                decision = 'hold'
                reasoning = "Detected hold intent from non-JSON response"
            elif 'avoid' in response_str:
                decision = 'avoid'
                target = '0'
                reasoning = "Detected avoidance intent from non-JSON response"
            
            return self._create_response(
                decision=decision,
                target=target,
                reasoning=reasoning,
                confidence=0.2  # Lower confidence for fallback parsing
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