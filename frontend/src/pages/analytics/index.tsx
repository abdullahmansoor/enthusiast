import { useEffect, useState } from "react";
import { PageMain } from "@/components/util/page-main";
import { PageHeading } from "@/components/util/page-heading";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { KPISection } from "@/components/analytics/kpi-cards";
import { TimeSeriesSection } from "@/components/analytics/time-series-chart";
import { ConversationsSection } from "@/components/analytics/conversations-table";
import { BusinessInsightsSection } from "@/components/analytics/business-insights";
import { ApiClient } from "@/lib/api";
import { authenticationProviderInstance } from "@/lib/authentication-provider";
import { AnalyticsFilters } from "@/lib/api/analytics";

function formatDate(date: Date): string {
  return date.toISOString().split("T")[0];
}

function subtractDays(days: number): string {
  const d = new Date();
  d.setDate(d.getDate() - days);
  return formatDate(d);
}

type AgentOption = { id: number; name: string };

export function AnalyticsDashboardPage() {
  const today = formatDate(new Date());
  const [startDate, setStartDate] = useState<string>(subtractDays(30));
  const [endDate, setEndDate] = useState<string>(today);
  const [agentId, setAgentId] = useState<string>("all");
  const [agents, setAgents] = useState<AgentOption[]>([]);
  const [refreshKey, setRefreshKey] = useState(0);
  const [selectedDate, setSelectedDate] = useState<string | null>(null);

  // Load agents for filter dropdown
  useEffect(() => {
    const api = new ApiClient(authenticationProviderInstance);
    api.analytics().getAgentsForFilter().then(setAgents).catch(() => {});
  }, []);

  // Auto-refresh every 60 seconds
  useEffect(() => {
    const interval = setInterval(() => setRefreshKey((k) => k + 1), 60_000);
    return () => clearInterval(interval);
  }, []);

  // Clear drill-down when filters change
  useEffect(() => {
    setSelectedDate(null);
  }, [startDate, endDate, agentId]);

  const filters: AnalyticsFilters = {
    start_date: startDate || undefined,
    end_date: endDate || undefined,
    agent_id: agentId === "all" ? undefined : agentId,
  };

  function applyPreset(days: number) {
    setStartDate(subtractDays(days));
    setEndDate(today);
  }

  return (
    <PageMain>
      <PageHeading
        title="Analytics Dashboard"
        description="Monitor agent performance, quality metrics, and conversation insights."
      />

      {/* Filters */}
      <div className="mb-6 flex flex-wrap items-end gap-4">
        <div className="flex flex-col gap-1.5">
          <Label htmlFor="start-date">Start Date</Label>
          <Input
            id="start-date"
            type="date"
            value={startDate}
            onChange={(e) => setStartDate(e.target.value)}
            className="w-40"
          />
        </div>

        <div className="flex flex-col gap-1.5">
          <Label htmlFor="end-date">End Date</Label>
          <Input
            id="end-date"
            type="date"
            value={endDate}
            onChange={(e) => setEndDate(e.target.value)}
            className="w-40"
          />
        </div>

        <div className="flex flex-col gap-1.5">
          <Label>Agent</Label>
          <Select value={agentId} onValueChange={setAgentId}>
            <SelectTrigger className="w-52">
              <SelectValue placeholder="All agents" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All agents</SelectItem>
              {agents.map((a) => (
                <SelectItem key={a.id} value={String(a.id)}>
                  {a.name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        <div className="flex gap-2">
          <Button variant="outline" size="sm" onClick={() => applyPreset(7)}>
            Last 7d
          </Button>
          <Button variant="outline" size="sm" onClick={() => applyPreset(30)}>
            Last 30d
          </Button>
          <Button variant="outline" size="sm" onClick={() => applyPreset(90)}>
            Last 90d
          </Button>
        </div>

        <div className="ml-auto flex items-center gap-2 text-xs text-muted-foreground">
          <span className="inline-block w-1.5 h-1.5 rounded-full bg-green-500 animate-pulse" />
          Auto-refreshes every 60s
        </div>
      </div>

      <div className="space-y-8">
        <KPISection filters={filters} refreshKey={refreshKey} />
        <BusinessInsightsSection filters={filters} refreshKey={refreshKey} />
        <TimeSeriesSection
          filters={filters}
          refreshKey={refreshKey}
          selectedDate={selectedDate}
          onDateSelect={(d) => setSelectedDate(d || null)}
        />
        <ConversationsSection
          filters={filters}
          refreshKey={refreshKey}
          selectedDate={selectedDate}
          onClearDate={() => setSelectedDate(null)}
        />
      </div>
    </PageMain>
  );
}
