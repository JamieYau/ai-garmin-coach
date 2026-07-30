import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it, vi } from "vitest";

import { MainNav } from "@/components/navigation/MainNav";

vi.mock("next/navigation", () => ({
  usePathname: () => "/settings",
  useRouter: () => ({
    push: vi.fn(),
    refresh: vi.fn(),
  }),
}));

vi.mock("@/lib/auth/client", () => ({
  authClient: {
    useSession: () => ({
      data: null,
      isPending: false,
      error: null,
    }),
  },
}));

describe("MainNav", () => {
  it("keeps the four primary destinations direct and places settings in More", () => {
    const markup = renderToStaticMarkup(
      <MainNav initialUser={{ email: "runner@example.com" }} />,
    );

    expect(markup).toContain('href="/dashboard"');
    expect(markup).toContain('href="/dashboard/activities"');
    expect(markup).toContain('href="/dashboard/recovery"');
    expect(markup).toContain('href="/dashboard/coach"');
    expect(markup).not.toContain('href="/settings"');
    expect(markup).not.toContain('href="/dashboard/sources"');
    expect(markup).toContain("More");
    expect(markup).toContain('data-active="true"');
  });

  it("uses an accessible avatar account trigger instead of inline identity text", () => {
    const markup = renderToStaticMarkup(
      <MainNav
        initialUser={{ name: "Demo Runner", email: "runner@example.com" }}
      />,
    );

    expect(markup).toContain('aria-label="Demo Runner account menu"');
    expect(markup).toContain("Demo Runner");
    expect(markup).not.toContain("hidden max-w-44");
  });
});
