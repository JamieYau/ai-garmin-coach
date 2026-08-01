import { cloneElement, isValidElement, type ReactNode } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it, vi } from "vitest";

import { SignOutButton } from "@/components/auth/SignOutButton";
import { MainNav } from "@/components/navigation/MainNav";

vi.mock("@/components/ui/dropdown-menu", () => {
  function Content({ children }: { children: ReactNode }) {
    return <div data-test-menu-content>{children}</div>;
  }

  function Trigger({
    children,
    render,
  }: {
    children: ReactNode;
    render?: ReactNode;
  }) {
    if (isValidElement(render)) {
      return cloneElement(render, undefined, children);
    }

    return <button type="button">{children}</button>;
  }

  return {
    DropdownMenu: ({ children }: { children: ReactNode }) => <>{children}</>,
    DropdownMenuContent: Content,
    DropdownMenuGroup: ({ children }: { children: ReactNode }) => (
      <div>{children}</div>
    ),
    DropdownMenuItem: ({
      children,
      render,
    }: {
      children: ReactNode;
      render?: ReactNode;
    }) =>
      isValidElement(render) ? (
        cloneElement(render, undefined, children)
      ) : (
        <button type="button">{children}</button>
      ),
    DropdownMenuLabel: ({ children }: { children: ReactNode }) => (
      <span>{children}</span>
    ),
    DropdownMenuSeparator: () => <hr />,
    DropdownMenuTrigger: Trigger,
  };
});

vi.mock("@/components/ui/sheet", () => {
  return {
    Sheet: ({ children }: { children: ReactNode }) => <>{children}</>,
    SheetContent: ({ children }: { children: ReactNode }) => (
      <aside>{children}</aside>
    ),
    SheetDescription: ({ children }: { children: ReactNode }) => (
      <p>{children}</p>
    ),
    SheetFooter: ({ children }: { children: ReactNode }) => (
      <footer>{children}</footer>
    ),
    SheetHeader: ({ children }: { children: ReactNode }) => (
      <div>{children}</div>
    ),
    SheetTitle: ({ children }: { children: ReactNode }) => <h2>{children}</h2>,
    SheetTrigger: ({
      children,
      render,
    }: {
      children: ReactNode;
      render?: ReactNode;
    }) =>
      isValidElement(render) ? (
        cloneElement(render, undefined, children)
      ) : (
        <button type="button">{children}</button>
      ),
  };
});

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
  it("keeps the four primary destinations direct and places secondary routes in More", () => {
    const markup = renderToStaticMarkup(
      <MainNav initialUser={{ email: "runner@example.com" }} />,
    );

    expect(markup).toContain('href="/dashboard"');
    expect(markup).toMatch(
      /<a class="flex items-center gap-2 font-semibold" href="\/dashboard">/,
    );
    expect(markup).toContain('href="/dashboard/activities"');
    expect(markup).toContain('href="/dashboard/recovery"');
    expect(markup).toContain('href="/dashboard/coach"');
    expect(markup).toContain("More");
    expect(markup).toContain('href="/dashboard/sources"');
    expect(markup).toContain('href="/settings"');
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
    expect(markup).toContain("Sign out");
    expect(markup).not.toContain("hidden max-w-44");
  });

  it("provides a labelled mobile navigation trigger", () => {
    const markup = renderToStaticMarkup(
      <MainNav initialUser={{ email: "runner@example.com" }} />,
    );

    expect(markup).toContain('aria-label="Open navigation menu"');
    expect(markup).toContain("lg:hidden");
    expect(markup).toContain("hidden items-center gap-1 lg:flex");
    expect(markup).toContain('aria-label="Dashboard navigation"');
    for (const destination of [
      "Overview",
      "Activities",
      "Recovery",
      "Coach",
      "Sources",
      "Settings",
    ]) {
      expect(markup).toContain(destination);
    }
  });

  it("marks the active mobile destination with aria-current", () => {
    const markup = renderToStaticMarkup(
      <MainNav initialUser={{ email: "runner@example.com" }} />,
    );

    expect(markup).toMatch(
      /<a class="flex min-h-11[^\"]*" aria-current="page" href="\/settings">/,
    );
  });

  it("keeps the Sheet sign-out action labelled at phone widths", () => {
    const markup = renderToStaticMarkup(<SignOutButton showLabel />);

    expect(markup).toContain('aria-label="Sign out"');
    expect(markup).toContain('<span class="inline">Sign out</span>');
  });
});
