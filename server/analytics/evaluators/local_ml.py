"""
Stage 2: Local ML evaluators (moderate speed, free, works offline).

These metrics use locally-run transformer models:
- Toxicity detection (Detoxify)
- Coherence scoring (Sentence-BERT)
- Repetition detection

These models are lazy-loaded to avoid startup overhead.
Can be disabled via ANALYTICS_CONFIG['enable_local_models'] = False
"""

from typing import Dict, Any
import numpy as np

from analytics.evaluators.registry import registry, MetricDefinition

# Lazy load heavy models to avoid startup overhead
_toxicity_model = None
_sentence_transformer = None


def get_toxicity_model():
    """
    Lazy load Detoxify model for toxicity detection.

    Returns:
        Detoxify model instance
    """
    global _toxicity_model
    if _toxicity_model is None:
        try:
            from detoxify import Detoxify
            _toxicity_model = Detoxify('original')
        except ImportError:
            raise ImportError(
                "detoxify is not installed. Install with: pip install detoxify"
            )
    return _toxicity_model


def get_sentence_transformer():
    """
    Lazy load Sentence-BERT model for embeddings.

    Returns:
        SentenceTransformer model instance
    """
    global _sentence_transformer
    if _sentence_transformer is None:
        try:
            from sentence_transformers import SentenceTransformer
            # Use lightweight model for speed
            _sentence_transformer = SentenceTransformer('all-MiniLM-L6-v2')
        except ImportError:
            raise ImportError(
                "sentence-transformers is not installed. "
                "Install with: pip install sentence-transformers"
            )
    return _sentence_transformer


def compute_toxicity(turn_data: Dict[str, Any]) -> float:
    """
    Compute toxicity score using Detoxify model.

    Checks for:
    - Toxicity
    - Severe toxicity
    - Obscene content
    - Threats
    - Insults
    - Identity attacks

    Args:
        turn_data: Dictionary with 'assistant_text' key

    Returns:
        Max toxicity score across all categories (0.0 to 1.0)
    """
    assistant_text = turn_data.get('assistant_text', '')

    if not assistant_text:
        return 0.0

    try:
        model = get_toxicity_model()
        results = model.predict(assistant_text)

        # Return max toxicity across all categories
        toxicity = max(
            results.get('toxicity', 0),
            results.get('severe_toxicity', 0),
            results.get('obscene', 0),
            results.get('threat', 0),
            results.get('insult', 0),
            results.get('identity_attack', 0)
        )

        return float(toxicity)

    except Exception as e:
        print(f"Error computing toxicity: {e}")
        return 0.0


def compute_coherence(turn_data: Dict[str, Any]) -> float:
    """
    Compute coherence score using sentence embeddings.

    Measures how well the assistant's response relates to the user's query
    using cosine similarity of sentence embeddings.

    Args:
        turn_data: Dictionary with 'user_text' and 'assistant_text' keys

    Returns:
        Coherence score (0.0 to 1.0), higher is better
    """
    user_text = turn_data.get('user_text', '')
    assistant_text = turn_data.get('assistant_text', '')

    if not user_text or not assistant_text:
        return 0.5  # Neutral score if missing text

    try:
        model = get_sentence_transformer()

        # Get embeddings for both texts
        embeddings = model.encode([user_text, assistant_text])

        # Compute cosine similarity
        similarity = np.dot(embeddings[0], embeddings[1]) / (
            np.linalg.norm(embeddings[0]) * np.linalg.norm(embeddings[1])
        )

        # Scale from [-1, 1] to [0, 1]
        coherence = (similarity + 1) / 2

        return float(coherence)

    except Exception as e:
        print(f"Error computing coherence: {e}")
        return 0.5


def compute_repetition(session_data: Dict[str, Any]) -> float:
    """
    Compute repetition score for a session.

    Measures how much the assistant repeats itself using n-gram overlap.

    Args:
        session_data: Dictionary with 'messages' key containing list of message dicts

    Returns:
        Repetition score (0.0 to 1.0), higher means more repetitive
    """
    messages = session_data.get('messages', [])

    # Filter for assistant messages
    assistant_messages = [
        msg['text'] for msg in messages
        if msg.get('role') == 'assistant'
    ]

    if len(assistant_messages) < 2:
        return 0.0  # No repetition possible with < 2 messages

    try:
        # Extract trigrams from each message
        def get_trigrams(text):
            words = text.lower().split()
            return set(tuple(words[i:i+3]) for i in range(len(words)-2))

        all_trigrams = []
        unique_trigrams = set()

        for msg in assistant_messages:
            trigrams = get_trigrams(msg)
            all_trigrams.extend(trigrams)
            unique_trigrams.update(trigrams)

        if not all_trigrams:
            return 0.0

        # Repetition = 1 - (unique / total)
        repetition = 1.0 - (len(unique_trigrams) / len(all_trigrams))

        return float(repetition)

    except Exception as e:
        print(f"Error computing repetition: {e}")
        return 0.0


# Register metrics
registry.register(MetricDefinition(
    name='toxicity',
    display_name='Toxicity',
    description='Toxicity score using Detoxify model (0=safe, 1=toxic)',
    level='turn',
    stage=2,
    compute_turn=compute_toxicity
))

registry.register(MetricDefinition(
    name='coherence',
    display_name='Coherence',
    description='How well response relates to query using sentence embeddings (0=poor, 1=excellent)',
    level='turn',
    stage=2,
    compute_turn=compute_coherence
))

registry.register(MetricDefinition(
    name='repetition',
    display_name='Repetition',
    description='Amount of repetitive content in conversation using n-gram overlap (0=no repetition, 1=very repetitive)',
    level='session',
    stage=2,
    reduce_session=compute_repetition
))
