import { useEffect, useRef, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { ApiClient } from "@/lib/api";
import { authenticationProviderInstance } from "@/lib/authentication-provider";
import { TimeSeriesData, TimeSeriesPoint } from "@/lib/types";
import { AnalyticsFilters } from "@/lib/api/analytics";

const METRICS = [
  { value: "answer_relevance", label: "Answer Relevance" },
  { value: "faithfulness", label: "Faithfulness" },
  { value: "coherence", label: "Coherence" },
  { value: "toxicity", label: "Toxicity" },
];

interface TooltipState {
  x: number;
  y: number;
  date: string;
  value: number;
  count: number;
}

interface SVGLineChartProps {
  data: TimeSeriesPoint[];
}

function SVGLineChart({ data }: SVGLineChartProps) {
  const svgRef = useRef<SVGSVGElement>(null);
  const [tooltip, setTooltip] = useState<TooltipState | null>(null);

  if (data.length === 0) {
    return (
      <div className="flex items-center justify-center h-48 text-sm text-muted-foreground">
        No data available for this period.
      </div>
    );
  }

  const width = 800;
  const height = 260;
  const paddingLeft = 48;
  const paddingRight = 24;
  const paddingTop = 16;
  const paddingBottom = 48;

  const chartWidth = width - paddingLeft - paddingRight;
  const chartHeight = height - paddingTop - paddingBottom;

  const minValue = 0;
  const maxValue = 1;

  const xStep = data.length > 1 ? chartWidth / (data.length - 1) : chartWidth / 2;

  function toSVGX(index: number): number {
    return paddingLeft + (data.length > 1 ? index * xStep : chartWidth / 2);
  }

  function toSVGY(value: number): number {
    return paddingTop + chartHeight - ((value - minValue) / (maxValue - minValue)) * chartHeight;
  }

  const points = data.map((d, i) => ({
    x: toSVGX(i),
    y: toSVGY(d.value),
    ...d,
  }));

  const polylinePoints = points.map((p) => `${p.x},${p.y}`).join(" ");

  // Y-axis ticks
  const yTicks = [0, 0.25, 0.5, 0.75, 1.0];

  // X-axis labels — show at most 8 evenly spaced labels
  const maxLabels = 8;
  const labelStep = Math.max(1, Math.ceil(data.length / maxLabels));
  const xLabels = data
    .map((d, i) => ({ index: i, date: d.date }))
    .filter((_, i) => i % labelStep === 0 || i === data.length - 1);

  function formatDateLabel(dateStr: string): string {
    const d = new Date(dateStr);
    return `${d.getMonth() + 1}/${d.getDate()}`;
  }

  function handleMouseEnter(point: (typeof points)[number]) {
    setTooltip({
      x: point.x,
      y: point.y,
      date: point.date,
      value: point.value,
      count: point.count,
    });
  }

  return (
    <div className="relative w-full overflow-x-auto">
      <svg
        ref={svgRef}
        viewBox={`0 0 ${width} ${height}`}
        className="w-full"
        onMouseLeave={() => setTooltip(null)}
      >
        {/* Y-axis grid lines and labels */}
        {yTicks.map((tick) => {
          const y = toSVGY(tick);
          return (
            <g key={tick}>
              <line
                x1={paddingLeft}
                y1={y}
                x2={width - paddingRight}
                y2={y}
                stroke="currentColor"
                strokeOpacity={0.1}
                strokeWidth={1}
              />
              <text
                x={paddingLeft - 6}
                y={y + 4}
                fontSize={11}
                textAnchor="end"
                fill="currentColor"
                fillOpacity={0.5}
              >
                {(tick * 100).toFixed(0)}%
              </text>
            </g>
          );
        })}

        {/* X-axis labels */}
        {xLabels.map(({ index, date }) => {
          const x = toSVGX(index);
          return (
            <text
              key={index}
              x={x}
              y={height - 8}
              fontSize={10}
              textAnchor="middle"
              fill="currentColor"
              fillOpacity={0.5}
            >
              {formatDateLabel(date)}
            </text>
          );
        })}

        {/* Axes */}
        <line
          x1={paddingLeft}
          y1={paddingTop}
          x2={paddingLeft}
          y2={paddingTop + chartHeight}
          stroke="currentColor"
          strokeOpacity={0.2}
          strokeWidth={1}
        />
        <line
          x1={paddingLeft}
          y1={paddingTop + chartHeight}
          x2={width - paddingRight}
          y2={paddingTop + chartHeight}
          stroke="currentColor"
          strokeOpacity={0.2}
          strokeWidth={1}
        />

        {/* Line */}
        {data.length > 1 && (
          <polyline
            points={polylinePoints}
            fill="none"
            stroke="hsl(221.2 83.2% 53.3%)"
            strokeWidth={2}
            strokeLinejoin="round"
            strokeLinecap="round"
          />
        )}

        {/* Data points */}
        {points.map((p, i) => (
          <circle
            key={i}
            cx={p.x}
            cy={p.y}
            r={4}
            fill="hsl(221.2 83.2% 53.3%)"
            stroke="white"
            strokeWidth={1.5}
            style={{ cursor: "pointer" }}
            onMouseEnter={() => handleMouseEnter(p)}
          />
        ))}

        {/* Tooltip */}
        {tooltip && (
          <g>
            <rect
              x={Math.min(tooltip.x + 8, width - 140)}
              y={Math.max(tooltip.y - 40, paddingTop)}
              width={130}
              height={52}
              rx={4}
              fill="hsl(var(--popover))"
              stroke="hsl(var(--border))"
              strokeWidth={1}
            />
            <text
              x={Math.min(tooltip.x + 14, width - 134)}
              y={Math.max(tooltip.y - 24, paddingTop + 16)}
              fontSize={11}
              fill="hsl(var(--popover-foreground))"
              fontWeight={600}
            >
              {tooltip.date}
            </text>
            <text
              x={Math.min(tooltip.x + 14, width - 134)}
              y={Math.max(tooltip.y - 10, paddingTop + 30)}
              fontSize={11}
              fill="hsl(var(--popover-foreground))"
            >
              Value: {(tooltip.value * 100).toFixed(1)}%
            </text>
            <text
              x={Math.min(tooltip.x + 14, width - 134)}
              y={Math.max(tooltip.y + 4, paddingTop + 44)}
              fontSize={11}
              fill="hsl(var(--muted-foreground))"
            >
              Count: {tooltip.count}
            </text>
          </g>
        )}
      </svg>
    </div>
  );
}

interface TimeSeriesSectionProps {
  filters: AnalyticsFilters;
}

export function TimeSeriesSection({ filters }: TimeSeriesSectionProps) {
  const [metric, setMetric] = useState<string>("answer_relevance");
  const [data, setData] = useState<TimeSeriesData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const api = new ApiClient(authenticationProviderInstance);
    setLoading(true);
    setError(null);

    api
      .analytics()
      .getTimeSeries(metric, filters)
      .then((ts) => {
        setData(ts);
        setLoading(false);
      })
      .catch((err) => {
        setError(err?.message ?? "Failed to load time series data");
        setLoading(false);
      });
  }, [metric, filters.start_date, filters.end_date, filters.agent_id]);

  const metricLabel = METRICS.find((m) => m.value === metric)?.label ?? metric;

  return (
    <section>
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-base font-semibold">Metric Over Time</h2>
        <Select value={metric} onValueChange={setMetric}>
          <SelectTrigger className="w-48">
            <SelectValue placeholder="Select metric" />
          </SelectTrigger>
          <SelectContent>
            {METRICS.map((m) => (
              <SelectItem key={m.value} value={m.value}>
                {m.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm font-medium text-muted-foreground">{metricLabel}</CardTitle>
        </CardHeader>
        <CardContent>
          {loading ? (
            <div className="space-y-2">
              <Skeleton className="h-48 w-full" />
            </div>
          ) : error ? (
            <p className="text-sm text-destructive py-8 text-center">{error}</p>
          ) : (
            <SVGLineChart data={data?.data ?? []} />
          )}
        </CardContent>
      </Card>
    </section>
  );
}
