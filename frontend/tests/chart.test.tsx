import { renderToStaticMarkup } from "react-dom/server";
import { Line, LineChart } from "recharts";
import { describe, expect, it } from "vitest";

import { ChartContainer, ChartStyle } from "@/components/ui/chart";
import { Table, TableBody, TableCell, TableRow } from "@/components/ui/table";

describe("chart components", () => {
  it("emits themed CSS variables for chart series", () => {
    const markup = renderToStaticMarkup(
      <ChartStyle
        id="fitness"
        config={{
          sleep: {
            label: "Sleep score",
            theme: {
              light: "var(--chart-1)",
              dark: "var(--chart-2)",
            },
          },
          hrv: {
            label: "HRV",
            color: "var(--chart-3)",
          },
        }}
      />,
    );

    expect(markup).toContain("[data-chart=fitness]");
    expect(markup).toContain("--color-sleep: var(--chart-1)");
    expect(markup).toContain(".dark [data-chart=fitness]");
    expect(markup).toContain("--color-sleep: var(--chart-2)");
    expect(markup).toContain("--color-hrv: var(--chart-3)");
  });

  it("renders a reusable responsive chart container", () => {
    const markup = renderToStaticMarkup(
      <ChartContainer
        id="activity-summary"
        config={{
          distance: {
            label: "Distance",
            color: "var(--chart-1)",
          },
        }}
      >
        <LineChart data={[{ date: "2026-07-08", distance: 5 }]}>
          <Line dataKey="distance" stroke="var(--color-distance)" />
        </LineChart>
      </ChartContainer>,
    );

    expect(markup).toContain('data-slot="chart"');
    expect(markup).toContain('data-chart="chart-activity-summary"');
    expect(markup).toContain("--color-distance: var(--chart-1)");
    expect(markup).toContain("w-full min-w-0");
    expect(markup).toContain("overflow-hidden");
  });

  it("contains wide tables inside their own horizontal scroll region", () => {
    const markup = renderToStaticMarkup(
      <Table className="min-w-[760px]" scrollHint="Swipe for details.">
        <TableBody>
          <TableRow>
            <TableCell>Sample row</TableCell>
          </TableRow>
        </TableBody>
      </Table>,
    );

    expect(markup).toContain("min-w-0");
    expect(markup).toContain('data-slot="table-container"');
    expect(markup).toContain("max-w-full overflow-x-auto overscroll-x-contain");
    expect(markup).toContain("Swipe for details.");
    expect(markup).toContain("min-w-[760px]");
  });
});
