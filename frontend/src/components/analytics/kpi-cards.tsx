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
  format?: "percent" | "raw" | "seconds";
  /** good = green when high, bad = green when low */
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

function KPICard({ title, value, format = "percent", direction = "good", subtitle }: KPICardProps) {
  const colorClass = getColorClass(value, direction);
  return (
    <Card>
      <CardHeader className="pb-1">
        <CardTitle className="text-xs font-medium text-muted-foreground leading-snug">{title}</CardTitle>
      </CardHeader>
      <CardContent className="pt-0">
        <p className={`text-2xl font-bold ${colorClass}`}>{formatValue(value, format)}</p>
        {subtitle && <p className="text-xs text-muted-foreground mt-0.5">{subtitle}</p>}
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

interface KPISectionProps {
  filters: AnalyticsFilters;
}

export function KPISection({ filters }: KPISectionProps) {
  const [data, setData] = useState<KPIData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const api = new ApiClient(authenticationProviderInstance);
    setLoading(true);
    setError(null);

    api
      .analytics()
      .getOverview(filters)
      .then((kpi) => {
        setData(kpi);
        setLoading(false);
      })
      .catch((err) => {
        setError(err?.message ?? "Failed to load KPI data");
        setLoading(false);
      });
  }, [filters.start_date, filters.end_date, filters.agent_id]);

  if (loading) {
    return (
      <section className="space-y-6">
        <div>
          <h2 className="text-base font-semibold mb-3">AI Quality</h2>
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
            {Array.from({ length: 6 }).map((_, i) => <KPICardSkeleton key={i} />)}
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
      {/* Row 1: AI Quality Proxies */}
      <div>
        <h2 className="text-base font-semibold mb-3">AI Quality</h2>
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
          <KPICard
            title="Answer Relevance"
            value={data?.answer_relevance ?? null}
            subtitle="LLM-judged"
          />
          <KPICard
            title="Composite Quality"
            value={data?.composite_quality ?? null}
            subtitle="Weighted business score"
          />
          <KPICard
            title="Faithfulness"
            value={data?.faithfulness ?? null}
            subtitle="Grounded in context"
          />
          <KPICard
            title="Coherence"
            value={data?.coherence ?? null}
            subtitle="Query–response alignment"
          />
          <KPICard
            title="Toxicity"
            value={data?.toxicity ?? null}
            direction="bad"
            subtitle="Lower is better"
          />
          <KPICard
            title="Total Conversations"
            value={data?.total_conversations ?? null}
            format="raw"
            direction="good"
          />
        </div>
      </div>

      {/* Row 2: Business Health */}
      <div>
        <h2 className="text-base font-semibold mb-3">Business Health</h2>
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-7 gap-3">
          <KPICard
            title="Answer Failure Rate"
            value={data?.answer_failure_rate ?? null}
            direction="bad"
            subtitle="Agent errors"
          />
          <KPICard
            title="Knowledge Gap Rate"
            value={data?.knowledge_gap_rate ?? null}
            direction="bad"
            subtitle="Missing catalog/docs"
          />
          <KPICard
            title="User Satisfaction"
            value={data?.user_satisfaction_score ?? null}
            subtitle="From user ratings"
          />
          <KPICard
            title="Abandonment Rate"
            value={data?.user_abandonment_rate ?? null}
            direction="bad"
            subtitle="Sessions user left"
          />
          <KPICard
            title="Avg Session Depth"
            value={data?.avg_session_depth ?? null}
            format="raw"
            subtitle="Turns per conversation"
          />
          <KPICard
            title="Product Surface Rate"
            value={data?.product_surface_rate ?? null}
            subtitle="Turns with products"
          />
          <KPICard
            title="Avg Response Latency"
            value={data?.avg_response_latency ?? null}
            format="seconds"
            direction="bad"
            subtitle="Lower is better"
          />
        </div>
      </div>
    </section>
  );
}
