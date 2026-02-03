"""
Stage 1: Rule-based evaluators (fast, no external dependencies).

These metrics are computed using simple rules and regex patterns:
- PII detection
- Language detection
- Response length
- Token counting

These are always enabled and run synchronously.
"""

import re
from typing import Dict, Any

from analytics.evaluators.registry import registry, MetricDefinition


def detect_pii(text: str) -> bool:
    """
    Detect Personally Identifiable Information using regex patterns.

    Patterns checked:
    - Email addresses
    - Phone numbers (US format)
    - Social Security Numbers (US)
    - Credit card numbers (basic pattern)

    Args:
        text: Text to check

    Returns:
        True if PII is detected, False otherwise
    """
    patterns = [
        # Email
        r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
        # Phone (US format)
        r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b',
        # SSN (US)
        r'\b\d{3}-\d{2}-\d{4}\b',
        # Credit card (basic - 4 groups of 4 digits)
        r'\b\d{4}[- ]?\d{4}[- ]?\d{4}[- ]?\d{4}\b',
    ]

    for pattern in patterns:
        if re.search(pattern, text, re.IGNORECASE):
            return True

    return False


def detect_language(text: str) -> str:
    """
    Detect language of text using langdetect library.

    Args:
        text: Text to analyze

    Returns:
        ISO 639-1 language code (e.g., 'en', 'es', 'fr') or 'unknown'
    """
    try:
        from langdetect import detect, LangDetectException
        return detect(text)
    except (LangDetectException, ImportError):
        return 'unknown'


def compute_pii_flag(turn_data: Dict[str, Any]) -> float:
    """
    Compute PII flag for a turn.

    Args:
        turn_data: Dictionary with 'assistant_text' key

    Returns:
        1.0 if PII detected, 0.0 otherwise
    """
    assistant_text = turn_data.get('assistant_text', '')
    return 1.0 if detect_pii(assistant_text) else 0.0


def compute_response_length(turn_data: Dict[str, Any]) -> float:
    """
    Compute response length in characters.

    Args:
        turn_data: Dictionary with 'assistant_text' key

    Returns:
        Length of response in characters
    """
    assistant_text = turn_data.get('assistant_text', '')
    return float(len(assistant_text))


def compute_response_words(turn_data: Dict[str, Any]) -> float:
    """
    Compute response length in words.

    Args:
        turn_data: Dictionary with 'assistant_text' key

    Returns:
        Length of response in words
    """
    assistant_text = turn_data.get('assistant_text', '')
    words = assistant_text.split()
    return float(len(words))


def compute_language(turn_data: Dict[str, Any]) -> float:
    """
    Detect language of assistant response.

    Note: This returns a string, not a float, but we encode it
    as the hash of the language code for storage.

    Args:
        turn_data: Dictionary with 'assistant_text' key

    Returns:
        Hash of language code (for storage as float)
    """
    assistant_text = turn_data.get('assistant_text', '')
    lang = detect_language(assistant_text)

    # Encode language as numeric value for storage
    # This is a simple hash - in practice, you might want to store
    # the actual language string in metadata instead
    return float(hash(lang) % 1000)


# Register metrics
registry.register(MetricDefinition(
    name='pii_flag',
    display_name='PII Detected',
    description='Whether personally identifiable information was detected in the response',
    level='turn',
    stage=1,
    compute_turn=compute_pii_flag
))

registry.register(MetricDefinition(
    name='response_length',
    display_name='Response Length (characters)',
    description='Length of assistant response in characters',
    level='turn',
    stage=1,
    compute_turn=compute_response_length
))

registry.register(MetricDefinition(
    name='response_words',
    display_name='Response Length (words)',
    description='Length of assistant response in words',
    level='turn',
    stage=1,
    compute_turn=compute_response_words
))
