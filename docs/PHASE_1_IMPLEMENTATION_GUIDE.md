# Phase 1 Implementation Guide
## Multi-Tenancy + Basic Agent Builder (Months 1-3)

**Last Updated:** January 20, 2026

---

## Overview

This guide provides detailed implementation steps for Phase 1 of the Agent Builder Platform. The goal is to transform the single-tenant application into a multi-tenant platform with workspace isolation and a basic visual agent builder.

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Month 1: Multi-Tenancy Foundation](#month-1-multi-tenancy-foundation)
3. [Month 2: Visual Agent Builder Backend](#month-2-visual-agent-builder-backend)
4. [Month 3: Knowledge Base & Basic Analytics](#month-3-knowledge-base--basic-analytics)
5. [Testing Strategy](#testing-strategy)
6. [Deployment Checklist](#deployment-checklist)

---

## Prerequisites

### Development Environment

```bash
# Clone and setup
cd /home/anas/other-projs/enthusiast
python -m venv venv
source venv/bin/activate
pip install -r server/requirements.txt

# Install additional dependencies for Phase 1
pip install django-guardian  # For object-level permissions
pip install django-cors-headers  # Already installed
pip install django-filter  # For advanced filtering
pip install drf-spectacular  # Better than drf-yasg
```

### Database Setup

```bash
# Ensure PostgreSQL with pgvector is running
docker-compose up -d db

# Create test database
psql -U postgres -h localhost -c "CREATE DATABASE enthusiast_test;"
```

### Feature Branch

```bash
git checkout -b feature/phase-1-multi-tenancy
```

---

## Month 1: Multi-Tenancy Foundation

### Week 1-2: Database Schema Refactor

#### Step 1: Create Workspace Models

**File:** `server/workspace/__init__.py`
```python
default_app_config = 'workspace.apps.WorkspaceConfig'
```

**File:** `server/workspace/apps.py`
```python
from django.apps import AppConfig

class WorkspaceConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'workspace'
    verbose_name = 'Workspace Management'
```

**File:** `server/workspace/models.py`
```python
import uuid
from django.db import models
from django.contrib.auth import get_user_model
from django.utils.text import slugify

User = get_user_model()


class Workspace(models.Model):
    """Multi-tenant workspace/organization"""

    # Plan choices
    PLAN_FREE = 'free'
    PLAN_PRO = 'pro'
    PLAN_ENTERPRISE = 'enterprise'

    PLAN_CHOICES = [
        (PLAN_FREE, 'Free'),
        (PLAN_PRO, 'Pro'),
        (PLAN_ENTERPRISE, 'Enterprise'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    slug = models.SlugField(unique=True, max_length=100)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Settings
    settings = models.JSONField(default=dict, blank=True)

    # Billing
    plan = models.CharField(max_length=50, choices=PLAN_CHOICES, default=PLAN_FREE)
    billing_email = models.EmailField(blank=True)

    # Quotas
    max_agents = models.IntegerField(default=3)
    max_conversations_per_month = models.IntegerField(default=1000)
    max_documents = models.IntegerField(default=100)
    max_storage_mb = models.IntegerField(default=500)

    # Stats (denormalized for performance)
    total_conversations = models.IntegerField(default=0)
    total_messages = models.IntegerField(default=0)
    current_month_conversations = models.IntegerField(default=0)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
            # Ensure uniqueness
            original_slug = self.slug
            counter = 1
            while Workspace.objects.filter(slug=self.slug).exists():
                self.slug = f"{original_slug}-{counter}"
                counter += 1
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

    class Meta:
        db_table = 'workspaces'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['slug']),
            models.Index(fields=['created_at']),
        ]


class WorkspaceMember(models.Model):
    """Workspace membership with roles"""

    ROLE_OWNER = 'owner'
    ROLE_ADMIN = 'admin'
    ROLE_MEMBER = 'member'
    ROLE_VIEWER = 'viewer'

    ROLE_CHOICES = [
        (ROLE_OWNER, 'Owner'),
        (ROLE_ADMIN, 'Admin'),
        (ROLE_MEMBER, 'Member'),
        (ROLE_VIEWER, 'Viewer'),
    ]

    workspace = models.ForeignKey(
        Workspace,
        on_delete=models.CASCADE,
        related_name='members'
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='workspace_memberships'
    )
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)

    created_at = models.DateTimeField(auto_now_add=True)
    invited_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='invited_members'
    )

    def __str__(self):
        return f"{self.user.email} - {self.workspace.name} ({self.role})"

    class Meta:
        db_table = 'workspace_members'
        unique_together = [('workspace', 'user')]
        indexes = [
            models.Index(fields=['workspace', 'role']),
            models.Index(fields=['user']),
        ]


class WorkspaceInvitation(models.Model):
    """Pending workspace invitations"""

    STATUS_PENDING = 'pending'
    STATUS_ACCEPTED = 'accepted'
    STATUS_DECLINED = 'declined'
    STATUS_EXPIRED = 'expired'

    STATUS_CHOICES = [
        (STATUS_PENDING, 'Pending'),
        (STATUS_ACCEPTED, 'Accepted'),
        (STATUS_DECLINED, 'Declined'),
        (STATUS_EXPIRED, 'Expired'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    workspace = models.ForeignKey(Workspace, on_delete=models.CASCADE)
    email = models.EmailField()
    role = models.CharField(max_length=20, choices=WorkspaceMember.ROLE_CHOICES)

    invited_by = models.ForeignKey(User, on_delete=models.CASCADE)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING)

    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    accepted_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Invite to {self.workspace.name} for {self.email}"

    class Meta:
        db_table = 'workspace_invitations'
        indexes = [
            models.Index(fields=['email', 'status']),
            models.Index(fields=['workspace', 'status']),
        ]
```

#### Step 2: Add Workspace to Existing Models

**File:** `server/agent/models/agent.py` (Update)
```python
# Add this import at the top
from workspace.models import Workspace

# Add this field to the Agent model
class Agent(models.Model):
    # Add after id field
    workspace = models.ForeignKey(
        Workspace,
        on_delete=models.CASCADE,
        related_name='agents',
        null=True  # Nullable during migration
    )

    # ... rest of the model
```

**Repeat for these models:**
- `Conversation` in `server/agent/models/conversation.py`
- `DataSet` in `server/catalog/models.py`
- Any other models that should be workspace-scoped

#### Step 3: Create Migration

```bash
cd server
python manage.py makemigrations workspace
python manage.py makemigrations agent
python manage.py makemigrations catalog

# Review migrations before running
python manage.py sqlmigrate workspace 0001
```

#### Step 4: Create Data Migration for Default Workspace

**File:** `server/workspace/migrations/0002_create_default_workspace.py`
```python
from django.db import migrations
import uuid

def create_default_workspace(apps, schema_editor):
    Workspace = apps.get_model('workspace', 'Workspace')
    User = apps.get_model('account', 'User')
    WorkspaceMember = apps.get_model('workspace', 'WorkspaceMember')

    # Create default workspace
    default_workspace = Workspace.objects.create(
        id=uuid.uuid4(),
        name='Default Workspace',
        slug='default',
        plan='free',
    )

    # Add all existing users to default workspace as owners
    for user in User.objects.all():
        WorkspaceMember.objects.create(
            workspace=default_workspace,
            user=user,
            role='owner'
        )

    # Update all existing records to use default workspace
    Agent = apps.get_model('agent', 'Agent')
    Agent.objects.filter(workspace__isnull=True).update(
        workspace=default_workspace
    )

    Conversation = apps.get_model('agent', 'Conversation')
    Conversation.objects.filter(workspace__isnull=True).update(
        workspace=default_workspace
    )

    DataSet = apps.get_model('catalog', 'DataSet')
    DataSet.objects.filter(workspace__isnull=True).update(
        workspace=default_workspace
    )

def reverse_migration(apps, schema_editor):
    pass  # Cannot reverse this migration

class Migration(migrations.Migration):
    dependencies = [
        ('workspace', '0001_initial'),
        ('agent', '0001_initial'),  # Adjust based on actual migration
        ('catalog', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(create_default_workspace, reverse_migration),
    ]
```

#### Step 5: Make Workspace Non-Nullable

After running the data migration, create another migration to make workspace required:

```bash
# Edit the model to remove null=True
# Then generate migration
python manage.py makemigrations

# This will create a migration that:
# - Sets null=False on workspace field
# - Adds database constraint
```

#### Step 6: Run Migrations

```bash
python manage.py migrate
```

### Week 3-4: Auth & Access Control

#### Step 1: Create Workspace Middleware

**File:** `server/workspace/middleware.py`
```python
from django.utils.deprecation import MiddlewareMixin
from django.http import JsonResponse
from workspace.models import WorkspaceMember

class WorkspaceMiddleware(MiddlewareMixin):
    """
    Inject workspace context into request based on:
    1. X-Workspace-ID header
    2. workspace_id query parameter
    3. Default workspace for user
    """

    def process_request(self, request):
        if not request.user.is_authenticated:
            request.workspace = None
            return None

        # Try to get workspace from header
        workspace_id = request.headers.get('X-Workspace-ID')

        # Try query parameter if header not present
        if not workspace_id:
            workspace_id = request.GET.get('workspace_id')

        if workspace_id:
            try:
                membership = WorkspaceMember.objects.select_related('workspace').get(
                    workspace_id=workspace_id,
                    user=request.user
                )
                request.workspace = membership.workspace
                request.workspace_role = membership.role
            except WorkspaceMember.DoesNotExist:
                return JsonResponse(
                    {'error': 'Workspace not found or access denied'},
                    status=403
                )
        else:
            # Get user's default workspace (most recently used or first one)
            membership = WorkspaceMember.objects.select_related('workspace').filter(
                user=request.user
            ).first()

            if membership:
                request.workspace = membership.workspace
                request.workspace_role = membership.role
            else:
                request.workspace = None
                request.workspace_role = None

        return None
```

#### Step 2: Create Permission Utilities

**File:** `server/workspace/permissions.py`
```python
from rest_framework import permissions
from workspace.models import WorkspaceMember

class WorkspacePermission(permissions.BasePermission):
    """Base permission for workspace-scoped resources"""

    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False

        if not hasattr(request, 'workspace') or not request.workspace:
            return False

        return True


class IsWorkspaceMember(WorkspacePermission):
    """User must be a member of the workspace"""
    pass


class IsWorkspaceAdmin(WorkspacePermission):
    """User must be admin or owner"""

    def has_permission(self, request, view):
        if not super().has_permission(request, view):
            return False

        return request.workspace_role in [
            WorkspaceMember.ROLE_OWNER,
            WorkspaceMember.ROLE_ADMIN
        ]


class IsWorkspaceOwner(WorkspacePermission):
    """User must be workspace owner"""

    def has_permission(self, request, view):
        if not super().has_permission(request, view):
            return False

        return request.workspace_role == WorkspaceMember.ROLE_OWNER


class CanModifyResource(WorkspacePermission):
    """User can modify resources (not viewer)"""

    def has_permission(self, request, view):
        if not super().has_permission(request, view):
            return False

        # Viewers can only read
        if request.method in permissions.SAFE_METHODS:
            return True

        return request.workspace_role != WorkspaceMember.ROLE_VIEWER


def check_workspace_quota(workspace, resource_type):
    """
    Check if workspace has capacity for new resource

    Args:
        workspace: Workspace instance
        resource_type: 'agents', 'conversations', 'documents'

    Returns:
        tuple: (bool, str) - (has_capacity, error_message)
    """
    if resource_type == 'agents':
        current = workspace.agents.filter(deleted_at__isnull=True).count()
        max_allowed = workspace.max_agents
        resource_name = 'agents'

    elif resource_type == 'conversations':
        from django.utils import timezone
        from datetime import datetime

        # Check current month only
        now = timezone.now()
        start_of_month = datetime(now.year, now.month, 1, tzinfo=now.tzinfo)
        current = workspace.conversations.filter(
            created_at__gte=start_of_month
        ).count()
        max_allowed = workspace.max_conversations_per_month
        resource_name = 'conversations this month'

    elif resource_type == 'documents':
        current = workspace.datasets.aggregate(
            total=models.Count('documents')
        )['total'] or 0
        max_allowed = workspace.max_documents
        resource_name = 'documents'

    else:
        return True, None

    if current >= max_allowed:
        return False, f"Workspace limit reached: {current}/{max_allowed} {resource_name}"

    return True, None
```

#### Step 3: Update Settings

**File:** `server/pecl/settings.py` (Add middleware)
```python
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'workspace.middleware.WorkspaceMiddleware',  # ADD THIS
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

INSTALLED_APPS = [
    # ... existing apps
    'workspace',  # ADD THIS
]
```

#### Step 4: Update Views with Workspace Filtering

**File:** `server/agent/views.py` (Example update)
```python
from workspace.permissions import IsWorkspaceMember, CanModifyResource
from workspace.permissions import check_workspace_quota

class AgentViewSet(viewsets.ModelViewSet):
    serializer_class = AgentSerializer
    permission_classes = [IsAuthenticated, IsWorkspaceMember, CanModifyResource]

    def get_queryset(self):
        # Filter by workspace from middleware
        return Agent.objects.filter(
            workspace=self.request.workspace,
            deleted_at__isnull=True
        )

    def perform_create(self, serializer):
        # Check quota
        has_capacity, error = check_workspace_quota(
            self.request.workspace,
            'agents'
        )
        if not has_capacity:
            raise ValidationError(error)

        # Save with workspace
        serializer.save(
            workspace=self.request.workspace,
            created_by=self.request.user
        )
```

**Repeat this pattern for all ViewSets:**
- ConversationViewSet
- DataSetViewSet
- DocumentViewSet
- ProductViewSet

#### Step 5: Create Workspace API Endpoints

**File:** `server/workspace/serializers.py`
```python
from rest_framework import serializers
from workspace.models import Workspace, WorkspaceMember, WorkspaceInvitation
from account.models import User

class WorkspaceSerializer(serializers.ModelSerializer):
    member_count = serializers.SerializerMethodField()
    agent_count = serializers.SerializerMethodField()
    my_role = serializers.SerializerMethodField()

    class Meta:
        model = Workspace
        fields = [
            'id', 'name', 'slug', 'plan', 'created_at', 'updated_at',
            'max_agents', 'max_conversations_per_month', 'max_documents',
            'total_conversations', 'total_messages', 'current_month_conversations',
            'member_count', 'agent_count', 'my_role'
        ]
        read_only_fields = ['id', 'slug', 'created_at', 'updated_at',
                            'total_conversations', 'total_messages']

    def get_member_count(self, obj):
        return obj.members.count()

    def get_agent_count(self, obj):
        return obj.agents.filter(deleted_at__isnull=True).count()

    def get_my_role(self, obj):
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return None

        try:
            membership = WorkspaceMember.objects.get(
                workspace=obj,
                user=request.user
            )
            return membership.role
        except WorkspaceMember.DoesNotExist:
            return None


class WorkspaceMemberSerializer(serializers.ModelSerializer):
    user_email = serializers.EmailField(source='user.email', read_only=True)
    user_name = serializers.SerializerMethodField()
    invited_by_email = serializers.EmailField(source='invited_by.email', read_only=True)

    class Meta:
        model = WorkspaceMember
        fields = [
            'id', 'user', 'user_email', 'user_name', 'role',
            'created_at', 'invited_by', 'invited_by_email'
        ]
        read_only_fields = ['id', 'created_at']

    def get_user_name(self, obj):
        return f"{obj.user.first_name} {obj.user.last_name}".strip() or obj.user.email


class WorkspaceInvitationSerializer(serializers.ModelSerializer):
    invited_by_email = serializers.EmailField(source='invited_by.email', read_only=True)
    workspace_name = serializers.CharField(source='workspace.name', read_only=True)

    class Meta:
        model = WorkspaceInvitation
        fields = [
            'id', 'workspace', 'workspace_name', 'email', 'role',
            'status', 'created_at', 'expires_at', 'invited_by', 'invited_by_email'
        ]
        read_only_fields = ['id', 'status', 'created_at', 'invited_by']
```

**File:** `server/workspace/views.py`
```python
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from datetime import timedelta

from workspace.models import Workspace, WorkspaceMember, WorkspaceInvitation
from workspace.serializers import (
    WorkspaceSerializer,
    WorkspaceMemberSerializer,
    WorkspaceInvitationSerializer
)
from workspace.permissions import IsWorkspaceAdmin, IsWorkspaceOwner


class WorkspaceViewSet(viewsets.ModelViewSet):
    serializer_class = WorkspaceSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        # Return workspaces where user is a member
        return Workspace.objects.filter(
            members__user=self.request.user
        ).distinct()

    def perform_create(self, serializer):
        workspace = serializer.save()

        # Add creator as owner
        WorkspaceMember.objects.create(
            workspace=workspace,
            user=self.request.user,
            role=WorkspaceMember.ROLE_OWNER
        )

    @action(detail=True, methods=['get'])
    def usage(self, request, pk=None):
        """Get workspace usage statistics"""
        workspace = self.get_object()

        # Calculate storage used
        from django.db.models import Sum
        storage_used = workspace.datasets.aggregate(
            total=Sum('documents__file_size')
        )['total'] or 0
        storage_used_mb = storage_used / (1024 * 1024)

        return Response({
            'agents': {
                'current': workspace.agents.filter(deleted_at__isnull=True).count(),
                'max': workspace.max_agents,
                'percentage': workspace.agents.filter(deleted_at__isnull=True).count() / workspace.max_agents * 100
            },
            'conversations': {
                'current': workspace.current_month_conversations,
                'max': workspace.max_conversations_per_month,
                'percentage': workspace.current_month_conversations / workspace.max_conversations_per_month * 100
            },
            'documents': {
                'current': workspace.datasets.aggregate(total=models.Count('documents'))['total'] or 0,
                'max': workspace.max_documents,
            },
            'storage': {
                'current_mb': round(storage_used_mb, 2),
                'max_mb': workspace.max_storage_mb,
                'percentage': storage_used_mb / workspace.max_storage_mb * 100
            }
        })

    @action(detail=True, methods=['get'])
    def members(self, request, pk=None):
        """List workspace members"""
        workspace = self.get_object()
        members = workspace.members.all()
        serializer = WorkspaceMemberSerializer(members, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated, IsWorkspaceAdmin])
    def invite(self, request, pk=None):
        """Invite a user to workspace"""
        workspace = self.get_object()
        email = request.data.get('email')
        role = request.data.get('role', WorkspaceMember.ROLE_MEMBER)

        if not email:
            return Response(
                {'error': 'Email is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Check if user already exists
        try:
            user = User.objects.get(email=email)
            # Check if already a member
            if WorkspaceMember.objects.filter(workspace=workspace, user=user).exists():
                return Response(
                    {'error': 'User is already a member'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        except User.DoesNotExist:
            user = None

        # Create invitation
        invitation = WorkspaceInvitation.objects.create(
            workspace=workspace,
            email=email,
            role=role,
            invited_by=request.user,
            expires_at=timezone.now() + timedelta(days=7)
        )

        # TODO: Send invitation email

        serializer = WorkspaceInvitationSerializer(invitation)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['patch'], permission_classes=[IsAuthenticated, IsWorkspaceAdmin])
    def update_member(self, request, pk=None):
        """Update member role"""
        workspace = self.get_object()
        user_id = request.data.get('user_id')
        new_role = request.data.get('role')

        try:
            member = WorkspaceMember.objects.get(
                workspace=workspace,
                user_id=user_id
            )

            # Cannot change owner role
            if member.role == WorkspaceMember.ROLE_OWNER:
                return Response(
                    {'error': 'Cannot modify owner role'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            member.role = new_role
            member.save()

            serializer = WorkspaceMemberSerializer(member)
            return Response(serializer.data)

        except WorkspaceMember.DoesNotExist:
            return Response(
                {'error': 'Member not found'},
                status=status.HTTP_404_NOT_FOUND
            )

    @action(detail=True, methods=['delete'], permission_classes=[IsAuthenticated, IsWorkspaceAdmin])
    def remove_member(self, request, pk=None):
        """Remove member from workspace"""
        workspace = self.get_object()
        user_id = request.data.get('user_id')

        try:
            member = WorkspaceMember.objects.get(
                workspace=workspace,
                user_id=user_id
            )

            # Cannot remove owner
            if member.role == WorkspaceMember.ROLE_OWNER:
                return Response(
                    {'error': 'Cannot remove workspace owner'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            member.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)

        except WorkspaceMember.DoesNotExist:
            return Response(
                {'error': 'Member not found'},
                status=status.HTTP_404_NOT_FOUND
            )
```

**File:** `server/workspace/urls.py`
```python
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from workspace.views import WorkspaceViewSet

router = DefaultRouter()
router.register(r'workspaces', WorkspaceViewSet, basename='workspace')

urlpatterns = [
    path('', include(router.urls)),
]
```

**File:** `server/pecl/urls.py` (Update)
```python
urlpatterns = [
    # ... existing patterns
    path('api/', include('workspace.urls')),
]
```

### Testing Multi-Tenancy

**File:** `server/workspace/tests.py`
```python
from django.test import TestCase
from django.contrib.auth import get_user_model
from workspace.models import Workspace, WorkspaceMember

User = get_user_model()

class WorkspaceTestCase(TestCase):
    def setUp(self):
        self.user1 = User.objects.create_user(
            email='user1@test.com',
            password='testpass123'
        )
        self.user2 = User.objects.create_user(
            email='user2@test.com',
            password='testpass123'
        )

    def test_create_workspace(self):
        """Test workspace creation"""
        workspace = Workspace.objects.create(
            name='Test Workspace',
            plan='free'
        )
        self.assertEqual(workspace.slug, 'test-workspace')
        self.assertEqual(workspace.max_agents, 3)

    def test_add_member(self):
        """Test adding member to workspace"""
        workspace = Workspace.objects.create(name='Test')

        WorkspaceMember.objects.create(
            workspace=workspace,
            user=self.user1,
            role=WorkspaceMember.ROLE_OWNER
        )

        self.assertEqual(workspace.members.count(), 1)
        self.assertTrue(
            WorkspaceMember.objects.filter(
                workspace=workspace,
                user=self.user1,
                role=WorkspaceMember.ROLE_OWNER
            ).exists()
        )

    def test_workspace_isolation(self):
        """Test that users can only see their workspaces"""
        workspace1 = Workspace.objects.create(name='Workspace 1')
        workspace2 = Workspace.objects.create(name='Workspace 2')

        WorkspaceMember.objects.create(
            workspace=workspace1,
            user=self.user1,
            role=WorkspaceMember.ROLE_OWNER
        )

        WorkspaceMember.objects.create(
            workspace=workspace2,
            user=self.user2,
            role=WorkspaceMember.ROLE_OWNER
        )

        # User 1 should only see workspace 1
        user1_workspaces = Workspace.objects.filter(
            members__user=self.user1
        )
        self.assertEqual(user1_workspaces.count(), 1)
        self.assertEqual(user1_workspaces.first().id, workspace1.id)
```

Run tests:
```bash
python manage.py test workspace
```

---

## Month 2: Visual Agent Builder Backend

### Week 1-2: Agent Configuration Models

#### Step 1: Update Agent Model for Flexible Config

**File:** `server/agent/models/agent.py` (Enhanced version)
```python
import uuid
from django.db import models
from django.contrib.auth import get_user_model
from workspace.models import Workspace

User = get_user_model()

class Agent(models.Model):
    """Enhanced agent model with flexible JSON configuration"""

    STATUS_DRAFT = 'draft'
    STATUS_ACTIVE = 'active'
    STATUS_ARCHIVED = 'archived'

    STATUS_CHOICES = [
        (STATUS_DRAFT, 'Draft'),
        (STATUS_ACTIVE, 'Active'),
        (STATUS_ARCHIVED, 'Archived'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    workspace = models.ForeignKey(
        Workspace,
        on_delete=models.CASCADE,
        related_name='agents'
    )

    # Basic info
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    avatar_url = models.URLField(blank=True)

    # Configuration (flexible JSON)
    config = models.JSONField(default=dict)
    # Default config structure defined in get_default_config()

    # Versioning
    version = models.IntegerField(default=1)
    parent_version = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='child_versions'
    )
    is_active = models.BooleanField(default=True)

    # Lifecycle
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_DRAFT
    )
    published_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_agents'
    )

    # Analytics (denormalized)
    total_conversations = models.IntegerField(default=0)
    avg_rating = models.FloatField(null=True, blank=True)

    @staticmethod
    def get_default_config():
        """Return default agent configuration"""
        return {
            "model": {
                "provider": "openai",
                "name": "gpt-4",
                "temperature": 0.7,
                "max_tokens": 2000,
                "top_p": 1.0
            },
            "system_prompt": "You are a helpful AI assistant.",
            "personality": {
                "tone": "professional",
                "formality": "neutral",
                "verbosity": "balanced"
            },
            "tools": [],
            "memory": {
                "type": "summary",
                "max_tokens": 2000
            },
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
        # Ensure config has default structure
        if not self.config:
            self.config = self.get_default_config()
        else:
            # Merge with defaults for missing keys
            default = self.get_default_config()
            for key in default:
                if key not in self.config:
                    self.config[key] = default[key]

        super().save(*args, **kwargs)

    def create_version(self, user):
        """Create a new version of this agent"""
        new_agent = Agent.objects.create(
            workspace=self.workspace,
            name=self.name,
            description=self.description,
            avatar_url=self.avatar_url,
            config=self.config.copy(),
            version=self.version + 1,
            parent_version=self,
            status=Agent.STATUS_DRAFT,
            created_by=user
        )
        return new_agent

    def __str__(self):
        return f"{self.name} (v{self.version})"

    class Meta:
        db_table = 'agents'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['workspace', 'status']),
            models.Index(fields=['workspace', 'is_active']),
            models.Index(fields=['deleted_at']),
        ]
```

#### Step 2: Create Agent Template Model

**File:** `server/agent/models/template.py`
```python
import uuid
from django.db import models
from django.contrib.postgres.fields import ArrayField
from django.contrib.auth import get_user_model

User = get_user_model()

class AgentTemplate(models.Model):
    """Reusable agent templates"""

    CATEGORY_CUSTOMER_SUPPORT = 'customer_support'
    CATEGORY_SALES = 'sales'
    CATEGORY_EDUCATION = 'education'
    CATEGORY_HEALTH = 'health'
    CATEGORY_FINANCE = 'finance'
    CATEGORY_GENERAL = 'general'

    CATEGORY_CHOICES = [
        (CATEGORY_CUSTOMER_SUPPORT, 'Customer Support'),
        (CATEGORY_SALES, 'Sales & Marketing'),
        (CATEGORY_EDUCATION, 'Education & Training'),
        (CATEGORY_HEALTH, 'Healthcare'),
        (CATEGORY_FINANCE, 'Finance & Banking'),
        (CATEGORY_GENERAL, 'General Purpose'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    name = models.CharField(max_length=255)
    description = models.TextField()
    category = models.CharField(max_length=100, choices=CATEGORY_CHOICES)
    tags = ArrayField(
        models.CharField(max_length=50),
        default=list,
        blank=True
    )

    # Template configuration
    config = models.JSONField()

    # Metadata
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_templates'
    )
    is_public = models.BooleanField(default=False)
    is_featured = models.BooleanField(default=False)

    # Stats
    clone_count = models.IntegerField(default=0)
    avg_rating = models.FloatField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    class Meta:
        db_table = 'agent_templates'
        ordering = ['-is_featured', '-clone_count', '-created_at']
        indexes = [
            models.Index(fields=['category', 'is_public']),
            models.Index(fields=['is_featured', 'is_public']),
        ]
```

This is getting quite long. Would you like me to continue with the rest of Month 2 and Month 3, or would you prefer I create additional separate documents for:
- Frontend implementation guide
- Analytics migration guide
- API documentation with examples

Let me know how you'd like me to proceed!
