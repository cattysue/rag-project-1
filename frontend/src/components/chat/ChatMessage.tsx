import type { ChatMessage } from "@/lib/types";

interface ChatMessageProps {
  message: ChatMessage;
}

export default function ChatMessageComponent({ message }: ChatMessageProps) {
  const isUser = message.role === "user";
  // Pre-filter sources that have no displayable content (both fields null)
  const displayableSources =
    message.sources?.filter(
      (s) => s.article_number !== null || s.article_title !== null
    ) ?? [];
  const hasSources = message.role === "assistant" && displayableSources.length > 0;
  // isNoInfo: assistant reply with no usable citations (backend returned sources: [])
  const isNoInfo = !isUser && !hasSources;

  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"}`}>
      <div
        className={`max-w-[80%] rounded-2xl px-4 text-sm ${
          isUser
            ? "py-2 bg-blue-600 text-white"
            : isNoInfo
            ? "py-3 border border-amber-200 bg-amber-50 text-amber-800"
            : "py-3 border border-gray-200 bg-white text-gray-800"
        }`}
      >
        <p className="whitespace-pre-wrap">{message.content}</p>

        {hasSources && (
          <div className="mt-2 flex flex-col gap-1 border-t border-gray-100 pt-2">
            {displayableSources.map((src, i) => (
              <div
                key={src.article_number ?? `src-${i}`}
                className="rounded-lg bg-blue-50 px-3 py-1.5 text-xs text-blue-700"
              >
                {src.article_number !== null && (
                  <span className="font-semibold">{src.article_number}</span>
                )}
                {src.article_number !== null && src.article_title !== null && (
                  <span className="mx-1">·</span>
                )}
                {src.article_title !== null && <span>{src.article_title}</span>}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
