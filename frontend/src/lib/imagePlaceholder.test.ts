import { describe, expect, it } from "vitest";
import { buildPlaceholderDataUrl, isTinyOrEmptyDataUrl } from "./imagePlaceholder";

describe("imagePlaceholder", () => {
  it("builds an svg data url containing the prompt", () => {
    const url = buildPlaceholderDataUrl("青空オフィス");
    expect(url.startsWith("data:image/svg+xml")).toBe(true);
    expect(decodeURIComponent(url)).toContain("青空オフィス");
    expect(decodeURIComponent(url)).toContain("MOCK IMAGE");
  });

  it("detects classic 1x1 png mocks", () => {
    expect(isTinyOrEmptyDataUrl(undefined)).toBe(true);
    expect(
      isTinyOrEmptyDataUrl(
        "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg==",
      ),
    ).toBe(true);
    expect(isTinyOrEmptyDataUrl("data:image/svg+xml;charset=utf-8,abc")).toBe(false);
  });
});
