import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { formatDistanceToNow } from "./date-utils";

describe("formatDistanceToNow", () => {
  const FIXED_NOW = new Date("2025-06-15T12:00:00Z");

  beforeEach(() => {
    vi.useFakeTimers();
    vi.setSystemTime(FIXED_NOW);
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("returns seconds for a very recent date", () => {
    const date = new Date("2025-06-15T11:59:30Z");
    expect(formatDistanceToNow(date)).toBe("30 seconds");
  });

  it("pluralises seconds correctly", () => {
    const date = new Date("2025-06-15T11:59:59Z");
    expect(formatDistanceToNow(date)).toBe("1 second");
  });

  it("returns minutes for dates < 1 hour ago", () => {
    const date = new Date("2025-06-15T11:30:00Z");
    expect(formatDistanceToNow(date)).toBe("30 minutes");
  });

  it("pluralises minutes correctly", () => {
    const date = new Date("2025-06-15T11:59:00Z");
    expect(formatDistanceToNow(date)).toBe("1 minute");
  });

  it("returns hours for dates < 1 day ago", () => {
    const date = new Date("2025-06-15T06:00:00Z");
    expect(formatDistanceToNow(date)).toBe("6 hours");
  });

  it("pluralises hours correctly", () => {
    const date = new Date("2025-06-15T11:00:00Z");
    expect(formatDistanceToNow(date)).toBe("1 hour");
  });

  it("returns days for dates < 30 days ago", () => {
    const date = new Date("2025-06-10T12:00:00Z");
    expect(formatDistanceToNow(date)).toBe("5 days");
  });

  it("pluralises days correctly", () => {
    const date = new Date("2025-06-14T12:00:00Z");
    expect(formatDistanceToNow(date)).toBe("1 day");
  });

  it("returns months for dates < 1 year ago", () => {
    const date = new Date("2025-04-15T12:00:00Z");
    expect(formatDistanceToNow(date)).toBe("2 months");
  });

  it("returns years for dates >= 1 year ago", () => {
    const date = new Date("2023-06-15T12:00:00Z");
    expect(formatDistanceToNow(date)).toBe("2 years");
  });

  it("adds suffix when addSuffix option is true", () => {
    const date = new Date("2025-06-15T11:00:00Z");
    expect(formatDistanceToNow(date, { addSuffix: true })).toBe("1 hour ago");
  });

  it("does not add suffix when addSuffix option is false", () => {
    const date = new Date("2025-06-15T11:00:00Z");
    expect(formatDistanceToNow(date, { addSuffix: false })).toBe("1 hour");
  });

  it("does not add suffix when option is omitted", () => {
    const date = new Date("2025-06-15T11:00:00Z");
    expect(formatDistanceToNow(date)).toBe("1 hour");
  });
});
