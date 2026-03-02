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
  isPercentage?: boolean;
  noColor?: boolean;
}

function getColorClass(value: number | null): string {
  if (value === null) return "text-muted-foreground";
  if (value >= 0.7) return "text-green-600";
  if (value >= 0.5) return "text-yellow-600";
  return "text-red-600";
}

function KPICard({ title, value, isPercentage = true, noColor = false }: KPICardProps) {
  const colorClass = noColor ? "text-foreground" : getColorClass(value);
  const displayValue =
    value === null
      ? "—"
      : isPercentage
      ? `${(value * 100).toFixed(1)}%`
      : value.toLocaleString();

  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-sm font-medium text-muted-foreground">{title}</CardTitle>
      </CardHeader>
      <CardContent>
        <p className={`text-3xl font-bold ${colorClass}`}>{displayValue}</p>
      </CardContent>
    </Card>
  );
}

function KPICardSkeleton() {
  return (
    <Card>
      <CardHeader className="pb-2">
        <Skeleton className="h-4 w-32" />
      </CardHeader>
      <CardContent>
        <Skeleton className="h-8 w-20" />
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
      <section>
        <h2 className="text-base font-semibold mb-4">Overview</h2>
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-4">
          {Array.from({ length: 6 }).map((_, i) => (
            <KPICardSkeleton key={i} />
          ))}
        </div>
      </section>
    );
  }

  if (error) {
    return (
      <section>
        <h2 className="text-base font-semibold mb-4">Overview</h2>
        <p className="text-sm text-destructive">{error}</p>
      </section>
    );
  }

  return (
    <section>
      <h2 className="text-base font-semibold mb-4">Overview</h2>
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-4">
        <KPICard title="Answer Relevance" value={data?.answer_relevance ?? null} />
        <KPICard title="Faithfulness" value={data?.faithfulness ?? null} />
        <KPICard title="Coherence" value={data?.coherence ?? null} />
        <KPICard title="Toxicity" value={data?.toxicity ?? null} />
        <KPICard title="Composite Quality" value={data?.composite_quality ?? null} />
        <KPICard
          title="Total Conversations"
          value={data?.total_conversations ?? null}
          isPercentage={false}
          noColor
        />
      </div>
    </section>
  );
}
