import { describe, expect, it } from "vitest";

import { getCrossSubdomainCookieDomain } from "@/lib/auth/cookie-domain";

describe("getCrossSubdomainCookieDomain", () => {
  it("uses an explicit production cookie domain", () => {
    expect(
      getCrossSubdomainCookieDomain(
        "https://ca-garmin-coach-web.environment.azurecontainerapps.io",
        "environment.azurecontainerapps.io",
      ),
    ).toBe("environment.azurecontainerapps.io");
  });

  it("derives the shared parent domain from a subdomain URL", () => {
    expect(
      getCrossSubdomainCookieDomain(
        "https://ca-garmin-coach-web.redforest-92647fd6.uksouth.azurecontainerapps.io",
        undefined,
      ),
    ).toBe("redforest-92647fd6.uksouth.azurecontainerapps.io");
  });

  it("does not enable cross-subdomain cookies for a bare or invalid host", () => {
    expect(getCrossSubdomainCookieDomain("https://example.com", undefined)).toBeUndefined();
    expect(getCrossSubdomainCookieDomain("not a URL", undefined)).toBeUndefined();
  });
});
