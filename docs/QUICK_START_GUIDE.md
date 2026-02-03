# Quick Start Guide
## Agent Builder Platform Implementation

**Last Updated:** January 20, 2026

---

## Overview

This guide provides a step-by-step walkthrough to start implementing the Agent Builder Platform. Follow these steps to set up your development environment and begin Phase 1 implementation.

---

## Prerequisites

### Required Software

- **Python 3.11+**
- **Node.js 20+** and npm
- **PostgreSQL 15+** with pgvector extension
- **Redis 7+**
- **Docker & Docker Compose** (recommended for development)
- **Git**

### Accounts Needed

- OpenAI API key (for LLM and embeddings)
- Optional: Anthropic, Google Cloud (for multi-provider support)

---

## Step 1: Repository Setup

### Clone and Prepare

```bash
# Navigate to project
cd /home/anas/other-projs/enthusiast

# Create feature branch
git checkout -b feature/agent-builder-platform

# Review the documentation
ls docs/
# - AGENT_BUILDER_PLATFORM_ROADMAP.md        (Complete roadmap)
# - PHASE_1_IMPLEMENTATION_GUIDE.md          (Detailed Phase 1 steps)
# - ANALYTICS_INTEGRATION_GUIDE.md           (Analytics setup)
# - FRONTEND_ARCHITECTURE.md                  (React app guide)
# - QUICK_START_GUIDE.md                      (This file)
```

---

## Step 2: Backend Setup

### Install Dependencies

```bash
cd server

# Create/activate virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install existing requirements
pip install -r requirements.txt

# Install additional dependencies for Phase 1
pip install django-guardian django-filter drf-spectacular

# For analytics (Stage 2 evaluators)
pip install detoxify sentence-transformers langdetect
```

### Environment Configuration

```bash
# Copy sample env
cp sample.env .env

# Edit .env and add/update these variables
```

**Key environment variables to configure:**

```bash
# Database
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/enthusiast

# Redis
REDIS_URL=redis://localhost:6379/0

# OpenAI
OPENAI_API_KEY=sk-...

# Django
SECRET_KEY=your-secret-key-here
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# CORS (for frontend)
CORS_ALLOWED_ORIGINS=http://localhost:3000,http://localhost:5173

# Celery
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0

# Analytics
ANALYTICS_ENABLE_LOCAL_MODELS=true
ANALYTICS_ENABLE_LLM_JUDGES=true
ANALYTICS_LLM_SAMPLING_RATE=0.1  # 10% to save costs
```

### Database Setup

```bash
# Start PostgreSQL with pgvector (using Docker)
docker run -d \
  --name enthusiast-postgres \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_PASSWORD=postgres \
  -e POSTGRES_DB=enthusiast \
  -p 5432:5432 \
  pgvector/pgvector:pg15

# Or use docker-compose
docker-compose up -d db

# Run migrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser
```

### Start Development Server

```bash
# Terminal 1: Django server
python manage.py runserver

# Terminal 2: Celery worker
celery -A pecl worker -l info

# Terminal 3: Celery beat (scheduler)
celery -A pecl beat -l info

# Terminal 4 (optional): Redis
redis-server
```

**Verify setup:**
- Django admin: http://localhost:8000/admin/
- API docs: http://localhost:8000/api/docs/

---

## Step 3: Phase 1 - Multi-Tenancy Implementation

### Week 1-2: Create Workspace App

Follow the detailed steps in `PHASE_1_IMPLEMENTATION_GUIDE.md`, but here's the quick version:

```bash
# Create workspace app
cd server
python manage.py startapp workspace

# Create the models
# Copy the Workspace, WorkspaceMember, and WorkspaceInvitation models
# from PHASE_1_IMPLEMENTATION_GUIDE.md into server/workspace/models.py

# Add to INSTALLED_APPS in settings.py
# INSTALLED_APPS = [
#     ...
#     'workspace',
# ]

# Create migrations
python manage.py makemigrations workspace
python manage.py migrate workspace
```

### Add Workspace Foreign Keys to Existing Models

**Update these models to include workspace field:**

1. `server/agent/models/agent.py` - Add workspace FK
2. `server/agent/models/conversation.py` - Add workspace FK
3. `server/catalog/models.py` (DataSet) - Add workspace FK

```python
# Example for Agent model
from workspace.models import Workspace

class Agent(models.Model):
    workspace = models.ForeignKey(
        Workspace,
        on_delete=models.CASCADE,
        related_name='agents',
        null=True  # Temporarily nullable for migration
    )
    # ... rest of fields
```

```bash
# Generate migrations
python manage.py makemigrations agent catalog

# Create data migration to assign default workspace
python manage.py makemigrations --empty workspace --name assign_default_workspace

# Edit the migration file to populate workspace_id
# (See PHASE_1_IMPLEMENTATION_GUIDE.md for complete migration code)

# Run migrations
python manage.py migrate

# Make workspace non-nullable
# Remove null=True from models, then:
python manage.py makemigrations
python manage.py migrate
```

### Add Workspace Middleware

```bash
# Create server/workspace/middleware.py
# Copy the WorkspaceMiddleware code from PHASE_1_IMPLEMENTATION_GUIDE.md

# Add to MIDDLEWARE in settings.py
MIDDLEWARE = [
    # ... existing middleware
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'workspace.middleware.WorkspaceMiddleware',  # ADD THIS
    # ...
]
```

### Create Workspace API Endpoints

```bash
# Create files:
# - server/workspace/serializers.py
# - server/workspace/views.py
# - server/workspace/urls.py
# - server/workspace/permissions.py

# Add to main urls.py
# path('api/', include('workspace.urls')),
```

### Test Multi-Tenancy

```bash
# Run tests
python manage.py test workspace

# Manual testing
# 1. Create a workspace via API
curl -X POST http://localhost:8000/api/workspaces/ \
  -H "Authorization: Token YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name": "Test Workspace"}'

# 2. List workspaces
curl http://localhost:8000/api/workspaces/ \
  -H "Authorization: Token YOUR_TOKEN"

# 3. Create agent in workspace
curl -X POST http://localhost:8000/api/agents/ \
  -H "Authorization: Token YOUR_TOKEN" \
  -H "X-Workspace-ID: WORKSPACE_UUID" \
  -H "Content-Type: application/json" \
  -d '{"name": "My Agent", "config": {}}'
```

---

## Step 4: Frontend Setup

### Initialize React App

```bash
# From project root
cd frontend  # or create if doesn't exist

# If frontend doesn't exist, create it
npm create vite@latest frontend -- --template react-ts
cd frontend

# Install dependencies
npm install

# Install additional libraries
npm install @tanstack/react-query zustand axios
npm install react-router-dom
npm install recharts date-fns
npm install lucide-react

# Install UI components
npx shadcn-ui@latest init
npx shadcn-ui@latest add button card dialog form input label select tabs toast table

# Install dev dependencies
npm install -D @types/node
```

### Configure Project

Follow the structure and code examples from `FRONTEND_ARCHITECTURE.md`:

1. Create the folder structure
2. Set up API client with axios
3. Configure TanStack Query
4. Create Zustand stores (auth, workspace)
5. Set up routing

### Start Frontend Dev Server

```bash
cd frontend
npm run dev
```

**Access:** http://localhost:5173 (or http://localhost:3000)

---

## Step 5: Integrate Analytics (Phase 3)

This can be done later, but here's a quick overview:

### Create Analytics App

```bash
cd server
python manage.py startapp analytics

# Add to INSTALLED_APPS
```

### Port Metrics Models

Follow `ANALYTICS_INTEGRATION_GUIDE.md`:

1. Create analytics models (TurnMetric, SessionMetric, DailyMetric)
2. Port evaluators from chat-verifier
3. Create metrics service
4. Add Celery tasks for evaluation pipeline
5. Create analytics API endpoints

### Key Files to Create

```
server/analytics/
├── models/
│   ├── metrics.py          # Metric storage models
│   └── evaluation.py       # Evaluation job tracking
├── evaluators/
│   ├── registry.py         # Metrics registry
│   ├── rule_based.py       # Stage 1 evaluators
│   ├── local_ml.py         # Stage 2 evaluators
│   └── llm_judges.py       # Stage 3 evaluators
├── services/
│   └── metrics_service.py  # Business logic
├── tasks.py                 # Celery tasks
├── views.py                # API endpoints
└── urls.py                 # URL routing
```

---

## Step 6: Testing Your Implementation

### Backend Tests

```bash
# Run all tests
python manage.py test

# Run specific app tests
python manage.py test workspace
python manage.py test agent
python manage.py test analytics

# With coverage
pip install coverage
coverage run --source='.' manage.py test
coverage report
```

### Frontend Tests

```bash
cd frontend

# Unit tests
npm run test

# E2E tests (Playwright)
npx playwright install
npm run test:e2e
```

### Manual Testing Checklist

**Multi-Tenancy:**
- [ ] Create workspace
- [ ] Invite team member
- [ ] Switch between workspaces
- [ ] Verify data isolation (can't see other workspace's data)

**Agent Builder:**
- [ ] Create agent
- [ ] Configure agent (prompts, model, tools)
- [ ] Test agent in preview
- [ ] Publish agent

**Knowledge Base:**
- [ ] Upload documents
- [ ] View document chunks
- [ ] Search documents
- [ ] Delete documents

**Analytics:**
- [ ] View dashboard KPIs
- [ ] Check time series charts
- [ ] Drill down into conversations
- [ ] Export data

---

## Step 7: Development Workflow

### Git Workflow

```bash
# Work on features in branches
git checkout -b feature/workspace-management
# ... make changes
git add .
git commit -m "Add workspace management"
git push origin feature/workspace-management

# Create PR for review
```

### Code Quality

```bash
# Backend linting
pip install black flake8 mypy
black server/
flake8 server/
mypy server/

# Frontend linting
cd frontend
npm run lint
npm run type-check
npm run format
```

### Database Migrations

```bash
# Always create migrations for model changes
python manage.py makemigrations

# Review SQL before applying
python manage.py sqlmigrate app_name migration_number

# Apply migrations
python manage.py migrate

# Rollback if needed
python manage.py migrate app_name previous_migration_number
```

---

## Step 8: Deployment Preparation

### Development Environment (Docker Compose)

```yaml
# docker-compose.yml
version: '3.8'

services:
  db:
    image: pgvector/pgvector:pg15
    environment:
      POSTGRES_DB: enthusiast
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"

  backend:
    build: ./server
    command: python manage.py runserver 0.0.0.0:8000
    volumes:
      - ./server:/app
    ports:
      - "8000:8000"
    environment:
      DATABASE_URL: postgresql://postgres:postgres@db:5432/enthusiast
      REDIS_URL: redis://redis:6379/0
    depends_on:
      - db
      - redis

  celery_worker:
    build: ./server
    command: celery -A pecl worker -l info
    volumes:
      - ./server:/app
    environment:
      DATABASE_URL: postgresql://postgres:postgres@db:5432/enthusiast
      REDIS_URL: redis://redis:6379/0
    depends_on:
      - db
      - redis

  celery_beat:
    build: ./server
    command: celery -A pecl beat -l info
    volumes:
      - ./server:/app
    environment:
      DATABASE_URL: postgresql://postgres:postgres@db:5432/enthusiast
      REDIS_URL: redis://redis:6379/0
    depends_on:
      - redis

  frontend:
    build: ./frontend
    ports:
      - "3000:3000"
    volumes:
      - ./frontend:/app
      - /app/node_modules
    environment:
      VITE_API_BASE_URL: http://localhost:8000

volumes:
  postgres_data:
```

```bash
# Start everything
docker-compose up -d

# View logs
docker-compose logs -f

# Stop everything
docker-compose down
```

---

## Common Issues and Solutions

### Issue: pgvector extension not found

**Solution:**
```sql
-- Connect to PostgreSQL
psql -U postgres -d enthusiast

-- Enable extension
CREATE EXTENSION IF NOT EXISTS vector;
```

### Issue: Migrations conflict

**Solution:**
```bash
# Show migration status
python manage.py showmigrations

# If conflicting, merge migrations
python manage.py makemigrations --merge

# Or rollback and reapply
python manage.py migrate app_name zero
python manage.py migrate app_name
```

### Issue: Celery tasks not running

**Solution:**
```bash
# Check Redis connection
redis-cli ping

# Check Celery worker is running
celery -A pecl inspect active

# Restart worker
pkill -f "celery worker"
celery -A pecl worker -l info
```

### Issue: CORS errors in frontend

**Solution:**
```python
# In server/pecl/settings.py
CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://localhost:5173",
]

# Or for development only
CORS_ALLOW_ALL_ORIGINS = True  # NOT for production!
```

---

## Next Steps

After completing Phase 1:

1. **Week 1-2:** Complete multi-tenancy implementation
2. **Week 3-4:** Implement workspace management UI
3. **Month 2:** Build agent builder backend and UI
4. **Month 3:** Enhance knowledge base and add basic analytics

Refer to the complete roadmap in `AGENT_BUILDER_PLATFORM_ROADMAP.md` for detailed timeline and features.

---

## Resources

### Documentation

- Main roadmap: `AGENT_BUILDER_PLATFORM_ROADMAP.md`
- Phase 1 guide: `PHASE_1_IMPLEMENTATION_GUIDE.md`
- Analytics guide: `ANALYTICS_INTEGRATION_GUIDE.md`
- Frontend guide: `FRONTEND_ARCHITECTURE.md`

### External Resources

- Django docs: https://docs.djangoproject.com/
- DRF docs: https://www.django-rest-framework.org/
- LangChain docs: https://python.langchain.com/
- React docs: https://react.dev/
- TanStack Query: https://tanstack.com/query/

### Getting Help

If you get stuck:
1. Check the relevant guide document
2. Review Django/React documentation
3. Search GitHub issues in similar projects
4. Ask in Django/React community forums

---

## Success Criteria

You'll know Phase 1 is complete when:

- [ ] Users can create and switch between workspaces
- [ ] All data is properly isolated by workspace
- [ ] Team members can be invited with different roles
- [ ] Basic agent CRUD works with workspace scoping
- [ ] API endpoints properly enforce workspace permissions
- [ ] Frontend can display workspace selector
- [ ] Tests pass for multi-tenancy logic

Good luck with the implementation! 🚀
