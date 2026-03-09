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

# Get analytics config and OpenAI API key from settings
ANALYTICS_CONFIG = getattr(settings, 'ANALYTICS_CONFIG', {})
OPENAI_API_KEY = ANALYTICS_CONFIG.get('openai_api_key') or getattr(settings, 'OPENAI_API_KEY', None)

# Get sampling rate from settings (default 10%)
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

    # Weights: business outcomes weighted higher than proxy quality metrics.
    # Positive weights → higher is better.
    # Negative weights → metric penalises score when high.
    weights = {
        'answer_relevance': 0.25,
        'faithfulness': 0.15,
        'coherence': 0.10,
        'toxicity': -0.10,          # penalty: higher toxicity → lower score
        'answer_failed': -0.20,     # penalty: failures directly hurt reliability
        'knowledge_gap': -0.10,     # penalty: gaps mean users can't get answers
        'user_rating': 0.10,        # bonus: direct customer signal (sparse but strong)
    }

    total_abs_weight = 0
    weighted_sum = 0

    for metric_name, weight in weights.items():
        values = [v for v in turn_metrics.get(metric_name, []) if v >= 0]
        if values:
            avg_value = sum(values) / len(values)
            weighted_sum += weight * avg_value
            total_abs_weight += abs(weight)

    if total_abs_weight == 0:
        return 0.5

    # Normalise: shift from [-1,1]-ish space to [0,1]
    raw = weighted_sum / total_abs_weight
    composite = (raw + 1.0) / 2.0

    return max(0.0, min(1.0, composite))


# Intent label → numeric encoding (stable mapping for storage as float)
INTENT_LABELS = [
    'product_search',       # 0
    'price_inquiry',        # 1
    'availability_check',   # 2
    'how_to_use',           # 3
    'support_complaint',    # 4
    'comparison',           # 5
    'general',              # 6
]
INTENT_TO_FLOAT = {label: float(i) for i, label in enumerate(INTENT_LABELS)}


def compute_intent_classification(turn_data: Dict[str, Any]) -> float:
    """
    Classify the user query intent using GPT-4o-mini.

    Intent types (encoded as float index):
    - 0: product_search   — "show me running shoes under $100"
    - 1: price_inquiry    — "how much does X cost"
    - 2: availability_check — "do you have X in stock"
    - 3: how_to_use       — "how do I set up X"
    - 4: support_complaint — "my order hasn't arrived"
    - 5: comparison       — "what's the difference between X and Y"
    - 6: general          — anything else

    This is the highest-value business intelligence metric: it tells you
    what customers actually want, enabling product and content decisions.

    Args:
        turn_data: Dictionary with 'user_text' key

    Returns:
        Float index of classified intent, or -1.0 if not sampled / unavailable
    """
    if not should_sample():
        return -1.0

    user_text = turn_data.get('user_text', '').strip()
    if not user_text:
        return INTENT_TO_FLOAT['general']

    prompt = f"""Classify the following customer message into exactly one intent category.

Customer message: "{user_text}"

Categories:
- product_search: looking for products, browsing, discovery
- price_inquiry: asking about cost or pricing
- availability_check: asking if something is in stock or available
- how_to_use: asking how to use, install, or operate something
- support_complaint: reporting an issue, complaint, or problem
- comparison: comparing two or more products or options
- general: anything that doesn't fit the above

Respond with ONLY a JSON object in this exact format:
{{"intent": "product_search", "confidence": 0.9}}"""

    try:
        messages = [
            {"role": "system", "content": "You are a customer intent classifier. Be consistent and objective."},
            {"role": "user", "content": prompt}
        ]
        response_text = call_openai(messages, temperature=0.0, max_tokens=60)
        result = json.loads(response_text)
        intent = result.get('intent', 'general')
        return INTENT_TO_FLOAT.get(intent, INTENT_TO_FLOAT['general'])

    except Exception as e:
        print(f"Error in intent_classification: {e}")
        return INTENT_TO_FLOAT['general']


def compute_resolution_quality(turn_data: Dict[str, Any]) -> float:
    """
    Evaluate whether the agent's response actually resolves the user's need,
    beyond surface-level relevance.

    This is a deeper quality signal than answer_relevance:
    - answer_relevance asks "did the response address the question?"
    - resolution_quality asks "did it *solve* the problem / meet the need?"

    For product queries: did the agent recommend something actionable?
    For support: did the agent provide a clear resolution path?

    Args:
        turn_data: Dictionary with 'user_text', 'assistant_text', 'context' keys

    Returns:
        Resolution quality score (0.0 = unresolved, 1.0 = fully resolved),
        or -1.0 if not sampled
    """
    if not should_sample():
        return -1.0

    user_text = turn_data.get('user_text', '')
    assistant_text = turn_data.get('assistant_text', '')

    if not user_text or not assistant_text:
        return 0.5

    prompt = f"""Evaluate whether the assistant's response fully resolves the customer's need.

Customer message: {user_text}

Assistant response: {assistant_text}

Score from 0.0 to 1.0:
- 1.0: Fully resolved — customer can take a clear next step based on this response
- 0.7: Mostly resolved — useful but missing a detail
- 0.4: Partially resolved — addresses topic but doesn't solve the need
- 0.1: Not resolved — off-topic, vague, or explicitly says it can't help
- 0.0: Harmful / misleading response

Respond with ONLY a JSON object:
{{"resolution": 0.85, "reasoning": "brief explanation"}}"""

    try:
        messages = [
            {"role": "system", "content": "You are evaluating whether AI assistant responses actually solve customer problems. Focus on actionability and completeness."},
            {"role": "user", "content": prompt}
        ]
        response_text = call_openai(messages, temperature=0.0, max_tokens=150)
        result = json.loads(response_text)
        score = float(result.get('resolution', 0.5))
        return max(0.0, min(1.0, score))

    except Exception as e:
        print(f"Error in resolution_quality: {e}")
        return 0.5


def compute_knowledge_gap_llm(turn_data: Dict[str, Any]) -> float:
    """
    Use an LLM to detect whether the agent failed to answer due to a knowledge gap,
    even when the response doesn't use explicit "I don't know" phrasing.

    More robust than regex-based detection which misses:
    - Vague / deflecting responses ("That's a great question...")
    - Partial answers that dodge the core query
    - Responses that hallucinate rather than admitting gaps

    Args:
        turn_data: Dictionary with 'user_text' and 'assistant_text' keys

    Returns:
        Probability of knowledge gap (0.0 = full answer, 1.0 = clear gap),
        or -1.0 if not sampled
    """
    if not should_sample():
        return -1.0

    user_text = turn_data.get('user_text', '')
    assistant_text = turn_data.get('assistant_text', '')

    if not user_text or not assistant_text:
        return 0.5

    prompt = f"""Determine whether the assistant's response indicates a knowledge gap — i.e., the agent
lacked information to properly answer the customer's question.

Signs of a knowledge gap:
- Explicitly says it doesn't have information
- Gives a vague/deflecting answer that avoids the actual question
- Recommends contacting someone else without answering
- The answer is clearly off-topic or hallucinated

Customer question: {user_text}

Assistant response: {assistant_text}

Respond with ONLY a JSON object:
{{"knowledge_gap": 0.1, "reasoning": "brief explanation"}}

Where 0.0 = no gap (response fully answered), 1.0 = clear knowledge gap."""

    try:
        messages = [
            {"role": "system", "content": "You are evaluating whether AI assistants have the knowledge to answer customer questions. Be strict about gaps and deflections."},
            {"role": "user", "content": prompt}
        ]
        response_text = call_openai(messages, temperature=0.0, max_tokens=150)
        result = json.loads(response_text)
        score = float(result.get('knowledge_gap', 0.0))
        return max(0.0, min(1.0, score))

    except Exception as e:
        print(f"Error in knowledge_gap_llm: {e}")
        return 0.0


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

registry.register(MetricDefinition(
    name='intent_classification',
    display_name='Query Intent Type',
    description=(
        'Classified user intent (encoded as float index): '
        '0=product_search, 1=price_inquiry, 2=availability_check, '
        '3=how_to_use, 4=support_complaint, 5=comparison, 6=general'
    ),
    level='turn',
    stage=3,
    compute_turn=compute_intent_classification
))

registry.register(MetricDefinition(
    name='resolution_quality',
    display_name='Resolution Quality (LLM-judged)',
    description=(
        'Whether the response fully resolves the customer need — '
        'goes deeper than relevance by asking "did it actually solve the problem?" '
        '(0=unresolved, 1=fully resolved)'
    ),
    level='turn',
    stage=3,
    compute_turn=compute_resolution_quality
))

registry.register(MetricDefinition(
    name='knowledge_gap_llm',
    display_name='Knowledge Gap (LLM-judged)',
    description=(
        'LLM-detected probability that the agent lacked information to answer. '
        'More robust than regex: catches vague/deflecting responses. '
        '(0=fully answered, 1=clear gap)'
    ),
    level='turn',
    stage=3,
    compute_turn=compute_knowledge_gap_llm
))
