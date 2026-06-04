"use client";

import { useState, useRef, useEffect } from "react";
import ChatMessageComponent from "@/components/chat/ChatMessage";
import ChatInput from "@/components/chat/ChatInput";
import { sendChatMessage } from "@/lib/api";
import type { ChatMessage } from "@/lib/types";

export default function ChatWindow() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);
  const abortControllerRef = useRef<AbortController | null>(null);
  const keyCounterRef = useRef(0);
  const nextKey = () => `msg-${++keyCounterRef.current}`;

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, errorMessage]);

  // Abort in-flight request on unmount
  useEffect(() => {
    return () => {
      abortControllerRef.current?.abort();
    };
  }, []);

  const handleSend = async (question: string) => {
    setErrorMessage(null);

    const userMessage: ChatMessage = { _key: nextKey(), role: "user", content: question };
    // history = prior conversation only (excludes current question, which is sent separately)
    const history = messages.map(({ role, content }) => ({ role, content }));

    setMessages((prev) => [...prev, userMessage]);
    setIsLoading(true);

    abortControllerRef.current?.abort();  // cancel any previous in-flight request
    abortControllerRef.current = new AbortController();

    try {
      const res = await sendChatMessage(question, history, abortControllerRef.current.signal);

      const botMessage: ChatMessage = {
        _key: nextKey(),
        role: "assistant",
        content: res.answer,
        sources: res.sources,
      };
      setMessages((prev) => [...prev, botMessage]);
    } catch (err) {
      if (err instanceof Error && err.name === "AbortError") return;
      setErrorMessage("서버에 연결할 수 없습니다. 잠시 후 다시 시도해 주세요.");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="flex flex-1 flex-col overflow-hidden">
      <div className="flex-1 overflow-y-auto px-4 py-6">
        <div className="mx-auto flex max-w-2xl flex-col gap-4">
          {messages.length === 0 && !errorMessage && (
            <div className="flex flex-col items-center gap-3 text-center">
              <p className="text-sm text-gray-400">
                규정에 대해 궁금한 점을 질문해 보세요.
              </p>
              <div className="rounded-lg border border-amber-100 bg-amber-50 px-4 py-3 text-left text-xs text-amber-700 max-w-sm">
                <p className="font-medium mb-1">💡 정확한 답변을 위한 팁</p>
                <p>공식 용어로 질문하면 더 정확한 답변을 받을 수 있어요.</p>
                <ul className="mt-1.5 space-y-0.5 list-none">
                  <li>✓ <span className="line-through text-amber-400">지참 금지 물건</span> → <span className="font-medium">반입금지 물건</span></li>
                  <li>✓ <span className="line-through text-amber-400">결석해서 시험 못 봤을 때</span> → <span className="font-medium">결시 성적 처리</span></li>
                  <li>✓ <span className="line-through text-amber-400">성적 불만 신청</span> → <span className="font-medium">이의신청 기간</span></li>
                </ul>
              </div>
            </div>
          )}
          {messages.map((msg) => (
            <ChatMessageComponent key={msg._key} message={msg} />
          ))}
          {errorMessage && (
            <p className="text-center text-sm text-red-500">{errorMessage}</p>
          )}
          <div ref={bottomRef} />
        </div>
      </div>

      <div className="mx-auto w-full max-w-2xl">
        <ChatInput onSend={handleSend} isLoading={isLoading} />
      </div>
    </div>
  );
}
