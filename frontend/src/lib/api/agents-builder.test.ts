import { describe, it, expect, vi, afterEach } from "vitest";
import { AgentsApiClient } from "./agents";

const BASE = "http://localhost:8000";

function makeClient(): AgentsApiClient {
  return new AgentsApiClient(BASE, { token: "tok" } as any);
}

function mockFetch(body: unknown, status = 200): void {
  global.fetch = vi.fn().mockResolvedValue({
    ok: status >= 200 && status < 300,
    status,
    statusText: status === 200 ? "OK" : "Error",
    json: () => Promise.resolve(body),
  } as Response);
}

function lastUrl(): string {
  return (global.fetch as ReturnType<typeof vi.fn>).mock.calls[0][0];
}

function lastInit(): RequestInit {
  return (global.fetch as ReturnType<typeof vi.fn>).mock.calls[0][1];
}

afterEach(() => vi.restoreAllMocks());

const AGENT_ID = "550e8400-e29b-41d4-a716-446655440000";

// ---------------------------------------------------------------------------
// listBuilderAgents
// ---------------------------------------------------------------------------
describe("AgentsApiClient.listBuilderAgents", () => {
  it("calls agents-builder list endpoint", async () => {
    mockFetch({ count: 1, results: [{ id: AGENT_ID, name: "Bot", status: "draft" }] });
    const result = await makeClient().listBuilderAgents();
    expect(lastUrl()).toContain("/api/agents-builder/");
    expect(result.results[0].id).toBe(AGENT_ID);
  });

  it("applies status filter via query string", async () => {
    mockFetch({ count: 0, results: [] });
    await makeClient().listBuilderAgents({ status: "published" });
    expect(lastUrl()).toContain("status=published");
  });

  it("applies pagination params", async () => {
    mockFetch({ results: [] });
    await makeClient().listBuilderAgents({ page: 2, page_size: 5 });
    expect(lastUrl()).toContain("page=2");
    expect(lastUrl()).toContain("page_size=5");
  });
});

// ---------------------------------------------------------------------------
// getBuilderAgent
// ---------------------------------------------------------------------------
describe("AgentsApiClient.getBuilderAgent", () => {
  it("fetches a single agent by ID", async () => {
    mockFetch({ id: AGENT_ID, name: "My Agent", status: "draft" });
    const result = await makeClient().getBuilderAgent(AGENT_ID);
    expect(lastUrl()).toContain(`/api/agents-builder/${AGENT_ID}/`);
    expect(result.name).toBe("My Agent");
  });

  it("throws on 404", async () => {
    mockFetch({ detail: "Not found" }, 404);
    await expect(makeClient().getBuilderAgent(AGENT_ID)).rejects.toThrow();
  });
});

// ---------------------------------------------------------------------------
// createBuilderAgent
// ---------------------------------------------------------------------------
describe("AgentsApiClient.createBuilderAgent", () => {
  it("POSTs to agents-builder with correct body", async () => {
    mockFetch({ id: AGENT_ID, name: "New", status: "draft" }, 201);
    const data = { name: "New", description: "desc", dataset: 42 };
    const result = await makeClient().createBuilderAgent(data);
    expect(lastUrl()).toContain("/api/agents-builder/");
    expect(lastInit().method).toBe("POST");
    const body = JSON.parse(lastInit().body as string);
    expect(body.name).toBe("New");
    expect(body.dataset).toBe(42);
    expect(result.id).toBe(AGENT_ID);
  });

  it("throws ApiError on 400 validation error", async () => {
    mockFetch({ name: ["This field is required."] }, 400);
    await expect(makeClient().createBuilderAgent({ name: "", dataset: 1 })).rejects.toThrow();
  });
});

// ---------------------------------------------------------------------------
// updateBuilderAgent
// ---------------------------------------------------------------------------
describe("AgentsApiClient.updateBuilderAgent", () => {
  it("PATCHes the agent with updated fields", async () => {
    mockFetch({ id: AGENT_ID, name: "Updated" });
    await makeClient().updateBuilderAgent(AGENT_ID, { name: "Updated" });
    expect(lastInit().method).toBe("PATCH");
    expect(lastUrl()).toContain(`/api/agents-builder/${AGENT_ID}/`);
    const body = JSON.parse(lastInit().body as string);
    expect(body.name).toBe("Updated");
  });
});

// ---------------------------------------------------------------------------
// deleteBuilderAgent
// ---------------------------------------------------------------------------
describe("AgentsApiClient.deleteBuilderAgent", () => {
  it("sends DELETE request", async () => {
    mockFetch(null, 204);
    await makeClient().deleteBuilderAgent(AGENT_ID);
    expect(lastInit().method).toBe("DELETE");
    expect(lastUrl()).toContain(`/api/agents-builder/${AGENT_ID}/`);
  });

  it("throws on error response", async () => {
    mockFetch({}, 403);
    await expect(makeClient().deleteBuilderAgent(AGENT_ID)).rejects.toThrow();
  });
});

// ---------------------------------------------------------------------------
// publishBuilderAgent
// ---------------------------------------------------------------------------
describe("AgentsApiClient.publishBuilderAgent", () => {
  it("POSTs to the publish action endpoint", async () => {
    mockFetch({ id: AGENT_ID, status: "published" });
    const result = await makeClient().publishBuilderAgent(AGENT_ID);
    expect(lastUrl()).toContain(`/api/agents-builder/${AGENT_ID}/publish/`);
    expect(lastInit().method).toBe("POST");
    expect(result.status).toBe("published");
  });
});

// ---------------------------------------------------------------------------
// cloneBuilderAgent
// ---------------------------------------------------------------------------
describe("AgentsApiClient.cloneBuilderAgent", () => {
  it("POSTs to the clone action with optional name", async () => {
    mockFetch({ id: "new-uuid", name: "My Agent (Copy)", status: "draft" });
    const result = await makeClient().cloneBuilderAgent(AGENT_ID, "My Agent (Copy)");
    expect(lastUrl()).toContain(`/api/agents-builder/${AGENT_ID}/clone/`);
    expect(lastInit().method).toBe("POST");
    expect(result.name).toBe("My Agent (Copy)");
  });
});

// ---------------------------------------------------------------------------
// testBuilderAgent
// ---------------------------------------------------------------------------
describe("AgentsApiClient.testBuilderAgent", () => {
  it("POSTs the test message and returns response", async () => {
    const payload = { response: "Hello!", conversation_id: "conv-1", message_id: 1, metadata: {} };
    mockFetch(payload);
    const result = await makeClient().testBuilderAgent(AGENT_ID, "Hello?");
    expect(lastUrl()).toContain(`/api/agents-builder/${AGENT_ID}/test/`);
    expect(lastInit().method).toBe("POST");
    expect(JSON.parse(lastInit().body as string).message).toBe("Hello?");
    expect(result.response).toBe("Hello!");
  });
});

// ---------------------------------------------------------------------------
// getBuilderAgentVersions
// ---------------------------------------------------------------------------
describe("AgentsApiClient.getBuilderAgentVersions", () => {
  it("fetches the versions list", async () => {
    mockFetch([{ id: AGENT_ID, version: 1 }, { id: AGENT_ID, version: 2 }]);
    const result = await makeClient().getBuilderAgentVersions(AGENT_ID);
    expect(lastUrl()).toContain(`/api/agents-builder/${AGENT_ID}/versions/`);
    expect(result).toHaveLength(2);
  });
});
