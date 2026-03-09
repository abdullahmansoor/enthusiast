import { useEffect, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { ApiClient } from "@/lib/api";
import { authenticationProviderInstance } from "@/lib/authentication-provider";
import { KPIData } from "@/lib/types";
import { AnalyticsFilters } from "@/lib/api/analytics";

interface KPICardProps {
  title: string;
  value: number | null;
  prevValue?: number | null;
  format?: "percent" | "raw" | "seconds";
  direction?: "good" | "bad";
  subtitle?: string;
}

function formatValue(value: number | null, format: KPICardProps["format"]): string {
  if (value === null) return "—";
  switch (format) {
    case "percent":
      return `${(value * 100).toFixed(1)}%`;
    case "raw":
      return value.toLocaleString(undefined, { maximumFractionDigits: 1 });
    case "seconds":
      return `${value.toFixed(1)}s`;
    default:
      return `${(value * 100).toFixed(1)}%`;
  }
}

function getColorClass(value: number | null, direction: KPICardProps["direction"] = "good"): string {
  if (value === null) return "text-muted-foreground";
  if (direction === "good") {
    if (value >= 0.7) return "text-green-600 dark:text-green-400";
    if (value >= 0.4) return "text-yellow-600 dark:text-yellow-400";
    return "text-red-600 dark:text-red-400";
  } else {
    if (value <= 0.1) return "text-green-600 dark:text-green-400";
    if (value <= 0.3) return "text-yellow-600 dark:text-yellow-400";
    return "text-red-600 dark:text-red-400";
  }
}

function TrendBadge({
  value,
  prevValue,
  direction = "good",
  format = "percent",
}: {
  value: number | null;
  prevValue: number | null | undefined;
  direction?: "good" | "bad";
  format?: KPICardProps["format"];
}) {
  if (value === null || prevValue === null || prevValue === undefined || prevValue === 0) return null;
  const delta = value - prevValue;
  if (Math.abs(delta) < 0.001) return null;
  const isUp = delta > 0;
  const isGood = direction === "good" ? isUp : !isUp;
  const displayDelta =
    format === "raw" || format === "seconds"
      ? Math.abs(delta).toFixed(1)
      : `${Math.abs(delta * 100).toFixed(1)}%`;
  return (
    <span
      className={`inline-flex items-center gap-0.5 text-xs font-medium ${
        isGood ? "text-green-600 dark:text-green-400" : "text-red-600 dark:text-red-400"
      }`}
    >
      {isUp ? "▲" : "▼"} {displayDelta}
    </span>
  );
}

function KPICard({ title, value, prevValue, format = "percent", direction = "good", subtitle }: KPICardProps) {
  const colorClass = getColorClass(value, direction);
  return (
    <Card>
      <CardHeader className="pb-1">
        <CardTitle className="text-xs font-medium text-muted-foreground leading-snug">{title}</CardTitle>
      </CardHeader>
      <CardContent className="pt-0">
        <p className={`text-2xl font-bold ${colorClass}`}>{formatValue(value, format)}</p>
        <div className="flex items-center gap-2 mt-0.5">
          {subtitle && <p className="text-xs text-muted-foreground">{subtitle}</p>}
          <TrendBadge value={value} prevValue={prevValue} direction={direction} format={format} />
        </div>
      </CardContent>
    </Card>
  );
}

function KPICardSkeleton() {
  return (
    <Card>
      <CardHeader className="pb-1">
        <Skeleton className="h-3 w-28" />
      </CardHeader>
      <CardContent className="pt-0">
        <Skeleton className="h-7 w-20 mt-1" />
      </CardContent>
    </Card>
  );
}

function getPrevFilters(filters: AnalyticsFilters): AnalyticsFilters | null {
  if (!filters.start_date || !filters.end_date) return null;
  const start = new Date(filters.start_date);
  const end = new Date(filters.end_date);
  const days = Math.max(1, Math.round((end.getTime() - start.getTime()) / 86_400_000));
  const prevEnd = new Date(start);
  prevEnd.setDate(prevEnd.getDate() - 1);
  const prevStart = new Date(prevEnd);
  prevStart.setDate(prevStart.getDate() - days + 1);
  return {
    ...filters,
    start_date: prevStart.toISOString().split("T")[0],
    end_date: prevEnd.toISOString().split("T")[0],
  };
}

interface KPISectionProps {
  filters: AnalyticsFilters;
  refreshKey?: number;
}

export function KPISection({ filters, refreshKey }: KPISectionProps) {
  const [data, setData] = useState<KPIData | null>(null);
  const [prev, setPrev] = useState<KPIData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const api = new ApiClient(authenticationProviderInstance);
    setLoading(true);
    setError(null);

    const prevFilters = getPrevFilters(filters);

    Promise.all([
      api.analytics().getOverview(filters),
      prevFilters ? api.analytics().getOverview(prevFilters).catch(() => null) : Promise.resolve(null),
    ])
      .then(([kpi, prevKpi]) => {
        setData(kpi);
        setPrev(prevKpi);
        setLoading(false);
      })
      .catch((err) => {
        setError(err?.message ?? "Failed to load KPI data");
        setLoading(false);
      });
  }, [filters.start_date, filters.end_date, filters.agent_id, refreshKey]);

  if (loading) {
    return (
      <section className="space-y-6">
        <div>
          <h2 className="text-base font-semibold mb-3">AI Quality</h2>
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-7 gap-3">
            {Array.from({ length: 7 }).map((_, i) => <KPICardSkeleton key={i} />)}
          </div>
        </div>
        <div>
          <h2 className="text-base font-semibold mb-3">Business Health</h2>
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-7 gap-3">
            {Array.from({ length: 7 }).map((_, i) => <KPICardSkeleton key={i} />)}
          </div>
        </div>
      </section>
    );
  }

  if (error) {
    return (
      <section>
        <h2 className="text-base font-semibold mb-3">Overview</h2>
        <p className="text-sm text-destructive">{error}</p>
      </section>
    );
  }

  return (
    <section className="space-y-6">
      <div>
        <h2 className="text-base font-semibold mb-3">AI Quality</h2>
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-7 gap-3">
          <KPICard title="Answer Relevance" value={data?.answer_relevance ?? null} prevValue={prev?.answer_relevance} subtitle="LLM-judged" />
          <KPICard title="Resolution Quality" value={data?.resolution_quality ?? null} prevValue={prev?.resolution_quality} subtitle="Solved the need?" />
          <KPICard title="Composite Quality" value={data?.composite_quality ?? null} prevValue={prev?.composite_quality} subtitle="Weighted business score" />
          <KPICard title="Faithfulness" value={data?.faithfulness ?? null} prevValue={prev?.faithfulness} subtitle="Grounded in context" />
          <KPICard title="Coherence" value={data?.coherence ?? null} prevValue={prev?.coherence} subtitle="Query–response alignment" />
          <KPICard title="Toxicity" value={data?.toxicity ?? null} prevValue={prev?.toxicity} direction="bad" subtitle="Lower is better" />
          <KPICard title="Total Conversations" value={data?.total_conversations ?? null} prevValue={prev?.total_conversations} format="raw" direction="good" />
        </div>
      </div>

      <div>
        <h2 className="text-base font-semibold mb-3">Business Health</h2>
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-7 gap-3">
          <KPICard title="Answer Failure Rate" value={data?.answer_failure_rate ?? null} prevValue={prev?.answer_failure_rate} direction="bad" subtitle="Agent errors" />
          <KPICard title="Knowledge Gap Rate" value={data?.knowledge_gap_rate ?? null} prevValue={prev?.knowledge_gap_rate} direction="bad" subtitle="Missing catalog/docs" />
          <KPICard title="User Satisfaction" value={data?.user_satisfaction_score ?? null} prevValue={prev?.user_satisfaction_score} subtitle="From user ratings" />
          <KPICard title="Abandonment Rate" value={data?.user_abandonment_rate ?? null} prevValue={prev?.user_abandonment_rate} direction="bad" subtitle="Sessions user left" />
          <KPICard title="Avg Session Depth" value={data?.avg_session_depth ?? null} prevValue={prev?.avg_session_depth} format="raw" subtitle="Turns per conversation" />
          <KPICard title="Product Surface Rate" value={data?.product_surface_rate ?? null} prevValue={prev?.product_surface_rate} subtitle="Turns with products" />
          <KPICard title="Avg Response Latency" value={data?.avg_response_latency ?? null} prevValue={prev?.avg_response_latency} format="seconds" direction="bad" subtitle="Lower is better" />
        </div>
      </div>
    </section>
  );
}
