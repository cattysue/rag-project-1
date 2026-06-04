import type { ChatMessage } from "@/lib/types";

interface ChatMessageProps {
  message: ChatMessage;
}

export default function ChatMessageComponent({ message }: ChatMessageProps) {
  const isUser = message.role === "user";
  const hasSources = message.role === "assistant" && (message.sources?.length ?? 0) > 0;
  // sources가 없는 assistant 메시지 = "규정에 명시되어 있지 않습니다" 또는 에러 안내
  const isNoInfo = message.role === "assistant" && !hasSources;

  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"}`}>
      <div
        className={`max-w-[80%] rounded-2xl px-4 py-3 text-sm ${
          isUser
            ? "bg-blue-600 text-white"
            : isNoInfo
            ? "border border-amber-200 bg-amber-50 text-amber-800"
            : "border border-gray-200 bg-white text-gray-800"
        }`}
      >
        <p className="whitespace-pre-wrap">{message.content}</p>

        {hasSources && (
          <div className="mt-2 flex flex-col gap-1 border-t border-gray-100 pt-2">
            {message.sources!.map((src, i) => (
              <div
                key={i}
                className="rounded-lg bg-blue-50 px-3 py-1.5 text-xs text-blue-700"
              >
                {src.article_number && (
                  <span className="font-semibold">{src.article_number}</span>
                )}
                {src.article_number && src.article_title && (
                  <span className="mx-1">·</span>
                )}
                {src.article_title && <span>{src.article_title}</span>}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
