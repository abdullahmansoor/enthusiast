import {BaseApiClient} from "@/lib/api/base.ts";
import {
    Agent,
    AgentConfig,
    AgentDetails,
    AgentBuilderAgent,
    AgentBuilderListResponse,
    AgentBuilderConfig,
    AgentTestResponse
} from "@/lib/types.ts";
import {ApiError} from "@/lib/api-error.ts";

export type AgentChoice = {
  key: string;
  name: string;
  agent_args: Record<string, string>;
  prompt_inputs: Record<string, string>;
  prompt_extension: Record<string, string>;
  tools: Record<string, string>[];
};

type AvailableAgentsResponse = {
  choices: AgentChoice[];
};

export class AgentsApiClient extends BaseApiClient {
    async getAvailableAgentTypes(): Promise<AgentChoice[]> {
        const response = await fetch(`${this.apiBase}/api/agents/types/`, this._requestConfiguration());

        if (!response.ok) {
            throw new Error(`Failed to fetch available agents: ${response.statusText}`);
        }

        const result = await response.json() as AvailableAgentsResponse;
        return result.choices;
    }
    async getDatasetAvailableAgents(dataSetId: number): Promise<Agent[]> {
        const query = new URLSearchParams({ dataset: dataSetId.toString() });
        const response = await fetch(
            `${this.apiBase}/api/agents/?${query.toString()}`,
            this._requestConfiguration()
        );

        if (!response.ok) {
            throw new Error(`Failed to fetch available agents: ${response.statusText}`);
        }

        return await response.json() as Agent[];
    }
    async getAgentById(agentId: number): Promise<AgentDetails> {
        const response = await fetch(`${this.apiBase}/api/agents/${agentId}/`, this._requestConfiguration());
        if (!response.ok) {
            throw new Error(`Failed to fetch agent: ${response.statusText}`);
        }
        return await response.json() as AgentDetails;
    }

    async createAgent(data: { name: string; agent_type: string; dataset: number; config: AgentConfig }): Promise<AgentDetails> {
        const response = await fetch(`${this.apiBase}/api/agents/`, {
            ...this._requestConfiguration(),
            method: 'POST',
            body: JSON.stringify(data),
        });
        if (!response.ok) {
            const errorData = await response.json().catch(() => ({}));
            throw new ApiError(`Failed to create agent: ${response.statusText}`, {
                data: errorData,
                status: response.status
            });
        }
        return await response.json() as AgentDetails;
    }

    async updateAgent(agentId: number, data: { name: string; agent_type: string; dataset: number; config: AgentConfig }): Promise<AgentDetails> {
        const response = await fetch(`${this.apiBase}/api/agents/${agentId}/`, {
            ...this._requestConfiguration(),
            method: 'PUT',
            body: JSON.stringify(data),
        });
        if (!response.ok) {
            const errorData = await response.json().catch(() => ({}));
            throw new ApiError(`Failed to update agent: ${response.statusText}`, {
                data: errorData,
                status: response.status
            });
        }
        return await response.json() as AgentDetails;

    }

    async deleteAgent(agentId: number): Promise<void> {
        const response = await fetch(`${this.apiBase}/api/agents/${agentId}/`, {
            ...this._requestConfiguration(),
            method: 'DELETE',
        });
        if (!response.ok) {
            const errorData = await response.json().catch(() => ({}));
            throw new ApiError(`Failed to delete agent: ${response.statusText}`, {
                data: errorData,
                status: response.status
            });
        }
    }

    // ==========================================
    // Agent Builder API Methods (MVP System)
    // ==========================================

    /**
     * List all agents created by the current user
     */
    async listBuilderAgents(params?: {
        status?: 'draft' | 'published' | 'archived';
        page?: number;
        page_size?: number;
    }): Promise<AgentBuilderListResponse> {
        const query = new URLSearchParams();
        if (params?.status) query.set('status', params.status);
        if (params?.page) query.set('page', params.page.toString());
        if (params?.page_size) query.set('page_size', params.page_size.toString());

        const response = await fetch(
            `${this.apiBase}/api/agents-builder/?${query.toString()}`,
            this._requestConfiguration()
        );

        if (!response.ok) {
            throw new ApiError(`Failed to fetch builder agents: ${response.statusText}`, {
                data: null,
                status: response.status
            });
        }

        return await response.json() as AgentBuilderListResponse;
    }

    /**
     * Get a specific agent by ID
     */
    async getBuilderAgent(agentId: string): Promise<AgentBuilderAgent> {
        const response = await fetch(
            `${this.apiBase}/api/agents-builder/${agentId}/`,
            this._requestConfiguration()
        );

        if (!response.ok) {
            throw new ApiError(`Failed to fetch agent: ${response.statusText}`, {
                data: null,
                status: response.status
            });
        }

        return await response.json() as AgentBuilderAgent;
    }

    /**
     * Create a new agent
     */
    async createBuilderAgent(data: {
        name: string;
        description?: string;
        dataset: number;
        config?: Partial<AgentBuilderConfig>;
    }): Promise<AgentBuilderAgent> {
        const response = await fetch(`${this.apiBase}/api/agents-builder/`, {
            ...this._requestConfiguration(),
            method: 'POST',
            body: JSON.stringify(data),
        });

        if (!response.ok) {
            const errorData = await response.json().catch(() => ({}));
            throw new ApiError(`Failed to create agent: ${response.statusText}`, {
                data: errorData,
                status: response.status
            });
        }

        return await response.json() as AgentBuilderAgent;
    }

    /**
     * Update an existing agent
     */
    async updateBuilderAgent(
        agentId: string,
        data: {
            name?: string;
            description?: string;
            config?: AgentBuilderConfig;
        }
    ): Promise<AgentBuilderAgent> {
        const response = await fetch(`${this.apiBase}/api/agents-builder/${agentId}/`, {
            ...this._requestConfiguration(),
            method: 'PATCH',
            body: JSON.stringify(data),
        });

        if (!response.ok) {
            const errorData = await response.json().catch(() => ({}));
            throw new ApiError(`Failed to update agent: ${response.statusText}`, {
                data: errorData,
                status: response.status
            });
        }

        return await response.json() as AgentBuilderAgent;
    }

    /**
     * Delete an agent (soft delete)
     */
    async deleteBuilderAgent(agentId: string): Promise<void> {
        const response = await fetch(`${this.apiBase}/api/agents-builder/${agentId}/`, {
            ...this._requestConfiguration(),
            method: 'DELETE',
        });

        if (!response.ok) {
            const errorData = await response.json().catch(() => ({}));
            throw new ApiError(`Failed to delete agent: ${response.statusText}`, {
                data: errorData,
                status: response.status
            });
        }
    }

    /**
     * Publish an agent (make it available for use)
     */
    async publishBuilderAgent(agentId: string): Promise<AgentBuilderAgent> {
        const response = await fetch(`${this.apiBase}/api/agents-builder/${agentId}/publish/`, {
            ...this._requestConfiguration(),
            method: 'POST',
        });

        if (!response.ok) {
            const errorData = await response.json().catch(() => ({}));
            throw new ApiError(`Failed to publish agent: ${response.statusText}`, {
                data: errorData,
                status: response.status
            });
        }

        return await response.json() as AgentBuilderAgent;
    }

    /**
     * Clone an agent
     */
    async cloneBuilderAgent(agentId: string, name?: string): Promise<AgentBuilderAgent> {
        const response = await fetch(`${this.apiBase}/api/agents-builder/${agentId}/clone/`, {
            ...this._requestConfiguration(),
            method: 'POST',
            body: JSON.stringify({ name }),
        });

        if (!response.ok) {
            const errorData = await response.json().catch(() => ({}));
            throw new ApiError(`Failed to clone agent: ${response.statusText}`, {
                data: errorData,
                status: response.status
            });
        }

        return await response.json() as AgentBuilderAgent;
    }

    /**
     * Test an agent with a sample message
     */
    async testBuilderAgent(agentId: string, message: string): Promise<AgentTestResponse> {
        const response = await fetch(`${this.apiBase}/api/agents-builder/${agentId}/test/`, {
            ...this._requestConfiguration(),
            method: 'POST',
            body: JSON.stringify({ message }),
        });

        if (!response.ok) {
            const errorData = await response.json().catch(() => ({}));
            throw new ApiError(`Failed to test agent: ${response.statusText}`, {
                data: errorData,
                status: response.status
            });
        }

        return await response.json() as AgentTestResponse;
    }

    /**
     * Get version history for an agent
     */
    async getBuilderAgentVersions(agentId: string): Promise<AgentBuilderAgent[]> {
        const response = await fetch(
            `${this.apiBase}/api/agents-builder/${agentId}/versions/`,
            this._requestConfiguration()
        );

        if (!response.ok) {
            throw new ApiError(`Failed to fetch agent versions: ${response.statusText}`, {
                data: null,
                status: response.status
            });
        }

        return await response.json() as AgentBuilderAgent[];
    }
}
