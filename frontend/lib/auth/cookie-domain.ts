export function getCrossSubdomainCookieDomain(
  authUrl: string | undefined,
  configuredDomain: string | undefined,
): string | undefined {
  if (configuredDomain) {
    return configuredDomain;
  }

  if (!authUrl) {
    return undefined;
  }

  try {
    const labels = new URL(authUrl).hostname.split(".");

    return labels.length >= 3 ? labels.slice(1).join(".") : undefined;
  } catch {
    return undefined;
  }
}
