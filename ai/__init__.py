"""
AI package for the AI Airport Simulation.

This package contains different AI implementations for air traffic control:
- BaseAI: Abstract base class for all AI implementations
- RuleBasedAI: Simple rule-based decision making
- OllamaAI: Integration with Ollama local AI models
- OpenAI: Integration with OpenAI ChatGPT API
"""

from .base_ai import BaseAI, AIResponse
from .rule_based_ai import RuleBasedAI
from .ollama_ai import OllamaAI
from .openai_ai import OpenAI

__all__ = [
    'BaseAI', 'AIResponse',
    'RuleBasedAI', 'OllamaAI', 'OpenAI'
] 