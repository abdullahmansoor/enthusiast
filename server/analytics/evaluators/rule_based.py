"""
Stage 1: Rule-based evaluators (fast, no external dependencies).

These metrics are computed using simple rules and regex patterns:
- PII detection
- Language detection
- Response length
- Token counting
- Business metrics: failure rate, knowledge gaps, user satisfaction, latency,
  session depth, abandonment, product surfacing
"""

import re
from typing import Dict, Any

from analytics.evaluators.registry import registry, MetricDefinition

# Phrases that signal the agent couldn't find relevant information
_KNOWLEDGE_GAP_PATTERNS = [
    r"don['\u2019]t have information",
    r"not in (?:my |the )?knowledge base",
    r"i cannot find",
    r"no (?:relevant )?(?:documents?|products?|information|data) (?:found|available)",
    r"outside (?:my |the )?(?:scope|knowledge)",
    r"i (?:don['\u2019]t|do not) have (?:enough |any )?(?:information|data|context) (?:to answer|about)",
    r"documents? and products? lists? are (?:completely )?empty",
]
_KNOWLEDGE_GAP_RE = re.compile(
    "|".join(_KNOWLEDGE_GAP_PATTERNS), re.IGNORECASE
)

# Patterns that indicate a product was surfaced (price mention, product category, name-like patterns)
_PRODUCT_SURFACE_PATTERNS = [
    r"\$[\d,]+(?:\.\d{2})?",          # Price: $XX.XX
    r"£[\d,]+(?:\.\d{2})?",
    r"€[\d,]+(?:\.\d{2})?",
    r"\b(?:price|cost|costs|priced at)\b",
    r"\b(?:category|categories)\b",
    r"\b(?:sku|model #|item #|product id)\b",
]
_PRODUCT_SURFACE_RE = re.compile(
    "|".join(_PRODUCT_SURFACE_PATTERNS), re.IGNORECASE
)


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


def compute_answer_failed(turn_data: Dict[str, Any]) -> float:
    """
    Flag turns where the agent failed to produce an answer.

    Args:
        turn_data: Dictionary with 'answer_failed' key (bool)

    Returns:
        1.0 if the answer failed, 0.0 otherwise
    """
    return 1.0 if turn_data.get('answer_failed', False) else 0.0


def compute_knowledge_gap(turn_data: Dict[str, Any]) -> float:
    """
    Detect turns where the agent explicitly states it lacks information.

    High values indicate gaps in the knowledge base / product catalog —
    questions customers ask that the agent can't answer.

    Args:
        turn_data: Dictionary with 'assistant_text' key

    Returns:
        1.0 if a knowledge gap phrase is detected, 0.0 otherwise
    """
    text = turn_data.get('assistant_text', '')
    return 1.0 if _KNOWLEDGE_GAP_RE.search(text) else 0.0


def compute_product_surface(turn_data: Dict[str, Any]) -> float:
    """
    Detect turns where the agent surfaced a product (mentioned price, category, etc.).

    For sales/product-discovery agents: low product_surface_rate means the
    agent is not driving product discovery even when products exist.

    Args:
        turn_data: Dictionary with 'assistant_text' key

    Returns:
        1.0 if a product was surfaced in the response, 0.0 otherwise
    """
    text = turn_data.get('assistant_text', '')
    return 1.0 if _PRODUCT_SURFACE_RE.search(text) else 0.0


def compute_response_latency(turn_data: Dict[str, Any]) -> float:
    """
    Compute response latency in seconds (time from user message to assistant reply).

    Args:
        turn_data: Dictionary with 'latency_seconds' key (float)

    Returns:
        Latency in seconds, or -1.0 if not available
    """
    latency = turn_data.get('latency_seconds')
    if latency is None or latency < 0:
        return -1.0
    return float(latency)


def compute_user_rating(turn_data: Dict[str, Any]) -> float:
    """
    Extract user-provided rating for this turn.

    Args:
        turn_data: Dictionary with 'user_rating' key (int or None)

    Returns:
        Rating value normalised to [0,1] assuming 1–5 scale, or -1.0 if not rated
    """
    rating = turn_data.get('user_rating')
    if rating is None:
        return -1.0  # sentinel: not rated
    # Normalise from 1–5 → 0.0–1.0
    return max(0.0, min(1.0, (float(rating) - 1) / 4.0))


# ── Session-level business metrics ──────────────────────────────────────────


def compute_session_depth(session_data: Dict[str, Any]) -> float:
    """
    Total number of turns (user + assistant) in the session.

    Higher depth = user engaged long enough to have a multi-turn conversation.
    Compare alongside user_abandonment to distinguish "engaged" from "stuck".

    Args:
        session_data: Dictionary with 'messages' key

    Returns:
        Turn count as float
    """
    messages = session_data.get('messages', [])
    return float(len(messages))


def compute_user_abandonment(session_data: Dict[str, Any]) -> float:
    """
    Detect whether the user abandoned the conversation without a final reply.

    If the last message is from the assistant (user never replied back after the
    final response), it suggests the user left — either satisfied or frustrated.
    Combined with session_depth and knowledge_gap_rate this becomes meaningful.

    Args:
        session_data: Dictionary with 'messages' key

    Returns:
        1.0 if the last message is from the assistant, 0.0 otherwise
    """
    messages = session_data.get('messages', [])
    if not messages:
        return 0.0
    last_role = messages[-1].get('role', '')
    return 1.0 if last_role == 'assistant' else 0.0


def compute_answer_failure_rate(session_data: Dict[str, Any]) -> float:
    """
    Fraction of assistant turns in the session where the agent failed to answer.

    Args:
        session_data: Dictionary with 'turn_metrics' key

    Returns:
        Failure rate (0.0 = no failures, 1.0 = all turns failed)
    """
    turn_metrics = session_data.get('turn_metrics', {})
    values = turn_metrics.get('answer_failed', [])
    if not values:
        return 0.0
    return float(sum(values) / len(values))


def compute_knowledge_gap_rate(session_data: Dict[str, Any]) -> float:
    """
    Fraction of assistant turns where a knowledge gap was detected.

    Args:
        session_data: Dictionary with 'turn_metrics' key

    Returns:
        Knowledge gap rate (0.0 = no gaps, 1.0 = every turn had a gap)
    """
    turn_metrics = session_data.get('turn_metrics', {})
    values = turn_metrics.get('knowledge_gap', [])
    if not values:
        return 0.0
    return float(sum(values) / len(values))


def compute_user_satisfaction_score(session_data: Dict[str, Any]) -> float:
    """
    Average user rating across all rated turns in the session.

    Only considers turns where a rating was provided (skips -1.0 sentinels).

    Args:
        session_data: Dictionary with 'turn_metrics' key

    Returns:
        Mean normalised rating [0,1], or -1.0 if no turns were rated
    """
    turn_metrics = session_data.get('turn_metrics', {})
    values = [v for v in turn_metrics.get('user_rating', []) if v >= 0]
    if not values:
        return -1.0
    return float(sum(values) / len(values))


# ── Register all metrics ─────────────────────────────────────────────────────

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

# ── Business metrics: turn-level ─────────────────────────────────────────────

registry.register(MetricDefinition(
    name='answer_failed',
    display_name='Answer Failed',
    description='Whether the agent failed to produce an answer for this turn (1=failed, 0=ok)',
    level='turn',
    stage=1,
    compute_turn=compute_answer_failed
))

registry.register(MetricDefinition(
    name='knowledge_gap',
    display_name='Knowledge Gap',
    description='Whether the agent stated it lacked information to answer (1=gap detected, 0=ok)',
    level='turn',
    stage=1,
    compute_turn=compute_knowledge_gap
))

registry.register(MetricDefinition(
    name='product_surface',
    display_name='Product Surfaced',
    description='Whether the agent mentioned a product (price, category, etc.) in its response (1=yes, 0=no)',
    level='turn',
    stage=1,
    compute_turn=compute_product_surface
))

registry.register(MetricDefinition(
    name='response_latency',
    display_name='Response Latency (seconds)',
    description='Time in seconds from user message to assistant reply. -1 if not available.',
    level='turn',
    stage=1,
    compute_turn=compute_response_latency
))

registry.register(MetricDefinition(
    name='user_rating',
    display_name='User Rating (normalised)',
    description='User-provided rating normalised to [0,1]. -1 if the turn was not rated.',
    level='turn',
    stage=1,
    compute_turn=compute_user_rating
))

# ── Business metrics: session-level ──────────────────────────────────────────

registry.register(MetricDefinition(
    name='session_depth',
    display_name='Session Depth (turns)',
    description='Total number of messages (user + assistant) in the session',
    level='session',
    stage=1,
    reduce_session=compute_session_depth
))

registry.register(MetricDefinition(
    name='user_abandonment',
    display_name='User Abandoned Session',
    description='1 if the session ended with an unanswered assistant message (user left), 0 if user sent the last message',
    level='session',
    stage=1,
    reduce_session=compute_user_abandonment
))

registry.register(MetricDefinition(
    name='answer_failure_rate',
    display_name='Answer Failure Rate',
    description='Fraction of turns in the session where the agent failed to produce an answer (0=none failed, 1=all failed)',
    level='session',
    stage=1,
    reduce_session=compute_answer_failure_rate
))

registry.register(MetricDefinition(
    name='knowledge_gap_rate',
    display_name='Knowledge Gap Rate',
    description='Fraction of turns where the agent stated it lacked information. High values = gaps in your knowledge base.',
    level='session',
    stage=1,
    reduce_session=compute_knowledge_gap_rate
))

registry.register(MetricDefinition(
    name='user_satisfaction_score',
    display_name='User Satisfaction Score',
    description='Average user rating across rated turns, normalised to [0,1]. -1 if no turns were rated.',
    level='session',
    stage=1,
    reduce_session=compute_user_satisfaction_score
))
