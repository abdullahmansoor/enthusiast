/**
 * BusinessInsightsSection
 *
 * Visualises the business-specific metrics using purpose-built chart types:
 *
 * 1. Conversation Funnel — stacked horizontal bar showing what fraction of
 *    sessions were: answered vs failed vs abandoned vs had knowledge gaps
 *
 * 2. Intent Distribution — horizontal bar chart showing the breakdown of
 *    customer query intents (product_search, price_inquiry, etc.)
 *
 * 3. Quality vs Satisfaction — 2-axis comparison card showing AI composite
 *    quality alongside direct user satisfaction score
 *
 * All charts are built with inline SVG (no charting library dependency).
 */

import { useEffect, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { ApiClient } from "@/lib/api";
import { authenticationProviderInstance } from "@/lib/authentication-provider";
import { KPIData } from "@/lib/types";
import { AnalyticsFilters } from "@/lib/api/analytics";

// Intent index → label (must match INTENT_LABELS in llm_judges.py)
const INTENT_LABELS: Record<number, string> = {
  0: "Product Search",
  1: "Price Inquiry",
  2: "Availability",
  3: "How to Use",
  4: "Support / Complaint",
  5: "Comparison",
  6: "General",
};

const INTENT_COLORS = [
  "hsl(221 83% 53%)",   // blue
  "hsl(142 71% 45%)",   // green
  "hsl(38 92% 50%)",    // amber
  "hsl(291 64% 55%)",   // purple
  "hsl(0 84% 60%)",     // red
  "hsl(197 71% 52%)",   // cyan
  "hsl(24 95% 53%)",    // orange
];

// ── Conversation Funnel ───────────────────────────────────────────────────────

interface FunnelProps {
  answered: number;      // 0-1
  failed: number;        // 0-1
  knowledgeGap: number;  // 0-1
  abandoned: number;     // 0-1
}

function ConversationFunnel({ answered, failed, knowledgeGap, abandoned }: FunnelProps) {
  const segments = [
    { label: "Answered", value: answered, color: "hsl(142 71% 45%)" },
    { label: "Knowledge Gap", value: knowledgeGap, color: "hsl(38 92% 50%)" },
    { label: "Failed", value: failed, color: "hsl(0 84% 60%)" },
    { label: "Abandoned", value: abandoned, color: "hsl(220 9% 60%)" },
  ];

  const total = segments.reduce((s, seg) => s + seg.value, 0) || 1;

  let cursor = 0;
  const rects = segments.map((seg) => {
    const pct = seg.value / total;
    const rect = { ...seg, x: cursor, width: pct };
    cursor += pct;
    return rect;
  });

  return (
    <div className="space-y-3">
      <svg viewBox="0 0 400 40" className="w-full rounded overflow-hidden">
        {rects.map((r) => (
          <rect
            key={r.label}
            x={r.x * 400}
            y={0}
            width={Math.max(r.width * 400, 1)}
            height={40}
            fill={r.color}
          />
        ))}
      </svg>
      <div className="flex flex-wrap gap-x-4 gap-y-1">
        {segments.map((seg) => (
          <div key={seg.label} className="flex items-center gap-1.5 text-xs">
            <span
              className="inline-block w-2.5 h-2.5 rounded-sm flex-shrink-0"
              style={{ background: seg.color }}
            />
            <span className="text-muted-foreground">{seg.label}</span>
            <span className="font-medium">{(seg.value * 100).toFixed(0)}%</span>
          </div>
        ))}
      </div>
    </div>
  );
}

// ── Intent Distribution Bar Chart ─────────────────────────────────────────────

interface IntentDistributionProps {
  /** Map of intent_index_float → fraction (0-1) */
  distribution: Record<string, number>;
}

function IntentDistributionChart({ distribution }: IntentDistributionProps) {
  const entries = Object.entries(distribution)
    .map(([key, val]) => ({
      label: INTENT_LABELS[parseInt(key)] ?? `Intent ${key}`,
      value: val,
      color: INTENT_COLORS[parseInt(key)] ?? INTENT_COLORS[6],
    }))
    .sort((a, b) => b.value - a.value);

  const max = Math.max(...entries.map((e) => e.value), 0.001);

  if (entries.length === 0) {
    return (
      <p className="text-sm text-muted-foreground text-center py-6">
        No intent data yet — requires LLM-judge sampling to be enabled.
      </p>
    );
  }

  return (
    <div className="space-y-2">
      {entries.map((entry) => (
        <div key={entry.label} className="flex items-center gap-2">
          <span className="text-xs text-muted-foreground w-32 shrink-0 text-right">
            {entry.label}
          </span>
          <div className="flex-1 h-5 bg-muted rounded overflow-hidden">
            <div
              className="h-full rounded transition-all"
              style={{
                width: `${(entry.value / max) * 100}%`,
                background: entry.color,
              }}
            />
          </div>
          <span className="text-xs font-medium w-10 text-right">
            {(entry.value * 100).toFixed(0)}%
          </span>
        </div>
      ))}
    </div>
  );
}

// ── Quality vs Satisfaction Gauge ─────────────────────────────────────────────

interface QualityGaugeProps {
  compositeQuality: number | null;
  userSatisfaction: number | null;
  answerRelevance: number | null;
  resolutionQuality: number | null;
  knowledgeGapRate: number | null;
}

function QualityGauge({ compositeQuality, userSatisfaction, answerRelevance, resolutionQuality, knowledgeGapRate }: QualityGaugeProps) {
  const items = [
    {
      label: "Composite Quality",
      value: compositeQuality,
      description: "Weighted business score (AI + reliability)",
    },
    {
      label: "User Satisfaction",
      value: userSatisfaction,
      description: "Direct voice-of-customer (from ratings)",
    },
    {
      label: "Answer Relevance",
      value: answerRelevance,
      description: "LLM-judged relevance to question",
    },
    {
      label: "Resolution Quality",
      value: resolutionQuality,
      description: "Did it actually solve the need?",
    },
    {
      label: "Knowledge Gap Rate",
      value: knowledgeGapRate,
      description: "Fraction of gaps (lower = better)",
      invert: true,
    },
  ];

  return (
    <div className="space-y-3">
      {items.map((item) => {
        const pct = item.value === null ? 0 : item.invert ? (1 - item.value) : item.value;
        const color =
          pct >= 0.7
            ? "hsl(142 71% 45%)"
            : pct >= 0.4
            ? "hsl(38 92% 50%)"
            : "hsl(0 84% 60%)";

        return (
          <div key={item.label}>
            <div className="flex justify-between items-baseline mb-1">
              <span className="text-xs font-medium">{item.label}</span>
              <span className="text-xs text-muted-foreground">
                {item.value === null ? "—" : `${(item.value * 100).toFixed(1)}%`}
              </span>
            </div>
            <div className="h-2 bg-muted rounded overflow-hidden">
              <div
                className="h-full rounded transition-all"
                style={{ width: `${pct * 100}%`, background: color }}
              />
            </div>
            <p className="text-xs text-muted-foreground mt-0.5">{item.description}</p>
          </div>
        );
      })}
    </div>
  );
}

// ── Main Section ─────────────────────────────────────────────────────────────

interface BusinessInsightsSectionProps {
  filters: AnalyticsFilters;
  refreshKey?: number;
}

export function BusinessInsightsSection({ filters, refreshKey }: BusinessInsightsSectionProps) {
  const [data, setData] = useState<KPIData | null>(null);
  const [intentDist, setIntentDist] = useState<Record<string, number>>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const api = new ApiClient(authenticationProviderInstance);
    setLoading(true);
    setError(null);

    Promise.all([
      api.analytics().getOverview(filters),
      api.analytics().getIntentDistribution(filters),
    ])
      .then(([kpi, dist]) => {
        setData(kpi);
        setIntentDist(dist);
        setLoading(false);
      })
      .catch((err) => {
        setError(err?.message ?? "Failed to load business insights");
        setLoading(false);
      });
  }, [filters.start_date, filters.end_date, filters.agent_id, refreshKey]);

  if (loading) {
    return (
      <section>
        <h2 className="text-base font-semibold mb-4">Business Insights</h2>
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
          {Array.from({ length: 3 }).map((_, i) => (
            <Card key={i}>
              <CardHeader><Skeleton className="h-4 w-40" /></CardHeader>
              <CardContent><Skeleton className="h-32 w-full" /></CardContent>
            </Card>
          ))}
        </div>
      </section>
    );
  }

  if (error) {
    return (
      <section>
        <h2 className="text-base font-semibold mb-4">Business Insights</h2>
        <p className="text-sm text-destructive">{error}</p>
      </section>
    );
  }

  // Derive funnel values from KPI data
  const failureRate = data?.answer_failure_rate ?? 0;
  const gapRate = data?.knowledge_gap_rate ?? 0;
  const abandonmentRate = data?.user_abandonment_rate ?? 0;
  // "answered" = everything not failed/gap/abandoned (simplified, may overlap)
  const answeredRate = Math.max(0, 1 - failureRate - gapRate - abandonmentRate * 0.3);

  return (
    <section>
      <h2 className="text-base font-semibold mb-4">Business Insights</h2>
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">

        {/* Conversation Funnel */}
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">Conversation Funnel</CardTitle>
            <p className="text-xs text-muted-foreground">
              What happens to each conversation
            </p>
          </CardHeader>
          <CardContent>
            <ConversationFunnel
              answered={answeredRate}
              failed={failureRate}
              knowledgeGap={gapRate}
              abandoned={abandonmentRate * 0.3}
            />
            <div className="mt-4 pt-3 border-t text-xs text-muted-foreground space-y-1">
              <p>
                <span className="font-medium text-foreground">Avg session depth: </span>
                {data?.avg_session_depth?.toFixed(1) ?? "—"} turns
              </p>
              <p>
                <span className="font-medium text-foreground">Product surface rate: </span>
                {data?.product_surface_rate !== null && data?.product_surface_rate !== undefined
                  ? `${(data.product_surface_rate * 100).toFixed(1)}%`
                  : "—"}
              </p>
              <p>
                <span className="font-medium text-foreground">Avg latency: </span>
                {data?.avg_response_latency !== null && data?.avg_response_latency !== undefined
                  ? `${data.avg_response_latency.toFixed(1)}s`
                  : "—"}
              </p>
            </div>
          </CardContent>
        </Card>

        {/* Intent Distribution */}
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">Query Intent Distribution</CardTitle>
            <p className="text-xs text-muted-foreground">
              What customers ask about (LLM-classified, sampled)
            </p>
          </CardHeader>
          <CardContent>
            <IntentDistributionChart distribution={intentDist} />
          </CardContent>
        </Card>

        {/* Quality vs Satisfaction */}
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">Quality Overview</CardTitle>
            <p className="text-xs text-muted-foreground">
              AI quality metrics vs direct customer signal
            </p>
          </CardHeader>
          <CardContent>
            <QualityGauge
              compositeQuality={data?.composite_quality ?? null}
              userSatisfaction={data?.user_satisfaction_score ?? null}
              answerRelevance={data?.answer_relevance ?? null}
              resolutionQuality={data?.resolution_quality ?? null}
              knowledgeGapRate={data?.knowledge_gap_rate ?? null}
            />
          </CardContent>
        </Card>

      </div>
    </section>
  );
}
