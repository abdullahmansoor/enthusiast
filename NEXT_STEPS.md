# Next Steps After Dependency Installation

Once you've installed the dependencies with `pip install -r server/requirements.txt`, follow these steps:

---

## Step 1: Add Analytics to Django Settings

**File:** `server/pecl/settings.py`

### Add to INSTALLED_APPS:
```python
INSTALLED_APPS = [
    # ... existing apps
    'agent',
    'catalog',
    'account',
    'sync',
    'analytics',  # ADD THIS
]
```

### Add Analytics Configuration (at the end of file):
```python
# Analytics Configuration
ANALYTICS_CONFIG = {
    # Enable local ML models (Stage 2: toxicity, coherence)
    'enable_local_models': True,

    # Enable LLM judges (Stage 3: relevance, faithfulness)
    'enable_llm_judges': True,

    # Sampling rate for LLM judges (0.1 = 10% to save costs)
    'llm_sampling_rate': 0.1,

    # Run evaluations asynchronously (don't block API responses)
    'async_evaluation': True,
}
```

---

## Step 2: Create and Run Migrations

```bash
cd server

# Activate virtual environment
source ../venv/bin/activate

# Create migrations for enhanced Agent model
python manage.py makemigrations agent --name enhance_agent_model_for_mvp

# Create migrations for Analytics app
python manage.py makemigrations analytics --name initial_analytics_models

# Review migrations (optional but recommended)
python manage.py sqlmigrate agent 0XXX  # Replace XXX with migration number
python manage.py sqlmigrate analytics 0001

# Run migrations
python manage.py migrate
```

---

## Step 3: Verify Analytics Setup

```bash
python manage.py shell
```

```python
# Test 1: Check metrics are registered
from analytics.evaluators import registry

print(f"Registered metrics: {len(registry)}")
print(f"Metric names: {registry.list_names()}")

# Expected output: Should show ~9 metrics
# ['pii_flag', 'response_length', 'response_words', 'toxicity',
#  'coherence', 'repetition', 'answer_relevance', 'faithfulness',
#  'composite_quality']

# Test 2: Check models are accessible
from analytics.models import TurnMetric, SessionMetric, DailyMetric, EvaluationJob

print("Analytics models loaded successfully!")

# Test 3: Check Agent model enhancements
from agent.models import Agent

default_config = Agent.get_default_config()
print(f"Default config keys: {list(default_config.keys())}")

# Expected: ['model', 'system_prompt', 'retrieval',
#            'conversation_starters', 'constraints']
```

---

## Step 4: Test Simple Metric Computation (Optional)

```python
from analytics.evaluators.rule_based import compute_pii_flag, compute_response_length

# Test PII detection
test_data = {
    'assistant_text': 'My email is test@example.com and phone is 555-123-4567'
}

pii_score = compute_pii_flag(test_data)
print(f"PII detected: {pii_score}")  # Should be 1.0

# Test response length
test_data2 = {
    'assistant_text': 'This is a test response'
}

length = compute_response_length(test_data2)
print(f"Response length: {length} characters")
```

---

## Step 5: Create a Test Agent (Optional)

```python
from agent.models import Agent
from catalog.models import DataSet
from django.contrib.auth import get_user_model

User = get_user_model()

# Get or create a user and dataset
user = User.objects.first()
dataset = DataSet.objects.first()

# Create an agent with default config
agent = Agent.objects.create(
    name="Test MVP Agent",
    description="Testing the enhanced agent model",
    dataset=dataset,
    created_by=user,
    status=Agent.STATUS_DRAFT
)

print(f"Created agent: {agent}")
print(f"Config: {agent.config}")

# Publish the agent
agent.publish()
print(f"Agent status: {agent.status}")
print(f"Published at: {agent.published_at}")
```

---

## Step 6: Check for Migration Issues

If you encounter issues with migrations, here are common solutions:

### Issue: "No changes detected"
```bash
# Make sure analytics is in INSTALLED_APPS
python manage.py showmigrations analytics

# Force create migrations
python manage.py makemigrations analytics --empty --name initial
```

### Issue: "Table already exists"
```bash
# Check existing tables
python manage.py dbshell
\dt analytics_*

# If tables exist, fake the migration
python manage.py migrate analytics --fake-initial
```

### Issue: "Cannot add field with UUID default"
```python
# In the migration file, you may need to use:
# default=uuid.uuid4 instead of default=uuid.uuid4()
```

---

## Step 7: Run Django Development Server

```bash
# Terminal 1: Start Redis (if not running)
redis-server

# Terminal 2: Start Django
python manage.py runserver

# Terminal 3: Start Celery worker (for async evaluation)
celery -A pecl worker -l info

# Terminal 4: Start Celery beat (for scheduled tasks)
celery -A pecl beat -l info
```

---

## What's Working Now

After these steps, you'll have:

✅ Enhanced Agent model with versioning and flexible config
✅ Analytics app with metrics models
✅ Three-stage evaluation pipeline (rule-based, ML, LLM judges)
✅ Metrics registry with 9+ metrics
✅ Database tables for storing metrics
✅ Backward compatibility with existing agents

---

## What to Build Next (Week 2)

Once this is set up, we'll build:

1. **Agent Builder API endpoints**
   - POST /api/agents/{id}/publish/
   - POST /api/agents/{id}/test/
   - GET /api/agents/{id}/conversations/

2. **Agent serializers with config validation**

3. **API tests**

4. **Updated API documentation**

---

## Need Help?

If you run into issues:

1. Check that all dependencies are installed:
   ```bash
   pip list | grep -E "(django|celery|langchain|openai|detoxify|sentence)"
   ```

2. Check Django can import analytics:
   ```bash
   python manage.py check analytics
   ```

3. Review the migration files:
   ```bash
   cat server/agent/migrations/*_enhance_agent_model_for_mvp.py
   cat server/analytics/migrations/0001_initial_analytics_models.py
   ```

4. Check the commit for reference:
   ```bash
   git show aabd827
   ```

---

## Summary

**Current Branch:** `feature/mvp-agent-builder-analytics`
**Last Commit:** `aabd827` - MVP Week 1: Foundation
**Progress:** Week 1 implementation complete
**Next:** Configure settings, run migrations, then start Week 2

We've built a solid foundation with enhanced models, a flexible metrics system, and a three-stage evaluation pipeline. Ready to build the API!
