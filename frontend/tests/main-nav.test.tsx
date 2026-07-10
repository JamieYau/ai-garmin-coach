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
  it("links to the authenticated settings page", () => {
    const markup = renderToStaticMarkup(
      <MainNav initialUser={{ email: "runner@example.com" }} />,
    );

    expect(markup).toContain('href="/settings"');
    expect(markup).toContain("Settings");
    expect(markup).toContain('aria-current="page"');
  });
});
