# Frontend Architecture Guide
## Agent Builder Platform Dashboard

**Last Updated:** January 20, 2026

---

## Overview

This guide outlines the architecture for the React-based dashboard that will provide the visual agent builder interface and analytics dashboards for the Agent Builder Platform.

---

## Table of Contents

1. [Tech Stack](#tech-stack)
2. [Project Structure](#project-structure)
3. [State Management](#state-management)
4. [API Integration](#api-integration)
5. [Key Features](#key-features)
6. [Component Library](#component-library)
7. [Styling Guidelines](#styling-guidelines)
8. [Performance Optimization](#performance-optimization)

---

## Tech Stack

### Core Technologies

- **React 18.2+** - UI framework with concurrent features
- **TypeScript 5.0+** - Type safety
- **Vite** - Build tool and dev server
- **TanStack Query v5** - Server state management and caching
- **Zustand** - Client state management
- **React Router v6** - Routing
- **TailwindCSS** - Utility-first styling
- **Shadcn/ui** - Component primitives

### Additional Libraries

- **Recharts** - Analytics visualization
- **React Hook Form** - Form management
- **Zod** - Schema validation
- **Monaco Editor** - Code/prompt editing
- **React Flow** - Flow diagram builder
- **date-fns** - Date utilities
- **Axios** - HTTP client

---

## Project Structure

```
frontend/
├── public/
│   └── assets/
├── src/
│   ├── api/                    # API client and hooks
│   │   ├── client.ts          # Axios instance
│   │   ├── agents.ts          # Agent endpoints
│   │   ├── workspaces.ts      # Workspace endpoints
│   │   ├── analytics.ts       # Analytics endpoints
│   │   └── knowledge.ts       # Knowledge base endpoints
│   │
│   ├── components/            # Shared components
│   │   ├── ui/               # Shadcn components
│   │   ├── layouts/          # Layout components
│   │   ├── common/           # Common reusable components
│   │   └── icons/            # Icon components
│   │
│   ├── features/             # Feature-based modules
│   │   ├── auth/
│   │   │   ├── components/
│   │   │   ├── hooks/
│   │   │   └── pages/
│   │   ├── workspaces/
│   │   ├── agents/
│   │   │   ├── components/
│   │   │   │   ├── AgentBuilder/
│   │   │   │   ├── AgentList/
│   │   │   │   └── AgentPreview/
│   │   │   ├── hooks/
│   │   │   └── pages/
│   │   ├── analytics/
│   │   │   ├── components/
│   │   │   │   ├── Dashboard/
│   │   │   │   ├── Charts/
│   │   │   │   └── Metrics/
│   │   │   └── pages/
│   │   ├── knowledge/
│   │   └── conversations/
│   │
│   ├── hooks/                # Global hooks
│   │   ├── useAuth.ts
│   │   ├── useWorkspace.ts
│   │   └── usePermissions.ts
│   │
│   ├── stores/               # Zustand stores
│   │   ├── auth.ts
│   │   ├── workspace.ts
│   │   └── ui.ts
│   │
│   ├── types/                # TypeScript types
│   │   ├── api.ts
│   │   ├── models.ts
│   │   └── index.ts
│   │
│   ├── utils/                # Utility functions
│   │   ├── formatters.ts
│   │   ├── validators.ts
│   │   └── constants.ts
│   │
│   ├── App.tsx
│   ├── main.tsx
│   └── router.tsx
│
├── package.json
├── tsconfig.json
├── vite.config.ts
└── tailwind.config.js
```

---

## State Management

### Zustand for Client State

**File:** `src/stores/workspace.ts`
```typescript
import { create } from 'zustand'
import { persist } from 'zustand/middleware'

interface Workspace {
  id: string
  name: string
  slug: string
  plan: string
  myRole: string
}

interface WorkspaceStore {
  currentWorkspace: Workspace | null
  workspaces: Workspace[]

  setCurrentWorkspace: (workspace: Workspace) => void
  setWorkspaces: (workspaces: Workspace[]) => void
  clearWorkspace: () => void
}

export const useWorkspaceStore = create<WorkspaceStore>()(
  persist(
    (set) => ({
      currentWorkspace: null,
      workspaces: [],

      setCurrentWorkspace: (workspace) =>
        set({ currentWorkspace: workspace }),

      setWorkspaces: (workspaces) =>
        set({ workspaces }),

      clearWorkspace: () =>
        set({ currentWorkspace: null, workspaces: [] }),
    }),
    {
      name: 'workspace-storage',
    }
  )
)
```

**File:** `src/stores/auth.ts`
```typescript
import { create } from 'zustand'
import { persist } from 'zustand/middleware'

interface User {
  id: string
  email: string
  firstName: string
  lastName: string
}

interface AuthStore {
  user: User | null
  token: string | null

  setAuth: (user: User, token: string) => void
  clearAuth: () => void
  isAuthenticated: () => boolean
}

export const useAuthStore = create<AuthStore>()(
  persist(
    (set, get) => ({
      user: null,
      token: null,

      setAuth: (user, token) => set({ user, token }),
      clearAuth: () => set({ user: null, token: null }),
      isAuthenticated: () => !!get().token,
    }),
    {
      name: 'auth-storage',
    }
  )
)
```

### TanStack Query for Server State

**File:** `src/api/client.ts`
```typescript
import axios from 'axios'
import { useAuthStore } from '@/stores/auth'
import { useWorkspaceStore } from '@/stores/workspace'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

export const apiClient = axios.create({
  baseURL: `${API_BASE_URL}/api`,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Request interceptor - add auth token and workspace
apiClient.interceptors.request.use(
  (config) => {
    const token = useAuthStore.getState().token
    const workspace = useWorkspaceStore.getState().currentWorkspace

    if (token) {
      config.headers.Authorization = `Token ${token}`
    }

    if (workspace) {
      config.headers['X-Workspace-ID'] = workspace.id
    }

    return config
  },
  (error) => Promise.reject(error)
)

// Response interceptor - handle errors
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      // Clear auth and redirect to login
      useAuthStore.getState().clearAuth()
      window.location.href = '/login'
    }

    return Promise.reject(error)
  }
)
```

**File:** `src/api/agents.ts`
```typescript
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { apiClient } from './client'
import type { Agent, AgentConfig } from '@/types/models'

// Fetch agents
export const useAgents = () => {
  return useQuery({
    queryKey: ['agents'],
    queryFn: async () => {
      const { data } = await apiClient.get<Agent[]>('/agents/')
      return data
    },
  })
}

// Fetch single agent
export const useAgent = (agentId: string) => {
  return useQuery({
    queryKey: ['agents', agentId],
    queryFn: async () => {
      const { data } = await apiClient.get<Agent>(`/agents/${agentId}/`)
      return data
    },
    enabled: !!agentId,
  })
}

// Create agent
export const useCreateAgent = () => {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (agent: Partial<Agent>) => {
      const { data } = await apiClient.post<Agent>('/agents/', agent)
      return data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['agents'] })
    },
  })
}

// Update agent
export const useUpdateAgent = (agentId: string) => {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (agent: Partial<Agent>) => {
      const { data } = await apiClient.put<Agent>(`/agents/${agentId}/`, agent)
      return data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['agents', agentId] })
      queryClient.invalidateQueries({ queryKey: ['agents'] })
    },
  })
}

// Delete agent
export const useDeleteAgent = () => {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (agentId: string) => {
      await apiClient.delete(`/agents/${agentId}/`)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['agents'] })
    },
  })
}

// Test agent
export const useTestAgent = () => {
  return useMutation({
    mutationFn: async ({
      agentId,
      message,
    }: {
      agentId: string
      message: string
    }) => {
      const { data } = await apiClient.post(`/agents/${agentId}/test/`, {
        message,
      })
      return data
    },
  })
}
```

---

## Key Features

### 1. Agent Builder Interface

**File:** `src/features/agents/components/AgentBuilder/AgentBuilder.tsx`
```typescript
import { useState } from 'react'
import { useParams } from 'react-router-dom'
import { useAgent, useUpdateAgent } from '@/api/agents'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Button } from '@/components/ui/button'
import { toast } from '@/components/ui/use-toast'

import BasicInfoSection from './BasicInfoSection'
import SystemPromptSection from './SystemPromptSection'
import ModelConfigSection from './ModelConfigSection'
import ToolsSection from './ToolsSection'
import MemorySection from './MemorySection'
import RetrievalSection from './RetrievalSection'
import PreviewPanel from './PreviewPanel'

export default function AgentBuilder() {
  const { agentId } = useParams<{ agentId: string }>()
  const { data: agent, isLoading } = useAgent(agentId!)
  const updateAgent = useUpdateAgent(agentId!)

  const [localConfig, setLocalConfig] = useState(agent?.config)

  if (isLoading) {
    return <div>Loading...</div>
  }

  if (!agent) {
    return <div>Agent not found</div>
  }

  const handleSave = async () => {
    try {
      await updateAgent.mutateAsync({
        config: localConfig,
      })
      toast({
        title: 'Saved',
        description: 'Agent configuration updated successfully',
      })
    } catch (error) {
      toast({
        title: 'Error',
        description: 'Failed to save agent configuration',
        variant: 'destructive',
      })
    }
  }

  const handlePublish = async () => {
    try {
      await updateAgent.mutateAsync({
        status: 'active',
        config: localConfig,
      })
      toast({
        title: 'Published',
        description: 'Agent is now active',
      })
    } catch (error) {
      toast({
        title: 'Error',
        description: 'Failed to publish agent',
        variant: 'destructive',
      })
    }
  }

  return (
    <div className="h-screen flex">
      {/* Left Sidebar - Configuration */}
      <div className="w-96 border-r bg-gray-50 overflow-y-auto">
        <div className="p-6 space-y-6">
          <div className="flex items-center justify-between">
            <h2 className="text-2xl font-bold">{agent.name}</h2>
            <div className="space-x-2">
              <Button variant="outline" onClick={handleSave}>
                Save
              </Button>
              <Button onClick={handlePublish}>
                Publish
              </Button>
            </div>
          </div>

          <Tabs defaultValue="basic">
            <TabsList className="grid w-full grid-cols-3">
              <TabsTrigger value="basic">Basic</TabsTrigger>
              <TabsTrigger value="advanced">Advanced</TabsTrigger>
              <TabsTrigger value="tools">Tools</TabsTrigger>
            </TabsList>

            <TabsContent value="basic" className="space-y-4">
              <BasicInfoSection
                config={localConfig}
                onChange={setLocalConfig}
              />
              <SystemPromptSection
                config={localConfig}
                onChange={setLocalConfig}
              />
              <ModelConfigSection
                config={localConfig}
                onChange={setLocalConfig}
              />
            </TabsContent>

            <TabsContent value="advanced" className="space-y-4">
              <MemorySection
                config={localConfig}
                onChange={setLocalConfig}
              />
              <RetrievalSection
                config={localConfig}
                onChange={setLocalConfig}
              />
            </TabsContent>

            <TabsContent value="tools" className="space-y-4">
              <ToolsSection
                config={localConfig}
                onChange={setLocalConfig}
              />
            </TabsContent>
          </Tabs>
        </div>
      </div>

      {/* Main Content - Preview */}
      <div className="flex-1 flex flex-col">
        <PreviewPanel agent={agent} config={localConfig} />
      </div>
    </div>
  )
}
```

### 2. Analytics Dashboard

**File:** `src/features/analytics/components/Dashboard/AnalyticsDashboard.tsx`
```typescript
import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { apiClient } from '@/api/client'
import { DateRangePicker } from '@/components/ui/date-range-picker'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'

import KPICards from './KPICards'
import TimeSeriesChart from './TimeSeriesChart'
import DistributionChart from './DistributionChart'
import ConversationTable from './ConversationTable'

export default function AnalyticsDashboard() {
  const [dateRange, setDateRange] = useState({
    start: new Date(Date.now() - 7 * 24 * 60 * 60 * 1000), // 7 days ago
    end: new Date(),
  })

  const [selectedAgent, setSelectedAgent] = useState<string | null>(null)

  // Fetch KPIs
  const { data: kpis } = useQuery({
    queryKey: ['analytics', 'kpis', dateRange, selectedAgent],
    queryFn: async () => {
      const { data } = await apiClient.get('/analytics/overview/', {
        params: {
          start_date: dateRange.start.toISOString().split('T')[0],
          end_date: dateRange.end.toISOString().split('T')[0],
          agent_id: selectedAgent,
        },
      })
      return data
    },
  })

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold">Analytics Dashboard</h1>
        <DateRangePicker value={dateRange} onChange={setDateRange} />
      </div>

      {/* KPI Cards */}
      <KPICards data={kpis} />

      {/* Tabs */}
      <Tabs defaultValue="quality">
        <TabsList>
          <TabsTrigger value="quality">Quality</TabsTrigger>
          <TabsTrigger value="performance">Performance</TabsTrigger>
          <TabsTrigger value="business">Business</TabsTrigger>
          <TabsTrigger value="conversations">Conversations</TabsTrigger>
        </TabsList>

        <TabsContent value="quality" className="space-y-6">
          <div className="grid gap-6 md:grid-cols-2">
            <Card>
              <CardHeader>
                <CardTitle>Answer Relevance Trend</CardTitle>
              </CardHeader>
              <CardContent>
                <TimeSeriesChart
                  metricName="answer_relevance_mean"
                  dateRange={dateRange}
                  agentId={selectedAgent}
                />
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Faithfulness Trend</CardTitle>
              </CardHeader>
              <CardContent>
                <TimeSeriesChart
                  metricName="faithfulness_mean"
                  dateRange={dateRange}
                  agentId={selectedAgent}
                />
              </CardContent>
            </Card>
          </div>

          <Card>
            <CardHeader>
              <CardTitle>Quality Score Distribution</CardTitle>
            </CardHeader>
            <CardContent>
              <DistributionChart
                metricName="composite_quality"
                dateRange={dateRange}
                agentId={selectedAgent}
              />
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="performance" className="space-y-6">
          {/* Performance charts */}
        </TabsContent>

        <TabsContent value="business" className="space-y-6">
          {/* Business metrics */}
        </TabsContent>

        <TabsContent value="conversations">
          <ConversationTable
            dateRange={dateRange}
            agentId={selectedAgent}
          />
        </TabsContent>
      </Tabs>
    </div>
  )
}
```

### 3. Time Series Chart Component

**File:** `src/features/analytics/components/Charts/TimeSeriesChart.tsx`
```typescript
import { useQuery } from '@tanstack/react-query'
import { apiClient } from '@/api/client'
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts'
import { format } from 'date-fns'

interface TimeSeriesChartProps {
  metricName: string
  dateRange: { start: Date; end: Date }
  agentId?: string | null
}

export default function TimeSeriesChart({
  metricName,
  dateRange,
  agentId,
}: TimeSeriesChartProps) {
  const { data, isLoading } = useQuery({
    queryKey: ['analytics', 'timeseries', metricName, dateRange, agentId],
    queryFn: async () => {
      const { data } = await apiClient.get('/analytics/timeseries/', {
        params: {
          metric_name: metricName,
          start_date: dateRange.start.toISOString().split('T')[0],
          end_date: dateRange.end.toISOString().split('T')[0],
          agent_id: agentId,
        },
      })
      return data
    },
  })

  if (isLoading) {
    return <div className="h-64 flex items-center justify-center">Loading...</div>
  }

  if (!data || data.length === 0) {
    return (
      <div className="h-64 flex items-center justify-center text-gray-400">
        No data available
      </div>
    )
  }

  // Format data for recharts
  const chartData = data.map((d: any) => ({
    date: format(new Date(d.date), 'MMM dd'),
    value: d.value,
  }))

  return (
    <ResponsiveContainer width="100%" height={300}>
      <LineChart data={chartData}>
        <CartesianGrid strokeDasharray="3 3" />
        <XAxis dataKey="date" />
        <YAxis domain={[0, 1]} />
        <Tooltip />
        <Legend />
        <Line
          type="monotone"
          dataKey="value"
          stroke="#3b82f6"
          strokeWidth={2}
          dot={{ r: 4 }}
          activeDot={{ r: 6 }}
        />
      </LineChart>
    </ResponsiveContainer>
  )
}
```

---

## Component Library

### Core UI Components

Using Shadcn/ui as base:

```bash
npx shadcn-ui@latest init

# Install components
npx shadcn-ui@latest add button
npx shadcn-ui@latest add card
npx shadcn-ui@latest add dialog
npx shadcn-ui@latest add dropdown-menu
npx shadcn-ui@latest add form
npx shadcn-ui@latest add input
npx shadcn-ui@latest add label
npx shadcn-ui@latest add select
npx shadcn-ui@latest add tabs
npx shadcn-ui@latest add toast
npx shadcn-ui@latest add table
```

### Custom Components

**File:** `src/components/common/MetricCard.tsx`
```typescript
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { ArrowUpIcon, ArrowDownIcon } from 'lucide-react'

interface MetricCardProps {
  title: string
  value: string | number
  change?: number
  changeType?: 'increase' | 'decrease'
  format?: 'number' | 'percentage' | 'currency' | 'duration'
}

export default function MetricCard({
  title,
  value,
  change,
  changeType,
  format = 'number',
}: MetricCardProps) {
  const formatValue = (val: string | number) => {
    if (typeof val === 'string') return val

    switch (format) {
      case 'percentage':
        return `${(val * 100).toFixed(1)}%`
      case 'currency':
        return `$${val.toFixed(2)}`
      case 'duration':
        return `${val.toFixed(0)}ms`
      default:
        return val.toFixed(2)
    }
  }

  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-sm font-medium text-gray-600">
          {title}
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="text-2xl font-bold">{formatValue(value)}</div>
        {change !== undefined && (
          <div
            className={`text-sm flex items-center mt-1 ${
              changeType === 'increase' ? 'text-green-600' : 'text-red-600'
            }`}
          >
            {changeType === 'increase' ? (
              <ArrowUpIcon className="w-4 h-4 mr-1" />
            ) : (
              <ArrowDownIcon className="w-4 h-4 mr-1" />
            )}
            {Math.abs(change).toFixed(1)}% from last period
          </div>
        )}
      </CardContent>
    </Card>
  )
}
```

---

## Styling Guidelines

### TailwindCSS Configuration

**File:** `tailwind.config.js`
```javascript
/** @type {import('tailwindcss').Config} */
export default {
  darkMode: ['class'],
  content: [
    './pages/**/*.{ts,tsx}',
    './components/**/*.{ts,tsx}',
    './app/**/*.{ts,tsx}',
    './src/**/*.{ts,tsx}',
  ],
  theme: {
    extend: {
      colors: {
        border: 'hsl(var(--border))',
        input: 'hsl(var(--input))',
        ring: 'hsl(var(--ring))',
        background: 'hsl(var(--background))',
        foreground: 'hsl(var(--foreground))',
        primary: {
          DEFAULT: 'hsl(var(--primary))',
          foreground: 'hsl(var(--primary-foreground))',
        },
        secondary: {
          DEFAULT: 'hsl(var(--secondary))',
          foreground: 'hsl(var(--secondary-foreground))',
        },
        destructive: {
          DEFAULT: 'hsl(var(--destructive))',
          foreground: 'hsl(var(--destructive-foreground))',
        },
        muted: {
          DEFAULT: 'hsl(var(--muted))',
          foreground: 'hsl(var(--muted-foreground))',
        },
        accent: {
          DEFAULT: 'hsl(var(--accent))',
          foreground: 'hsl(var(--accent-foreground))',
        },
      },
      borderRadius: {
        lg: 'var(--radius)',
        md: 'calc(var(--radius) - 2px)',
        sm: 'calc(var(--radius) - 4px)',
      },
    },
  },
  plugins: [require('tailwindcss-animate')],
}
```

### Design Tokens

**File:** `src/styles/globals.css`
```css
@tailwind base;
@tailwind components;
@tailwind utilities;

@layer base {
  :root {
    --background: 0 0% 100%;
    --foreground: 222.2 84% 4.9%;

    --card: 0 0% 100%;
    --card-foreground: 222.2 84% 4.9%;

    --popover: 0 0% 100%;
    --popover-foreground: 222.2 84% 4.9%;

    --primary: 221.2 83.2% 53.3%;
    --primary-foreground: 210 40% 98%;

    --secondary: 210 40% 96.1%;
    --secondary-foreground: 222.2 47.4% 11.2%;

    --muted: 210 40% 96.1%;
    --muted-foreground: 215.4 16.3% 46.9%;

    --accent: 210 40% 96.1%;
    --accent-foreground: 222.2 47.4% 11.2%;

    --destructive: 0 84.2% 60.2%;
    --destructive-foreground: 210 40% 98%;

    --border: 214.3 31.8% 91.4%;
    --input: 214.3 31.8% 91.4%;
    --ring: 221.2 83.2% 53.3%;

    --radius: 0.5rem;
  }

  .dark {
    --background: 222.2 84% 4.9%;
    --foreground: 210 40% 98%;

    --card: 222.2 84% 4.9%;
    --card-foreground: 210 40% 98%;

    --popover: 222.2 84% 4.9%;
    --popover-foreground: 210 40% 98%;

    --primary: 217.2 91.2% 59.8%;
    --primary-foreground: 222.2 47.4% 11.2%;

    --secondary: 217.2 32.6% 17.5%;
    --secondary-foreground: 210 40% 98%;

    --muted: 217.2 32.6% 17.5%;
    --muted-foreground: 215 20.2% 65.1%;

    --accent: 217.2 32.6% 17.5%;
    --accent-foreground: 210 40% 98%;

    --destructive: 0 62.8% 30.6%;
    --destructive-foreground: 210 40% 98%;

    --border: 217.2 32.6% 17.5%;
    --input: 217.2 32.6% 17.5%;
    --ring: 224.3 76.3% 48%;
  }
}

@layer base {
  * {
    @apply border-border;
  }
  body {
    @apply bg-background text-foreground;
  }
}
```

---

## Performance Optimization

### Code Splitting

```typescript
// router.tsx
import { lazy, Suspense } from 'react'
import { createBrowserRouter } from 'react-router-dom'

const AgentBuilder = lazy(() => import('@/features/agents/pages/AgentBuilder'))
const AnalyticsDashboard = lazy(() => import('@/features/analytics/pages/Dashboard'))

export const router = createBrowserRouter([
  {
    path: '/agents/:agentId/edit',
    element: (
      <Suspense fallback={<div>Loading...</div>}>
        <AgentBuilder />
      </Suspense>
    ),
  },
  {
    path: '/analytics',
    element: (
      <Suspense fallback={<div>Loading...</div>}>
        <AnalyticsDashboard />
      </Suspense>
    ),
  },
])
```

### Query Optimization

```typescript
// Prefetch on hover
const prefetchAgent = (agentId: string) => {
  queryClient.prefetchQuery({
    queryKey: ['agents', agentId],
    queryFn: () => apiClient.get(`/agents/${agentId}/`).then(r => r.data),
  })
}

// Use in component
<Link
  to={`/agents/${agent.id}`}
  onMouseEnter={() => prefetchAgent(agent.id)}
>
  {agent.name}
</Link>
```

### Virtualization for Large Lists

```typescript
import { useVirtualizer } from '@tanstack/react-virtual'

function ConversationList({ conversations }: { conversations: Conversation[] }) {
  const parentRef = useRef<HTMLDivElement>(null)

  const virtualizer = useVirtualizer({
    count: conversations.length,
    getScrollElement: () => parentRef.current,
    estimateSize: () => 80,
  })

  return (
    <div ref={parentRef} className="h-[600px] overflow-auto">
      <div
        style={{
          height: `${virtualizer.getTotalSize()}px`,
          position: 'relative',
        }}
      >
        {virtualizer.getVirtualItems().map((virtualItem) => (
          <div
            key={virtualItem.key}
            style={{
              position: 'absolute',
              top: 0,
              left: 0,
              width: '100%',
              height: `${virtualItem.size}px`,
              transform: `translateY(${virtualItem.start}px)`,
            }}
          >
            <ConversationItem conversation={conversations[virtualItem.index]} />
          </div>
        ))}
      </div>
    </div>
  )
}
```

---

## Development Workflow

### Setup

```bash
# Install dependencies
cd frontend
npm install

# Start dev server
npm run dev

# Build for production
npm run build

# Preview production build
npm run preview
```

### Environment Variables

**File:** `frontend/.env.development`
```
VITE_API_BASE_URL=http://localhost:8000
VITE_WS_URL=ws://localhost:8000
```

**File:** `frontend/.env.production`
```
VITE_API_BASE_URL=https://api.yourdomain.com
VITE_WS_URL=wss://api.yourdomain.com
```

---

## Testing Strategy

### Unit Tests (Vitest)

```typescript
// __tests__/components/MetricCard.test.tsx
import { render, screen } from '@testing-library/react'
import MetricCard from '@/components/common/MetricCard'

describe('MetricCard', () => {
  it('renders metric value', () => {
    render(<MetricCard title="Answer Relevance" value={0.85} format="percentage" />)

    expect(screen.getByText('Answer Relevance')).toBeInTheDocument()
    expect(screen.getByText('85.0%')).toBeInTheDocument()
  })

  it('shows change indicator', () => {
    render(
      <MetricCard
        title="Conversations"
        value={1250}
        change={12.5}
        changeType="increase"
      />
    )

    expect(screen.getByText(/12.5%/)).toBeInTheDocument()
  })
})
```

### Integration Tests (Playwright)

```typescript
// e2e/agent-builder.spec.ts
import { test, expect } from '@playwright/test'

test('create and configure agent', async ({ page }) => {
  await page.goto('/agents')

  // Create agent
  await page.click('text=Create Agent')
  await page.fill('[name="name"]', 'Test Agent')
  await page.fill('[name="description"]', 'A test agent')
  await page.click('text=Create')

  // Configure agent
  await expect(page).toHaveURL(/\/agents\/.*\/edit/)
  await page.fill('[name="system_prompt"]', 'You are a helpful assistant')
  await page.click('text=Save')

  // Verify
  await expect(page.locator('text=Saved')).toBeVisible()
})
```

---

This frontend architecture provides a solid foundation for building a modern, performant React application with excellent developer experience and user experience.
