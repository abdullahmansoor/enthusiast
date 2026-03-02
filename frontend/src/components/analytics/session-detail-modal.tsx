import { useEffect, useState } from "react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "@/components/ui/dialog";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { ApiClient } from "@/lib/api";
import { authenticationProviderInstance } from "@/lib/authentication-provider";
import { SessionDetail, MessageDetail } from "@/lib/types";

const METRIC_DISPLAY_NAMES: Record<string, string> = {
  answer_relevance: "Answer Relevance",
  faithfulness: "Faithfulness",
  coherence: "Coherence",
  toxicity: "Toxicity",
  composite_quality: "Composite Quality",
};

function formatMetricValue(value: number): string {
  return `${(value * 100).toFixed(1)}%`;
}

function getMetricBadgeVariant(
  metricName: string,
  value: number
): "default" | "secondary" | "destructive" | "outline" {
  if (metricName === "toxicity") {
    return value > 0.3 ? "destructive" : "secondary";
  }
  if (value >= 0.7) return "default";
  if (value >= 0.5) return "outline";
  return "destructive";
}

function MetricBadge({ name, value }: { name: string; value: number }) {
  const displayName = METRIC_DISPLAY_NAMES[name] ?? name;
  const variant = getMetricBadgeVariant(name, value);
  return (
    <Badge variant={variant} className="text-xs">
      {displayName}: {formatMetricValue(value)}
    </Badge>
  );
}

interface MessageMetricsProps {
  metrics: Record<string, number>;
}

function MessageMetrics({ metrics }: MessageMetricsProps) {
  const [expanded, setExpanded] = useState(false);
  const entries = Object.entries(metrics);

  if (entries.length === 0) return null;

  return (
    <div className="mt-1.5">
      <button
        className="text-xs text-muted-foreground hover:text-foreground underline-offset-2 hover:underline"
        onClick={() => setExpanded((prev) => !prev)}
      >
        {expanded ? "Hide metrics" : "Show metrics"}
      </button>
      {expanded && (
        <div className="flex flex-wrap gap-1.5 mt-1.5">
          {entries.map(([name, value]) => (
            <MetricBadge key={name} name={name} value={value} />
          ))}
        </div>
      )}
    </div>
  );
}

interface MessageBubbleProps {
  message: MessageDetail;
}

function MessageBubble({ message }: MessageBubbleProps) {
  const isUser = message.role === "user";

  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"} mb-4`}>
      <div className={`max-w-[75%] ${isUser ? "items-end" : "items-start"} flex flex-col`}>
        <div
          className={`px-4 py-2.5 rounded-2xl text-sm leading-relaxed ${
            isUser
              ? "bg-blue-600 text-white rounded-br-sm"
              : "bg-muted text-foreground rounded-bl-sm"
          }`}
        >
          <p className="whitespace-pre-wrap">{message.text}</p>
        </div>
        {!isUser && message.metrics && Object.keys(message.metrics).length > 0 && (
          <MessageMetrics metrics={message.metrics} />
        )}
      </div>
    </div>
  );
}

interface SessionDetailModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  conversationId: string | null;
}

export function SessionDetailModal({ open, onOpenChange, conversationId }: SessionDetailModalProps) {
  const [detail, setDetail] = useState<SessionDetail | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!open || !conversationId) {
      setDetail(null);
      setError(null);
      return;
    }

    const api = new ApiClient(authenticationProviderInstance);
    setLoading(true);
    setError(null);

    api
      .analytics()
      .getConversationDetail(conversationId)
      .then((d) => {
        setDetail(d);
        setLoading(false);
      })
      .catch((err) => {
        setError(err?.message ?? "Failed to load session detail");
        setLoading(false);
      });
  }, [open, conversationId]);

  const sessionMetricEntries = detail ? Object.entries(detail.session_metrics) : [];

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl w-full max-h-[90vh] flex flex-col overflow-hidden p-0">
        {/* Header */}
        <div className="px-6 pt-6 pb-4 border-b flex-shrink-0">
          <DialogHeader>
            <DialogTitle>
              {loading ? (
                <Skeleton className="h-5 w-48" />
              ) : (
                `Session: ${detail?.agent_name ?? "Unknown Agent"}`
              )}
            </DialogTitle>
            <DialogDescription>
              {loading ? (
                <Skeleton className="h-4 w-64 mt-1" />
              ) : detail ? (
                `${detail.message_count} messages · ${new Date(detail.created_at).toLocaleString()}`
              ) : null}
            </DialogDescription>
          </DialogHeader>

          {/* Session-level metrics summary */}
          {!loading && sessionMetricEntries.length > 0 && (
            <div className="flex flex-wrap gap-2 mt-3">
              {sessionMetricEntries.map(([name, value]) => (
                <MetricBadge key={name} name={name} value={value} />
              ))}
            </div>
          )}

          {loading && (
            <div className="flex gap-2 mt-3 flex-wrap">
              {Array.from({ length: 4 }).map((_, i) => (
                <Skeleton key={i} className="h-5 w-28" />
              ))}
            </div>
          )}
        </div>

        {/* Chat replay */}
        <div className="flex-1 overflow-y-auto px-6 py-4">
          {loading ? (
            <div className="space-y-4">
              {Array.from({ length: 4 }).map((_, i) => (
                <div key={i} className={`flex ${i % 2 === 0 ? "justify-end" : "justify-start"}`}>
                  <Skeleton className="h-16 w-64 rounded-2xl" />
                </div>
              ))}
            </div>
          ) : error ? (
            <p className="text-sm text-destructive text-center py-8">{error}</p>
          ) : detail && detail.messages.length > 0 ? (
            detail.messages.map((msg) => (
              <MessageBubble key={msg.id} message={msg} />
            ))
          ) : (
            <p className="text-sm text-muted-foreground text-center py-8">
              No messages in this session.
            </p>
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
}
