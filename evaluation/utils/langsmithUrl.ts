/**
 * LangSmith trace URL 组装
 * 与 ChatPage 使用的 project 一致
 */
const LANGSMITH_TRACE_BASE =
  "https://smith.langchain.com/o/e91da43a-00f9-4d3e-a615-413bcf3ba1ac/projects/p/4b428bee-1b11-4e87-b87f-ace2c5aa162a";

export function getLangsmithTraceUrl(
  traceId: string | null | undefined,
): string | null {
  if (!traceId || typeof traceId !== "string" || !traceId.trim()) {
    return null;
  }
  return `${LANGSMITH_TRACE_BASE}/r/${traceId.trim()}`;
}
