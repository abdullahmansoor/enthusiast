"""
Tests for Agent Builder API (MVP).

Tests cover:
- Agent CRUD operations
- Config validation
- Publishing workflow
- Testing agents
- Getting conversations and stats
"""

from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status

from agent.models import Agent, Conversation, Message
from catalog.models import DataSet

User = get_user_model()


class AgentBuilderAPITestCase(TestCase):
    """Test cases for Agent Builder API"""

    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create_user(
            email='test@example.com',
            password='testpass123'
        )

        self.dataset = DataSet.objects.create(
            name='Test Dataset'
        )

        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

        self.agent_data = {
            'name': 'Test Agent',
            'description': 'A test agent for MVP',
            'dataset': self.dataset.id,
            'config': {
                'model': {
                    'provider': 'openai',
                    'name': 'gpt-4',
                    'temperature': 0.7,
                    'max_tokens': 2000
                },
                'system_prompt': 'You are a helpful assistant.',
                'retrieval': {
                    'enabled': True,
                    'top_k': 5
                },
                'conversation_starters': [
                    'How can I help you?'
                ]
            }
        }

    def test_create_agent(self):
        """Test creating a new agent"""
        response = self.client.post(
            '/api/agents-builder/',
            self.agent_data,
            format='json'
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['name'], 'Test Agent')
        self.assertEqual(response.data['status'], 'draft')
        self.assertEqual(response.data['version'], 1)

        # Verify created_by is set
        agent = Agent.objects.get(id=response.data['id'])
        self.assertEqual(agent.created_by, self.user)

    def test_create_agent_with_invalid_config(self):
        """Test creating agent with invalid config"""
        invalid_data = self.agent_data.copy()
        invalid_data['config'] = {
            'model': {
                'provider': 'openai',
                # Missing 'name' field
            },
            'system_prompt': 'Test'
        }

        response = self.client.post(
            '/api/agents-builder/',
            invalid_data,
            format='json'
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_list_agents(self):
        """Test listing agents"""
        # Create 2 agents
        Agent.objects.create(
            name='Agent 1',
            dataset=self.dataset,
            created_by=self.user
        )
        Agent.objects.create(
            name='Agent 2',
            dataset=self.dataset,
            created_by=self.user
        )

        response = self.client.get('/api/agents-builder/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 2)

    def test_get_agent_detail(self):
        """Test getting agent details"""
        agent = Agent.objects.create(
            name='Test Agent',
            dataset=self.dataset,
            created_by=self.user
        )

        response = self.client.get(f'/api/agents-builder/{agent.id}/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], 'Test Agent')
        self.assertIn('config', response.data)

    def test_update_agent(self):
        """Test updating an agent"""
        agent = Agent.objects.create(
            name='Old Name',
            dataset=self.dataset,
            created_by=self.user
        )

        update_data = {
            'name': 'New Name',
            'description': 'Updated description',
            'dataset': self.dataset.id,
            'config': agent.config
        }

        response = self.client.put(
            f'/api/agents-builder/{agent.id}/',
            update_data,
            format='json'
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], 'New Name')

        # Verify in database
        agent.refresh_from_db()
        self.assertEqual(agent.name, 'New Name')

    def test_delete_agent_soft_delete(self):
        """Test deleting an agent (soft delete)"""
        agent = Agent.objects.create(
            name='To Delete',
            dataset=self.dataset,
            created_by=self.user
        )

        response = self.client.delete(f'/api/agents-builder/{agent.id}/')

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        # Verify soft delete
        agent.refresh_from_db()
        self.assertIsNotNone(agent.deleted_at)
        self.assertEqual(agent.status, 'archived')

    def test_publish_agent(self):
        """Test publishing an agent"""
        agent = Agent.objects.create(
            name='Draft Agent',
            dataset=self.dataset,
            created_by=self.user,
            status='draft'
        )

        response = self.client.post(f'/api/agents-builder/{agent.id}/publish/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Verify published
        agent.refresh_from_db()
        self.assertEqual(agent.status, 'active')
        self.assertIsNotNone(agent.published_at)

    def test_publish_agent_without_system_prompt(self):
        """Test publishing agent without system prompt fails"""
        agent = Agent.objects.create(
            name='Invalid Agent',
            dataset=self.dataset,
            created_by=self.user
        )
        agent.config['system_prompt'] = ''
        agent.save()

        response = self.client.post(f'/api/agents-builder/{agent.id}/publish/')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_archive_agent(self):
        """Test archiving an agent"""
        agent = Agent.objects.create(
            name='Active Agent',
            dataset=self.dataset,
            created_by=self.user,
            status='active'
        )

        response = self.client.post(f'/api/agents-builder/{agent.id}/archive/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Verify archived
        agent.refresh_from_db()
        self.assertEqual(agent.status, 'archived')

    def test_get_agent_conversations(self):
        """Test getting conversations for an agent"""
        agent = Agent.objects.create(
            name='Test Agent',
            dataset=self.dataset,
            created_by=self.user
        )

        # Create some conversations
        for i in range(3):
            Conversation.objects.create(
                agent=agent,
                user=self.user,
                data_set=self.dataset
            )

        response = self.client.get(f'/api/agents-builder/{agent.id}/conversations/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 3)

    def test_get_agent_stats(self):
        """Test getting agent statistics"""
        agent = Agent.objects.create(
            name='Test Agent',
            dataset=self.dataset,
            created_by=self.user
        )

        # Create conversation with messages
        conversation = Conversation.objects.create(
            agent=agent,
            user=self.user,
            data_set=self.dataset
        )
        Message.objects.create(
            conversation=conversation,
            role='user',
            text='Test question'
        )
        Message.objects.create(
            conversation=conversation,
            role='assistant',
            text='Test response'
        )

        response = self.client.get(f'/api/agents-builder/{agent.id}/stats/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['total_conversations'], 1)
        self.assertEqual(response.data['total_messages'], 2)

    def test_duplicate_agent(self):
        """Test duplicating an agent"""
        agent = Agent.objects.create(
            name='Original Agent',
            description='Original description',
            dataset=self.dataset,
            created_by=self.user
        )

        response = self.client.post(
            f'/api/agents-builder/{agent.id}/duplicate/',
            {'name': 'Duplicated Agent'},
            format='json'
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['agent']['name'], 'Duplicated Agent')
        self.assertEqual(response.data['agent']['status'], 'draft')
        self.assertEqual(response.data['agent']['version'], 1)

        # Verify duplicate exists
        self.assertEqual(Agent.objects.filter(created_by=self.user).count(), 2)

    def test_agent_isolation_between_users(self):
        """Test that users can only see their own agents"""
        # Create another user
        other_user = User.objects.create_user(
            email='other@example.com',
            password='otherpass123'
        )

        # Create agent for current user
        my_agent = Agent.objects.create(
            name='My Agent',
            dataset=self.dataset,
            created_by=self.user
        )

        # Create agent for other user
        other_agent = Agent.objects.create(
            name='Other Agent',
            dataset=self.dataset,
            created_by=other_user
        )

        # Current user should only see their agent
        response = self.client.get('/api/agents-builder/')
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['results'][0]['name'], 'My Agent')

        # Current user should not be able to access other user's agent
        response = self.client.get(f'/api/agents-builder/{other_agent.id}/')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class AgentConfigValidationTestCase(TestCase):
    """Test cases for agent configuration validation"""

    def setUp(self):
        self.user = User.objects.create_user(
            email='test@example.com',
            password='testpass123'
        )
        self.dataset = DataSet.objects.create(name='Test Dataset')
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def test_temperature_validation(self):
        """Test that temperature is validated"""
        data = {
            'name': 'Test Agent',
            'dataset': self.dataset.id,
            'config': {
                'model': {
                    'provider': 'openai',
                    'name': 'gpt-4',
                    'temperature': 3.0  # Invalid: > 2
                },
                'system_prompt': 'Test'
            }
        }

        response = self.client.post('/api/agents-builder/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_top_k_validation(self):
        """Test that top_k is validated"""
        data = {
            'name': 'Test Agent',
            'dataset': self.dataset.id,
            'config': {
                'model': {
                    'provider': 'openai',
                    'name': 'gpt-4'
                },
                'system_prompt': 'Test',
                'retrieval': {
                    'top_k': 100  # Invalid: > 20
                }
            }
        }

        response = self.client.post('/api/agents-builder/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_config_merge_with_defaults(self):
        """Test that partial config is merged with defaults"""
        data = {
            'name': 'Test Agent',
            'dataset': self.dataset.id,
            'config': {
                'model': {
                    'provider': 'openai',
                    'name': 'gpt-3.5-turbo'
                },
                'system_prompt': 'Custom prompt'
                # Missing retrieval, conversation_starters, constraints
            }
        }

        response = self.client.post('/api/agents-builder/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Verify defaults were added
        agent = Agent.objects.get(id=response.data['id'])
        self.assertIn('retrieval', agent.config)
        self.assertIn('conversation_starters', agent.config)
        self.assertIn('constraints', agent.config)
