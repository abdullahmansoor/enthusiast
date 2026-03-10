import { describe, it, expect } from "vitest";
import { renderHook, act } from "@testing-library/react";
import { useToast, reducer } from "./use-toast";

// ---------------------------------------------------------------------------
// reducer unit tests (pure function — no DOM needed)
// ---------------------------------------------------------------------------
describe("toast reducer", () => {
  const baseState = { toasts: [] };

  it("ADD_TOAST appends a toast", () => {
    const newToast = { id: "1", title: "Hi", open: true } as any;
    const next = reducer(baseState, { type: "ADD_TOAST", toast: newToast });
    expect(next.toasts).toHaveLength(1);
    expect(next.toasts[0].title).toBe("Hi");
  });

  it("ADD_TOAST respects TOAST_LIMIT of 1 (keeps newest)", () => {
    const state = { toasts: [{ id: "1", title: "Old", open: true } as any] };
    const next = reducer(state, { type: "ADD_TOAST", toast: { id: "2", title: "New", open: true } as any });
    expect(next.toasts).toHaveLength(1);
    expect(next.toasts[0].title).toBe("New");
  });

  it("UPDATE_TOAST updates the matching toast", () => {
    const state = { toasts: [{ id: "1", title: "Old", open: true } as any] };
    const next = reducer(state, { type: "UPDATE_TOAST", toast: { id: "1", title: "Updated" } });
    expect(next.toasts[0].title).toBe("Updated");
  });

  it("DISMISS_TOAST marks the toast as closed", () => {
    const state = { toasts: [{ id: "1", title: "Hi", open: true } as any] };
    const next = reducer(state, { type: "DISMISS_TOAST", toastId: "1" });
    expect(next.toasts[0].open).toBe(false);
  });

  it("DISMISS_TOAST with no id closes all toasts", () => {
    const state = {
      toasts: [
        { id: "1", title: "A", open: true } as any,
        { id: "2", title: "B", open: true } as any,
      ],
    };
    const next = reducer(state, { type: "DISMISS_TOAST" });
    next.toasts.forEach((t) => expect(t.open).toBe(false));
  });

  it("REMOVE_TOAST removes the matching toast", () => {
    const state = { toasts: [{ id: "1", title: "Hi", open: false } as any] };
    const next = reducer(state, { type: "REMOVE_TOAST", toastId: "1" });
    expect(next.toasts).toHaveLength(0);
  });

  it("REMOVE_TOAST with no id clears all toasts", () => {
    const state = { toasts: [{ id: "1" } as any, { id: "2" } as any] };
    const next = reducer(state, { type: "REMOVE_TOAST" });
    expect(next.toasts).toHaveLength(0);
  });
});

// ---------------------------------------------------------------------------
// useToast hook tests
// ---------------------------------------------------------------------------
describe("useToast hook", () => {
  it("starts with no toasts", () => {
    const { result } = renderHook(() => useToast());
    expect(result.current.toasts).toHaveLength(0);
  });

  it("exposes a toast function", () => {
    const { result } = renderHook(() => useToast());
    expect(typeof result.current.toast).toBe("function");
  });

  it("exposes a dismiss function", () => {
    const { result } = renderHook(() => useToast());
    expect(typeof result.current.dismiss).toBe("function");
  });

  it("adds a toast when toast() is called", () => {
    const { result } = renderHook(() => useToast());
    act(() => {
      result.current.toast({ title: "Test Toast" });
    });
    expect(result.current.toasts[0].title).toBe("Test Toast");
  });
});
