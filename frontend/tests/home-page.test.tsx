import { renderToStaticMarkup } from "react-dom/server";
import { beforeEach, describe, expect, it, vi } from "vitest";

import Home from "@/app/page";
import { getCurrentSession } from "@/lib/auth/server";

vi.mock("next/navigation", () => ({
  redirect: vi.fn(),
}));

vi.mock("@/lib/auth/server", () => ({
  getCurrentSession: vi.fn(),
}));

const getCurrentSessionMock = vi.mocked(getCurrentSession);
const redirectMock = vi.mocked(
  (await import("next/navigation")).redirect,
);

describe("Home", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("shows the public landing page without a session", async () => {
    getCurrentSessionMock.mockResolvedValue(null);

    const markup = renderToStaticMarkup(await Home());

    expect(markup).toContain("Personal training and recovery context");
    expect(redirectMock).not.toHaveBeenCalled();
  });

  it("redirects an authenticated visitor to the dashboard", async () => {
    getCurrentSessionMock.mockResolvedValue({
      user: { id: "user-1", email: "runner@example.com" },
    } as Awaited<ReturnType<typeof getCurrentSession>>);

    await Home();

    expect(redirectMock).toHaveBeenCalledWith("/dashboard");
  });
});
