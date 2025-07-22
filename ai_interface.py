"""
AI interface for air traffic control integration.
Supports ollama, remote AI endpoints, and custom AI implementations.
"""
import json
import requests
import time
import logging
import os
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import asdict
from models import Aircraft, AircraftState
from config import get_config

# Setup AI decision logging
def setup_ai_logging():
    """Setup dedicated logging for AI decisions."""
    # Create logs directory if it doesn't exist
    log_dir = "logs"
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    
    # Create AI decision logger
    ai_logger = logging.getLogger('ai_decisions')
    ai_logger.setLevel(logging.INFO)
    
    # Clear any existing handlers
    ai_logger.handlers.clear()
    
    # Create file handler with timestamp in filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_filename = os.path.join(log_dir, f"ai_decisions_{timestamp}.log")
    file_handler = logging.FileHandler(log_filename)
    file_handler.setLevel(logging.INFO)
    
    # Create console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    
    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s | %(levelname)s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)
    
    # Add handlers to logger
    ai_logger.addHandler(file_handler)
    ai_logger.addHandler(console_handler)
    
    # Prevent propagation to avoid duplicate logs
    ai_logger.propagate = False
    
    return ai_logger, log_filename

# Initialize AI logging
AI_LOGGER, LOG_FILE_PATH = setup_ai_logging()

def get_log_file_path() -> str:
    """Get the current AI decision log file path."""
    return LOG_FILE_PATH

def log_session_end():
    """Log session end information."""
    AI_LOGGER.info("="*80)
    AI_LOGGER.info("AIRPORT SIMULATION AI DECISION LOG - SESSION ENDED")
    AI_LOGGER.info("="*80)

class AIResponse:
    """Standardized AI response format."""
    
    def __init__(self, decision: str, target: Optional[int] = None, reasoning: str = "", start_time: float = None):
        self.decision = decision  # 'land', 'gate', 'takeoff', 'hold', 'wait'
        self.target = target     # runway/gate ID if applicable
        self.reasoning = reasoning
        self.confidence = 1.0
        self.timestamp = time.time()
        self.start_time = start_time if start_time is not None else self.timestamp
        self.processing_time = self.timestamp - self.start_time  # AI thought time

class BaseAI:
    """Base class for AI implementations."""
    
    def __init__(self, name: str):
        self.name = name
        self.decision_history: List[Dict] = []
    
    def make_decision(self, situation: Dict) -> AIResponse:
        """Make an ATC decision based on the current situation."""
        raise NotImplementedError
    
    def log_decision(self, situation: Dict, response: AIResponse):
        """Log decision for analysis."""
        # Store in memory for backward compatibility
        self.decision_history.append({
            'timestamp': time.time(),
            'situation': situation,
            'decision': response.decision,
            'target': response.target,
            'reasoning': response.reasoning
        })
        
        # Enhanced logging to file and console
        aircraft = situation.get('aircraft', {})
        runways = situation.get('runways', [])
        gates = situation.get('gates', [])
        
        # Create detailed log entry
        log_entry = f"""
AI_DECISION | {self.name}
├─ Aircraft: {aircraft.get('callsign', 'UNKNOWN')} [{aircraft.get('state', 'UNKNOWN')}]
├─ Position: ({aircraft.get('position', {}).get('x', 0):.0f}, {aircraft.get('position', {}).get('y', 0):.0f})
├─ Assigned Runway: {aircraft.get('assigned_runway', 'None')}
├─ Assigned Gate: {aircraft.get('assigned_gate', 'None')}
├─ DECISION: {response.decision.upper()}"""
        
        if response.target is not None:
            log_entry += f" → Target: {response.target}"
        
        # Format decision time as readable local timestamp
        decision_datetime = datetime.fromtimestamp(response.timestamp)
        decision_time_str = decision_datetime.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]  # Include milliseconds
        
        log_entry += f"""
├─ REASONING: {response.reasoning}
├─ Airport Status:
│  ├─ Available Runways: {len([r for r in runways if r.get('state') == 'available'])}/{len(runways)}
│  ├─ Available Gates: {len([g for g in gates if g.get('available', False)])}/{len(gates)}
│  └─ Total Aircraft: {len(situation.get('all_aircraft', []))}
├─ Decision Time: {decision_time_str}
└─ AI Thought Time: {response.processing_time:.3f}s
"""
        
        # Log to file and console
        AI_LOGGER.info(log_entry.strip())
        
        # Also create a summary line for easier parsing
        summary = f"SUMMARY | {aircraft.get('callsign', 'UNKNOWN')} | {aircraft.get('state', 'UNKNOWN')} → {response.decision.upper()}"
        if response.target is not None:
            summary += f"({response.target})"
        summary += f" | {response.reasoning}"
        
        AI_LOGGER.info(summary)

class RuleBasedAI(BaseAI):
    """Simple rule-based AI for baseline comparison."""
    
    def __init__(self):
        super().__init__("RuleBasedAI")
    
    def make_decision(self, situation: Dict) -> AIResponse:
        """Make decision using simple rules."""
        start_time = time.time()  # Track AI thought time
        
        aircraft = situation['aircraft']
        available_runways = [r for r in situation['runways'] if r['state'] == 'available']
        available_gates = [g for g in situation['gates'] if g['available']]
        
        if aircraft['state'] == 'approaching':
            if available_runways:
                runway_id = available_runways[0]['id']
                return AIResponse(
                    decision='land',
                    target=runway_id,
                    reasoning=f"Landing on first available runway {runway_id}",
                    start_time=start_time
                )
            else:
                return AIResponse(
                    decision='hold',
                    reasoning="No runways available, holding pattern",
                    start_time=start_time
                )
        
        elif aircraft['state'] == 'landing':
            if available_gates:
                gate_id = available_gates[0]['id']
                return AIResponse(
                    decision='gate',
                    target=gate_id,
                    reasoning=f"Assigning to first available gate {gate_id}",
                    start_time=start_time
                )
            else:
                return AIResponse(
                    decision='wait',
                    reasoning="No gates available, waiting on runway",
                    start_time=start_time
                )
        
        elif aircraft['state'] == 'at_gate':
            # Random departure decision
            if len(situation['all_aircraft']) > 3 and available_runways:
                runway_id = available_runways[0]['id']
                return AIResponse(
                    decision='takeoff',
                    target=runway_id,
                    reasoning=f"Traffic building up, clearing for takeoff on runway {runway_id}",
                    start_time=start_time
                )
        
        return AIResponse(decision='wait', reasoning="No action needed", start_time=start_time)

class OllamaAI(BaseAI):
    """AI implementation using ollama local models."""
    
    def __init__(self, model: str = None):
        config = get_config()
        default_model = config.ai.ollama.model if hasattr(config, 'ai') and hasattr(config.ai, 'ollama') else 'llama2'
        default_host = config.ai.ollama.host if hasattr(config, 'ai') and hasattr(config.ai, 'ollama') else 'http://localhost:11434'
        super().__init__(f"OllamaAI-{model or default_model}")
        self.model = model or default_model
        self.host = default_host
        self.available_models = []
        self._check_model_availability()
    
    def _format_situation_prompt(self, situation: Dict) -> str:
        """Format situation into a prompt for the AI using the configured safety-focused prompt."""
        config = get_config()
        aircraft = situation['aircraft']
        runways = situation['runways']
        gates = situation['gates']
        all_aircraft = situation['all_aircraft']
        safety_context = situation.get('safety_context', {})
        
        # Build runway status string
        runway_status = ""
        for runway in runways:
            status = runway['state']
            occupant = f" (occupied by {runway['occupied_by']})" if runway['occupied_by'] else ""
            runway_status += f"- Runway {runway['id']}: {status}{occupant}\n"
        
        # Build gate status string
        gate_status = ""
        for gate in gates:
            status = "Available" if gate['available'] else f"Occupied by {gate['occupied_by']}"
            gate_status += f"- Gate {gate['id']}: {status}\n"
        
        # Create crash warning if there have been crashes
        crash_warning = ""
        if safety_context.get('total_crashes', 0) > 0:
            crash_warning = f"⚠️ WARNING: {safety_context['total_crashes']} aircraft have already crashed this session!"
            if safety_context.get('crashed_aircraft'):
                crashed_list = ', '.join(safety_context['crashed_aircraft'][-3:])  # Show last 3 crashes
                crash_warning += f" Recent crashes: {crashed_list}"
        
        # Format collision warning if present
        collision_warning = ""
        if situation.get('collision_warning'):
            cw = situation['collision_warning']
            collision_warning = f"🚨 COLLISION ALERT: {cw['warning']} TAKE IMMEDIATE AVOIDANCE ACTION!"
        
        # Use the configured safety-focused prompt with all context
        system_prompt = config.prompts.system_prompt if hasattr(config, 'prompts') and hasattr(config.prompts, 'system_prompt') else "You are an AI air traffic controller. Make safe decisions."
        prompt = system_prompt.format(
            callsign=aircraft['callsign'],
            state=aircraft['state'],
            x=aircraft['position']['x'],
            y=aircraft['position']['y'],
            aircraft_type=aircraft['aircraft_type'],
            assigned_runway=aircraft['assigned_runway'],
            assigned_gate=aircraft['assigned_gate'],
            fuel=aircraft['fuel'],
            is_low_fuel=aircraft['is_low_fuel'],
            is_critical_fuel=aircraft['is_critical_fuel'],
            fuel_priority=aircraft['fuel_priority'],
            runway_count=len(runways),
            runway_status=runway_status.strip(),
            gate_count=len(gates),
            gate_status=gate_status.strip(),
            total_aircraft=len(all_aircraft),
            total_crashes=safety_context.get('total_crashes', 0),
            fuel_emergency_count=safety_context.get('fuel_emergency_count', 0),
            low_fuel_count=safety_context.get('low_fuel_count', 0),
            crash_warning=crash_warning,
            collision_warning=collision_warning
        )
        
        return prompt
    
    def _check_model_availability(self):
        """Check what models are available in ollama."""
        try:
            response = requests.get(f"{self.host}/api/tags", timeout=5)
            if response.status_code == 200:
                data = response.json()
                # Handle both possible response formats
                if 'models' in data:
                    models_list = data['models']
                    if models_list and isinstance(models_list, list):
                        if isinstance(models_list[0], dict):
                            self.available_models = [model.get('name', str(model)) for model in models_list]
                        else:
                            self.available_models = [str(model) for model in models_list]
                    else:
                        self.available_models = []
                else:
                    # Fallback for different API response format
                    self.available_models = []
                
                print(f"Available Ollama models: {', '.join(self.available_models)}")
                
                if self.available_models and self.model not in self.available_models:
                    print(f"Warning: Model '{self.model}' not found in ollama.")
                    print(f"Available models: {', '.join(self.available_models)}")
                    print(f"Falling back to first available model: {self.available_models[0]}")
                    self.model = self.available_models[0]
                    self.name = f"OllamaAI-{self.model}"
                elif not self.available_models:
                    print(f"No models found in ollama, keeping configured model: {self.model}")
            else:
                print(f"Could not connect to ollama at {self.host} (status: {response.status_code})")
        except Exception as e:
            print(f"Could not check ollama models: {e}")
            # Continue with configured model if check fails
    
    def switch_model(self, new_model: str) -> bool:
        """Switch to a different ollama model."""
        if new_model in self.available_models:
            self.model = new_model
            self.name = f"OllamaAI-{new_model}"
            print(f"Switched ollama model to: {new_model}")
            return True
        else:
            print(f"Model '{new_model}' not available. Available: {', '.join(self.available_models)}")
            return False
    
    def get_available_models(self) -> List[str]:
        """Get list of available ollama models."""
        return self.available_models
    
    def make_decision(self, situation: Dict) -> AIResponse:
        """Make decision using ollama."""
        start_time = time.time()  # Track AI thought time
        
        try:
            prompt = self._format_situation_prompt(situation)
            
            response = requests.post(
                f"{self.host}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.3,
                        "top_p": 0.9
                    }
                },
                timeout=10
            )
            
            if response.status_code == 200:
                result = response.json()
                ai_response_text = result.get('response', '').strip()
                
                # Try to parse JSON response
                try:
                    ai_decision = json.loads(ai_response_text)
                    return AIResponse(
                        decision=ai_decision.get('decision', 'wait'),
                        target=ai_decision.get('target'),
                        reasoning=ai_decision.get('reasoning', 'AI decision'),
                        start_time=start_time
                    )
                except json.JSONDecodeError:
                    # Fallback parsing if JSON is malformed
                    return self._parse_text_response(ai_response_text, start_time)
            
        except requests.RequestException as e:
            print(f"Ollama request failed: {e}")
        except Exception as e:
            print(f"Ollama AI error: {e}")
        
        # Fallback to rule-based decision
        fallback_response = RuleBasedAI().make_decision(situation)
        fallback_response.start_time = start_time  # Preserve original start time
        fallback_response.processing_time = time.time() - start_time
        return fallback_response
    
    def _parse_text_response(self, text: str, start_time: float) -> AIResponse:
        """Parse non-JSON text response as backup."""
        text_lower = text.lower()
        
        if 'land' in text_lower:
            return AIResponse(decision='land', reasoning="AI suggested landing", start_time=start_time)
        elif 'gate' in text_lower:
            return AIResponse(decision='gate', reasoning="AI suggested gate assignment", start_time=start_time)
        elif 'takeoff' in text_lower:
            return AIResponse(decision='takeoff', reasoning="AI suggested takeoff", start_time=start_time)
        elif 'hold' in text_lower:
            return AIResponse(decision='hold', reasoning="AI suggested holding pattern", start_time=start_time)
        else:
            return AIResponse(decision='wait', reasoning="AI response unclear, waiting", start_time=start_time)

class RemoteAI(BaseAI):
    """AI implementation using remote API endpoints."""
    
    def __init__(self, endpoint: str, api_key: str = ""):
        super().__init__(f"RemoteAI-{endpoint}")
        self.endpoint = endpoint
        self.api_key = api_key
    
    def make_decision(self, situation: Dict) -> AIResponse:
        """Make decision using remote AI API."""
        start_time = time.time()  # Track AI thought time
        
        try:
            headers = {
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {self.api_key}' if self.api_key else ''
            }
            
            payload = {
                'situation': situation,
                'task': 'air_traffic_control',
                'format': 'json'
            }
            
            response = requests.post(
                self.endpoint,
                json=payload,
                headers=headers,
                timeout=15
            )
            
            if response.status_code == 200:
                result = response.json()
                return AIResponse(
                    decision=result.get('decision', 'wait'),
                    target=result.get('target'),
                    reasoning=result.get('reasoning', 'Remote AI decision'),
                    start_time=start_time
                )
        
        except requests.RequestException as e:
            print(f"Remote AI request failed: {e}")
        except Exception as e:
            print(f"Remote AI error: {e}")
        
        # Fallback to rule-based decision
        fallback_response = RuleBasedAI().make_decision(situation)
        fallback_response.start_time = start_time  # Preserve original start time
        fallback_response.processing_time = time.time() - start_time
        return fallback_response

class AIManager:
    """Manages AI implementations and decision routing."""
    
    def __init__(self):
        config = get_config()
        self.current_ai: BaseAI = RuleBasedAI()
        self.available_ais: Dict[str, BaseAI] = {
            'rule_based': RuleBasedAI(),
        }
        
        # Log initialization
        print(f"AI Decision Logging initialized. Log file: {LOG_FILE_PATH}")
        AI_LOGGER.info("="*80)
        AI_LOGGER.info("AIRPORT SIMULATION AI DECISION LOG - SESSION STARTED")
        AI_LOGGER.info("="*80)
        AI_LOGGER.info(f"Active AI: {self.current_ai.name}")
        AI_LOGGER.info(f"Configuration: {len(self.available_ais)} AI implementations available")
        
        # Initialize ollama AI if available
        ollama_host = config.ai.ollama.host if hasattr(config, 'ai') and hasattr(config.ai, 'ollama') else None
        ai_enabled = getattr(config.ai, 'ai_enabled', True) if hasattr(config, 'ai') else True
        if ollama_host:
            try:
                ollama_ai = OllamaAI()
                self.available_ais['ollama'] = ollama_ai
                if ai_enabled:
                    self.current_ai = ollama_ai
                    AI_LOGGER.info(f"Switched to primary AI: {self.current_ai.name}")
            except Exception as e:
                print(f"Failed to initialize Ollama AI: {e}")
                AI_LOGGER.warning(f"Failed to initialize Ollama AI: {e}")
        
        # Initialize OpenAI if configured
        openai_enabled = getattr(config.ai, 'openai', None) and getattr(config.ai.openai, 'enabled', False) if hasattr(config, 'ai') else False
        if openai_enabled:
            try:
                # Import here to avoid circular imports
                from ai.openai_ai import OpenAI
                
                openai_config = config.ai.openai
                api_key = getattr(openai_config, 'api_key', 'local')
                model = getattr(openai_config, 'model', 'gpt-3.5-turbo')
                base_url = getattr(openai_config, 'base_url', None)
                local_server = getattr(openai_config, 'local_server', False)
                
                openai_ai = OpenAI(
                    api_key=api_key,
                    model=model,
                    base_url=base_url,
                    local_server=local_server
                )
                
                # Try to connect
                if openai_ai.connect():
                    self.available_ais['openai'] = openai_ai
                    AI_LOGGER.info("OpenAI AI initialized successfully")
                else:
                    AI_LOGGER.warning("OpenAI AI failed to connect")
                    
            except Exception as e:
                print(f"Failed to initialize OpenAI AI: {e}")
                AI_LOGGER.warning(f"Failed to initialize OpenAI AI: {e}")
        
        # Initialize remote AI if configured (legacy support)
        remote_endpoint = getattr(config.ai, 'remote_ai_endpoint', None) if hasattr(config, 'ai') else None
        if remote_endpoint:
            try:
                remote_ai = RemoteAI(remote_endpoint)
                self.available_ais['remote'] = remote_ai
                AI_LOGGER.info("Remote AI initialized successfully")
            except Exception as e:
                print(f"Failed to initialize Remote AI: {e}")
                AI_LOGGER.warning(f"Failed to initialize Remote AI: {e}")
        
        AI_LOGGER.info(f"Available AI implementations: {list(self.available_ais.keys())}")
        AI_LOGGER.info("-"*80)
    
    def switch_ai(self, ai_name: str) -> bool:
        """Switch to a different AI implementation."""
        if ai_name in self.available_ais:
            old_ai = self.current_ai.name
            self.current_ai = self.available_ais[ai_name]
            print(f"Switched to AI: {self.current_ai.name}")
            AI_LOGGER.info("="*50)
            AI_LOGGER.info(f"AI SWITCH: {old_ai} → {self.current_ai.name}")
            AI_LOGGER.info("="*50)
            return True
        else:
            AI_LOGGER.warning(f"Failed to switch to AI '{ai_name}' - not available")
        return False
    
    def get_available_ais(self) -> List[str]:
        """Get list of available AI implementations."""
        return list(self.available_ais.keys())
    
    def switch_ollama_model(self, model_name: str) -> bool:
        """Switch the ollama AI to a different model."""
        if 'ollama' in self.available_ais:
            ollama_ai = self.available_ais['ollama']
            if isinstance(ollama_ai, OllamaAI):
                return ollama_ai.switch_model(model_name)
        return False
    
    def get_ollama_models(self) -> List[str]:
        """Get available ollama models."""
        if 'ollama' in self.available_ais:
            ollama_ai = self.available_ais['ollama']
            if isinstance(ollama_ai, OllamaAI):
                return ollama_ai.get_available_models()
        return []
    
    def make_atc_decision(self, aircraft: Aircraft, airport_state: Dict) -> Dict:
        """Make ATC decision using current AI."""
        # Format situation for AI
        situation = {
            'aircraft': {
                'id': aircraft.id,
                'callsign': aircraft.callsign,
                'state': aircraft.state.value,
                'position': {'x': aircraft.position.x, 'y': aircraft.position.y},
                'aircraft_type': aircraft.aircraft_type,
                'assigned_runway': aircraft.assigned_runway,
                'assigned_gate': aircraft.assigned_gate,
                'fuel': aircraft.fuel,
                'is_low_fuel': aircraft.is_low_fuel(),
                'is_critical_fuel': aircraft.is_critical_fuel(),
                'fuel_priority': aircraft.get_fuel_priority()
            },
            'runways': airport_state['runways'],
            'gates': airport_state['gates'],
            'all_aircraft': airport_state['aircraft'],
            'safety_context': {
                'total_crashes': airport_state.get('total_crashes', 0),
                'crashed_aircraft': airport_state.get('crashed_aircraft', []),
                'fuel_emergency_count': sum(1 for a in airport_state['aircraft'] 
                                          if a.get('is_critical_fuel', False)),
                'low_fuel_count': sum(1 for a in airport_state['aircraft'] 
                                    if a.get('is_low_fuel', False) and not a.get('is_critical_fuel', False))
            },
            'collision_warning': airport_state.get('collision_warning', None)
        }
        
        # Get AI decision
        try:
            # Check if this is the new modular AI interface (OpenAI) or old interface
            if hasattr(self.current_ai, 'local_server') or 'OpenAI' in self.current_ai.name:
                # New modular interface expects (aircraft, airport_state, config)
                from config import get_config
                config = get_config()
                # Pass the aircraft dict directly - it's already properly formatted
                ai_response = self.current_ai.make_decision(
                    aircraft=situation['aircraft'],
                    airport_state=situation,
                    config=config
                )
            else:
                # Old interface expects just the situation dict
                ai_response = self.current_ai.make_decision(situation)
        except Exception as e:
            # Fallback error handling
            print(f"AI decision error: {e}")
            ai_response = AIResponse(decision='wait', reasoning=f'AI error: {str(e)}')
        
        # Log decision (if method exists)
        if hasattr(self.current_ai, 'log_decision'):
            self.current_ai.log_decision(situation, ai_response)
        
        # Convert to simulation format
        decision = {
            'aircraft_id': aircraft.id,
            'timestamp': time.time(),
            'action': None,
            'target': ai_response.target,
            'reasoning': ai_response.reasoning,
            'ai_name': self.current_ai.name
        }
        
        # Map AI decisions to simulation actions
        if ai_response.decision == 'land':
            decision['action'] = 'assign_landing'
        elif ai_response.decision == 'gate':
            decision['action'] = 'assign_gate'
        elif ai_response.decision == 'takeoff':
            decision['action'] = 'assign_takeoff'
        elif ai_response.decision == 'assign_runway':
            decision['action'] = 'assign_runway'
        elif ai_response.decision == 'hold':
            decision['action'] = 'hold_pattern'
        elif ai_response.decision == 'avoid':
            decision['action'] = 'collision_avoidance'
        elif ai_response.decision == 'wait':
            decision['action'] = None  # No action
        
        return decision
    
    def get_decision_history(self, ai_name: str = None) -> List[Dict]:
        """Get decision history for analysis."""
        if ai_name and ai_name in self.available_ais:
            return self.available_ais[ai_name].decision_history
        return self.current_ai.decision_history
    
    def get_performance_stats(self, ai_name: str = None) -> Dict:
        """Get performance statistics for an AI."""
        try:
            ai = self.available_ais.get(ai_name, self.current_ai)
            if not ai:
                return {'total_decisions': 0, 'ai_name': 'None'}
                
            history = getattr(ai, 'decision_history', [])
            
            if not history:
                return {'total_decisions': 0, 'ai_name': ai.name}
            
            total_decisions = len(history)
            decision_types = {}
            avg_response_time = 0
            
            for decision in history:
                if isinstance(decision, dict):
                    decision_type = decision.get('decision', 'unknown')
                    decision_types[decision_type] = decision_types.get(decision_type, 0) + 1
            
            return {
                'ai_name': ai.name,
                'total_decisions': total_decisions,
                'decision_breakdown': decision_types,
                'avg_response_time': avg_response_time
            }
        except Exception as e:
            print(f"Error getting performance stats: {e}")
            return {'total_decisions': 0, 'ai_name': 'Error'} 