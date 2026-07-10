import { QueryClient } from "@tanstack/react-query";
import { describe, expect, it, vi } from "vitest";

import { invalidateDashboardData } from "@/hooks/useDataControls";

describe("data control hooks", () => {
  it("invalidates all dashboard queries after lifecycle mutations", async () => {
    const queryClient = new QueryClient();
    const invalidateQueries = vi.spyOn(queryClient, "invalidateQueries");

    await invalidateDashboardData(queryClient);

    expect(invalidateQueries).toHaveBeenCalledWith({
      queryKey: ["dashboard"],
    });
  });
});
