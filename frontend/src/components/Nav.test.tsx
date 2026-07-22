import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { Nav } from "./Nav";

vi.mock("next/navigation", () => ({
  usePathname: () => "/tests",
}));

vi.mock("next/link", () => ({
  default: ({
    href,
    children,
    className,
  }: {
    href: string;
    children: React.ReactNode;
    className?: string;
  }) => (
    <a href={href} className={className}>
      {children}
    </a>
  ),
}));

describe("Nav", () => {
  it("renders brand and key routes including Tests", () => {
    render(<Nav />);
    expect(screen.getByText(/Bedrock/)).toBeTruthy();
    expect(screen.getByRole("link", { name: "Tests" }).getAttribute("href")).toBe("/tests");
    expect(screen.getByRole("link", { name: "Ops" }).getAttribute("href")).toBe("/ops");
    expect(screen.getByRole("link", { name: "GCP" }).getAttribute("href")).toBe("/gcp");
    expect(screen.getByRole("link", { name: "信用情報" }).getAttribute("href")).toBe("/credit");
    expect(screen.getByRole("link", { name: "Text / RAG" }).getAttribute("href")).toBe("/chat");
  });
});

