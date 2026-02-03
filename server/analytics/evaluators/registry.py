"""
Metrics registry for managing all available metrics.

This provides a central place to:
- Register new metrics
- Query available metrics
- Execute metric computations
"""

from typing import Dict, List, Callable, Optional
from dataclasses import dataclass


@dataclass
class MetricDefinition:
    """
    Definition of a single metric.

    Attributes:
        name: Unique identifier (e.g., 'answer_relevance')
        display_name: Human-readable name (e.g., 'Answer Relevance')
        description: What this metric measures
        level: 'turn' (per-message), 'session' (per-conversation), or 'daily' (aggregated)
        stage: 1 (rule-based), 2 (local ML), or 3 (LLM-as-judge)
        compute_turn: Function to compute turn-level metric
        reduce_session: Function to aggregate turns to session
        rollup_daily: Function to aggregate sessions to daily
    """
    name: str
    display_name: str
    description: str
    level: str  # 'turn', 'session', 'daily'
    stage: int  # 1=rule-based, 2=local-ml, 3=llm-judge

    compute_turn: Optional[Callable] = None
    reduce_session: Optional[Callable] = None
    rollup_daily: Optional[Callable] = None

    def __post_init__(self):
        """Validate metric definition"""
        if self.level not in ['turn', 'session', 'daily']:
            raise ValueError(f"Invalid level: {self.level}. Must be 'turn', 'session', or 'daily'")

        if self.stage not in [1, 2, 3]:
            raise ValueError(f"Invalid stage: {self.stage}. Must be 1, 2, or 3")


class MetricsRegistry:
    """
    Central registry for all metrics.

    Usage:
        # Register a metric
        registry.register(MetricDefinition(
            name='toxicity',
            display_name='Toxicity',
            description='Toxic content score',
            level='turn',
            stage=2,
            compute_turn=compute_toxicity_fn
        ))

        # Get a metric
        metric = registry.get('toxicity')

        # List all metrics
        all_metrics = registry.list()

        # Filter metrics
        turn_metrics = registry.list(level='turn')
        fast_metrics = registry.list(stage=1)
    """

    def __init__(self):
        self._metrics: Dict[str, MetricDefinition] = {}

    def register(self, metric: MetricDefinition):
        """
        Register a metric in the registry.

        Args:
            metric: MetricDefinition instance

        Raises:
            ValueError: If metric with same name already exists
        """
        if metric.name in self._metrics:
            raise ValueError(f"Metric '{metric.name}' is already registered")

        self._metrics[metric.name] = metric

    def get(self, name: str) -> Optional[MetricDefinition]:
        """
        Get a metric by name.

        Args:
            name: Metric name

        Returns:
            MetricDefinition or None if not found
        """
        return self._metrics.get(name)

    def list(
        self,
        level: Optional[str] = None,
        stage: Optional[int] = None
    ) -> List[MetricDefinition]:
        """
        List all metrics, optionally filtered.

        Args:
            level: Filter by level ('turn', 'session', 'daily')
            stage: Filter by stage (1, 2, 3)

        Returns:
            List of MetricDefinition instances
        """
        metrics = list(self._metrics.values())

        if level:
            metrics = [m for m in metrics if m.level == level]

        if stage:
            metrics = [m for m in metrics if m.stage == stage]

        return metrics

    def list_names(
        self,
        level: Optional[str] = None,
        stage: Optional[int] = None
    ) -> List[str]:
        """
        List metric names, optionally filtered.

        Args:
            level: Filter by level
            stage: Filter by stage

        Returns:
            List of metric names
        """
        return [m.name for m in self.list(level=level, stage=stage)]

    def clear(self):
        """Clear all registered metrics (mainly for testing)"""
        self._metrics.clear()

    def __len__(self):
        """Return number of registered metrics"""
        return len(self._metrics)

    def __contains__(self, name: str):
        """Check if metric is registered"""
        return name in self._metrics


# Global registry instance
registry = MetricsRegistry()
