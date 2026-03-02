import "@testing-library/jest-dom";

// Polyfill fetch for jsdom
import { vi } from "vitest";

// Silence console.error for expected validation errors in tests
const originalError = console.error;
beforeAll(() => {
  console.error = (...args: any[]) => {
    if (typeof args[0] === "string" && args[0].includes("Warning:")) return;
    originalError(...args);
  };
});
afterAll(() => {
  console.error = originalError;
});

// Mock import.meta.env
vi.stubEnv("VITE_API_BASE", "http://localhost:8000");
