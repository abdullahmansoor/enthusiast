"""
Evaluators package for computing metrics.

Three-stage evaluation pipeline:
- Stage 1: Rule-based (fast, no dependencies) - PII, language detection
- Stage 2: Local ML models (moderate, free) - toxicity, coherence
- Stage 3: LLM-as-judge (slow, costly) - relevance, faithfulness

Import these modules to register metrics:
- rule_based
- local_ml
- llm_judges
"""

from .registry import registry, MetricDefinition

__all__ = ['registry', 'MetricDefinition']
