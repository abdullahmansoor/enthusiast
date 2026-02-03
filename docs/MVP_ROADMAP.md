# MVP Roadmap: Agent Builder + Analytics Platform
## Focused 6-Week Implementation Plan

**Last Updated:** January 20, 2026
**Goal:** Build a functional agent builder with comprehensive analytics in 6 weeks

---

## Table of Contents

1. [MVP Scope](#mvp-scope)
2. [Architecture Decision: Analytics Integration](#architecture-decision-analytics-integration)
3. [6-Week Timeline](#6-week-timeline)
4. [Technical Implementation](#technical-implementation)
5. [MVP Feature List](#mvp-feature-list)
6. [Success Criteria](#success-criteria)

---

## MVP Scope

### What's IN the MVP

**Agent Builder:**
- ✅ Create and configure agents with visual interface
- ✅ Customize system prompts and model parameters
- ✅ Upload documents for RAG knowledge base
- ✅ Test agent in preview mode
- ✅ Basic conversation management

**Analytics:**
- ✅ Real-time conversation monitoring
- ✅ Quality metrics (answer relevance, faithfulness, coherence)
- ✅ Performance metrics (latency, token usage, cost)
- ✅ Safety metrics (toxicity, PII detection)
- ✅ Time series charts and KPI dashboard
- ✅ Conversation drill-down and replay

**Infrastructure:**
- ✅ Single workspace (no multi-tenancy for MVP)
- ✅ User authentication
- ✅ REST API + WebSocket for streaming
- ✅ Background job processing (Celery)

### What's OUT of MVP (Phase 2)

- ❌ Multi-tenancy / workspaces
- ❌ Team collaboration
- ❌ Custom tool builder
- ❌ Conversation flow designer
- ❌ A/B testing framework
- ❌ Multiple deployment channels (just API)
- ❌ Agent marketplace/templates
- ❌ Advanced access control

---

## Architecture Decision: Analytics Integration

### Recommendation: **Direct Integration (Copy & Port)**

**Approach:** Copy the analytics code from chat-verifier and integrate directly into Django app as an `analytics` Django app.

### Why This Approach?

**Pros:**
- ✅ **Simpler development** - No package management overhead
- ✅ **Faster iteration** - Modify code directly without republishing packages
- ✅ **Single codebase** - Easier to understand and debug
- ✅ **Shared models** - Direct access to Conversation, Message, Agent models
- ✅ **Unified authentication** - No need for service-to-service auth
- ✅ **Better performance** - No network overhead, direct DB access
- ✅ **Easier deployment** - One Docker container, one process

**Cons:**
- ❌ Code duplication if you have multiple projects needing analytics
- ❌ Can't easily swap analytics provider later

**Alternative (Not Recommended for MVP):**
- Make it a separate microservice - adds complexity
- Make it a Python package - overhead of package management

### Implementation Strategy

```
1. Copy chat-verifier analytics code
2. Adapt to Django ORM (from SQLAlchemy)
3. Integrate with existing models
4. Use same Celery setup for background jobs
5. Add analytics endpoints to existing API
```

**Migration Path for Later:**
If you need to reuse analytics in other projects later, you can always extract it into a package. But for MVP, keep it simple and integrated.

---

## 6-Week Timeline

### Week 1: Foundation Setup
**Goal:** Prepare codebase and database for agent builder + analytics

**Tasks:**
- [ ] Clean up existing codebase
- [ ] Update Agent model for flexible JSON config
- [ ] Create analytics app structure
- [ ] Set up additional dependencies
- [ ] Database schema updates

**Deliverables:**
- Enhanced Agent model with flexible config
- Analytics Django app skeleton
- Migration scripts ready

---

### Week 2: Agent Builder Backend
**Goal:** Build API endpoints for agent management

**Tasks:**
- [ ] Agent CRUD endpoints with JSON config
- [ ] Agent configuration validation
- [ ] Test agent endpoint (dry-run)
- [ ] Enhanced document upload and processing
- [ ] Agent version tracking

**Deliverables:**
- Agent builder API complete
- Swagger/OpenAPI docs updated
- Postman collection for testing

---

### Week 3: Analytics Backend - Metrics Pipeline
**Goal:** Implement core metrics computation

**Tasks:**
- [ ] Port metrics models (TurnMetric, SessionMetric, DailyMetric)
- [ ] Implement evaluators:
  - Stage 1: Rule-based (PII, language detection)
  - Stage 2: Local ML (toxicity, coherence)
  - Stage 3: LLM judges (relevance, faithfulness)
- [ ] Create metrics service with computation logic
- [ ] Celery tasks for evaluation pipeline
- [ ] Hook metrics computation into conversation flow

**Deliverables:**
- Metrics computed automatically for all conversations
- Background evaluation pipeline working
- Test coverage for evaluators

---

### Week 4: Analytics Backend - Dashboard APIs
**Goal:** Build analytics query APIs

**Tasks:**
- [ ] KPI overview endpoint
- [ ] Time series endpoint
- [ ] Distribution/histogram endpoint
- [ ] Conversation list with metrics
- [ ] Session detail with turn breakdown
- [ ] Redis caching for performance

**Deliverables:**
- Complete analytics REST API
- API documentation
- Sample queries and responses

---

### Week 5: Frontend - Agent Builder UI
**Goal:** Build visual agent configuration interface

**Tasks:**
- [ ] React app setup with TypeScript
- [ ] Agent list page
- [ ] Agent builder page:
  - Basic info form
  - System prompt editor
  - Model configuration
  - Preview/test panel
- [ ] Document upload interface
- [ ] API integration with TanStack Query

**Deliverables:**
- Working agent builder UI
- Users can create and test agents visually

---

### Week 6: Frontend - Analytics Dashboard
**Goal:** Build analytics visualization

**Tasks:**
- [ ] Dashboard layout with KPI cards
- [ ] Time series charts (Recharts)
- [ ] Quality metrics tab
- [ ] Performance metrics tab
- [ ] Conversation list with drill-down
- [ ] Session replay viewer
- [ ] Polish and bug fixes

**Deliverables:**
- Complete analytics dashboard
- Users can monitor agent performance
- MVP ready for demo/testing

---

## Technical Implementation

### Project Structure (MVP)

```
enthusiast/
├── server/                          # Django backend
│   ├── agent/                       # Agent management (existing)
│   │   ├── models/
│   │   │   ├── agent.py            # ENHANCED: JSON config
│   │   │   ├── conversation.py
│   │   │   └── message.py
│   │   ├── views.py                # ENHANCED: New endpoints
│   │   └── urls.py
│   │
│   ├── catalog/                     # Knowledge base (existing)
│   │   ├── models.py
│   │   └── views.py
│   │
│   ├── analytics/                   # NEW: Analytics app
│   │   ├── models/
│   │   │   ├── metrics.py          # TurnMetric, SessionMetric, DailyMetric
│   │   │   └── evaluation.py      # EvaluationJob
│   │   ├── evaluators/
│   │   │   ├── registry.py         # Metrics registry
│   │   │   ├── rule_based.py       # Stage 1
│   │   │   ├── local_ml.py         # Stage 2
│   │   │   └── llm_judges.py       # Stage 3
│   │   ├── services/
│   │   │   └── metrics_service.py  # Business logic
│   │   ├── tasks.py                # Celery tasks
│   │   ├── views.py                # Dashboard APIs
│   │   └── urls.py
│   │
│   ├── account/                     # Users (existing)
│   └── pecl/                        # Settings (existing)
│
├── frontend/                        # NEW: React dashboard
│   ├── src/
│   │   ├── features/
│   │   │   ├── agents/             # Agent builder
│   │   │   │   ├── AgentList.tsx
│   │   │   │   ├── AgentBuilder.tsx
│   │   │   │   └── AgentPreview.tsx
│   │   │   └── analytics/          # Analytics dashboard
│   │   │       ├── Dashboard.tsx
│   │   │       ├── KPICards.tsx
│   │   │       ├── TimeSeriesChart.tsx
│   │   │       └── ConversationList.tsx
│   │   ├── api/                    # API client
│   │   └── components/             # Shared components
│   └── package.json
│
└── docs/                            # Documentation
    ├── MVP_ROADMAP.md              # This file
    └── MVP_IMPLEMENTATION.md       # Detailed steps
```

### Database Schema (MVP Changes)

**Enhanced Agent Model:**
```python
class Agent(models.Model):
    id = models.UUIDField(primary_key=True)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)

    # NEW: Flexible JSON configuration
    config = models.JSONField(default=dict)
    # Structure:
    # {
    #   "model": {"provider": "openai", "name": "gpt-4", "temperature": 0.7},
    #   "system_prompt": "You are...",
    #   "retrieval": {"enabled": true, "top_k": 5},
    #   ...
    # }

    # NEW: Versioning
    version = models.IntegerField(default=1)
    status = models.CharField(max_length=20, default='draft')

    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
```

**Analytics Models:**
```python
class TurnMetric(models.Model):
    """Per-message metrics"""
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE)
    message = models.ForeignKey(Message, on_delete=models.CASCADE)
    metric_name = models.CharField(max_length=100)
    value = models.FloatField()
    timestamp = models.DateTimeField(auto_now_add=True)

class SessionMetric(models.Model):
    """Per-conversation aggregated metrics"""
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE)
    metric_name = models.CharField(max_length=100)
    value = models.FloatField()
    count = models.IntegerField()

class DailyMetric(models.Model):
    """Daily rollups for trends"""
    date = models.DateField()
    agent_id = models.UUIDField()
    metric_name = models.CharField(max_length=100)
    value = models.FloatField()
    count = models.IntegerField()
```

### API Endpoints (MVP)

**Agent Builder:**
```
GET    /api/agents/                    List agents
POST   /api/agents/                    Create agent
GET    /api/agents/{id}/               Get agent
PUT    /api/agents/{id}/               Update agent
DELETE /api/agents/{id}/               Delete agent
POST   /api/agents/{id}/test/          Test agent with message
GET    /api/agents/{id}/conversations/ Recent conversations

POST   /api/conversations/             Create conversation
GET    /api/conversations/{id}/        Get conversation
POST   /api/conversations/{id}/        Send message
```

**Analytics:**
```
GET    /api/analytics/overview/        KPI summary
GET    /api/analytics/timeseries/      Time series for metric
GET    /api/analytics/distribution/    Histogram distribution
GET    /api/analytics/conversations/   Conversation list with metrics
GET    /api/analytics/conversations/{id}/detail/  Session detail
```

---

## MVP Feature List

### 1. Agent Builder Features

**Agent Configuration:**
- [ ] Agent name, description, avatar
- [ ] System prompt with markdown editor
- [ ] Model selection (GPT-4, GPT-3.5, GPT-4o-mini)
- [ ] Temperature slider
- [ ] Max tokens setting
- [ ] Conversation starters (pre-defined prompts)

**Knowledge Base:**
- [ ] Upload PDF, DOCX, TXT, MD files
- [ ] Automatic chunking and embedding
- [ ] View uploaded documents
- [ ] Delete documents
- [ ] Configure retrieval (top_k, score_threshold)

**Testing:**
- [ ] Test panel with chat interface
- [ ] Send test messages
- [ ] See retrieved context
- [ ] View token usage
- [ ] Clear test conversation

**Publishing:**
- [ ] Save as draft
- [ ] Publish agent (make active)
- [ ] Create new version

### 2. Analytics Features

**Dashboard Overview:**
- [ ] KPI Cards:
  - Total conversations
  - Average quality score
  - Average response time
  - Total cost (estimated)
- [ ] Date range picker (last 7, 30, 90 days)
- [ ] Agent selector (filter by agent)

**Quality Metrics:**
- [ ] Answer Relevance (LLM-judged)
  - Time series chart
  - Distribution histogram
  - Average score
- [ ] Faithfulness (LLM-judged)
  - Grounding to source documents
  - Hallucination detection
- [ ] Coherence (ML-based)
  - Response relevance to query
- [ ] Toxicity (ML-based)
  - Detoxify model

**Performance Metrics:**
- [ ] Response time (P50, P95)
- [ ] Time to first token (TTFT)
- [ ] Token usage per conversation
- [ ] Estimated cost per conversation

**Safety Metrics:**
- [ ] PII detection rate
- [ ] Toxic response rate
- [ ] Flagged conversations

**Conversation Explorer:**
- [ ] Searchable conversation list
- [ ] Filter by:
  - Date range
  - Agent
  - Quality score
  - Rating (thumbs up/down)
- [ ] Sort by date, quality, duration
- [ ] Session replay:
  - Full conversation transcript
  - Turn-by-turn metrics
  - Retrieved context shown
  - Token usage breakdown

---

## Success Criteria

### Week 3 Checkpoint
- ✅ Can create agent via API with JSON config
- ✅ Metrics are computed automatically
- ✅ Can query metrics via API

### Week 6 MVP Complete
- ✅ Can create and configure agent visually
- ✅ Can upload documents and they're indexed
- ✅ Can test agent in preview mode
- ✅ Analytics dashboard shows:
  - Real-time conversation count
  - Quality scores (relevance, faithfulness)
  - Performance metrics (latency, cost)
  - Conversation list with drill-down
- ✅ All metrics update automatically
- ✅ Dashboard is responsive and fast (<2s load)

### Demo Scenarios

**Scenario 1: Create Agent**
1. User creates new agent "Customer Support Bot"
2. Sets system prompt: "You are a helpful customer support agent"
3. Uploads 10 PDF product manuals
4. Tests agent with sample questions
5. Publishes agent

**Scenario 2: Monitor Performance**
1. User has 100+ conversations
2. Opens analytics dashboard
3. Sees quality score trending up over time
4. Identifies 3 low-quality conversations
5. Drills down to see what went wrong
6. Updates system prompt to improve

---

## Development Best Practices

### Code Quality
- Type hints in Python
- TypeScript for frontend (no `any` types)
- Unit tests for evaluators (90%+ coverage)
- API integration tests

### Performance
- Redis caching for dashboard queries (5 min TTL)
- Async evaluation (don't block conversation API)
- Pagination for conversation lists (20 per page)
- Lazy load ML models (on first use)

### Cost Optimization
- Sample LLM evaluations (10% by default)
- Use GPT-4o-mini for evaluations (cheaper than GPT-4)
- Cache embedding results
- Batch evaluation jobs

### Error Handling
- Graceful degradation if evaluation fails
- Retry logic for LLM API calls
- Clear error messages in UI
- Sentry for error tracking

---

## Next Steps

1. **Read MVP_IMPLEMENTATION.md** - Detailed step-by-step guide
2. **Set up development environment** - Docker, dependencies
3. **Start Week 1 tasks** - Foundation setup
4. **Daily standup** - Track progress, unblock issues
5. **Weekly demos** - Show progress, get feedback

---

## Deployment (Simple MVP Deployment)

### Development
```bash
docker-compose up -d
```

### Production (Simple)
- Single VM (4 CPU, 16GB RAM)
- Docker Compose
- PostgreSQL + Redis + Django + Celery
- Nginx reverse proxy
- Let's Encrypt SSL
- CloudFlare CDN for frontend

**Estimated Cost:** $50-100/month

---

## Post-MVP Roadmap

After successful MVP, prioritize:

1. **Multi-tenancy** - Add workspaces for multiple users
2. **A/B testing** - Compare agent versions
3. **Custom tools** - Allow users to add API integrations
4. **Deployment options** - Chat widget, WhatsApp, Slack
5. **Advanced analytics** - Cohort analysis, funnel tracking
6. **Collaboration** - Team features, sharing agents

---

This MVP is designed to be **achievable in 6 weeks** with 1-2 developers, while delivering maximum value: a working agent builder with production-grade analytics.
