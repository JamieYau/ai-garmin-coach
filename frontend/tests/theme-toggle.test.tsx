import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it, vi } from "vitest";

import {
  getNextTheme,
  getThemeLabel,
  ThemeToggle,
} from "@/components/theme/ThemeToggle";

vi.mock("next-themes", () => ({
  useTheme: () => ({
    theme: "system",
    resolvedTheme: "dark",
    setTheme: vi.fn(),
  }),
}));

describe("ThemeToggle", () => {
  it("renders a stable loading control before hydration", () => {
    const markup = renderToStaticMarkup(<ThemeToggle />);

    expect(markup).toContain("Theme preference loading");
    expect(markup).toContain("disabled");
  });

  it("cycles from system to light, light to dark, and dark to system", () => {
    expect(getNextTheme("system")).toBe("light");
    expect(getNextTheme(undefined)).toBe("light");
    expect(getNextTheme("light")).toBe("dark");
    expect(getNextTheme("dark")).toBe("system");
  });

  it("labels theme states for accessible toggle text", () => {
    expect(getThemeLabel("system")).toBe("System theme");
    expect(getThemeLabel(undefined)).toBe("System theme");
    expect(getThemeLabel("light")).toBe("Light theme");
    expect(getThemeLabel("dark")).toBe("Dark theme");
  });
});
