import uuid
from django.db import models
from django.utils import timezone
from django.contrib.auth import get_user_model

from catalog.models import DataSet

User = get_user_model()


class AgentQuerySet(models.QuerySet):
    def active(self):
        return self.filter(deleted_at__isnull=True)


class AgentManager(models.Manager):
    def get_queryset(self):
        return AgentQuerySet(self.model, using=self._db).active()


class Agent(models.Model):
    """
    Enhanced Agent model with flexible JSON configuration for MVP.

    The config field contains all agent behavior settings:
    - model: LLM provider and parameters
    - system_prompt: Instructions for the agent
    - retrieval: RAG configuration
    - conversation_starters: Pre-defined prompts
    - constraints: Limits and guardrails
    """

    STATUS_DRAFT = 'draft'
    STATUS_ACTIVE = 'active'
    STATUS_ARCHIVED = 'archived'

    STATUS_CHOICES = [
        (STATUS_DRAFT, 'Draft'),
        (STATUS_ACTIVE, 'Active'),
        (STATUS_ARCHIVED, 'Archived'),
    ]

    # Primary key
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # Basic info
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    avatar_url = models.URLField(blank=True, max_length=500)

    # Legacy field - keeping for backward compatibility
    agent_type = models.CharField(max_length=255, blank=True, default='tool_calling')

    # Configuration (flexible JSON)
    config = models.JSONField(default=dict, blank=True)

    # Relationships
    dataset = models.ForeignKey(
        DataSet,
        on_delete=models.CASCADE,
        related_name="agents"
    )
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_agents'
    )

    # Versioning & Status
    version = models.IntegerField(default=1)
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_DRAFT
    )

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    published_at = models.DateTimeField(null=True, blank=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    # Analytics (denormalized for performance)
    total_conversations = models.IntegerField(default=0)
    avg_rating = models.FloatField(null=True, blank=True)

    # Legacy field - keeping for backward compatibility
    corrupted = models.BooleanField(default=False)

    # Managers
    objects = AgentManager()
    all_objects = models.Manager()

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["dataset", "name"],
                name="unique_agent_name_per_dataset"
            )
        ]
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', 'deleted_at']),
            models.Index(fields=['created_at']),
            models.Index(fields=['dataset', 'status']),
        ]

    def __str__(self):
        return f"{self.name} (v{self.version})"

    def set_deleted_at(self):
        """Soft delete the agent"""
        self.deleted_at = timezone.now()
        self.status = self.STATUS_ARCHIVED
        self.save()

    @staticmethod
    def get_default_config():
        """
        Return default agent configuration structure.
        This ensures all new agents have a complete config.
        """
        return {
            "model": {
                "provider": "openai",
                "name": "gpt-4",
                "temperature": 0.7,
                "max_tokens": 2000,
                "top_p": 1.0
            },
            "system_prompt": "You are a helpful AI assistant. Answer questions accurately and concisely based on the provided context.",
            "retrieval": {
                "enabled": True,
                "top_k": 5,
                "score_threshold": 0.7
            },
            "conversation_starters": [
                "How can I help you today?",
                "What would you like to know?"
            ],
            "constraints": {
                "max_conversation_length": 50,
                "max_response_tokens": 1000,
                "response_timeout_seconds": 30
            }
        }

    def save(self, *args, **kwargs):
        """
        Override save to ensure config has default structure.
        Merges user config with defaults to prevent missing keys.
        """
        if not self.config:
            self.config = self.get_default_config()
        else:
            # Merge with defaults for missing keys
            default = self.get_default_config()
            for key in default:
                if key not in self.config:
                    self.config[key] = default[key]
                elif isinstance(default[key], dict) and isinstance(self.config[key], dict):
                    # Merge nested dicts
                    for nested_key in default[key]:
                        if nested_key not in self.config[key]:
                            self.config[key][nested_key] = default[key][nested_key]

        super().save(*args, **kwargs)

    def publish(self):
        """Publish the agent (make it active)"""
        self.status = self.STATUS_ACTIVE
        self.published_at = timezone.now()
        self.save()

    def archive(self):
        """Archive the agent"""
        self.status = self.STATUS_ARCHIVED
        self.save()
