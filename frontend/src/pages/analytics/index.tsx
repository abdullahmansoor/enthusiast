import { useState } from "react";
import { PageMain } from "@/components/util/page-main";
import { PageHeading } from "@/components/util/page-heading";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { KPISection } from "@/components/analytics/kpi-cards";
import { TimeSeriesSection } from "@/components/analytics/time-series-chart";
import { ConversationsSection } from "@/components/analytics/conversations-table";
import { AnalyticsFilters } from "@/lib/api/analytics";

function formatDate(date: Date): string {
  return date.toISOString().split("T")[0];
}

function subtractDays(days: number): string {
  const d = new Date();
  d.setDate(d.getDate() - days);
  return formatDate(d);
}

export function AnalyticsDashboardPage() {
  const today = formatDate(new Date());
  const [startDate, setStartDate] = useState<string>(subtractDays(30));
  const [endDate, setEndDate] = useState<string>(today);
  const [agentId, setAgentId] = useState<string>("");

  const filters: AnalyticsFilters = {
    start_date: startDate || undefined,
    end_date: endDate || undefined,
    agent_id: agentId || undefined,
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
          <Label htmlFor="agent-id">Agent ID (optional)</Label>
          <Input
            id="agent-id"
            type="text"
            placeholder="All agents"
            value={agentId}
            onChange={(e) => setAgentId(e.target.value)}
            className="w-48"
          />
        </div>

        <div className="flex gap-2">
          <Button variant="outline" size="sm" onClick={() => applyPreset(7)}>
            Last 7 days
          </Button>
          <Button variant="outline" size="sm" onClick={() => applyPreset(30)}>
            Last 30 days
          </Button>
          <Button variant="outline" size="sm" onClick={() => applyPreset(90)}>
            Last 90 days
          </Button>
        </div>
      </div>

      <div className="space-y-8">
        <KPISection filters={filters} />
        <TimeSeriesSection filters={filters} />
        <ConversationsSection filters={filters} />
      </div>
    </PageMain>
  );
}
