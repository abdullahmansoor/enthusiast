# Agent Builder Platform - Complete Roadmap

**Last Updated:** January 20, 2026
**Version:** 1.0
**Status:** Planning Phase

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Platform Vision & Goals](#platform-vision--goals)
3. [Current State Analysis](#current-state-analysis)
4. [Target Architecture](#target-architecture)
5. [Feature Breakdown](#feature-breakdown)
6. [Implementation Phases](#implementation-phases)
7. [Technical Specifications](#technical-specifications)
8. [Database Schema Changes](#database-schema-changes)
9. [API Endpoints](#api-endpoints)
10. [Analytics Integration](#analytics-integration)
11. [Frontend Requirements](#frontend-requirements)
12. [Security & Access Control](#security--access-control)
13. [Deployment Strategy](#deployment-strategy)
14. [Cost Estimation](#cost-estimation)
15. [Success Metrics](#success-metrics)

---

## Executive Summary

Transform the current enthusiast e-commerce AI framework into a **multi-tenant agent builder platform** where users can:
- Create and configure custom AI agents without coding
- Upload and manage their own documents and knowledge bases
- Customize agent prompts, behavior, and tools
- Monitor agent performance through comprehensive analytics dashboards
- Deploy agents via API or embedded chat widgets
- A/B test different agent configurations

**Key Differentiators:**
- No-code agent builder with visual configuration
- RAG-powered agents with custom document ingestion
- Production-grade analytics (35+ metrics)
- Multi-tenant isolation and resource management
- Plugin marketplace for extensions

---

## Platform Vision & Goals

### Vision Statement
"Empower businesses to build, deploy, and optimize custom AI agents that understand their unique context and deliver measurable business value."

### Primary Goals
1. **Democratize AI Agent Creation** - Non-technical users can build sophisticated agents
2. **Provide Deep Insights** - Comprehensive analytics on agent performance and user interactions
3. **Ensure Production Readiness** - Scalable, secure, and reliable infrastructure
4. **Enable Customization** - Flexible configuration for diverse use cases
5. **Drive Business Outcomes** - Focus on metrics that matter (containment, conversion, satisfaction)

### Target Users
- **SaaS Companies** - Customer support automation
- **E-commerce Businesses** - Product recommendations and sales assistance
- **Marketing Teams** - Lead qualification and engagement
- **Healthcare Providers** - Patient triage and information
- **Educational Institutions** - Student support and tutoring

---

## Current State Analysis

### What We Have (Enthusiast Repository)

**Strengths:**
- ✅ Production-ready Django backend with REST API
- ✅ LangChain-based agent architecture with tool calling
- ✅ RAG implementation with pgvector (document + product retrieval)
- ✅ Plugin system for extensibility (models, sources, tools)
- ✅ WebSocket streaming for real-time responses
- ✅ Celery for background task processing
- ✅ User authentication and basic access control
- ✅ Multi-agent support (agent types configured in settings)
- ✅ Document and product management APIs
- ✅ File upload support (PDF, images, text)
- ✅ Conversation history and memory management

**Gaps:**
- ❌ Single-tenant design (no workspace/organization concept)
- ❌ No visual agent builder UI
- ❌ Limited agent customization (mostly code-level)
- ❌ No analytics or performance tracking
- ❌ No usage quotas or billing
- ❌ No agent deployment/embedding tools
- ❌ No A/B testing framework
- ❌ No agent versioning or rollback
- ❌ Limited access control (no role-based permissions)
- ❌ No marketplace or sharing capabilities

### What We Have (Chat-Verifier Dashboard)

**Strengths:**
- ✅ Comprehensive analytics (35+ metrics)
- ✅ Three-tier metrics architecture (turn → session → daily → weekly)
- ✅ Multi-stage evaluation pipeline (rule-based → local ML → LLM judges)
- ✅ Rich dashboard APIs with filtering and aggregation
- ✅ A/B testing and cohort analysis
- ✅ Real-time alerting on threshold violations
- ✅ Celery-based data ingestion and processing
- ✅ Redis caching for performance
- ✅ Outlier detection and drill-down capabilities

**Gaps:**
- ❌ Designed for external API integration (not embedded)
- ❌ Separate codebase (needs integration)
- ❌ Different database schema
- ❌ No real-time metrics (batch processing only)
- ❌ Limited customization of metrics

---

## Target Architecture

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Frontend Layer                           │
│  ┌───────────────┐  ┌───────────────┐  ┌──────────────┐   │
│  │ Agent Builder │  │   Analytics   │  │ Admin Portal │   │
│  │   Interface   │  │   Dashboard   │  │              │   │
│  └───────────────┘  └───────────────┘  └──────────────┘   │
└─────────────────────────────────────────────────────────────┘
                            ↕ REST API
┌─────────────────────────────────────────────────────────────┐
│                     API Gateway Layer                        │
│  ┌────────────┐  ┌────────────┐  ┌────────────────────┐   │
│  │ Auth & ACL │  │Rate Limit  │  │ Multi-tenant       │   │
│  │            │  │            │  │ Context Injection  │   │
│  └────────────┘  └────────────┘  └────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                            ↕
┌─────────────────────────────────────────────────────────────┐
│                   Application Layer                          │
│  ┌─────────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │ Agent Builder   │  │   Analytics  │  │  Workspace   │  │
│  │    Service      │  │   Service    │  │   Service    │  │
│  └─────────────────┘  └──────────────┘  └──────────────┘  │
│  ┌─────────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │ Conversation    │  │   Embedding  │  │   Billing    │  │
│  │    Manager      │  │   Service    │  │   Service    │  │
│  └─────────────────┘  └──────────────┘  └──────────────┘  │
└─────────────────────────────────────────────────────────────┘
                            ↕
┌─────────────────────────────────────────────────────────────┐
│                      Agent Runtime                           │
│  ┌─────────────────────────────────────────────────────┐   │
│  │           Agent Execution Engine (LangChain)        │   │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────────────┐  │   │
│  │  │ Tools    │  │ Retrievers│  │ Memory Manager   │  │   │
│  │  └──────────┘  └──────────┘  └──────────────────┘  │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                            ↕
┌─────────────────────────────────────────────────────────────┐
│                    Background Jobs (Celery)                  │
│  ┌──────────────┐  ┌───────────────┐  ┌───────────────┐   │
│  │  Embeddings  │  │   Metrics     │  │  Evaluations  │   │
│  │  Generation  │  │   Rollup      │  │   Pipeline    │   │
│  └──────────────┘  └───────────────┘  └───────────────┘   │
└─────────────────────────────────────────────────────────────┘
                            ↕
┌─────────────────────────────────────────────────────────────┐
│                      Data Layer                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐ │
│  │  PostgreSQL  │  │    Redis     │  │   Object Store   │ │
│  │  + pgvector  │  │   (Cache +   │  │   (Files, Logs)  │ │
│  │              │  │   Broker)    │  │                  │ │
│  └──────────────┘  └──────────────┘  └──────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

### Key Architectural Decisions

1. **Multi-Tenancy Strategy: Database-Level Isolation**
   - Single database with `workspace_id` foreign keys
   - Row-level security policies for data isolation
   - Shared infrastructure for cost efficiency
   - Consider separate databases for enterprise tier

2. **Analytics Architecture: Embedded + Real-time**
   - Integrate analytics directly into Django app (not separate service)
   - Real-time metrics via streaming (WebSocket)
   - Batch rollups for historical analysis (Celery)
   - Separate read replicas for analytics queries

3. **Agent Configuration: JSON-Based with UI Builder**
   - Store agent config as structured JSON in database
   - UI builder generates/validates JSON
   - Version control with rollback support
   - Export/import for sharing templates

4. **LLM Provider Strategy: Multi-Provider Support**
   - Abstract provider interface (existing plugin system)
   - Allow per-workspace provider selection
   - Support BYO API keys (Bring Your Own)
   - Fallback/retry across providers

5. **Scalability Approach: Horizontal + Queue-Based**
   - Stateless API servers (scale horizontally)
   - Celery workers for agent execution (scale per load)
   - Redis pub/sub for WebSocket distribution
   - CDN for static assets and chat widgets

---

## Feature Breakdown

### Phase 1: Foundation (Multi-Tenancy + Basic Builder)

#### 1.1 Workspace Management
- **Workspaces (Organizations)**
  - Create/manage workspaces
  - Invite team members
  - Role-based access control (Owner, Admin, Member, Viewer)
  - Workspace settings (branding, default models, quotas)

#### 1.2 Visual Agent Builder
- **Agent Configuration UI**
  - Agent name, description, avatar
  - System prompt editor with variables
  - Model selection (GPT-4, GPT-3.5, Claude, etc.)
  - Temperature and generation parameters
  - Conversation starter prompts
  - Personality traits (tone, style, formality)

#### 1.3 Knowledge Base Management
- **Document Upload & Processing**
  - Drag-and-drop file upload
  - Support formats: PDF, DOCX, TXT, MD, CSV
  - Automatic chunking and embedding
  - Document preview and metadata editing
  - Organize into collections/folders
  - Sync from external sources (Google Drive, Notion, Confluence)

#### 1.4 Basic Analytics
- **Core Metrics Dashboard**
  - Total conversations
  - Total messages
  - Average conversation length
  - Response time (avg, P50, P95)
  - User satisfaction (thumbs up/down)
  - Active users

### Phase 2: Advanced Agent Features

#### 2.1 Tool Configuration
- **Built-in Tools**
  - Web search (Google, Bing)
  - API caller (custom REST APIs)
  - Database query (SQL, vector search)
  - Calculator
  - Date/time utilities

- **Custom Tool Builder**
  - No-code API integration wizard
  - Request/response mapping
  - Authentication configuration (API key, OAuth)
  - Test playground

#### 2.2 Conversation Flow Designer
- **Visual Flow Builder**
  - Drag-and-drop node editor
  - Conditional branches (if/else)
  - Human handoff triggers
  - Form collection nodes
  - Integration nodes (CRM, ticketing)

#### 2.3 Memory & Context Management
- **Configurable Memory**
  - Short-term memory (conversation history)
  - Long-term memory (user profiles, preferences)
  - Memory summarization strategies
  - Context window management
  - User segmentation

#### 2.4 Multi-Channel Deployment
- **Deployment Options**
  - Embeddable chat widget (JavaScript SDK)
  - REST API access
  - WhatsApp integration
  - Slack bot
  - Discord bot
  - Microsoft Teams
  - Telegram

### Phase 3: Production-Grade Analytics

#### 3.1 Quality Metrics
- Answer relevance (LLM-as-judge)
- Coherence scoring
- Repetition detection
- Memory usage effectiveness
- Style consistency
- Composite quality score

#### 3.2 Faithfulness & Safety
- Faithfulness to source documents
- Hallucination detection
- Toxicity scoring
- PII detection and masking
- Content moderation

#### 3.3 Performance Metrics
- Time to first token (TTFT)
- Token generation rate
- End-to-end latency percentiles
- Cost per conversation
- Token usage tracking
- Error rates and types

#### 3.4 Business Metrics
- Containment rate (no human handoff)
- Conversion rate (goal completion)
- Drop-off rate
- User satisfaction (CSAT)
- Net Promoter Score (NPS)
- Funnel analysis

#### 3.5 Advanced Analytics Features
- **Real-time Dashboard**
  - Live conversation monitoring
  - Active users count
  - Response time tracking
  - Alert notifications

- **Historical Analysis**
  - Time series charts (hourly, daily, weekly, monthly)
  - Cohort analysis (by date, model, prompt version)
  - Distribution histograms
  - Percentile tracking

- **Drill-Down Capabilities**
  - Click on any metric to see underlying conversations
  - Filter by date range, agent, user, outcome
  - Session replay with turn-by-turn breakdown
  - Highlighted issues (low scores, errors, long latency)

- **A/B Testing Framework**
  - Compare agent versions side-by-side
  - Statistical significance testing
  - Traffic splitting (10%, 50%, 90%)
  - Automatic winner promotion

### Phase 4: Optimization & Scale

#### 4.1 Agent Versioning & Testing
- Version control for agent configurations
- Test playground with sample conversations
- Regression testing suite
- Gradual rollout (canary deployments)
- Rollback to previous versions

#### 4.2 Prompt Optimization
- Prompt template library
- Variable injection and testing
- A/B testing for prompts
- LLM-powered prompt improvement suggestions
- Few-shot example management

#### 4.3 Cost Optimization
- Model selection recommendations
- Context pruning strategies
- Caching for repeated queries
- Streaming vs batch trade-offs
- Custom fine-tuned models

#### 4.4 Collaboration & Sharing
- Agent templates marketplace
- Share agents across workspaces
- Public agent directory
- Comment and review system
- Clone and customize templates

### Phase 5: Enterprise Features

#### 5.1 Advanced Security
- SSO integration (SAML, OAuth)
- IP whitelisting
- Audit logs
- Data retention policies
- Encryption at rest and in transit
- Compliance certifications (SOC 2, GDPR, HIPAA)

#### 5.2 Custom Deployments
- On-premises deployment option
- VPC/private cloud hosting
- Dedicated database instances
- Custom domain and SSL
- White-label branding

#### 5.3 Advanced Integrations
- CRM integrations (Salesforce, HubSpot)
- Ticketing systems (Zendesk, Intercom)
- Analytics platforms (Google Analytics, Mixpanel)
- Data warehouses (Snowflake, BigQuery)
- Webhook automation

#### 5.4 Enterprise Support
- Priority support channel
- Dedicated success manager
- Custom SLA agreements
- Training and onboarding
- Regular business reviews

---

## Implementation Phases

### Phase 1: Foundation (Months 1-3)

**Goal:** Transform single-tenant app to multi-tenant platform with basic agent builder

#### Month 1: Multi-Tenancy Foundation
**Week 1-2: Database Schema Refactor**
- Create Workspace model
- Add workspace_id to all existing models
- Implement row-level security policies
- Data migration scripts
- Update all queries with workspace filtering

**Week 3-4: Auth & Access Control**
- Implement workspace membership
- Role-based permissions (Owner, Admin, Member, Viewer)
- Workspace invitation system
- Switch workspace functionality
- Update API authentication middleware

#### Month 2: Visual Agent Builder (Backend)
**Week 1-2: Agent Configuration Models**
- Flexible JSON-based agent config schema
- Agent versioning model
- Agent template model
- Config validation and defaults
- Migration from code-based config

**Week 3-4: Agent Builder APIs**
- CRUD endpoints for agents
- Agent configuration validation
- Agent duplication/cloning
- Agent version management
- Test agent endpoint (dry-run)

#### Month 3: Knowledge Base Enhancement
**Week 1-2: Document Management Improvements**
- Document collections/folders
- Batch upload processing
- Document metadata editor
- Search and filter documents
- Document versioning

**Week 3-4: Basic Analytics Implementation**
- Create metrics database tables
- Implement turn/session tracking
- Basic dashboard APIs
- Real-time conversation monitoring
- Export conversation transcripts

**Deliverables:**
- Multi-tenant database with workspace isolation
- Agent builder API endpoints
- Enhanced document management
- Basic analytics dashboard APIs
- Updated authentication and authorization

---

### Phase 2: Advanced Agent Features (Months 4-6)

**Goal:** Add powerful customization capabilities and multi-channel deployment

#### Month 4: Tool System Overhaul
**Week 1-2: Tool Registry & Configuration**
- Tool configuration model
- Tool marketplace/catalog
- Built-in tool implementations (web search, API caller, calculator)
- Tool testing framework

**Week 3-4: Custom Tool Builder**
- No-code API integration wizard
- Request/response schema builder
- Authentication configuration
- Tool testing playground

#### Month 5: Conversation Flow Designer
**Week 1-2: Flow Engine Backend**
- Flow definition schema (nodes, edges, conditions)
- Flow execution engine
- State management for flows
- Human handoff logic

**Week 3-4: Memory & Context Management**
- User profile storage
- Long-term memory implementation
- Context summarization
- Memory retrieval strategies

#### Month 6: Multi-Channel Deployment
**Week 1-2: Deployment Infrastructure**
- Chat widget SDK (JavaScript)
- Widget customization options
- CORS and embedding security
- API key management for external access

**Week 3-4: Channel Integrations**
- WhatsApp Business API integration
- Slack bot framework
- Webhook receiver for external platforms

**Deliverables:**
- Tool marketplace and custom tool builder
- Conversation flow designer (backend)
- Multi-channel deployment SDKs
- Enhanced memory management

---

### Phase 3: Production-Grade Analytics (Months 7-9)

**Goal:** Integrate comprehensive analytics from chat-verifier dashboard

#### Month 7: Analytics Infrastructure
**Week 1-2: Metrics Models Integration**
- Port metrics models from chat-verifier
- Create turn/session/daily metrics tables
- Implement metrics registry pattern
- Set up Celery tasks for rollups

**Week 3-4: Evaluation Pipeline**
- Stage 1: Rule-based evaluators (PII, language)
- Stage 2: Local ML models (toxicity, coherence)
- Stage 3: LLM-as-judge (faithfulness, relevance)
- Sampling and cost control

#### Month 8: Analytics APIs
**Week 1-2: Dashboard Endpoints**
- KPI overview endpoint
- Time series endpoint with grouping
- Distribution and percentiles
- Session drill-down

**Week 3-4: Advanced Analytics**
- Funnel analysis endpoints
- Cohort comparison
- Outlier detection
- Alert configuration

#### Month 9: A/B Testing Framework
**Week 1-2: Experiment Infrastructure**
- Experiment model and traffic splitting
- Random assignment with consistency
- Variant tracking in conversations

**Week 3-4: Statistical Analysis**
- Significance testing
- Confidence intervals
- Comparison dashboards
- Automated winner selection

**Deliverables:**
- Full analytics pipeline (35+ metrics)
- Dashboard APIs with caching
- A/B testing framework
- Real-time and historical reporting

---

### Phase 4: Optimization & Scale (Months 10-12)

**Goal:** Production hardening, performance optimization, and scaling

#### Month 10: Performance & Optimization
**Week 1-2: Query Optimization**
- Database indexing review
- Query profiling and optimization
- Read replica setup for analytics
- Connection pooling tuning

**Week 3-4: Caching Strategy**
- Redis caching for hot paths
- CDN for static assets
- Agent config caching
- Embedding result caching

#### Month 11: Agent Marketplace
**Week 1-2: Template System**
- Public agent templates
- Template categories and tags
- Rating and review system
- Clone from template

**Week 3-4: Sharing & Collaboration**
- Share agents across workspaces
- Permission management for shared agents
- Version tracking and updates
- Usage analytics for templates

#### Month 12: Monitoring & Reliability
**Week 1-2: Observability**
- Application metrics (Prometheus/Datadog)
- Error tracking (Sentry)
- Log aggregation (ELK/Loki)
- Performance monitoring (APM)

**Week 3-4: Reliability Engineering**
- Rate limiting and throttling
- Circuit breakers for external APIs
- Graceful degradation
- Disaster recovery planning

**Deliverables:**
- Optimized database and caching
- Agent marketplace
- Full observability stack
- Production reliability features

---

### Phase 5: Enterprise Features (Months 13-15)

**Goal:** Enterprise-ready features for large customers

#### Month 13: Security Hardening
- SSO integration (SAML, OAuth)
- Audit logging
- Compliance certifications prep
- Penetration testing

#### Month 14: Custom Deployments
- On-premises deployment packaging
- Helm charts for Kubernetes
- White-label customization
- Multi-region support

#### Month 15: Integrations & Support
- Major CRM integrations
- Analytics platform connectors
- Enterprise support infrastructure
- Documentation and training materials

**Deliverables:**
- Enterprise security features
- Deployment flexibility
- Integration ecosystem
- Enterprise support model

---

## Technical Specifications

### Tech Stack

**Backend:**
- Django 5.2+ (current)
- Django REST Framework
- Django Channels (WebSocket)
- Celery + Redis (task queue)
- PostgreSQL 15+ with pgvector
- LangChain (agent framework)

**Frontend (New):**
- React 18+
- TypeScript
- TanStack Query (data fetching)
- Recharts (analytics visualization)
- TailwindCSS (styling)
- Zustand (state management)

**Infrastructure:**
- Docker + Docker Compose (development)
- Kubernetes (production)
- Redis (cache + broker)
- S3/MinIO (file storage)
- Nginx (reverse proxy)
- CloudFlare (CDN)

**Observability:**
- Prometheus (metrics)
- Grafana (dashboards)
- Sentry (error tracking)
- ELK Stack (logs)

### Development Environment Setup

**Prerequisites:**
- Docker & Docker Compose
- Python 3.11+
- Node.js 20+
- PostgreSQL 15+ with pgvector

**Project Structure:**
```
enthusiast/
├── server/                 # Django backend (existing)
│   ├── agent/             # Agent management
│   ├── catalog/           # Knowledge base
│   ├── account/           # Users & auth
│   ├── workspace/         # NEW: Workspaces
│   ├── analytics/         # NEW: Analytics
│   └── billing/           # NEW: Billing
├── frontend/              # NEW: React dashboard
│   ├── src/
│   │   ├── features/
│   │   │   ├── agent-builder/
│   │   │   ├── analytics/
│   │   │   ├── workspaces/
│   │   │   └── knowledge-base/
│   │   ├── components/
│   │   ├── hooks/
│   │   └── api/
│   └── public/
├── plugins/               # Existing plugins
├── widget/                # NEW: Chat widget SDK
├── docs/                  # Documentation
└── deploy/                # Deployment configs
```

---

## Database Schema Changes

### New Models

#### 1. Workspace Model
```python
class Workspace(models.Model):
    """Multi-tenant workspace/organization"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    name = models.CharField(max_length=255)
    slug = models.SlugField(unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Settings
    settings = models.JSONField(default=dict)  # Branding, defaults, quotas

    # Billing
    plan = models.CharField(max_length=50, default='free')  # free, pro, enterprise
    billing_email = models.EmailField(blank=True)

    # Quotas
    max_agents = models.IntegerField(default=3)
    max_conversations_per_month = models.IntegerField(default=1000)
    max_documents = models.IntegerField(default=100)
    max_storage_mb = models.IntegerField(default=500)

    # Stats (denormalized for performance)
    total_conversations = models.IntegerField(default=0)
    total_messages = models.IntegerField(default=0)

    class Meta:
        db_table = 'workspaces'
        indexes = [
            models.Index(fields=['slug']),
            models.Index(fields=['created_at']),
        ]
```

#### 2. WorkspaceMember Model
```python
class WorkspaceMember(models.Model):
    """Workspace membership with roles"""

    ROLE_CHOICES = [
        ('owner', 'Owner'),
        ('admin', 'Admin'),
        ('member', 'Member'),
        ('viewer', 'Viewer'),
    ]

    workspace = models.ForeignKey(Workspace, on_delete=models.CASCADE, related_name='members')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='workspace_memberships')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)

    created_at = models.DateTimeField(auto_now_add=True)
    invited_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='invited_members')

    class Meta:
        db_table = 'workspace_members'
        unique_together = [('workspace', 'user')]
        indexes = [
            models.Index(fields=['workspace', 'role']),
        ]
```

#### 3. Updated Agent Model
```python
class Agent(models.Model):
    """Enhanced agent model with flexible configuration"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    workspace = models.ForeignKey(Workspace, on_delete=models.CASCADE)  # NEW

    # Basic info
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    avatar_url = models.URLField(blank=True)

    # Configuration (flexible JSON)
    config = models.JSONField(default=dict)
    # Config structure:
    # {
    #   "model": {"provider": "openai", "name": "gpt-4", "temperature": 0.7},
    #   "system_prompt": "You are a helpful assistant...",
    #   "personality": {"tone": "professional", "formality": "formal"},
    #   "tools": ["web_search", "calculator"],
    #   "memory": {"type": "summary", "max_tokens": 2000},
    #   "retrieval": {"top_k": 5, "score_threshold": 0.7},
    #   "conversation_starters": ["How can I help?", "Ask me anything"],
    # }

    # Versioning
    version = models.IntegerField(default=1)
    parent_version = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True)
    is_active = models.BooleanField(default=True)

    # Lifecycle
    status = models.CharField(max_length=20, default='draft')  # draft, active, archived
    published_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)

    # Analytics (denormalized)
    total_conversations = models.IntegerField(default=0)
    avg_rating = models.FloatField(null=True)

    class Meta:
        db_table = 'agents'
        indexes = [
            models.Index(fields=['workspace', 'status']),
            models.Index(fields=['workspace', 'is_active']),
        ]
```

#### 4. AgentTemplate Model
```python
class AgentTemplate(models.Model):
    """Reusable agent templates"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)

    name = models.CharField(max_length=255)
    description = models.TextField()
    category = models.CharField(max_length=100)  # customer_support, sales, education, etc.
    tags = ArrayField(models.CharField(max_length=50), default=list)

    # Template configuration
    config = models.JSONField()

    # Metadata
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    is_public = models.BooleanField(default=False)
    is_featured = models.BooleanField(default=False)

    # Stats
    clone_count = models.IntegerField(default=0)
    avg_rating = models.FloatField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'agent_templates'
```

#### 5. AgentExperiment Model (A/B Testing)
```python
class AgentExperiment(models.Model):
    """A/B testing experiments"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    workspace = models.ForeignKey(Workspace, on_delete=models.CASCADE)
    name = models.CharField(max_length=255)

    # Variants
    control_agent = models.ForeignKey(Agent, on_delete=models.CASCADE, related_name='experiments_as_control')
    variant_agents = models.ManyToManyField(Agent, related_name='experiments_as_variant', through='ExperimentVariant')

    # Traffic split
    traffic_allocation = models.JSONField()  # {"control": 50, "variant_a": 50}

    # Status
    status = models.CharField(max_length=20, default='draft')  # draft, running, completed
    started_at = models.DateTimeField(null=True)
    ended_at = models.DateTimeField(null=True)

    # Goals
    primary_metric = models.CharField(max_length=100)  # e.g., "answer_relevance", "containment_rate"

    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)

    class Meta:
        db_table = 'agent_experiments'
```

#### 6. Analytics Models (Ported from chat-verifier)

```python
class TurnMetric(models.Model):
    """Turn-level metrics"""
    workspace = models.ForeignKey(Workspace, on_delete=models.CASCADE)
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE)
    message = models.ForeignKey(Message, on_delete=models.CASCADE)

    metric_name = models.CharField(max_length=100)
    value = models.FloatField()

    # Context dimensions
    agent_id = models.UUIDField()
    agent_version = models.IntegerField()
    model = models.CharField(max_length=100)

    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'metrics_turn'
        indexes = [
            models.Index(fields=['workspace', 'timestamp']),
            models.Index(fields=['conversation', 'metric_name']),
            models.Index(fields=['metric_name', 'timestamp']),
        ]


class SessionMetric(models.Model):
    """Session-level aggregated metrics"""
    workspace = models.ForeignKey(Workspace, on_delete=models.CASCADE)
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE)

    metric_name = models.CharField(max_length=100)
    value = models.FloatField()
    count = models.IntegerField(default=1)  # for averaging

    # Context
    agent_id = models.UUIDField()
    agent_version = models.IntegerField()
    model = models.CharField(max_length=100)

    # Filters for analytics
    country = models.CharField(max_length=10, blank=True)
    channel = models.CharField(max_length=50, blank=True)

    timestamp = models.DateTimeField()

    class Meta:
        db_table = 'metrics_session'
        indexes = [
            models.Index(fields=['workspace', 'timestamp']),
            models.Index(fields=['metric_name', 'agent_id']),
        ]


class DailyMetric(models.Model):
    """Daily aggregated metrics"""
    workspace = models.ForeignKey(Workspace, on_delete=models.CASCADE)
    date = models.DateField()

    metric_name = models.CharField(max_length=100)
    value = models.FloatField()
    count = models.IntegerField()

    # Dimensions
    agent_id = models.UUIDField(null=True)
    model = models.CharField(max_length=100, blank=True)
    country = models.CharField(max_length=10, blank=True)
    channel = models.CharField(max_length=50, blank=True)

    class Meta:
        db_table = 'metrics_daily'
        unique_together = [('workspace', 'date', 'metric_name', 'agent_id', 'model', 'country', 'channel')]
        indexes = [
            models.Index(fields=['workspace', 'date']),
            models.Index(fields=['date', 'metric_name']),
        ]
```

### Migration Strategy

**Step 1: Add Workspace Foreign Keys**
- Add nullable `workspace_id` to all models
- Create default workspace for existing data
- Populate workspace_id for all existing records

**Step 2: Make Workspace Required**
- Remove null=True from workspace_id
- Add database constraints
- Update all queries to include workspace filtering

**Step 3: Add New Models**
- Create analytics tables
- Create workspace member tables
- Create agent template tables

**Step 4: Data Migration**
- Migrate existing agent configs to new JSON format
- Generate embeddings for existing documents
- Backfill basic metrics from conversation history

---

## API Endpoints

### Workspace Management

```
POST   /api/workspaces/                      Create workspace
GET    /api/workspaces/                      List user's workspaces
GET    /api/workspaces/{id}/                 Get workspace details
PATCH  /api/workspaces/{id}/                 Update workspace
DELETE /api/workspaces/{id}/                 Delete workspace

GET    /api/workspaces/{id}/members/         List members
POST   /api/workspaces/{id}/members/         Invite member
PATCH  /api/workspaces/{id}/members/{user}/  Update member role
DELETE /api/workspaces/{id}/members/{user}/  Remove member

GET    /api/workspaces/{id}/usage/           Usage stats and quotas
```

### Agent Builder

```
GET    /api/agents/                          List workspace agents
POST   /api/agents/                          Create agent
GET    /api/agents/{id}/                     Get agent details
PUT    /api/agents/{id}/                     Update agent
DELETE /api/agents/{id}/                     Delete agent
POST   /api/agents/{id}/clone/               Clone agent
POST   /api/agents/{id}/publish/             Publish agent version

POST   /api/agents/{id}/test/                Test agent (dry-run)
GET    /api/agents/{id}/versions/            List versions
POST   /api/agents/{id}/rollback/            Rollback to version

GET    /api/agents/{id}/analytics/           Agent-specific analytics
GET    /api/agents/{id}/conversations/       Recent conversations
```

### Agent Templates

```
GET    /api/templates/                       Browse templates
GET    /api/templates/{id}/                  Template details
POST   /api/templates/{id}/clone/            Clone to workspace
POST   /api/templates/                       Create template (from agent)

GET    /api/templates/categories/            List categories
GET    /api/templates/featured/              Featured templates
```

### Knowledge Base

```
GET    /api/knowledge/collections/           List collections
POST   /api/knowledge/collections/           Create collection
GET    /api/knowledge/collections/{id}/      Collection details
DELETE /api/knowledge/collections/{id}/      Delete collection

POST   /api/knowledge/documents/             Upload document(s)
GET    /api/knowledge/documents/             List documents
GET    /api/knowledge/documents/{id}/        Document details
DELETE /api/knowledge/documents/{id}/        Delete document
PATCH  /api/knowledge/documents/{id}/        Update metadata

POST   /api/knowledge/documents/sync/        Sync external sources
GET    /api/knowledge/documents/{id}/chunks/ View chunks
```

### Conversations (Enhanced)

```
POST   /api/conversations/                   Create conversation
GET    /api/conversations/                   List conversations
GET    /api/conversations/{id}/              Get conversation
POST   /api/conversations/{id}/              Send message
DELETE /api/conversations/{id}/              Delete conversation

POST   /api/conversations/{id}/feedback/     Submit feedback
POST   /api/conversations/{id}/handoff/      Request human handoff
GET    /api/conversations/{id}/export/       Export transcript
```

### Analytics Dashboard

```
GET    /api/analytics/overview/              Overview KPIs
GET    /api/analytics/timeseries/            Time series data
GET    /api/analytics/distribution/          Distribution histograms
GET    /api/analytics/funnel/                Funnel analysis
GET    /api/analytics/outliers/              Outlier sessions

GET    /api/analytics/metrics/               List available metrics
GET    /api/analytics/sessions/              Drill-down sessions
GET    /api/analytics/sessions/{id}/         Session detail

POST   /api/analytics/export/                Export data (CSV)
```

### A/B Testing

```
POST   /api/experiments/                     Create experiment
GET    /api/experiments/                     List experiments
GET    /api/experiments/{id}/                Experiment details
PATCH  /api/experiments/{id}/                Update experiment
POST   /api/experiments/{id}/start/          Start experiment
POST   /api/experiments/{id}/stop/           Stop experiment

GET    /api/experiments/{id}/results/        Results comparison
GET    /api/experiments/{id}/significance/   Statistical analysis
```

### Deployment

```
GET    /api/deployments/widget-config/       Widget configuration
POST   /api/deployments/api-keys/            Generate API key
GET    /api/deployments/api-keys/            List API keys
DELETE /api/deployments/api-keys/{id}/       Revoke API key

GET    /api/deployments/channels/            List channel integrations
POST   /api/deployments/channels/            Add channel
DELETE /api/deployments/channels/{id}/       Remove channel
```

---

## Analytics Integration

### Integration Strategy

**Option 1: Embedded Integration (RECOMMENDED)**
- Port analytics code directly into Django app
- Single codebase and deployment
- Shared database and infrastructure
- Easier to maintain

**Option 2: Microservice Integration**
- Keep analytics as separate FastAPI service
- Communicate via REST API or message queue
- Independent scaling
- More complex deployment

**Recommendation:** Option 1 (Embedded) for simplicity and consistency

### Implementation Plan

#### 1. Port Models
- Copy metrics models from chat-verifier
- Adapt to Django ORM
- Add workspace foreign keys
- Create migrations

#### 2. Port Evaluators
- Create `server/analytics/evaluators/` directory
- Port rule-based evaluators
- Port transformer-based evaluators
- Port LLM judges
- Update to use Django models

#### 3. Create Analytics Service
- `server/analytics/services/metrics_service.py`
- Port business logic methods
- Use Django queryset instead of raw SQL
- Add workspace filtering

#### 4. Create API Endpoints
- `server/analytics/views.py`
- `server/analytics/urls.py`
- Add authentication and workspace checks
- Implement caching with Redis

#### 5. Celery Tasks
- Port ingest tasks (adapt from Kogents to Conversations)
- Port rollup tasks
- Port evaluation pipeline
- Schedule with Celery Beat

#### 6. Real-Time Metrics
- WebSocket consumer for live metrics
- Redis pub/sub for distribution
- Update on new conversations/messages

### Key Differences from Chat-Verifier

| Aspect | Chat-Verifier | Agent Builder Platform |
|--------|---------------|------------------------|
| Data Source | External API (Kogents) | Internal (Conversations) |
| Framework | FastAPI | Django + DRF |
| Multi-tenancy | None | Workspace-based |
| Real-time | Batch only | Streaming + Batch |
| Integration | Separate service | Embedded in main app |
| Authentication | API key | Token + Workspace |

### Metrics Configuration

Allow workspace-level metric configuration:
- Enable/disable specific metrics
- Set sampling rates (cost control)
- Configure alert thresholds
- Choose evaluation models

```python
# Workspace settings JSON
{
  "analytics": {
    "enabled_metrics": ["answer_relevance", "faithfulness", "toxicity"],
    "llm_judge_sampling_rate": 0.1,  # 10% for cost control
    "local_evaluators": true,
    "alert_thresholds": {
      "answer_relevance": {"warn": 0.7, "critical": 0.5},
      "toxicity": {"warn": 0.3, "critical": 0.5}
    }
  }
}
```

---

## Frontend Requirements

### Main Dashboard Pages

#### 1. Workspace Selector
- Dropdown to switch workspaces
- Create new workspace
- Workspace settings

#### 2. Agents Page
- Grid/list of agents
- Agent status (draft, active, archived)
- Quick stats (conversations, avg rating)
- Create/clone/delete actions

#### 3. Agent Builder
**Left Sidebar:**
- Configuration sections (expandable)
  - Basic Info
  - System Prompt
  - Model Selection
  - Tools
  - Memory
  - Retrieval
  - Conversation Starters

**Main Canvas:**
- Live preview of chat interface
- Test conversations
- Sample queries

**Right Sidebar:**
- Version history
- Quick stats
- Publish/rollback buttons

#### 4. Knowledge Base
- File upload area (drag-and-drop)
- Document list with search/filter
- Collection organizer (folders)
- Document preview
- Sync configuration

#### 5. Analytics Dashboard
**Overview Tab:**
- KPI cards (quality, performance, business)
- Sparklines showing trends
- Alert notifications

**Quality Tab:**
- Time series charts
- Distribution histograms
- Drill-down table

**Performance Tab:**
- Latency charts
- Cost tracking
- Token usage

**Conversations Tab:**
- Searchable conversation list
- Filters (date, agent, rating, outcome)
- Session replay viewer

#### 6. A/B Testing
- Experiment creation wizard
- Running experiments list
- Results dashboard with significance

#### 7. Settings
- Workspace settings
- Team members
- Billing
- API keys
- Integrations

### Component Library

**Core Components:**
- AgentCard
- ConversationList
- MessageBubble
- MetricCard
- TimeSeriesChart
- DistributionChart
- FunnelChart
- CodeEditor (for prompts)
- JSONEditor (for config)

### State Management

Use Zustand for global state:
- Current workspace
- User info
- Selected agent
- Dashboard filters

### API Integration

Use TanStack Query for:
- Automatic caching
- Optimistic updates
- Background refetching
- Pagination

---

## Security & Access Control

### Role-Based Access Control (RBAC)

| Permission | Owner | Admin | Member | Viewer |
|------------|-------|-------|--------|--------|
| View agents | ✅ | ✅ | ✅ | ✅ |
| Create agents | ✅ | ✅ | ✅ | ❌ |
| Edit agents | ✅ | ✅ | ✅ | ❌ |
| Delete agents | ✅ | ✅ | ❌ | ❌ |
| Publish agents | ✅ | ✅ | ❌ | ❌ |
| View analytics | ✅ | ✅ | ✅ | ✅ |
| Manage members | ✅ | ✅ | ❌ | ❌ |
| Billing | ✅ | ❌ | ❌ | ❌ |
| Delete workspace | ✅ | ❌ | ❌ | ❌ |

### Workspace Isolation

**Database Level:**
- All queries filtered by `workspace_id`
- Django middleware injects workspace context
- Row-level security policies in PostgreSQL

**API Level:**
- Extract workspace from URL or token
- Check user membership and role
- Raise 403 if unauthorized

**File Storage:**
- Separate S3 prefixes per workspace: `workspace-{id}/documents/`
- Pre-signed URLs with expiration
- Access control via workspace membership

### API Security

**Authentication:**
- JWT tokens for dashboard
- API keys for external integrations
- OAuth for third-party apps

**Rate Limiting:**
- Per workspace, per endpoint
- Redis-based sliding window
- Different limits by plan tier

**Input Validation:**
- Pydantic schemas for all inputs
- SQL injection prevention (ORM)
- XSS prevention (sanitize outputs)
- File upload restrictions (size, type)

### Data Privacy

**PII Handling:**
- Detect PII in conversations
- Option to mask/redact PII
- GDPR-compliant data export/deletion
- Data retention policies

**Encryption:**
- TLS for data in transit
- Encrypted fields for sensitive data
- Encrypted S3 storage

---

## Deployment Strategy

### Development Environment

```yaml
# docker-compose.yml
services:
  db:
    image: pgvector/pgvector:pg15
    environment:
      POSTGRES_DB: enthusiast
      POSTGRES_PASSWORD: dev
    volumes:
      - postgres_data:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine

  backend:
    build: ./server
    command: python manage.py runserver 0.0.0.0:8000
    volumes:
      - ./server:/app
    environment:
      DATABASE_URL: postgres://postgres:dev@db:5432/enthusiast
      REDIS_URL: redis://redis:6379/0
    depends_on:
      - db
      - redis

  celery_worker:
    build: ./server
    command: celery -A pecl worker -l info
    volumes:
      - ./server:/app
    depends_on:
      - db
      - redis

  celery_beat:
    build: ./server
    command: celery -A pecl beat -l info
    depends_on:
      - redis

  frontend:
    build: ./frontend
    command: npm run dev
    volumes:
      - ./frontend:/app
    ports:
      - "3000:3000"
```

### Staging Environment

**Infrastructure:**
- Kubernetes cluster (GKE/EKS)
- Managed PostgreSQL (CloudSQL/RDS)
- Managed Redis (Memorystore/ElastiCache)
- S3-compatible object storage
- CloudFlare CDN

**Deployment:**
- Helm charts for Kubernetes
- GitOps with ArgoCD
- Blue-green deployments
- Automated DB migrations

### Production Environment

**High Availability:**
- Multiple availability zones
- Database read replicas
- Redis cluster mode
- Load balancer with health checks

**Scaling:**
- Horizontal pod autoscaling (HPA)
- Vertical pod autoscaling (VPA)
- Separate worker pools for different task types
- Database connection pooling (PgBouncer)

**Monitoring:**
- Prometheus + Grafana
- Sentry for errors
- ELK for logs
- Uptime monitoring (Pingdom/UptimeRobot)

**Backup & Recovery:**
- Automated DB backups (hourly)
- Point-in-time recovery
- S3 versioning for files
- Disaster recovery runbook

---

## Cost Estimation

### Infrastructure Costs (Monthly)

**Small Scale (100 workspaces, 10K conversations/month):**
- Kubernetes cluster (3 nodes): $150
- PostgreSQL (db.t3.medium): $70
- Redis (cache.t3.small): $15
- S3 storage (100 GB): $3
- CDN/Bandwidth: $20
- **Total: ~$260/month**

**Medium Scale (1,000 workspaces, 100K conversations/month):**
- Kubernetes cluster (10 nodes): $500
- PostgreSQL (db.r5.large + replica): $300
- Redis (cache.r5.large): $120
- S3 storage (1 TB): $25
- CDN/Bandwidth: $100
- **Total: ~$1,045/month**

**Large Scale (10,000 workspaces, 1M conversations/month):**
- Kubernetes cluster (50 nodes): $2,500
- PostgreSQL (db.r5.4xlarge + 2 replicas): $1,500
- Redis cluster: $500
- S3 storage (10 TB): $250
- CDN/Bandwidth: $500
- **Total: ~$5,250/month**

### LLM API Costs

**Per 1,000 conversations (estimates):**
- Agent responses (GPT-4): $50-200 (depends on context size)
- Embeddings (OpenAI): $1-5
- Analytics evaluation (GPT-4o-mini, 10% sampling): $5-10

**Cost optimization strategies:**
- Use cheaper models (GPT-3.5, Claude Haiku) for simple queries
- Implement aggressive caching
- Offer BYO API key option
- Sample evaluations instead of 100%

### Development Costs

**Team (15 months):**
- 2 Backend Engineers: $300K
- 1 Frontend Engineer: $150K
- 1 DevOps Engineer: $120K
- 1 Product Manager: $120K
- **Total: ~$690K**

**Additional:**
- Design/UX: $30K
- QA/Testing: $40K
- Documentation: $20K
- **Total: ~$780K**

---

## Success Metrics

### Product Metrics

**Adoption:**
- Number of workspaces created
- Active workspaces (used in last 30 days)
- Agents created per workspace
- Conversations per agent per day

**Engagement:**
- Daily/Weekly/Monthly active users
- Average session duration
- Features used per session
- Return rate (day 1, day 7, day 30)

**Quality:**
- Average agent quality score
- Percentage of agents with >0.7 quality
- User satisfaction (NPS)
- Support ticket volume

### Business Metrics

**Revenue:**
- Monthly Recurring Revenue (MRR)
- Customer Acquisition Cost (CAC)
- Lifetime Value (LTV)
- LTV:CAC ratio (target: >3)

**Retention:**
- Monthly churn rate (target: <5%)
- Cohort retention curves
- Expansion revenue (upgrades)
- Net Revenue Retention (target: >110%)

### Technical Metrics

**Performance:**
- API response time (P50, P95, P99)
- Agent response time
- Error rate (target: <0.1%)
- Uptime (target: 99.9%)

**Cost Efficiency:**
- Infrastructure cost per workspace
- LLM cost per conversation
- Support cost per customer
- Gross margin (target: >70%)

---

## Risks & Mitigation

### Technical Risks

**Risk: Vector search performance degradation with scale**
- Mitigation: Use IVFFlat indexing, separate read replicas, implement caching

**Risk: High LLM API costs**
- Mitigation: Aggressive caching, model selection, BYO key option, usage quotas

**Risk: Complex multi-tenancy bugs**
- Mitigation: Comprehensive test suite, workspace isolation checks, code review

**Risk: Analytics processing bottleneck**
- Mitigation: Sampling, async processing, separate workers, database optimization

### Business Risks

**Risk: Low user adoption**
- Mitigation: Free tier, template marketplace, excellent onboarding, case studies

**Risk: High churn**
- Mitigation: Focus on value delivery, responsive support, product analytics

**Risk: Competition from larger players**
- Mitigation: Niche focus, superior UX, faster iteration, community building

**Risk: Data security breach**
- Mitigation: Security audits, compliance certifications, bug bounty program

---

## Next Steps

### Immediate Actions (This Month)

1. **Stakeholder Alignment**
   - Review this roadmap with team
   - Prioritize features based on user feedback
   - Finalize Phase 1 scope

2. **Design Mockups**
   - Create wireframes for agent builder
   - Design analytics dashboard
   - User flow diagrams

3. **Technical Preparation**
   - Set up development environment
   - Create feature branches
   - Write first set of tests

4. **User Research**
   - Interview 10 potential users
   - Validate pain points
   - Refine value proposition

### Month 1 Kickoff

- Sprint planning for Phase 1
- Architecture review meeting
- Begin multi-tenancy implementation
- Start frontend scaffolding

---

## Appendix

### A. Agent Configuration Schema

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "properties": {
    "model": {
      "type": "object",
      "properties": {
        "provider": {"type": "string", "enum": ["openai", "anthropic", "google"]},
        "name": {"type": "string"},
        "temperature": {"type": "number", "minimum": 0, "maximum": 2},
        "max_tokens": {"type": "integer", "minimum": 1},
        "top_p": {"type": "number", "minimum": 0, "maximum": 1}
      },
      "required": ["provider", "name"]
    },
    "system_prompt": {"type": "string"},
    "personality": {
      "type": "object",
      "properties": {
        "tone": {"type": "string", "enum": ["professional", "casual", "friendly"]},
        "formality": {"type": "string", "enum": ["formal", "neutral", "informal"]},
        "verbosity": {"type": "string", "enum": ["concise", "balanced", "detailed"]}
      }
    },
    "tools": {
      "type": "array",
      "items": {"type": "string"}
    },
    "memory": {
      "type": "object",
      "properties": {
        "type": {"type": "string", "enum": ["summary", "buffer", "knowledge_graph"]},
        "max_tokens": {"type": "integer"}
      }
    },
    "retrieval": {
      "type": "object",
      "properties": {
        "enabled": {"type": "boolean"},
        "top_k": {"type": "integer", "minimum": 1, "maximum": 20},
        "score_threshold": {"type": "number", "minimum": 0, "maximum": 1}
      }
    },
    "conversation_starters": {
      "type": "array",
      "items": {"type": "string"},
      "maxItems": 5
    },
    "constraints": {
      "type": "object",
      "properties": {
        "max_conversation_length": {"type": "integer"},
        "max_response_tokens": {"type": "integer"},
        "response_timeout_seconds": {"type": "integer"}
      }
    }
  },
  "required": ["model", "system_prompt"]
}
```

### B. Metrics Definitions

See chat-verifier `METRICS_STRATEGY.md` for detailed metric definitions.

Key metrics:
- **answer_relevance**: How well the response answers the user's question
- **faithfulness**: Whether the response is grounded in retrieved documents
- **coherence**: Logical flow and readability of response
- **toxicity**: Harmful or offensive content score
- **ttft_ms**: Time to first token (latency)
- **containment_rate**: % of conversations that don't require human handoff
- **conversion_rate**: % of conversations that achieve the goal

### C. API Authentication

**JWT Token Format:**
```json
{
  "user_id": "uuid",
  "workspace_id": "uuid",
  "role": "admin",
  "exp": 1234567890
}
```

**API Key Format:**
```
pb_live_1234567890abcdef  # production
pb_test_1234567890abcdef  # testing
```

### D. Glossary

- **Agent**: A configured AI assistant with specific behavior and knowledge
- **Workspace**: Multi-tenant organization/team container
- **Dataset**: Collection of documents and products for retrieval
- **Turn**: Single user message + assistant response pair
- **Session**: Complete conversation from start to end
- **Containment**: Conversation handled by agent without human handoff
- **Faithfulness**: Accuracy of response relative to source documents
- **Hallucination**: Response contains information not in source documents

---

**End of Document**

This roadmap should be treated as a living document and updated as we learn more from user feedback and implementation experience.
