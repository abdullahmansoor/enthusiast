import { BaseApiClient } from "@/lib/api/base";
import {
  KPIData,
  TimeSeriesData,
  DistributionData,
  ConversationListData,
  SessionDetail,
  MetricDefinition,
} from "@/lib/types";

export type AnalyticsFilters = {
  start_date?: string;
  end_date?: string;
  agent_id?: string;
};

export class AnalyticsApiClient extends BaseApiClient {
  private buildQuery(params: Record<string, string | undefined>): string {
    const q = new URLSearchParams();
    for (const [k, v] of Object.entries(params)) {
      if (v !== undefined && v !== "") q.set(k, v);
    }
    return q.toString();
  }

  async getOverview(filters: AnalyticsFilters = {}): Promise<KPIData> {
    const qs = this.buildQuery({
      start_date: filters.start_date,
      end_date: filters.end_date,
      agent_id: filters.agent_id,
    });
    const response = await fetch(
      `${this.apiBase}/api/analytics/overview/?${qs}`,
      this._requestConfiguration()
    );
    if (!response.ok) throw new Error(`Analytics overview failed: ${response.statusText}`);
    return response.json() as Promise<KPIData>;
  }

  async getTimeSeries(
    metric_name: string,
    filters: AnalyticsFilters & { granularity?: "daily" | "weekly" } = {}
  ): Promise<TimeSeriesData> {
    const qs = this.buildQuery({
      metric_name,
      start_date: filters.start_date,
      end_date: filters.end_date,
      agent_id: filters.agent_id,
      granularity: filters.granularity,
    });
    const response = await fetch(
      `${this.apiBase}/api/analytics/timeseries/?${qs}`,
      this._requestConfiguration()
    );
    if (!response.ok) throw new Error(`Time series failed: ${response.statusText}`);
    return response.json() as Promise<TimeSeriesData>;
  }

  async getDistribution(metric_name: string, filters: AnalyticsFilters = {}): Promise<DistributionData> {
    const qs = this.buildQuery({
      metric_name,
      start_date: filters.start_date,
      end_date: filters.end_date,
      agent_id: filters.agent_id,
    });
    const response = await fetch(
      `${this.apiBase}/api/analytics/distribution/?${qs}`,
      this._requestConfiguration()
    );
    if (!response.ok) throw new Error(`Distribution failed: ${response.statusText}`);
    return response.json() as Promise<DistributionData>;
  }

  async getConversations(
    filters: AnalyticsFilters & { page?: number; page_size?: number; sort_by?: string } = {}
  ): Promise<ConversationListData> {
    const qs = this.buildQuery({
      start_date: filters.start_date,
      end_date: filters.end_date,
      agent_id: filters.agent_id,
      page: filters.page?.toString(),
      page_size: filters.page_size?.toString(),
      sort_by: filters.sort_by,
    });
    const response = await fetch(
      `${this.apiBase}/api/analytics/conversations/?${qs}`,
      this._requestConfiguration()
    );
    if (!response.ok) throw new Error(`Conversations failed: ${response.statusText}`);
    return response.json() as Promise<ConversationListData>;
  }

  async getConversationDetail(conversationId: string): Promise<SessionDetail> {
    const response = await fetch(
      `${this.apiBase}/api/analytics/${conversationId}/detail/`,
      this._requestConfiguration()
    );
    if (!response.ok) throw new Error(`Session detail failed: ${response.statusText}`);
    return response.json() as Promise<SessionDetail>;
  }

  async getMetricsCatalog(filters: { level?: string; stage?: number } = {}): Promise<MetricDefinition[]> {
    const qs = this.buildQuery({
      level: filters.level,
      stage: filters.stage?.toString(),
    });
    const response = await fetch(
      `${this.apiBase}/api/analytics/metrics/?${qs}`,
      this._requestConfiguration()
    );
    if (!response.ok) throw new Error(`Metrics catalog failed: ${response.statusText}`);
    return response.json() as Promise<MetricDefinition[]>;
  }

  async getAgentsForFilter(): Promise<{ id: number; name: string }[]> {
    const response = await fetch(
      `${this.apiBase}/api/agents-builder/`,
      this._requestConfiguration()
    );
    if (!response.ok) return [];
    const data = await response.json();
    return Array.isArray(data) ? data : (data.results ?? []);
  }
}
