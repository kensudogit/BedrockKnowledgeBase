import { describe, expect, it } from "vitest";
import { redirectUri } from "./cognito";

describe("cognito helpers", () => {
  it("redirectUri uses NEXT_PUBLIC_APP_URL when window is undefined", () => {
    expect(redirectUri()).toMatch(/\/auth\/callback$/);
  });
});
