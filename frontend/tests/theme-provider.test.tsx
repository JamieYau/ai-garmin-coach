import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { ThemeProvider } from "@/components/theme/ThemeProvider";

describe("ThemeProvider", () => {
  it("renders children inside the next-themes provider", () => {
    const markup = renderToStaticMarkup(
      <ThemeProvider
        attribute="class"
        defaultTheme="system"
        enableSystem
        disableTransitionOnChange
      >
        <main>Theme-aware content</main>
      </ThemeProvider>,
    );

    expect(markup).toContain("Theme-aware content");
  });
});
