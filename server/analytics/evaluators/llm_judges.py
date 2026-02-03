"""
Stage 3: LLM-as-judge evaluators (slow, costly, high quality).

These metrics use GPT-4o-mini to evaluate subjective quality:
- Answer relevance: Does the response answer the question?
- Faithfulness: Is the response grounded in the provided context?

These are the most expensive metrics and should be sampled (not run on every message).
Configure sampling rate via ANALYTICS_CONFIG['llm_sampling_rate'] (default: 0.1 = 10%)
"""

from typing import Dict, Any
import json
import random

from django.conf import settings

from analytics.evaluators.registry import registry, MetricDefinition

# Get OpenAI API key from settings
OPENAI_API_KEY = getattr(settings, 'OPENAI_API_KEY', None)

# Get sampling rate from settings (default 10%)
ANALYTICS_CONFIG = getattr(settings, 'ANALYTICS_CONFIG', {})
LLM_SAMPLING_RATE = ANALYTICS_CONFIG.get('llm_sampling_rate', 0.1)


def should_sample() -> bool:
    """
    Determine if this evaluation should run based on sampling rate.

    Returns:
        True if should evaluate, False otherwise
    """
    return random.random() < LLM_SAMPLING_RATE


def call_openai(messages, temperature=0.0, max_tokens=200):
    """
    Call OpenAI API with retry logic.

    Args:
        messages: List of message dicts
        temperature: Sampling temperature
        max_tokens: Max tokens in response

    Returns:
        Response content string

    Raises:
        Exception if API call fails
    """
    if not OPENAI_API_KEY:
        raise ValueError("OPENAI_API_KEY not configured in settings")

    try:
        from openai import OpenAI
        client = OpenAI(api_key=OPENAI_API_KEY)

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens
        )

        return response.choices[0].message.content

    except ImportError:
        raise ImportError("openai package not installed. Install with: pip install openai")
    except Exception as e:
        raise Exception(f"OpenAI API error: {str(e)}")


def compute_answer_relevance(turn_data: Dict[str, Any]) -> float:
    """
    Evaluate answer relevance using GPT-4o-mini as judge.

    Measures how well the assistant's response answers the user's question.

    Args:
        turn_data: Dictionary with 'user_text' and 'assistant_text' keys

    Returns:
        Relevance score (0.0 to 1.0), higher is better
    """
    # Sampling check
    if not should_sample():
        return -1.0  # Sentinel value indicating "not evaluated"

    user_text = turn_data.get('user_text', '')
    assistant_text = turn_data.get('assistant_text', '')

    if not user_text or not assistant_text:
        return 0.5  # Neutral score if missing text

    prompt = f"""Rate the relevance of the assistant's response to the user's question on a scale of 0.0 to 1.0.

User Question: {user_text}

Assistant Response: {assistant_text}

Respond with ONLY a JSON object in this exact format:
{{"relevance": 0.85, "reasoning": "brief explanation"}}"""

    try:
        messages = [
            {"role": "system", "content": "You are an impartial judge evaluating chatbot responses. Be objective and consistent."},
            {"role": "user", "content": prompt}
        ]

        response_text = call_openai(messages, temperature=0.0, max_tokens=150)

        # Parse JSON response
        result = json.loads(response_text)
        relevance = float(result.get('relevance', 0.5))

        # Clamp to [0, 1]
        return max(0.0, min(1.0, relevance))

    except Exception as e:
        print(f"Error in answer_relevance evaluation: {e}")
        return 0.5  # Neutral on error


def compute_faithfulness(turn_data: Dict[str, Any]) -> float:
    """
    Evaluate faithfulness to retrieved context using GPT-4o-mini as judge.

    Measures whether the assistant's response is grounded in the provided context
    or if it hallucinates information.

    Args:
        turn_data: Dictionary with 'context' and 'assistant_text' keys

    Returns:
        Faithfulness score (0.0 to 1.0), higher is better
    """
    # Sampling check
    if not should_sample():
        return -1.0  # Sentinel value indicating "not evaluated"

    context = turn_data.get('context', '')
    assistant_text = turn_data.get('assistant_text', '')

    if not context:
        return 1.0  # No context means no grounding required

    if not assistant_text:
        return 0.5

    prompt = f"""Evaluate if the assistant's response is faithful to the provided context.
Rate from 0.0 (completely fabricated/hallucinated) to 1.0 (fully grounded in context).

Context:
{context}

Assistant Response:
{assistant_text}

Respond with ONLY a JSON object in this exact format:
{{"faithfulness": 0.9, "unsupported_claims": ["claim1", "claim2"], "reasoning": "explanation"}}"""

    try:
        messages = [
            {"role": "system", "content": "You are an impartial judge evaluating factual accuracy and grounding. Be strict about hallucinations."},
            {"role": "user", "content": prompt}
        ]

        response_text = call_openai(messages, temperature=0.0, max_tokens=200)

        # Parse JSON response
        result = json.loads(response_text)
        faithfulness = float(result.get('faithfulness', 1.0))

        # Clamp to [0, 1]
        return max(0.0, min(1.0, faithfulness))

    except Exception as e:
        print(f"Error in faithfulness evaluation: {e}")
        return 1.0  # Neutral on error (assume faithful)


def compute_composite_quality(session_data: Dict[str, Any]) -> float:
    """
    Compute composite quality score from multiple metrics.

    This aggregates turn-level metrics into a single quality score for the session.

    Args:
        session_data: Dictionary with 'turn_metrics' key containing list of metric dicts

    Returns:
        Composite quality score (0.0 to 1.0)
    """
    turn_metrics = session_data.get('turn_metrics', {})

    if not turn_metrics:
        return 0.5

    # Weights for each metric
    weights = {
        'answer_relevance': 0.4,
        'faithfulness': 0.3,
        'coherence': 0.2,
        'toxicity': -0.1,  # Negative weight (lower is better)
    }

    total_weight = 0
    weighted_sum = 0

    for metric_name, weight in weights.items():
        if metric_name in turn_metrics:
            values = turn_metrics[metric_name]
            if values:
                avg_value = sum(values) / len(values)
                weighted_sum += weight * avg_value
                total_weight += abs(weight)

    if total_weight == 0:
        return 0.5

    # Normalize to [0, 1]
    composite = weighted_sum / total_weight

    # Handle toxicity (which was negative)
    composite = (composite + 1) / 2 if any(w < 0 for w in weights.values()) else composite

    return max(0.0, min(1.0, composite))


# Register metrics
registry.register(MetricDefinition(
    name='answer_relevance',
    display_name='Answer Relevance (LLM-judged)',
    description='How well the response answers the user question, evaluated by GPT-4o-mini (0=poor, 1=excellent)',
    level='turn',
    stage=3,
    compute_turn=compute_answer_relevance
))

registry.register(MetricDefinition(
    name='faithfulness',
    display_name='Faithfulness (LLM-judged)',
    description='How well the response is grounded in the provided context, evaluated by GPT-4o-mini (0=hallucinated, 1=grounded)',
    level='turn',
    stage=3,
    compute_turn=compute_faithfulness
))

registry.register(MetricDefinition(
    name='composite_quality',
    display_name='Composite Quality Score',
    description='Weighted average of multiple quality metrics (0=poor, 1=excellent)',
    level='session',
    stage=3,
    reduce_session=compute_composite_quality
))
