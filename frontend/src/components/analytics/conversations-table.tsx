import { useEffect, useState } from "react";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { ApiClient } from "@/lib/api";
import { authenticationProviderInstance } from "@/lib/authentication-provider";
import { ConversationListData, ConversationWithMetrics } from "@/lib/types";
import { AnalyticsFilters } from "@/lib/api/analytics";
import { formatDistanceToNow } from "@/lib/date-utils";
import { SessionDetailModal } from "@/components/analytics/session-detail-modal";

const PAGE_SIZE = 20;

function formatMetric(value: number | undefined): string {
  if (value === undefined || value === null) return "—";
  return `${(value * 100).toFixed(1)}%`;
}

function formatDate(dateStr: string): string {
  const d = new Date(dateStr);
  return formatDistanceToNow(d, { addSuffix: true });
}

interface ConversationRowProps {
  conversation: ConversationWithMetrics;
  onViewDetail: (id: string) => void;
}

function ConversationRow({ conversation, onViewDetail }: ConversationRowProps) {
  return (
    <TableRow
      className="cursor-pointer"
      onClick={() => onViewDetail(conversation.id)}
    >
      <TableCell className="font-medium">{conversation.agent_name || conversation.agent_id}</TableCell>
      <TableCell className="text-muted-foreground">{formatDate(conversation.created_at)}</TableCell>
      <TableCell>{conversation.message_count}</TableCell>
      <TableCell>{formatMetric(conversation.metrics?.answer_relevance)}</TableCell>
      <TableCell>{formatMetric(conversation.metrics?.faithfulness)}</TableCell>
      <TableCell>{formatMetric(conversation.metrics?.coherence)}</TableCell>
      <TableCell>
        <Button
          variant="ghost"
          size="sm"
          onClick={(e) => {
            e.stopPropagation();
            onViewDetail(conversation.id);
          }}
        >
          View
        </Button>
      </TableCell>
    </TableRow>
  );
}

function TableRowSkeleton() {
  return (
    <TableRow>
      {Array.from({ length: 7 }).map((_, i) => (
        <TableCell key={i}>
          <Skeleton className="h-4 w-full" />
        </TableCell>
      ))}
    </TableRow>
  );
}

interface ConversationsSectionProps {
  filters: AnalyticsFilters;
}

export function ConversationsSection({ filters }: ConversationsSectionProps) {
  const [page, setPage] = useState(1);
  const [data, setData] = useState<ConversationListData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedConversationId, setSelectedConversationId] = useState<string | null>(null);
  const [modalOpen, setModalOpen] = useState(false);

  useEffect(() => {
    // Reset to page 1 when filters change
    setPage(1);
  }, [filters.start_date, filters.end_date, filters.agent_id]);

  useEffect(() => {
    const api = new ApiClient(authenticationProviderInstance);
    setLoading(true);
    setError(null);

    api
      .analytics()
      .getConversations({ ...filters, page, page_size: PAGE_SIZE })
      .then((result) => {
        setData(result);
        setLoading(false);
      })
      .catch((err) => {
        setError(err?.message ?? "Failed to load conversations");
        setLoading(false);
      });
  }, [page, filters.start_date, filters.end_date, filters.agent_id]);

  function handleViewDetail(id: string) {
    setSelectedConversationId(id);
    setModalOpen(true);
  }

  const totalPages = data ? Math.ceil(data.total / PAGE_SIZE) : 0;

  return (
    <section>
      <h2 className="text-base font-semibold mb-4">Conversations</h2>

      {error ? (
        <p className="text-sm text-destructive">{error}</p>
      ) : (
        <>
          <div className="rounded-md border">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Agent</TableHead>
                  <TableHead>Created At</TableHead>
                  <TableHead>Messages</TableHead>
                  <TableHead>Answer Relevance</TableHead>
                  <TableHead>Faithfulness</TableHead>
                  <TableHead>Coherence</TableHead>
                  <TableHead>Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {loading
                  ? Array.from({ length: 5 }).map((_, i) => <TableRowSkeleton key={i} />)
                  : data?.results.length === 0
                  ? (
                    <TableRow>
                      <TableCell colSpan={7} className="text-center text-muted-foreground py-8">
                        No conversations found for this period.
                      </TableCell>
                    </TableRow>
                  )
                  : data?.results.map((conv) => (
                    <ConversationRow
                      key={conv.id}
                      conversation={conv}
                      onViewDetail={handleViewDetail}
                    />
                  ))}
              </TableBody>
            </Table>
          </div>

          {/* Pagination */}
          {!loading && data && totalPages > 1 && (
            <div className="flex items-center justify-between mt-4">
              <p className="text-sm text-muted-foreground">
                Showing {((page - 1) * PAGE_SIZE) + 1}–{Math.min(page * PAGE_SIZE, data.total)} of {data.total} conversations
              </p>
              <div className="flex gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  disabled={page <= 1}
                  onClick={() => setPage((p) => Math.max(1, p - 1))}
                >
                  Previous
                </Button>
                <span className="flex items-center text-sm px-2">
                  Page {page} of {totalPages}
                </span>
                <Button
                  variant="outline"
                  size="sm"
                  disabled={!data.has_more && page >= totalPages}
                  onClick={() => setPage((p) => p + 1)}
                >
                  Next
                </Button>
              </div>
            </div>
          )}
        </>
      )}

      <SessionDetailModal
        open={modalOpen}
        onOpenChange={setModalOpen}
        conversationId={selectedConversationId}
      />
    </section>
  );
}
