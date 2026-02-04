export interface PaginatedResult<T> {
  results: T[];
  count: number;
}

export type DataSet = {
  id: number | undefined;
  name: string;
  languageModelProvider: string;
  languageModel: string;
  embeddingProvider: string;
  embeddingModel: string;
  embeddingVectorSize: number;
  systemMessage: string;
}

export type Product = {
  id: number;
  name: string;
  sku: string;
  slug: string;
  description: string;
  categories: string;
  properties: string;
}

export type CatalogSource = {
  id: number;
  plugin_name: string;
  config: string;
  data_set_id: number;
  corrupted: boolean;
}

export type Document = {
  id: number;
  url: string;
  title: string;
  content: string;
  isIndexed: boolean;
}

export type Account = {
  email: string;
  isStaff: boolean;
}

export type User = {
  id: number;
  email: string;
  isActive: boolean;
  isStaff: boolean;
}

export type SourcePlugin = {
  name: string;
  configuration_args: Record<string, ExtraArgDetail>;
};

export type Agent = {
  id: number;
  name: string;
  agent_type: string;
  created_at: string;
  updated_at: string;
  deleted_at: string;
  corrupted: boolean;
};

export type Conversation = {
  id: number;
  started_at: Date;
  model: string;
  dimensions: number;
  data_set: string;
  summary?: string;
  agent: Agent;
  history?: Message[];
}

export type Message = {
  id: number;
  role: string;
  text: string;
}

export type ServiceAccount = {
  id: number;
  email: string;
  isActive: boolean;
  dateCreated: string;
  dataSetIds: number[];
};

export type ProvidersConfig = {
  languageModelProviders: string[];
  embeddingProviders: string[];
}

export type TypeInfo = {
  container: string | null;
  inner_type?: string;
  key_type?: string;
  value_type?: string;
  nullable?: boolean;
};

export type ExtraArgDetail = {
  type: TypeInfo;
  description?: string | null;
  title?: string | null;
};

export type AgentConfig = {
  agent_args?: Record<string, ExtraArgDetail>;
  prompt_input?: Record<string, ExtraArgDetail>;
  prompt_extension?: Record<string, ExtraArgDetail>;
  tools?: Array<Record<string, ExtraArgDetail>>;
};

export type AgentDetails = {
  id: number;
  name: string;
  description: string;
  config: AgentConfig;
  dataset: number;
  agent_type: string;
  created_at: string;
  updated_at: string;
};

// Agent Builder Types (New MVP System)
export type AgentBuilderModelConfig = {
  provider: string;
  name: string;
  temperature?: number;
  max_tokens?: number;
  top_p?: number;
};

export type AgentBuilderRetrievalConfig = {
  enabled: boolean;
  top_k?: number;
  similarity_threshold?: number;
  reranking_enabled?: boolean;
};

export type AgentBuilderConfig = {
  model: AgentBuilderModelConfig;
  system_prompt: string;
  retrieval: AgentBuilderRetrievalConfig;
  max_history_messages?: number;
  enable_citations?: boolean;
  custom_settings?: Record<string, any>;
};

export type AgentBuilderAgent = {
  id: string; // UUID
  name: string;
  description: string;
  dataset: number;
  dataset_name?: string;
  config: AgentBuilderConfig;
  version: number;
  status: 'draft' | 'published' | 'archived';
  created_by: number;
  created_at: string;
  updated_at: string;
  published_at: string | null;
  deleted_at: string | null;
};

export type AgentBuilderListItem = {
  id: string;
  name: string;
  description: string;
  status: 'draft' | 'published' | 'archived';
  version: number;
  created_at: string;
  updated_at: string;
  published_at: string | null;
};

export type AgentBuilderListResponse = {
  count: number;
  next: string | null;
  previous: string | null;
  results: AgentBuilderListItem[];
};

export type AgentTestRequest = {
  message: string;
};

export type AgentTestResponse = {
  response: string;
  conversation_id: string;
  message_id: number;
  metadata: {
    model_used?: string;
    retrieved_context?: any[];
    processing_time?: number;
  };
};
