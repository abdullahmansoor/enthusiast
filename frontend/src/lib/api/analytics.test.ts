import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { AnalyticsApiClient } from "./analytics";

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------
const BASE = "http://localhost:8000";
const TOKEN = "test-token";

function makeClient(): AnalyticsApiClient {
  return new AnalyticsApiClient(BASE, { token: TOKEN } as any);
}

function mockFetch(body: unknown, status = 200): void {
  global.fetch = vi.fn().mockResolvedValue({
    ok: status >= 200 && status < 300,
    status,
    statusText: status === 200 ? "OK" : "Bad Request",
    json: () => Promise.resolve(body),
  } as Response);
}

function lastUrl(): string {
  return (global.fetch as ReturnType<typeof vi.fn>).mock.calls[0][0];
}

afterEach(() => vi.restoreAllMocks());

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------
describe("AnalyticsApiClient.getOverview", () => {
  it("calls the correct URL with no filters", async () => {
    const payload = { total_conversations: 5, date_range: { start: "2025-01-01", end: "2025-01-31" } };
    mockFetch(payload);
    const client = makeClient();
    const result = await client.getOverview();
    expect(lastUrl()).toContain("/api/analytics/overview/");
    expect(result.total_conversations).toBe(5);
  });

  it("appends date filters to the query string", async () => {
    mockFetch({});
    const client = makeClient();
    await client.getOverview({ start_date: "2025-01-01", end_date: "2025-01-31" });
    expect(lastUrl()).toContain("start_date=2025-01-01");
    expect(lastUrl()).toContain("end_date=2025-01-31");
  });

  it("appends agent_id filter", async () => {
    mockFetch({});
    const client = makeClient();
    await client.getOverview({ agent_id: "abc-123" });
    expect(lastUrl()).toContain("agent_id=abc-123");
  });

  it("throws on non-ok response", async () => {
    mockFetch({}, 500);
    const client = makeClient();
    await expect(client.getOverview()).rejects.toThrow();
  });
});

describe("AnalyticsApiClient.getTimeSeries", () => {
  it("sends metric_name in the query string", async () => {
    mockFetch({ metric_name: "faithfulness", data: [], date_range: {} });
    const client = makeClient();
    await client.getTimeSeries("faithfulness");
    expect(lastUrl()).toContain("metric_name=faithfulness");
  });

  it("includes granularity when provided", async () => {
    mockFetch({ data: [] });
    const client = makeClient();
    await client.getTimeSeries("coherence", { granularity: "weekly" });
    expect(lastUrl()).toContain("granularity=weekly");
  });

  it("does not include empty filters in query string", async () => {
    mockFetch({ data: [] });
    const client = makeClient();
    await client.getTimeSeries("toxicity", {});
    expect(lastUrl()).not.toContain("agent_id");
    expect(lastUrl()).not.toContain("start_date");
  });
});

describe("AnalyticsApiClient.getDistribution", () => {
  it("calls the distribution endpoint with metric_name", async () => {
    const payload = { metric_name: "answer_relevance", stats: { mean: 0.8, count: 100 }, values: [0.7, 0.9] };
    mockFetch(payload);
    const client = makeClient();
    const result = await client.getDistribution("answer_relevance");
    expect(lastUrl()).toContain("/api/analytics/distribution/");
    expect(lastUrl()).toContain("metric_name=answer_relevance");
    expect(result.stats.mean).toBe(0.8);
  });
});

describe("AnalyticsApiClient.getConversations", () => {
  it("calls conversations endpoint", async () => {
    mockFetch({ results: [], count: 0, total: 0, has_more: false });
    const client = makeClient();
    await client.getConversations();
    expect(lastUrl()).toContain("/api/analytics/conversations/");
  });

  it("includes pagination params", async () => {
    mockFetch({ results: [] });
    const client = makeClient();
    await client.getConversations({ page: 2, page_size: 10 });
    expect(lastUrl()).toContain("page=2");
    expect(lastUrl()).toContain("page_size=10");
  });
});

describe("AnalyticsApiClient.getConversationDetail", () => {
  it("calls the detail endpoint with the correct ID", async () => {
    const id = "conv-uuid-123";
    const payload = { conversation_id: id, messages: [], session_metrics: {} };
    mockFetch(payload);
    const client = makeClient();
    const result = await client.getConversationDetail(id);
    expect(lastUrl()).toContain(`/api/analytics/conversations/${id}/detail/`);
    expect(result.conversation_id).toBe(id);
  });
});

describe("AnalyticsApiClient.getMetricsCatalog", () => {
  it("calls the metrics endpoint", async () => {
    mockFetch([{ name: "toxicity", display_name: "Toxicity", level: "turn", stage: 2 }]);
    const client = makeClient();
    const result = await client.getMetricsCatalog();
    expect(lastUrl()).toContain("/api/analytics/metrics/");
    expect(result[0].name).toBe("toxicity");
  });

  it("filters by level", async () => {
    mockFetch([]);
    const client = makeClient();
    await client.getMetricsCatalog({ level: "session" });
    expect(lastUrl()).toContain("level=session");
  });

  it("filters by stage", async () => {
    mockFetch([]);
    const client = makeClient();
    await client.getMetricsCatalog({ stage: 1 });
    expect(lastUrl()).toContain("stage=1");
  });
});
