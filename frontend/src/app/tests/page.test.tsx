import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("next/navigation", () => ({
  usePathname: () => "/tests",
}));

vi.mock("next/link", () => ({
  default: ({ href, children }: { href: string; children: React.ReactNode }) => (
    <a href={href}>{children}</a>
  ),
}));

vi.mock("@/lib/api", () => ({
  api: {
    testsLatest: vi.fn().mockResolvedValue({
      run: {
        run_id: "r1",
        status: "passed",
        passed: 2,
        failed: 0,
        skipped: 0,
        total: 2,
        duration_ms: 10,
        created_at: "2026-07-22T00:00:00Z",
        suites: [
          {
            suite: "python",
            runner: "pytest",
            passed: 2,
            failed: 0,
            total: 2,
            tests: [
              { id: "a", name: "test_a", file: "t.py", status: "passed", suite: "python", duration_ms: 1 },
            ],
          },
        ],
      },
    }),
    testsHistory: vi.fn().mockResolvedValue({ items: [] }),
    runTests: vi.fn(),
    testsRun: vi.fn(),
  },
}));

import TestsPage from "./page";

describe("TestsPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders title and run controls", async () => {
    render(<TestsPage />);
    expect(screen.getByRole("heading", { name: "Test Results" })).toBeTruthy();
    expect(screen.getByRole("button", { name: "全スイート実行" })).toBeTruthy();
    expect(await screen.findByText(/成功 2/)).toBeTruthy();
  });
});
