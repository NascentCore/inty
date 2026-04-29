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

/** Query params for the ops-site voice recording detail view (hash route `voice-recording`). */
export type VoiceRecordingLinkParams = {
  audioUrl: string;
  userId: string;
  agentId: string;
  agentName?: string;
  createdAt: string | null;
  durationSeconds: number | null;
  messageId: number;
};

export function buildVoiceRecordingPageUrl(
  baseUrl: string,
  params: VoiceRecordingLinkParams,
): string {
  const search = new URLSearchParams();
  search.set("audioUrl", params.audioUrl);
  search.set("userId", params.userId);
  search.set("agentId", params.agentId);
  search.set("messageId", String(params.messageId));
  if (params.agentName != null && params.agentName !== "") {
    search.set("agentName", params.agentName);
  }
  if (params.createdAt != null && params.createdAt !== "") {
    search.set("createdAt", params.createdAt);
  }
  if (params.durationSeconds != null) {
    search.set("durationSeconds", String(params.durationSeconds));
  }
  return `${baseUrl}#voice-recording?${search.toString()}`;
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
