export function getEvaluationBaseUrl(): string {
  if (typeof window === "undefined") {
    return "";
  }
  return `${window.location.origin}${window.location.pathname}`;
}

export function buildAgentProfilePageUrl(
  baseUrl: string,
  agentId: string,
): string {
  return `${baseUrl}#agents?agentId=${encodeURIComponent(agentId)}`;
}

export function buildUserProfilePageUrl(
  baseUrl: string,
  userId: string,
): string {
  return `${baseUrl}#user-daily-messages?userId=${encodeURIComponent(userId)}`;
}

export function buildReportUserConversationsPageUrl(
  baseUrl: string,
  reportId: string,
): string {
  return `${baseUrl}#report-user-conversations?reportId=${encodeURIComponent(reportId)}`;
}

export function parseEvaluationHashRoute(hash: string): {
  pageKey: string;
  params: URLSearchParams;
} {
  const normalizedHash = hash.startsWith("#") ? hash.slice(1) : hash;
  const [pageKey = "", queryString = ""] = normalizedHash.split("?", 2);
  return {
    pageKey,
    params: new URLSearchParams(queryString),
  };
}

function getHashParamForPage(
  hash: string,
  pageKey: string,
  paramName: string,
): string {
  const parsed = parseEvaluationHashRoute(hash);
  if (parsed.pageKey !== pageKey) {
    return "";
  }
  return parsed.params.get(paramName)?.trim() || "";
}

export function getDeepLinkedAgentIdFromHash(hash: string): string {
  return getHashParamForPage(hash, "agents", "agentId");
}

export function getDeepLinkedUserIdFromHash(hash: string): string {
  return getHashParamForPage(hash, "user-daily-messages", "userId");
}

export function getDeepLinkedReportIdFromHash(hash: string): string {
  return getHashParamForPage(hash, "report-user-conversations", "reportId");
}
