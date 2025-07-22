"""Configuration manager for the AI Airport Simulation."""

import os
import yaml
import logging
from dataclasses import dataclass, field
from typing import Dict, Any, Optional


@dataclass
class Config:
    """Main configuration container with basic structure."""
    
    def __init__(self):
        # Airport configuration
        self.airport = type('obj', (object,), {
            'airport_width': 1200,
            'airport_height': 800,
            'runways': type('obj', (object,), {'count': 2})(),
            'gates': type('obj', (object,), {'count': 4})()
        })()
        
        # AI configuration
        self.ai = type('obj', (object,), {
            'default_mode': 'rule_based',
            'ollama': type('obj', (object,), {
                'host': 'http://localhost:11434',
                'model': 'granite3.2:latest'
            })(),
            'openai': type('obj', (object,), {
                'enabled': False,
                'api_key': '',
                'model': 'gpt-3.5-turbo'
            })()
        })()
        
        # Prompts configuration
        self.prompts = type('obj', (object,), {
            'system_prompt': ''
        })()


class ConfigManager:
    """Configuration manager for loading and managing config data."""
    
    def __init__(self, config_path: str = "config.yaml"):
        self.config_path = config_path
        self.logger = logging.getLogger(__name__)
        self._config = None
    
    def load_config(self) -> Config:
        """Load configuration from YAML file."""
        if not os.path.exists(self.config_path):
            self.logger.warning(f"Config file {self.config_path} not found, using defaults")
            self._config = Config()
            return self._config
        
        try:
            with open(self.config_path, 'r') as file:
                yaml_data = yaml.safe_load(file)
            
            config = Config()
            
            # Load airport settings
            if 'airport' in yaml_data:
                airport_data = yaml_data['airport']
                config.airport.airport_width = airport_data.get('airport_width', 1200)
                config.airport.airport_height = airport_data.get('airport_height', 800)
                
                if 'runways' in airport_data:
                    config.airport.runways.count = airport_data['runways'].get('count', 2)
                if 'gates' in airport_data:
                    config.airport.gates.count = airport_data['gates'].get('count', 4)
            
            # Load AI settings
            if 'ai' in yaml_data:
                ai_data = yaml_data['ai']
                config.ai.default_mode = ai_data.get('default_mode', 'rule_based')
                
                if 'ollama' in ai_data:
                    ollama_data = ai_data['ollama']
                    config.ai.ollama.host = ollama_data.get('host', 'http://localhost:11434')
                    config.ai.ollama.model = ollama_data.get('model', 'granite3.2:latest')
                
                if 'openai' in ai_data:
                    openai_data = ai_data['openai']
                    config.ai.openai.enabled = openai_data.get('enabled', False)
                    config.ai.openai.api_key = openai_data.get('api_key', '')
                    config.ai.openai.model = openai_data.get('model', 'gpt-3.5-turbo')
            
            # Load prompts
            if 'prompts' in yaml_data:
                config.prompts.system_prompt = yaml_data['prompts'].get('system_prompt', '')
            
            # Apply environment overrides
            openai_key = os.getenv('OPENAI_API_KEY')
            if openai_key:
                config.ai.openai.api_key = openai_key
            
            self._config = config
            self.logger.info(f"Configuration loaded from {self.config_path}")
            return config
            
        except Exception as e:
            self.logger.error(f"Error loading config: {e}")
            self._config = Config()
            return self._config
    
    def get_config(self) -> Config:
        """Get current configuration, loading if necessary."""
        if self._config is None:
            return self.load_config()
        return self._config


# Global configuration manager instance
config_manager = ConfigManager()


def get_config() -> Config:
    """Get the global configuration instance."""
    return config_manager.get_config()